"""Timestamp mixin for automatic created_at and updated_at fields."""

from datetime import datetime
from typing import Any, Dict


class TimestampMixin:
    """
    Mixin to add automatic timestamps to documents.

    Adds created_at and updated_at fields automatically.

    Example:
        >>> class UserRepository(Repository, TimestampMixin):
        ...     collection_name = 'users'
    """

    def _prepare_for_insert(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Add timestamps when creating document."""
        data = super()._prepare_for_insert(data) if hasattr(super(), '_prepare_for_insert') else data

        now = datetime.utcnow()
        data.setdefault('created_at', now)
        data.setdefault('updated_at', now)

        return data

    def _prepare_for_update(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Update timestamp when updating document."""
        data = super()._prepare_for_update(data) if hasattr(super(), '_prepare_for_update') else data

        data['updated_at'] = datetime.utcnow()

        # Remove created_at if present (should not be updated)
        data.pop('created_at', None)

        return data

    def touch(self, id) -> bool:
        """
        Update only the updated_at timestamp.

        Args:
            id: Document ID

        Returns:
            True if successful
        """
        return self.update(id, {})

    def recently_created(self, minutes: int = 60):
        """
        Get documents created recently.

        Args:
            minutes: Number of minutes to look back

        Returns:
            QueryBuilder instance
        """
        from datetime import timedelta
        cutoff = datetime.utcnow() - timedelta(minutes=minutes)
        return self.query().where_greater_than('created_at', cutoff)

    def recently_updated(self, minutes: int = 60):
        """
        Get documents updated recently.

        Args:
            minutes: Number of minutes to look back

        Returns:
            QueryBuilder instance
        """
        from datetime import timedelta
        cutoff = datetime.utcnow() - timedelta(minutes=minutes)
        return self.query().where_greater_than('updated_at', cutoff)

    def order_by_created(self, direction: str = 'desc'):
        """
        Order by creation date.

        Args:
            direction: 'asc' or 'desc'

        Returns:
            QueryBuilder instance
        """
        return self.query().order_by('created_at', direction)

    def order_by_updated(self, direction: str = 'desc'):
        """
        Order by update date.

        Args:
            direction: 'asc' or 'desc'

        Returns:
            QueryBuilder instance
        """
        return self.query().order_by('updated_at', direction)
