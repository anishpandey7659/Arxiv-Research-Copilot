from .parser import PDFParserService
from src.config import get_settings

def make_pdf_parser_service()->PDFParserService:
    """Create cached PDF parser service using Docling."""
    settings=get_settings()
    max_pages=settings.pdf_parser.max_pages
    max_file_size_mb=settings.pdf_parser.max_file_size_mb
    do_ocr=settings.pdf_parser.do_ocr
    do_table_structure=settings.pdf_parser.do_table_structure
    return PDFParserService(max_pages=max_pages,max_file_size_mb=max_file_size_mb,do_ocr=do_ocr,do_table_structure=do_table_structure)