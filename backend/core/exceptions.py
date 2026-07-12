"""
ResearchAI — Custom Exception Hierarchy
All domain-specific exceptions are defined here so callers can catch
them at the appropriate granularity.
"""


class ResearchAIError(Exception):
    """Base exception for all ResearchAI errors."""
    def __init__(self, message: str, detail: str = ""):
        super().__init__(message)
        self.detail = detail


class WatsonxError(ResearchAIError):
    """Raised when the IBM watsonx API call fails."""


class SearchError(ResearchAIError):
    """Raised when an external search API call fails."""


class PDFProcessingError(ResearchAIError):
    """Raised when PDF extraction or parsing fails."""


class VectorStoreError(ResearchAIError):
    """Raised when a vector store operation fails."""


class EmbeddingError(ResearchAIError):
    """Raised when embedding generation fails."""


class CitationError(ResearchAIError):
    """Raised when citation generation fails."""


class ReportError(ResearchAIError):
    """Raised when report generation fails."""


class DatabaseError(ResearchAIError):
    """Raised when a database operation fails."""


class ValidationError(ResearchAIError):
    """Raised when user input validation fails."""
