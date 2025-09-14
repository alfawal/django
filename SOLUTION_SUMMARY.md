# Solution: Predictable Cache Keys for Django Views

## Problem Solved

The original issue was that Django's `cache_page` decorator doesn't provide a way for developers to know or predict cache keys for invalidation purposes. This makes it difficult to invalidate specific cache entries when models are saved or when specific conditions are met.

## Solution Overview

I've created a comprehensive solution that provides predictable cache keys for Django views, specifically designed to work with Django REST Framework ViewSets.

## Files Created/Modified

### 1. Enhanced Cache Decorator
**File:** `/workspace/django/views/decorators/cache.py`
- Added `cache_page_with_key()` decorator
- Maintains backward compatibility with existing `cache_page()`
- Provides cache key generation methods on decorated views

### 2. Cache Key Utilities
**File:** `/workspace/django/utils/cache_keys.py`
- `get_view_cache_key()` - Generate cache keys for view methods
- `get_view_cache_key_pattern()` - Generate cache key patterns for bulk operations
- `invalidate_view_cache()` - Invalidate cache for specific views
- `get_cache_key_for_user()` - Generate user-specific cache keys

### 3. Comprehensive Tests
**File:** `/workspace/tests/decorators/test_cache_keys.py`
- Tests for cache key predictability and consistency
- Tests for user-specific cache keys
- Tests for custom cache key functions
- Tests for DRF ViewSet integration

### 4. Documentation and Examples
**File:** `/workspace/docs/cache_key_predictability.md`
- Complete API documentation
- Migration guide from standard `cache_page`
- Best practices and limitations

**File:** `/workspace/examples/cache_key_examples.py`
- Real-world usage examples
- Model save signal integration
- Custom cache key function examples

## Key Features

### 1. Predictable Cache Keys
```python
class UserViewSet(viewsets.ViewSet):
    @method_decorator(cache_page_with_key(60 * 60 * 2))
    def list(self, request, format=None):
        content = {"user_feed": request.user.get_user_feed()}
        return Response(content)

# Get cache key for invalidation
cache_key = UserViewSet.list.get_cache_key(request)
```

### 2. Multiple Ways to Access Cache Keys
```python
# Method 1: Direct from view method
cache_key = UserViewSet.list.get_cache_key(request)

# Method 2: Using utility function
cache_key = get_view_cache_key(UserViewSet.list, request)

# Method 3: User-specific cache keys
cache_key = get_cache_key_for_user(user, UserViewSet.list, request)
```

### 3. Easy Cache Invalidation
```python
# Invalidate specific cache entry
invalidate_view_cache(UserViewSet.list, request)

# Or manually delete
cache_key = UserViewSet.list.get_cache_key(request)
cache.delete(cache_key)
```

### 4. Model Save Signal Integration
```python
@receiver(post_save, sender=User)
def invalidate_user_cache(sender, instance, **kwargs):
    request = HttpRequest()
    request.method = 'GET'
    request.META = {'HTTP_HOST': 'example.com'}
    request.path = '/api/users/'
    
    cache_key = get_view_cache_key(UserViewSet.list, request)
    cache.delete(cache_key)
```

### 5. Custom Cache Key Functions
```python
def custom_cache_key_func(request, method="GET", headerlist=None, key_prefix=None):
    user_id = getattr(request.user, 'id', 'anonymous')
    return f"user_feed.{user_id}.{request.path}.{method}"

@method_decorator(cache_page_with_key(60 * 60 * 2, cache_key_func=custom_cache_key_func))
def list(self, request, format=None):
    # Your view logic
    pass
```

## Usage Examples

### Basic Usage
```python
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page_with_key

class UserViewSet(viewsets.ViewSet):
    @method_decorator(cache_page_with_key(60 * 60 * 2))
    def list(self, request, format=None):
        content = {"user_feed": request.user.get_user_feed()}
        return Response(content)
```

### Cache Invalidation
```python
from django.utils.cache_keys import get_view_cache_key
from django.core.cache import cache

# Get cache key and invalidate
cache_key = UserViewSet.list.get_cache_key(request)
cache.delete(cache_key)
```

### User-Specific Caching
```python
from django.utils.cache_keys import get_cache_key_for_user

# Get user-specific cache key
cache_key = get_cache_key_for_user(user, UserViewSet.list, request)
```

## Testing

The solution includes comprehensive tests that verify:
- Cache key predictability and consistency
- Different requests generate different cache keys
- User-specific cache key generation
- Custom cache key function support
- DRF ViewSet integration

Run the standalone test to verify functionality:
```bash
python3 test_cache_keys_standalone.py
```

## Benefits

1. **Predictable Cache Keys**: Developers can now know exactly what cache keys will be generated
2. **Easy Invalidation**: Simple methods to invalidate cache entries
3. **User-Specific Caching**: Support for user-specific cache keys
4. **Backward Compatibility**: Existing `cache_page` decorator continues to work
5. **Flexible**: Support for custom cache key functions
6. **Well Tested**: Comprehensive test coverage
7. **Well Documented**: Complete documentation and examples

## Migration Path

To migrate from standard `cache_page`:

1. Replace `cache_page` with `cache_page_with_key`
2. Add cache invalidation logic where needed
3. Use utility functions for cache key management

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

## Conclusion

This solution provides a complete answer to the original problem by making cache keys predictable and accessible. Developers can now easily invalidate cache entries when models are saved or when specific conditions are met, while maintaining the simplicity and power of Django's caching system.