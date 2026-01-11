import asyncio
from typing import Any, Mapping, Optional, Union
from unittest.mock import AsyncMock, MagicMock

from pymongo import AsyncMongoClient
from pymongo.errors import DuplicateKeyError

ASYNC_DATABASE_OPERATIONS = ["command", "create_collection", "drop_collection"]
ASYNC_COLLECTION_OPERATIONS = ["find_one", "find_one_and_update", "insert_one", "insert_many", "update_one", "update_many", "delete_one", "delete_many", "count_documents", "distinct", "create_index", "bulk_write", "drop", "drop_indexes"]
ASYNC_CURSOR_COLLECTION_OPERATIONS = ["find"]
ASYNC_COROUTINE_CURSOR_OPERATIONS = ["aggregate"]
ALL_SUPPORTED_OPERATIONS = ASYNC_COLLECTION_OPERATIONS + ASYNC_CURSOR_COLLECTION_OPERATIONS + ASYNC_COROUTINE_CURSOR_OPERATIONS + ASYNC_DATABASE_OPERATIONS

def from_filemapping[T: MongoMock](mapping: Mapping[str, Any]) -> T:
    cls = globals().get(f"{''.join(word.capitalize() for word in mapping['cmd'].split('_'))}Mock")
    if not cls:
        raise KeyError(f"unknown wiremongo cmd `{mapping['cmd']}` Not implemented")
    mock = cls()
    for method, arguments in mapping.items():
        if method.startswith("with_") or method.startswith("returns"):
            if isinstance(arguments, dict) and "args" in arguments:
                args = arguments.get("args", [])
                kwargs = arguments.get("kwargs", {})
            else:
                args = list(arguments) if isinstance(arguments, list) or isinstance(arguments, tuple) else [arguments]
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

        for method in ASYNC_COROUTINE_CURSOR_OPERATIONS:
            setattr(self, method, default_cursor_method)


class MockDatabase:
    """Mock database that returns MockCollection instances"""

    def __init__(self, *args, **kwargs):
        self.name = kwargs.get("name", "mock_db")
        self._collections = {}

        # Make common database operations async
        for method in ASYNC_DATABASE_OPERATIONS:
            setattr(self, method, AsyncMock(return_value=None))

    def __getitem__(self, name):
        if name not in self._collections:
            self._collections[name] = MockCollection(name=name)
        return self._collections[name]

    def get_collection(self, name, *args, **kwargs):
        return self[name]


class MockClient:
    """Mock client that mimics pymongo.AsyncMongoClient"""

    def __init__(self, *args, **kwargs):
        self._databases = {}
        # Make common client operations async
        self.close = AsyncMock(return_value=None)
        self.server_info = AsyncMock(return_value=None)
        self.list_databases = AsyncMock(return_value=None)

    def __getitem__(self, name):
        if name not in self._databases:
            self._databases[name] = MockDatabase(name=name)
        return self._databases[name]

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

    def __repr__(self):
        return f"{self.operation.capitalize()}Mock(database={self.database}, collection={self.collection}, query={self.query}, kwargs={self.kwargs})"


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

    def __repr__(self):
        return f"FindMock(query={self.query}, kwargs={self.kwargs})"


class FindOneMock(MongoMock):
    def __init__(self):
        super().__init__("find_one")

    def with_query(self, query: dict, **kwargs) -> "FindOneMock":
        self.query = query
        self.kwargs = kwargs
        return self

    def __repr__(self):
        return f"FindOneMock(query={self.query}, kwargs={self.kwargs})"


class InsertOneMock(MongoMock):
    def __init__(self):
        super().__init__("insert_one")

    def with_document(self, document: dict, **kwargs) -> "InsertOneMock":
        self.query = document
        self.kwargs = kwargs
        return self

    def __repr__(self):
        return f"InsertOneMock(query={self.query}, kwargs={self.kwargs})"


class InsertManyMock(MongoMock):
    def __init__(self):
        super().__init__("insert_many")

    def with_documents(self, documents: list[dict], **kwargs) -> "InsertManyMock":
        self.query = documents
        self.kwargs = kwargs
        return self

    def __repr__(self):
        return f"InsertManyMock(query={self.query}, kwargs={self.kwargs})"


class FindOneAndUpdateMock(MongoMock):
    def __init__(self):
        super().__init__("find_one_and_update")

    def with_update(self, filter: dict, update: dict, **kwargs) -> "FindOneAndUpdateMock":
        self.query = (filter, update)
        self.kwargs = kwargs
        return self

    def __repr__(self):
        return f"FindOneAndUpdateMock(query={self.query}, kwargs={self.kwargs})"

