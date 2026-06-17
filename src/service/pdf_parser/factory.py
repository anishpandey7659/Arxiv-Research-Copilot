from .client import ArxivClient
from src.config import get_settings

def make_arxiv_client() -> ArxivClient:
    """Factory function to create an instance of ArxivClient with the appropriate settings.
    Returns:
        An instance of ArxivClient configured with settings from the environment.
    """
    # Get settings from centralized config
    settings = get_settings()
    # Create arXiv client with explicit settings
    return ArxivClient(settings.arxiv)
