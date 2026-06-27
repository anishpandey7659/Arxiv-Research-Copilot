from src.services.guardrails.Input_guardrails.client import InputGuardrails

from .input_limit import InputLimitsGuardrail
from .llm_classify import LLmClassification
from .PII import PIIGuardrail
from .regex_classfy import RegrexClassification

def make_Input_guardrails():
    input_limit_client=InputLimitsGuardrail()
    llm_classify_client=LLmClassification()
    pii_client=PIIGuardrail()
    regrex_client=RegrexClassification()
    return InputGuardrails(input_limit_client,pii_client,regrex_client,llm_classify_client)