import logging
from typing import Dict, Optional

from src.schemas.guardrails.models import InputGuardrailResult
from src.services.guardrails.resources.prompt_classifier import (
    DEFAULT_REJECTION,
    GREETING_MESSAGE,
    Input_prompt,
    OFF_TOPIC_MESSAGE,
    REJECTION_MESSAGES,
)
from src.services.groq_llm.factory import make_groq_llm_client
from src.exceptions import LLmClassificationError

logger = logging.getLogger(__name__)



class LLmClassification:
    """Classifies a user query via an LLM and returns the appropriate user-facing response.

    Wraps an LLM with structured output so responses are parsed directly
    into an `InputGuardrailResult` (category, unsafe flag, reason), then
    maps that result to a rejection message, a canned greeting/off-topic
    reply, or the model's own category for safe/normal queries.
    """

    def __init__(self, model: str = "llama-3.3-70b-versatile"):
        """Initialize the LLM classification client.

        :param model: Name of the Groq-hosted model to use for classification
        """
        self.model = model
        self.llm_client = make_groq_llm_client().get_langchain_model(model)
        self.llm_struture = self.llm_client.with_structured_output(InputGuardrailResult)

        logger.info(f"LLM classification client initialized with model={model}")

    def _build_prompt(self, query: str) -> str:
        """Append the user's query to the base classification instructions.

        :param query: Raw user input to classify
        :returns: Full prompt string sent to the LLM (system instructions + query)
        """
        return Input_prompt + f"\n {query}"

    def _get_user_facing_response(self, classifier_output: InputGuardrailResult) -> Optional[str]:
        """Map a classification result to the message that should be shown to the user.

        :param classifier_output: Parsed classifier result, e.g. category
            "sexual", unsafe=True, reason="..."
        :returns: The rejection/canned message to show the user, or the raw
            category value for queries that should proceed normally
        """
        if classifier_output.unsafe:
            category = classifier_output.category.value
            logger.warning(f"Unsafe query classified, category={category}")
            return REJECTION_MESSAGES.get(category, DEFAULT_REJECTION)

        if classifier_output.category.value == "greeting":
            logger.debug("Query classified as greeting")
            return GREETING_MESSAGE

        if classifier_output.category.value == "off_topic":
            logger.debug("Query classified as off_topic")
            return OFF_TOPIC_MESSAGE

        return classifier_output.category.value

    def classify_result(self, query: str) -> Dict[str, Optional[object]]:
        """Run the full classification pipeline for a single query.

        :param query: Raw user input string
        :returns: A dict with "answer" (the user-facing string to display)
            and "reason" (the raw `InputGuardrailResult` returned by the model)
        :raises LLmClassificationError: if the underlying LLM call fails unexpectedly
        """
        if not query or not query.strip():
            logger.warning("Empty query provided to LLM classifier")
            return {"answer": DEFAULT_REJECTION, "reason": None}

        prompt = self._build_prompt(query)
        logger.debug("Invoking LLM for query classification")

        try:
            result = self.llm_struture.invoke(prompt)
        except Exception as e:
            logger.error(f"LLM classification call failed: {e}")
            raise LLmClassificationError("LLM classification call failed") from e

        answer = self._get_user_facing_response(result)
        logger.info(f"Query classified, category={result.category.value} unsafe={result.unsafe}")

        return {"answer": answer, "reason": result}