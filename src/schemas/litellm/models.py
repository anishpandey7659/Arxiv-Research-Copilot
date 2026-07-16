from typing import Any
from dataclasses import dataclass, field
from src.config import get_settings

settings = get_settings()

@dataclass(frozen=True)
class ModelConfig:
    name: str
    provider_model: str
    label: str
    api_base: str =settings.litellm.api_base
    api_key_env: str =settings.litellm.virtual_key
    timeout: float =settings.litellm.timeout
    extra_params: dict[str, Any] = field(default_factory=dict)

@dataclass(frozen=True)
class EmbeddingModelConfig(ModelConfig):
    """Extends ModelConfig with embedding-specific fields."""
    dimensions: int = 1024
    task_param_key: str = "input_type"     # "input_type" for Cohere/Voyage, "task" for Jina
    passage_value: str = "search_document"  # provider-specific value for indexing mode
    query_value: str = "search_query"       # provider-specific value for query mode


# --- Provider configs, reusing your existing pattern ---
EMBEDDING_PROVIDERS: list[EmbeddingModelConfig] = [
    
    EmbeddingModelConfig(
        name="jina-embed",
        provider_model="jina_ai/jina-embeddings-v3",
        label="Jina Embeddings v3",
        dimensions=1024,
        task_param_key="task",
        passage_value="retrieval.passage",
        query_value="retrieval.query",
    ),
    EmbeddingModelConfig(
        name="cohere-embed",
        provider_model="cohere/embed-v4.0",
        label="Cohere Embed v4",
        dimensions=1024,
        task_param_key="input_type",
        passage_value="search_document",
        query_value="search_query",
    ),
    EmbeddingModelConfig(
        name="voyage-embed",
        provider_model="voyage/voyage-3.5",
        label="Voyage 3.5",
        dimensions=1024,
        task_param_key="input_type",
        passage_value="document",
        query_value="query",
    ),
]
