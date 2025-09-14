# Predictable Cache Keys for Django Views

This document describes how to use predictable cache keys with Django's `cache_page` decorator, allowing developers to know and predict cache keys for invalidation purposes.

## Problem

The standard Django `cache_page` decorator generates cache keys internally, making it difficult for developers to know the exact cache key for invalidation. This is particularly problematic when you need to invalidate cache entries when models are saved or when specific conditions are met.

## Solution

We provide an enhanced `cache_page_with_key` decorator and utility functions that make cache keys predictable and accessible.

## Basic Usage

### Using the Enhanced Decorator

```python
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page_with_key
from rest_framework.viewsets import ViewSet
from rest_framework.response import Response

class UserViewSet(ViewSet):
    @method_decorator(cache_page_with_key(60 * 60 * 2))  # 2 hours
    def list(self, request, format=None):
        content = {
            "user_feed": request.user.get_user_feed(),
        }
        return Response(content)
```

### Getting Cache Keys

There are several ways to get the cache key for a view:

#### Method 1: Using the View's Cache Key Method

```python
# Get cache key for a specific request
cache_key = UserViewSet.list.get_cache_key(request)
print(f"Cache key: {cache_key}")
```

#### Method 2: Using Utility Functions

```python
from django.utils.cache_keys import get_view_cache_key

# Get cache key using utility function
cache_key = get_view_cache_key(UserViewSet.list, request)
print(f"Cache key: {cache_key}")
```

## Cache Invalidation

### Invalidating Specific Cache Entries

```python
from django.utils.cache_keys import invalidate_view_cache
from django.core.cache import cache

# Method 1: Using the utility function
invalidated = invalidate_view_cache(UserViewSet.list, request)

# Method 2: Manual invalidation
cache_key = UserViewSet.list.get_cache_key(request)
cache.delete(cache_key)
```

### Model Save Signal Example

```python
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils.cache_keys import get_view_cache_key

@receiver(post_save, sender=User)
def invalidate_user_cache(sender, instance, **kwargs):
    """Invalidate cache when a user is saved."""
    # Create a mock request for cache key generation
    request = HttpRequest()
    request.method = 'GET'
    request.META = {'HTTP_HOST': 'example.com'}
    request.path = '/api/users/'
    
    # Invalidate cache
    cache_key = get_view_cache_key(UserViewSet.list, request)
    cache.delete(cache_key)
```

## User-Specific Cache Keys

For user-specific cached views, you can generate cache keys that include user information:

```python
from django.utils.cache_keys import get_cache_key_for_user

# Get user-specific cache key
cache_key = get_cache_key_for_user(
    user,
    UserViewSet.list,
    request,
    headerlist=['HTTP_COOKIE']
)
```

## Custom Cache Key Functions

You can provide a custom cache key function for more control over key generation:

```python
def custom_cache_key_func(request, method="GET", headerlist=None, key_prefix=None):
    """Custom cache key function that includes user ID."""
    user_id = getattr(request.user, 'id', 'anonymous')
    return f"user_feed.{user_id}.{request.path}.{method}"

class CustomUserViewSet(ViewSet):
    @method_decorator(cache_page_with_key(
        60 * 60 * 2,
        cache_key_func=custom_cache_key_func
    ))
    def list(self, request, format=None):
        content = {
            "user_feed": request.user.get_user_feed(),
        }
        return Response(content)
```

## Advanced Usage

### Cache Key Patterns

For bulk cache invalidation, you can get cache key patterns:

```python
from django.utils.cache_keys import get_view_cache_key_pattern

# Get cache key pattern
pattern = get_view_cache_key_pattern(UserViewSet.list)
print(f"Pattern: {pattern}")
# Output: "views.decorators.cache.cache_page.*.GET.*.*"
```

### Configuration Access

The decorator stores cache configuration that you can access:

```python
# Access cache configuration
config = UserViewSet.list._cache_config
print(f"Timeout: {config['timeout']}")
print(f"Key prefix: {config['key_prefix']}")
print(f"Cache alias: {config['cache_alias']}")
```

## API Reference

### `cache_page_with_key(timeout, *, cache=None, key_prefix=None, cache_key_func=None)`

Enhanced cache_page decorator that provides predictable cache keys.

**Parameters:**
- `timeout`: Cache timeout in seconds
- `cache`: Cache alias to use (optional)
- `key_prefix`: Key prefix for cache keys (optional)
- `cache_key_func`: Custom cache key function (optional)

**Returns:**
Decorated view function with additional cache key methods.

### `get_view_cache_key(view_method, request, method="GET", headerlist=None, key_prefix=None)`

Generate a cache key for a view method.

**Parameters:**
- `view_method`: The view method (e.g., UserViewSet.list)
- `request`: HttpRequest object
- `method`: HTTP method (default: GET)
- `headerlist`: List of headers to include in cache key
- `key_prefix`: Key prefix for cache key

**Returns:**
Cache key string.

### `get_view_cache_key_pattern(view_method, key_prefix=None)`

Generate a cache key pattern for a view method.

**Parameters:**
- `view_method`: The view method
- `key_prefix`: Key prefix for cache key

**Returns:**
Cache key pattern string with wildcards.

### `invalidate_view_cache(view_method, request=None, method="GET", headerlist=None, key_prefix=None, cache=None)`

Invalidate cache for a specific view method.

**Parameters:**
- `view_method`: The view method to invalidate cache for
- `request`: HttpRequest object (required for specific cache key)
- `method`: HTTP method (default: GET)
- `headerlist`: List of headers to include in cache key
- `key_prefix`: Key prefix for cache key
- `cache`: Cache instance to use (default: default cache)

**Returns:**
True if cache was invalidated, False if not found.

### `get_cache_key_for_user(user, view_method, request, method="GET", headerlist=None, key_prefix=None)`

Generate a cache key for a specific user and view method.

**Parameters:**
- `user`: User instance
- `view_method`: The view method
- `request`: HttpRequest object
- `method`: HTTP method (default: GET)
- `headerlist`: List of headers to include in cache key
- `key_prefix`: Key prefix for cache key

**Returns:**
User-specific cache key string.

## Migration from Standard cache_page

To migrate from the standard `cache_page` decorator:

1. Replace `cache_page` with `cache_page_with_key`
2. Add cache invalidation logic where needed
3. Use the provided utility functions for cache key management

**Before:**
```python
@method_decorator(cache_page(60 * 60 * 2))
def list(self, request, format=None):
    # No way to get cache key
    pass
```

**After:**
```python
@method_decorator(cache_page_with_key(60 * 60 * 2))
def list(self, request, format=None):
    # Cache key available via self.list.get_cache_key(request)
    pass
```

## Testing

The enhanced decorator includes comprehensive tests to ensure cache key predictability and consistency. Run the tests with:

```bash
python manage.py test tests.decorators.test_cache_keys
```

## Best Practices

1. **Use descriptive key prefixes** to avoid cache key conflicts
2. **Include user-specific information** in cache keys when needed
3. **Invalidate cache on model changes** using Django signals
4. **Test cache invalidation** to ensure it works correctly
5. **Monitor cache performance** to ensure invalidation doesn't impact performance

## Limitations

1. Cache key patterns for bulk invalidation depend on cache backend support
2. Custom cache key functions should be deterministic and consistent
3. Cache invalidation requires knowledge of the request context
4. User-specific cache keys require user information in the request

## Examples

See `examples/cache_key_examples.py` for comprehensive usage examples.