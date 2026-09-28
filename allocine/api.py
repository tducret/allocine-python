from datetime import date as Date

import backoff
import httpx2

SHOWTIMES_BASE_URL = "https://www.allocine.fr/_/showtimes"
THEATERS_BASE_URL = "https://www.allocine.fr/salle/cinema"


class AllocineApi:
    """Client to process requests with the Allocine APIs."""

    def __init__(self):
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; \
                                   Intel Mac OS X 10.14; rv:63.0) \
                                   Gecko/20100101 Firefox/63.0",
        }
        self.session = httpx2.Client(headers=headers, timeout=30)

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

        return self._get(url=url)

    def get_showtimes_by_movie_and_theater_id(self, movie_id: int, theater_id: str):
        url = f"{SHOWTIMES_BASE_URL}/ope/movie-{movie_id}/theater-{theater_id}/"
        return self._get(url=url)

    def get_theater_page(self, theater_id: str) -> str:
        url = f"https://www.allocine.fr/seance/salle_gen_csalle={theater_id}.html"
        return self._get_text(url=url)

    def get_theaterlist_by_geocode(self, geocode: int | str, page: int = 1) -> str:
        url = f"{THEATERS_BASE_URL}/ville-{geocode}/"
        params = {"page": page} if page > 1 else None
        return self._get_text(url=url, params=params)

    @backoff.on_exception(backoff.expo, ValueError, max_tries=5, max_time=30)
    def _get(self, url: str, expected_status: int = 200, *args, **kwargs) -> dict:
        ret = self.session.get(url, *args, **kwargs)
        if ret.status_code != expected_status:
            raise ValueError("{!r} : expected status {}, received {}".format(url, expected_status, ret.status_code))
        return ret.json()

    @backoff.on_exception(backoff.expo, ValueError, max_tries=5, max_time=30)
    def _get_text(self, url: str, expected_status: int = 200, *args, **kwargs) -> str:
        ret = self.session.get(url, *args, **kwargs)
        if ret.status_code != expected_status:
            raise ValueError("{!r} : expected status {}, received {}".format(url, expected_status, ret.status_code))
        return ret.text
