import json
import os
import tempfile
import pytest
import pytest_asyncio
from wiremongo import WireMongo
from wiremongo.tools import read_filemappings


@pytest_asyncio.fixture
async def temp_mappings_dir():
    """Create a temporary directory with test mapping files"""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create the expected directory structure
        mappings_dir = os.path.join(temp_dir, 'tests', 'resources', 'mappings')
        os.makedirs(mappings_dir, exist_ok=True)
        
        # Create test mapping files
        mapping1 = {
            "cmd": "find_one",
            "with_database": "test_db",
            "with_collection": "users",
            "with_query": {"_id": "123"},
            "returns": {"_id": "123", "name": "John"}
        }
        
        mapping2 = {
            "cmd": "insert_one",
            "with_database": "test_db",
            "with_collection": "users",
            "with_document": {"name": "Jane"},
            "returns": {"inserted_id": "456"}
        }
        
        with open(os.path.join(mappings_dir, 'mapping1.json'), 'w') as f:
            json.dump(mapping1, f)
            
        with open(os.path.join(mappings_dir, 'mapping2.json'), 'w') as f:
            json.dump(mapping2, f)
        
        # Change to temp directory
        original_cwd = os.getcwd()
        os.chdir(temp_dir)
        
        yield mappings_dir
        
        # Restore original directory
        os.chdir(original_cwd)


@pytest.mark.asyncio
async def test_read_filemappings_success(temp_mappings_dir):
    """Test successful reading of file mappings"""
    wiremongo = WireMongo()
    
    await read_filemappings(wiremongo)
    
    # Verify mocks were loaded
    assert len(wiremongo.mocks) == 2
    
    # Test the loaded mocks work
    result = await wiremongo.client["test_db"]["users"].find_one({"_id": "123"})
    assert result["name"] == "John"


@pytest.mark.asyncio
async def test_read_filemappings_no_directory():
    """Test behavior when mappings directory doesn't exist"""
    wiremongo = WireMongo()
    
    # Should not raise error, just load no mocks
    await read_filemappings(wiremongo)
    assert len(wiremongo.mocks) == 0


@pytest.mark.asyncio
async def test_read_filemappings_empty_directory():
    """Test behavior with empty mappings directory"""
    with tempfile.TemporaryDirectory() as temp_dir:
        mappings_dir = os.path.join(temp_dir, 'tests', 'resources', 'mappings')
        os.makedirs(mappings_dir, exist_ok=True)
        
        original_cwd = os.getcwd()
        os.chdir(temp_dir)
        
        try:
            wiremongo = WireMongo()
            await read_filemappings(wiremongo)
            assert len(wiremongo.mocks) == 0
        finally:
            os.chdir(original_cwd)