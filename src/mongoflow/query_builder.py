"""Fluent query builder for MongoFlow."""

from typing import Any, Dict, Generator, List, Optional, Tuple, Union

from pymongo.collection import Collection
from pymongo.cursor import Cursor

from mongoflow.exceptions import QueryError
from mongoflow.utils import serialize_document


class QueryBuilder:
    """
    Fluent query builder for MongoDB operations.

    Example:
        >>> query = QueryBuilder(collection)
        >>> results = (query
        ...     .where('age', 25, '$gte')
        ...     .where('status', 'active')
        ...     .order_by('created_at', 'desc')
        ...     .limit(10)
        ...     .get())
    """

    __slots__ = [
        "_collection",
        "_filter",
        "_projection",
        "_sort",
        "_skip_value",
        "_limit_value",
        "_hint_value",
        "_cached_count",
    ]

    def __init__(self, collection: Collection):
        """Initialize query builder with a collection."""
        self._collection = collection
        self._filter: Dict[str, Any] = {}
        self._projection: Optional[Dict[str, int]] = None
        self._sort: List[Tuple[str, int]] = []
        self._skip_value: int = 0
        self._limit_value: int = 0
        self._hint_value: Optional[Union[str, List[Tuple[str, int]]]] = None
        self._cached_count: Optional[int] = None

    def where(self, field: str, value: Any, operator: str = "$eq") -> "QueryBuilder":
        """
        Add a WHERE condition.

        Args:
            field: Field name
            value: Value to compare
            operator: MongoDB operator ($eq, $ne, $gt, $gte, $lt, $lte, etc.)

        Returns:
            Self for chaining

        Example:
            >>> query.where('age', 18, '$gte').where('status', 'active')
        """
        if operator == "$eq":
            self._filter[field] = value
        else:
            if field not in self._filter:
                self._filter[field] = {}
            self._filter[field][operator] = value

        self._cached_count = None  # Invalidate cache
        return self

    def where_in(self, field: str, values: List[Any]) -> "QueryBuilder":
        """Filter where field value is in list."""
        self._filter[field] = {"$in": values}
        self._cached_count = None
        return self

    def where_not_in(self, field: str, values: List[Any]) -> "QueryBuilder":
        """Filter where field value is not in list."""
        self._filter[field] = {"$nin": values}
        self._cached_count = None
        return self

    def where_between(self, field: str, start: Any, end: Any) -> "QueryBuilder":
        """Filter where field value is between two values (inclusive)."""
        self._filter[field] = {"$gte": start, "$lte": end}
        self._cached_count = None
        return self

    def where_greater_than(self, field: str, value: Any) -> "QueryBuilder":
        """Filter where field value is greater than."""
        self._filter[field] = {"$gt": value}
        self._cached_count = None
        return self

    def where_less_than(self, field: str, value: Any) -> "QueryBuilder":
        """Filter where field value is less than."""
        self._filter[field] = {"$lt": value}
        self._cached_count = None
        return self

    def where_like(self, field: str, pattern: str, case_sensitive: bool = False) -> "QueryBuilder":
        """
        Filter using regex pattern (like SQL LIKE).

        Args:
            field: Field name
            pattern: Regex pattern
            case_sensitive: Whether to match case

        Returns:
            Self for chaining
        """
        options = "" if case_sensitive else "i"
        self._filter[field] = {"$regex": pattern, "$options": options}
        self._cached_count = None
        return self

    def where_null(self, field: str) -> "QueryBuilder":
        """Filter where field is null."""
        self._filter[field] = None
        self._cached_count = None
        return self

    def where_not_null(self, field: str) -> "QueryBuilder":
        """Filter where field is not null."""
        self._filter[field] = {"$ne": None}
        self._cached_count = None
        return self

    def where_exists(self, field: str, exists: bool = True) -> "QueryBuilder":
        """Filter where field exists or not."""
        self._filter[field] = {"$exists": exists}
        self._cached_count = None
        return self

    def or_where(self, conditions: List[Dict[str, Any]]) -> "QueryBuilder":
        """
        Add OR conditions.

        Example:
            >>> query.or_where([
            ...     {'status': 'active'},
            ...     {'role': 'admin'}
            ... ])
        """
        if "$or" in self._filter:
            self._filter["$or"].extend(conditions)
        else:
            self._filter["$or"] = conditions
        self._cached_count = None
        return self

    def and_where(self, conditions: List[Dict[str, Any]]) -> "QueryBuilder":
        """Add AND conditions."""
        if "$and" in self._filter:
            self._filter["$and"].extend(conditions)
        else:
            self._filter["$and"] = conditions
        self._cached_count = None
        return self

    def select(self, *fields: str) -> "QueryBuilder":
        """
        Select specific fields to return.

        Example:
            >>> query.select('name', 'email', 'age')
        """
        if self._projection is None:
            self._projection = {}
        for field in fields:
            self._projection[field] = 1
        return self

    def exclude(self, *fields: str) -> "QueryBuilder":
        """
        Exclude specific fields from results.

        Example:
            >>> query.exclude('password', 'secret_key')
        """
        if self._projection is None:
            self._projection = {}
        for field in fields:
            self._projection[field] = 0
        return self

    def order_by(self, field: str, direction: str = "asc") -> "QueryBuilder":
        """
        Add ORDER BY clause.

        Args:
            field: Field to sort by
            direction: 'asc' or 'desc'

        Returns:
            Self for chaining
        """
        sort_direction = 1 if direction.lower() == "asc" else -1
        self._sort.append((field, sort_direction))
        return self

    def skip(self, value: int) -> "QueryBuilder":
        """Skip N documents (for pagination)."""
        self._skip_value = value
        return self

    def limit(self, value: int) -> "QueryBuilder":
        """Limit number of documents returned."""
        self._limit_value = value
        return self

    def hint(self, index: Union[str, List[Tuple[str, int]]]) -> "QueryBuilder":
        """Provide index hint for query optimization."""
        self._hint_value = index
        return self

    def get(self) -> List[Dict[str, Any]]:
        """
        Execute query and return all matching documents.

        Returns:
            List of documents
        """
        try:
            cursor = self._build_cursor()
            documents = list(cursor)
            return [serialize_document(doc) for doc in documents]
        except Exception as e:
            raise QueryError(f"Query execution failed: {e}")

    def first(self) -> Optional[Dict[str, Any]]:
        """
        Get first matching document.

        Returns:
            Document or None if not found
        """
        self._limit_value = 1
        results = self.get()
        return results[0] if results else None

    def last(self) -> Optional[Dict[str, Any]]:
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

        result = self.first()
        self._sort = original_sort  # Restore original sort
        return result

    def count(self) -> int:
        """
        Count matching documents.

        Returns:
            Number of documents
        """
        if self._cached_count is not None:
            return self._cached_count

        try:
            if not self._filter:
                # Use estimated count for better performance
                count = self._collection.estimated_document_count()
            else:
                count = self._collection.count_documents(self._filter)

            self._cached_count = count
            return count
        except Exception as e:
            raise QueryError(f"Count failed: {e}")

    def exists(self) -> bool:
        """Check if any matching documents exist."""
        return self.count() > 0

    def distinct(self, field: str) -> List[Any]:
        """
        Get distinct values for a field.

        Args:
            field: Field name

        Returns:
            List of distinct values
        """
        try:
            return self._collection.distinct(field, self._filter)
        except Exception as e:
            raise QueryError(f"Distinct query failed: {e}")

    def stream(self, batch_size: int = 100) -> Generator[Dict[str, Any], None, None]:
        """
        Stream results for memory efficiency.

        Args:
            batch_size: Number of documents per batch

        Yields:
            Documents one by one

        Example:
            >>> for doc in query.stream(batch_size=500):
            ...     process(doc)
        """
        cursor = self._build_cursor()
        cursor.batch_size(batch_size)

        for document in cursor:
            yield serialize_document(document)

    def paginate(self, page: int = 1, per_page: int = 20) -> Dict[str, Any]:
        """
        Get paginated results.

        Args:
            page: Page number (1-based)
            per_page: Items per page

        Returns:
            Dictionary with pagination info

        Example:
            >>> result = query.paginate(page=2, per_page=20)
            >>> result['items']  # Documents
            >>> result['total']  # Total count
            >>> result['pages']  # Total pages
        """
        skip_value = (page - 1) * per_page

        # Get items
        self.skip(skip_value).limit(per_page)
        items = self.get()

        # Get total count
        total = self.count()

        return {
            "items": items,
            "total": total,
            "page": page,
            "per_page": per_page,
            "pages": (total + per_page - 1) // per_page if per_page > 0 else 0,
            "has_next": page * per_page < total,
            "has_prev": page > 1,
        }

    def aggregate(self, pipeline: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Execute aggregation pipeline.

        Args:
            pipeline: MongoDB aggregation pipeline

        Returns:
            List of aggregation results
        """
        try:
            # Add match stage if filter exists
            if self._filter:
                pipeline = [{"$match": self._filter}] + pipeline

            results = list(self._collection.aggregate(pipeline))
            return [serialize_document(doc) for doc in results]
        except Exception as e:
            raise QueryError(f"Aggregation failed: {e}")

    def sum(self, field: str) -> Union[int, float]:
        """Calculate sum of a field."""
        pipeline = [
            {"$group": {"_id": None, "total": {"$sum": f"${field}"}}}
        ]
        results = self.aggregate(pipeline)
        return results[0]["total"] if results else 0

    def avg(self, field: str) -> Union[int, float]:
        """Calculate average of a field."""
        pipeline = [
            {"$group": {"_id": None, "average": {"$avg": f"${field}"}}}
        ]
        results = self.aggregate(pipeline)
        return results[0]["average"] if results else 0

    def min(self, field: str) -> Any:
        """Find minimum value of a field."""
        pipeline = [
            {"$group": {"_id": None, "minimum": {"$min": f"${field}"}}}
        ]
        results = self.aggregate(pipeline)
        return results[0]["minimum"] if results else None

    def max(self, field: str) -> Any:
        """Find maximum value of a field."""
        pipeline = [
            {"$group": {"_id": None, "maximum": {"$max": f"${field}"}}}
        ]
        results = self.aggregate(pipeline)
        return results[0]["maximum"] if results else None

    def _build_cursor(self) -> Cursor:
        """Build MongoDB cursor with all query parameters."""
        cursor = self._collection.find(self._filter, self._projection)

        if self._hint_value:
            cursor = cursor.hint(self._hint_value)

        if self._sort:
            cursor = cursor.sort(self._sort)

        if self._skip_value > 0:
            cursor = cursor.skip(self._skip_value)

        if self._limit_value > 0:
            cursor = cursor.limit(self._limit_value)

        return cursor

    def __repr__(self) -> str:
        """String representation of query."""
        return (
            f"QueryBuilder(filter={self._filter}, "
            f"sort={self._sort}, skip={self._skip_value}, "
            f"limit={self._limit_value})"
        )
