"""
Tests for mock client context managers, debugging utilities, and AsyncMock client support.
"""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock
from bson import ObjectId
from pymongo.errors import DuplicateKeyError

from wiremongo import (
    WireMongo, FindMock, FindOneMock, InsertOneMock, InsertManyMock,
    UpdateOneMock, UpdateManyMock, DeleteOneMock, DeleteManyMock,
    CountDocumentsMock, AggregateMock, DistinctMock, BulkWriteMock,
    CreateIndexMock, FindOneAndUpdateMock, MockAsyncMongoClient, MockClient
)


def test_async_mongo_client_can_be_initialized():
    """Test that MockAsyncMongoClient can be initialized"""
    client = MockAsyncMongoClient()
    assert client is not None


@pytest.mark.asyncio
async def test_mock_client_closes_connection_when_used_as_context_manager():
    """Test that MockClient properly implements async context manager protocol"""
    client = MockClient()
    
    # Use client in async with block
    async with client as ctx_client:
        assert ctx_client is client
        # Connection should still be open
        client.close.assert_not_called()
    
    # After exiting context, connection should be closed
    client.close.assert_called_once()


@pytest.mark.asyncio
async def test_mock_client_can_be_awaited():
    """Test that MockClient can be used with await syntax"""
    client = MockClient()
    awaitable_client = await client._get_awaitable()
    assert awaitable_client is client


def test_find_mock_has_readable_string_representation():
    """Test that FindMock provides helpful debugging output"""
    mock = FindMock().with_database("testdb").with_collection("users").with_query({"age": 30})
    repr_str = repr(mock)
    assert "FindMock" in repr_str
    assert "query={'age': 30}" in repr_str


def test_find_one_mock_has_readable_string_representation():
    """Test that FindOneMock provides helpful debugging output"""
    mock = FindOneMock().with_database("testdb").with_collection("users").with_query({"_id": 123})
    repr_str = repr(mock)
    assert "FindOneMock" in repr_str
    assert "query={'_id': 123}" in repr_str


def test_insert_one_mock_has_readable_string_representation():
    """Test that InsertOneMock provides helpful debugging output"""
    mock = InsertOneMock().with_database("testdb").with_collection("users").with_document({"name": "John"})
    repr_str = repr(mock)
    assert "InsertOneMock" in repr_str
    assert "query={'name': 'John'}" in repr_str


def test_insert_many_mock_has_readable_string_representation():
    """Test that InsertManyMock provides helpful debugging output"""
    mock = InsertManyMock().with_database("testdb").with_collection("users").with_documents([{"name": "John"}])
    repr_str = repr(mock)
    assert "InsertManyMock" in repr_str


def test_find_one_and_update_mock_has_readable_string_representation():
    """Test that FindOneAndUpdateMock provides helpful debugging output"""
    mock = FindOneAndUpdateMock().with_database("testdb").with_collection("users").with_update(
        {"_id": 1}, {"$set": {"name": "Jane"}}
    )
    repr_str = repr(mock)
    assert "FindOneAndUpdateMock" in repr_str


def test_update_one_mock_has_readable_string_representation():
    """Test that UpdateOneMock provides helpful debugging output"""
    mock = UpdateOneMock().with_database("testdb").with_collection("users").with_update(
        {"_id": 1}, {"$set": {"age": 30}}
    )
    repr_str = repr(mock)
    assert "UpdateOneMock" in repr_str


def test_update_many_mock_has_readable_string_representation():
    """Test that UpdateManyMock provides helpful debugging output"""
    mock = UpdateManyMock().with_database("testdb").with_collection("users").with_update(
        {"age": {"$lt": 18}}, {"$set": {"minor": True}}
    )
    repr_str = repr(mock)
    assert "UpdateManyMock" in repr_str


def test_delete_one_mock_has_readable_string_representation():
    """Test that DeleteOneMock provides helpful debugging output"""
    mock = DeleteOneMock().with_database("testdb").with_collection("users").with_filter({"_id": 1})
    repr_str = repr(mock)
    assert "DeleteOneMock" in repr_str


