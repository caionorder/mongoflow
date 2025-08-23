#!/usr/bin/env python
"""Basic usage examples for MongoFlow."""

from mongoflow import MongoFlow, Repository
from mongoflow.mixins import SoftDeleteMixin, TimestampMixin


def main():
    """Run basic usage examples."""

    # Connect to MongoDB
    MongoFlow.connect(
        uri='mongodb://localhost:27017',
        database='example_db'
    )

    # Define a repository with mixins
    class UserRepository(Repository, TimestampMixin, SoftDeleteMixin):
        collection_name = 'users'

        def find_active_adults(self):
            """Custom method to find active adult users."""
            return (self.query()
                   .where('status', 'active')
                   .where_greater_than('age', 18)
                   .order_by('created_at', 'desc')
                   .get())

    # Initialize repository
    users = UserRepository()

    # Create users
    print("Creating users...")
    user1 = users.create({
        'name': 'John Doe',
        'email': 'john@example.com',
        'age': 30,
        'status': 'active'
    })
    print(f"Created user: {user1}")

    user2 = users.create({
        'name': 'Jane Smith',
        'email': 'jane@example.com',
        'age': 25,
        'status': 'active'
    })

    # Query users
    print("\nQuerying active users...")
    active_users = users.where('status', 'active').get()
    print(f"Found {len(active_users)} active users")

    # Use custom method
    print("\nFinding active adults...")
    adults = users.find_active_adults()
    for user in adults:
        print(f"  - {user['name']} ({user['age']} years old)")

    # Update user
    print(f"\nUpdating user {user1['_id']}...")
    users.update(user1['_id'], {'age': 31})

    # Soft delete
    print(f"\nSoft deleting user {user2['_id']}...")
    users.soft_delete(user2['_id'])

    # Query with soft delete
    print("\nActive users (excluding soft deleted):")
    for user in users.query().get():
        print(f"  - {user['name']}")

    print("\nAll users (including soft deleted):")
    for user in users.with_trashed().get():
        print(f"  - {user['name']} {'(deleted)' if user.get('deleted_at') else ''}")

    # Aggregation example
    print("\nUser statistics by status:")
    pipeline = [
        {'$group': {
            '_id': '$status',
            'count': {'$sum': 1},
            'avg_age': {'$avg': '$age'}
        }}
    ]
    stats = users.query().aggregate(pipeline)
    for stat in stats:
        print(f"  Status: {stat['_id']}, Count: {stat['count']}, Avg Age: {stat.get('avg_age', 0):.1f}")

    # Pagination example
    print("\nPaginated results (page 1, 2 items per page):")
    page_result = users.query().paginate(page=1, per_page=2)
    print(f"  Total items: {page_result['total']}")
    print(f"  Total pages: {page_result['pages']}")
    print("  Current page items:")
    for item in page_result['items']:
        print(f"    - {item['name']}")

    # Clean up
    print("\nCleaning up...")
    users.truncate()
    print("Done!")


if __name__ == '__main__':
    main()
