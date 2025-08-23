"""Base repository class for MongoFlow."""

from abc import ABC
from typing import Optional


class BaseRepository(ABC):
    """
    Abstract base repository class.

    All repositories should inherit from this class.
    """

    collection_name: Optional[str] = None
    connection_name: str = "default"

    def __init__(self, collection_name: Optional[str] = None):
        """Initialize base repository."""
        self._collection_name = collection_name or self.collection_name
        if not self._collection_name:
            raise ValueError("Collection name must be specified")
