# MongoFlow 🌊

Elegant MongoDB Object Document Mapper (ODM) for Python - with a fluent query builder that makes working with MongoDB a breeze! 🚀

## ✨ Features

- 🎯 **Intuitive Query Builder** - Fluent, chainable queries that feel natural
- ⚡ **High Performance** - Connection pooling, batch operations, and streaming
- 🔧 **Flexible** - Use as simple queries or full ODM with models
- 🎨 **Clean API** - Pythonic, fully typed, and well-documented
- 🚀 **Production Ready** - Battle-tested patterns with automatic retries
- 💾 **Smart Caching** - Optional Redis integration for blazing speed
- 🔄 **Async Support** - Full async/await support with Motor
- 📦 **Lightweight** - Minimal dependencies, maximum functionality

## 📦 Installation

```bash
# Basic installation
pip install mongoflow

# With all features
pip install mongoflow[all]

# With specific features
pip install mongoflow[cache]      # Redis caching
pip install mongoflow[validation] # Pydantic validation
pip install mongoflow[async]      # Async support
```

## 🚀 Quick Start

### Basic Usage

```python
from mongoflow import MongoFlow, Repository

# Connect to MongoDB
MongoFlow.connect('mongodb://localhost:27017', 'mydb')

# Define a repository
class UserRepository(Repository):
    collection_name = 'users'

# Use it!
users = UserRepository()

# Create
user = users.create({
    'name': 'John Doe',
    'email': 'john@example.com',
    'age': 30
})

# Query with fluent builder
active_adults = (users.query()
    .where('status', 'active')
    .where_greater_than('age', 18)
    .order_by('created_at', 'desc')
    .limit(10)
    .get())
```

### Async Support

```python
import asyncio
from mongoflow import AsyncMongoFlow, AsyncRepository

class AsyncUserRepository(AsyncRepository):
    collection_name = 'users'

async def main():
    # Connect
    await AsyncMongoFlow.connect('mongodb://localhost:27017', 'mydb')
    
    repo = AsyncUserRepository()
    
    # All methods support async/await
    user = await repo.create({'name': 'Jane'})
    users = await repo.query().where('active', True).get()
    
    # Async streaming for large datasets
    async for user in repo.query().stream():
        print(user)

asyncio.run(main())
```

## 📚 Query Builder Methods

Both sync and async query builders support the following methods:

### Filtering Methods

```python
# Basic where conditions
.where('field', 'value')                    # field == value
.where('field', 'value', '$ne')            # field != value
.where_in('field', [1, 2, 3])              # field in [1, 2, 3]
.where_not_in('field', [1, 2, 3])          # field not in [1, 2, 3]
.where_between('field', min, max)          # min <= field <= max
.where_greater_than('field', value)        # field > value
.where_less_than('field', value)           # field < value
.where_like('field', 'pattern')            # regex pattern matching
.where_null('field')                        # field is null
.where_not_null('field')                    # field is not null
.where_exists('field', True)               # field exists in document

# Logical operators
.or_where([{'field1': 'value1'}, {'field2': 'value2'}])
.and_where([{'field1': 'value1'}, {'field2': 'value2'}])
```

### Query Modifiers

```python
# Projection
.select('field1', 'field2')                # Include only these fields
.exclude('field1', 'field2')               # Exclude these fields

# Sorting and pagination
.order_by('field', 'asc')                  # Sort ascending
.order_by('field', 'desc')                 # Sort descending
.skip(10)                                   # Skip N documents
.limit(20)                                  # Limit to N documents
.paginate(page=2, per_page=20)            # Get paginated results
```

### Execution Methods

```python
# Sync methods
.get()                                      # Get all results
.first()                                    # Get first result
.last()                                     # Get last result
.count()                                    # Count matching documents
.exists()                                   # Check if any documents exist
.distinct('field')                          # Get distinct values
.stream(batch_size=100)                    # Stream results

# Async methods (same as above but with await)
await query.get()
await query.first()
await query.last()
await query.count()
await query.exists()
await query.distinct('field')
async for doc in query.stream():
    process(doc)
```

### Aggregation Methods

```python
# Simple aggregations
.sum('field')                               # Sum of field values
.avg('field')                               # Average of field values
.min('field')                               # Minimum value
.max('field')                               # Maximum value

# Group operations
.group('status', {'count': {'$sum': 1}})   # Group by field
.group(
    {'status': '$status', 'type': '$type'},  # Group by multiple fields
    {'total': {'$sum': '$amount'}}           # With aggregations
)

# Custom aggregation pipelines
.aggregate([
    {'$match': {'status': 'active'}},
    {'$group': {'_id': '$category', 'total': {'$sum': '$amount'}}}
])
```

### Async-Specific Features

All the above methods work with async query builders, just remember to use `await`:

```python
# Async examples
users = await users.query().where('active', True).get()
count = await users.query().where_between('age', 18, 65).count()
stats = await users.query().group('role', {'count': {'$sum': 1}})

# Async streaming
async for user in users.query().where('status', 'active').stream():
    await process_user(user)
