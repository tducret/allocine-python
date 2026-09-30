import base64
import json
import re
import unicodedata
from collections import Counter
from datetime import date as Date
from datetime import datetime, timedelta
from os import PathLike

import jmespath
from parsel import Selector

from allocine.api import AllocineApi
from allocine.cache import CacheOption
from allocine.models import Location, MovieVersion, Showtime, Theater

DEFAULT_DATE_FORMAT = "%Y-%m-%dT%H:%M:%S"

DEPARTMENT_NAMES = {
    "01": "Ain",
    "02": "Aisne",
    "03": "Allier",
    "04": "Alpes-de-Haute-Provence",
    "05": "Hautes-Alpes",
    "06": "Alpes-Maritimes",
    "07": "Ardèche",
    "08": "Ardennes",
    "09": "Ariège",
    "10": "Aube",
    "11": "Aude",
    "12": "Aveyron",
    "13": "Bouches-du-Rhône",
    "14": "Calvados",
    "15": "Cantal",
    "16": "Charente",
    "17": "Charente-Maritime",
    "18": "Cher",
    "19": "Corrèze",
    "2A": "Corse-du-Sud",
    "2B": "Haute-Corse",
    "21": "Côte-d'Or",
    "22": "Côtes-d'Armor",
    "23": "Creuse",
    "24": "Dordogne",
    "25": "Doubs",
    "26": "Drôme",
    "27": "Eure",
    "28": "Eure-et-Loir",
    "29": "Finistère",
    "30": "Gard",
    "31": "Haute-Garonne",
    "32": "Gers",
    "33": "Gironde",
    "34": "Hérault",
    "35": "Ille-et-Vilaine",
    "36": "Indre",
    "37": "Indre-et-Loire",
    "38": "Isère",
    "39": "Jura",
    "40": "Landes",
    "41": "Loir-et-Cher",
    "42": "Loire",
    "43": "Haute-Loire",
    "44": "Loire-Atlantique",
    "45": "Loiret",
    "46": "Lot",
    "47": "Lot-et-Garonne",
    "48": "Lozère",
    "49": "Maine-et-Loire",
    "50": "Manche",
    "51": "Marne",
    "52": "Haute-Marne",
    "53": "Mayenne",
    "54": "Meurthe-et-Moselle",
    "55": "Meuse",
    "56": "Morbihan",
    "57": "Moselle",
    "58": "Nièvre",
    "59": "Nord",
    "60": "Oise",
    "61": "Orne",
    "62": "Pas-de-Calais",
    "63": "Puy-de-Dôme",
    "64": "Pyrénées-Atlantiques",
    "65": "Hautes-Pyrénées",
    "66": "Pyrénées-Orientales",
    "67": "Bas-Rhin",
    "68": "Haut-Rhin",
    "69": "Rhône",
    "70": "Haute-Saône",
    "71": "Saône-et-Loire",
    "72": "Sarthe",
    "73": "Savoie",
    "74": "Haute-Savoie",
    "75": "Paris",
    "76": "Seine-Maritime",
    "77": "Seine-et-Marne",
    "78": "Yvelines",
    "79": "Deux-Sèvres",
    "80": "Somme",
    "81": "Tarn",
    "82": "Tarn-et-Garonne",
    "83": "Var",
    "84": "Vaucluse",
    "85": "Vendée",
    "86": "Vienne",
    "87": "Haute-Vienne",
    "88": "Vosges",
    "89": "Yonne",
    "90": "Territoire de Belfort",
    "91": "Essonne",
    "92": "Hauts-de-Seine",
    "93": "Seine-Saint-Denis",
    "94": "Val-de-Marne",
    "95": "Val-d'Oise",
    "971": "Guadeloupe",
    "972": "Martinique",
    "973": "Guyane",
    "974": "La Réunion",
}


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
            try:
                return self._get_theater_details_from_page(theater_id)
            except ValueError:
                raise ValueError(f"Theater not found. Is theater id {theater_id!r} correct?") from None

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
            if response.get("error") is True and response.get("message") == "no.showtime.error":
                break
            if response.get("error") is True and response.get("message") == "next.showtime.on":
                next_date = Date.fromisoformat(response["nextDate"])
                if next_date > requested_date:
                    requested_date = next_date
                    continue
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

    def get_geocodes(self, dept: str | int | None = None) -> list[Location]:
        if dept is None:
            selector = Selector(text=self._client.get_locationlist())
            return _parse_departments(selector)

        department = self._find_department(dept)
        if department.dept == "75":
            return [
                Location(
                    geocode=department.geocode,
                    name=department.name,
                    location_type="city",
                    dept=department.dept,
                    zipcode="75000",
                )
            ]
        locations = []
        page = 1
        while True:
            selector = Selector(text=self._client.get_locationlist(department.geocode, page=page))
            locations.extend(_parse_cities(selector, department.dept))
            if not selector.css(".button-right:not(.button-disabled)"):
                return list({location.geocode: location for location in locations}.values())
            page += 1

    def search_theaters(
        self,
        geocode: int | str | None = None,
        dept: str | int | None = None,
        zipcode: str | int | None = None,
    ) -> list[Theater]:
        if sum(value is not None for value in (geocode, dept, zipcode)) != 1:
            raise ValueError("Exactly one of geocode, dept, or zipcode must be provided")

        location_type = "ville"
        if dept is not None:
            department = self._find_department(dept)
            geocode = department.geocode
            if department.dept != "75":
                location_type = "departement"
        elif zipcode is not None:
            normalized_zipcode = str(zipcode).zfill(5)
            response = self._client.get_city_locations(normalized_zipcode)
            raw_cities = response.get("values", {}).get("cities", [])
            location = next(
                (item["node"] for item in raw_cities if item.get("node", {}).get("zip") == normalized_zipcode),
                None,
            )
            if location is None:
                raise ValueError(f"No location found for zipcode {normalized_zipcode!r}")
            geocode = location["id"]

        assert geocode is not None
        theaters = []
        page = 1
        while True:
            selector = Selector(
                text=self._client.get_theaterlist_by_geocode(
                    geocode=geocode,
                    page=page,
                    location_type=location_type,
                )
            )
            theaters.extend(_parse_theaters(selector))
            if not selector.css(".button-right:not(.button-disabled)"):
                return theaters
            page += 1

    def _find_department(self, dept: str | int) -> Location:
        department_code = str(dept).upper().zfill(2)
        department = next((item for item in self.get_geocodes() if item.dept == department_code), None)
        if department is None:
            raise ValueError(f"Department not found: {department_code!r}")
        return department

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
                        if value
                    ]
                    screen_formats.extend(
                        {"DIGITAL": "Numérique", "IMAX": "IMAX", "F_3D": "3D"}.get(value, value)
                        for value in raw_showtime.get("projection") or []
                        if value and (value != "DIGITAL" or not screen_formats)
                    )

                    if synopsis := raw_movie.get("synopsis"):
                        synopsis = re.sub(r"<.*?>", "", synopsis)
                        synopsis = synopsis.replace("\xa0", " ")  # Remove HTML tags (ex: <span>)
                        synopsis = unicodedata.normalize("NFKD", synopsis)

                    movie = MovieVersion(
                        movie_id=raw_movie["internalId"],
                        title=raw_movie.get("title"),
                        img_url=jmespath.search("poster.url", raw_movie),
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


def _normalize_location_name(name: str) -> str:
    name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", " ", name.lower()).strip()


DEPARTMENT_CODES = {_normalize_location_name(name): code for code, name in DEPARTMENT_NAMES.items()}
DEPARTMENT_CODES["reunion"] = "974"
DEPARTMENT_CODES["alpes de haute provence"] = "04"
DEPARTMENT_CODES["cotes d armor"] = "22"
DEPARTMENT_CODES["cote d or"] = "21"
DEPARTMENT_CODES["pyrenees atlantiques"] = "64"
DEPARTMENT_CODES["l eure et loir"] = "28"


def _location_path(selector: Selector) -> str | None:
    if path := selector.attrib.get("href"):
        return path
    for class_name in (selector.attrib.get("class") or "").split():
        if not class_name.startswith("ACr"):
            continue
        try:
            return base64.b64decode(class_name.replace("ACr", "")).decode()
        except (ValueError, UnicodeDecodeError):
            continue
    return None


def _parse_departments(selector: Selector) -> list[Location]:
    departments = []
    for item in selector.css(".mdl-more-item"):
        path = _location_path(item)
        match = re.search(r"/departement-(\d+)/", path or "")
        if not match:
            continue
        name = " ".join((item.xpath("string()").get() or "").split())
        department_code = DEPARTMENT_CODES.get(_normalize_location_name(name))
        if department_code is None:
            continue
        departments.append(
            Location(
                geocode=int(match.group(1)),
                name=name,
                location_type="department",
                dept=department_code,
                zipcode=None,
            )
        )
    if not any(department.dept == "75" for department in departments):
        for item in selector.css(".mdl-more-item"):
            path = _location_path(item)
            name = " ".join((item.xpath("string()").get() or "").split())
            match = re.search(r"/ville-(\d+)/", path or "")
            if match and name == "Paris":
                departments.append(
                    Location(
                        geocode=int(match.group(1)),
                        name=name,
                        location_type="department",
                        dept="75",
                        zipcode=None,
                    )
                )
                break
    return departments


def _parse_cities(selector: Selector, department_code: str) -> list[Location]:
    cities = []
    for group in selector.css(".gd-col-left > .hred"):
        item = group.css(".titlebar-link")[0] if group.css(".titlebar-link") else None
        path = _location_path(item) if item is not None else None
        match = re.search(r"/ville-(\d+)/", path or "")
        if item is None or not match:
            continue
        zipcodes = []
        for raw_address in group.css("address.address").xpath("string()").getall():
            if zipcode_match := re.search(r"\b\d{5}\b", raw_address):
                zipcodes.append(zipcode_match.group())
        cities.append(
            Location(
                geocode=int(match.group(1)),
                name=" ".join((item.xpath("string()").get() or "").split()),
                location_type="city",
                dept=department_code,
                zipcode=Counter(zipcodes).most_common(1)[0][0] if zipcodes else None,
            )
        )
    return cities


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
