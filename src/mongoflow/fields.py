"""Field definitions and validators for MongoFlow models."""

from datetime import datetime
from typing import Any, Callable, List, Optional, Type, Union

from bson import ObjectId


class Field:
    """
    Base field class for model definitions.

    Example:
        >>> class User:
        ...     name = Field(required=True, max_length=100)
        ...     age = Field(field_type=int, min_value=0)
    """

    def __init__(
        self,
        field_type: Optional[Type] = None,
        required: bool = False,
        default: Any = None,
        default_factory: Optional[Callable] = None,
        validators: Optional[List[Callable]] = None,
        unique: bool = False,
        index: bool = False,
        min_length: Optional[int] = None,
        max_length: Optional[int] = None,
        min_value: Optional[Union[int, float]] = None,
        max_value: Optional[Union[int, float]] = None,
        choices: Optional[List[Any]] = None,
        description: Optional[str] = None,
    ):
        """Initialize field with validation rules."""
        self.field_type = field_type
        self.required = required
        self.default = default
        self.default_factory = default_factory
        self.validators = validators or []
        self.unique = unique
        self.index = index
        self.min_length = min_length
        self.max_length = max_length
        self.min_value = min_value
        self.max_value = max_value
        self.choices = choices
        self.description = description
        self.name = None  # Set by metaclass

    def validate(self, value: Any) -> Any:
        """Validate field value."""
        # Check required
        if value is None:
            if self.required:
                raise ValueError(f"{self.name} is required")
            return self.get_default()

        # Type check
        if self.field_type and not isinstance(value, self.field_type):
            try:
                value = self.field_type(value)
            except (TypeError, ValueError):
                raise ValueError(f"{self.name} must be of type {self.field_type.__name__}")

        # Length validation
        if self.min_length is not None and len(value) < self.min_length:
            raise ValueError(f"{self.name} must be at least {self.min_length} characters")

        if self.max_length is not None and len(value) > self.max_length:
            raise ValueError(f"{self.name} must be at most {self.max_length} characters")

        # Value range validation
        if self.min_value is not None and value < self.min_value:
            raise ValueError(f"{self.name} must be at least {self.min_value}")

        if self.max_value is not None and value > self.max_value:
            raise ValueError(f"{self.name} must be at most {self.max_value}")

        # Choices validation
        if self.choices and value not in self.choices:
            raise ValueError(f"{self.name} must be one of {self.choices}")

        # Custom validators
        for validator in self.validators:
            if not validator(value):
                raise ValueError(f"{self.name} validation failed")

        return value

    def get_default(self) -> Any:
        """Get default value for field."""
        if self.default_factory:
            return self.default_factory()
        return self.default

    def __set_name__(self, owner, name):
        """Set field name when class is created."""
        self.name = name

    def __get__(self, instance, owner):
        """Get field value from instance."""
        if instance is None:
            return self
        return instance.__dict__.get(self.name, self.get_default())

    def __set__(self, instance, value):
        """Set field value on instance."""
        instance.__dict__[self.name] = self.validate(value)


class StringField(Field):
    """String field with additional string-specific validations."""

    def __init__(self, **kwargs):
        kwargs.setdefault('field_type', str)
        super().__init__(**kwargs)


class IntField(Field):
    """Integer field."""

    def __init__(self, **kwargs):
        kwargs.setdefault('field_type', int)
        super().__init__(**kwargs)


class FloatField(Field):
    """Float field."""

    def __init__(self, **kwargs):
        kwargs.setdefault('field_type', float)
        super().__init__(**kwargs)


class BoolField(Field):
    """Boolean field."""

    def __init__(self, **kwargs):
        kwargs.setdefault('field_type', bool)
        super().__init__(**kwargs)


class DateTimeField(Field):
    """DateTime field with auto_now and auto_now_add support."""

    def __init__(self, auto_now: bool = False, auto_now_add: bool = False, **kwargs):
        kwargs.setdefault('field_type', datetime)
        self.auto_now = auto_now
        self.auto_now_add = auto_now_add
        super().__init__(**kwargs)

    def get_default(self) -> Any:
        """Get default value, handling auto timestamps."""
        if self.auto_now or self.auto_now_add:
            return datetime.utcnow()
        return super().get_default()


class ObjectIdField(Field):
    """MongoDB ObjectId field."""

    def __init__(self, **kwargs):
        kwargs.setdefault('field_type', ObjectId)
        super().__init__(**kwargs)

    def validate(self, value: Any) -> Any:
        """Validate and convert to ObjectId."""
        if value is None:
            return super().validate(value)

        if isinstance(value, str):
            try:
                value = ObjectId(value)
            except Exception:
                raise ValueError(f"{self.name} must be a valid ObjectId")

        return super().validate(value)


class ListField(Field):
    """List field with item validation."""

    def __init__(self, item_field: Optional[Field] = None, **kwargs):
        kwargs.setdefault('field_type', list)
        self.item_field = item_field
        super().__init__(**kwargs)

    def validate(self, value: Any) -> Any:
        """Validate list and its items."""
        value = super().validate(value)

        if value is not None and self.item_field:
            validated_items = []
            for item in value:
                validated_items.append(self.item_field.validate(item))
            return validated_items

        return value


class DictField(Field):
    """Dictionary field."""

    def __init__(self, **kwargs):
        kwargs.setdefault('field_type', dict)
        super().__init__(**kwargs)


class EmailField(StringField):
    """Email field with validation."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.validators.append(self._validate_email)

    @staticmethod
    def _validate_email(value: str) -> bool:
        """Basic email validation."""
        import re
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, value))


class URLField(StringField):
    """URL field with validation."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.validators.append(self._validate_url)

    @staticmethod
    def _validate_url(value: str) -> bool:
        """Basic URL validation."""
        import re
        pattern = r'^https?://[^\s/$.?#].[^\s]*$'
        return bool(re.match(pattern, value))


class ReferenceField(ObjectIdField):
    """Reference to another document."""

    def __init__(self, reference_model: Optional[Type] = None, **kwargs):
        self.reference_model = reference_model
        super().__init__(**kwargs)


class EmbeddedDocumentField(Field):
    """Embedded document field."""

    def __init__(self, document_class: Type, **kwargs):
        self.document_class = document_class
        kwargs.setdefault('field_type', dict)
        super().__init__(**kwargs)

    def validate(self, value: Any) -> Any:
        """Validate embedded document."""
        if value is None:
            return super().validate(value)

        if isinstance(value, dict):
            # Convert dict to document instance
            return self.document_class(**value)
        elif isinstance(value, self.document_class):
            return value
        else:
            raise ValueError(f"{self.name} must be a {self.document_class.__name__}")
