from src.schemas.guardrails.models import ClassificationResult
from collections import defaultdict
import time
import tiktoken

class InputLimitsGuardrail:
    def __init__(
        self,
        max_tokens: int = 2000,
        max_requests_per_minute: int = 10
    ):
        self.max_tokens = max_tokens
        self.max_rpm = max_requests_per_minute
        self.request_counts = defaultdict(list)

    def _count_tokens(self,text: str) -> int:
        encoding = tiktoken.get_encoding("cl100k_base")
        return len(encoding.encode(text))
    
    def check(self, text: str, user_id: str) -> ClassificationResult:
        # Token limit
        tokens = self._count_tokens(text)
        if tokens > self.max_tokens:
            return ClassificationResult(
                passed=False,
                reason=f"Input too long: {tokens} tokens (max {self.max_tokens})"
            )

        # Rate limit
        now = time.time()
        recent = [t for t in self.request_counts[user_id] if now - t < 60]
        self.request_counts[user_id] = recent

        if len(recent) >= self.max_rpm:
            return ClassificationResult(
                passed=False,
                reason="Rate limit exceeded"
            )

        self.request_counts[user_id].append(now)
        return ClassificationResult(passed=True)
    