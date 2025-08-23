"""Soft delete mixin for MongoFlow repositories."""

from datetime import datetime
from typing import Union

from bson import ObjectId


class SoftDeleteMixin:
    """
    Mixin to add soft delete functionality.

    Documents are marked as deleted instead of being physically removed.

    Example:
        >>> class UserRepository(Repository, SoftDeleteMixin):
        ...     collection_name = 'users'
        ...
        >>> users = UserRepository()
        >>> users.soft_delete('user_id')
        >>> users.restore('user_id')
        >>> deleted_users = users.only_trashed().get()
    """

    soft_delete_field: str = 'deleted_at'

    def soft_delete(self, id: Union[str, ObjectId]) -> bool:
        """
        Soft delete a document.

        Args:
            id: Document ID

        Returns:
            True if successful
        """
        return self.update(id, {self.soft_delete_field: datetime.utcnow()})

    def restore(self, id: Union[str, ObjectId]) -> bool:
        """
        Restore a soft deleted document.

        Args:
            id: Document ID

        Returns:
            True if successful
        """
        return self.update(id, {self.soft_delete_field: None})

    def force_delete(self, id: Union[str, ObjectId]) -> bool:
        """
        Permanently delete a document.

        Args:
            id: Document ID

        Returns:
            True if successful
        """
        # Call the actual delete method from parent
        return super().delete(id)

    def delete(self, id: Union[str, ObjectId]) -> bool:
        """
        Override delete to use soft delete by default.

        Args:
            id: Document ID

        Returns:
            True if successful
        """
        return self.soft_delete(id)

    def query(self):
        """
        Override query to exclude soft deleted documents by default.

        Returns:
            QueryBuilder instance
        """
        q = super().query()
        # Exclude soft deleted documents
        return q.where_null(self.soft_delete_field)

    def with_trashed(self):
        """
        Include soft deleted documents in query.

        Returns:
            QueryBuilder instance
        """
        # Get base query without soft delete filter
        return super().query()

    def only_trashed(self):
        """
        Get only soft deleted documents.

        Returns:
            QueryBuilder instance
        """
        return super().query().where_not_null(self.soft_delete_field)

    def is_trashed(self, id: Union[str, ObjectId]) -> bool:
        """
        Check if a document is soft deleted.

        Args:
            id: Document ID

        Returns:
            True if soft deleted
        """
        doc = self.with_trashed().where('_id', id).first()
        if doc:
            return doc.get(self.soft_delete_field) is not None
        return False

    def empty_trash(self) -> int:
        """
        Permanently delete all soft deleted documents.

        Returns:
            Number of documents deleted
        """
        # Find all soft deleted documents
        trashed = self.only_trashed().get()
        count = 0

        for doc in trashed:
            if self.force_delete(doc['_id']):
                count += 1

        return count

    def prune(self, days: int = 30) -> int:
        """
        Delete documents that have been soft deleted for more than N days.

        Args:
            days: Number of days

        Returns:
            Number of documents deleted
        """
        from datetime import timedelta

        cutoff = datetime.utcnow() - timedelta(days=days)
        old_trashed = (super().query()
                      .where_less_than(self.soft_delete_field, cutoff)
                      .get())

        count = 0
        for doc in old_trashed:
            if self.force_delete(doc['_id']):
                count += 1

        return count
