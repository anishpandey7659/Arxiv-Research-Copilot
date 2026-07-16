
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from pathlib import Path
from typing import Any,Dict
import logfire
from src.repositories.paper import PaperRepository
from src.schemas.arxiv.paper import ArxivPaper, PaperCreate
from src.services.arxiv.client import ArxivClient
from src.services.pdf_parser.parser import PDFParserService
from src.services.indexing.hybrid_indexer import HybridIndexingService
from src.db.interfaces.base import BaseDatabase
from src.schemas.paperIngestion.model import PaperProcessingError,PipelineResult

class PaperIngestionPipeline:
    """
    Downloads arxiv papers, parses their PDFs, persists the structured
    result to Postgres, and indexes them into the hybrid/vector search
    store.

    All external dependencies (arxiv client, pdf parser, db client,
    indexing client) are injectable so the pipeline can be unit-tested
    with fakes/mocks; if omitted, sensible defaults are built from the
    project's factories.

    Every stage emits a Logfire span so timings, arguments, and failures
    show up in the Logfire dashboard/trace view without manual
    stopwatch code or print statements. Call `logfire.configure()` once
    at process startup (e.g. in your app entrypoint) before using this
    class; the pipeline itself only calls `logfire.span` / log methods.
    """

    REFERENCES_TITLE = "REFERENCES"
    PARSER_NAME = "DOCLING"

    def __init__(
        self,
        arxiv_client: ArxivClient ,
        pdf_parser_service:PDFParserService ,
        db_client: BaseDatabase,
        indexing_client: HybridIndexingService,
        max_concurrent_downloads: int ,
        max_concurrent_parses: int,
    ) -> None:
        self._arxiv_client = arxiv_client 
        self._pdf_parser_service = pdf_parser_service 
        self._db_client = db_client 
        self._indexing_client = indexing_client 

        # Bound concurrency so a large batch doesn't hammer the network
        # or spawn unbounded parser threads.
        self._download_semaphore = asyncio.Semaphore(max_concurrent_downloads)
        self._parse_semaphore = asyncio.Semaphore(max_concurrent_parses)

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    async def run(self, papers: list[ArxivPaper]) -> PipelineResult:
        """Run the full pipeline: process -> store -> index."""
        result = PipelineResult(timings={"requested": len(papers)})

        with logfire.span(
            "paper_ingestion_pipeline.run", paper_count=len(papers)
        ) as run_span:
            if not papers:
                logfire.info("No papers supplied, nothing to do.")
                return result

            result.processed, result.errors = await self.process_papers(papers)


            if result.processed:
                with logfire.span(
                    "pipeline.store", paper_count=len(result.processed)
                ) as span:
                    result.stored = self.store_papers(result.processed)
                    span.set_attribute("stored_count", len(result.stored))

                with logfire.span(
                    "pipeline.index", paper_count=len(result.stored)
                ) as span:
                    result.indexed_stats = await self.index_papers(result.stored)
                    span.set_attribute("indexed_count", result.indexed_stats)
            else:
                logfire.warn(
                    "No papers were successfully processed; skipping store/index."
                )

            run_span.set_attributes(
                {
                    "processed_count": len(result.processed),
                    "stored_count": len(result.stored),
                    "indexed_count": result.indexed_stats,
                    "error_count": len(result.errors),
                }
            )
        logfire.info(f"Pipeline finished\n{result.summary()}")
        return result

    async def process_papers(
        self, papers: list[ArxivPaper]
    ) -> tuple[list[PaperCreate], list[PaperProcessingError]]:
        """Download + parse a batch of papers concurrently, tolerating per-paper failures."""
        with logfire.span(
            "pipeline.process_papers", paper_count=len(papers)
        ) as span:
            tasks = [self._process_paper_safe(paper) for paper in papers]
            outcomes = await asyncio.gather(*tasks)

            processed = [p for p in outcomes if isinstance(p, PaperCreate)]
            errors = [e for e in outcomes if isinstance(e, PaperProcessingError)]

            span.set_attributes(
                {
                    "succeeded": len(processed),
                    "failed": len(errors),
                }
            )
            logfire.info(
                "Processed papers",
                succeeded=len(processed),
                failed=len(errors),
                total=len(papers),
            )
            return processed, errors

    def store_papers(self, processed_papers: list[PaperCreate]) -> list[Any]:
        """Persist processed papers to Postgres."""
        with logfire.span(
            "pipeline.store_papers", paper_count=len(processed_papers)
        ):
            with self._db_client.get_session() as session:
                repo = PaperRepository(session)
                stored = repo.create_many(processed_papers)
            logfire.info("Stored papers in Postgres", stored_count=len(stored))
            return stored

    async def index_papers(self, stored_papers: list[Any]) -> Dict[str, int]:
        """Index stored papers into the hybrid/vector search store."""
        if not stored_papers:
            return {"error":0}
        with logfire.span(
            "pipeline.index_papers", paper_count=len(stored_papers)
        ):
            total_stats = await self._indexing_client.index_papers_batch(
                stored_papers
            )
            logfire.info("Indexed stats", indexed_count=total_stats)
            return total_stats
    
    async def fetch_paper(self, arxiv_id: str) -> ArxivPaper | None:
        """Retrieve a paper from arXiv for ingestion into the pipeline.

        :param arxiv_id: arXiv identifier of the paper.
        :returns: The retrieved ``ArxivPaper`` if the paper exists; otherwise ``None``.
        """
        with logfire.span("pipeline.fetch_paper", arxiv_id=arxiv_id):
            return await self._arxiv_client.fetch_paper_by_id(arxiv_id=arxiv_id)

    
    # ------------------------------------------------------------------ #
    # Internals
    # ------------------------------------------------------------------ #

    async def _process_paper_safe(
        self, paper: ArxivPaper
    ) -> PaperCreate | PaperProcessingError:
        """Wraps process_paper so one bad paper doesn't sink asyncio.gather."""
        try:
            return await self._process_paper(paper)
        except Exception as exc:  # noqa: BLE001 - intentional broad catch at boundary
            logfire.exception(
                "Failed to process paper", arxiv_id=paper.arxiv_id
            )
            return PaperProcessingError(
                arxiv_id=paper.arxiv_id, stage="process", error=str(exc)
            )

    async def _process_paper(self, paper: ArxivPaper) -> PaperCreate:
        with logfire.span(
            "pipeline.process_paper", arxiv_id=paper.arxiv_id
        ):
            pdf_path = await self._download(paper)
            parsed_pdf = await self._parse(paper, pdf_path)
            sections, references = self._split_sections(parsed_pdf.sections)

            paper_create = PaperCreate(
                **paper.model_dump(),
                raw_text=parsed_pdf.raw_text,
                sections=sections,
                references=references,
                parser_used=self.PARSER_NAME,
                parser_metadata=getattr(parsed_pdf, "metadata", None),
                pdf_processed=True,
                pdf_processing_date=datetime.now(timezone.utc),
            )
            return paper_create

    async def _download(self, paper: ArxivPaper) -> Path:
        with logfire.span("pipeline.download", arxiv_id=paper.arxiv_id):
            async with self._download_semaphore:
                pdf_path = await self._arxiv_client.download_pdf(paper)
            return Path(pdf_path)

    async def _parse(self, paper: ArxivPaper, pdf_path: Path):
        with logfire.span("pipeline.parse", arxiv_id=paper.arxiv_id):
            async with self._parse_semaphore:
                parsed_pdf = await asyncio.to_thread(
                    self._pdf_parser_service.parse_pdf, pdf_path
                )
            return parsed_pdf

    def _split_sections(
        self, raw_sections: list[Any]
    ) -> tuple[list[dict], list[dict] | None]:
        """Extracts title/content pairs and pulls a trailing REFERENCES section out."""
        sections = [
            section.model_dump(include={"title", "content"})
            for section in raw_sections
        ]

        references: list[dict] | None = None
        if sections and sections[-1]["title"].strip().upper() == self.REFERENCES_TITLE:
            references = [sections.pop()]

        return sections, references

