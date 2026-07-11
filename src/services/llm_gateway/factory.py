from functools import lru_cache

from src.config import get_settings
from src.services.llm_gateway.client import LLMClient


@lru_cache(maxsize=1)
def make_groq_llm_client() -> LLMClient:
    """Create and return a singleton Groq LLM client."""
    settings = get_settings()
    return LLMClient(settings)