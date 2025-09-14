"""
Examples demonstrating predictable cache keys with Django REST Framework.

This file shows how to use the enhanced cache_page decorator to get
predictable cache keys for cache invalidation.
"""

from django.http import HttpRequest
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page_with_key
from django.utils.cache_keys import (
    get_view_cache_key,
    get_view_cache_key_pattern,
    invalidate_view_cache,
    get_cache_key_for_user,
)
from rest_framework.viewsets import ViewSet
from rest_framework.response import Response


class UserViewSet(ViewSet):
    """
    Example ViewSet showing how to use predictable cache keys.
    """
    
    @method_decorator(cache_page_with_key(60 * 60 * 2))  # 2 hours
    def list(self, request, format=None):
        """
        List user feed with caching.
        
        Cache key can be obtained using:
        - UserViewSet.list.get_cache_key(request)
        - get_view_cache_key(UserViewSet.list, request)
        """
        content = {
            "user_feed": request.user.get_user_feed(),
        }
        return Response(content)
    
    @method_decorator(cache_page_with_key(60 * 60 * 1))  # 1 hour
    def retrieve(self, request, pk=None, format=None):
        """
        Retrieve specific user with caching.
        """
        content = {
            "user": {"id": pk, "name": f"User {pk}"},
        }
        return Response(content)


def example_cache_invalidation():
    """
    Example showing how to invalidate cache for specific views.
    """
    # Create a mock request
    request = HttpRequest()
    request.method = 'GET'
    request.META = {
        'HTTP_HOST': 'example.com',
        'HTTP_COOKIE': 'sessionid=abc123',
    }
    request.path = '/api/users/'
    
    # Method 1: Using the view's cache key method
    cache_key = UserViewSet.list.get_cache_key(request)
    print(f"Cache key: {cache_key}")
    
    # Method 2: Using the utility function
    cache_key2 = get_view_cache_key(UserViewSet.list, request)
    print(f"Cache key (utility): {cache_key2}")
    
    # Method 3: Invalidate cache
    invalidated = invalidate_view_cache(UserViewSet.list, request)
    print(f"Cache invalidated: {invalidated}")


def example_user_specific_cache():
    """
    Example showing user-specific cache invalidation.
    """
    class MockUser:
        def __init__(self, user_id):
            self.id = user_id
    
    # Create mock request and user
    request = HttpRequest()
    request.method = 'GET'
    request.META = {'HTTP_HOST': 'example.com'}
    request.path = '/api/users/'
    
    user = MockUser(123)
    
    # Get user-specific cache key
    cache_key = get_cache_key_for_user(user, UserViewSet.list, request)
    print(f"User-specific cache key: {cache_key}")


def example_model_save_signal():
    """
    Example showing how to invalidate cache when a model is saved.
    """
    from django.db.models.signals import post_save
    from django.dispatch import receiver
    
    class User(models.Model):
        name = models.CharField(max_length=100)
        
        def get_user_feed(self):
            return f"Feed for {self.name}"
    
    @receiver(post_save, sender=User)
    def invalidate_user_cache(sender, instance, **kwargs):
        """
        Invalidate cache when a user is saved.
        """
        # Create a mock request for cache key generation
        request = HttpRequest()
        request.method = 'GET'
        request.META = {'HTTP_HOST': 'example.com'}
        request.path = '/api/users/'
        
        # Invalidate cache for the user list view
        invalidate_view_cache(UserViewSet.list, request)
        
        # Or get the specific cache key and delete it
        cache_key = get_view_cache_key(UserViewSet.list, request)
        from django.core.cache import cache
        cache.delete(cache_key)


def example_custom_cache_key_function():
    """
    Example showing how to use a custom cache key function.
    """
    def custom_cache_key_func(request, method="GET", headerlist=None, key_prefix=None):
        """
        Custom cache key function that includes user ID in the key.
        """
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
    
    # Usage
    request = HttpRequest()
    request.user = MockUser(123)
    request.path = '/api/users/'
    
    viewset = CustomUserViewSet()
    cache_key = viewset.list.get_cache_key(request)
    print(f"Custom cache key: {cache_key}")
    # Output: "user_feed.123./api/users/.GET"


def example_bulk_cache_invalidation():
    """
    Example showing how to invalidate multiple cache entries.
    """
    from django.core.cache import cache
    
    # Get cache key pattern
    pattern = get_view_cache_key_pattern(UserViewSet.list)
    print(f"Cache key pattern: {pattern}")
    
    # In a real implementation, you would use cache backend specific methods
    # to find and delete keys matching the pattern
    # For example, with Redis:
    # cache.delete_pattern(pattern)
    
    # Or invalidate all cache entries for a specific view
    # (This would require cache backend support)
    invalidate_view_cache(UserViewSet.list)


if __name__ == "__main__":
    # Run examples
    print("=== Cache Key Examples ===")
    example_cache_invalidation()
    print("\n=== User-Specific Cache ===")
    example_user_specific_cache()
    print("\n=== Custom Cache Key Function ===")
    example_custom_cache_key_function()
    print("\n=== Bulk Cache Invalidation ===")
    example_bulk_cache_invalidation()