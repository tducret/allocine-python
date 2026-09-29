import pytest
from diskcache import Cache

from allocine.cache import CACHE_MISS, HttpCache, HttpResponse

CACHE_CONTROL = "max-age=3600, public, stale-if-error=172800, stale-while-revalidate=86400"


def response(cache_control: str = CACHE_CONTROL) -> HttpResponse:
    result = HttpResponse(
        status_code=200,
        headers={"cache-control": cache_control, "age": "300", "last-modified": "Sun, 27 Sep 2026 20:55:44 GMT"},
        content=b'{"results": []}',
    )
    result.headers["content-encoding"] = "gzip"
    result.headers["content-length"] = "123"
    return result


def test_cache_is_disabled_by_default():
    cache = HttpCache()

    cache.set("https://example.com", response())

    assert cache.get("https://example.com") is CACHE_MISS
    assert cache.clear() == 0


def test_response_cache_policy_and_clear(tmp_path):
    cache = HttpCache(True, tmp_path)
    cache.set("https://example.com", response(), {"page": 1})

    cached = cache.get("https://example.com", {"page": 1})
    assert cached.is_fresh(cached.stored_at + 3299)
    assert not cached.is_fresh(cached.stored_at + 3300)
    assert cached.can_serve_on_error(cached.stored_at + 176099)
    assert not cached.can_serve_on_error(cached.stored_at + 176100)
    assert cached.to_response().json() == {"results": []}
    assert "content-encoding" not in cached.headers
    assert "content-length" not in cached.headers
    cached.headers["content-encoding"] = "gzip"  # Existing cache entries may still contain this header.
    assert cached.to_response().json() == {"results": []}
    assert cache.get("https://example.com", {"page": 2}) is CACHE_MISS
    assert cache.clear() == 1
    cache.close()


@pytest.mark.parametrize("cache_control", ["", "private, max-age=3600", "public, no-store, max-age=3600"])
def test_response_is_not_cacheable(cache_control, tmp_path):
    cache = HttpCache(True, tmp_path)

    cache.set("https://example.com", response(cache_control))

    assert cache.get("https://example.com") is CACHE_MISS
    cache.close()


def test_cache_is_persistent(tmp_path):
    first_cache = HttpCache(True, tmp_path)
    first_cache.set("https://example.com", response())
    first_cache.close()

    second_cache = HttpCache(True, tmp_path)
    assert second_cache.get("https://example.com").to_response().content == b'{"results": []}'
    second_cache.close()


def test_injected_cache_is_used(tmp_path):
    with Cache(tmp_path) as backend:
        cache = HttpCache(backend)
        cache.set("https://example.com", response())

        assert cache.get("https://example.com") is not CACHE_MISS


def test_cache_dir_requires_managed_cache(tmp_path):
    with pytest.raises(ValueError, match="cache_dir can only be used when cache=True"):
        HttpCache(False, tmp_path)
