"""Repository pattern implementation for MongoFlow."""

from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Union

from bson import ObjectId
from pymongo import UpdateOne
from pymongo.collection import Collection

from mongoflow.base import BaseRepository
from mongoflow.connection import MongoFlow
from mongoflow.exceptions import RepositoryError
from mongoflow.query_builder import QueryBuilder
from mongoflow.utils import convert_object_id, serialize_document


class Repository(BaseRepository):
    """
    Enhanced repository with all features.

    Example:
        >>> class UserRepository(Repository):
        ...     collection_name = 'users'
        ...
        ...     def find_by_email(self, email: str):
        ...         return self.where('email', email).first()
    """

    collection_name: Optional[str] = None
    connection_name: str = "default"
    indexes: List[Dict[str, Any]] = []

    def __init__(self, collection_name: Optional[str] = None):
        """Initialize repository."""
        self._collection_name = collection_name or self.collection_name
        if not self._collection_name:
            raise RepositoryError("Collection name must be specified")

        self._connection = MongoFlow.get_connection(self.connection_name)
        self._database = self._connection.database
        self._collection: Optional[Collection] = None
        self._ensure_indexes()

    @property
    def collection(self) -> Collection:
        """Get MongoDB collection (lazy loading)."""
        if self._collection is None:
            self._collection = self._database[self._collection_name]
        return self._collection

    def _ensure_indexes(self) -> None:
        """Create indexes if they don't exist."""
        if self.indexes:
            for index_spec in self.indexes:
                try:
                    self.collection.create_index(**index_spec)
                except Exception:
                    # Log but don't fail - index might already exist
                    pass

    def query(self) -> QueryBuilder:
        """Create a new query builder."""
        return QueryBuilder(self.collection)

    def where(self, field: str, value: Any, operator: str = "$eq") -> QueryBuilder:
        """Shortcut to start a query with where clause."""
        return self.query().where(field, value, operator)

    def all(self) -> List[Dict[str, Any]]:
        """Get all documents."""
        return self.query().get()

    def find(self, id: Union[str, ObjectId]) -> Optional[Dict[str, Any]]:
        """Find document by ID."""
        id = convert_object_id(id)
        return self.query().where("_id", id).first()

    def find_by(self, **kwargs) -> Optional[Dict[str, Any]]:
        """Find single document by multiple fields."""
        query = self.query()
        for field, value in kwargs.items():
            query.where(field, value)
        return query.first()

    def find_many(self, ids: List[Union[str, ObjectId]]) -> List[Dict[str, Any]]:
        """Find multiple documents by IDs."""
        ids = [convert_object_id(id) for id in ids]
        return self.query().where_in("_id", ids).get()

    def create(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new document.

        Args:
            data: Document data

        Returns:
            Created document with ID
        """
        try:
            data = self._prepare_for_insert(data)
            result = self.collection.insert_one(data)
            data["_id"] = str(result.inserted_id)
            return data
        except Exception as e:
            raise RepositoryError(f"Failed to create document: {e}")

    def create_many(self, documents: List[Dict[str, Any]]) -> List[str]:
        """
        Create multiple documents.

        Args:
            documents: List of documents

        Returns:
            List of created IDs
        """
        try:
            if not documents:
                return []

            prepared = [self._prepare_for_insert(doc) for doc in documents]
            result = self.collection.insert_many(prepared)
            return [str(id) for id in result.inserted_ids]
        except Exception as e:
            raise RepositoryError(f"Failed to create documents: {e}")

    def update(self, id: Union[str, ObjectId], data: Dict[str, Any]) -> bool:
        """
        Update a document by ID.

        Args:
            id: Document ID
            data: Update data

        Returns:
            True if updated, False otherwise
        """
        try:
            id = convert_object_id(id)
            data = self._prepare_for_update(data)
            result = self.collection.update_one(
                {"_id": id},
                {"$set": data}
            )
            return result.modified_count > 0
        except Exception as e:
            raise RepositoryError(f"Failed to update document: {e}")

    def update_many(self, filter_dict: Dict[str, Any], data: Dict[str, Any]) -> int:
        """
        Update multiple documents.

        Args:
            filter_dict: Filter criteria
            data: Update data

        Returns:
            Number of updated documents
        """
        try:
            data = self._prepare_for_update(data)
            result = self.collection.update_many(
                filter_dict,
                {"$set": data}
            )
            return result.modified_count
        except Exception as e:
            raise RepositoryError(f"Failed to update documents: {e}")

    def upsert(self, filter_dict: Dict[str, Any], data: Dict[str, Any]) -> Tuple[Optional[str], bool]:
        """
        Update or insert a document.

        Args:
            filter_dict: Filter criteria
            data: Document data

        Returns:
            Tuple of (document_id, was_created)
        """
        try:
            data = self._prepare_for_update(data)
            result = self.collection.update_one(
                filter_dict,
                {"$set": data},
                upsert=True
            )

            if result.upserted_id:
                return str(result.upserted_id), True
            else:
                # Find the document to get its ID
                doc = self.collection.find_one(filter_dict)
                return str(doc["_id"]) if doc else None, False
        except Exception as e:
            raise RepositoryError(f"Failed to upsert document: {e}")

    def find_or_create(self, filter_dict: Dict[str, Any], defaults: Optional[Dict[str, Any]] = None) -> Tuple[Dict[str, Any], bool]:
        """
        Find a document or create if not exists.

        Args:
            filter_dict: Search criteria
            defaults: Default values if creating

        Returns:
            Tuple of (document, was_created)
        """
        try:
            # Try to find first
            document = self.collection.find_one(filter_dict)

            if document:
                return serialize_document(document), False

            # Not found, create new
            new_data = {**filter_dict, **(defaults or {})}
            new_data = self._prepare_for_insert(new_data)
            result = self.collection.insert_one(new_data)
            new_data["_id"] = str(result.inserted_id)

            return new_data, True
        except Exception as e:
            raise RepositoryError(f"Failed in find_or_create: {e}")

    def delete(self, id: Union[str, ObjectId]) -> bool:
        """
        Delete a document by ID.

        Args:
            id: Document ID

        Returns:
            True if deleted, False otherwise
        """
        try:
            id = convert_object_id(id)
            result = self.collection.delete_one({"_id": id})
            return result.deleted_count > 0
        except Exception as e:
            raise RepositoryError(f"Failed to delete document: {e}")

    def delete_many(self, filter_dict: Dict[str, Any]) -> int:
        """
        Delete multiple documents.

        Args:
            filter_dict: Filter criteria

        Returns:
            Number of deleted documents
        """
        try:
            result = self.collection.delete_many(filter_dict)
            return result.deleted_count
        except Exception as e:
            raise RepositoryError(f"Failed to delete documents: {e}")

    def truncate(self) -> bool:
        """Delete all documents in collection."""
        try:
            result = self.collection.delete_many({})
            return result.deleted_count > 0
        except Exception as e:
            raise RepositoryError(f"Failed to truncate collection: {e}")

    def bulk_write(self, operations: List[Dict[str, Any]]) -> Dict[str, int]:
        """
        Execute bulk write operations.

        Args:
            operations: List of bulk operations

        Returns:
            Operation statistics
        """
        try:
            if not operations:
                return {"inserted": 0, "updated": 0, "deleted": 0}

            result = self.collection.bulk_write(operations)

            return {
                "inserted": result.inserted_count,
                "updated": result.modified_count,
                "deleted": result.deleted_count,
                "matched": result.matched_count,
            }
        except Exception as e:
            raise RepositoryError(f"Bulk write failed: {e}")

    def bulk_upsert(self, documents: List[Dict[str, Any]], unique_fields: List[str]) -> Dict[str, int]:
        """
        Bulk upsert documents.

        Args:
            documents: List of documents
            unique_fields: Fields that determine uniqueness

        Returns:
            Operation statistics
        """
        try:
            operations = []

            for doc in documents:
                # Build filter from unique fields
                filter_dict = {field: doc[field] for field in unique_fields if field in doc}

                # Prepare update data
                update_data = self._prepare_for_update(doc.copy())

                operations.append(
                    UpdateOne(
                        filter_dict,
                        {"$set": update_data},
                        upsert=True
                    )
                )

            if operations:
                result = self.collection.bulk_write(operations)
                return {
                    "matched": result.matched_count,
                    "modified": result.modified_count,
                    "upserted": result.upserted_count,
                }

            return {"matched": 0, "modified": 0, "upserted": 0}
        except Exception as e:
            raise RepositoryError(f"Bulk upsert failed: {e}")

    def increment(self, id: Union[str, ObjectId], field: str, value: int = 1) -> bool:
        """
        Increment a numeric field.

        Args:
            id: Document ID
            field: Field to increment
            value: Increment value (negative to decrement)

        Returns:
            True if successful
        """
        try:
            id = convert_object_id(id)
            result = self.collection.update_one(
                {"_id": id},
                {
                    "$inc": {field: value},
                    "$set": {"updated_at": datetime.utcnow()}
                }
            )
            return result.modified_count > 0
        except Exception as e:
            raise RepositoryError(f"Failed to increment field: {e}")

    def push(self, id: Union[str, ObjectId], field: str, value: Any) -> bool:
        """
        Push value to array field.

        Args:
            id: Document ID
            field: Array field name
            value: Value to push

        Returns:
            True if successful
        """
        try:
            id = convert_object_id(id)
            result = self.collection.update_one(
                {"_id": id},
                {
                    "$push": {field: value},
                    "$set": {"updated_at": datetime.utcnow()}
                }
            )
            return result.modified_count > 0
        except Exception as e:
            raise RepositoryError(f"Failed to push to array: {e}")

    def pull(self, id: Union[str, ObjectId], field: str, value: Any) -> bool:
        """
        Pull value from array field.

        Args:
            id: Document ID
            field: Array field name
            value: Value to pull

        Returns:
            True if successful
        """
        try:
            id = convert_object_id(id)
            result = self.collection.update_one(
                {"_id": id},
                {
                    "$pull": {field: value},
                    "$set": {"updated_at": datetime.utcnow()}
                }
            )
            return result.modified_count > 0
        except Exception as e:
            raise RepositoryError(f"Failed to pull from array: {e}")

    def _prepare_for_insert(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare document for insertion."""
        data["created_at"] = datetime.utcnow()
        data["updated_at"] = datetime.utcnow()
        return data

    def _prepare_for_update(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare document for update."""
        data["updated_at"] = datetime.utcnow()
        # Remove _id if present
        data.pop("_id", None)
        return data
