"""Test configuration and fixtures for MongoFlow."""

import pytest
from mongomock import MongoClient as MockMongoClient

from mongoflow import MongoFlow, Repository


@pytest.fixture
def mock_client():
    """Create a mock MongoDB client."""
    return MockMongoClient()


@pytest.fixture
def mock_db(mock_client):
    """Create a mock database."""
    return mock_client.test_db


@pytest.fixture
def mock_collection(mock_db):
    """Create a mock collection."""
    return mock_db.test_collection


@pytest.fixture(autouse=True)
def setup_mongoflow(monkeypatch, mock_client):
    """Set up MongoFlow with mock client."""
    def mock_connect(*args, **kwargs):
        instance = MongoFlow(
            uri="mongodb://localhost:27017",
            database="test_db",
            connection_name="default"
        )
        instance._client = mock_client
        instance._database = mock_client.test_db
        MongoFlow._instances["default"] = instance
        MongoFlow._default_connection = "default"
        return instance

    monkeypatch.setattr(MongoFlow, "connect", mock_connect)

    # Connect for tests
    MongoFlow.connect()


@pytest.fixture
def user_repository():
    """Create a test user repository."""
    class UserRepository(Repository):
        collection_name = "users"

    return UserRepository()


@pytest.fixture
def sample_users():
    """Sample user data for testing."""
    return [
        {"name": "John Doe", "email": "john@example.com", "age": 30, "status": "active"},
        {"name": "Jane Smith", "email": "jane@example.com", "age": 25, "status": "active"},
        {"name": "Bob Wilson", "email": "bob@example.com", "age": 35, "status": "inactive"},
        {"name": "Alice Brown", "email": "alice@example.com", "age": 28, "status": "active"},
        {"name": "Charlie Davis", "email": "charlie@example.com", "age": 45, "status": "inactive"},
    ]
