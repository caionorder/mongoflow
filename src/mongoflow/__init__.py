"""
MongoFlow - Elegant MongoDB ODM for Python
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

MongoFlow is a modern MongoDB Object Document Mapper (ODM) that makes
it easy to work with MongoDB in Python applications.

Basic usage:
    >>> from mongoflow import MongoFlow, Repository
    >>>
    >>> # Connect to MongoDB
    >>> MongoFlow.connect('mongodb://localhost:27017', 'mydb')
    >>>
    >>> # Define a repository
    >>> class UserRepository(Repository):
    ...     collection_name = 'users'
    >>>
    >>> # Use it!
    >>> repo = UserRepository()
    >>> user = repo.create({'name': 'John', 'age': 30})

Async usage:
    >>> from mongoflow import AsyncMongoFlow, AsyncRepository
    >>> import asyncio
    >>>
    >>> async def main():
    ...     await AsyncMongoFlow.connect('mongodb://localhost:27017', 'mydb')
    ...
    ...     class UserRepository(AsyncRepository):
    ...         collection_name = 'users'
    ...
    ...     repo = UserRepository()
    ...     user = await repo.create({'name': 'John', 'age': 30})
    >>>
    >>> asyncio.run(main())

Full documentation is available at https://mongoflow.readthedocs.io
"""

from mongoflow.base import BaseRepository
from mongoflow.connection import MongoFlow
from mongoflow.exceptions import (
    ConnectionError,
    MongoFlowError,
    QueryError,
    RepositoryError,
    ValidationError,
)
from mongoflow.model import Model
from mongoflow.query_builder import QueryBuilder
from mongoflow.repository import Repository
from mongoflow.version import __version__

__all__ = [
    # Core
    "MongoFlow",
    "Repository",
    "BaseRepository",
    "Model",
    "QueryBuilder",

    # Version
    "__version__",

    # Exceptions
    "MongoFlowError",
    "ConnectionError",
    "QueryError",
    "ValidationError",
    "RepositoryError",
]

# Convenience aliases
connect = MongoFlow.connect
disconnect = MongoFlow.disconnect

# Async support (optional - requires motor)
try:
    from mongoflow.async_connection import AsyncMongoFlow
    from mongoflow.async_model import AsyncModel
    from mongoflow.async_query_builder import AsyncQueryBuilder
    from mongoflow.async_repository import AsyncRepository

    # Add async classes to exports
    __all__ += [
        "AsyncMongoFlow",
        "AsyncRepository",
        "AsyncQueryBuilder",
        "AsyncModel",
    ]

    # Async convenience aliases
    async_connect = AsyncMongoFlow.connect
    async_disconnect = AsyncMongoFlow.disconnect

    # Flag to indicate async support is available
    ASYNC_SUPPORT = True

except ImportError:
    # Async support not available (motor not installed)
    ASYNC_SUPPORT = False

    # Define placeholder message for better error handling
    _async_error_msg = (
        "Async support requires Motor. "
        "Install with: pip install mongoflow[async] or pip install motor"
    )

    # Create placeholder classes that raise helpful errors
    class AsyncMongoFlow:
        def __init__(self, *args, **kwargs):
            raise ImportError(_async_error_msg)

        @classmethod
        def connect(cls, *args, **kwargs):
            raise ImportError(_async_error_msg)

    class AsyncRepository:
        def __init__(self, *args, **kwargs):
            raise ImportError(_async_error_msg)

    class AsyncQueryBuilder:
        def __init__(self, *args, **kwargs):
            raise ImportError(_async_error_msg)

    class AsyncModel:
        def __init__(self, *args, **kwargs):
            raise ImportError(_async_error_msg)

    # Still export them so imports don't fail, but they'll error when used
    __all__ += [
        "AsyncMongoFlow",
        "AsyncRepository",
        "AsyncQueryBuilder",
        "AsyncModel",
        "ASYNC_SUPPORT",
    ]

# Export ASYNC_SUPPORT flag
__all__.append("ASYNC_SUPPORT")

# Version check helper
def check_async_support():
    """Check if async support is available."""
    if not ASYNC_SUPPORT:
        print("❌ Async support not available. Install with: pip install mongoflow[async]")
        return False
    print("✅ Async support is available")
    return True
