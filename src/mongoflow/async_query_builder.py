"""Async query builder for MongoFlow."""

from typing import Any, AsyncGenerator, Dict, List, Optional, Tuple, Union

from mongoflow.exceptions import QueryError
from mongoflow.utils import serialize_document


class AsyncQueryBuilder:
    """
    Async query builder for MongoDB operations.

    Example:
        >>> query = AsyncQueryBuilder(collection)
        >>> results = await query.where('age', 25).get()
    """

    def __init__(self, collection):
        """Initialize async query builder."""
        self._collection = collection
        self._filter: Dict[str, Any] = {}
        self._projection: Optional[Dict[str, int]] = None
        self._sort: List[Tuple[str, int]] = []
        self._skip_value: int = 0
        self._limit_value: int = 0
        self._hint_value: Optional[Union[str, List[Tuple[str, int]]]] = None

    def where(self, field: str, value: Any, operator: str = "$eq") -> "AsyncQueryBuilder":
        """Add WHERE condition."""
        if operator == "$eq":
            self._filter[field] = value
        else:
            if field not in self._filter:
                self._filter[field] = {}
            self._filter[field][operator] = value
        return self

    def where_in(self, field: str, values: List[Any]) -> "AsyncQueryBuilder":
        """Filter where field value is in list."""
        self._filter[field] = {"$in": values}
        return self

    def where_not_in(self, field: str, values: List[Any]) -> "AsyncQueryBuilder":
        """Filter where field value is not in list."""
        self._filter[field] = {"$nin": values}
        return self

    def where_between(self, field: str, start: Any, end: Any) -> "AsyncQueryBuilder":
        """Filter where field value is between two values."""
        self._filter[field] = {"$gte": start, "$lte": end}
        return self

    def where_greater_than(self, field: str, value: Any) -> "AsyncQueryBuilder":
        """Filter where field value is greater than."""
        self._filter[field] = {"$gt": value}
        return self

    def where_less_than(self, field: str, value: Any) -> "AsyncQueryBuilder":
        """Filter where field value is less than."""
        self._filter[field] = {"$lt": value}
        return self

    def where_like(self, field: str, pattern: str, case_sensitive: bool = False) -> "AsyncQueryBuilder":
        """Filter using regex pattern."""
        options = "" if case_sensitive else "i"
        self._filter[field] = {"$regex": pattern, "$options": options}
        return self

    def where_null(self, field: str) -> "AsyncQueryBuilder":
        """Filter where field is null."""
        self._filter[field] = None
        return self

    def where_not_null(self, field: str) -> "AsyncQueryBuilder":
        """Filter where field is not null."""
        self._filter[field] = {"$ne": None}
        return self

    def where_exists(self, field: str, exists: bool = True) -> "AsyncQueryBuilder":
        """Filter where field exists or not."""
        self._filter[field] = {"$exists": exists}
        return self

    def or_where(self, conditions: List[Dict[str, Any]]) -> "AsyncQueryBuilder":
        """Add OR conditions."""
        if "$or" in self._filter:
            self._filter["$or"].extend(conditions)
        else:
            self._filter["$or"] = conditions
        return self

    def and_where(self, conditions: List[Dict[str, Any]]) -> "AsyncQueryBuilder":
        """Add AND conditions."""
        if "$and" in self._filter:
            self._filter["$and"].extend(conditions)
        else:
            self._filter["$and"] = conditions
        return self

    def select(self, *fields: str) -> "AsyncQueryBuilder":
        """Select specific fields."""
        if self._projection is None:
            self._projection = {}
        for field in fields:
            self._projection[field] = 1
        return self

    def exclude(self, *fields: str) -> "AsyncQueryBuilder":
        """Exclude specific fields."""
        if self._projection is None:
            self._projection = {}
        for field in fields:
            self._projection[field] = 0
        return self

    def order_by(self, field: str, direction: str = "asc") -> "AsyncQueryBuilder":
        """Add ORDER BY clause."""
        sort_direction = 1 if direction.lower() == "asc" else -1
        self._sort.append((field, sort_direction))
        return self

    def skip(self, value: int) -> "AsyncQueryBuilder":
        """Skip N documents."""
        self._skip_value = value
        return self

    def limit(self, value: int) -> "AsyncQueryBuilder":
        """Limit number of documents."""
        self._limit_value = value
        return self

    def hint(self, index: Union[str, List[Tuple[str, int]]]) -> "AsyncQueryBuilder":
        """Provide index hint."""
        self._hint_value = index
        return self

    async def get(self) -> List[Dict[str, Any]]:
        """Execute query and return all matching documents."""
        try:
            cursor = self._collection.find(self._filter, self._projection)

            if self._hint_value:
                cursor = cursor.hint(self._hint_value)

            if self._sort:
                cursor = cursor.sort(self._sort)

            if self._skip_value > 0:
                cursor = cursor.skip(self._skip_value)

            if self._limit_value > 0:
                cursor = cursor.limit(self._limit_value)

            documents = await cursor.to_list(length=None)
            return [serialize_document(doc) for doc in documents]
        except Exception as e:
            raise QueryError(f"Async query execution failed: {e}")

    async def first(self) -> Optional[Dict[str, Any]]:
        """Get first matching document."""
        self._limit_value = 1
        results = await self.get()
        return results[0] if results else None

    async def last(self) -> Optional[Dict[str, Any]]:
        """
        Get last matching document (based on current sort).

        Returns:
            Document or None if not found
        """
        # Reverse the sort order
        original_sort = self._sort.copy()
        self._sort = [(field, -direction) for field, direction in self._sort]

        if not self._sort:
            # If no sort specified, sort by _id desc to get last inserted
            self._sort = [("_id", -1)]

        result = await self.first()
        self._sort = original_sort  # Restore original sort
        return result

    async def count(self) -> int:
        """Count matching documents."""
        try:
            if not self._filter:
                # Use estimated count for better performance
                count = await self._collection.estimated_document_count()
            else:
                count = await self._collection.count_documents(self._filter)
            return count
        except Exception as e:
            raise QueryError(f"Async count failed: {e}")

    async def exists(self) -> bool:
        """Check if any matching documents exist."""
        count = await self.count()
        return count > 0

    async def distinct(self, field: str) -> List[Any]:
        """Get distinct values for a field."""
        try:
            return await self._collection.distinct(field, self._filter)
        except Exception as e:
            raise QueryError(f"Async distinct query failed: {e}")

    async def stream(self, batch_size: int = 100) -> AsyncGenerator[Dict[str, Any], None]:
        """Stream results for memory efficiency."""
        cursor = self._collection.find(self._filter, self._projection)

        if self._hint_value:
            cursor = cursor.hint(self._hint_value)

        if self._sort:
            cursor = cursor.sort(self._sort)

        if self._skip_value > 0:
            cursor = cursor.skip(self._skip_value)

        if self._limit_value > 0:
            cursor = cursor.limit(self._limit_value)

        cursor = cursor.batch_size(batch_size)

        async for document in cursor:
            yield serialize_document(document)

    async def paginate(self, page: int = 1, per_page: int = 20) -> Dict[str, Any]:
        """Get paginated results."""
        skip_value = (page - 1) * per_page

        # Get items
        self.skip(skip_value).limit(per_page)
        items = await self.get()

        # Get total count
        total = await self.count()

        return {
            "items": items,
            "total": total,
            "page": page,
            "per_page": per_page,
            "pages": (total + per_page - 1) // per_page if per_page > 0 else 0,
            "has_next": page * per_page < total,
            "has_prev": page > 1,
        }

    async def aggregate(self, pipeline: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Execute aggregation pipeline."""
        try:
            if self._filter:
                pipeline = [{"$match": self._filter}] + pipeline

            cursor = self._collection.aggregate(pipeline)
            results = await cursor.to_list(length=None)
            return [serialize_document(doc) for doc in results]
        except Exception as e:
            raise QueryError(f"Async aggregation failed: {e}")

    async def sum(self, field: str) -> Union[int, float]:
        """Calculate sum of a field."""
        pipeline = [
            {"$group": {"_id": None, "total": {"$sum": f"${field}"}}}
        ]
        results = await self.aggregate(pipeline)
        return results[0]["total"] if results else 0

    async def avg(self, field: str) -> Union[int, float]:
        """Calculate average of a field."""
        pipeline = [
            {"$group": {"_id": None, "average": {"$avg": f"${field}"}}}
        ]
        results = await self.aggregate(pipeline)
        return results[0]["average"] if results else 0

    async def min(self, field: str) -> Any:
        """Find minimum value of a field."""
        pipeline = [
            {"$group": {"_id": None, "minimum": {"$min": f"${field}"}}}
        ]
        results = await self.aggregate(pipeline)
        return results[0]["minimum"] if results else None

    async def max(self, field: str) -> Any:
        """Find maximum value of a field."""
        pipeline = [
            {"$group": {"_id": None, "maximum": {"$max": f"${field}"}}}
        ]
        results = await self.aggregate(pipeline)
        return results[0]["maximum"] if results else None

    async def group(self, group_by: Union[str, Dict[str, Any]], accumulators: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Group documents by field(s) and apply aggregation functions.

        Args:
            group_by: Field name or dict for grouping
            accumulators: Dict of field names to accumulator expressions

        Returns:
            List of grouped results

        Example:
            >>> # Group by status and count
            >>> await query.group('status', {'count': {'$sum': 1}})
            
            >>> # Group by multiple fields
            >>> await query.group({'status': '$status', 'category': '$category'}, 
            ...                   {'total': {'$sum': '$amount'}})
        """
        if isinstance(group_by, str):
            group_id = f"${group_by}"
        else:
            group_id = group_by

        group_stage = {"_id": group_id}
        group_stage.update(accumulators)

        pipeline = [{"$group": group_stage}]
        return await self.aggregate(pipeline)
