from mongoflow import MongoFlow


def test_connection_singleton():
    """Test that connection is singleton."""
    conn1 = MongoFlow.get_connection()
    conn2 = MongoFlow.get_connection()
    assert conn1 is conn2


def test_multiple_connections():
    """Test multiple named connections."""
    MongoFlow.connect(
        uri="mongodb://localhost:27017",
        database="test_db1",
        connection_name="conn1"
    )
    MongoFlow.connect(
        uri="mongodb://localhost:27017",
        database="test_db2",
        connection_name="conn2"
    )

    conn1 = MongoFlow.get_connection("conn1")
    conn2 = MongoFlow.get_connection("conn2")

    assert conn1 is not conn2
    assert conn1.database_name == "test_db1"
    assert conn2.database_name == "test_db2"