class UpdateOneMock(MongoMock):
    def __init__(self):
        super().__init__("update_one")

    def with_update(self, filter: dict, update: dict, **kwargs) -> "UpdateOneMock":
        self.query = (filter, update)
        self.kwargs = kwargs
        return self

    def __repr__(self):
        return f"UpdateOneMock(query={self.query}, kwargs={self.kwargs})"


class UpdateManyMock(MongoMock):
    def __init__(self):
        super().__init__("update_many")

    def with_update(self, filter: dict, update: dict, **kwargs) -> "UpdateManyMock":
        self.query = (filter, update)
        self.kwargs = kwargs
        return self

    def __repr__(self):
        return f"UpdateManyMock(query={self.query}, kwargs={self.kwargs})"


class DeleteOneMock(MongoMock):
    def __init__(self):
        super().__init__("delete_one")

    def with_filter(self, filter: dict, **kwargs) -> "DeleteOneMock":
        self.query = filter
        self.kwargs = kwargs
        return self

    def __repr__(self):
        return f"DeleteOneMock(query={self.query}, kwargs={self.kwargs})"


class DeleteManyMock(MongoMock):
    def __init__(self):
        super().__init__("delete_many")

    def with_filter(self, filter: dict, **kwargs) -> "DeleteManyMock":
        self.query = filter
        self.kwargs = kwargs
        return self

    def __repr__(self):
        return f"DeleteManyMock(query={self.query}, kwargs={self.kwargs})"

class CountDocumentsMock(MongoMock):
    def __init__(self):
        super().__init__("count_documents")

    def with_filter(self, filter: dict, **kwargs) -> "CountDocumentsMock":
        self.query = filter
        self.kwargs = kwargs
        return self

    def __repr__(self):
        return f"CountDocumentsMock(query={self.query}, kwargs={self.kwargs})"


class AggregateMock(MongoMock):
    def __init__(self):
        super().__init__("aggregate")

    def with_pipeline(self, pipeline: list[dict], **kwargs) -> "AggregateMock":
        self.query = pipeline
        self.kwargs = kwargs
        return self

    async def get_result(self):
        result = super().get_result()
        return AsyncCursor(result if result is not None else [])

    def __repr__(self):
        return f"AggregateMock(query={self.query}, kwargs={self.kwargs})"


class DistinctMock(MongoMock):
    def __init__(self):
        super().__init__("distinct")

    def with_key(self, key: str, filter: Optional[dict] = None, **kwargs) -> "DistinctMock":
        self.query = (key, filter)
        self.kwargs = kwargs
        return self

    def __repr__(self):
        return f"DistinctMock(query={self.query}, kwargs={self.kwargs})"


class BulkWriteMock(MongoMock):
    def __init__(self):
        super().__init__("bulk_write")

    def with_operations(self, operations: list[Any], **kwargs) -> "BulkWriteMock":
        self.query = operations
        self.kwargs = kwargs
        return self

    def __repr__(self):
        return f"BulkWriteMock(query={self.query}, kwargs={self.kwargs})"


class CreateIndexMock(MongoMock):
    def __init__(self):
        super().__init__("create_index")

    def with_keys(self, keys: Union[str, dict, list[tuple], tuple[tuple]], **kwargs) -> "CreateIndexMock":
        self.query = keys
        self.kwargs = kwargs
        return self

    def __repr__(self):
        return f"CreateIndexMock(query={self.query}, kwargs={self.kwargs})"


