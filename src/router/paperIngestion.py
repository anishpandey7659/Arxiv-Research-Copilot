# src/api/paper_ingestion.py
from src.dependencies import get_redis, get_paper_ingestion_pipeline
from src.services.paperIngestion.client import PaperIngestionPipeline
from arq.connections import ArqRedis
from fastapi import APIRouter, HTTPException,Depends
from src.schemas.api.ingestion import IngestResponse


ingestionrouter = APIRouter(prefix="/api/v1", tags=["ingest-rag"])



@ingestionrouter.post("/{arxiv_id}/ingest", response_model=IngestResponse, status_code=202)
async def ingest_paper(
    arxiv_id: str,
    redis: ArqRedis = Depends(get_redis),
    pipeline: PaperIngestionPipeline = Depends(get_paper_ingestion_pipeline),
) -> IngestResponse:
    paper = await pipeline.fetch_paper(arxiv_id)
    if paper is None:
        raise HTTPException(status_code=404, detail=f"Paper {arxiv_id} not found on arxiv.")

    job_id = f"pdf_process:{arxiv_id}"
    job = await redis.enqueue_job("pdf_process_pipeline", arxiv_id, _job_id=job_id)

    if job is None:
        return IngestResponse(
            message="Paper is already queued or being processed.",
            arxiv_id=arxiv_id,
            job_id=job_id,
            already_queued=True,
        )

    return IngestResponse(
        message="Paper queued successfully.",
        arxiv_id=arxiv_id,
        job_id=job.job_id,
        already_queued=False,
    )