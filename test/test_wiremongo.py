from datetime import datetime, timezone

import pytest
import pytest_asyncio
from bson import ObjectId
from pymongo import InsertOne, UpdateOne, DeleteOne
from pymongo.errors import DuplicateKeyError, PyMongoError
from pymongo.results import InsertOneResult, UpdateResult, DeleteResult, InsertManyResult, BulkWriteResult

from wiremongo import (
    WireMongo, FindMock, FindOneMock, InsertOneMock, InsertManyMock,
    UpdateOneMock, UpdateManyMock, DeleteOneMock, DeleteManyMock,
    CountDocumentsMock, AggregateMock, DistinctMock, BulkWriteMock,
    CreateIndexMock
)


@pytest_asyncio.fixture
async def wiremongo():
    wire = WireMongo()
    yield wire
    wire.reset()

@pytest.mark.asyncio
async def test_find_operation(wiremongo: WireMongo):
    # Setup test data
    now = datetime.now(timezone.utc)
    doc1 = {"_id": ObjectId(), "name": "John", "age": 30, "created_at": now}
    doc2 = {"_id": ObjectId(), "name": "Jane", "age": 25, "created_at": now}

    # Test basic find
    wiremongo.mock(
        FindMock()
        .with_database("testdb")
        .with_collection("users")
        .with_query({"age": {"$gt": 20}})
        .returns([doc1, doc2])
    )
    wiremongo.build()

    results = []
    async for doc in wiremongo.client["testdb"]["users"].find({"age": {"$gt": 20}}):
        results.append(doc)
    assert len(results) == 2
    assert results[0]["name"] == "John"
    assert results[1]["name"] == "Jane"

    # Test find with projection
    wiremongo.mock(
        FindMock()
        .with_database("testdb")
        .with_collection("users")
        .with_query({"age": 30}, projection={"name": 1, "_id": 0})
        .returns([{"name": "John"}])
    )
    wiremongo.build()

    results = []
    async for doc in wiremongo.client["testdb"]["users"].find(
        {"age": 30},
        projection={"name": 1, "_id": 0}
    ):
        results.append(doc)
    assert len(results) == 1
    assert "name" in results[0]
    assert "_id" not in results[0]

@pytest.mark.asyncio
async def test_find_one_operation(wiremongo: WireMongo):
    doc_id = ObjectId()
    doc = {"_id": doc_id, "name": "John", "age": 30}

    # Test successful find_one
    wiremongo.mock(
        FindOneMock()
        .with_database("testdb")
        .with_collection("users")
        .with_query({"_id": doc_id})
        .returns(doc)
    )
    wiremongo.build()

    result = await wiremongo.client["testdb"]["users"].find_one({"_id": doc_id})
    assert result == doc
    oid = ObjectId()
    # Test find_one with no results
    wiremongo.mock(
        FindOneMock()
        .with_database("testdb")
        .with_collection("users")
        .with_query({"_id": oid})
        .returns(None)
    )
    wiremongo.build()

    result = await wiremongo.client["testdb"]["users"].find_one({"_id": oid})
    assert result is None


@pytest.mark.asyncio
async def test_duplicate_insert_should_fail(wiremongo: WireMongo):
    # Test duplicate key error
    wiremongo.mock(
        InsertOneMock()
        .with_database("testdb")
        .with_collection("users")
        .with_document({"_id": 1, "name": "John"})
        .returns_duplicate_key_error()
    )
    wiremongo.build()

    with pytest.raises(DuplicateKeyError):
        await wiremongo.client["testdb"]["users"].insert_one({"_id": 1, "name": "John"})

@pytest.mark.asyncio
async def test_insert_operations(wiremongo: WireMongo):
    # Test insert_one
    doc_id = ObjectId()
    doc = {"name": "John", "age": 30}

    wiremongo.mock(
        InsertOneMock()
        .with_database("testdb")
        .with_collection("users")
        .with_document(doc)
        .returns(InsertOneResult(doc_id, acknowledged=True))
    )
    wiremongo.build()

    result = await wiremongo.client["testdb"]["users"].insert_one(doc)
    assert result.inserted_id == doc_id
    assert result.acknowledged is True

    # Test insert_many
    docs = [
        {"name": "John", "age": 30},
        {"name": "Jane", "age": 25}
    ]
    ids = [ObjectId(), ObjectId()]

    wiremongo.mock(
        InsertManyMock()
        .with_database("testdb")
        .with_collection("users")
        .with_documents(docs)
        .returns(InsertManyResult(ids, acknowledged=True))
    )
    wiremongo.build()

    result = await wiremongo.client["testdb"]["users"].insert_many(docs)
    assert result.inserted_ids == ids
    assert result.acknowledged is True

