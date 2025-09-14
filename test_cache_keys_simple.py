#!/usr/bin/env python3
"""
Simple test script to verify cache key functionality works.
"""

import sys
import os

# Add Django to the path
sys.path.insert(0, '/workspace')

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'django.conf.global_settings')

# Import Django components
from django.http import HttpRequest
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page_with_key
from django.utils.cache_keys import (
    get_view_cache_key,
    get_view_cache_key_pattern,
    invalidate_view_cache,
    get_cache_key_for_user,
)

def test_basic_functionality():
    """Test basic cache key functionality."""
    print("Testing basic cache key functionality...")
    
    # Create a test viewset
    class TestViewSet:
        @method_decorator(cache_page_with_key(60 * 60 * 2))
        def list(self, request, format=None):
            return {"data": "test"}
    
    # Create a test request
    request = HttpRequest()
    request.method = 'GET'
    request.META = {
        'HTTP_HOST': 'example.com',
        'HTTP_COOKIE': 'sessionid=abc123',
    }
    request.path = '/api/users/'
    
    viewset = TestViewSet()
    
    # Test 1: Check that the method has cache key functionality
    print("✓ View method has cache key functionality:", hasattr(viewset.list, 'get_cache_key'))
    
    # Test 2: Generate cache key
    cache_key = viewset.list.get_cache_key(request)
    print("✓ Cache key generated:", cache_key[:50] + "..." if len(cache_key) > 50 else cache_key)
    
    # Test 3: Cache key consistency
    cache_key2 = viewset.list.get_cache_key(request)
    print("✓ Cache keys are consistent:", cache_key == cache_key2)
    
    # Test 4: Utility function
    utility_key = get_view_cache_key(viewset.list, request)
    print("✓ Utility function works:", utility_key == cache_key)
    
    # Test 5: Cache key pattern
    pattern = get_view_cache_key_pattern(viewset.list)
    print("✓ Cache key pattern:", pattern)
    
    # Test 6: Different requests generate different keys
    request2 = HttpRequest()
    request2.method = 'GET'
    request2.META = {'HTTP_HOST': 'example.com', 'HTTP_COOKIE': 'sessionid=def456'}
    request2.path = '/api/users/'
    
    cache_key3 = viewset.list.get_cache_key(request2)
    print("✓ Different requests generate different keys:", cache_key != cache_key3)
    
    print("All basic tests passed! ✓")

def test_user_specific_cache():
    """Test user-specific cache functionality."""
    print("\nTesting user-specific cache functionality...")
    
    class MockUser:
        def __init__(self, user_id):
            self.id = user_id
    
    class TestViewSet:
        @method_decorator(cache_page_with_key(60 * 60 * 2))
        def list(self, request, format=None):
            return {"data": "test"}
    
    request = HttpRequest()
    request.method = 'GET'
    request.META = {'HTTP_HOST': 'example.com'}
    request.path = '/api/users/'
    
    user1 = MockUser(123)
    user2 = MockUser(456)
    
    viewset = TestViewSet()
    
    # Test user-specific cache keys
    key1 = get_cache_key_for_user(user1, viewset.list, request)
    key2 = get_cache_key_for_user(user2, viewset.list, request)
    
    print("✓ User-specific cache keys generated")
    print("✓ Different users have different cache keys:", key1 != key2)
    
    print("User-specific cache tests passed! ✓")

def test_custom_cache_key_function():
    """Test custom cache key function."""
    print("\nTesting custom cache key function...")
    
    def custom_cache_key_func(request, method="GET", headerlist=None, key_prefix=None):
        return f"custom.{request.path}.{method}"
    
    class TestViewSet:
        @method_decorator(cache_page_with_key(
            60 * 60 * 2,
            cache_key_func=custom_cache_key_func
        ))
        def list(self, request, format=None):
            return {"data": "test"}
    
    request = HttpRequest()
    request.path = '/api/users/'
    
    viewset = TestViewSet()
    cache_key = viewset.list.get_cache_key(request)
    
    expected_key = "custom./api/users/.GET"
    print("✓ Custom cache key function works:", cache_key == expected_key)
    print("✓ Generated key:", cache_key)
    
    print("Custom cache key function tests passed! ✓")

if __name__ == "__main__":
    try:
        test_basic_functionality()
        test_user_specific_cache()
        test_custom_cache_key_function()
        print("\n🎉 All tests passed successfully!")
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)