import pytest
import pytest_asyncio
from wiremongo import WireMongo


@pytest_asyncio.fixture
async def wiremongo():
    wire = WireMongo()
    yield wire
    wire.reset()


@pytest_asyncio.fixture
async def wiremongo():
    wire = WireMongo()
    yield wire
    wire.reset()


@pytest.mark.asyncio
async def test_database_command_operation():
    """Test database command operation works with MockDatabase"""
    from wiremongo import MockDatabase
    
    db = MockDatabase(name="test_db")
    
    # Set up the mock to return a specific value
    db.command.return_value = {"ok": 1, "result": "pong"}
    
    # Test that the mock works
    result = await db.command("ping")
    assert result == {"ok": 1, "result": "pong"}
    db.command.assert_called_once_with("ping")


@pytest.mark.asyncio
async def test_database_create_collection():
    """Test database create_collection operation works with MockDatabase"""
    from wiremongo import MockDatabase
    
    db = MockDatabase(name="test_db")
    
    # Set up the mock to return a specific value
    db.create_collection.return_value = {"name": "new_collection"}
    
    # Test that the mock works
    result = await db.create_collection("new_collection")
    assert result == {"name": "new_collection"}
    db.create_collection.assert_called_once_with("new_collection")


@pytest.mark.asyncio
async def test_database_drop_collection():
    """Test database drop_collection operation works with MockDatabase"""
    from wiremongo import MockDatabase
    
    db = MockDatabase(name="test_db")
    
    # Set up the mock to return a specific value
    db.drop_collection.return_value = {"dropped": "old_collection"}
    
    # Test that the mock works
    result = await db.drop_collection("old_collection")
    assert result == {"dropped": "old_collection"}
    db.drop_collection.assert_called_once_with("old_collection")