from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Optional

from langfuse._client.span import LangfuseSpan
from src.services.guardrails.Input_guardrails.client import InputGuardrails
from src.services.embeddings.jina_client import EmbeddingsClient
from src.services.langfuse.client import LangfuseTracer
from src.services.LLM_gateway.client import LLMClient
from src.services.opensearch.client import OpenSearchClient


@dataclass
class Context:
    """Runtime context for agent dependencies.

    This contains immutable dependencies that nodes need but don't modify.

    :param llm_client: LLM client (OpenAI or Bedrock — satisfies LLMClientProtocol)
    :param opensearch_client: Client for document search
    :param embeddings_client: Client for embeddings
    :param langfuse_tracer: Optional tracer for observability
    :param guardrails_service: Optional Bedrock Guardrails service
    :param trace: Current Langfuse trace object (if enabled)
    :param langfuse_enabled: Whether Langfuse tracing is enabled
    :param model_name: Model to use for LLM calls
    :param temperature: Temperature for generation
    :param top_k: Number of documents to retrieve
    :param max_retrieval_attempts: Maximum retrieval attempts
    :param guardrail_threshold: Threshold for guardrail validation (0-100)
    """

    llm_client: LLMClient
    opensearch_client: OpenSearchClient
    embeddings_client: EmbeddingsClient
    langfuse_tracer: Optional[LangfuseTracer]
    guardrails_service: Optional[InputGuardrails] = None
    trace: Optional["LangfuseSpan"] = None
    langfuse_enabled: bool = False
    model_name: str = "gpt-4o-mini"
    temperature: float = 0.0
    top_k: int = 3
    max_retrieval_attempts: int = 2