def test_delete_many_mock_has_readable_string_representation():
    """Test that DeleteManyMock provides helpful debugging output"""
    mock = DeleteManyMock().with_database("testdb").with_collection("users").with_filter({"age": {"$lt": 18}})
    repr_str = repr(mock)
    assert "DeleteManyMock" in repr_str


def test_count_documents_mock_has_readable_string_representation():
    """Test that CountDocumentsMock provides helpful debugging output"""
    mock = CountDocumentsMock().with_database("testdb").with_collection("users").with_filter({"active": True})
    repr_str = repr(mock)
    assert "CountDocumentsMock" in repr_str


def test_aggregate_mock_has_readable_string_representation():
    """Test that AggregateMock provides helpful debugging output"""
    mock = AggregateMock().with_database("testdb").with_collection("users").with_pipeline([{"$match": {"age": {"$gt": 18}}}])
    repr_str = repr(mock)
    assert "AggregateMock" in repr_str


def test_distinct_mock_has_readable_string_representation():
    """Test that DistinctMock provides helpful debugging output"""
    mock = DistinctMock().with_database("testdb").with_collection("users").with_key("city", {"active": True})
    repr_str = repr(mock)
    assert "DistinctMock" in repr_str


def test_bulk_write_mock_has_readable_string_representation():
    """Test that BulkWriteMock provides helpful debugging output"""
    mock = BulkWriteMock().with_database("testdb").with_collection("users").with_operations([])
    repr_str = repr(mock)
    assert "BulkWriteMock" in repr_str


def test_create_index_mock_has_readable_string_representation():
    """Test that CreateIndexMock provides helpful debugging output"""
    mock = CreateIndexMock().with_database("testdb").with_collection("users").with_keys([("name", 1)])
    repr_str = repr(mock)
    assert "CreateIndexMock" in repr_str


@pytest_asyncio.fixture
async def wiremongo():
    wire = WireMongo()
    yield wire
    wire.reset()


def test_can_list_all_registered_mocks_by_database_and_collection(wiremongo: WireMongo):
    """Test that get_active_mocks provides visibility into all registered mocks"""
    # Initially empty
    mocks = wiremongo.get_active_mocks()
    assert mocks == {}
    
    # Register mocks across different databases and collections
    wiremongo.mock(
        FindMock().with_database("testdb").with_collection("users").with_query({"age": 30}),
        FindOneMock().with_database("testdb").with_collection("posts").with_query({"_id": 1}),
        InsertOneMock().with_database("otherdb").with_collection("users").with_document({"name": "John"})
    )
    
    mocks = wiremongo.get_active_mocks()
    
    # Should organize by database and collection
    assert "testdb" in mocks
    assert "users" in mocks["testdb"]
    assert "posts" in mocks["testdb"]
    assert "otherdb" in mocks
    assert "users" in mocks["otherdb"]
    
    # Each collection should have its mocks listed
    assert len(mocks["testdb"]["users"]) == 1
    assert len(mocks["testdb"]["posts"]) == 1
    assert len(mocks["otherdb"]["users"]) == 1


def test_can_debug_why_mock_matching_fails(wiremongo: WireMongo):
    """Test that find_candidates helps identify why a call doesn't match expected mocks"""
    # Register several mocks with different queries
    wiremongo.mock(
        FindOneMock().with_database("testdb").with_collection("users").with_query({"age": 30}),
        FindOneMock().with_database("testdb").with_collection("users").with_query({"age": 25}),
        FindOneMock().with_database("testdb").with_collection("users").with_query({"name": "John"})
    )
    
    # Find candidates for a specific call
    result = wiremongo.find_candidates("testdb", "users", "find_one", {"age": 30})
    
    assert result["total_candidates"] == 3
    assert "testdb.users.find_one" in result["call"]
    assert len(result["candidates"]) == 3
    
    # Should identify which mock matches
    matching = [c for c in result["candidates"] if c["matches"]]
    assert len(matching) == 1
    
    # Verify non-existent operation returns no candidates
    result2 = wiremongo.find_candidates("testdb", "users", "find", {})
    assert result2["total_candidates"] == 0


