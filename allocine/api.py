from datetime import date as Date
from os import PathLike

import backoff
import httpx2

from allocine.cache import CACHE_MISS, CachedResponse, CacheOption, HttpCache

SHOWTIMES_BASE_URL = "https://www.allocine.fr/_/showtimes"
THEATERS_BASE_URL = "https://www.allocine.fr/salle/cinema"


class AllocineApi:
    """Client to process requests with the Allocine APIs."""

    def __init__(
        self,
        *,
        cache: CacheOption = False,
        cache_dir: str | PathLike[str] | None = None,
    ):
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; \
                                   Intel Mac OS X 10.14; rv:63.0) \
                                   Gecko/20100101 Firefox/63.0",
        }
        self.session = httpx2.Client(headers=headers, timeout=30)
        self.cache = HttpCache(cache, cache_dir)

    def get_showtimelist_by_theater_id(
        self,
        theater_id: str,
        page: int | None = None,
        date: Date | None = None,
    ):
        url = f"{SHOWTIMES_BASE_URL}/theater-{theater_id}/"
        if date:
            url += f"d-{date.isoformat()}/"
        if page:
            url += f"p-{page}/"

        return self._get(url)

    def get_showtimes_by_movie_and_theater_id(
        self,
        movie_id: int,
        theater_id: str,
    ):
        url = f"{SHOWTIMES_BASE_URL}/ope/movie-{movie_id}/theater-{theater_id}/"
        return self._get(url)

    def get_theater_page(self, theater_id: str) -> str:
        url = f"https://www.allocine.fr/seance/salle_gen_csalle={theater_id}.html"
        return self._get_text(url)

    def get_theaterlist_by_geocode(self, geocode: int | str, page: int = 1) -> str:
        url = f"{THEATERS_BASE_URL}/ville-{geocode}/"
        params = {"page": page} if page > 1 else None
        return self._get_text(url, params=params)

    def clear_cache(self) -> int:
        return self.cache.clear()

    def close(self) -> None:
        self.session.close()
        self.cache.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    def _get(self, url: str, expected_status: int = 200, *args, **kwargs) -> dict:
        return self._request(url, expected_status, *args, **kwargs).json()

    def _get_text(self, url: str, expected_status: int = 200, *args, **kwargs) -> str:
        return self._request(url, expected_status, *args, **kwargs).text

    def _request(self, url: str, expected_status: int, *args, **kwargs) -> httpx2.Response:
        params = kwargs.get("params")
        cached = self.cache.get(url, params)
        if cached is not CACHE_MISS and cached.is_fresh():
            return cached.to_response()

        if cached is not CACHE_MISS:
            headers = dict(kwargs.get("headers") or {})
            if etag := cached.headers.get("etag"):
                headers["If-None-Match"] = etag
            if last_modified := cached.headers.get("last-modified"):
                headers["If-Modified-Since"] = last_modified
            kwargs["headers"] = headers

        try:
            response = self._fetch(url, expected_status, *args, **kwargs)
        except (ValueError, httpx2.HTTPError):
            if cached is not CACHE_MISS and cached.can_serve_on_error():
                return cached.to_response()
            raise

        if response.status_code == 304 and cached is not CACHE_MISS:
            response = self._revalidated_response(cached, response)
        self.cache.set(url, response, params)
        return response

    @backoff.on_exception(backoff.expo, ValueError, max_tries=5, max_time=30)
    def _fetch(self, url: str, expected_status: int, *args, **kwargs) -> httpx2.Response:
        ret = self.session.get(url, *args, **kwargs)
        if ret.status_code not in {expected_status, 304}:
            raise ValueError("{!r} : expected status {}, received {}".format(url, expected_status, ret.status_code))
        return ret

    @staticmethod
    def _revalidated_response(cached: CachedResponse, response: httpx2.Response) -> httpx2.Response:
        return cached.to_response(response.headers)
