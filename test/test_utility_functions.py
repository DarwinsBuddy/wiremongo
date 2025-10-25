import asyncio
import pytest
from wiremongo import from_mongo, async_partial, call_base_class_methods


def test_from_mongo_with_object_id():
    """Test from_mongo function converts _id to id"""
    data = {"_id": "507f1f77bcf86cd799439011", "name": "John", "age": 30}
    result = from_mongo(**data)
    
    assert "id" in result
    assert "_id" not in result
    assert result["id"] == "507f1f77bcf86cd799439011"
    assert result["name"] == "John"
    assert result["age"] == 30


def test_from_mongo_without_object_id():
    """Test from_mongo function without _id field"""
    data = {"name": "John", "age": 30}
    result = from_mongo(**data)
    
    assert "_id" not in result
    assert "id" not in result
    assert result["name"] == "John"
    assert result["age"] == 30


@pytest.mark.asyncio
async def test_async_partial_with_async_function():
    """Test async_partial with async function"""
    async def async_func(a, b, c=None):
        return f"{a}-{b}-{c}"
    
    partial_func = async_partial(async_func, "first", c="third")
    result = await partial_func("second")
    
    assert result == "first-second-third"


@pytest.mark.asyncio
async def test_async_partial_with_sync_function():
    """Test async_partial with sync function"""
    def sync_func(a, b, c=None):
        return f"{a}-{b}-{c}"
    
    partial_func = async_partial(sync_func, "first", c="third")
    result = await partial_func("second")
    
    assert result == "first-second-third"


def test_call_base_class_methods():
    """Test call_base_class_methods function"""
    class BaseA:
        def test_method(self, value):
            return f"BaseA-{value}"
    
    class BaseB:
        def test_method(self, value):
            return f"BaseB-{value}"
    
    class Child(BaseA, BaseB):
        def test_method(self, value):
            return f"Child-{value}"
    
    instance = Child()
    results = call_base_class_methods(Child, "test_method", instance, "test")
    
    # Should call methods from base classes (excluding Child itself by default)
    assert len(results) == 2
    assert "BaseA-test" in results
    assert "BaseB-test" in results


def test_call_base_class_methods_include_self():
    """Test call_base_class_methods with exclude_self=False"""
    class BaseA:
        def test_method(self, value):
            return f"BaseA-{value}"
    
    class Child(BaseA):
        def test_method(self, value):
            return f"Child-{value}"
    
    instance = Child()
    results = call_base_class_methods(Child, "test_method", instance, "test", exclude_self=False)
    
    # Should include Child class method
    assert len(results) == 2
    assert "Child-test" in results
    assert "BaseA-test" in results


def test_call_base_class_methods_nonexistent_method():
    """Test call_base_class_methods with non-existent method"""
    class Base:
        pass
    
    class Child(Base):
        pass
    
    instance = Child()
    results = call_base_class_methods(Child, "nonexistent_method", instance)
    
    assert results == []


def test_call_base_class_methods_non_callable():
    """Test call_base_class_methods with non-callable attribute"""
    class Base:
        not_a_method = "just a string"
    
    class Child(Base):
        pass
    
    instance = Child()
    results = call_base_class_methods(Child, "not_a_method", instance)
    
    # Should return empty list since attribute is not callable
    assert results == []