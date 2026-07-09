from src.services.guardrails.Input_guardrails.client import InputGuardrails
from typing import Optional
from src.config import Settings, get_settings
from .input_limit import InputLimitsGuardrail
from .llm_classify import LLmClassification
from .PII import PIIGuardrail
from .regex_classfy import RegrexClassification

def make_Input_guardrails(settings: Optional[Settings] = None)->InputGuardrails:
    """Factory function to Create the the object of Input Guardrails 
    :param -> Take Setting Optional
    :Return -> return the object of Input guardrails
    """

    if settings is None:
        settings = get_settings()

    input_limit_client = InputLimitsGuardrail(settings.Input_limit_max_tokens,settings.max_requests_per_minute)
    llm_classify_client = LLmClassification()
    pii_client = PIIGuardrail()
    regrex_client = RegrexClassification()

    return InputGuardrails(input_limit_client,pii_client,regrex_client,llm_classify_client)