@pytest.mark.asyncio
async def test_update_operations(wiremongo: WireMongo):
    # Test update_one
    filter_doc = {"name": "John"}
    update_doc = {"$set": {"age": 31}}

    wiremongo.mock(
        UpdateOneMock()
        .with_database("testdb")
        .with_collection("users")
        .with_update(filter_doc, update_doc)
        .returns(UpdateResult({"n": 1, "nModified": 1}, acknowledged=True))
    )
    wiremongo.build()

    result = await wiremongo.client["testdb"]["users"].update_one(filter_doc, update_doc)
    assert result.modified_count == 1
    assert result.matched_count == 1

    # Test update_many
    filter_doc = {"age": {"$lt": 30}}
    update_doc = {"$inc": {"age": 1}}

    wiremongo.mock(
        UpdateManyMock()
        .with_database("testdb")
        .with_collection("users")
        .with_update(filter_doc, update_doc)
        .returns(UpdateResult({"n": 5, "nModified": 5}, acknowledged=True))
    )
    wiremongo.build()

    result = await wiremongo.client["testdb"]["users"].update_many(filter_doc, update_doc)
    assert result.modified_count == 5
    assert result.matched_count == 5

@pytest.mark.asyncio
async def test_delete_operations(wiremongo: WireMongo):
    # Test delete_one
    filter_doc = {"name": "John"}

    wiremongo.mock(
        DeleteOneMock()
        .with_database("testdb")
        .with_collection("users")
        .with_filter(filter_doc)
        .returns(DeleteResult({"n": 1}, acknowledged=True))
    )
    wiremongo.build()

    result = await wiremongo.client["testdb"]["users"].delete_one(filter_doc)
    assert result.deleted_count == 1

    # Test delete_many
    filter_doc = {"age": {"$lt": 30}}

    wiremongo.mock(
        DeleteManyMock()
        .with_database("testdb")
        .with_collection("users")
        .with_filter(filter_doc)
        .returns(DeleteResult({"n": 5}, acknowledged=True))
    )
    wiremongo.build()

    result = await wiremongo.client["testdb"]["users"].delete_many(filter_doc)
    assert result.deleted_count == 5

@pytest.mark.asyncio
async def test_count_documents(wiremongo: WireMongo):
    filter_doc = {"age": {"$gt": 25}}

    wiremongo.mock(
        CountDocumentsMock()
        .with_database("testdb")
        .with_collection("users")
        .with_filter(filter_doc)
        .returns(42)
    )
    wiremongo.build()

    count = await wiremongo.client["testdb"]["users"].count_documents(filter_doc)
    assert count == 42

@pytest.mark.asyncio
async def test_aggregate_operation(wiremongo: WireMongo):
    pipeline = [
        {"$match": {"age": {"$gt": 25}}},
        {"$group": {"_id": "$city", "total": {"$sum": 1}}}
    ]

    expected_results = [
        {"_id": "New York", "total": 10},
        {"_id": "London", "total": 5}
    ]

    wiremongo.mock(
        AggregateMock()
        .with_database("testdb")
        .with_collection("users")
        .with_pipeline(pipeline)
        .returns(expected_results)
    )
    wiremongo.build()

    results = []
    async for doc in wiremongo.client["testdb"]["users"].aggregate(pipeline):
        results.append(doc)
    assert results == expected_results

@pytest.mark.asyncio
async def test_distinct_operation(wiremongo: WireMongo):
    key = "city"
    filter_doc = {"age": {"$gt": 25}}
    expected_values = ["New York", "London", "Paris"]

    wiremongo.mock(
        DistinctMock()
        .with_database("testdb")
        .with_collection("users")
        .with_key(key, filter_doc)
        .returns(expected_values)
    )
    wiremongo.build()

    values = await wiremongo.client["testdb"]["users"].distinct(key, filter_doc)
    assert values == expected_values

