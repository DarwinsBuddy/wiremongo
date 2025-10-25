import pytest
from wiremongo import MongoMock


def test_mongo_mock_matches_no_query_no_args():
    """Test MongoMock matching with no query and no args"""
    mock = MongoMock("test")
    assert mock.matches() is True


def test_mongo_mock_matches_with_query():
    """Test MongoMock matching with query"""
    mock = MongoMock("test")
    mock.query = {"name": "John"}
    
    # Should match when args match query
    assert mock.matches({"name": "John"}) is True
    assert mock.matches({"name": "Jane"}) is False


def test_mongo_mock_matches_tuple_query():
    """Test MongoMock matching with tuple queries"""
    mock = MongoMock("test")
    mock.query = ({"name": "John"}, {"$set": {"age": 31}})
    
    # Should match tuple args
    assert mock.matches({"name": "John"}, {"$set": {"age": 31}}) is True
    assert mock.matches({"name": "Jane"}, {"$set": {"age": 31}}) is False


def test_mongo_mock_matches_with_kwargs():
    """Test MongoMock matching with kwargs"""
    mock = MongoMock("test")
    mock.query = {"name": "test"}  # Set a query so it doesn't return True immediately
    mock.kwargs = {"limit": 10, "skip": 5}
    
    # With query set, it will check kwargs when no args provided
    assert mock.matches(limit=10, skip=5, extra=True) is True
    assert mock.matches(limit=10, skip=5) is True
    assert mock.matches(limit=5, skip=5) is False  # limit doesn't match


def test_mongo_mock_matches_empty_kwargs():
    """Test MongoMock matching with empty kwargs"""
    mock = MongoMock("test")
    mock.kwargs = {}
    
    # Should return True when no kwargs to match
    assert mock.matches(some_arg="value") is True


def test_mongo_mock_compare_values_with_object_id():
    """Test MongoMock._compare_values with ObjectId-like objects"""
    mock = MongoMock("test")
    
    class MockObjectId:
        def __init__(self, value):
            self._type_marker = "ObjectId"
            self.value = value
        def __str__(self):
            return self.value
    
    obj1 = MockObjectId("507f1f77bcf86cd799439011")
    obj2 = MockObjectId("507f1f77bcf86cd799439011")
    obj3 = MockObjectId("507f1f77bcf86cd799439012")
    
    assert mock._compare_values(obj1, obj2) is True
    assert mock._compare_values(obj1, obj3) is False


def test_mongo_mock_compare_values_with_dict():
    """Test MongoMock._compare_values with dict comparison"""
    mock = MongoMock("test")
    
    # Test dict comparison with _id field
    class MockObjectId:
        def __init__(self, value):
            self._type_marker = "ObjectId"
            self.value = value
        def __str__(self):
            return self.value
    
    obj1 = MockObjectId("507f1f77bcf86cd799439011")
    obj2 = MockObjectId("507f1f77bcf86cd799439011")
    obj3 = MockObjectId("507f1f77bcf86cd799439012")
    
    dict1 = {"_id": obj1, "name": "John"}
    dict2 = {"_id": obj2, "name": "John"}
    dict3 = {"_id": obj3, "name": "John"}
    
    assert mock._compare_values(dict1, dict2) is True
    assert mock._compare_values(dict1, dict3) is False


def test_mongo_mock_compare_values_nested_dict():
    """Test MongoMock._compare_values with nested dict scenarios"""
    mock = MongoMock("test")
    
    dict1 = {"user": {"name": "John", "age": 30}, "active": True}
    dict2 = {"user": {"name": "John", "age": 30}, "active": True, "extra": "field"}
    
    # dict1 should match dict2 (all keys in dict1 exist in dict2)
    assert mock._compare_values(dict1, dict2) is True
    
    # dict2 should not match dict1 (extra field in dict2 not in dict1)
    assert mock._compare_values(dict2, dict1) is False
    
    # Test with mismatched nested values
    dict3 = {"user": {"name": "Jane", "age": 30}, "active": True}
    assert mock._compare_values(dict1, dict3) is False


def test_mongo_mock_priority():
    """Test MongoMock priority functionality"""
    mock = MongoMock("test")
    
    # Test default priority
    assert mock._priority == 0
    
    # Test priority setter
    mock.priority(5)
    assert mock._priority == 5


def test_mongo_mock_error_handling():
    """Test MongoMock error handling in get_result"""
    mock = MongoMock("test")
    
    # Test with Exception as result
    error = ValueError("Test error")
    mock.returns_error(error)
    
    with pytest.raises(ValueError) as exc_info:
        mock.get_result()
    assert str(exc_info.value) == "Test error"
    
    # Test returns_duplicate_key_error with custom message
    mock.returns_duplicate_key_error("Custom duplicate key message")
    
    with pytest.raises(Exception) as exc_info:
        mock.get_result()
    assert "Custom duplicate key message" in str(exc_info.value)