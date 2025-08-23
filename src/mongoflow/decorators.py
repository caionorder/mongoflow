"""Decorators for MongoFlow."""

import functools
import time
from typing import Callable, Optional, TypeVar

from mongoflow.exceptions import MongoFlowError

T = TypeVar("T")


def retry_on_error(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: tuple = (Exception,)
) -> Callable:
    """
    Retry decorator for handling transient errors.

    Args:
        max_attempts: Maximum number of retry attempts
        delay: Initial delay between retries in seconds
        backoff: Backoff multiplier for delay
        exceptions: Tuple of exceptions to catch

    Example:
        >>> @retry_on_error(max_attempts=3, delay=1.0)
        ... def fetch_data():
        ...     return api_call()
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
            last_exception = None
            current_delay = delay

            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        time.sleep(current_delay)
                        current_delay *= backoff
                    else:
                        raise

            raise last_exception

        return wrapper
    return decorator


def cache_result(ttl: int = 300) -> Callable:
    """
    Cache decorator for method results.

    Args:
        ttl: Time to live in seconds

    Example:
        >>> @cache_result(ttl=60)
        ... def expensive_operation():
        ...     return compute_result()
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        cache = {}
        cache_time = {}

        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
            # Create cache key from arguments
            key = str(args) + str(kwargs)

            # Check if cached and not expired
            if key in cache:
                if time.time() - cache_time[key] < ttl:
                    return cache[key]

            # Compute and cache result
            result = func(*args, **kwargs)
            cache[key] = result
            cache_time[key] = time.time()

            return result

        # Add method to clear cache
        wrapper.clear_cache = lambda: (cache.clear(), cache_time.clear())

        return wrapper
    return decorator


def validate_input(**validators) -> Callable:
    """
    Validate input parameters decorator.

    Args:
        **validators: Validation functions for parameters

    Example:
        >>> @validate_input(age=lambda x: x >= 0)
        ... def set_age(age: int):
        ...     return age
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
            # Get function signature
            import inspect
            sig = inspect.signature(func)
            bound = sig.bind(*args, **kwargs)
            bound.apply_defaults()

            # Validate each parameter
            for param_name, validator in validators.items():
                if param_name in bound.arguments:
                    value = bound.arguments[param_name]
                    if not validator(value):
                        raise ValueError(f"Invalid value for {param_name}: {value}")

            return func(*args, **kwargs)

        return wrapper
    return decorator


def benchmark(func: Callable[..., T]) -> Callable[..., T]:
    """
    Benchmark decorator to measure execution time.

    Example:
        >>> @benchmark
        ... def slow_operation():
        ...     time.sleep(1)
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs) -> T:
        start_time = time.perf_counter()
        result = func(*args, **kwargs)
        end_time = time.perf_counter()

        print(f"{func.__name__} took {end_time - start_time:.4f} seconds")
        return result

    return wrapper


def deprecated(message: Optional[str] = None) -> Callable:
    """
    Mark a function as deprecated.

    Args:
        message: Optional deprecation message

    Example:
        >>> @deprecated("Use new_function instead")
        ... def old_function():
        ...     pass
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
            import warnings

            msg = message or f"{func.__name__} is deprecated"
            warnings.warn(msg, DeprecationWarning, stacklevel=2)

            return func(*args, **kwargs)

        return wrapper
    return decorator


def synchronized(lock=None) -> Callable:
    """
    Thread synchronization decorator.

    Args:
        lock: Optional lock object, creates new one if None

    Example:
        >>> import threading
        >>> lock = threading.Lock()
        >>>
        >>> @synchronized(lock)
        ... def critical_section():
        ...     # Thread-safe code
        ...     pass
    """
    import threading

    if lock is None:
        lock = threading.Lock()

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
            with lock:
                return func(*args, **kwargs)

        return wrapper
    return decorator


def lazy_property(func: Callable[..., T]) -> property:
    """
    Lazy property decorator - computes value once and caches it.

    Example:
        >>> class MyClass:
        ...     @lazy_property
        ...     def expensive_property(self):
        ...         return compute_expensive_value()
    """
    attr_name = f"_lazy_{func.__name__}"

    @functools.wraps(func)
    def wrapper(self) -> T:
        if not hasattr(self, attr_name):
            setattr(self, attr_name, func(self))
        return getattr(self, attr_name)

    return property(wrapper)


def ensure_connection(func: Callable[..., T]) -> Callable[..., T]:
    """
    Ensure MongoDB connection is established before executing method.

    Example:
        >>> @ensure_connection
        ... def query_database(self):
        ...     return self.collection.find()
    """
    @functools.wraps(func)
    def wrapper(self, *args, **kwargs) -> T:
        # Check if connection exists
        if not hasattr(self, '_connection') or self._connection is None:
            raise MongoFlowError("No database connection established")

        # Check if connection is alive
        try:
            self._connection.client.admin.command('ping')
        except Exception as e:
            raise MongoFlowError(f"Database connection lost: {e}")

        return func(self, *args, **kwargs)

    return wrapper
