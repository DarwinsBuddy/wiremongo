import pytest

from wiremongo import MockCollection, MockDatabase, MockClient


def test_mock_collection_name_attribute():
    """Test MockCollection name attribute initialization"""
    # Test with explicit name
    collection = MockCollection(name="test_collection")
    assert collection.name == "test_collection"
    
    # Test with default name
    collection = MockCollection()
    assert collection.name == "mock_collection"


def test_mock_database_name_attribute():
    """Test MockDatabase name attribute initialization"""
    # Test with explicit name
    db = MockDatabase(name="test_db")
    assert db.name == "test_db"
    
    # Test with default name
    db = MockDatabase()
    assert db.name == "mock_db"


def test_mock_database_collection_access():
    """Test MockDatabase collection access methods"""
    db = MockDatabase(name="test_db")
    
    # Test __getitem__ access
    coll1 = db["users"]
    coll2 = db["users"]
    assert coll1 is coll2  # Should return same instance
    
    # Test get_collection method
    coll3 = db.get_collection("users")
    assert coll3 is coll1


def test_mock_client_database_access():
    """Test MockClient database access methods"""
    client = MockClient()
    
    # Test __getitem__ access
    db1 = client["test_db"]
    db2 = client["test_db"]
    assert db1 is db2  # Should return same instance
    
    # Test get_database method
    db3 = client.get_database("test_db")
    assert db3 is db1


@pytest.mark.asyncio
async def test_mock_client_async_methods():
    """Test MockClient async methods work correctly"""
    client = MockClient()
    
    # Test that async methods can be called and return expected values
    client.close.return_value = "closed"
    client.server_info.return_value = {"version": "4.4.0"}
    client.list_databases.return_value = {"databases": []}
    
    close_result = await client.close()
    server_result = await client.server_info()
    db_result = await client.list_databases()
    
    assert close_result == "closed"
    assert server_result == {"version": "4.4.0"}
    assert db_result == {"databases": []}


@pytest.mark.asyncio
async def test_mock_database_async_operations():
    """Test MockDatabase async operations work correctly"""
    db = MockDatabase(name="test_db")
    
    # Test that async methods can be called and return expected values
    db.command.return_value = {"ok": 1}
    db.create_collection.return_value = {"name": "new_coll"}
    db.drop_collection.return_value = {"dropped": "old_coll"}
    
    cmd_result = await db.command("ping")
    create_result = await db.create_collection("new_coll")
    drop_result = await db.drop_collection("old_coll")
    
    assert cmd_result == {"ok": 1}
    assert create_result == {"name": "new_coll"}
    assert drop_result == {"dropped": "old_coll"}