# Final Solution: Predictable Cache Keys for Django Views (Fixed)

## Problem Identified and Solved

You were absolutely right! The original solution had a critical flaw: **it required an HttpRequest object for cache invalidation, which is not available when saving models from Django admin or other non-request contexts**.

## The Fix

I've completely redesigned the solution to work **without requiring an HttpRequest object**. Here's how it now works:

### 1. Enhanced Decorator with URL Path Support

```python
class TenantViewSet(viewsets.ViewSet):
    @method_decorator(cache_page_with_key(
        60 * 60 * 2,  # 2 hours
        url_path='/api/tenants/'  # Specify URL path for cache invalidation
    ))
    def list(self, request, format=None):
        content = {"tenants": request.user.get_tenant_list()}
        return Response(content)
```

### 2. Cache Invalidation from Model Save Signals

```python
from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=Tenant)
def invalidate_tenant_cache(sender, instance, **kwargs):
    """This now works from Django admin saves!"""
    
    # Method 1: Simple invalidation using stored URL path
    TenantViewSet.list.invalidate_cache()
    
    # Method 2: Invalidate specific tenant cache
    TenantViewSet.retrieve.invalidate_cache(f'/api/tenants/{instance.id}/')
    
    # Method 3: Get cache key for manual deletion
    cache_key = TenantViewSet.list.get_cache_key_without_request('/api/tenants/')
    cache.delete(cache_key)
```

## Key Features of the Fixed Solution

### ✅ **Works Without HttpRequest**
- Cache invalidation works from model save signals
- No request object required
- Perfect for Django admin saves

### ✅ **Multiple Invalidation Methods**
```python
# Method 1: Using stored URL path
viewset.list.invalidate_cache()

# Method 2: Using specific URL path
viewset.list.invalidate_cache('/api/tenants/')

# Method 3: Manual cache key generation
cache_key = viewset.list.get_cache_key_without_request('/api/tenants/')
cache.delete(cache_key)

# Method 4: Pattern-based invalidation (for bulk operations)
invalidate_view_cache_by_pattern(TenantViewSet.list)
```

### ✅ **Flexible URL Path Handling**
```python
# Store URL path in decorator
@method_decorator(cache_page_with_key(60 * 60 * 2, url_path='/api/tenants/'))
def list(self, request, format=None):
    pass

# Or provide URL path at runtime
cache_key = viewset.list.get_cache_key_without_request('/api/tenants/')
```

### ✅ **Comprehensive Error Handling**
```python
# Raises ValueError if no URL path is available
try:
    viewset.list.get_cache_key_without_request()
except ValueError as e:
    print("URL path must be provided either in decorator or method call")
```

## Complete Example: Tenant Model Save Scenario

```python
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page_with_key
from rest_framework.viewsets import ViewSet
from rest_framework.response import Response

class Tenant(models.Model):
    name = models.CharField(max_length=100)
    domain = models.CharField(max_length=100, unique=True)
    is_active = models.BooleanField(default=True)

class TenantViewSet(ViewSet):
    @method_decorator(cache_page_with_key(60 * 60 * 2, url_path='/api/tenants/'))
    def list(self, request, format=None):
        tenants = Tenant.objects.filter(is_active=True)
        return Response({"tenants": [{"id": t.id, "name": t.name} for t in tenants]})
    
    @method_decorator(cache_page_with_key(60 * 60 * 1, url_path='/api/tenants/{pk}/'))
    def retrieve(self, request, pk=None, format=None):
        tenant = Tenant.objects.get(pk=pk, is_active=True)
        return Response({"tenant": {"id": tenant.id, "name": tenant.name}})

# This now works from Django admin saves!
@receiver(post_save, sender=Tenant)
def invalidate_tenant_cache(sender, instance, **kwargs):
    print(f"Invalidating cache for tenant: {instance.name}")
    
    # Invalidate list cache (uses stored URL path)
    list_count = TenantViewSet.list.invalidate_cache()
    print(f"Invalidated {list_count} list cache entries")
    
    # Invalidate specific tenant cache
    retrieve_count = TenantViewSet.retrieve.invalidate_cache(f'/api/tenants/{instance.id}/')
    print(f"Invalidated {retrieve_count} tenant cache entries")
    
    # Or get cache keys for manual deletion
    list_cache_key = TenantViewSet.list.get_cache_key_without_request('/api/tenants/')
    tenant_cache_key = TenantViewSet.retrieve.get_cache_key_without_request(f'/api/tenants/{instance.id}/')
    
    from django.core.cache import cache
    cache.delete(list_cache_key)
    cache.delete(tenant_cache_key)
```

## Files Created/Updated

1. **`/workspace/django/views/decorators/cache.py`** - Enhanced decorator with URL path support
2. **`/workspace/django/utils/cache_keys.py`** - Utility functions for cache key management
3. **`/workspace/tests/decorators/test_cache_keys.py`** - Comprehensive tests
4. **`/workspace/examples/tenant_cache_invalidation.py`** - Real-world examples
5. **`/workspace/test_tenant_cache_fix.py`** - Verification tests

## Testing Results

All tests pass successfully! ✅

```
🎉 All tests passed! The tenant cache invalidation fix works correctly.

Key benefits of the fix:
✓ Cache invalidation works from model save signals
✓ No HttpRequest object required
✓ Multiple invalidation approaches available
✓ URL path can be stored in decorator for convenience
✓ Supports both specific and bulk cache invalidation
```

## Migration Guide

### Before (Broken):
```python
@method_decorator(cache_page(60 * 60 * 2))
def list(self, request, format=None):
    # No way to get cache key for invalidation
    pass

@receiver(post_save, sender=Tenant)
def invalidate_cache(sender, instance, **kwargs):
    # This doesn't work - no request available!
    cache_key = get_view_cache_key(TenantViewSet.list, request)  # ❌ No request!
```

### After (Fixed):
```python
@method_decorator(cache_page_with_key(60 * 60 * 2, url_path='/api/tenants/'))
def list(self, request, format=None):
    # Cache key available via self.list.get_cache_key_without_request()
    pass

@receiver(post_save, sender=Tenant)
def invalidate_cache(sender, instance, **kwargs):
    # This works perfectly! ✅
    TenantViewSet.list.invalidate_cache()  # Uses stored URL path
    # Or:
    cache_key = TenantViewSet.list.get_cache_key_without_request('/api/tenants/')
    cache.delete(cache_key)
```

## Summary

The solution now **completely addresses your original concern**: cache invalidation works from Django admin saves and other non-request contexts. The key insight was to store the URL path in the decorator and provide methods that work without requiring an HttpRequest object.

This makes the cache key system truly predictable and usable in all scenarios, including the critical tenant model save scenario you described.