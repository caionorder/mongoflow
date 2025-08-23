"""Async repository implementation for MongoFlow."""

from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Union

from bson import ObjectId

from mongoflow.async_connection import AsyncMongoFlow
from mongoflow.async_query_builder import AsyncQueryBuilder
from mongoflow.base import BaseRepository
from mongoflow.exceptions import RepositoryError
from mongoflow.utils import convert_object_id, serialize_document


class AsyncRepository(BaseRepository):
    """
    Async repository with Motor support.

    Example:
        >>> class UserRepository(AsyncRepository):
        ...     collection_name = 'users'
        ...
        >>> users = UserRepository()
        >>> user = await users.create({'name': 'John'})
        >>> all_users = await users.all()
    """

    def __init__(self, collection_name: Optional[str] = None):
        """Initialize async repository."""
        self._collection_name = collection_name or self.collection_name
        if not self._collection_name:
            raise RepositoryError("Collection name must be specified")

        self._connection = AsyncMongoFlow.get_connection(self.connection_name)
        self._database = None
        self._collection = None

    async def get_database(self):
        """Get async database instance."""
        if self._database is None:
            self._database = await self._connection.database
        return self._database

    async def get_collection(self):
        """Get async collection instance."""
        if self._collection is None:
            db = await self.get_database()
            self._collection = db[self._collection_name]
            await self._ensure_indexes()
        return self._collection

    async def _ensure_indexes(self) -> None:
        """Create indexes if they don't exist."""
        if hasattr(self, 'indexes') and self.indexes:
            collection = await self.get_collection()
            for index_spec in self.indexes:
                try:
                    await collection.create_index(**index_spec)
                except Exception:
                    pass  # Index might already exist

    def query(self) -> AsyncQueryBuilder:
        """Create async query builder."""
        # Note: This is synchronous but returns async query builder
        return AsyncQueryBuilder(self._collection)

    async def all(self) -> List[Dict[str, Any]]:
        """Get all documents."""
        collection = await self.get_collection()
        query = AsyncQueryBuilder(collection)
        return await query.get()

    async def find(self, id: Union[str, ObjectId]) -> Optional[Dict[str, Any]]:
        """Find document by ID."""
        collection = await self.get_collection()
        id = convert_object_id(id)
        doc = await collection.find_one({"_id": id})
        return serialize_document(doc) if doc else None

    async def find_by(self, **kwargs) -> Optional[Dict[str, Any]]:
        """Find single document by fields."""
        collection = await self.get_collection()
        doc = await collection.find_one(kwargs)
        return serialize_document(doc) if doc else None

    async def create(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new document."""
        try:
            collection = await self.get_collection()
            data = self._prepare_for_insert(data)
            result = await collection.insert_one(data)
            data["_id"] = str(result.inserted_id)
            return data
        except Exception as e:
            raise RepositoryError(f"Failed to create document: {e}")

    async def create_many(self, documents: List[Dict[str, Any]]) -> List[str]:
        """Create multiple documents."""
        try:
            if not documents:
                return []

            collection = await self.get_collection()
            prepared = [self._prepare_for_insert(doc) for doc in documents]
            result = await collection.insert_many(prepared)
            return [str(id) for id in result.inserted_ids]
        except Exception as e:
            raise RepositoryError(f"Failed to create documents: {e}")

    async def update(self, id: Union[str, ObjectId], data: Dict[str, Any]) -> bool:
        """Update a document by ID."""
        try:
            collection = await self.get_collection()
            id = convert_object_id(id)
            data = self._prepare_for_update(data)
            result = await collection.update_one(
                {"_id": id},
                {"$set": data}
            )
            return result.modified_count > 0
        except Exception as e:
            raise RepositoryError(f"Failed to update document: {e}")

    async def update_many(self, filter_dict: Dict[str, Any], data: Dict[str, Any]) -> int:
        """Update multiple documents."""
        try:
            collection = await self.get_collection()
            data = self._prepare_for_update(data)
            result = await collection.update_many(
                filter_dict,
                {"$set": data}
            )
            return result.modified_count
        except Exception as e:
            raise RepositoryError(f"Failed to update documents: {e}")

    async def delete(self, id: Union[str, ObjectId]) -> bool:
        """Delete a document by ID."""
        try:
            collection = await self.get_collection()
            id = convert_object_id(id)
            result = await collection.delete_one({"_id": id})
            return result.deleted_count > 0
        except Exception as e:
            raise RepositoryError(f"Failed to delete document: {e}")

    async def delete_many(self, filter_dict: Dict[str, Any]) -> int:
        """Delete multiple documents."""
        try:
            collection = await self.get_collection()
            result = await collection.delete_many(filter_dict)
            return result.deleted_count
        except Exception as e:
            raise RepositoryError(f"Failed to delete documents: {e}")

    async def count(self, filter_dict: Optional[Dict[str, Any]] = None) -> int:
        """Count documents."""
        collection = await self.get_collection()
        if not filter_dict:
            return await collection.estimated_document_count()
        return await collection.count_documents(filter_dict)

    async def find_or_create(
        self,
        filter_dict: Dict[str, Any],
        defaults: Optional[Dict[str, Any]] = None
    ) -> Tuple[Dict[str, Any], bool]:
        """Find or create a document."""
        try:
            collection = await self.get_collection()

            # Try to find first
            document = await collection.find_one(filter_dict)

            if document:
                return serialize_document(document), False

            # Not found, create new
            new_data = {**filter_dict, **(defaults or {})}
            new_data = self._prepare_for_insert(new_data)
            result = await collection.insert_one(new_data)
            new_data["_id"] = str(result.inserted_id)

            return new_data, True
        except Exception as e:
            raise RepositoryError(f"Failed in find_or_create: {e}")

    async def bulk_write(self, operations: List[Any]) -> Dict[str, int]:
        """Execute bulk write operations."""
        try:
            if not operations:
                return {"inserted": 0, "updated": 0, "deleted": 0}

            collection = await self.get_collection()
            result = await collection.bulk_write(operations)

            return {
                "inserted": result.inserted_count,
                "updated": result.modified_count,
                "deleted": result.deleted_count,
                "matched": result.matched_count,
            }
        except Exception as e:
            raise RepositoryError(f"Bulk write failed: {e}")

    async def aggregate(self, pipeline: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Execute aggregation pipeline."""
        try:
            collection = await self.get_collection()
            cursor = collection.aggregate(pipeline)
            results = await cursor.to_list(length=None)
            return [serialize_document(doc) for doc in results]
        except Exception as e:
            raise RepositoryError(f"Aggregation failed: {e}")

    async def truncate(self) -> bool:
        """Delete all documents in collection."""
        try:
            collection = await self.get_collection()
            result = await collection.delete_many({})
            return result.deleted_count > 0
        except Exception as e:
            raise RepositoryError(f"Failed to truncate collection: {e}")

    def _prepare_for_insert(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare document for insertion."""
        data["created_at"] = datetime.utcnow()
        data["updated_at"] = datetime.utcnow()
        return data

    def _prepare_for_update(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare document for update."""
        data["updated_at"] = datetime.utcnow()
        data.pop("_id", None)
        data.pop("created_at", None)
        return data
