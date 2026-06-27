import logging
import time
from typing import Dict, Optional, Tuple, Union

from .input_limit import InputLimitsGuardrail
from .llm_classify import LLmClassification
from .PII import PIIGuardrail
from .regex_classfy import RegrexClassification
from src.exceptions import GuardrailError

logger = logging.getLogger(__name__)



class InputGuardrails:
    """Service for running layered safety checks on incoming user queries.

    Runs input-limit checks, PII detection/redaction, regex-based
    classification, and LLM-based classification in sequence. Each layer
    can short-circuit the pipeline by returning a blocked result.
    """

    def __init__(
        self,
        Input_limit: InputLimitsGuardrail,
        pii_guarrails: PIIGuardrail,
        regex_guardrail: RegrexClassification,
        llm_guadrails: LLmClassification,
    ):
        """Initialize the input guardrails pipeline.

        :param Input_limit: Client used to enforce per-user input limits
        :param pii_guarrails: Client used to detect and redact PII
        :param regex_guardrail: Client used for regex-based classification
        :param llm_guadrails: Client used for LLM-based classification
        """
        self._input_limit_client = Input_limit
        self._pii_client = pii_guarrails
        self._regex_client = regex_guardrail
        self._llm_classify_client = llm_guadrails

        logger.info("Input guardrails initialized")

    def classify_input(self, query: str, user_id: str) -> Union[Dict, Tuple[Dict, str]]:
        """Run the full guardrail pipeline against a user query.

        Strategy:
        - Reject empty/invalid input early
        - Enforce per-user input limits
        - Detect and redact PII before any further checks
        - Apply fast regex-based classification
        - Fall back to LLM-based classification for anything not already blocked

        :param query: Raw text submitted by the user
        :param user_id: Identifier used for per-user limits and auditing
        :returns: A dict with a "reason" key if blocked by the limit check,
            a default-message dict if blocked by the regex classifier,
            (llm_result, query) if the LLM classifier marks the query as
            "normal", or the raw llm_result dict otherwise
        :raises GuardrailError: if any underlying guardrail client raises
            an unexpected exception
        """
        if not query or not query.strip():
            logger.warning(f"Empty query provided for user {user_id}")
            return {"reason": "Query cannot be empty."}

        if not user_id:
            logger.warning("Missing user_id for incoming query")
            return {"reason": "user_id is required."}

        start_time = time.monotonic()
        logger.info(f"Guardrail pipeline started for user {user_id}")

        try:
            limit_result = self._check_input_limit(query, user_id)
            if limit_result is not None:
                return limit_result

            query = self._check_pii(query, user_id)

            regex_result = self._check_regex(query, user_id)
            if regex_result is not None:
                return regex_result

            llm_result = self._check_llm(query, user_id)
        except Exception as e:
            logger.error(f"Unexpected error in guardrail pipeline for user {user_id}: {e}")
            raise GuardrailError(f"Guardrail pipeline failed for user_id={user_id}") from e

        elapsed_ms = (time.monotonic() - start_time) * 1000
        logger.info(f"Guardrail pipeline finished for user {user_id} in {elapsed_ms:.1f}ms")

        if llm_result.get("answer") == "normal":
            return llm_result, query

        # Off-topic, sexual, racist, or any other unsafe classification.
        logger.warning(f"Query flagged by LLM classifier for user {user_id}: {llm_result.get('answer')}")
        return llm_result

    def _check_input_limit(self, query: str, user_id: str) -> Optional[Dict]:
        """Check per-user input limits.

        :param query: Raw user query
        :param user_id: Identifier used for per-user limits
        :returns: A dict with a "reason" key if blocked, otherwise None
        """
        logger.debug(f"Checking input limit for user {user_id}")
        limit_check = self._input_limit_client.check(query, user_id)

        if not limit_check.passed:
            logger.info(f"Blocked by input limit check for user {user_id}: {limit_check.reason}")
            return {"reason": limit_check.reason}

        return None

    def _check_pii(self, query: str, user_id: str) -> str:
        """Detect and redact PII from a query.

        Note: query content is intentionally never logged here, to avoid
        leaking sensitive data into logs.

        :param query: Raw (or already limit-checked) user query
        :param user_id: Identifier used for auditing
        :returns: The original query, or a redacted version if PII was found
        """
        logger.debug(f"Checking PII for user {user_id}")
        pii_check = self._pii_client.check(query)

        if not pii_check.passed:
            logger.info(f"PII detected for user {user_id}, redacting query")
            return self._pii_client.redact(query)

        return query

    def _check_regex(self, query: str, user_id: str) -> Optional[Dict]:
        """Run regex-based classification on a query.

        :param query: Query to classify
        :param user_id: Identifier used for auditing
        :returns: A default-message dict if blocked, otherwise None
        """
        logger.debug(f"Checking regex classification for user {user_id}")
        regex_check = self._regex_client.classify_input(query)

        if regex_check:
            default_message = self._regex_client.get_default_message(regex_check)
            if default_message:
                logger.info(f"Blocked by regex classifier for user {user_id}: category={regex_check}")
                return default_message

        return None

    def _check_llm(self, query: str, user_id: str) -> Dict:
        """Run LLM-based classification on a query.

        :param query: Query to classify
        :param user_id: Identifier used for auditing
        :returns: The raw classification result dict from the LLM client
        """
        logger.debug(f"Checking LLM classification for user {user_id}")
        return self._llm_classify_client.classify_result(query)