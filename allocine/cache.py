from collections.abc import Mapping
from dataclasses import dataclass
from json import loads
from os import PathLike
from time import time
from urllib.parse import urlencode
from weakref import finalize

from diskcache import Cache
from platformdirs import user_cache_path

CACHE_VERSION = 3
CACHE_MISS = object()

CacheOption = bool | Cache


@dataclass
class HttpResponse:
    status_code: int
    headers: dict[str, str]
    content: bytes = b""

    @property
    def text(self) -> str:
        return self.content.decode("utf-8", errors="replace")

    def json(self):
        return loads(self.content)


@dataclass(frozen=True)
class CachedResponse:
    status_code: int
    headers: dict[str, str]
    content: bytes
    stored_at: float
    initial_age: int
    max_age: int
    stale_if_error: int
    stale_while_revalidate: int

    def age(self, now: float | None = None) -> float:
        return self.initial_age + (time() if now is None else now) - self.stored_at

    def is_fresh(self, now: float | None = None) -> bool:
        return self.age(now) < self.max_age

    def can_serve_on_error(self, now: float | None = None) -> bool:
        return self.age(now) < self.max_age + self.stale_if_error

    def retention(self) -> float:
        stale = max(self.stale_if_error, self.stale_while_revalidate)
        return self.max_age + stale - self.initial_age

    def to_response(self, revalidation_headers: Mapping[str, str] | None = None) -> HttpResponse:
        headers = dict(self.headers)
        if revalidation_headers is not None:
            headers.pop("age", None)
            headers.update(revalidation_headers)
        return HttpResponse(self.status_code, _decoded_headers(headers), self.content)


class HttpCache:
    def __init__(
        self,
        cache: CacheOption = False,
        cache_dir: str | PathLike[str] | None = None,
    ) -> None:
        if cache_dir is not None and cache is not True:
            raise ValueError("cache_dir can only be used when cache=True")

        self._owns_backend = cache is True
        self._backend = (
            Cache(cache_dir or user_cache_path("allocine")) if cache is True else None if cache is False else cache
        )
        self._finalizer = (
            finalize(self, self._backend.close) if self._owns_backend and self._backend is not None else None
        )

    def get(self, url: str, params: dict | None = None):
        if self._backend is None:
            return CACHE_MISS
        return self._backend.get(self._key(url, params), default=CACHE_MISS)

    def set(self, url: str, response: HttpResponse, params: dict | None = None) -> None:
        if self._backend is None or (cached := _to_cached_response(response)) is None:
            return
        if (retention := cached.retention()) > 0:
            self._backend.set(self._key(url, params), cached, expire=retention)

    def clear(self) -> int:
        return self._backend.clear() if self._backend is not None else 0

    def close(self) -> None:
        if self._finalizer is not None:
            self._finalizer()

    @staticmethod
    def _key(url: str, params: dict | None) -> str:
        query = urlencode(sorted((params or {}).items()), doseq=True)
        return f"http:v{CACHE_VERSION}:{url}?{query}"


def _to_cached_response(response: HttpResponse) -> CachedResponse | None:
    directives = _parse_cache_control(response.headers.get("cache-control", ""))
    if "public" not in directives or "no-store" in directives or "private" in directives:
        return None
    if (max_age := _seconds(directives, "max-age")) is None:
        return None

    return CachedResponse(
        status_code=response.status_code,
        headers=_decoded_headers(response.headers),
        content=response.content,
        stored_at=time(),
        initial_age=_header_seconds(response.headers.get("age")) or 0,
        max_age=max_age,
        stale_if_error=_seconds(directives, "stale-if-error") or 0,
        stale_while_revalidate=_seconds(directives, "stale-while-revalidate") or 0,
    )


def _parse_cache_control(value: str) -> dict[str, str | None]:
    directives = {}
    for item in value.split(","):
        name, separator, directive_value = item.strip().partition("=")
        if name:
            directives[name.lower()] = directive_value.strip('"') if separator else None
    return directives


def _decoded_headers(headers: Mapping[str, str]) -> dict[str, str]:
    decoded_headers = dict(headers)
    for name in ("content-encoding", "content-length", "transfer-encoding"):
        decoded_headers.pop(name, None)
    return decoded_headers


def _seconds(directives: dict[str, str | None], name: str) -> int | None:
    return _header_seconds(directives.get(name))


def _header_seconds(value: str | None) -> int | None:
    try:
        return max(0, int(value)) if value is not None else None
    except ValueError:
        return None
