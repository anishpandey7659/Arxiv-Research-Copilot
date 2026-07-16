# src/schemas/paperIngestion/api.py  (or wherever your API schemas live)
from pydantic import BaseModel, Field


class IngestResponse(BaseModel):
    """Response returned immediately after queuing (or attempting to queue) a paper."""

    message: str = Field(
        ...,
        description="Human-readable status message.",
        examples=["Paper queued successfully.", "Paper is already queued or being processed."],
    )
    arxiv_id: str = Field(..., description="The arxiv id that was requested for ingestion.")
    job_id: str | None = Field(
        None,
        description="ARQ job id, usable to poll /papers/jobs/{job_id} for status.",
    )
    already_queued: bool = Field(
        False,
        description="True if this arxiv_id was already queued/processing and no new job was created.",
    )