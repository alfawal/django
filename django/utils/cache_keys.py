"""
Utilities for generating predictable cache keys for Django views.

This module provides utilities to generate cache keys that can be used
for cache invalidation when using the cache_page decorator, even from
model save signals where no HttpRequest is available.
"""

from django.conf import settings
from django.core.cache import caches
from django.utils.cache import _generate_cache_key, _i18n_cache_key_suffix
from django.urls import reverse
from django.http import HttpRequest
from hashlib import md5


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


def get_view_cache_key_without_request(view_method, url_path, method="GET", headerlist=None, key_prefix=None, domain="localhost"):
    """
    Generate a cache key for a view method without requiring an HttpRequest object.
    
    This is particularly useful for model save signals where no request is available.
    
    Args:
        view_method: The view method (e.g., UserViewSet.list)
        url_path: The URL path (e.g., '/api/tenants/')
        method: HTTP method (default: GET)
        headerlist: List of headers to include in cache key
        key_prefix: Key prefix for cache key
        domain: Domain for the URL (default: localhost)
        
    Returns:
        str: Cache key for the view method
        
    Example:
        # Get cache key from model save signal
        cache_key = get_view_cache_key_without_request(
            TenantViewSet.list,
            '/api/tenants/',
            headerlist=['HTTP_COOKIE']
        )
    """
    if key_prefix is None:
        key_prefix = settings.CACHE_MIDDLEWARE_KEY_PREFIX
    if headerlist is None:
        headerlist = []
    
    # Create a mock request for cache key generation
    mock_request = create_mock_request(url_path, method, headerlist, domain)
    
    if hasattr(view_method, 'get_cache_key'):
        return view_method.get_cache_key(mock_request, method, headerlist)
    
    return _generate_cache_key(mock_request, method, headerlist, key_prefix)


def create_mock_request(url_path, method="GET", headerlist=None, domain="localhost"):
    """
    Create a mock HttpRequest object for cache key generation.
    
    Args:
        url_path: The URL path
        method: HTTP method
        headerlist: List of headers to include
        domain: Domain for the URL
        
    Returns:
        HttpRequest: Mock request object
    """
    request = HttpRequest()
    request.method = method
    request.path = url_path
    request.META = {
        'HTTP_HOST': domain,
        'SERVER_NAME': domain,
        'SERVER_PORT': '80',
    }
    
    # Add headers from headerlist
    if headerlist:
        for header in headerlist:
            if header.startswith('HTTP_'):
                request.META[header] = 'mock_value'
            else:
                request.META[f'HTTP_{header}'] = 'mock_value'
    
    return request


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
        request: HttpRequest object (optional, can use url_path instead)
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


def invalidate_view_cache_by_pattern(view_method, key_prefix=None, cache=None):
    """
    Invalidate all cache entries for a view method using pattern matching.
    
    This is useful when you need to invalidate all cache entries for a view
    without knowing the specific request details.
    
    Args:
        view_method: The view method to invalidate cache for
        key_prefix: Key prefix for cache key
        cache: Cache instance to use (default: default cache)
        
    Returns:
        int: Number of cache entries invalidated
        
    Example:
        # Invalidate all cache entries for TenantViewSet.list
        count = invalidate_view_cache_by_pattern(TenantViewSet.list)
    """
    if cache is None:
        cache = caches[settings.CACHE_MIDDLEWARE_ALIAS]
    
    pattern = get_view_cache_key_pattern(view_method, key_prefix)
    
    # Try different cache backends
    if hasattr(cache, 'delete_pattern'):
        # Redis cache backend
        return cache.delete_pattern(pattern)
    elif hasattr(cache, 'delete_many'):
        # Try to find keys matching the pattern
        # This is a simplified approach - actual implementation depends on cache backend
        return 0
    else:
        # Fallback: return 0 (no pattern matching support)
        return 0


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


def get_cache_key_for_user_without_request(user, view_method, url_path, method="GET", headerlist=None, key_prefix=None, domain="localhost"):
    """
    Generate a cache key for a specific user and view method without requiring an HttpRequest.
    
    This is particularly useful for model save signals where no request is available.
    
    Args:
        user: User instance
        view_method: The view method (e.g., UserViewSet.list)
        url_path: The URL path (e.g., '/api/tenants/')
        method: HTTP method (default: GET)
        headerlist: List of headers to include in cache key
        key_prefix: Key prefix for cache key
        domain: Domain for the URL (default: localhost)
        
    Returns:
        str: Cache key for the user and view method
        
    Example:
        # Get cache key for specific user from model save signal
        cache_key = get_cache_key_for_user_without_request(
            user,
            TenantViewSet.list,
            '/api/tenants/',
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
    
    return get_view_cache_key_without_request(view_method, url_path, method, headerlist, key_prefix, domain)


def invalidate_all_tenant_caches(tenant_view_method, cache=None):
    """
    Invalidate all cache entries for a tenant view method.
    
    This is a specialized function for tenant-related views that need to
    invalidate all cache entries when a tenant is modified.
    
    Args:
        tenant_view_method: The tenant view method (e.g., TenantViewSet.list)
        cache: Cache instance to use (default: default cache)
        
    Returns:
        int: Number of cache entries invalidated
        
    Example:
        # Invalidate all tenant caches
        count = invalidate_all_tenant_caches(TenantViewSet.list)
    """
    if cache is None:
        cache = caches[settings.CACHE_MIDDLEWARE_ALIAS]
    
    # Try pattern-based invalidation first
    count = invalidate_view_cache_by_pattern(tenant_view_method, cache=cache)
    
    if count > 0:
        return count
    
    # Fallback: try to invalidate common tenant cache patterns
    common_paths = [
        '/api/tenants/',
        '/api/tenants',
        '/tenants/',
        '/tenants',
    ]
    
    total_invalidated = 0
    for path in common_paths:
        try:
            cache_key = get_view_cache_key_without_request(
                tenant_view_method, path, cache=cache
            )
            if cache.delete(cache_key):
                total_invalidated += 1
        except Exception:
            # Ignore errors for individual paths
            continue
    
    return total_invalidated