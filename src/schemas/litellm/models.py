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
    api_key_env: str =settings.litellm.master_key
    timeout: float =settings.litellm.timeout
    extra_params: dict[str, Any] = field(default_factory=dict)