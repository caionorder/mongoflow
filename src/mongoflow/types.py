"""Type definitions for MongoFlow."""

from datetime import datetime
from typing import Any, Dict, List, Optional, TypeVar, Union

from bson import ObjectId
from typing_extensions import NotRequired, TypedDict

# Generic type for models
T = TypeVar('T')

# MongoDB types
DocumentType = Dict[str, Any]
FilterType = Dict[str, Any]
ProjectionType = Optional[Dict[str, int]]
PipelineType = List[Dict[str, Any]]
UpdateType = Dict[str, Any]

# ID types
IdType = Union[str, ObjectId]

# Sort types
SortDirection = Union[int, str]  # 1/-1 or 'asc'/'desc'
SortSpec = List[tuple[str, SortDirection]]

# Index types
IndexSpec = Union[str, List[tuple[str, int]]]


class PaginationResult(TypedDict):
    """Pagination result type."""
    items: List[DocumentType]
    total: int
    page: int
    per_page: int
    pages: int
    has_next: bool
    has_prev: bool


class BulkWriteResult(TypedDict):
    """Bulk write operation result."""
    inserted: int
    updated: int
    deleted: int
    matched: int


class UpsertResult(TypedDict):
    """Upsert operation result."""
    matched: int
    modified: int
    upserted: NotRequired[int]


class ConnectionOptions(TypedDict, total=False):
    """MongoDB connection options."""
    maxPoolSize: int
    minPoolSize: int
    maxIdleTimeMS: int
    serverSelectionTimeoutMS: int
    connectTimeoutMS: int
    retryWrites: bool
    retryReads: bool
    w: Union[int, str]
    j: bool
    wtimeout: int


class IndexOptions(TypedDict, total=False):
    """Index creation options."""
    unique: bool
    sparse: bool
    background: bool
    expireAfterSeconds: int
    partialFilterExpression: FilterType
    collation: Dict[str, Any]


class QueryOptions(TypedDict, total=False):
    """Query execution options."""
    skip: int
    limit: int
    sort: SortSpec
    projection: ProjectionType
    hint: IndexSpec
    batch_size: int
    no_cursor_timeout: bool
    allow_partial_results: bool
    collation: Dict[str, Any]


class AggregationOptions(TypedDict, total=False):
    """Aggregation pipeline options."""
    allowDiskUse: bool
    batchSize: int
    bypassDocumentValidation: bool
    collation: Dict[str, Any]
    hint: IndexSpec
    maxTimeMS: int


class FieldDefinition(TypedDict, total=False):
    """Field definition for models."""
    type: type
    required: bool
    default: Any
    unique: bool
    index: bool
    validators: List[callable]
    min_length: int
    max_length: int
    min_value: Union[int, float]
    max_value: Union[int, float]
    choices: List[Any]
    description: str


# Timestamp types
class TimestampedDocument(TypedDict):
    """Document with timestamps."""
    created_at: datetime
    updated_at: datetime


# Soft delete types
class SoftDeletableDocument(TypedDict):
    """Document with soft delete support."""
    deleted_at: NotRequired[Optional[datetime]]
    is_deleted: NotRequired[bool]


# Versioned document types
class VersionedDocument(TypedDict):
    """Document with version control."""
    version: int
    version_history: NotRequired[List[Dict[str, Any]]]


# Cache types
CacheKey = str
CacheTTL = int

# Session types
SessionType = Any  # pymongo.client_session.ClientSession

# Transaction options
class TransactionOptions(TypedDict, total=False):
    """Transaction options."""
    readConcern: Dict[str, Any]
    writeConcern: Dict[str, Any]
    readPreference: str
    maxCommitTimeMS: int
