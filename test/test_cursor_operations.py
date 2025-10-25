import pytest
import pytest_asyncio
from wiremongo import AsyncCursor, FindMock, AggregateMock


@pytest.mark.asyncio
async def test_async_cursor_iteration():
    """Test AsyncCursor async iteration"""
    cursor = AsyncCursor([{"name": "John"}, {"name": "Jane"}])
    
    results = []
    async for doc in cursor:
        results.append(doc)
    
    assert len(results) == 2
    assert results[0]["name"] == "John"
    assert results[1]["name"] == "Jane"


@pytest.mark.asyncio
async def test_async_cursor_single_result():
    """Test AsyncCursor with single result (not list)"""
    cursor = AsyncCursor({"name": "John"})
    
    results = []
    async for doc in cursor:
        results.append(doc)
    
    assert len(results) == 1
    assert results[0]["name"] == "John"


@pytest.mark.asyncio
async def test_async_cursor_to_list_with_limit():
    """Test AsyncCursor to_list with length limit"""
    cursor = AsyncCursor([{"a": 1}, {"b": 2}, {"c": 3}])
    
    limited = await cursor.to_list(2)
    assert len(limited) == 2
    assert limited == [{"a": 1}, {"b": 2}]


@pytest.mark.asyncio
async def test_async_cursor_to_list_without_limit():
    """Test AsyncCursor to_list without length limit"""
    cursor = AsyncCursor([{"a": 1}, {"b": 2}])
    
    all_results = await cursor.to_list()
    assert len(all_results) == 2
    assert all_results == [{"a": 1}, {"b": 2}]


@pytest.mark.asyncio
async def test_async_cursor_empty():
    """Test AsyncCursor with empty results"""
    cursor = AsyncCursor([])
    
    results = []
    async for doc in cursor:
        results.append(doc)
    
    assert len(results) == 0


@pytest.mark.asyncio
async def test_find_mock_returns_cursor():
    """Test FindMock.get_result returns AsyncCursor"""
    mock = FindMock()
    mock.result = [{"name": "John"}, {"name": "Jane"}]
    
    cursor = mock.get_result()
    assert isinstance(cursor, AsyncCursor)
    assert cursor.results == [{"name": "John"}, {"name": "Jane"}]


@pytest.mark.asyncio
async def test_find_mock_returns_cursor_with_none_result():
    """Test FindMock.get_result with None result returns empty cursor"""
    mock = FindMock()
    mock.result = None
    
    cursor = mock.get_result()
    assert isinstance(cursor, AsyncCursor)
    assert cursor.results == []


@pytest.mark.asyncio
async def test_aggregate_mock_returns_cursor():
    """Test AggregateMock.get_result returns AsyncCursor"""
    mock = AggregateMock()
    mock.result = [{"_id": "NYC", "count": 5}]
    
    cursor = mock.get_result()
    assert hasattr(cursor, '__aiter__')
    
    results = []
    async for doc in cursor:
        results.append(doc)
    
    assert len(results) == 1
    assert results[0]["_id"] == "NYC"


@pytest.mark.asyncio
async def test_aggregate_mock_returns_cursor_with_none_result():
    """Test AggregateMock.get_result with None result returns empty cursor"""
    mock = AggregateMock()
    mock.result = None
    
    cursor = mock.get_result()
    results = await cursor.to_list()
    assert results == []