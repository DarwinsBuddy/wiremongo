import pytest
from wiremongo import from_filemapping, FindOneMock, InsertOneMock, UpdateOneMock, CreateIndexMock


def test_from_filemapping_find_one():
    """Test creating FindOneMock from file mapping"""
    mapping = {
        "cmd": "find_one",
        "with_database": "test_db",
        "with_collection": "users",
        "with_query": {"_id": "123"},
        "returns": {"_id": "123", "name": "John"}
    }
    
    mock = from_filemapping(mapping)
    assert isinstance(mock, FindOneMock)
    assert mock.database == "test_db"
    assert mock.collection == "users"
    assert mock.query == {"_id": "123"}
    assert mock.result == {"_id": "123", "name": "John"}


def test_from_filemapping_insert_one():
    """Test creating InsertOneMock from file mapping"""
    mapping = {
        "cmd": "insert_one",
        "with_database": "test_db",
        "with_collection": "users",
        "with_document": {"name": "Jane"},
        "returns": {"inserted_id": "456"}
    }
    
    mock = from_filemapping(mapping)
    assert isinstance(mock, InsertOneMock)
    assert mock.database == "test_db"
    assert mock.collection == "users"
    assert mock.query == {"name": "Jane"}
    assert mock.result == {"inserted_id": "456"}


def test_from_filemapping_with_args_kwargs():
    """Test file mapping with args and kwargs format"""
    mapping = {
        "cmd": "update_one",
        "with_database": "test_db",
        "with_collection": "users",
        "with_update": {
            "args": [{"_id": "123"}, {"$set": {"name": "Updated"}}],
            "kwargs": {"upsert": True}
        },
        "returns": {"modified_count": 1}
    }
    
    mock = from_filemapping(mapping)
    assert isinstance(mock, UpdateOneMock)
    assert mock.database == "test_db"
    assert mock.collection == "users"
    assert mock.query == ({"_id": "123"}, {"$set": {"name": "Updated"}})
    assert mock.kwargs == {"upsert": True}
    assert mock.result == {"modified_count": 1}


def test_from_filemapping_unknown_command():
    """Test error handling for unknown command"""
    mapping = {
        "cmd": "unknown_command",
        "with_database": "test_db",
        "with_collection": "users"
    }
    
    with pytest.raises(KeyError) as exc_info:
        from_filemapping(mapping)
    assert "unknown wiremongo cmd `unknown_command`" in str(exc_info.value)


def test_from_filemapping_list_args():
    """Test file mapping with list arguments"""
    mapping = {
        "cmd": "find_one",
        "with_database": "test_db",
        "with_collection": "users",
        "with_query": [{"_id": "123"}],
        "returns": {"_id": "123", "name": "John"}
    }
    
    mock = from_filemapping(mapping)
    assert isinstance(mock, FindOneMock)
    assert mock.query == {"_id": "123"}


def test_from_filemapping_list_args_create_index():
    """Test file mapping with list arguments"""
    mapping = {
        "cmd": "create_index",
        "with_database": "test_db",
        "with_collection": "users",
        "with_keys": {
            "user_id": 1,
            "name": 1
        },
        "returns": None
    }

    mock = from_filemapping(mapping)
    assert isinstance(mock, CreateIndexMock)
    assert mock.query == {
        "user_id": 1,
        "name": 1
    }
