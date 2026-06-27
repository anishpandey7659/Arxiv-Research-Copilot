from src.schemas.guardrails.models import ClassificationResult
import re
import tiktoken

class PIIGuardrail:
    def __init__(self):
        self.patterns = {
            "email": r'\b[\w.-]+@[\w.-]+\.\w+\b',
            "phone": r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',
            "ssn": r'\b\d{3}-\d{2}-\d{4}\b',
            "credit_card": r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b',
        }

    def check(self, text: str) -> ClassificationResult:
        detected = {}

        for pii_type, pattern in self.patterns.items():
            matches = re.findall(pattern, text)
            if matches:
                detected[pii_type] = len(matches)

        if detected:
            return ClassificationResult(
                passed=False,
                reason=f"PII detected: {detected}",
                suggested_action="redact"
            )

        return ClassificationResult(passed=True)

    def redact(self, text: str) -> str:
        redacted = text
        for pii_type, pattern in self.patterns.items():
            redacted = re.sub(pattern, f"[{pii_type.upper()}_REDACTED]", redacted)
        return redacted