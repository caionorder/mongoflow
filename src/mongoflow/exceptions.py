"""Custom exceptions for MongoFlow."""


class MongoFlowError(Exception):
    """Base exception for MongoFlow."""
    pass


class ConnectionError(MongoFlowError):
    """Raised when connection to MongoDB fails."""
    pass


class QueryError(MongoFlowError):
    """Raised when query execution fails."""
    pass


class ValidationError(MongoFlowError):
    """Raised when validation fails."""
    pass


class RepositoryError(MongoFlowError):
    """Raised when repository operation fails."""
    pass


class ModelError(MongoFlowError):
    """Raised when model operation fails."""
    pass