@pytest.mark.asyncio
async def test_create_index(wiremongo: WireMongo):
    keys = [("name", 1), ("age", -1)]

    wiremongo.mock(
        CreateIndexMock()
        .with_database("testdb")
        .with_collection("users")
        .with_keys(keys, unique=True)
        .returns("name_1_age_-1")
    )
    wiremongo.build()

    index_name = await wiremongo.client["testdb"]["users"].create_index(
        keys,
        unique=True
    )
    assert index_name == "name_1_age_-1"

@pytest.mark.asyncio
async def test_bulk_write(wiremongo: WireMongo):
    operations = [
        InsertOne({"name": "John"}),
        UpdateOne({"name": "Jane"}, {"$set": {"age": 30}}),
        DeleteOne({"name": "Bob"})
    ]

    result = BulkWriteResult({
        "nInserted": 1,
        "nModified": 1,
        "nRemoved": 1,
        "nMatched": 1,
        "nUpserted": 0,
        "upserted": []
    }, acknowledged=True)

    wiremongo.mock(
        BulkWriteMock()
        .with_database("testdb")
        .with_collection("users")
        .with_operations(operations)
        .returns(result)
    )
    wiremongo.build()

    bulk_result = await wiremongo.client["testdb"]["users"].bulk_write(operations)
    assert bulk_result.inserted_count == 1
    assert bulk_result.modified_count == 1
    assert bulk_result.deleted_count == 1

@pytest.mark.asyncio
async def test_priority_matching(wiremongo: WireMongo):
    # Lower priority mock
    wiremongo.mock(
        FindMock()
        .with_database("testdb")
        .with_collection("users")
        .with_query({})
        .priority(1)
        .returns([{"name": "Low Priority"}])
    )

    # Higher priority mock
    wiremongo.mock(
        FindMock()
        .with_database("testdb")
        .with_collection("users")
        .with_query({})
        .priority(2)
        .returns([{"name": "High Priority"}])
    )
    wiremongo.build()

    results = []
    async for doc in wiremongo.client["testdb"]["users"].find({}):
        results.append(doc)
    assert len(results) == 1
    assert results[0]["name"] == "High Priority"

@pytest.mark.asyncio
async def test_no_match_found_error_handling(wiremongo: WireMongo):
    wiremongo.mock().build()
    # Test find_one returns None for no match
    with pytest.raises(AssertionError) as exc_info:
        await wiremongo.client["testdb"]["users"].find_one({"unmatched": True})
        assert "No matching mock found for find" in str(exc_info.value)

@pytest.mark.asyncio
async def test_error_handling(wiremongo: WireMongo):
    # Test custom error
    wiremongo.mock(
        FindOneMock()
        .with_database("testdb")
        .with_collection("users")
        .with_query({})
        .returns_error(PyMongoError("Custom error"))
    )
    wiremongo.build()

    with pytest.raises(PyMongoError) as exc_info:
        await wiremongo.client["testdb"]["users"].find_one({})
    assert str(exc_info.value) == "Custom error"

    # Test find raises AssertionError for no match
    wiremongo.reset()
    wiremongo.build()  # Need to rebuild after reset
    with pytest.raises(AssertionError) as exc_info:
        async for _ in await wiremongo.client["testdb"]["users"].find({"unmatched": True}):
            pass
    assert "No matching mock found for {'unmatched': True}" in str(exc_info.value)

@pytest.mark.asyncio
async def test_reset_functionality(wiremongo: WireMongo):
    wiremongo.mock(
        FindMock()
        .with_database("testdb")
        .with_collection("users")
        .with_query({})
        .returns([{"name": "Test"}])
    )
    wiremongo.build()

    # First call works
    results = []
    async for doc in wiremongo.client["testdb"]["users"].find({}):
        results.append(doc)
    assert len(results) == 1

    # Reset mocks
    wiremongo.reset()

    # After reset, should raise error
    with pytest.raises(AssertionError):
        async for _ in wiremongo.client["testdb"]["users"].find({}):
            pass


