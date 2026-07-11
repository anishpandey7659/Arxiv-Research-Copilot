from src.schemas.api.ask import PaperSearchRequest
from src.schemas.arxiv.paper import ArxivPaper
from fastapi import APIRouter, HTTPException,Query
from src.dependencies import  ArxivDep


arxivrouter = APIRouter(prefix="/api/v1", tags=["agentic-rag"])


@arxivrouter.post("/papers/search", response_model=list[ArxivPaper])
async def search_papers(request:PaperSearchRequest,arxiv_client:ArxivDep):
    """
    Fetch papers from arXiv matching a search query.
    """
    try:
        papers = await arxiv_client.fetch_papers_with_query(
            search_query=request.search_query,
            max_results=request.max_results,
            start=request.start,
            sort_by=request.sort_by,
            sort_order=request.sort_order,
        )
        return papers
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch papers: {str(e)}")
