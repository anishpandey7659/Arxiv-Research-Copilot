from fastapi import FastAPI
from src.route.Agenticask import router

import logfire
from src.config import get_settings
from src.services.arxiv.factory import make_arxiv_client
from src.services.embeddings.factory import make_embeddings_service
from src.services.guardrails.Input_guardrails.factory import make_Input_guardrails
from src.services.indexing.factory import make_hybrid_indexing_service
from src.services.pdf_parser.factory import make_pdf_parser_service
from src.services.langfuse.factory import make_langfuse_tracer
from src.services.LLM_gateway.factory import make_groq_llm_client
from src.services.Logfire.factory import configure_logfire
from src.services.opensearch.factory import make_opensearch_client
from src.services.agents.factory import make_agentic_rag_service
from src.db.factory import make_database

from contextlib import asynccontextmanager
import logging
# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

import logfire
logfire.configure()
logfire.instrument_system_metrics()

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
    app.state.llm_client        = make_groq_llm_client()
    

    database = make_database()
    app.state.database = database
    logger.info("Database connected")
    
    configure_logfire(settings)
    if settings.logfire.enabled:
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

app.include_router(router)

@app.get("/health")
def health():
    return {'status':"ok"}


# uvicorn src.main:app --reload