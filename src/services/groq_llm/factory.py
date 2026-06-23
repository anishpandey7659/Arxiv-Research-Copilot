from functools import lru_cache

from src.config import get_settings
from src.services.groq_llm.client import GroqLLMClient


@lru_cache(maxsize=1)
def make_groq_llm_client() -> GroqLLMClient:
    """Create and return a singleton OpenAI LLM client."""
    settings = get_settings()
    return GroqLLMClient(settings)