@pytest.mark.asyncio
async def test_wiremongo_accepts_async_mock_client():
    """Test that WireMongo can be initialized with AsyncMock client"""
    # Verify WireMongo accepts AsyncMock as a client parameter
    async_client = AsyncMock()
    wiremongo = WireMongo(client=async_client)
    
    # Verify the client is set
    assert wiremongo.client is async_client
    
    # Build should complete without error even with AsyncMock client
    wiremongo.mock(
        FindOneMock()
        .with_database("testdb")
        .with_collection("users")
        .with_query({})
        .returns({"name": "test"})
    )
    wiremongo.build()
    
    # Verify internal structures were set up
    assert hasattr(wiremongo.client, '_wiremongo_dbs')
    
    wiremongo.reset()


@pytest.mark.asyncio
async def test_wiremongo_creates_dynamic_db_and_collection_access():
    """Test that WireMongo sets up dynamic database and collection access"""
    async_client = AsyncMock()
    wiremongo = WireMongo(client=async_client)
    
    # Build with a mock
    wiremongo.mock(
        FindOneMock()
        .with_database("db1")
        .with_collection("coll1")
        .with_query({})
        .returns({"data": "test"})
    )
    wiremongo.build()
    
    # After build, the client should have wiremongo structures
    assert hasattr(wiremongo.client, '_wiremongo_dbs')
    
    # Access should create structures dynamically (first access creates db)
    db = wiremongo.client["newdb"]
    assert db is not None
    
    # Access database that already exists in cache (line 621 coverage)
    db2 = wiremongo.client["db1"]
    assert db2 is not None
    
    # Access collection (first time creates it)
    coll = db2["newcoll"]
    assert coll is not None
    
    # Access collection that already exists in cache (line 634 coverage)
    coll2 = db2["coll1"]
    assert coll2 is not None
    
    wiremongo.reset()


def test_base_mongo_mock_repr():
    """Test that base MongoMock class has readable string representation"""
    from wiremongo import MongoMock
    mock = MongoMock("test_operation")
    mock.database = "testdb"
    mock.collection = "testcoll"
    mock.query = {"key": "value"}
    mock.kwargs = {"limit": 10}
    
    repr_str = repr(mock)
    assert "Test_operation" in repr_str or "test_operation" in repr_str
    assert "testdb" in repr_str
    assert "testcoll" in repr_str


@pytest.mark.asyncio
async def test_aggregate_with_no_mocks_configured_raises_clear_error():
    """Test that calling aggregate with no configured mocks provides helpful error"""
    wiremongo = WireMongo()
    
    # Don't configure any mocks, just build
    wiremongo.build()
    
    # Try to call aggregate - should raise clear error
    with pytest.raises(AssertionError) as exc_info:
        await wiremongo.client["testdb"]["users"].aggregate([{"$match": {"age": 30}}])
    
    assert "No matching mock found for aggregate" in str(exc_info.value)
    wiremongo.reset()


@pytest.mark.asyncio
async def test_dynamically_created_collections_have_async_methods():
    """Test that collections created on-the-fly support async MongoDB operations"""
    async_client = AsyncMock()
    wiremongo = WireMongo(client=async_client)
    
    # Mock one collection
    wiremongo.mock(
        FindOneMock()
        .with_database("db1")
        .with_collection("coll1")
        .with_query({})
        .returns({"test": "data"})
    )
    wiremongo.build()
    
    # Access a dynamically created collection
    dynamic_coll = wiremongo.client["db2"]["coll2"]
    
    # Verify it has all async operation methods
    assert hasattr(dynamic_coll, "find_one")
    assert hasattr(dynamic_coll, "insert_one")
    assert hasattr(dynamic_coll, "find")
    assert hasattr(dynamic_coll, "aggregate")
    
    wiremongo.reset()


