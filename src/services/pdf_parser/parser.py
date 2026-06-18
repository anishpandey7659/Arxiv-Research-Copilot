import logging
from pathlib import Path
from typing import Optional

from src.exceptions import PDFParsingException, PDFValidationError
from src.schemas.pdf_parser.models import PdfContent

from .docling import DoclingParser

logger = logging.getLogger(__name__)

class PDFParserService:
    """Main PDF parsing service using Docling only."""

    def __init__(self,max_pages:int,max_file_size_mb:int,do_ocr: bool = False,do_table_structure: bool = True):
        self._docling_parser=DoclingParser(max_pages,max_file_size_mb,do_ocr,do_table_structure)

    def parse_pdf(self,pdf_path:Path):
        """->Optional[PdfContent]"""
        if not pdf_path.exists():
            logger.error(f"PDF Doesnot Exits in that path: {pdf_path}")
            raise PDFValidationError(f"PDF Doesnot Exits in that path: {pdf_path}")
        try:
            result=self._docling_parser.parse_pdf(pdf_path)
            if result:
                logger.info(f"Parsed for {pdf_path}")
                return result
            else:
                logger.error(f"Docling parsing returned no result for {pdf_path.name}")
                raise PDFParsingException(f"Docling parsing returned no result for {pdf_path.name}")
        except (PDFValidationError,PDFParsingException):
            raise
        except Exception as  e:
            logger.error(f"Docling parsing error for : {pdf_path} , ERROR CAUSE:{e}")
            raise PDFValidationError(f"Docling parsing error for : {pdf_path} , ERROR CAUSE:{e}")
