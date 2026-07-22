from datetime import datetime
from typing import List, Optional
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session, load_only

from src.models.paper import Paper
from src.schemas.arxiv.paper import PaperCreate


# Columns needed for list/summary views. Deliberately excludes the large
# parsed-content columns (raw_text, sections, references, parser_metadata)
# so list endpoints don't pay to fetch + deserialize full paper bodies.
LIST_VIEW_COLUMNS = (
    Paper.id,
    Paper.arxiv_id,
    Paper.title,
    Paper.authors,
    Paper.abstract,
    Paper.categories,
    Paper.published_date,
    Paper.pdf_url,
    Paper.pdf_processed,
    Paper.pdf_processing_date,
    Paper.created_at,
    Paper.updated_at,
)


class PaperRepository:
    def __init__(self, session: Session):
        self.session = session

    def create(self, paper: PaperCreate) -> Paper:
        db_paper = Paper(**paper.model_dump())
        self.session.add(db_paper)
        self.session.commit()
        self.session.refresh(db_paper)
        return db_paper

    def create_many(self, papers: list[PaperCreate]) -> list[Paper]:
        db_objects = [Paper(**paper.model_dump()) for paper in papers]
        self.session.add_all(db_objects)
        self.session.commit()
        return db_objects

    def get_by_arxiv_id(self, arxiv_id: str) -> Optional[Paper]:
        """Full row, including raw_text/sections/references — detail view."""
        stmt = select(Paper).where(Paper.arxiv_id == arxiv_id)
        return self.session.scalar(stmt)

    def get_by_id(self, paper_id: UUID) -> Optional[Paper]:
        """Full row, including raw_text/sections/references — detail view."""
        stmt = select(Paper).where(Paper.id == paper_id)
        return self.session.scalar(stmt)

    def get_all(self, limit: int = 100, offset: int = 0) -> List[Paper]:
        """Lightweight list view — excludes large parsed-content columns."""
        stmt = (
            select(Paper)
            .options(load_only(*LIST_VIEW_COLUMNS))
            .order_by(Paper.published_date.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(self.session.scalars(stmt))

    def get_count(self) -> int:
        stmt = select(func.count(Paper.id))
        return self.session.scalar(stmt) or 0

    def get_processed_papers(self, limit: int = 100, offset: int = 0) -> List[Paper]:
        """Papers with successfully processed PDF content — lightweight list view."""
        stmt = (
            select(Paper)
            .options(load_only(*LIST_VIEW_COLUMNS))
            .where(Paper.pdf_processed == True)
            .order_by(Paper.pdf_processing_date.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(self.session.scalars(stmt))

    def get_unprocessed_papers(self, limit: int = 100, offset: int = 0) -> List[Paper]:
        """Papers not yet processed for PDF content — lightweight list view."""
        stmt = (
            select(Paper)
            .options(load_only(*LIST_VIEW_COLUMNS))
            .where(Paper.pdf_processed == False)
            .order_by(Paper.published_date.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(self.session.scalars(stmt))

    def get_papers_with_raw_text(self, limit: int = 100, offset: int = 0) -> List[Paper]:
        """Papers that have raw text stored. Caller wants raw_text, so it's
        deliberately NOT excluded here — this is the one list method that
        needs the large column."""
        stmt = (
            select(Paper)
            .where(Paper.raw_text != None)
            .order_by(Paper.pdf_processing_date.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(self.session.scalars(stmt))

    def get_processing_stats(self) -> dict:
        """Get statistics about PDF processing status."""
        total_papers = self.get_count()

        processed_stmt = select(func.count(Paper.id)).where(Paper.pdf_processed == True)
        processed_papers = self.session.scalar(processed_stmt) or 0

        text_stmt = select(func.count(Paper.id)).where(Paper.raw_text != None)
        papers_with_text = self.session.scalar(text_stmt) or 0

        return {
            "total_papers": total_papers,
            "processed_papers": processed_papers,
            "papers_with_text": papers_with_text,
            "processing_rate": (processed_papers / total_papers * 100) if total_papers > 0 else 0,
            "text_extraction_rate": (papers_with_text / processed_papers * 100) if processed_papers > 0 else 0,
        }

    def update(self, paper: Paper) -> Paper:
        self.session.add(paper)
        self.session.commit()
        self.session.refresh(paper)
        return paper

    def upsert(self, paper_create: PaperCreate) -> Paper:
        existing_paper = self.get_by_arxiv_id(paper_create.arxiv_id)
        if existing_paper:
            for key, value in paper_create.model_dump(exclude_unset=True).items():
                setattr(existing_paper, key, value)
            return self.update(existing_paper)
        else:
            return self.create(paper_create)