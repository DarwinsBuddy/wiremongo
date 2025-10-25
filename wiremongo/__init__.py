import asyncio
from typing import Any, Mapping, Optional, Union
from unittest.mock import AsyncMock, MagicMock

from pymongo import AsyncMongoClient
from pymongo.errors import DuplicateKeyError

ASYNC_DATABASE_OPERATIONS = ["command", "create_collection", "drop_collection"]
ASYNC_COLLECTION_OPERATIONS = ["find_one", "find_one_and_update", "insert_one", "insert_many", "update_one", "update_many", "delete_one", "delete_many", "count_documents", "distinct", "create_index", "bulk_write", "drop", "drop_indexes"]
ASYNC_CURSOR_COLLECTION_OPERATIONS = ["find", "aggregate"]
ALL_SUPPORTED_OPERATIONS = ASYNC_COLLECTION_OPERATIONS + ASYNC_CURSOR_COLLECTION_OPERATIONS + ASYNC_DATABASE_OPERATIONS

def from_filemapping[T: MongoMock](mapping: Mapping[str, Any]) -> T:
    cls = globals().get(f"{''.join(word.capitalize() for word in mapping['cmd'].split('_'))}Mock")
    if not cls:
        raise KeyError(f"unknown wiremongo cmd `{mapping['cmd']}` Not implemented")
    mock = cls()
    for method, arguments in mapping.items():
        if method.startswith("with_") or method.startswith("returns"):
            if isinstance(arguments, dict):
                args = arguments["args"]
                kwargs = arguments["kwargs"]
            else:
                args = arguments if isinstance(arguments, list) else [arguments]
                kwargs = dict()
            call_base_class_methods(cls, method, mock, *args, exclude_self=False, **kwargs)
    return mock

class MockAsyncMongoClient(AsyncMock):
    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(spec=AsyncMongoClient, *args, **kwargs)

def from_mongo(**kwargs) -> Mapping[str, Any]:
    if "_id" in kwargs:
        kwargs["id"] = str(kwargs.pop("_id"))
    return kwargs

def async_partial(f, *args, **kwargs):
   async def f2(*args2, **kwargs2):
       result = f(*args, *args2, **kwargs, **kwargs2)
       if asyncio.iscoroutinefunction(f):
           result = await result
       return result

   return f2


def call_base_class_methods(cls, method_name, instance, *args, exclude_self = True, **kwargs):
    """
    Call a specific method from all base classes of a given class.

    Parameters:
    - cls: The class whose base classes you want to inspect.
    - method_name: The name of the method to call.
    - instance: An instance of the class cls.
    """
    results = []
    for base_cls in (cls.mro()[1:] if exclude_self else cls.mro()):  # potentially skip the class itself
        if hasattr(base_cls, method_name):
            method = getattr(base_cls, method_name)
            if callable(method):
                results.append(method(instance, *args, **kwargs))
    return results

class AsyncCursor:
    """Async cursor implementation that mimics MongoDB cursor"""

    def __init__(self, results):
        self.results = results if isinstance(results, list) else [results]
        self._index = 0

    def __aiter__(self):
        return self

    async def __anext__(self):
        if self._index >= len(self.results):
            raise StopAsyncIteration
        result = self.results[self._index]
        self._index += 1
        return result

    async def to_list(self, length=None):
        return self.results[:length] if length is not None else self.results


class MockCollection(MagicMock):
    """Mock collection that supports async operations"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.name = kwargs.get("name", "mock_collection")

        # Special handling for cursor methods
        def default_cursor_method(*args, **kwargs):
            raise AssertionError(f"No matching mock found for {method}")

        for method in ASYNC_COLLECTION_OPERATIONS:
            setattr(self, method, AsyncMock(side_effect=async_partial(default_cursor_method)))

        for method in ASYNC_CURSOR_COLLECTION_OPERATIONS:
            setattr(self, method, default_cursor_method)


class MockDatabase(MagicMock):
    """Mock database that returns MockCollection instances"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.name = kwargs.get("name", "mock_db")

        # Make common database operations async
        for method in ASYNC_DATABASE_OPERATIONS:
            setattr(self, method, AsyncMock(return_value=None))

    def __getitem__(self, name):
        if not hasattr(self, f"_mock_collection_{name}"):
            setattr(self, f"_mock_collection_{name}", MockCollection(name=name))
        return getattr(self, f"_mock_collection_{name}")

    def get_collection(self, name, *args, **kwargs):
        return self[name]


