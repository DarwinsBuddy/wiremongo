import pytest
import pytest_asyncio
from wiremongo import WireMongo, FindOneAndUpdateMock


@pytest_asyncio.fixture
async def wiremongo():
    wire = WireMongo()
    yield wire
    wire.reset()


@pytest.mark.asyncio
async def test_find_one_and_update_operation(wiremongo: WireMongo):
    """Test find_one_and_update collection operation"""
    filter_doc = {"name": "John"}
    update_doc = {"$set": {"age": 31}}
    expected_result = {"_id": "123", "name": "John", "age": 31}

    wiremongo.mock(
        FindOneAndUpdateMock()
        .with_database("testdb")
        .with_collection("users")
        .with_update(filter_doc, update_doc, return_document=True)
        .returns(expected_result)
    )
    wiremongo.build()

    result = await wiremongo.client["testdb"]["users"].find_one_and_update(
        filter_doc, update_doc, return_document=True
    )
    assert result == expected_result


@pytest.mark.asyncio
async def test_collection_drop_operation(wiremongo: WireMongo):
    """Test collection drop operation with proper mocking"""
    from wiremongo import MongoMock
    
    # Create a mock for drop operation
    drop_mock = MongoMock("drop")
    drop_mock.with_database("testdb")
    drop_mock.with_collection("users")
    drop_mock.returns({"dropped": True})
    
    wiremongo.mock(drop_mock)
    wiremongo.build()
    
    # Test that the mock works
    collection = wiremongo.client["testdb"]["users"]
    result = await collection.drop()
    assert result == {"dropped": True}


@pytest.mark.asyncio
async def test_collection_drop_indexes_operation(wiremongo: WireMongo):
    """Test collection drop_indexes operation with proper mocking"""
    from wiremongo import MongoMock
    
    # Create a mock for drop_indexes operation
    drop_indexes_mock = MongoMock("drop_indexes")
    drop_indexes_mock.with_database("testdb")
    drop_indexes_mock.with_collection("users")
    drop_indexes_mock.returns({"nIndexesWas": 3})
    
    wiremongo.mock(drop_indexes_mock)
    wiremongo.build()
    
    # Test that the mock works
    collection = wiremongo.client["testdb"]["users"]
    result = await collection.drop_indexes()
    assert result == {"nIndexesWas": 3}