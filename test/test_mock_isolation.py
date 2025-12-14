import pytest
from wiremongo import WireMongo, FindOneMock, InsertOneMock


@pytest.fixture
def wiremongo():
    wire = WireMongo()
    yield wire
    wire.reset()


@pytest.mark.asyncio
async def test_mock_isolation_different_operations(wiremongo: WireMongo):
    """Test that mocks for different operations don't interfere"""
    # Mock for find_one
    wiremongo.mock(
        FindOneMock()
        .with_database("testdb")
        .with_collection("users")
        .with_query({"name": "John"})
        .returns({"_id": "1", "name": "John"})
    )
    
    # Mock for insert_one with same query pattern
    wiremongo.mock(
        InsertOneMock()
        .with_database("testdb")
        .with_collection("users")
        .with_document({"name": "John"})
        .returns({"inserted_id": "2"})
    )
    
    wiremongo.build()
    
    # Both operations should work independently
    result = await wiremongo.client["testdb"]["users"].find_one({"name": "John"})
    assert result["name"] == "John"
    
    result = await wiremongo.client["testdb"]["users"].insert_one({"name": "John"})
    assert result["inserted_id"] == "2"


@pytest.mark.asyncio
async def test_mock_isolation_different_databases(wiremongo: WireMongo):
    """Test that mocks for different databases don't interfere"""
    wiremongo.mock(
        FindOneMock()
        .with_database("db1")
        .with_collection("users")
        .with_query({"name": "John"})
        .returns({"db": "db1"})
    )
    
    wiremongo.mock(
        FindOneMock()
        .with_database("db2")
        .with_collection("users")
        .with_query({"name": "John"})
        .returns({"db": "db2"})
    )
    
    wiremongo.build()
    
    result1 = await wiremongo.client["db1"]["users"].find_one({"name": "John"})
    result2 = await wiremongo.client["db2"]["users"].find_one({"name": "John"})
    
    assert result1["db"] == "db1"
    assert result2["db"] == "db2"


@pytest.mark.asyncio
async def test_mock_isolation_different_collections(wiremongo: WireMongo):
    """Test that mocks for different collections don't interfere"""
    wiremongo.mock(
        FindOneMock()
        .with_database("testdb")
        .with_collection("users")
        .with_query({"name": "John"})
        .returns({"collection": "users"})
    )
    
    wiremongo.mock(
        FindOneMock()
        .with_database("testdb")
        .with_collection("orders")
        .with_query({"name": "John"})
        .returns({"collection": "orders"})
    )
    
    wiremongo.build()
    
    result1 = await wiremongo.client["testdb"]["users"].find_one({"name": "John"})
    result2 = await wiremongo.client["testdb"]["orders"].find_one({"name": "John"})
    
    assert result1["collection"] == "users"
    assert result2["collection"] == "orders"


@pytest.mark.asyncio
async def test_no_cross_contamination(wiremongo: WireMongo):
    """Test that unrelated mocks don't affect each other's matching"""
    # Mock that should NOT match
    wiremongo.mock(
        FindOneMock()
        .with_database("other_db")
        .with_collection("other_collection")
        .with_query({"name": "John"})
        .returns({"wrong": "result"})
    )
    
    # Mock that SHOULD match
    wiremongo.mock(
        FindOneMock()
        .with_database("testdb")
        .with_collection("users")
        .with_query({"name": "John"})
        .returns({"correct": "result"})
    )
    
    wiremongo.build()
    
    result = await wiremongo.client["testdb"]["users"].find_one({"name": "John"})
    assert result["correct"] == "result"
    assert "wrong" not in result