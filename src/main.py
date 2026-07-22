from fastapi import FastAPI,Request
from src.router.Agenticask import router
from src.router.searchpaper import arxivrouter 
from src.router.paperIngestion import ingestionrouter 
from fastapi.responses import JSONResponse
import logfire
from src.config import get_settings
from src.services.arxiv.factory import make_arxiv_client
from src.services.embeddings.factory import make_embeddings_service
from src.services.guardrails.Input_guardrails.factory import make_Input_guardrails
from src.services.indexing.factory import make_hybrid_indexing_service
from src.services.pdf_parser.factory import make_pdf_parser_service
from src.services.langfuse.factory import make_langfuse_tracer
from src.services.llm_gateway.factory import make_llm_client
from src.services.logfire.factory import configure_logfire
from src.services.opensearch.factory import make_opensearch_client
from src.services.agents.factory import make_agentic_rag_service
from src.services.paperIngestion.factory import get_paperIngestion
from src.services.cache.factory import make_cache_client

from src.db.factory import make_database
from arq import create_pool
from arq.connections import RedisSettings
from contextlib import asynccontextmanager
import logging
# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting RAG API...")

    settings = get_settings()
    app.state.settings =settings

    app.state.arxiv_client      = make_arxiv_client()
    app.state.embedding_client  = make_embeddings_service()
    app.state.guardrails_client = make_Input_guardrails()
    app.state.indexing_client   = make_hybrid_indexing_service()
    app.state.pdf_parser_client = make_pdf_parser_service()
    app.state.langfuse_client   = make_langfuse_tracer()
    app.state.llm_client        = make_llm_client()
    app.state.cache_client      = make_cache_client(settings)
    
    # ARQ redis pool — used to enqueue ingestion jobs onto the worker queue
    app.state.redis = await create_pool(RedisSettings(
        host= settings.redis.host,
        port=settings.redis.port,
        username=settings.redis.username,
        password=settings.redis.password,
        ssl=settings.redis.ssl
    ))
    
    logger.info("ARQ redis pool connected")

    app.state.paper_ingestion_pipeline = get_paperIngestion(
        max_concurrent_downloads=8,
        max_concurrent_parses=4,
    )

    database = make_database()
    app.state.database = database
    logger.info("Database connected")
    
    configure_logfire(settings)
    if settings.logfire.enabled:
        logfire.instrument_system_metrics()
        logfire.instrument_fastapi(app, request_attributes_mapper=_skip_health)

    # Initialize search service
    opensearch_client = make_opensearch_client()
    app.state.opensearch_client = opensearch_client

    if opensearch_client.health_check():
        logger.info("OpenSearch connected successfully")

        setup_results = opensearch_client.setup_indices(force=False)
        if setup_results.get("hybrid_index"):
            logger.info("Hybrid index created")
        else:
            logger.info("Hybrid index already exists")

        try:
            stats = opensearch_client.client.count(index=opensearch_client.index_name)
            logger.info(f"OpenSearch ready: {stats['count']} documents indexed")
        except Exception:
            logger.info("OpenSearch index ready (stats unavailable)")
    else:
        logger.warning("OpenSearch connection failed - search features will be limited")

    
    agentic_rag_service = make_agentic_rag_service(
            opensearch_client=app.state.opensearch_client,
            llm_client=app.state.llm_client,
            embeddings_client=app.state.embedding_client,
            langfuse_tracer=app.state.langfuse_client ,
            guardrails_service=app.state.guardrails_client,
        )
    app.state.agentic_rag_service = agentic_rag_service

    yield
    await app.state.cache_client.close() # your CacheClient.close() -> self.redis.close()
    await app.state.redis.close() # ARQ pool
    database.teardown()
    logger.info("API shutdown complete")


def _skip_health(request, attributes):
    return {} if request.url.path == "/api/v1/health" else attributes



import os
app = FastAPI(
    title="arXiv Paper Curator API",
    description="Personal arXiv CS.AI paper curator with RAG capabilities",
    version=os.getenv("APP_VERSION", "0.1.0"),
    lifespan=lifespan,
)
app.include_router(ingestionrouter)
app.include_router(router)
app.include_router(arxivrouter)

def _is_ok(v):
    if isinstance(v, dict):
        return v.get("status") == "ok"
    return v == "ok"

@app.get("/api/v1/health")
async def health(request: Request):
    checks = {}

    # LLM Check
    try:
        llm_health = await request.app.state.llm_client.health_check()

        checks["llm_client"] = {
            "status": "ok" if llm_health["healthy"] else "unhealthy",
            "healthy_models": llm_health["healthy_models"],
            "total_models": llm_health["total_models"],
        }
    except Exception as e:
        checks["llm_client"] = {"status": "error", "error": str(e)}
    
    # OpenSearch
    try:
        checks["opensearch"] = "ok" if request.app.state.opensearch_client.health_check() else "unhealthy"
    except Exception as e:
        checks["opensearch"] = f"error: {e}"

    # Redis (ARQ pool)
    try:
        await request.app.state.redis.ping()
        checks["redis"] = "ok"
    except Exception as e:
        checks["redis"] = f"error: {e}"

    # Redis (Cache)
    try:
        await request.app.state.cache_client.redis.ping()
        checks["redis_cache"] = "ok"
    except Exception as e:
        checks["redis_cache"] = f"error: {e}"
        
    # Database
    try:
        request.app.state.database.health_check()  # adjust to your DB client's actual method
        checks["database"] = "ok"
    except Exception as e:
        checks["database"] = f"error: {e}"

    # Embedding
    try:
        request.app.state.embedding_client.health_check_all()
        checks["embedding"] = "ok"
    except Exception as e:
        checks["embedding"] = f"error: {e}"

    healthy = all(_is_ok(v) for v in checks.values())
    status_code = 200 if healthy else 503
    return JSONResponse(
        status_code=status_code,
        content={"status": "ok" if healthy else "degraded", "checks": checks},
    )

# uvicorn src.main:app --reload