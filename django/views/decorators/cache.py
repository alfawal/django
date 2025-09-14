from functools import wraps

from asgiref.sync import iscoroutinefunction

from django.middleware.cache import CacheMiddleware
from django.utils.cache import add_never_cache_headers, patch_cache_control
from django.utils.decorators import decorator_from_middleware_with_args


def cache_page(timeout, *, cache=None, key_prefix=None):
    """
    Decorator for views that tries getting the page from the cache and
    populates the cache if the page isn't in the cache yet.

    The cache is keyed by the URL and some data from the headers.
    Additionally there is the key prefix that is used to distinguish different
    cache areas in a multi-site setup. You could use the
    get_current_site().domain, for example, as that is unique across a Django
    project.

    Additionally, all headers from the response's Vary header will be taken
    into account on caching -- just like the middleware does.
    """
    return decorator_from_middleware_with_args(CacheMiddleware)(
        page_timeout=timeout,
        cache_alias=cache,
        key_prefix=key_prefix,
    )


def cache_page_with_key(timeout, *, cache=None, key_prefix=None, cache_key_func=None, url_path=None):
    """
    Enhanced cache_page decorator that provides predictable cache keys.
    
    This decorator works like cache_page but also stores a cache key generation
    function that can be used to predict cache keys for invalidation, even
    without an HttpRequest object (useful for model save signals).
    
    Args:
        timeout: Cache timeout in seconds
        cache: Cache alias to use
        key_prefix: Key prefix for cache keys
        cache_key_func: Optional function to generate cache keys. If not provided,
                       uses the default Django cache key generation.
        url_path: Optional URL path for cache key generation without request.
                 If provided, enables cache invalidation from model save signals.
    
    The decorated method will have several methods for cache key generation:
    - get_cache_key(request) - Generate cache key from HttpRequest
    - get_cache_key_without_request(url_path) - Generate cache key without request
    - invalidate_cache() - Invalidate all cache entries for this view
    """
    def decorator(view_func):
        # Store the cache key generation function on the view
        if cache_key_func:
            view_func._cache_key_func = cache_key_func
        else:
            # Use default Django cache key generation
            from django.utils.cache import _generate_cache_key, _i18n_cache_key_suffix
            from django.conf import settings
            from hashlib import md5
            
            def default_cache_key_func(request, method="GET", headerlist=None, key_prefix=None):
                if key_prefix is None:
                    key_prefix = settings.CACHE_MIDDLEWARE_KEY_PREFIX
                if headerlist is None:
                    headerlist = []
                return _generate_cache_key(request, method, headerlist, key_prefix)
            
            view_func._cache_key_func = default_cache_key_func
        
        # Store cache configuration for key generation
        view_func._cache_config = {
            'timeout': timeout,
            'cache_alias': cache,
            'key_prefix': key_prefix,
            'url_path': url_path,
        }
        
        # Apply the original cache_page decorator
        cached_view = cache_page(timeout, cache=cache, key_prefix=key_prefix)(view_func)
        
        # Add cache key generation method
        def get_cache_key(request, method="GET", headerlist=None):
            """
            Generate a cache key for this view method.
            
            Args:
                request: HttpRequest object
                method: HTTP method (default: GET)
                headerlist: List of headers to include in cache key
                
            Returns:
                str: Cache key for this view
            """
            config = view_func._cache_config
            key_prefix = config['key_prefix']
            return view_func._cache_key_func(request, method, headerlist, key_prefix)
        
        def get_cache_key_without_request(url_path=None, method="GET", headerlist=None, domain="localhost"):
            """
            Generate a cache key for this view method without requiring an HttpRequest.
            
            This is particularly useful for model save signals where no request is available.
            
            Args:
                url_path: The URL path (uses stored url_path if not provided)
                method: HTTP method (default: GET)
                headerlist: List of headers to include in cache key
                domain: Domain for the URL (default: localhost)
                
            Returns:
                str: Cache key for this view
            """
            from django.utils.cache_keys import get_view_cache_key_without_request
            
            config = view_func._cache_config
            key_prefix = config['key_prefix']
            url_path = url_path or config['url_path']
            
            if not url_path:
                raise ValueError("url_path must be provided either in decorator or method call")
            
            return get_view_cache_key_without_request(
                view_func, url_path, method, headerlist, key_prefix, domain
            )
        
        def invalidate_cache(url_path=None, method="GET", headerlist=None, domain="localhost"):
            """
            Invalidate all cache entries for this view method.
            
            Args:
                url_path: The URL path (uses stored url_path if not provided)
                method: HTTP method (default: GET)
                headerlist: List of headers to include in cache key
                domain: Domain for the URL (default: localhost)
                
            Returns:
                int: Number of cache entries invalidated
            """
            from django.utils.cache_keys import invalidate_view_cache_by_pattern, get_view_cache_key_without_request
            from django.core.cache import caches
            from django.conf import settings
            
            cache = caches[view_func._cache_config.get('cache_alias', settings.CACHE_MIDDLEWARE_ALIAS)]
            
            # Try pattern-based invalidation first
            count = invalidate_view_cache_by_pattern(view_func, view_func._cache_config['key_prefix'], cache)
            
            if count > 0:
                return count
            
            # Fallback: try to invalidate using stored URL path
            url_path = url_path or view_func._cache_config['url_path']
            if url_path:
                try:
                    cache_key = get_view_cache_key_without_request(
                        view_func, url_path, method, headerlist, 
                        view_func._cache_config['key_prefix'], domain
                    )
                    return 1 if cache.delete(cache_key) else 0
                except Exception:
                    return 0
            
            return 0
        
        cached_view.get_cache_key = get_cache_key
        cached_view.get_cache_key_without_request = get_cache_key_without_request
        cached_view.invalidate_cache = invalidate_cache
        
        return cached_view
    
    return decorator


def _check_request(request, decorator_name):
    # Ensure argument looks like a request.
    if not hasattr(request, "META"):
        raise TypeError(
            f"{decorator_name} didn't receive an HttpRequest. If you are "
            "decorating a classmethod, be sure to use @method_decorator."
        )


def cache_control(**kwargs):
    def _cache_controller(viewfunc):
        if iscoroutinefunction(viewfunc):

            async def _view_wrapper(request, *args, **kw):
                _check_request(request, "cache_control")
                response = await viewfunc(request, *args, **kw)
                patch_cache_control(response, **kwargs)
                return response

        else:

            def _view_wrapper(request, *args, **kw):
                _check_request(request, "cache_control")
                response = viewfunc(request, *args, **kw)
                patch_cache_control(response, **kwargs)
                return response

        return wraps(viewfunc)(_view_wrapper)

    return _cache_controller


def never_cache(view_func):
    """
    Decorator that adds headers to a response so that it will never be cached.
    """

    if iscoroutinefunction(view_func):

        async def _view_wrapper(request, *args, **kwargs):
            _check_request(request, "never_cache")
            response = await view_func(request, *args, **kwargs)
            add_never_cache_headers(response)
            return response

    else:

        def _view_wrapper(request, *args, **kwargs):
            _check_request(request, "never_cache")
            response = await view_func(request, *args, **kwargs)
            add_never_cache_headers(response)
            return response

    return wraps(view_func)(_view_wrapper)