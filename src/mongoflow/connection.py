"""MongoDB connection management for MongoFlow."""

import os
from typing import Dict, Optional
from urllib.parse import quote_plus

from pymongo import MongoClient
from pymongo.database import Database
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError

from mongoflow.exceptions import ConnectionError


class MongoFlow:
    """
    MongoDB connection manager with connection pooling and multi-database support.

    Example:
        >>> MongoFlow.connect('mongodb://localhost:27017', 'mydb')
        >>> db = MongoFlow.get_database()
    """

    _instances: Dict[str, "MongoFlow"] = {}
    _default_connection: Optional[str] = None

    def __init__(
        self,
        uri: Optional[str] = None,
        database: Optional[str] = None,
        connection_name: str = "default",
        **options
    ):
        """
        Initialize MongoDB connection.

        Args:
            uri: MongoDB connection URI
            database: Database name
            connection_name: Connection identifier for multiple connections
            **options: Additional PyMongo connection options
        """
        self.uri = uri or os.getenv("MONGOFLOW_URI", "mongodb://localhost:27017")
        self.database_name = database or os.getenv("MONGOFLOW_DATABASE", "mongoflow_db")
        self.connection_name = connection_name
        self.options = options

        # Connection pool settings
        self.options.setdefault("maxPoolSize", 100)
        self.options.setdefault("minPoolSize", 10)
        self.options.setdefault("maxIdleTimeMS", 60000)
        self.options.setdefault("serverSelectionTimeoutMS", 5000)
        self.options.setdefault("connectTimeoutMS", 10000)
        self.options.setdefault("retryWrites", True)

        self._client: Optional[MongoClient] = None
        self._database: Optional[Database] = None

    @classmethod
    def connect(
        cls,
        uri: Optional[str] = None,
        database: Optional[str] = None,
        connection_name: str = "default",
        username: Optional[str] = None,
        password: Optional[str] = None,
        set_as_default: bool = True,
        **options
    ) -> "MongoFlow":
        """
        Create and register a MongoDB connection.

        Args:
            uri: MongoDB URI (can be None if using username/password)
            database: Database name
            connection_name: Connection identifier
            username: MongoDB username (optional)
            password: MongoDB password (optional)
            set_as_default: Set this as the default connection
            **options: Additional connection options

        Returns:
            MongoFlow instance

        Example:
            >>> MongoFlow.connect('mongodb://localhost:27017', 'mydb')
            >>> # Or with auth
            >>> MongoFlow.connect(
            ...     uri='mongodb://localhost:27017',
            ...     database='mydb',
            ...     username='user',
            ...     password='pass'
            ... )
        """
        # Build URI with credentials if provided
        if username and password and uri:
            if "@" not in uri:
                # Add credentials to URI
                protocol, rest = uri.split("://", 1)
                uri = f"{protocol}://{quote_plus(username)}:{quote_plus(password)}@{rest}"

        instance = cls(uri, database, connection_name, **options)
        cls._instances[connection_name] = instance

        if set_as_default or cls._default_connection is None:
            cls._default_connection = connection_name

        # Test connection
        instance._connect()

        return instance

    @classmethod
    def get_connection(cls, name: Optional[str] = None) -> "MongoFlow":
        """Get a registered connection by name."""
        name = name or cls._default_connection
        if name not in cls._instances:
            raise ConnectionError(f"Connection '{name}' not found. Use MongoFlow.connect() first.")
        return cls._instances[name]

    @classmethod
    def disconnect(cls, name: Optional[str] = None) -> None:
        """Disconnect and remove a connection."""
        name = name or cls._default_connection
        if name in cls._instances:
            instance = cls._instances[name]
            instance.close()
            del cls._instances[name]

            if cls._default_connection == name:
                cls._default_connection = None

    @classmethod
    def get_database(cls, name: Optional[str] = None) -> Database:
        """Get database from a connection."""
        connection = cls.get_connection(name)
        return connection.database

    def _connect(self) -> MongoClient:
        """Create or return existing MongoDB client."""
        if self._client is None:
            try:
                self._client = MongoClient(self.uri, **self.options)
                # Test connection
                self._client.admin.command("ping")
            except (ConnectionFailure, ServerSelectionTimeoutError) as e:
                raise ConnectionError(f"Failed to connect to MongoDB: {e}")
        return self._client

    @property
    def client(self) -> MongoClient:
        """Get MongoDB client (lazy connection)."""
        if self._client is None:
            self._connect()
        return self._client

    @property
    def database(self) -> Database:
        """Get database instance (lazy loading)."""
        if self._database is None:
            self._database = self.client[self.database_name]
        return self._database

    def close(self) -> None:
        """Close MongoDB connection."""
        if self._client:
            self._client.close()
            self._client = None
            self._database = None
