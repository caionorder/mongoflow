from mongoflow import MongoFlow, Repository

# Connect to MongoDB
MongoFlow.connect('mongodb://localhost:27017', 'mydb')

# Define a repository
class UserRepository(Repository):
    collection_name = 'users'

    def find_active_users(self):
        return self.query().where('status', 'active').get()

    def find_adults(self):
        return self.query().where_greater_than('age', 18).get()

# Use it!
users = UserRepository()

# Create
user = users.create({
    'name': 'John Doe',
    'email': 'john@example.com',
    'age': 30,
    'status': 'active'
})

# Query with fluent builder
active_adults = (users.query()
    .where('status', 'active')
    .where_greater_than('age', 18)
    .order_by('created_at', 'desc')
    .limit(10)
    .get())

# New query methods examples
# Filter by range
users_in_age_range = users.query().where_between('age', 25, 35).get()

# Check existence
has_active_users = users.query().where('status', 'active').exists()

# Get distinct values
distinct_statuses = users.query().distinct('status')

# Aggregation examples
total_age = users.query().sum('age')
average_age = users.query().avg('age')
min_age = users.query().min('age')
max_age = users.query().max('age')

# Group by status and count
user_stats = users.query().group('status', {'count': {'$sum': 1}})

# Complex grouping
age_groups = users.query().group(
    {'age_group': {'$divide': ['$age', 10]}},
    {'count': {'$sum': 1}, 'avg_age': {'$avg': '$age'}}
)

# Logical operators
admin_or_moderator = users.query().or_where([
    {'role': 'admin'},
    {'role': 'moderator'}
]).get()

# Check if field exists
users_with_avatar = users.query().where_exists('avatar_url', True).get()

# Get last user
last_user = users.query().order_by('created_at', 'desc').last()

# Find one
user = users.find('user_id')
user = users.find_by(email='john@example.com')

# Update
users.update('user_id', {'status': 'inactive'})

# Delete
users.delete('user_id')
