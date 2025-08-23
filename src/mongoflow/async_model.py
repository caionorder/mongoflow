"""Async model implementation for MongoFlow."""

from typing import ClassVar, List, Optional, Union

from bson import ObjectId

from mongoflow.async_repository import AsyncRepository
from mongoflow.exceptions import ModelError
from mongoflow.model import ModelMeta


class AsyncModel(metaclass=ModelMeta):
    """
    Async model base class.

    Example:
        >>> class User(AsyncModel):
        ...     collection_name = 'users'
        ...     name = StringField(required=True)
        ...
        >>> user = User(name='John')
        >>> await user.save()
    """

    collection_name: ClassVar[Optional[str]] = None
    _repository: ClassVar[Optional[AsyncRepository]] = None

    @classmethod
    def get_repository(cls) -> AsyncRepository:
        """Get or create async repository."""
        if cls._repository is None:
            if not cls.collection_name:
                raise ModelError(f"{cls.__name__} must define collection_name")

            class ModelAsyncRepository(AsyncRepository):
                collection_name = cls.collection_name

            cls._repository = ModelAsyncRepository()

        return cls._repository

    @classmethod
    async def create(cls, **kwargs) -> 'AsyncModel':
        """Create and save a new model instance."""
        instance = cls(**kwargs)
        await instance.save()
        return instance

    @classmethod
    async def find(cls, id: Union[str, ObjectId]) -> Optional['AsyncModel']:
        """Find model by ID."""
        repo = cls.get_repository()
        doc = await repo.find(id)
        if doc:
            return cls.from_dict(doc)
        return None

    @classmethod
    async def find_by(cls, **kwargs) -> Optional['AsyncModel']:
        """Find model by field values."""
        repo = cls.get_repository()
        doc = await repo.find_by(**kwargs)
        if doc:
            return cls.from_dict(doc)
        return None

    @classmethod
    async def all(cls) -> List['AsyncModel']:
        """Get all model instances."""
        repo = cls.get_repository()
        docs = await repo.all()
        return [cls.from_dict(doc) for doc in docs]

    async def save(self) -> 'AsyncModel':
        """Save model to database."""
        try:
            repo = self.get_repository()
            data = self.to_dict(include_id=False)

            if self._is_new:
                result = await repo.create(data)
                self._id = result['_id']
                self._is_new = False
            else:
                await repo.update(self._id, data)

            return self
        except Exception as e:
            raise ModelError(f"Failed to save {self.__class__.__name__}: {e}")

    async def delete(self) -> bool:
        """Delete model from database."""
        if self._id:
            repo = self.get_repository()
            return await repo.delete(self._id)
        return False

    async def reload(self) -> 'AsyncModel':
        """Reload model from database."""
        if self._id:
            repo = self.get_repository()
            doc = await repo.find(self._id)
            if doc:
                for key, value in doc.items():
                    setattr(self, key, value)
        return self

    async def update(self, **kwargs) -> 'AsyncModel':
        """Update model fields and save."""
        for key, value in kwargs.items():
            setattr(self, key, value)
        return await self.save()
