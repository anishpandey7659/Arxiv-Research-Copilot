import logging
import re
import unicodedata
from typing import Dict, List, Optional, Tuple, Union

from src.schemas.guardrails.models import Category, RegrexResult
from src.services.guardrails.resources.patterns import (
    DANGEROUS_PATTERNS,
    GREETINGS_PATTERNS,
    HATE_PATTERNS,
    JAILBREAK_PATTERNS,
    SEXUAL_PATTERNS,
)
from src.services.guardrails.resources.prompt_classifier import (
    DEFAULT_REJECTION,
    GREETING_MESSAGE,
    REJECTION_MESSAGES,
)

logger = logging.getLogger(__name__)


class RegrexClassification:
    """Fast, deterministic classifier that flags input against regex pattern banks.

    Priority order matters: the most severe / highest-risk categories are
    checked first, since a single input could trip multiple banks and the
    most serious classification should win, not whichever bank happens to
    be checked last.
    """

    def __init__(self):
        """Initialize the pattern banks, priority order, and default actions."""
        self.JAILBREAK_PATTERNS = JAILBREAK_PATTERNS
        self.SEXUAL_PATTERNS = SEXUAL_PATTERNS
        self.HATE_PATTERNS = HATE_PATTERNS
        self.DANGEROUS_PATTERNS = DANGEROUS_PATTERNS
        self.GREETINGS_PATTERNS = GREETINGS_PATTERNS

        # Each entry is (Category, bank_key) where bank_key is the key used to
        # look up that category's pattern list in bank_map.
        self.PRIORITY_ORDER: List[Tuple[Category, str]] = [
            (Category.SEXUAL_MINOR, "SEXUAL_MINOR_PATTERNS"),
            (Category.DANGEROUS, "DANGEROUS_PATTERNS"),
            (Category.SEXUAL, "SEXUAL_PATTERNS"),
            (Category.HATE, "HATE_PATTERNS"),
            (Category.JAILBREAK, "JAILBREAK_PATTERNS"),
            (Category.GREETING, "GREETINGS_PATTERNS"),
        ]

        # Action mapping per category - adjust to your risk tolerance.
        self.DEFAULT_ACTIONS: Dict[Category, str] = {
            Category.SEXUAL_MINOR: "block",
            Category.DANGEROUS: "block",
            Category.SEXUAL: "review",
            Category.HATE: "review",
            Category.JAILBREAK: "review",
            Category.GREETING: "allow",
            Category.SAFE: "allow",
        }

        logger.info("Regex classifier initialized")

    def normalize_text(self, text: str) -> str:
        """Normalize text to reduce trivial regex evasion.

        - Unicode normalize (catches some homoglyph tricks)
        - Strip zero-width and invisible characters
        - Collapse repeated whitespace

        :param text: Raw input text
        :returns: Normalized text, or an empty string if `text` is falsy
        """
        if not text:
            return ""

        # Normalize unicode (e.g., fullwidth chars -> ascii equivalents where possible)
        text = unicodedata.normalize("NFKC", text)

        # Strip zero-width and other invisible/control characters often used
        # to break up flagged words (e.g., "i\u200bgnore")
        text = re.sub(r"[\u200b\u200c\u200d\ufeff\u2060]", "", text)

        # Collapse excessive whitespace/newlines
        text = re.sub(r"\s+", " ", text).strip()

        return text

    def _scan(self, text: str, patterns: List[re.Pattern]) -> List[Dict]:
        """Scan text against a single pattern bank.

        A single bad pattern is logged and skipped rather than allowed to
        crash the whole classification pipeline.

        :param text: Normalized text to scan
        :param patterns: Compiled regex patterns to check against `text`
        :returns: A list of hit dicts (index, pattern, matched_text, span)
        """
        hits = []
        for idx, pattern in enumerate(patterns):
            try:
                match = pattern.search(text)
            except re.error as e:
                logger.error(f"Pattern at index {idx} failed to evaluate: {e}")
                continue

            if match:
                hits.append(
                    {
                        "index": idx,
                        "pattern": pattern.pattern,
                        "matched_text": match.group(0),
                        "span": match.span(),
                    }
                )
        return hits

    def classify_input(
        self,
        text: str,
        sexual_minor_patterns: Optional[List[re.Pattern]] = None,
        custom_actions: Optional[Dict[Category, str]] = None,
    ) -> RegrexResult:
        """Run input through all guardrail pattern banks and return the highest-priority classification.

        Pattern lists are looked up via `bank_map` rather than imported
        implicitly, so banks can be swapped per environment (e.g. stricter
        banks in a teen-facing product) without changing this method.

        :param text: Raw user input to classify
        :param sexual_minor_patterns: Optional pattern list for the
            highest-priority sexual-minor-content category
        :param custom_actions: Optional overrides for `self.DEFAULT_ACTIONS`
        :returns: A `RegrexResult` for the first matching category in
            priority order, or a SAFE result if nothing matched
        """
        if not text or not text.strip():
            logger.debug("Empty text provided to regex classifier")

        normalized = self.normalize_text(text)
        actions = {**self.DEFAULT_ACTIONS, **(custom_actions or {})}

        # Keys here must match the bank_key strings used in PRIORITY_ORDER.
        bank_map = {
            "SEXUAL_MINOR_PATTERNS": sexual_minor_patterns or [],
            "DANGEROUS_PATTERNS": self.DANGEROUS_PATTERNS or [],
            "SEXUAL_PATTERNS": self.SEXUAL_PATTERNS or [],
            "HATE_PATTERNS": self.HATE_PATTERNS or [],
            "JAILBREAK_PATTERNS": self.JAILBREAK_PATTERNS or [],
            "GREETINGS_PATTERNS": self.GREETINGS_PATTERNS or [],
        }

        # Check categories in priority order; first non-empty hit wins.
        for category, bank_key in self.PRIORITY_ORDER:
            hits = self._scan(normalized, bank_map.get(bank_key, []))
            if hits:
                logger.info(f"Regex classifier matched category={category.value}, hits={len(hits)}")
                return RegrexResult(
                    category=category,
                    matched=True,
                    matched_patterns=hits,
                    action=actions.get(category, "review"),
                    raw_input=text,
                    normalized_input=normalized,
                )

        logger.debug("Regex classifier found no matches, classified as SAFE")
        return RegrexResult(
            category=Category.SAFE,
            matched=False,
            matched_patterns=[],
            action="allow",
            raw_input=text,
            normalized_input=normalized,
        )

    def get_default_message(self, classifier_output: RegrexResult) -> Union[str, bool]:
        """Decide what to do with a classified input.

        :param classifier_output: Output from `classify_input`
        :returns: A rejection/canned message string if the category is
            blocked (greeting, hate, jailbreak, sexual, dangerous), or
            False if the input is safe and should be sent further down
            the pipeline (e.g. to the LLM classifier)
        """
        category = classifier_output.category.value

        if category == "greeting":
            logger.debug("Regex classifier matched greeting pattern")
            return GREETING_MESSAGE

        blocked_categories = {"hate", "jailbreak", "sexual", "dangerous"}
        if category in blocked_categories:
            logger.warning(f"Regex classifier blocked category={category}")
            return REJECTION_MESSAGES.get(category, DEFAULT_REJECTION)

        return False