class MockClient(MagicMock):
    """Mock client that mimics pymongo.AsyncMongoClient"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__class__ = type("MockAsyncMongoClient", (MagicMock,), {"__class__": AsyncMongoClient, "__await__": lambda self: self._get_awaitable().__await__()})

        # Make common client operations async
        async_methods = ["close", "server_info", "list_databases"]
        for method in async_methods:
            setattr(self, method, AsyncMock(return_value=None))

    def __getitem__(self, name):
        if not hasattr(self, f"_mock_database_{name}"):
            setattr(self, f"_mock_database_{name}", MockDatabase(name=name))
        return getattr(self, f"_mock_database_{name}")

    def get_database(self, name, *args, **kwargs):
        return self[name]

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    def _get_awaitable(self):
        async def awaitable():
            return self

        return awaitable()


class MongoMock:
    """Base class for all mongo operation mocks"""

    def __init__(self, operation: str):
        self.operation = operation
        self.database = None
        self.collection = None
        self.result = None
        self.query = None
        self.kwargs = {}
        self._priority = 0

    def with_database(self, database: str) -> "MongoMock":
        self.database = database
        return self

    def with_collection(self, collection: str) -> "MongoMock":
        self.collection = collection
        return self

    def returns(self, result: Any) -> "MongoMock":
        self.result = result
        return self

    def returns_error(self, error: Exception) -> "MongoMock":
        self.result = error
        return self

    def returns_duplicate_key_error(self, message: str = "Duplicate key error") -> "MongoMock":
        return self.returns_error(DuplicateKeyError(message))

    def priority(self, priority: int) -> "MongoMock":
        self._priority = priority
        return self

    def matches(self, *args, **kwargs) -> bool:
        """Check if the mock matches the given arguments"""
        if not args and not self.query:
            return True
        if args and self.query:
            if isinstance(self.query, tuple):
                return all(self._compare_values(arg, q) for arg, q in zip(args, self.query))
            return self._compare_values(args[0], self.query)
        return all(self.kwargs.get(k) == v for k, v in kwargs.items() if k in self.kwargs)

    def _compare_values(self, val1, val2):
        """Compare two values, handling ObjectId and other special types"""
        if hasattr(val1, "_type_marker") and hasattr(val2, "_type_marker"):  # For ObjectId
            return str(val1) == str(val2)
        if isinstance(val1, dict) and isinstance(val2, dict):
            if "_id" in val1 and "_id" in val2:  # Special handling for _id field
                if not self._compare_values(val1["_id"], val2["_id"]):
                    return False
            return all(k in val2 and self._compare_values(v, val2[k]) for k, v in val1.items() if k != "_id")
        return val1 == val2

    def get_result(self):
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


class FindMock(MongoMock):
    def __init__(self):
        super().__init__("find")

    def with_query(self, query: dict, **kwargs) -> "FindMock":
        self.query = query
        self.kwargs = kwargs
        return self

    def get_result(self):
        result = super().get_result()
        return AsyncCursor(result if result is not None else [])


class FindOneMock(MongoMock):
    def __init__(self):
        super().__init__("find_one")

    def with_query(self, query: dict, **kwargs) -> "FindOneMock":
        self.query = query
        self.kwargs = kwargs
        return self


class InsertOneMock(MongoMock):
    def __init__(self):
        super().__init__("insert_one")

    def with_document(self, document: dict, **kwargs) -> "InsertOneMock":
        self.query = document
        self.kwargs = kwargs
        return self


class InsertManyMock(MongoMock):
    def __init__(self):
        super().__init__("insert_many")

    def with_documents(self, documents: list[dict], **kwargs) -> "InsertManyMock":
        self.query = documents
        self.kwargs = kwargs
        return self


class FindOneAndUpdateMock(MongoMock):
    def __init__(self):
        super().__init__("find_one_and_update")

    def with_update(self, filter: dict, update: dict, **kwargs) -> "FindOneAndUpdateMock":
        self.query = (filter, update)
        self.kwargs = kwargs
        return self

class UpdateOneMock(MongoMock):
    def __init__(self):
        super().__init__("update_one")

    def with_update(self, filter: dict, update: dict, **kwargs) -> "UpdateOneMock":
        self.query = (filter, update)
        self.kwargs = kwargs
        return self


class UpdateManyMock(MongoMock):
    def __init__(self):
        super().__init__("update_many")

    def with_update(self, filter: dict, update: dict, **kwargs) -> "UpdateManyMock":
        self.query = (filter, update)
        self.kwargs = kwargs
        return self


class DeleteOneMock(MongoMock):
    def __init__(self):
        super().__init__("delete_one")

    def with_filter(self, filter: dict, **kwargs) -> "DeleteOneMock":
        self.query = filter
        self.kwargs = kwargs
        return self


class DeleteManyMock(MongoMock):
    def __init__(self):
        super().__init__("delete_many")

    def with_filter(self, filter: dict, **kwargs) -> "DeleteManyMock":
        self.query = filter
        self.kwargs = kwargs
        return self


class CountDocumentsMock(MongoMock):
    def __init__(self):
        super().__init__("count_documents")

    def with_filter(self, filter: dict, **kwargs) -> "CountDocumentsMock":
        self.query = filter
        self.kwargs = kwargs
        return self


class AggregateMock(MongoMock):
    def __init__(self):
        super().__init__("aggregate")

    def with_pipeline(self, pipeline: list[dict], **kwargs) -> "AggregateMock":
        self.query = pipeline
        self.kwargs = kwargs
        return self

    def get_result(self):
        result = super().get_result()
        return AsyncCursor(result if result is not None else [])


class DistinctMock(MongoMock):
    def __init__(self):
        super().__init__("distinct")

    def with_key(self, key: str, filter: Optional[dict] = None, **kwargs) -> "DistinctMock":
        self.query = (key, filter)
        self.kwargs = kwargs
        return self


class BulkWriteMock(MongoMock):
    def __init__(self):
        super().__init__("bulk_write")

    def with_operations(self, operations: list[Any], **kwargs) -> "BulkWriteMock":
        self.query = operations
        self.kwargs = kwargs
        return self


class CreateIndexMock(MongoMock):
    def __init__(self):
        super().__init__("create_index")

    def with_keys(self, keys: Union[str, list[tuple], dict], **kwargs) -> "CreateIndexMock":
        self.query = keys
        self.kwargs = kwargs
        return self


class WireMongo:
    """Main class for mocking MongoDB operations"""

    def __init__(self, client=None):
        self.client = client or MockClient()
        self.mocks: list[MongoMock] = []
        self._original_methods = {}
        self._default_handlers = {}

    def mock(self, *mocks: MongoMock) -> "WireMongo":
        """Add mocks to be used"""
        self.mocks.extend(mocks)
        return self

    def build(self):
        """Build the mock setup"""
        # Set up default handlers for all collections that have mocks
        collections = {(mock.database, mock.collection) for mock in self.mocks} if self.mocks else {("mock_db", "mock_collection")}

        for db, coll in collections:
            collection = self.client[db][coll]
            operations = ALL_SUPPORTED_OPERATIONS

            for operation in operations:

                def create_default_handler(op=operation):
                    raise AssertionError(f"No matching mock found for {op}")

                key = (db, coll, operation)
                if key not in self._original_methods:
                    self._original_methods[key] = getattr(collection, operation, None)

                    if operation in ASYNC_CURSOR_COLLECTION_OPERATIONS:
                        new_mock = default_handler = create_default_handler
                    else:
                        default_handler = async_partial(create_default_handler)
                        new_mock = AsyncMock(side_effect=default_handler)
                    self._default_handlers[key] = default_handler
                    setattr(collection, operation, new_mock)

        # Set up specific mock handlers
        for mock in self.mocks:
            collection = self.client[mock.database][mock.collection]

            def create_handler(operation: str, mock_list: list[MongoMock]):
                def handler(*args, **kwargs):
                    # Sort mocks by priority to use highest priority match
                    matching_mocks = [(i, m) for i, m in enumerate(mock_list) if m.operation == operation and m.matches(*args, **kwargs)]
                    if not matching_mocks:
                        raise AssertionError(f"No matching mock found for {operation}: args={args}, kwargs={kwargs}")

                    # Use the highest priority mock
                    idx, mock = max(matching_mocks, key=lambda x: x[1]._priority)
                    return mock.get_result()

                return handler

            # Store original method if not already stored
            key = (mock.database, mock.collection, mock.operation)
            if key not in self._original_methods:
                self._original_methods[key] = getattr(collection, mock.operation, None)
                # Store default handler
                if mock.operation in ASYNC_CURSOR_COLLECTION_OPERATIONS:

                    def default_handler(*args, **kwargs):
                        raise AssertionError(f"No matching mock found for {mock.operation}")

                    self._default_handlers[key] = default_handler

            # Create new mock with the handler
            if mock.operation in ASYNC_CURSOR_COLLECTION_OPERATIONS:
                new_mock = create_handler(mock.operation, self.mocks)
            else:
                new_mock = AsyncMock(side_effect=async_partial(create_handler(mock.operation, self.mocks)))
            setattr(collection, mock.operation, new_mock)

    def reset(self):
        """Clear all mocks and restore original methods"""
        # Restore original methods
        for key, method in self._original_methods.items():
            db, coll, op = key
            if method is not None:
                collection = self.client[db][coll]
                if op in ASYNC_CURSOR_COLLECTION_OPERATIONS:
                    # Restore default handler that raises AssertionError
                    new_mock = self._default_handlers[key]
                else:
                    new_mock = AsyncMock(side_effect=async_partial(self._default_handlers[key]))
                setattr(collection, op, new_mock)

        self._original_methods.clear()
        self._default_handlers.clear()
        self.mocks.clear()