# wiremongo

A lightweight test library for mocking MongoDB operations with AsyncMongoClient compatibility. Designed for creating integrated tests without requiring a real MongoDB instance.

## Installation

```bash
pip install wiremongo
```

## Usage

### Basic Usage

Replace your real AsyncMongoClient with MockClient in your tests:

```python
from wiremongo import MockClient, FindOneMock, InsertOneMock

# Replace AsyncMongoClient with MockClient in your tests
client = MockClient()
db = client["test_db"]
collection = db["test_collection"]

# Mock find_one operation
find_mock = FindOneMock().with_query({"_id": "123"}).returns({"_id": "123", "name": "test"})
collection.find_one = find_mock.get_result

# Use in your tests
result = await collection.find_one({"_id": "123"})
assert result["name"] == "test"
```

### JSON File Mappings

Use the provided hook to load mock mappings from JSON files:

```python
from wiremongo import WireMongo
from wiremongo.tools import read_filemappings

wiremongo = WireMongo()

# Load mock mappings from tests/resources/mappings/*.json
await read_filemappings(wiremongo)
```

Create JSON mapping files in `tests/resources/mappings/`:

```json
{
  "cmd": "find_one",
  "with_database": "test_db",
  "with_collection": "users",
  "with_query": {"_id": "123"},
  "returns": {"_id": "123", "name": "John"}
}
```

## Supported Operations

- **Collection Operations**: find_one, find, insert_one, insert_many, update_one, update_many, delete_one, delete_many, count_documents, distinct, create_index, bulk_write, drop, drop_indexes
- **Database Operations**: command, create_collection, drop_collection
- **Cursor Operations**: find, aggregate with async iteration support

## Development

```bash
# Clone and setup
git clone <repository-url>
cd wiremongo
poetry install

# Activate virtual environment
poetry shell

# Run tests
poetry run pytest
```