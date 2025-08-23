from mongoflow import MongoFlow, Repository

# Connect to MongoDB
MongoFlow.connect('mongodb://localhost:27017', 'mydb')

# Define a repository
class UserRepository(Repository):
    collection_name = 'users'

    def find_active_users(self):
        return self.where('status', 'active').get()

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

# Find one
user = users.find('user_id')
user = users.find_by(email='john@example.com')

# Update
users.update('user_id', {'status': 'inactive'})

# Delete
users.delete('user_id')
