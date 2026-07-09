import logging
from typing import Any, Dict, List, Optional
import groq
from groq import Groq
from pydantic import ValidationError,BaseModel
from groq import AsyncGroq
from src.config import Settings
from src.exceptions import GroqConnectionError, GroqLLMException, GroqTimeoutError
from src.services.LLM_gateway.prompts.prompt import RAGPromptBuilder,ResponseParser
from .route import build_router
from litellm import Router
logger = logging.getLogger(__name__)


class LLMClient:
    """Client for OpenAI API — drop-in replacement for OllamaClient."""

    def __init__(self, settings: Settings):
        self.api_key = settings.groq_api_key
        self.timeout = settings.groq_timeout
        self.prompt_builder = RAGPromptBuilder()
        self.llm: Optional[Router] = None 
        self.response_parser = ResponseParser()
        self._async_client: Optional[AsyncGroq] = None

    async def _ensure_router(self) -> Router:
        if self.llm is None:
            self.llm = await build_router()
        return self.llm

    async def get_structured_response(
            self,
            query: str,
            schema_model: type[BaseModel],
            system_prompt: str,
            model_group: str = "chat",
        ):
            router = await self._ensure_router()  
            response = await router.acompletion(
                model=model_group,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": query},
                ],
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": schema_model.__name__,
                        "schema": schema_model.model_json_schema(),
                    },
                },
            )
            content = response.choices[0].message.content
            try:
                return schema_model.model_validate_json(content)
            except ValidationError as e:
                logger.error(f"Structured output failed schema validation: {e}")
        
                raise

    async def get_response(
        self,
        query: str,
        system_prompt: str = "You are a helpful assistant.",
        model_group: str = "chat",
        temperature: float = 0.0,
        **kwargs,
    ) -> dict:
        """Return a plain text completion — no schema, no RAG context."""
        try:
            router = await self._ensure_router()
            response = await router.acompletion(
                model=model_group,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": query},
                ],
                temperature=temperature,
                **kwargs,
            )
            return {"model":response.model,"answer":response.choices[0].message.content or ""}
        except groq.AuthenticationError as e:
            raise GroqLLMException(f"Groq authentication failed — check GROQ_API_KEY: {e}")
        except groq.APITimeoutError as e:
            raise GroqTimeoutError(f"Groq API timed out: {e}")
        except groq.APIConnectionError as e:
            raise GroqConnectionError(f"Cannot reach Groq API: {e}")
        except groq.RateLimitError as e:
            raise GroqLLMException(f"Groq rate limit exceeded: {e}")
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            raise GroqLLMException(f"Failed to generate response: {e}")

    async def health_check(self) -> Dict[str, Any]:
        """Check Groq API connectivity."""
        try:
            router = await self._ensure_router()
            models = await router.acompletion(
                model="chat",
                messages=[{"role": "user", "content": "What is the capital of France?"}]
            )
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
            router = await self._ensure_router()

            response = await router.acompletion(
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
            router = await self._ensure_router()

            stream = await router.acompletion(
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