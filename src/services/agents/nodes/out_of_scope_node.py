import logging
from typing import Dict, List

import logfire

from langchain_core.messages import AIMessage
from langgraph.runtime import Runtime

from ..context import Context
from ..state import AgentState
from .utils import get_latest_query
from src.services.agents.models import GuardrailScoring
from typing import Optional
from src.services.guardrails.resources.prompt_classifier import (
    DEFAULT_REJECTION,
    GREETING_MESSAGE,
    OFF_TOPIC_MESSAGE,
    REJECTION_MESSAGES,
)

logger = logging.getLogger(__name__)



def _get_user_facing_response(classifier_output: GuardrailScoring) -> Optional[str]:
    """Return the appropriate user-facing response for a guardrail classification.

    Maps the classifier's category to a predefined response message:
    - ``greeting`` → greeting message.
    - ``off_topic`` → off-topic message.
    - Any other non-``normal`` category → rejection message based on the category.
    - ``normal`` → returns ``"normal"`` to indicate the query should proceed
      to the next node without a canned response.

    Args:
        classifier_output: The guardrail classification result containing
            the predicted category and related metadata.

    Returns:
        A predefined user-facing message for non-normal categories, or
        ``"normal"`` if the query passes the guardrail checks.
    """
    if classifier_output.category !='normal':
        if classifier_output.category == "greeting":
            logger.debug("Query classified as greeting")
            return GREETING_MESSAGE
        if classifier_output.category== "off_topic":
            logger.debug("Query classified as off_topic")
            return OFF_TOPIC_MESSAGE
        category = classifier_output.category
        logger.warning(f"Unsafe query classified, category={category}")
        return REJECTION_MESSAGES.get(category, DEFAULT_REJECTION)
    
    # If it is normal then passes to next node
    return classifier_output.category


@logfire.instrument("node:out_of_scope", extract_args=False)
async def ainvoke_out_of_scope_step(
    state: AgentState,
    runtime: Runtime[Context],
) :
    #-> Dict[str, List[AIMessage]]
    """Handle out-of-scope queries with a helpful message.

    This node responds to queries that are outside the domain of
    CS/AI/ML research papers with a polite, informative message.

    :param state: Current agent state
    :param runtime: Runtime context (not used in this node)
    :returns: Dictionary with messages containing the out-of-scope response
    """
    logfire.info("NODE: out_of_scope")

    question = get_latest_query(state["messages"])
    classifier_output: Optional[GuardrailScoring] = state.get("guardrail_result")

    canned_response = (
        _get_user_facing_response(classifier_output) if classifier_output else None
    )

    if canned_response:
        response_text = canned_response
    else:
        # Fallback: generic out-of-scope response when no classifier result
        # is available or the category has no canned message mapped.
        response_text = (
            "I apologize, but I can only help with questions about academic research papers "
            "in Computer Science, Artificial Intelligence, and Machine Learning from arXiv.\n\n"
            f"Your question: '{question}'\n\n"
            "This appears to be outside my domain of expertise. For questions like this, you might want to try:\n"
            "- General-purpose AI assistants for broad knowledge questions\n"
            "- Domain-specific resources for topics outside CS/AI/ML\n"
            "- Technical documentation if asking about specific software/tools\n\n"
            "If you have a question about AI/ML research papers, I'd be happy to help!"
        )

    logfire.info("Responding with out-of-scope message")

    return {"messages": [AIMessage(content=response_text)]}