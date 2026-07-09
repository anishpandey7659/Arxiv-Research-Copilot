import logging
from typing import List, Optional

from openai import AsyncOpenAI

logger = logging.getLogger(__name__)


class EmbeddingsClient:
    """Client for Jina AI embeddings via LiteLLM proxy server (OpenAI-compatible endpoint)."""

    def __init__(
        self,
        api_key: str,
        api_base: str = "http://localhost:4000",
        model: str = "jina-embed",
        dimensions: int = 1024,
    ):
        self.model = model
        self.dimensions = dimensions
        self.client = AsyncOpenAI(api_key=api_key, base_url=api_base)
        logger.info(f"Jina embeddings client initialized (model={model}, api_base={api_base})")

    async def embed_passages(self, texts: List[str], batch_size: int = 100) -> List[List[float]]:
        embeddings: List[List[float]] = []

        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]

            try:
                response = await self.client.embeddings.create(
                    model=self.model,
                    input=batch,
                    extra_body={
                        "dimensions": self.dimensions,
                        "task": "retrieval.passage",
                    },
                )

                batch_embeddings = [item.embedding for item in response.data]
                embeddings.extend(batch_embeddings)

                logger.debug(f"Embedded batch of {len(batch)} passages")

            except Exception as e:
                logger.error(f"Error embedding passages: {e}")
                raise

        logger.info(f"Successfully embedded {len(texts)} passages")
        return embeddings

    async def embed_query(self, query: str) -> List[float]:
        try:
            response = await self.client.embeddings.create(
                model=self.model,
                input=[query],
                extra_body={
                    "dimensions": self.dimensions,
                    "task": "retrieval.query",
                },
            )

            embedding = response.data[0].embedding
            logger.debug(f"Embedded query: '{query[:50]}...'")
            return embedding

        except Exception as e:
            logger.error(f"Error embedding query: {e}")
            raise

    async def health_check(self) -> bool:
        """Check whether the embeddings service is reachable and functioning.

        Performs a minimal embedding call to verify both the LiteLLM proxy
        and the upstream provider (Jina) are working end-to-end.

        :returns: True if healthy, False otherwise
        """
        try:
            response = await self.client.embeddings.create(
                model=self.model,
                input=["health check"],
                extra_body={
                    "dimensions": self.dimensions,
                    "task": "retrieval.query",
                },
            )

            if response.data and len(response.data[0].embedding) > 0:
                logger.debug("Embeddings health check passed")
                return True

            logger.warning("Embeddings health check failed: empty response")
            return False

        except Exception as e:
            logger.error(f"Embeddings health check failed: {e}")
            return False