import re
import unicodedata
from datetime import date as Date
from datetime import datetime, timedelta

import backoff
import httpx2
import jmespath

from allocine.models import MovieVersion, Showtime, Theater

DEFAULT_DATE_FORMAT = "%Y-%m-%dT%H:%M:%S"
SHOWTIMES_BASE_URL = "https://www.allocine.fr/_/showtimes"


class Allocine:
    def __init__(self):
        self.__client = Client()

    def get_theater(self, theater_id: str, date: Date | None = None):
        ret = self.__client.get_showtimelist_by_theater_id(theater_id=theater_id, date=date)
        if not ret.get("results"):
            raise ValueError(f"Theater not found. Is theater id {theater_id!r} correct?")

        theaters = self.__get_theaters_from_raw_showtimelist(raw_showtimelist=ret, theater_id=theater_id)
        if len(theaters) != 1:
            raise ValueError("Expecting 1 theater but received {}".format(len(theaters)))

        return theaters[0]

    def __get_theaters_from_raw_showtimelist(self, raw_showtimelist: dict, theater_id: str):
        raw_showtimes = raw_showtimelist.get("results") or []
        if not raw_showtimes:
            return []

        movie_id = raw_showtimes[0]["movie"]["internalId"]
        operation = self.__client.get_showtimes_by_movie_and_theater_id(
            movie_id=movie_id,
            theater_id=theater_id,
        )
        raw_theater = operation["results"]["theater"]
        location = raw_theater["location"]
        return [
            Theater(
                theater_id=raw_theater["internalId"],
                name=raw_theater["name"],
                address=location["address"],
                zipcode=location["zip"],
                city=location["city"],
                showtimes=self.__parse_showtimes(raw_showtimes=raw_showtimes),
            )
        ]

    def __parse_showtimes(self, raw_showtimes: list[dict]):
        showtimes = []
        for showtime_data in raw_showtimes:
            raw_movie = showtime_data["movie"]
            duration_match = re.fullmatch(r"(?:(\d+)h)?\s*(?:(\d+)min)?", raw_movie.get("runtime") or "")
            duration_obj = None
            if duration_match and any(duration_match.groups()):
                hours, minutes = duration_match.groups(default="0")
                duration_obj = timedelta(hours=int(hours), minutes=int(minutes))

            rating = jmespath.search("stats.userRating.score", raw_movie)
            try:
                rating = float(rating)
            except (ValueError, TypeError):
                rating = None

            countries = [country.get("localizedName") for country in raw_movie.get("countries") or []]
            countries = [country for country in countries if country]
            year = jmespath.search("data.productionYear", raw_movie)
            if year:
                year = int(year)

            directors = []
            for credit in sorted(raw_movie.get("credits") or [], key=lambda item: item.get("rank") or 0):
                if jmespath.search("position.name", credit) == "DIRECTOR":
                    name = _person_name(credit.get("person"))
                    if name:
                        directors.append(name)

            actors = []
            cast = jmespath.search("cast.nodes", raw_movie) or []
            for cast_member in sorted(cast, key=lambda item: item.get("rank") or 0):
                person = (
                    cast_member.get("actor") or cast_member.get("originalVoiceActor") or cast_member.get("voiceActor")
                )
                name = _person_name(person)
                if name:
                    actors.append(name)

            genres = ", ".join(genre["translate"] for genre in raw_movie.get("genres") or [] if genre.get("translate"))
            for showtime_group in (showtime_data.get("showtimes") or {}).values():
                for raw_showtime in showtime_group:
                    tags = raw_showtime.get("tags") or []
                    language = (
                        "Français"
                        if "Localization.Language.French" in tags
                        or raw_showtime.get("diffusionVersion") in {"DUBBED", "LOCAL"}
                        else "Version originale"
                    )
                    screen_formats = [
                        {"E_4DX": "4DX", "PLF": "PLF"}.get(value, value)
                        for value in raw_showtime.get("experience") or []
                    ]
                    screen_formats.extend(
                        {"DIGITAL": "Numérique", "IMAX": "IMAX", "F_3D": "3D"}.get(value, value)
                        for value in raw_showtime.get("projection") or []
                        if value != "DIGITAL" or not screen_formats
                    )
                    movie = MovieVersion(
                        movie_id=raw_movie["internalId"],
                        title=raw_movie.get("title"),
                        rating=rating,
                        language=language,
                        screen_format=" ".join(screen_formats) or "Numérique",
                        synopsis=_clean_synopsis(raw_movie.get("synopsis")),
                        original_title=raw_movie.get("originalTitle"),
                        year=year,
                        countries=countries,
                        genres=genres,
                        directors=", ".join(directors),
                        actors=", ".join(actors),
                        duration=duration_obj,
                    )
                    showtimes.append(
                        Showtime(
                            date_time=_str_datetime_to_datetime_obj(raw_showtime["startsAt"]),
                            movie=movie,
                        )
                    )
        return showtimes


class Error503(Exception):
    pass


class Client:
    """Client to process requests with the Allocine APIs."""

    def __init__(self):
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; \
                                   Intel Mac OS X 10.14; rv:63.0) \
                                   Gecko/20100101 Firefox/63.0",
        }
        self.session = httpx2.Client(headers=headers, timeout=None)

    @backoff.on_exception(backoff.expo, Error503, max_tries=5, max_time=30)
    def _get(self, url: str, expected_status: int = 200, *args, **kwargs) -> dict:
        ret = self.session.get(url, *args, **kwargs)
        if ret.status_code != expected_status:
            if ret.status_code == 503:
                raise Error503
            raise ValueError("{!r} : expected status {}, received {}".format(url, expected_status, ret.status_code))
        return ret.json()

    def get_showtimelist_by_theater_id(
        self,
        theater_id: str,
        page: int | None = None,
        date: Date | None = None,
    ):
        date = date or datetime.now().date()
        first_page = page or 1
        url = f"{SHOWTIMES_BASE_URL}/theater-{theater_id}/d-{date.isoformat()}/p-{first_page}/"
        response = self._get(url=url)

        if page is not None:
            return response

        response = {**response, "results": list(response.get("results") or [])}
        pagination = response.get("pagination")
        total_pages = int(pagination.get("totalPages", 1)) if isinstance(pagination, dict) else 1
        for next_page in range(2, total_pages + 1):
            url = f"{SHOWTIMES_BASE_URL}/theater-{theater_id}/d-{date.isoformat()}/p-{next_page}/"
            next_response = self._get(url=url)
            response["results"].extend(next_response.get("results") or [])
        return response

    def get_showtimes_by_movie_and_theater_id(self, movie_id: int, theater_id: str):
        url = f"{SHOWTIMES_BASE_URL}/ope/movie-{movie_id}/theater-{theater_id}/"
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


def _person_name(person):
    if not person:
        return None
    return " ".join(part for part in (person.get("firstName"), person.get("lastName")) if part)
