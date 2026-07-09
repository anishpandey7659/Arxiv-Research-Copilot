from typing import Optional

from src.config import Settings, get_settings

from .jina_client import EmbeddingsClient


def make_embeddings_service(settings: Optional[Settings] = None) -> EmbeddingsClient:
    """Factory function to create embeddings service.

    Creates a new client instance each time to avoid closed client issues.

    :param settings: Optional settings instance
    :returns: JinaEmbeddingsClient instance
    """
    if settings is None:
        settings = get_settings()

    # Get API key from settings
    api_key = settings.litellm.master_key
    base_url = settings.litellm.api_base


    return EmbeddingsClient(api_key=api_key,api_base=base_url)