from typing import Optional
from src.config import Settings, get_settings
from src.services.arxiv.factory import make_arxiv_client
from src.services.indexing.factory import make_hybrid_indexing_service
from src.db.factory import make_database
from .client import PaperIngestionPipeline
from src.services.pdf_parser.factory import make_pdf_parser_service


def get_paperIngestion(max_concurrent_downloads: int = 8,max_concurrent_parses: int = 4,
                       settings:Optional[Settings] = None,
                       opensearch_host: Optional[str] = None)->PaperIngestionPipeline:

    """Create and configure a PaperIngestionPipeline instance.

    Initializes all required dependencies, including the ArXiv client,
    PDF parser, database client, and hybrid indexing service.

    :param max_concurrent_downloads: Maximum number of PDFs that can be
        downloaded concurrently.
    :param max_concurrent_parses: Maximum number of PDFs that can be
        parsed concurrently.
    :param settings: Optional application settings.
    :param opensearch_host: Optional OpenSearch host used by the indexing
        service.
    :returns: A configured PaperIngestionPipeline instance.
    """
    if settings is None:
        settings = get_settings()

    arxiv_client =  make_arxiv_client()
    pdf_parser_service =  make_pdf_parser_service()
    db_client =  make_database()
    indexing_client =  make_hybrid_indexing_service(opensearch_host=settings.opensearch.host)
    
    return PaperIngestionPipeline(arxiv_client,pdf_parser_service,
                                  db_client,indexing_client,
                                  max_concurrent_downloads,max_concurrent_parses)