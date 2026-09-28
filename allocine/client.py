import json
import re
import unicodedata
from datetime import date as Date
from datetime import datetime, timedelta
from os import PathLike

import jmespath
from parsel import Selector

from allocine.api import AllocineApi
from allocine.cache import CacheOption
from allocine.models import MovieVersion, Showtime, Theater

DEFAULT_DATE_FORMAT = "%Y-%m-%dT%H:%M:%S"


class Allocine:
    def __init__(
        self,
        *,
        cache: CacheOption = True,
        cache_dir: str | PathLike[str] | None = None,
    ):
        self._client = AllocineApi(cache=cache, cache_dir=cache_dir)

    def get_theater(self, theater_id: str) -> Theater:
        resp = self._client.get_showtimelist_by_theater_id(theater_id=theater_id)
        if not resp.get("results"):
            raise ValueError(f"Theater not found. Is theater id {theater_id!r} correct?")

        movie_id: int | None = jmespath.search("results[0].movie.internalId", resp)
        assert movie_id is not None, "We need at least one showtime to get details about a theater"

        return self._get_theater_details_from_movie_id(theater_id, movie_id)

    def get_showtimes(
        self,
        theater_id: str,
        from_date: Date | None = None,
        to_date: Date | None = None,
    ) -> list[Showtime]:
        today = Date.today()
        from_date = max(from_date or today, today)
        to_date = to_date or from_date
        if from_date > to_date:
            raise ValueError("from_date must be before or equal to to_date")

        showtimes = []
        requested_date = from_date
        while requested_date <= to_date:
            response = self._client.get_showtimelist_by_theater_id(
                theater_id=theater_id,
                date=requested_date,
            )
            day_showtimes = self._parse_showtimes(response.get("results") or [])
            for page in range(2, (jmespath.search("pagination.totalPages", response) or 1) + 1):
                response = self._client.get_showtimelist_by_theater_id(
                    theater_id=theater_id,
                    date=requested_date,
                    page=page,
                )
                day_showtimes.extend(self._parse_showtimes(response.get("results") or []))

            showtimes.extend(showtime for showtime in day_showtimes if showtime.date == requested_date)
            requested_date += timedelta(days=1)

        return showtimes

    def search_theaters(self, geocode: int | str) -> list[Theater]:
        theaters = []
        page = 1
        while True:
            selector = Selector(text=self._client.get_theaterlist_by_geocode(geocode=geocode, page=page))
            theaters.extend(_parse_theaters(selector))
            if not selector.css(".button-right:not(.button-disabled)"):
                return theaters
            page += 1

    def clear_cache(self) -> int:
        return self._client.clear_cache()

    def close(self) -> None:
        self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    def _get_theater_details_from_movie_id(self, theater_id: str, movie_id: int) -> Theater:
        operation = self._client.get_showtimes_by_movie_and_theater_id(
            movie_id=movie_id,
            theater_id=theater_id,
        )
        raw_theater = operation["results"]["theater"]
        if raw_theater is None:
            return self._get_theater_details_from_page(theater_id)

        location = raw_theater["location"]
        return Theater(
            theater_id=raw_theater["internalId"],
            name=raw_theater["name"],
            address=location["address"],
            zipcode=location["zip"],
            city=location["city"],
        )

    def _get_theater_details_from_page(self, theater_id: str) -> Theater:
        selector = Selector(text=self._client.get_theater_page(theater_id))
        for raw_data in selector.css('script[type="application/ld+json"]::text').getall():
            theater_data = json.loads(raw_data)
            if theater_data.get("@type") != "MovieTheater":
                continue

            address = theater_data.get("address") or {}
            return Theater(
                theater_id=theater_id,
                name=theater_data["name"],
                address=address.get("streetAddress") or "",
                zipcode=address.get("postalCode") or "",
                city=address.get("addressLocality") or "",
            )

        raise ValueError(f"Theater details not found for theater id {theater_id!r}")

    def _parse_showtimes(self, raw_showtimes: list[dict]):
        showtimes = []
        for showtime_data in raw_showtimes:
            raw_movie = showtime_data.get("movie")
            if not raw_movie:
                continue
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
            if year := jmespath.search("data.productionYear", raw_movie):
                year = int(year)

            directors = []
            for credit in sorted(raw_movie.get("credits") or [], key=lambda item: item.get("rank") or 0):
                if jmespath.search("position.name", credit) == "DIRECTOR":
                    if name := _person_name(credit.get("person")):
                        directors.append(name)

            actors = []
            cast = jmespath.search("cast.nodes", raw_movie) or []
            for cast_member in sorted(cast, key=lambda item: item.get("rank") or 0):
                person = (
                    cast_member.get("actor") or cast_member.get("originalVoiceActor") or cast_member.get("voiceActor")
                )
                if name := _person_name(person):
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

                    if synopsis := raw_movie.get("synopsis"):
                        synopsis = re.sub(r"<.*?>", "", synopsis)
                        synopsis = synopsis.replace("\xa0", " ")  # Remove HTML tags (ex: <span>)
                        synopsis = unicodedata.normalize("NFKD", synopsis)

                    movie = MovieVersion(
                        movie_id=raw_movie["internalId"],
                        title=raw_movie.get("title"),
                        rating=rating,
                        language=language,
                        screen_format=" ".join(screen_formats) or "Numérique",
                        synopsis=synopsis,
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
                            date_time=datetime.strptime(raw_showtime["startsAt"], DEFAULT_DATE_FORMAT),
                            movie=movie,
                        )
                    )
        return showtimes


def _person_name(person):
    if not person:
        return None
    return " ".join(part for part in (person.get("firstName"), person.get("lastName")) if part)


def _parse_theaters(selector: Selector) -> list[Theater]:
    theaters = []
    for card in selector.css("div.theater-card"):
        theater_json = card.css(".add-theater-anchor[data-theater]::attr(data-theater)").get()
        if not theater_json:
            continue

        theater_data = json.loads(theater_json)
        full_address = " ".join((card.css("address.address").xpath("string()").get() or "").split())
        address_match = re.fullmatch(r"(.*)\s+(\d{5})\s+(.+)", full_address)
        address, zipcode, city = address_match.groups() if address_match else (full_address, "", "")
        theaters.append(
            Theater(
                theater_id=theater_data["id"],
                name=theater_data["name"],
                address=address,
                zipcode=zipcode,
                city=city,
            )
        )
    return theaters