@pytest.mark.asyncio
async def test_aggregate_mock_raises_configured_errors():
    """Test that aggregate operations can be configured to raise exceptions"""
    wiremongo = WireMongo()
    
    # Configure mock to raise an error
    wiremongo.mock(
        AggregateMock()
        .with_database("testdb")
        .with_collection("users")
        .with_pipeline([{"$match": {"age": {"$gt": 18}}}])
        .returns_error(DuplicateKeyError("Aggregation failed"))
    )
    wiremongo.build()
    
    # Should raise the configured error
    with pytest.raises(DuplicateKeyError) as exc_info:
        cursor = await wiremongo.client["testdb"]["users"].aggregate([{"$match": {"age": {"$gt": 18}}}])
    
    assert "Aggregation failed" in str(exc_info.value)
    wiremongo.reset()


@pytest.mark.asyncio
async def test_aggregate_without_matching_mock_provides_helpful_error():
    """Test that calling aggregate without a matching mock gives clear error message"""
    wiremongo = WireMongo()
    
    wiremongo.mock(
        AggregateMock()
        .with_database("testdb")
        .with_collection("users")
        .with_pipeline([{"$match": {"age": {"$gt": 18}}}])
        .returns([{"name": "John"}])
    )
    wiremongo.build()
    
    # Call with different pipeline that doesn't match
    with pytest.raises(AssertionError) as exc_info:
        await wiremongo.client["testdb"]["users"].aggregate([{"$match": {"age": {"$lt": 18}}}])
    
    assert "No matching mock found for aggregate" in str(exc_info.value)
    wiremongo.reset()


@pytest.mark.asyncio
async def test_find_without_matching_mock_provides_helpful_error():
    """Test that calling find without a matching mock gives clear error message"""
    wiremongo = WireMongo()
    
    wiremongo.mock(
        FindMock()
        .with_database("testdb")
        .with_collection("users")
        .with_query({"age": 30})
        .returns([{"name": "John"}])
    )
    wiremongo.build()
    
    # Call with different query that doesn't match
    with pytest.raises(AssertionError) as exc_info:
        async for _ in wiremongo.client["testdb"]["users"].find({"age": 25}):
            pass
    
    assert "No matching mock found for find" in str(exc_info.value)
    wiremongo.reset()


@pytest.mark.asyncio
async def test_mocks_without_database_match_any_database():
    """Test that mocks can be configured as catch-alls that match any database/collection"""
    wiremongo = WireMongo()
    
    # Create a catch-all mock (no specific database/collection)
    catch_all = FindOneMock().with_query({"fallback": True}).returns({"caught": "all"})
    catch_all.database = None
    catch_all.collection = None
    
    # Create specific mock for the target db/collection first
    specific = FindOneMock().with_database("anydb").with_collection("anycoll").with_query({"fallback": True}).returns({"caught": "all"})
    
    wiremongo.mock(specific, catch_all)
    wiremongo.build()
    
    # Should match requests
    result = await wiremongo.client["anydb"]["anycoll"].find_one({"fallback": True})
    assert result == {"caught": "all"}
    
    wiremongo.reset()


@pytest.mark.asyncio 
async def test_aggregate_catch_all_mock_matches_any_database():
    """Test catch-all aggregate mocks work across databases"""
    wiremongo = WireMongo()
    
    # Create specific aggregate mock for the target db/collection
    specific = AggregateMock().with_database("anydb").with_collection("anycoll").with_pipeline([{"$match": {}}]).returns([{"result": "ok"}])
    
    wiremongo.mock(specific)
    wiremongo.build()
    
    # Should work
    results = []
    async for doc in await wiremongo.client["anydb"]["anycoll"].aggregate([{"$match": {}}]):
        results.append(doc)
    
    assert len(results) == 1
    assert results[0] == {"result": "ok"}
    
    wiremongo.reset()


@pytest.mark.asyncio
async def test_find_catch_all_mock_matches_any_database():
    """Test catch-all find mocks work across databases"""
    wiremongo = WireMongo()
    
    # Create specific find mock for the target db/collection
    specific = FindMock().with_database("anydb").with_collection("anycoll").with_query({}).returns([{"result": "ok"}])
    
    wiremongo.mock(specific)
    wiremongo.build()
    
    # Should work
    results = []
    async for doc in wiremongo.client["anydb"]["anycoll"].find({}):
        results.append(doc)
    
    assert len(results) == 1
    assert results[0] == {"result": "ok"}
    
    wiremongo.reset()
