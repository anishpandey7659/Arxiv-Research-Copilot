from typing import Optional

from src.config import Settings, get_settings
from src.schemas.litellm.models import EmbeddingModelConfig,EMBEDDING_PROVIDERS
from .jina_client import EmbeddingsClient



def make_embeddings_service(
    settings: Optional[Settings] = None,
    providers: Optional[list[EmbeddingModelConfig]] = None,
) -> EmbeddingsClient:
    """Factory function to create an embeddings service.

    Creates a new client instance each time to avoid closed client issues.

    :param settings: Optional settings instance. Falls back to global settings
        if not provided.
    :param providers: Optional override for the provider list (primary +
        fallbacks). Defaults to ``EMBEDDING_PROVIDERS``.
    :returns: EmbeddingsClient instance
    """
    if settings is None:
        settings = get_settings()

    if providers is None:
        providers = EMBEDDING_PROVIDERS

    return EmbeddingsClient(providers=providers)