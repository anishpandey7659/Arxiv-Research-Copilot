import logging
import time
from typing import Dict, Literal

import logfire
from langgraph.runtime import Runtime

from ..context import Context
from ..models import GuardrailScoring
from ..state import AgentState
from .utils import get_latest_query

logger = logging.getLogger(__name__)


def continue_after_guardrail(state: AgentState, runtime: Runtime[Context]) -> Literal["continue", "out_of_scope"]:
    """Determine whether to continue or reject based on guardrail results.

    :param state: Current agent state with guardrail results
    :param runtime: Runtime context containing guardrail threshold
    :returns: "continue" if score >= threshold, "out_of_scope" otherwise
    """
    guardrail_result = state.get("guardrail_result")
    if not guardrail_result:
        logger.warning("No guardrail result found, defaulting to continue")
        return "continue"

    category = guardrail_result.category

    logger.info(f"Guardrail category: {category} ,{guardrail_result}")
    return "continue" if category == 'normal' else "out_of_scope"


@logfire.instrument("node:guardrail", extract_args=False)
async def ainvoke_guardrail_step(
    state: AgentState,
    runtime: Runtime[Context],
) -> Dict[str, GuardrailScoring]:
    """Asynchronously invoke the guardrail validation step.

    Uses Custom Guardrails where we can Input token and Rate limiting, PII classifer, 
    Regrex classifer, and LLM classifer
    Guardrail result categories into multiple category 
    if normal: passes to next node
    else: user get Deafult message

    :param state: Current agent state
    :param runtime: Runtime context
    :returns: Dictionary with guardrail_result
    """
    logger.info("NODE: guardrail_validation")
    start_time = time.time()

    query = get_latest_query(state["messages"])
    logger.debug(f"Evaluating query: {query[:100]}...")

    span = None
    if runtime.context.langfuse_enabled and runtime.context.trace:
        try:
            span = runtime.context.langfuse_tracer.create_span(
                trace=runtime.context.trace,
                name="guardrail_validation",
                input_data={
                    "query": query,
                    "category": runtime.context.category,
                    "guardrails_provider": "custom",
                },
                metadata={"node": "guardrail"},
            )
        except Exception as e:
            logfire.warning(f"Failed to create Langfuse span for guardrail: {e}")

    try:
        if runtime.context.guardrails_service:
            result = await runtime.context.guardrails_service.classify_input(query,user_id='1') # Change this user_id now just for development
            category = result.category.value
            reason = result.reason
            logfire.info(f"Custom guardrail: category={category}, allowed={'Yes' if category=='normal' else 'No'}, reason={reason}")
        else:
            # No guardrails configured — fail-open
            category = 'normal'
            reason = "No guardrail service configured — passing through"
            logfire.debug(reason)

        response = GuardrailScoring(category=category, reason=reason)

        if span:
            execution_time = (time.time() - start_time) * 1000
            runtime.context.langfuse_tracer.end_span(
                span,
                output={
                    "score": response.category,
                    "reason": response.reason,
                    "decision": "continue" if response.category == 'normal' else "out_of_scope",
                },
                metadata={"execution_time_ms": execution_time},
            )

    except Exception as e:
        logfire.error(f"Guardrail validation failed: {e}, falling back to allow")
        response = GuardrailScoring(
            category='normal',
            reason=f"Guardrail check failed (fail-open): {str(e)}",
        )
        sanitized_query = None
        if span:
            execution_time = (time.time() - start_time) * 1000
            runtime.context.langfuse_tracer.update_span(
                span,
                output={"category": response.category, "reason": response.reason, "error": str(e)},
                metadata={"execution_time_ms": execution_time, "fallback": True},
                level="WARNING",
            )
            runtime.context.langfuse_tracer.end_span(span)

    result = {"guardrail_result": response}
    return result
