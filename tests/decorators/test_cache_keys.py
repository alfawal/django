"""
Tests for the enhanced cache_page decorator with predictable cache keys.
"""

from django.http import HttpRequest
from django.test import SimpleTestCase, override_settings
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page_with_key
from django.utils.cache_keys import (
    get_view_cache_key,
    get_view_cache_key_pattern,
    invalidate_view_cache,
    get_cache_key_for_user,
)


class CacheKeyPredictabilityTest(SimpleTestCase):
    """Test cache key predictability for the enhanced cache_page decorator."""

    def setUp(self):
        self.request = HttpRequest()
        self.request.method = 'GET'
        self.request.META = {
            'HTTP_HOST': 'example.com',
            'HTTP_COOKIE': 'sessionid=abc123',
        }
        self.request.path = '/api/users/'

    def test_cache_page_with_key_decorator(self):
        """Test that cache_page_with_key decorator adds cache key functionality."""
        
        class TestViewSet:
            @method_decorator(cache_page_with_key(60 * 60 * 2))
            def list(self, request, format=None):
                return {"data": "test"}

        viewset = TestViewSet()
        
        # Check that the method has cache key functionality
        self.assertTrue(hasattr(viewset.list, 'get_cache_key'))
        self.assertTrue(hasattr(viewset.list, '_cache_key_func'))
        self.assertTrue(hasattr(viewset.list, '_cache_config'))
        
        # Test cache key generation
        cache_key = viewset.list.get_cache_key(self.request)
        self.assertIsInstance(cache_key, str)
        self.assertTrue(cache_key.startswith('views.decorators.cache.cache_page.'))

    def test_cache_key_consistency(self):
        """Test that cache keys are consistent for the same request."""
        
        class TestViewSet:
            @method_decorator(cache_page_with_key(60 * 60 * 2))
            def list(self, request, format=None):
                return {"data": "test"}

        viewset = TestViewSet()
        
        # Generate cache key multiple times
        key1 = viewset.list.get_cache_key(self.request)
        key2 = viewset.list.get_cache_key(self.request)
        
        # Keys should be identical
        self.assertEqual(key1, key2)

    def test_cache_key_different_requests(self):
        """Test that different requests generate different cache keys."""
        
        class TestViewSet:
            @method_decorator(cache_page_with_key(60 * 60 * 2))
            def list(self, request, format=None):
                return {"data": "test"}

        viewset = TestViewSet()
        
        # Create two different requests
        request1 = HttpRequest()
        request1.method = 'GET'
        request1.META = {'HTTP_HOST': 'example.com', 'HTTP_COOKIE': 'sessionid=abc123'}
        request1.path = '/api/users/'
        
        request2 = HttpRequest()
        request2.method = 'GET'
        request2.META = {'HTTP_HOST': 'example.com', 'HTTP_COOKIE': 'sessionid=def456'}
        request2.path = '/api/users/'
        
        # Generate cache keys
        key1 = viewset.list.get_cache_key(request1)
        key2 = viewset.list.get_cache_key(request2)
        
        # Keys should be different due to different cookies
        self.assertNotEqual(key1, key2)

    def test_cache_key_with_headers(self):
        """Test cache key generation with specific headers."""
        
        class TestViewSet:
            @method_decorator(cache_page_with_key(60 * 60 * 2))
            def list(self, request, format=None):
                return {"data": "test"}

        viewset = TestViewSet()
        
        # Test with different header lists
        key1 = viewset.list.get_cache_key(self.request, headerlist=['HTTP_COOKIE'])
        key2 = viewset.list.get_cache_key(self.request, headerlist=['HTTP_COOKIE', 'HTTP_ACCEPT_LANGUAGE'])
        
        # Keys should be different
        self.assertNotEqual(key1, key2)

    def test_get_view_cache_key_utility(self):
        """Test the get_view_cache_key utility function."""
        
        class TestViewSet:
            @method_decorator(cache_page_with_key(60 * 60 * 2))
            def list(self, request, format=None):
                return {"data": "test"}

        viewset = TestViewSet()
        
        # Test utility function
        cache_key = get_view_cache_key(viewset.list, self.request)
        self.assertIsInstance(cache_key, str)
        self.assertTrue(cache_key.startswith('views.decorators.cache.cache_page.'))

    def test_get_view_cache_key_pattern(self):
        """Test the get_view_cache_key_pattern utility function."""
        
        class TestViewSet:
            @method_decorator(cache_page_with_key(60 * 60 * 2))
            def list(self, request, format=None):
                return {"data": "test"}

        viewset = TestViewSet()
        
        # Test pattern generation
        pattern = get_view_cache_key_pattern(viewset.list)
        self.assertIsInstance(pattern, str)
        self.assertTrue(pattern.startswith('views.decorators.cache.cache_page.'))
        self.assertIn('*', pattern)  # Should contain wildcards

    def test_get_cache_key_for_user(self):
        """Test cache key generation for specific users."""
        
        class MockUser:
            def __init__(self, user_id):
                self.id = user_id

        class TestViewSet:
            @method_decorator(cache_page_with_key(60 * 60 * 2))
            def list(self, request, format=None):
                return {"data": "test"}

        viewset = TestViewSet()
        user = MockUser(123)
        
        # Test user-specific cache key
        cache_key = get_cache_key_for_user(user, viewset.list, self.request)
        self.assertIsInstance(cache_key, str)
        self.assertTrue(cache_key.startswith('views.decorators.cache.cache_page.'))
        
        # Different users should have different cache keys
        user2 = MockUser(456)
        cache_key2 = get_cache_key_for_user(user2, viewset.list, self.request)
        self.assertNotEqual(cache_key, cache_key2)

    def test_invalidate_view_cache(self):
        """Test cache invalidation functionality."""
        
        class TestViewSet:
            @method_decorator(cache_page_with_key(60 * 60 * 2))
            def list(self, request, format=None):
                return {"data": "test"}

        viewset = TestViewSet()
        
        # Test invalidation (should return False since cache is empty)
        result = invalidate_view_cache(viewset.list, self.request)
        self.assertIsInstance(result, bool)

    def test_custom_cache_key_function(self):
        """Test using a custom cache key function."""
        
        def custom_cache_key_func(request, method="GET", headerlist=None, key_prefix=None):
            return f"custom.{request.path}.{method}"

        class TestViewSet:
            @method_decorator(cache_page_with_key(60 * 60 * 2, cache_key_func=custom_cache_key_func))
            def list(self, request, format=None):
                return {"data": "test"}

        viewset = TestViewSet()
        
        # Test custom cache key generation
        cache_key = viewset.list.get_cache_key(self.request)
        self.assertEqual(cache_key, f"custom.{self.request.path}.GET")

    def test_cache_config_storage(self):
        """Test that cache configuration is properly stored."""
        
        class TestViewSet:
            @method_decorator(cache_page_with_key(60 * 60 * 2, key_prefix="test"))
            def list(self, request, format=None):
                return {"data": "test"}

        viewset = TestViewSet()
        
        # Check cache configuration
        config = viewset.list._cache_config
        self.assertEqual(config['timeout'], 60 * 60 * 2)
        self.assertEqual(config['key_prefix'], 'test')
        self.assertIsNone(config['cache_alias'])

    @override_settings(CACHE_MIDDLEWARE_KEY_PREFIX='test_prefix')
    def test_key_prefix_from_settings(self):
        """Test that key prefix is taken from settings when not specified."""
        
        class TestViewSet:
            @method_decorator(cache_page_with_key(60 * 60 * 2))
            def list(self, request, format=None):
                return {"data": "test"}

        viewset = TestViewSet()
        
        # Test cache key generation with settings prefix
        cache_key = viewset.list.get_cache_key(self.request)
        self.assertIn('test_prefix', cache_key)

    def test_drf_viewset_example(self):
        """Test the specific DRF ViewSet example from the user's request."""
        
        class UserViewSet:
            @method_decorator(cache_page_with_key(60 * 60 * 2))
            @method_decorator(lambda view_func: lambda request, *args, **kwargs: view_func(request, *args, **kwargs))  # Mock vary_on_cookie
            def list(self, request, format=None):
                content = {
                    "user_feed": "mock_user_feed",
                }
                return content

        viewset = UserViewSet()
        
        # Test that we can get the cache key
        cache_key = viewset.list.get_cache_key(self.request)
        self.assertIsInstance(cache_key, str)
        
        # Test that the cache key is predictable
        cache_key2 = viewset.list.get_cache_key(self.request)
        self.assertEqual(cache_key, cache_key2)
        
        # Test utility function access
        utility_key = get_view_cache_key(viewset.list, self.request)
        self.assertEqual(cache_key, utility_key)