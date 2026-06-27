from enum import Enum
from pydantic import BaseModel, Field
from dataclasses import dataclass, field
from typing import Optional


class Category(Enum):
    SAFE = "safe"
    GREETING = "greeting"
    JAILBREAK = "jailbreak"
    SEXUAL = "sexual"
    SEXUAL_MINOR = "sexual_minor"      # highest priority, hard-block
    HATE = "hate"
    DANGEROUS = "dangerous"

class LLM_CATEGORY(Enum):
    OFF_TOPIC = "off_topic"
    NORMAL = "normal"
    GREETING = "greeting"
    JAILBREAK = "jailbreak"
    SEXUAL = "sexual"
    HATE = "hate"
    DANGEROUS = "dangerous"


class InputGuardrailResult(BaseModel):
    category: LLM_CATEGORY
    unsafe: bool
    reason: str = Field(
        description="Short reason for classification",
        max_length=100
    )
    
class ClassificationResult(BaseModel):
    passed: bool = Field(description="Wheather Guardrails pass or not tell in true or false")
    reason: Optional[str] = Field(default=None,description="Check PII")
    suggested_action: Optional[str] = Field(default=None,description="action to take")


@dataclass
class RegrexResult:
    category: Category
    matched: bool
    matched_patterns: list = field(default_factory=list)
    action: str = "allow"             # "allow" | "review" | "block"
    raw_input: str = ""
    normalized_input: str = ""