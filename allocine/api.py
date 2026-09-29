import logging
from datetime import date as Date
from datetime import timedelta
from os import PathLike

import backoff
import wreq
from wreq.blocking import Client, Response

from allocine.cache import CACHE_MISS, CachedResponse, CacheOption, HttpCache, HttpResponse

logger = logging.getLogger(__name__)

SHOWTIMES_BASE_URL = "https://www.allocine.fr/_/showtimes"
THEATERS_BASE_URL = "https://www.allocine.fr/salle/cinema"


class _RateLimitError(Exception):
    pass


class AllocineApi:
    """Client to process requests with the Allocine APIs."""

    def __init__(
        self,
        *,
        cache: CacheOption = False,
        cache_dir: str | PathLike[str] | None = None,
    ):
        self.session = self._new_client()
        self.cache = HttpCache(cache, cache_dir)

    def _new_client(self) -> Client:
        return Client(emulation=wreq.Emulation.random(), timeout=timedelta(seconds=30))

    def _recreate_client(self) -> None:
        logger.info("Recreating HTTP client")
        self.session.close()
        self.session = self._new_client()

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

        response = self._request(url, 200, not_found_ok=True)
        if response.status_code == 404:
            return {"results": []}
        return response.json()

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

    def get_locationlist(self, department_geocode: int | None = None, page: int = 1) -> str:
        if department_geocode is None:
            return self._get_text("https://www.allocine.fr/salle/")
        params = {"page": page} if page > 1 else None
        return self._get_text(f"{THEATERS_BASE_URL}/departement-{department_geocode}/", params=params)

    def get_city_locations(self, search: str) -> dict:
        return self._get(f"https://www.allocine.fr/_/localization_city/{search}")

    def get_theaterlist_by_geocode(
        self,
        geocode: int | str,
        page: int = 1,
        location_type: str = "ville",
    ) -> str:
        url = f"{THEATERS_BASE_URL}/{location_type}-{geocode}/"
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

    def _request(
        self,
        url: str,
        expected_status: int,
        *args,
        not_found_ok: bool = False,
        **kwargs,
    ) -> HttpResponse:
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
            response = self._fetch(url, expected_status, *args, not_found_ok=not_found_ok, **kwargs)
        except (
            _RateLimitError,
            ValueError,
            wreq.BodyError,
            wreq.ConnectionError,
            wreq.ConnectionResetError,
            wreq.DecodingError,
            wreq.RedirectError,
            wreq.RequestError,
            wreq.TimeoutError,
            wreq.TlsError,
        ):
            if cached is not CACHE_MISS and cached.can_serve_on_error():
                return cached.to_response()
            raise

        if response.status_code == 304 and cached is not CACHE_MISS:
            response = self._revalidated_response(cached, response)
        if response.status_code == 200:
            self.cache.set(url, response, params)
        return response

    @backoff.on_exception(
        backoff.expo,
        _RateLimitError,
        factor=10,
        max_value=60,
        max_tries=7,
        jitter=None,
        on_backoff=lambda details: details["args"][0]._recreate_client(),
    )
    @backoff.on_exception(backoff.expo, ValueError, max_tries=5, max_time=30)
    def _fetch(
        self,
        url: str,
        expected_status: int,
        *args,
        not_found_ok: bool = False,
        **kwargs,
    ) -> HttpResponse:
        if params := kwargs.pop("params", None):
            kwargs["query"] = params
        ret = self.session.get(url, *args, **kwargs)
        status_code = ret.status.as_int()
        if status_code == 429:
            ret.close()
            raise _RateLimitError(f"{url!r}: rate limit exceeded")
        try:
            response = HttpResponse(status_code, self._response_headers(ret), ret.bytes())
        finally:
            ret.close()
        if status_code not in {expected_status, 304} and not (not_found_ok and status_code == 404):
            raise ValueError("{!r} : expected status {}, received {}".format(url, expected_status, status_code))
        return response

    @staticmethod
    def _response_headers(response: Response) -> dict[str, str]:
        return {name.decode("ascii"): value.decode("latin-1") for name, value in response.headers}

    @staticmethod
    def _revalidated_response(cached: CachedResponse, response: HttpResponse) -> HttpResponse:
        return cached.to_response(response.headers)
