import logging
from typing import Any, Dict, List, Optional
import groq
from groq import Groq
from groq import AsyncGroq
from src.config import Settings
from src.exceptions import GroqConnectionError, GroqLLMException, GroqTimeoutError
from src.services.groq_llm.prompts.prompt import RAGPromptBuilder,ResponseParser

logger = logging.getLogger(__name__)


class GroqLLMClient:
    """Client for OpenAI API — drop-in replacement for OllamaClient."""

    def __init__(self, settings: Settings):
        self.api_key = settings.groq_api_key
        self.timeout = settings.groq_timeout
        self.prompt_builder = RAGPromptBuilder()
        self.response_parser = ResponseParser()
        self._async_client: Optional[AsyncGroq] = None

    def _get_async_client(self) -> AsyncGroq:
        if self._async_client is None:
            self._async_client = AsyncGroq(
                api_key=self.api_key,
                timeout=float(self.timeout),
            )
        return self._async_client

    def get_langchain_model(self, model: str, temperature: float = 0.0):
        """Return a LangChain ChatOpenAI instance for use in agent nodes."""
        from langchain_groq import ChatGroq

        return ChatGroq(
            model=model,
            api_key=self.api_key,
            temperature=temperature,
        )

    async def health_check(self) -> Dict[str, Any]:
        """Check Groq API connectivity."""
        try:
            client = self._get_async_client()
            models = await client.models.list()
            return {
                "status": "healthy",
                "message": "Groq API is reachable",
                "model_count": len(list(models)),
            }
        except groq.AuthenticationError as e:
            raise GroqLLMException(f"Groq authentication failed — check GROQ_API_KEY: {e}")
        except groq.APITimeoutError as e:
            raise GroqTimeoutError(f"Groq API timed out: {e}")
        except groq.APIConnectionError as e:
            raise GroqConnectionError(f"Cannot reach Groq API: {e}")
        except groq.RateLimitError as e:
            raise GroqLLMException(f"Groq rate limit exceeded: {e}")
        except groq.APIStatusError as e:
            raise GroqLLMException(f"Groq API returned status {e.status_code}: {e}")
        except Exception as e:
            raise GroqLLMException(f"Groq health check failed: {e}")

    async def generate_rag_answer(
        self,
        query: str,
        chunks: List[Dict[str, Any]],
        model: Optional[str] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """Generate a RAG answer using retrieved chunks via OpenAI chat completions."""
        try:
            model = model or "openai/gpt-oss-120b"
            prompt = self.prompt_builder.create_rag_prompt(query, chunks)
            client = self._get_async_client()

            response = await client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a helpful research assistant. Answer questions based only "
                            "on the provided context from academic papers. Be concise and accurate."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.0,
            )

            answer = response.choices[0].message.content or ""

            sources = []
            seen_urls: set = set()
            for chunk in chunks:
                arxiv_id = chunk.get("arxiv_id")
                if arxiv_id:
                    arxiv_id_clean = arxiv_id.split("v")[0] if "v" in arxiv_id else arxiv_id
                    pdf_url = f"https://arxiv.org/pdf/{arxiv_id_clean}.pdf"
                    if pdf_url not in seen_urls:
                        sources.append(pdf_url)
                        seen_urls.add(pdf_url)

            citations = list(set(chunk.get("arxiv_id") for chunk in chunks if chunk.get("arxiv_id")))

            usage = response.usage
            return {
                "answer": answer,
                "sources": sources,
                "confidence": "high",
                "citations": citations[:5],
                "usage": {
                    "prompt_tokens": usage.prompt_tokens if usage else 0,
                    "completion_tokens": usage.completion_tokens if usage else 0,
                    "total_tokens": usage.total_tokens if usage else 0,
                },
            }

        except groq.AuthenticationError as e:
            raise GroqLLMException(f"Groq authentication failed — check GROQ_API_KEY: {e}")
        except groq.APITimeoutError as e:
            raise GroqTimeoutError(f"Groq API timed out: {e}")
        except groq.APIConnectionError as e:
            raise GroqConnectionError(f"Cannot reach Groq API: {e}")
        except groq.RateLimitError as e:
            raise GroqLLMException(f"Groq rate limit exceeded — try again shortly: {e}")
        except Exception as e:
            logger.error(f"Error generating RAG answer: {e}")
            raise GroqLLMException(f"Failed to generate RAG answer: {e}")

    async def generate_rag_answer_stream(
        self,
        query: str,
        chunks: List[Dict[str, Any]],
        model: Optional[str] = None,
    ):
        """Stream a RAG answer using OpenAI streaming chat completions."""
        try:
            model = model or "openai/gpt-oss-120b"
            prompt = self.prompt_builder.create_rag_prompt(query, chunks)
            client = self._get_async_client()

            stream = await client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a helpful research assistant. Answer questions based only "
                            "on the provided context from academic papers. Be concise and accurate."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.0,
                stream=True,
            )

            full_text = ""
            async for chunk in stream:
                delta = chunk.choices[0].delta
                if delta.content:
                    full_text += delta.content
                    yield {"response": delta.content, "done": False}

            yield {"response": "", "done": True, "full_response": full_text}

        except groq.AuthenticationError as e:
            raise GroqLLMException(f"Groq authentication failed: {e}")
        except groq.APITimeoutError as e:
            raise GroqTimeoutError(f"Groq API timed out: {e}")
        except groq.APIConnectionError as e:
            raise GroqConnectionError(f"Cannot reach Groq API: {e}")
        except Exception as e:
            logger.error(f"Error in streaming generation: {e}")
            raise GroqLLMException(f"Streaming generation failed: {e}")