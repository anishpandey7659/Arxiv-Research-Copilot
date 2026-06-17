from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field

class ArxivPaper(BaseModel):
    arxiv_id:str=Field(..., description="ArXiv ID of the paper, e.g., '2101.00001'")
    title:str=Field(..., description="Title of the paper")
    abstract:str=Field(..., description="Abstract of the paper")
    authors:List[str]=Field(..., description="List of authors of the paper")
    published_date:datetime=Field(..., description="Publication date of the paper")
    categories:List[str]=Field(..., description="List of categories for the paper")
    pdf_url:str=Field(..., description="URL of the PDF version of the paper")