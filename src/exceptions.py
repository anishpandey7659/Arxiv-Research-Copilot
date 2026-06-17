
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