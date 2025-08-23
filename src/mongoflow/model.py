"""Model base class for MongoFlow."""

from datetime import datetime
from typing import Any, ClassVar, Dict, List, Optional, Union

from bson import ObjectId

from mongoflow.exceptions import ModelError
from mongoflow.fields import Field, ObjectIdField
from mongoflow.query_builder import QueryBuilder
from mongoflow.repository import Repository


class ModelMeta(type):
    """Metaclass for Model to handle field definitions."""

    def __new__(mcs, name, bases, namespace):
        # Collect fields from class definition
        fields = {}
        for key, value in namespace.items():
            if isinstance(value, Field):
                fields[key] = value
                value.name = key

        # Store fields in class
        namespace['_fields'] = fields

        # Create the class
        cls = super().__new__(mcs, name, bases, namespace)

        # Set up repository if collection_name is defined
        if 'collection_name' in namespace:
            cls._repository = None

        return cls


class Model(metaclass=ModelMeta):
    """
    Base model class for MongoFlow.

    Example:
        >>> class User(Model):
        ...     collection_name = 'users'
        ...
        ...     name = StringField(required=True)
        ...     email = EmailField(unique=True)
        ...     age = IntField(min_value=0)
        ...
        >>> user = User(name='John', email='john@example.com')
        >>> user.save()
    """

    collection_name: ClassVar[Optional[str]] = None
    _fields: ClassVar[Dict[str, Field]] = {}
    _repository: ClassVar[Optional[Repository]] = None

    # Default fields
    _id = ObjectIdField()

    def __init__(self, **kwargs):
        """Initialize model with field values."""
        self._id = kwargs.pop('_id', None)
        self._is_new = self._id is None

        # Set field values
        for field_name, field in self._fields.items():
            value = kwargs.pop(field_name, field.get_default())
            setattr(self, field_name, value)

        # Store any extra attributes
        for key, value in kwargs.items():
            setattr(self, key, value)

    @classmethod
    def get_repository(cls) -> Repository:
        """Get or create repository for this model."""
        if cls._repository is None:
            if not cls.collection_name:
                raise ModelError(f"{cls.__name__} must define collection_name")

            # Create a dynamic repository class for this model
            class ModelRepository(Repository):
                collection_name = cls.collection_name

            cls._repository = ModelRepository()

        return cls._repository

    @classmethod
    def objects(cls) -> QueryBuilder:
        """Get query builder for this model."""
        return cls.get_repository().query()

    @classmethod
    def create(cls, **kwargs) -> 'Model':
        """Create and save a new model instance."""
        instance = cls(**kwargs)
        instance.save()
        return instance

    @classmethod
    def find(cls, id: Union[str, ObjectId]) -> Optional['Model']:
        """Find model by ID."""
        doc = cls.get_repository().find(id)
        if doc:
            return cls.from_dict(doc)
        return None

    @classmethod
    def find_by(cls, **kwargs) -> Optional['Model']:
        """Find model by field values."""
        doc = cls.get_repository().find_by(**kwargs)
        if doc:
            return cls.from_dict(doc)
        return None

    @classmethod
    def all(cls) -> List['Model']:
        """Get all model instances."""
        docs = cls.get_repository().all()
        return [cls.from_dict(doc) for doc in docs]

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Model':
        """Create model instance from dictionary."""
        return cls(**data)

    def to_dict(self, include_id: bool = True) -> Dict[str, Any]:
        """Convert model to dictionary."""
        data = {}

        if include_id and self._id:
            data['_id'] = str(self._id) if isinstance(self._id, ObjectId) else self._id

        # Add field values
        for field_name in self._fields:
            value = getattr(self, field_name, None)
            if value is not None:
                if isinstance(value, datetime):
                    value = value.isoformat()
                elif isinstance(value, ObjectId):
                    value = str(value)
                elif isinstance(value, Model):
                    value = value.to_dict()
                data[field_name] = value

        # Add any extra attributes
        for key, value in self.__dict__.items():
            if not key.startswith('_') and key not in data and key not in self._fields:
                data[key] = value

        return data

    def save(self) -> 'Model':
        """Save model to database."""
        try:
            repo = self.get_repository()
            data = self.to_dict(include_id=False)

            if self._is_new:
                # Create new document
                result = repo.create(data)
                self._id = result['_id']
                self._is_new = False
            else:
                # Update existing document
                repo.update(self._id, data)

            return self
        except Exception as e:
            raise ModelError(f"Failed to save {self.__class__.__name__}: {e}")

    def delete(self) -> bool:
        """Delete model from database."""
        if self._id:
            return self.get_repository().delete(self._id)
        return False

    def reload(self) -> 'Model':
        """Reload model from database."""
        if self._id:
            doc = self.get_repository().find(self._id)
            if doc:
                for key, value in doc.items():
                    setattr(self, key, value)
        return self

    def update(self, **kwargs) -> 'Model':
        """Update model fields and save."""
        for key, value in kwargs.items():
            setattr(self, key, value)
        return self.save()

    def __repr__(self) -> str:
        """String representation of model."""
        return f"{self.__class__.__name__}(id={self._id})"

    def __eq__(self, other) -> bool:
        """Check model equality."""
        if not isinstance(other, self.__class__):
            return False
        return self._id == other._id

    def __hash__(self) -> int:
        """Get model hash."""
        return hash(self._id) if self._id else hash(id(self))
