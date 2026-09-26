import re
import unicodedata
from datetime import datetime, timedelta

import backoff
import httpx2
import jmespath

from allocine.models import MovieVersion, Showtime, Theater

DEFAULT_DATE_FORMAT = "%Y-%m-%dT%H:%M:%S"
BASE_URL = "http://api.allocine.fr/rest/v3"
PARTNER_KEY = "000042532791"


class Allocine:
    def __init__(self, base_url=BASE_URL):
        self.__client = Client(base_url=base_url)
        self.__movie_store = {}  # Dict to store the movie info (and avoid useless requests)

    def get_theater(self, theater_id: str):
        ret = self.__client.get_showtimelist_by_theater_id(theater_id=theater_id)
        if jmespath.search("feed.totalResults", ret) == 0:
            raise ValueError(f"Theater not found. Is theater id {theater_id!r} correct?")

        theaters = self.__get_theaters_from_raw_showtimelist(raw_showtimelist=ret)
        if len(theaters) != 1:
            raise ValueError("Expecting 1 theater but received {}".format(len(theaters)))

        return theaters[0]

    def __get_theaters_from_raw_showtimelist(self, raw_showtimelist: dict, distance_max_inclusive: int = 0):
        theaters = []
        for theater_showtime in jmespath.search("feed.theaterShowtimes", raw_showtimelist):
            raw_theater = jmespath.search("place.theater", theater_showtime)

            if raw_theater.get("distance") is not None:
                # distance is not present when theater ids were used for search
                if raw_theater.get("distance") > distance_max_inclusive:
                    # Skip theaters that are above the max distance specified
                    continue

            raw_showtimes = jmespath.search("movieShowtimes", theater_showtime)
            showtimes = self.__parse_showtimes(raw_showtimes=raw_showtimes)
            theater = Theater(
                theater_id=raw_theater.get("code"),
                name=raw_theater.get("name"),
                address=raw_theater.get("address"),
                zipcode=raw_theater.get("postalCode"),
                city=raw_theater.get("city"),
                showtimes=showtimes,
            )
            theaters.append(theater)
        return theaters

    def search_theaters(self, geocode: int):
        theaters = []
        page = 1
        while True:
            ret = self.__client.get_showtimelist_from_geocode(geocode=geocode, page=page)
            total_results = jmespath.search("feed.totalResults", ret)
            if total_results == 0:
                raise ValueError(f"Theater not found. Is geocode {geocode!r} correct?")

            theaters_to_parse = jmespath.search("feed.theaterShowtimes", ret)
            if theaters_to_parse:
                theaters += self.__get_theaters_from_raw_showtimelist(raw_showtimelist=ret, distance_max_inclusive=0)
                page += 1
            else:
                break
        return theaters

    def __parse_showtimes(self, raw_showtimes: dict):
        showtimes = []
        for showtime_data in raw_showtimes:
            raw_movie = jmespath.search("onShow.movie", showtime_data)
            language = jmespath.search('version."$"', showtime_data)
            screen_format = jmespath.search('screenFormat."$"', showtime_data)
            duration = raw_movie.get("runtime")
            duration_obj = timedelta(seconds=duration) if duration else None

            rating = jmespath.search("statistics.userRating", raw_movie)
            try:
                rating = float(rating)
            except (ValueError, TypeError):
                rating = None

            movie_id = raw_movie.get("code")
            movie_info = self.get_movie_info(movie_id)
            countries = jmespath.search('nationality[]."$"', movie_info)
            year = movie_info.get("productionYear")
            if year:
                year = int(year)
            movie = MovieVersion(
                movie_id=movie_id,
                title=raw_movie.get("title"),
                rating=rating,
                language=language,
                screen_format=screen_format,
                synopsis=_clean_synopsis(movie_info.get("synopsis")),
                original_title=movie_info.get("originalTitle"),
                year=year,
                countries=countries,
                genres=", ".join(jmespath.search('genre[]."$"', movie_info)),
                directors=jmespath.search("castingShort.directors", movie_info),
                actors=jmespath.search("castingShort.actors", movie_info),
                duration=duration_obj,
            )
            for showtimes_of_day in showtime_data.get("scr") or []:
                day = showtimes_of_day.get("d")
                for one_showtime in showtimes_of_day.get("t"):
                    datetime_str = "{}T{}:00".format(day, one_showtime.get("$"))
                    datetime_obj = _str_datetime_to_datetime_obj(datetime_str)
                    showtime = Showtime(
                        date_time=datetime_obj,
                        movie=movie,
                    )
                    showtimes.append(showtime)
        return showtimes

    def get_movie_info(self, movie_id: int):
        movie_info = self.__movie_store.get(movie_id)
        if movie_info is None:
            movie_info = self.__client.get_movie_info_by_id(movie_id).get("movie")
            self.__movie_store[movie_id] = movie_info
        return movie_info


class SingletonMeta(type):
    _instance = None

    def __call__(self, *args, **kwargs):
        if self._instance is None:
            self._instance = super().__call__(*args, **kwargs)
        return self._instance


class Error503(Exception):
    pass


class Client(metaclass=SingletonMeta):
    """Client to process the requests with allocine APIs.
    This is a singleton to avoid the creation of a new session for every theater.
    """

    def __init__(self, base_url):
        self.base_url = base_url
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; \
                                   Intel Mac OS X 10.14; rv:63.0) \
                                   Gecko/20100101 Firefox/63.0",
        }
        self.session = httpx2.Client(headers=headers, timeout=None)

    @backoff.on_exception(backoff.expo, Error503, max_tries=5, max_time=30)
    def _get(self, url: str, expected_status: int = 200, *args, **kwargs):
        ret = self.session.get(url, *args, **kwargs)
        if ret.status_code != expected_status:
            if ret.status_code == 503:
                raise Error503
            raise ValueError("{!r} : expected status {}, received {}".format(url, expected_status, ret.status_code))
        return ret.json()

    def get_showtimelist_by_theater_id(self, theater_id: str, page: int = 1, count: int = 10):
        url = (
            f"{self.base_url}/showtimelist?partner={PARTNER_KEY}&format=json"
            f"&theaters={theater_id}&page={page}&count={count}"
        )
        return self._get(url=url)

    def get_theater_info_by_id(self, theater_id: str):
        url = f"{self.base_url}/theater?partner={PARTNER_KEY}&format=json&code={theater_id}"
        return self._get(url=url)

    def get_showtimelist_from_geocode(self, geocode: int, page: int = 1, count: int = 10):
        url = (
            f"{self.base_url}/showtimelist?partner={PARTNER_KEY}&format=json"
            f"&geocode={geocode}&page={page}&count={count}"
        )
        return self._get(url=url)

    def get_movie_info_by_id(self, movie_id: int):
        url = f"{self.base_url}/movie?partner={PARTNER_KEY}&format=json&code={movie_id}"
        return self._get(url=url)


def _str_datetime_to_datetime_obj(datetime_str, date_format=DEFAULT_DATE_FORMAT):
    return datetime.strptime(datetime_str, date_format)


def _cleanhtml(raw_html):
    cleanr = re.compile("<.*?>")
    cleantext = re.sub(cleanr, "", raw_html)
    return cleantext


def _clean_synopsis(raw_synopsis):
    if raw_synopsis is None:
        return None

    synopsis = _cleanhtml(raw_synopsis)  # Remove HTML tags (ex: <span>)
    synopsis = synopsis.replace("\xa0", " ")
    return unicodedata.normalize("NFKD", synopsis)
