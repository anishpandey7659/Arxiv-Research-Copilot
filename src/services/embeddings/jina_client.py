import logging
from typing import List, Optional
from src.schemas.litellm.models import EmbeddingModelConfig,EMBEDDING_PROVIDERS
from openai import AsyncOpenAI

logger = logging.getLogger(__name__)


class EmbeddingsClient:
    """Multi-provider embeddings client with automatic fallback (Cohere/Jina/Voyage via LiteLLM)."""

    def __init__(self, providers: list[EmbeddingModelConfig] = EMBEDDING_PROVIDERS):
        self.providers = providers
        # one AsyncOpenAI client is enough since api_base/key are shared via the proxy
        self.client = AsyncOpenAI(
            api_key=providers[0].api_key_env,
            base_url=providers[0].api_base,
        )
        logger.info(f"Embeddings client initialized (providers={[p.name for p in providers]})")


    def _extra_body(self, cfg: EmbeddingModelConfig, mode: str) -> dict:
        """Build provider-specific extra_body for passage/query mode."""
        value = cfg.passage_value if mode == "passage" else cfg.query_value
        return {"dimensions": cfg.dimensions, cfg.task_param_key: value, **cfg.extra_params}


    async def _embed_with_fallback(self, texts: List[str], mode: str) -> List[List[float]]:
        """Try each provider in order, return first success, raise if all fail."""
        last_err: Exception | None = None
        for cfg in self.providers:
            try:
                response = await self.client.embeddings.create(
                    model=cfg.name,
                    input=texts,
                    extra_body=self._extra_body(cfg, mode),
                    timeout=cfg.timeout,
                )
                return [item.embedding for item in response.data]
            except Exception as e:
                last_err = e
                logger.warning(f"[{cfg.label}] embedding call failed: {e} — trying next provider")
                continue
        raise RuntimeError(f"All embedding providers failed: {last_err}") from last_err

    async def embed_passages(self, texts: List[str], batch_size: int = 100) -> List[List[float]]:
        """Embed documents for indexing, batched, with provider fallback."""
        embeddings: List[List[float]] = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            embeddings.extend(await self._embed_with_fallback(batch, mode="passage"))
        return embeddings

    async def embed_query(self, query: str) -> List[float]:
        """Embed a search query for vector similarity lookup."""
        return (await self._embed_with_fallback([query], mode="query"))[0]

    async def health_check(self) -> bool:
        """Quick check: True if at least one provider is reachable and working."""
        try:
            embedding = await self.embed_query("health check")
            healthy = len(embedding) > 0
            if healthy:
                logger.debug("Embeddings health check passed")
            else:
                logger.warning("Embeddings health check failed: empty response")
            return healthy
        except Exception as e:
            logger.error(f"Embeddings health check failed: {e}")
            return False

    async def health_check_all(self) -> dict[str, bool]:
        """Per-provider check: probes each provider directly (no fallback),
        so you know exactly which ones are up vs. down.

        Useful for monitoring dashboards/alerting — health_check() alone
        can't tell you if provider #1 is down but #2 is silently covering for it.
        """
        results: dict[str, bool] = {}

        for cfg in self.providers:
            try:
                response = await self.client.embeddings.create(
                    model=cfg.name,
                    input=["health check"],
                    extra_body=self._extra_body(cfg, mode="query"),
                    timeout=cfg.timeout,
                )
                ok = bool(response.data and len(response.data[0].embedding) > 0)
                results[cfg.name] = ok
                if ok:
                    logger.debug(f"[{cfg.label}] health check passed")
                else:
                    logger.warning(f"[{cfg.label}] health check failed: empty response")

            except Exception as e:
                results[cfg.name] = False
                logger.error(f"[{cfg.label}] health check failed: {e}")

        return results