class WireMongo:
    """Main class for mocking MongoDB operations"""

    def __init__(self, client=None):
        self.client = client or MockClient()
        self.mocks: list[MongoMock] = []
        self._original_methods = {}
        self._default_handlers = {}
        # Store collection objects per (database, collection) to avoid AsyncMock reuse issues
        self._collection_cache = {}

    def get_active_mocks(self) -> dict[str, dict[str, list[str]]]:
        """
        Returns a dictionary of all currently registered mocks.
        Format: { "database_name": { "collection_name": ["OperationMock(query=..., ...)", ...] } }
        """
        active_mocks = {}
        for mock in self.mocks:
            db = mock.database or "any_db"
            coll = mock.collection or "any_collection"
            
            if db not in active_mocks:
                active_mocks[db] = {}
            if coll not in active_mocks[db]:
                active_mocks[db][coll] = []
            
            active_mocks[db][coll].append(repr(mock))
        return active_mocks

    def find_candidates(self, database: str, collection: str, operation: str, *args, **kwargs) -> dict[str, Any]:
        """
        Finds all mocks registered for a specific call and reports if they match.
        Useful for debugging why a specific call isn't matching any mock.
        """
        candidates = [m for m in self.mocks if m.operation == operation 
                     and m.database == database 
                     and m.collection == collection]
        
        results = []
        for mock in candidates:
            results.append({
                "mock": repr(mock),
                "priority": mock._priority,
                "matches": mock.matches(*args, **kwargs)
            })
        
        return {
            "call": f"{database}.{collection}.{operation}(args={args}, kwargs={kwargs})",
            "total_candidates": len(candidates),
            "candidates": results
        }

    def mock(self, *mocks: MongoMock) -> "WireMongo":
        """Add mocks to be used"""
        self.mocks.extend(mocks)
        return self

    def _ensure_collection_has_async_methods(self, collection):
        """Ensure a collection mock has async methods for all supported operations."""
        # Always set async methods, don't check hasattr as MagicMock always returns something
        for operation in ASYNC_COLLECTION_OPERATIONS:
            setattr(collection, operation, AsyncMock(return_value=None))
        for operation in ASYNC_CURSOR_COLLECTION_OPERATIONS:
            setattr(collection, operation, MagicMock(return_value=AsyncCursor([])))
        for operation in ASYNC_COROUTINE_CURSOR_OPERATIONS:
            setattr(collection, operation, AsyncMock(return_value=AsyncCursor([])))
        return collection

    def _get_collection(self, database: str, collection: str):
        """Get or create a collection mock for the given database and collection.
        
        This ensures each (database, collection) pair gets a unique mock object,
        avoiding issues with AsyncMock reusing the same object for different keys.
        """
        key = (database, collection)
        if key not in self._collection_cache:
            # Create a new mock collection
            if isinstance(self.client, MockClient):
                # Use the client's normal __getitem__ behavior
                self._collection_cache[key] = self.client[database][collection]
            else:
                # For AsyncMock clients, we need to manually manage the hierarchy
                # to ensure each (db, collection) pair gets a unique object
                
                # Initialize the cache structures if needed
                if not hasattr(self.client, '_wiremongo_dbs'):
                    self.client._wiremongo_dbs = {}
                    # Save the original __getitem__ so we can fall back to it
                    self.client._original_getitem = self.client.__getitem__
                
                # Get or create database mock
                if database not in self.client._wiremongo_dbs:
                    db_mock = MagicMock(name=database)
                    db_mock._wiremongo_collections = {}
                    # Save original db __getitem__ for fallback
                    db_mock._original_getitem = db_mock.__getitem__
                    self.client._wiremongo_dbs[database] = db_mock
                
                db_mock = self.client._wiremongo_dbs[database]
                
                # Get or create collection mock
                if collection not in db_mock._wiremongo_collections:
                    coll_mock = MagicMock(name=f"{database}.{collection}")
                    # Ensure it has async methods
                    self._ensure_collection_has_async_methods(coll_mock)
                    db_mock._wiremongo_collections[collection] = coll_mock
                
                self._collection_cache[key] = db_mock._wiremongo_collections[collection]
                
        return self._collection_cache[key]

    def build(self):
        """Build the mock setup"""
        # Set up default handlers for all collections that have mocks
        collections = {(mock.database, mock.collection) for mock in self.mocks} if self.mocks else {("mock_db", "mock_collection")}

        for db, coll in collections:
            collection = self._get_collection(db, coll)
            operations = ALL_SUPPORTED_OPERATIONS

            for operation in operations:
                # Capture operation and collection info in local variables to avoid closure issues
                op = operation
                db_name = db
                coll_name = coll
                
                # Capture operation in closure by using default parameter
                def create_default_handler(op=op, *args, **kwargs):
                    raise AssertionError(f"No matching mock found for {op} args={args} kwargs={kwargs} - Candidates are {self.mocks}")

                key = (db_name, coll_name, op)
                if key not in self._original_methods:
                    self._original_methods[key] = getattr(collection, op, None)

                    if op in ASYNC_CURSOR_COLLECTION_OPERATIONS:
                        new_mock = default_handler = create_default_handler
                    elif op in ASYNC_COROUTINE_CURSOR_OPERATIONS:
                        # Capture operation value using default parameter to avoid closure issue
                        async def async_default_handler(op=op, *args, **kwargs):
                            raise AssertionError(f"No matching mock found for {op} args={args} kwargs={kwargs} - Candidates are {self.mocks}")
                        default_handler = async_default_handler
                        new_mock = AsyncMock(side_effect=default_handler)
                    else:
                        default_handler = async_partial(create_default_handler)
                        new_mock = AsyncMock(side_effect=default_handler)
                    self._default_handlers[key] = default_handler
                    setattr(collection, op, new_mock)

        # Helper function to create handlers - defined outside loop to avoid closure issues
        def create_handler(operation: str, database: str, collection_name: str):
            """Create a handler function for a specific operation, database, and collection."""
            if operation in ASYNC_COROUTINE_CURSOR_OPERATIONS:
                async def handler(*args, **kwargs):
                    # Look for specific mocks for this database/collection
                    candidates = [m for m in self.mocks if m.operation == operation and m.database == database and m.collection == collection_name]
                    # Also include catch-all None.None mocks as fallback
                    catch_all = [m for m in self.mocks if m.operation == operation and m.database is None and m.collection is None]
                    candidates.extend(catch_all)
                    matching_mocks = [(i, m) for i, m in enumerate(candidates) if m.matches(*args, **kwargs)]
                    if not matching_mocks:
                        raise AssertionError(f"No matching mock found for {operation}: args={args}, kwargs={kwargs} - Candidates are {candidates}")
                    idx, selected_mock = max(matching_mocks, key=lambda x: x[1]._priority)
                    return await selected_mock.get_result()
                return handler
            else:
                def handler(*args, **kwargs):
                    # Look for specific mocks for this database/collection
                    candidates = [m for m in self.mocks if m.operation == operation and m.database == database and m.collection == collection_name]
                    # Also include catch-all None.None mocks as fallback
                    catch_all = [m for m in self.mocks if m.operation == operation and m.database is None and m.collection is None]
                    candidates.extend(catch_all)
                    matching_mocks = [(i, m) for i, m in enumerate(candidates) if m.matches(*args, **kwargs)]
                    if not matching_mocks:
                        raise AssertionError(f"No matching mock found for {operation}: args={args}, kwargs={kwargs} - Candidates are {candidates}")
                    idx, selected_mock = max(matching_mocks, key=lambda x: x[1]._priority)
                    return selected_mock.get_result()
                return handler

        # Set up specific mock handlers - one per (database, collection, operation)
        handled_operations = set()
        for i, mock in enumerate(self.mocks):
            key = (mock.database, mock.collection, mock.operation)
            if key in handled_operations:
                continue
            handled_operations.add(key)
            
            collection = self._get_collection(mock.database, mock.collection)

            # Create new mock with the handler - pass values explicitly to avoid closure issues
            handler_func = create_handler(mock.operation, mock.database, mock.collection)
            if mock.operation in ASYNC_COROUTINE_CURSOR_OPERATIONS:
                new_mock = AsyncMock(side_effect=handler_func)
            elif mock.operation in ASYNC_CURSOR_COLLECTION_OPERATIONS:
                new_mock = handler_func
            else:
                new_mock = AsyncMock(side_effect=async_partial(handler_func))
            setattr(collection, mock.operation, new_mock)
        
        # Set up client access ONCE at the end, after all collections are cached
        if not isinstance(self.client, MockClient) and hasattr(self.client, '_wiremongo_dbs'):
            # Capture client, dbs, and the ensure method in closure
            client = self.client
            dbs = client._wiremongo_dbs
            ensure_async = self._ensure_collection_has_async_methods
            collection_cache = self._collection_cache
            
            # Override __getitem__ at client level to return our db mocks
            def client_getitem(mock_self, key):
                if key in dbs:
                    db = dbs[key]
                else:
                    # Create a new database on the fly
                    db = MagicMock(name=key)
                    db._wiremongo_collections = {}
                    dbs[key] = db
                
                # Capture db and collections in closure
                collections = db._wiremongo_collections
                
                # Override __getitem__ at db level to return our collection mocks
                def db_getitem(db_self, coll_key):
                    if coll_key in collections:
                        return collections[coll_key]
                    # Fall back: create a new collection with async methods on the fly
                    coll_mock = MagicMock(name=f"{key}.{coll_key}")
                    ensure_async(coll_mock)
                    collections[coll_key] = coll_mock
                    collection_cache[(key, coll_key)] = coll_mock
                    return coll_mock
                db.__getitem__ = db_getitem
                return db
            
            client.__getitem__ = client_getitem

    def reset(self):
        """Clear all mocks and restore original methods"""
        # Restore original methods
        for key, method in self._original_methods.items():
            db, coll, op = key
            if method is not None:
                collection = self._get_collection(db, coll)
                if op in ASYNC_CURSOR_COLLECTION_OPERATIONS:
                    new_mock = self._default_handlers[key]
                elif op in ASYNC_COROUTINE_CURSOR_OPERATIONS:
                    new_mock = AsyncMock(side_effect=self._default_handlers[key])
                else:
                    new_mock = AsyncMock(side_effect=async_partial(self._default_handlers[key]))
                setattr(collection, op, new_mock)

        self._original_methods.clear()
        self._default_handlers.clear()
        self._collection_cache.clear()
        self.mocks.clear()