import logging
import os
from typing import Any
from litellm import ModelConfig, Router
from src.config import get_settings
settings = get_settings()
# Logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger("llm_router")

from src.schemas.litellm.models import ModelConfig

MODEL_CONFIGS: list[ModelConfig] = [
    ModelConfig(name="chat", provider_model="groq/llama-3.3-70b-versatile", label="groq-llama3"),
    ModelConfig(name="chat", provider_model="openrouter/hy3-295B", label="hy3-fallback"),
    ModelConfig(name="chat", provider_model="gemini/gemini-2.5-flash",       label="gemini"),
    ModelConfig(name="chat", provider_model="groq/gpt-oss-120b",             label="openai-via-groq"),

    # Struture 
    ModelConfig(name="structured-output", provider_model="gemini/gemini-2.5-flash",       label="gemini"),
    ModelConfig(name="structured-output", provider_model="groq/llama-3.3-70b-versatile", label="structured-output"),
    
    # fallback group: "chat-fallback" — only used if all "chat" deployments fail
    ModelConfig(name="chat-fallback1", provider_model="openrouter/nvidia/nemotron-3-ultra-550b-a55b:free", label="nemotron-fallback"),
    ModelConfig(name="chat-fallback2", provider_model="openrouter/hy3-295B", label="hy3-fallback"),

]

def build_model_list(configs: list[ModelConfig]) -> list[dict[str, Any]]:
    model_list = []
    for cfg in configs:
        litellm_params = {
            "model": cfg.provider_model,
            "api_key": cfg.api_key_env,
            "api_base": cfg.api_base,
            "timeout": cfg.timeout,
            **cfg.extra_params,
        }
        model_list.append(
            {
                "model_name": cfg.name,
                "litellm_params": litellm_params,
                "model_info": {"id": cfg.label},
            }
        )
    logger.info("Built model list with %d entries: %s", len(model_list), [c.label for c in configs])
    return model_list


async def build_router(configs: list[ModelConfig] | None = None) -> Router:
    configs = configs or MODEL_CONFIGS
    if not configs:
        raise ValueError("No model configs provided; router requires at least one model.")
    print(f"Building router with {len(configs)} model configs")
    strategy = settings.litellm.routing_strategy
    router = Router(
        model_list=build_model_list(configs),
        routing_strategy=strategy,
        num_retries=settings.litellm.num_retries,
        timeout=settings.litellm.request_timeout,
        allowed_fails=settings.litellm.allowed_fails,
        cooldown_time=settings.litellm.cooldown_time,
        fallbacks=[
                {"chat": ["chat-fallback1", "chat-fallback2"]},
            ],
    )
    logger.info("Router initialized with strategy=%s, %d models", strategy, len(configs))
    return router
