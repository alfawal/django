"""
Utilities for generating predictable cache keys for Django views.

This module provides utilities to generate cache keys that can be used
for cache invalidation when using the cache_page decorator.
"""

from django.conf import settings
from django.core.cache import caches
from django.utils.cache import _generate_cache_key, _i18n_cache_key_suffix


def get_view_cache_key(view_method, request, method="GET", headerlist=None, key_prefix=None):
    """
    Generate a cache key for a view method.
    
    This function can be used to generate cache keys for view methods
    decorated with cache_page_with_key, allowing for predictable cache
    invalidation.
    
    Args:
        view_method: The view method (e.g., UserViewSet.list)
        request: HttpRequest object
        method: HTTP method (default: GET)
        headerlist: List of headers to include in cache key
        key_prefix: Key prefix for cache key
        
    Returns:
        str: Cache key for the view method
        
    Example:
        # Get cache key for a specific request
        cache_key = get_view_cache_key(
            UserViewSet.list,
            request,
            headerlist=['HTTP_COOKIE']
        )
        
        # Invalidate cache
        from django.core.cache import cache
        cache.delete(cache_key)
    """
    if hasattr(view_method, 'get_cache_key'):
        # Use the view's own cache key generation method
        return view_method.get_cache_key(request, method, headerlist)
    
    # Fallback to default cache key generation
    if key_prefix is None:
        key_prefix = settings.CACHE_MIDDLEWARE_KEY_PREFIX
    if headerlist is None:
        headerlist = []
    
    return _generate_cache_key(request, method, headerlist, key_prefix)


def get_view_cache_key_pattern(view_method, key_prefix=None):
    """
    Generate a cache key pattern for a view method.
    
    This is useful for finding all cache keys related to a specific view
    when you need to invalidate multiple cache entries.
    
    Args:
        view_method: The view method (e.g., UserViewSet.list)
        key_prefix: Key prefix for cache key
        
    Returns:
        str: Cache key pattern (with wildcards for variable parts)
        
    Example:
        # Get cache key pattern
        pattern = get_view_cache_key_pattern(UserViewSet.list)
        # Returns something like: "views.decorators.cache.cache_page.*.GET.*.*"
    """
    if key_prefix is None:
        key_prefix = settings.CACHE_MIDDLEWARE_KEY_PREFIX
    
    # Generate pattern based on Django's cache key format
    pattern = f"views.decorators.cache.cache_page.{key_prefix}.GET.*.*"
    return pattern


def invalidate_view_cache(view_method, request=None, method="GET", headerlist=None, key_prefix=None, cache=None):
    """
    Invalidate cache for a specific view method.
    
    Args:
        view_method: The view method to invalidate cache for
        request: HttpRequest object (required for specific cache key)
        method: HTTP method (default: GET)
        headerlist: List of headers to include in cache key
        key_prefix: Key prefix for cache key
        cache: Cache instance to use (default: default cache)
        
    Returns:
        bool: True if cache was invalidated, False if not found
        
    Example:
        # Invalidate specific request cache
        invalidate_view_cache(UserViewSet.list, request)
        
        # Invalidate all caches for this view (requires cache backend support)
        invalidate_view_cache(UserViewSet.list)
    """
    if cache is None:
        cache = caches[settings.CACHE_MIDDLEWARE_ALIAS]
    
    if request is not None:
        # Invalidate specific cache key
        cache_key = get_view_cache_key(view_method, request, method, headerlist, key_prefix)
        return cache.delete(cache_key)
    else:
        # Try to invalidate using pattern (requires cache backend support)
        pattern = get_view_cache_key_pattern(view_method, key_prefix)
        # This is a simplified approach - actual implementation depends on cache backend
        return False


def get_cache_key_for_user(user, view_method, request, method="GET", headerlist=None, key_prefix=None):
    """
    Generate a cache key for a specific user and view method.
    
    This is particularly useful for user-specific cached views where you need
    to invalidate cache for a specific user.
    
    Args:
        user: User instance
        view_method: The view method (e.g., UserViewSet.list)
        request: HttpRequest object
        method: HTTP method (default: GET)
        headerlist: List of headers to include in cache key
        key_prefix: Key prefix for cache key
        
    Returns:
        str: Cache key for the user and view method
        
    Example:
        # Get cache key for specific user
        cache_key = get_cache_key_for_user(
            user,
            UserViewSet.list,
            request,
            headerlist=['HTTP_COOKIE']
        )
    """
    # Add user-specific information to headerlist
    if headerlist is None:
        headerlist = []
    
    # Add user ID to make cache key user-specific
    user_header = f"HTTP_X_USER_ID:{user.id}"
    if user_header not in headerlist:
        headerlist = headerlist + [user_header]
    
    return get_view_cache_key(view_method, request, method, headerlist, key_prefix)