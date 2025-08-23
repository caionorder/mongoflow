"""Async MongoDB connection management for MongoFlow."""

import os
from typing import Dict, Optional

try:
    from motor.core import AgnosticDatabase
    from motor.motor_asyncio import AsyncIOMotorClient
    HAS_MOTOR = True
except ImportError:
    HAS_MOTOR = False
    AsyncIOMotorClient = None
    AgnosticDatabase = None

from mongoflow.exceptions import ConnectionError


class AsyncMongoFlow:
    """
    Async MongoDB connection manager using Motor.

    Example:
        >>> await AsyncMongoFlow.connect('mongodb://localhost:27017', 'mydb')
        >>> db = await AsyncMongoFlow.get_database()
    """

    _instances: Dict[str, "AsyncMongoFlow"] = {}
    _default_connection: Optional[str] = None

    def __init__(
        self,
        uri: Optional[str] = None,
        database: Optional[str] = None,
        connection_name: str = "default",
        **options
    ):
        """Initialize async MongoDB connection."""
        if not HAS_MOTOR:
            raise ImportError(
                "Motor is required for async support. "
                "Install with: pip install mongoflow[async]"
            )

        self.uri = uri or os.getenv("MONGOFLOW_URI", "mongodb://localhost:27017")
        self.database_name = database or os.getenv("MONGOFLOW_DATABASE", "mongoflow_db")
        self.connection_name = connection_name
        self.options = options

        # Connection pool settings
        self.options.setdefault("maxPoolSize", 100)
        self.options.setdefault("minPoolSize", 10)
        self.options.setdefault("maxIdleTimeMS", 60000)
        self.options.setdefault("serverSelectionTimeoutMS", 5000)

        self._client: Optional[AsyncIOMotorClient] = None
        self._database: Optional[AgnosticDatabase] = None

    @classmethod
    async def connect(
        cls,
        uri: Optional[str] = None,
        database: Optional[str] = None,
        connection_name: str = "default",
        username: Optional[str] = None,
        password: Optional[str] = None,
        set_as_default: bool = True,
        **options
    ) -> "AsyncMongoFlow":
        """
        Create and register an async MongoDB connection.

        Args:
            uri: MongoDB URI
            database: Database name
            connection_name: Connection identifier
            username: MongoDB username
            password: MongoDB password
            set_as_default: Set as default connection
            **options: Additional connection options

        Returns:
            AsyncMongoFlow instance
        """
        # Build URI with credentials if provided
        if username and password and uri:
            if "@" not in uri:
                from urllib.parse import quote_plus
                protocol, rest = uri.split("://", 1)
                uri = f"{protocol}://{quote_plus(username)}:{quote_plus(password)}@{rest}"

        instance = cls(uri, database, connection_name, **options)
        cls._instances[connection_name] = instance

        if set_as_default or cls._default_connection is None:
            cls._default_connection = connection_name

        # Test connection
        await instance._connect()

        return instance

    @classmethod
    def get_connection(cls, name: Optional[str] = None) -> "AsyncMongoFlow":
        """Get a registered async connection."""
        name = name or cls._default_connection
        if name not in cls._instances:
            raise ConnectionError(f"Async connection '{name}' not found")
        return cls._instances[name]

    @classmethod
    async def disconnect(cls, name: Optional[str] = None) -> None:
        """Disconnect and remove an async connection."""
        name = name or cls._default_connection
        if name in cls._instances:
            instance = cls._instances[name]
            await instance.close()
            del cls._instances[name]

            if cls._default_connection == name:
                cls._default_connection = None

    async def _connect(self) -> AsyncIOMotorClient:
        """Create or return existing async MongoDB client."""
        if self._client is None:
            try:
                self._client = AsyncIOMotorClient(self.uri, **self.options)
                # Test connection
                await self._client.admin.command("ping")
            except Exception as e:
                raise ConnectionError(f"Failed to connect to MongoDB: {e}")
        return self._client

    @property
    async def client(self) -> AsyncIOMotorClient:
        """Get async MongoDB client."""
        if self._client is None:
            await self._connect()
        return self._client

    @property
    async def database(self) -> AgnosticDatabase:
        """Get async database instance."""
        if self._database is None:
            client = await self.client
            self._database = client[self.database_name]
        return self._database

    async def close(self) -> None:
        """Close async MongoDB connection."""
        if self._client:
            self._client.close()
            self._client = None
            self._database = None
