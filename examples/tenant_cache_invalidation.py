"""
Example showing how to handle cache invalidation for Tenant model saves
from Django admin or other non-request contexts.
"""

from django.db import models
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page_with_key
from rest_framework.viewsets import ViewSet
from rest_framework.response import Response
from django.utils.cache_keys import (
    get_view_cache_key_without_request,
    invalidate_view_cache_by_pattern,
    invalidate_all_tenant_caches,
)


class Tenant(models.Model):
    """Example Tenant model."""
    name = models.CharField(max_length=100)
    domain = models.CharField(max_length=100, unique=True)
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return self.name


class TenantViewSet(ViewSet):
    """
    Example ViewSet for Tenant with cache invalidation support.
    """
    
    @method_decorator(cache_page_with_key(
        60 * 60 * 2,  # 2 hours
        url_path='/api/tenants/'  # Specify URL path for cache invalidation
    ))
    def list(self, request, format=None):
        """List all tenants with caching."""
        tenants = Tenant.objects.filter(is_active=True)
        content = {
            "tenants": [
                {"id": t.id, "name": t.name, "domain": t.domain}
                for t in tenants
            ]
        }
        return Response(content)
    
    @method_decorator(cache_page_with_key(
        60 * 60 * 1,  # 1 hour
        url_path='/api/tenants/{pk}/'  # URL with parameter
    ))
    def retrieve(self, request, pk=None, format=None):
        """Retrieve specific tenant with caching."""
        try:
            tenant = Tenant.objects.get(pk=pk, is_active=True)
            content = {
                "tenant": {
                    "id": tenant.id,
                    "name": tenant.name,
                    "domain": tenant.domain
                }
            }
        except Tenant.DoesNotExist:
            content = {"error": "Tenant not found"}
        
        return Response(content)


# Method 1: Simple cache invalidation using stored URL path
@receiver(post_save, sender=Tenant)
def invalidate_tenant_cache_simple(sender, instance, **kwargs):
    """
    Simple cache invalidation using the stored URL path.
    
    This works because we specified url_path in the decorator.
    """
    print(f"Invalidating cache for tenant: {instance.name}")
    
    # Invalidate list cache
    count = TenantViewSet.list.invalidate_cache()
    print(f"Invalidated {count} cache entries for tenant list")
    
    # Invalidate specific tenant cache
    count = TenantViewSet.retrieve.invalidate_cache(f'/api/tenants/{instance.id}/')
    print(f"Invalidated {count} cache entries for tenant {instance.id}")


# Method 2: More comprehensive cache invalidation
@receiver(post_save, sender=Tenant)
def invalidate_tenant_cache_comprehensive(sender, instance, **kwargs):
    """
    Comprehensive cache invalidation for tenant changes.
    
    This method tries multiple approaches to ensure cache invalidation.
    """
    print(f"Comprehensive cache invalidation for tenant: {instance.name}")
    
    # Method 2a: Use utility functions with URL paths
    from django.utils.cache_keys import get_view_cache_key_without_request
    from django.core.cache import cache
    
    # Invalidate list cache
    list_cache_key = get_view_cache_key_without_request(
        TenantViewSet.list,
        '/api/tenants/',
        headerlist=['HTTP_COOKIE']  # Include common headers
    )
    cache.delete(list_cache_key)
    print(f"Deleted list cache key: {list_cache_key[:50]}...")
    
    # Invalidate specific tenant cache
    tenant_cache_key = get_view_cache_key_without_request(
        TenantViewSet.retrieve,
        f'/api/tenants/{instance.id}/',
        headerlist=['HTTP_COOKIE']
    )
    cache.delete(tenant_cache_key)
    print(f"Deleted tenant cache key: {tenant_cache_key[:50]}...")
    
    # Method 2b: Try pattern-based invalidation
    list_count = invalidate_view_cache_by_pattern(TenantViewSet.list)
    retrieve_count = invalidate_view_cache_by_pattern(TenantViewSet.retrieve)
    
    print(f"Pattern-based invalidation: {list_count} list entries, {retrieve_count} retrieve entries")


# Method 3: Using specialized tenant cache invalidation
@receiver(post_save, sender=Tenant)
def invalidate_tenant_cache_specialized(sender, instance, **kwargs):
    """
    Use specialized tenant cache invalidation function.
    
    This is the most robust approach for tenant-related caches.
    """
    print(f"Specialized cache invalidation for tenant: {instance.name}")
    
    # Invalidate all tenant list caches
    list_count = invalidate_all_tenant_caches(TenantViewSet.list)
    print(f"Invalidated {list_count} tenant list cache entries")
    
    # For specific tenant, we still need to handle the retrieve view
    from django.utils.cache_keys import get_view_cache_key_without_request
    from django.core.cache import cache
    
    # Try common URL patterns for the specific tenant
    common_paths = [
        f'/api/tenants/{instance.id}/',
        f'/api/tenants/{instance.id}',
        f'/tenants/{instance.id}/',
        f'/tenants/{instance.id}',
    ]
    
    for path in common_paths:
        try:
            cache_key = get_view_cache_key_without_request(
                TenantViewSet.retrieve, path
            )
            if cache.delete(cache_key):
                print(f"Deleted cache for path: {path}")
        except Exception as e:
            print(f"Could not invalidate cache for path {path}: {e}")


