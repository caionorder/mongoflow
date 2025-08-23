#!/usr/bin/env python
"""Async usage example for MongoFlow."""

import asyncio
from datetime import datetime

from mongoflow import AsyncMongoFlow
from mongoflow.async_model import AsyncModel
from mongoflow.async_repository import AsyncRepository
from mongoflow.fields import EmailField, IntField, StringField


# Define async repository
class AsyncUserRepository(AsyncRepository):
    collection_name = 'async_users'

    indexes = [
        {'keys': [('email', 1)], 'unique': True},
        {'keys': [('created_at', -1)]},
    ]

    async def find_active_users(self):
        """Find all active users."""
        collection = await self.get_collection()
        query = self.query()
        query._collection = collection
        return await query.where('status', 'active').get()

    async def get_user_stats(self):
        """Get user statistics."""
        pipeline = [
            {'$group': {
                '_id': '$status',
                'count': {'$sum': 1},
                'avg_age': {'$avg': '$age'}
            }}
        ]
        return await self.aggregate(pipeline)


# Define async model
class AsyncUser(AsyncModel):
    collection_name = 'async_users'

    name = StringField(required=True, max_length=100)
    email = EmailField(required=True)
    age = IntField(min_value=0, max_value=150)
    status = StringField(choices=['active', 'inactive'], default='active')


async def basic_crud_example():
    """Basic CRUD operations with async."""
    print("\n=== Basic CRUD Example ===")

    repo = AsyncUserRepository()

    # Create
    print("\nCreating users...")
    user1 = await repo.create({
        'name': 'Async John',
        'email': 'john@async.com',
        'age': 30,
        'status': 'active'
    })
    print(f"Created: {user1}")

    user2 = await repo.create({
        'name': 'Async Jane',
        'email': 'jane@async.com',
        'age': 25,
        'status': 'active'
    })

    # Read
    print("\nFinding user...")
    user = await repo.find(user1['_id'])
    print(f"Found: {user}")

    # Update
    print("\nUpdating user...")
    updated = await repo.update(user1['_id'], {'age': 31})
    print(f"Updated: {updated}")

    # Delete
    print("\nDeleting user...")
    deleted = await repo.delete(user2['_id'])
    print(f"Deleted: {deleted}")

    # List all
    print("\nAll users:")
    all_users = await repo.all()
    for u in all_users:
        print(f"  - {u['name']}")


async def query_builder_example():
    """Query builder example with async."""
    print("\n=== Query Builder Example ===")

    repo = AsyncUserRepository()

    # Setup test data
    test_users = [
        {'name': 'Alice', 'email': 'alice@test.com', 'age': 28, 'status': 'active'},
        {'name': 'Bob', 'email': 'bob@test.com', 'age': 35, 'status': 'inactive'},
        {'name': 'Charlie', 'email': 'charlie@test.com', 'age': 42, 'status': 'active'},
        {'name': 'Diana', 'email': 'diana@test.com', 'age': 23, 'status': 'active'},
    ]

    await repo.truncate()
    await repo.create_many(test_users)

    # Complex query
    print("\nActive users over 25:")
    collection = await repo.get_collection()
    query = repo.query()
    query._collection = collection

    results = await (query
        .where('status', 'active')
        .where_greater_than('age', 25)
        .order_by('age', 'desc')
        .get())

    for user in results:
        print(f"  - {user['name']} (age: {user['age']})")

    # Pagination
    print("\nPaginated results:")
    page_results = await query.paginate(page=1, per_page=2)
    print(f"  Total: {page_results['total']}")
    print(f"  Pages: {page_results['pages']}")

    # Aggregation
    print("\nUser statistics:")
    stats = await repo.get_user_stats()
    for stat in stats:
        print(f"  Status: {stat['_id']}, Count: {stat['count']}")


async def streaming_example():
    """Streaming example for large datasets."""
    print("\n=== Streaming Example ===")

    repo = AsyncUserRepository()

    # Create many users
    print("Creating 100 test users...")
    users = [
        {
            'name': f'User {i}',
            'email': f'user{i}@test.com',
            'age': 20 + (i % 50),
            'status': 'active' if i % 2 == 0 else 'inactive'
        }
        for i in range(100)
    ]

    await repo.truncate()
    await repo.create_many(users)

    # Stream results
    print("\nStreaming users (batch size: 10):")
    collection = await repo.get_collection()
    query = repo.query()
    query._collection = collection

    count = 0
    async for user in query.stream(batch_size=10):
        count += 1
        if count <= 5:
            print(f"  Processing: {user['name']}")
        elif count == 6:
            print("  ...")

    print(f"Total processed: {count}")


async def model_example():
    """Model usage example."""
    print("\n=== Model Example ===")

    # Create user using model
    print("\nCreating user with model...")
    user = AsyncUser(
        name='Model User',
        email='model@user.com',
        age=30
    )
    await user.save()
    print(f"Created: {user}")

    # Find user
    print("\nFinding user...")
    found = await AsyncUser.find(user._id)
    print(f"Found: {found}")

    # Update user
    print("\nUpdating user...")
    await found.update(age=31)
    print(f"Updated age: {found.age}")

    # Get all users
    print("\nAll model users:")
    all_users = await AsyncUser.all()
    for u in all_users:
        print(f"  - {u.name}")

    # Delete user
    print("\nDeleting user...")
    await found.delete()
    print("User deleted")


async def concurrent_operations():
    """Concurrent operations example."""
    print("\n=== Concurrent Operations Example ===")

    repo = AsyncUserRepository()
    await repo.truncate()

    # Create users concurrently
    print("\nCreating 10 users concurrently...")

    async def create_user(i):
        return await repo.create({
            'name': f'Concurrent User {i}',
            'email': f'concurrent{i}@test.com',
            'age': 20 + i,
            'status': 'active'
        })

    # Run concurrent creates
    start_time = datetime.utcnow()
    tasks = [create_user(i) for i in range(10)]
    results = await asyncio.gather(*tasks)
    end_time = datetime.utcnow()

    print(f"Created {len(results)} users in {(end_time - start_time).total_seconds():.2f} seconds")

    # Concurrent reads
    print("\nReading users concurrently...")

    async def find_user(user_id):
        return await repo.find(user_id)

    user_ids = [r['_id'] for r in results[:5]]
    tasks = [find_user(uid) for uid in user_ids]
    found_users = await asyncio.gather(*tasks)

    print(f"Found {len(found_users)} users concurrently")


async def main():
    """Run all async examples."""
    # Connect to MongoDB
    await AsyncMongoFlow.connect(
        uri='mongodb://localhost:27017',
        database='async_example_db'
    )

    try:
        # Run examples
        await basic_crud_example()
        await query_builder_example()
        await streaming_example()
        await model_example()
        await concurrent_operations()

    finally:
        # Cleanup
        print("\n=== Cleanup ===")
        repo = AsyncUserRepository()
        await repo.truncate()
        print("Database cleaned")

        # Disconnect
        await AsyncMongoFlow.disconnect()
        print("Disconnected from MongoDB")


if __name__ == '__main__':
    # Run async main
    asyncio.run(main())
