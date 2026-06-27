
class ArxivAPIException(Exception):
    """Base exception for arXiv API-related errors."""

class ArxivParseError(ArxivAPIException):
    """Exception raised when parsing the API response fails."""

class ArxivAPIRequestError(ArxivAPIException):
    """Exception raised when an API request fails."""

class ArxivAPITimeoutError(ArxivAPIException):
    """Exception raised when an API request times out."""

class PDFDownloadException(Exception):
    """Exception raised when downloading a PDF fails."""

class PDFDownloadTimeoutError(PDFDownloadException):
    """Exception raised when downloading a PDF times out."""

class PDFParsingException(Exception):
    """Exception raised when Parsing a PDF """

class PDFValidationError(PDFParsingException):
    """Exception raised when We dont have valid PDF"""

class LLMException(Exception):
    """Base exception for LLM-related errors."""

class GroqLLMException(LLMException):
    """Exception raised for Groq API errors."""

class GroqConnectionError(GroqLLMException):
    """Exception raised due to Connection Failed"""

class GroqTimeoutError(GroqLLMException):
    """Exception raised when the Groq API times out."""

class GuardrailError(Exception):
    """Raised when a guardrail check fails unexpectedly.

    This is distinct from a normal "blocked" classification result, which
    is returned rather than raised.
    """

class LLmClassificationError(Exception):
    """Raised when the underlying LLM classification call fails unexpectedly."""