# Method 4: Custom cache key function for tenant-specific caching
def tenant_cache_key_func(request, method="GET", headerlist=None, key_prefix=None):
    """
    Custom cache key function that includes tenant information.
    
    This ensures that cache keys are tenant-specific and can be
    easily invalidated when tenants change.
    """
    from django.utils.cache import _generate_cache_key
    from django.conf import settings
    
    if key_prefix is None:
        key_prefix = settings.CACHE_MIDDLEWARE_KEY_PREFIX
    if headerlist is None:
        headerlist = []
    
    # Add tenant-specific information to the cache key
    tenant_id = getattr(request, 'tenant_id', 'no-tenant')
    tenant_domain = getattr(request, 'tenant_domain', 'no-domain')
    
    # Create a custom key that includes tenant info
    custom_key_prefix = f"{key_prefix}.tenant.{tenant_id}.{tenant_domain}"
    
    return _generate_cache_key(request, method, headerlist, custom_key_prefix)


class TenantSpecificViewSet(ViewSet):
    """
    ViewSet with tenant-specific cache keys.
    """
    
    @method_decorator(cache_page_with_key(
        60 * 60 * 2,
        url_path='/api/tenants/',
        cache_key_func=tenant_cache_key_func
    ))
    def list(self, request, format=None):
        """List tenants with tenant-specific caching."""
        # In a real implementation, you'd extract tenant info from request
        request.tenant_id = getattr(request, 'tenant_id', 'default')
        request.tenant_domain = getattr(request, 'tenant_domain', 'default.com')
        
        tenants = Tenant.objects.filter(is_active=True)
        content = {
            "tenants": [
                {"id": t.id, "name": t.name, "domain": t.domain}
                for t in tenants
            ]
        }
        return Response(content)


# Method 5: Bulk cache invalidation for tenant changes
@receiver(post_save, sender=Tenant)
def invalidate_tenant_cache_bulk(sender, instance, **kwargs):
    """
    Bulk cache invalidation for tenant changes.
    
    This method invalidates all possible cache entries related to tenants.
    """
    print(f"Bulk cache invalidation for tenant: {instance.name}")
    
    from django.core.cache import cache
    
    # Get all possible cache keys for tenant views
    tenant_urls = [
        '/api/tenants/',
        '/api/tenants',
        '/tenants/',
        '/tenants',
        f'/api/tenants/{instance.id}/',
        f'/api/tenants/{instance.id}',
        f'/tenants/{instance.id}/',
        f'/tenants/{instance.id}',
    ]
    
    total_invalidated = 0
    
    for url in tenant_urls:
        try:
            # Try to get cache key for list view
            list_key = get_view_cache_key_without_request(
                TenantViewSet.list, url
            )
            if cache.delete(list_key):
                total_invalidated += 1
                print(f"Deleted list cache for: {url}")
        except Exception:
            pass
        
        try:
            # Try to get cache key for retrieve view
            retrieve_key = get_view_cache_key_without_request(
                TenantViewSet.retrieve, url
            )
            if cache.delete(retrieve_key):
                total_invalidated += 1
                print(f"Deleted retrieve cache for: {url}")
        except Exception:
            pass
    
    print(f"Total cache entries invalidated: {total_invalidated}")


# Method 6: Using Django's cache key patterns (if supported by backend)
@receiver(post_save, sender=Tenant)
def invalidate_tenant_cache_patterns(sender, instance, **kwargs):
    """
    Use cache key patterns for invalidation (requires cache backend support).
    
    This is the most efficient method if your cache backend supports pattern matching.
    """
    print(f"Pattern-based cache invalidation for tenant: {instance.name}")
    
    from django.core.cache import caches
    from django.conf import settings
    
    cache = caches[settings.CACHE_MIDDLEWARE_ALIAS]
    
    # Try pattern-based deletion if supported
    if hasattr(cache, 'delete_pattern'):
        # Delete all cache entries matching tenant patterns
        patterns = [
            "views.decorators.cache.cache_page.*.GET.*tenant*",
            "views.decorators.cache.cache_page.*.GET.*tenants*",
            f"views.decorators.cache.cache_page.*.GET.*{instance.id}*",
        ]
        
        total_deleted = 0
        for pattern in patterns:
            deleted = cache.delete_pattern(pattern)
            total_deleted += deleted
            print(f"Deleted {deleted} entries matching pattern: {pattern}")
        
        print(f"Total entries deleted via patterns: {total_deleted}")
    else:
        print("Cache backend does not support pattern deletion")


if __name__ == "__main__":
    print("Tenant cache invalidation examples loaded.")
    print("Use these methods in your Django project to handle cache invalidation")
    print("when saving Tenant models from Django admin or other non-request contexts.")