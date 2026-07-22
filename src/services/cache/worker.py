# worker.py
from __future__ import annotations

import logfire
from arq.connections import RedisSettings
from src.config import get_settings
from src.services.paperIngestion.factory import get_paperIngestion
from src.services.paperIngestion.client import PaperIngestionPipeline

settings = get_settings()

async def startup(ctx: dict) -> None:
    logfire.configure()
    ctx["pipeline"] = get_paperIngestion(
        max_concurrent_downloads=8,
        max_concurrent_parses=4,
    )


async def shutdown(ctx: dict) -> None:
    pipeline = ctx.get("pipeline")
    if pipeline is not None:
        await pipeline.close()


async def pdf_process_pipeline(ctx: dict,arxiv_id: str) -> dict:
    """
    ARQ task entrypoint. Fetches paper metadata from the arxiv API,
    then runs the full download -> parse -> store -> index pipeline.
    """
    pipeline: PaperIngestionPipeline = ctx["pipeline"]
    paper = await pipeline.fetch_paper(arxiv_id)

    if paper is None:
        return {"arxiv_id": arxiv_id, "error": "paper not found on arxiv"}

    result = await pipeline.run([paper])

    return {
        "arxiv_id": arxiv_id,
        "processed": len(result.processed),
        "stored": len(result.stored),
        "indexed": result.indexed_stats,
        "errors": [e.__dict__ for e in result.errors],
    }


class WorkerSettings:
    functions = [pdf_process_pipeline]
    on_startup = startup
    on_shutdown = shutdown
    redis_settings =  RedisSettings(
                host= settings.redis.host,
                port=settings.redis.port,
                username=settings.redis.username,
                password=settings.redis.password,
                ssl=settings.redis.ssl)
    max_jobs = 8
    job_timeout = 600