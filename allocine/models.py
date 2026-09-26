import logging
import unicodedata
from dataclasses import dataclass
from datetime import date as Date
from datetime import datetime, timedelta
from datetime import time as Time
from typing import List, Optional

from allocine import nationalities

logger = logging.getLogger(__name__)


@dataclass
class Movie:
    movie_id: int
    title: str
    original_title: str
    rating: Optional[float]
    duration: Optional[timedelta]
    genres: str
    countries: List[str]
    directors: str
    actors: str
    synopsis: str
    year: int

    @property
    def duration_str(self):
        if self.duration is not None:
            return _strfdelta(self.duration, "{hours:02d}h{minutes:02d}")
        else:
            return "HH:MM"

    @property
    def duration_short_str(self) -> str:
        if self.duration is not None:
            return _strfdelta(self.duration, "{hours:d}h{minutes:02d}")
        else:
            return "NA"

    @property
    def rating_str(self):
        return "{0:.1f}".format(self.rating) if self.rating else ""

    @property
    def nationalities(self):
        """Return the nationality tuples, from the movie countries.
        Example: if self.countries = ['France'] => [('français', 'française')]
        """
        if self.countries:
            nationality_tuples = []
            for country_name in self.countries:
                normalized_country_name = _strip_accents(country_name).lower()
                country_code = nationalities.countries.get(normalized_country_name)

                if country_code is not None:
                    nationality_tuples.append(nationalities.nationalities[country_code])
                else:
                    logger.warning(f"Country {country_name!r} not found in nationalities")
                    nationality_tuples.append((f"de {country_name}", f"de {country_name}"))
            return nationality_tuples
        else:
            return None

    def __str__(self):
        return f"{self.title} [{self.movie_id}] ({self.duration_str})"

    def __eq__(self, other):
        return (self.movie_id) == (other.movie_id)

    def __hash__(self):
        """This function allows us
        to do a set(list_of_Movie_objects)"""
        return hash(self.movie_id)


@dataclass
class MovieVersion(Movie):
    language: str
    screen_format: str

    @property
    def version(self):
        version = "VF" if self.language == "Français" else "VOST"
        if self.screen_format != "Numérique":
            version += f" {self.screen_format}"
        return version

    def get_movie(self):
        return Movie(
            movie_id=self.movie_id,
            title=self.title,
            rating=self.rating,
            duration=self.duration,
            original_title=self.original_title,
            year=self.year,
            genres=self.genres,
            countries=self.countries,
            directors=self.directors,
            actors=self.actors,
            synopsis=self.synopsis,
        )

    def __str__(self):
        movie_str = super().__str__()
        return f"{movie_str} ({self.version})"

    def __eq__(self, other):
        return (self.movie_id, self.version) == (other.movie_id, other.version)

    def __hash__(self):
        """This function allows us
        to do a set(list_of_MovieVersion_objects)"""
        return hash((self.movie_id, self.version))


@dataclass
class Schedule:
    date_time: datetime

    @property
    def date(self) -> Date:
        return self.date_time.date()

    @property
    def hour(self) -> Time:
        return self.date_time.time()

    @property
    def hour_str(self) -> str:
        return self.date_time.strftime("%H:%M")

    @property
    def hour_short_str(self) -> str:
        return get_hour_short_str(self.hour)

    @property
    def date_str(self) -> str:
        return self.date_time.strftime("%d/%m/%Y %H:%M")

    @property
    def day_str(self) -> str:
        return day_str(self.date)

    @property
    def short_day_str(self) -> str:
        return short_day_str(self.date)


def get_hour_short_str(hour: Time) -> str:
    # Ex: 9h, 11h, 23h30
    # Minus in '%-H' removes the leading 0
    return hour.strftime("%-Hh%M").replace("h00", "h")


@dataclass
class Showtime(Schedule):
    movie: MovieVersion

    def __str__(self):
        return f"{self.date_str} : {self.movie}"


def day_str(date: Date) -> str:
    return to_french_weekday(date.weekday())


def to_french_weekday(weekday: int) -> str:
    days = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]
    return days[weekday]


def get_french_month(month_number: int) -> str:
    months = [
        "Janvier",
        "Février",
        "Mars",
        "Avril",
        "Mai",
        "Juin",
        "Juillet",
        "Août",
        "Septembre",
        "Octobre",
        "Novembre",
        "Décembre",
    ]
    return months[month_number - 1]


def to_french_short_weekday(weekday: int) -> str:
    return to_french_weekday(weekday)[:3]


def short_day_str(date: Date) -> str:
    return day_str(date)[:3]


@dataclass
class Theater:
    theater_id: str
    name: str
    showtimes: List[Showtime]
    address: str
    zipcode: str
    city: str

    @property
    def address_str(self):
        address_str = f"{self.address}, " if self.address else ""
        address_str += f"{self.zipcode} {self.city}"
        return address_str

    def get_showtimes_of_a_movie(self, movie_version: MovieVersion, date: Optional[Date] = None):
        movie_showtimes = [showtime for showtime in self.showtimes if showtime.movie == movie_version]
        if date:
            return [showtime for showtime in movie_showtimes if showtime.date == date]
        else:
            return movie_showtimes

    def get_showtimes_of_a_day(self, date: Date):
        from allocine.schedules import get_showtimes_of_a_day

        return get_showtimes_of_a_day(showtimes=self.showtimes, date=date)

    def get_movies_available_for_a_day(self, date: Date):
        """Returns a list of movies available on a specified day"""
        movies = [showtime.movie for showtime in self.get_showtimes_of_a_day(date)]
        return list(set(movies))

    def get_showtimes_per_movie_version(self):
        movies = {}
        for showtime in self.showtimes:
            if movies.get(showtime.movie) is None:
                movies[showtime.movie] = []
            movies[showtime.movie].append(showtime)
        return movies

    def get_showtimes_per_movie(self):
        movies = {}
        for showtime in self.showtimes:
            movie = showtime.movie.get_movie()  # Without language nor screen_format
            if movies.get(movie) is None:
                movies[movie] = []
            movies[movie].append(showtime)
        return movies

    def get_program_per_movie(self):
        from allocine.schedules import build_program_str

        program_per_movie = {}
        for movie, showtimes in self.get_showtimes_per_movie().items():
            program_per_movie[movie] = build_program_str(showtimes=showtimes)
        return program_per_movie

    def filter_showtimes(self, date_min: Optional[Date] = None, date_max: Optional[Date] = None):
        if date_min:
            self.showtimes = [s for s in self.showtimes if s.date >= date_min]
        if date_max:
            self.showtimes = [s for s in self.showtimes if s.date <= date_max]

    def __eq__(self, other):
        return (self.theater_id) == (other.theater_id)

    def __hash__(self):
        """This function allows us to do a set(list_of_Theaters_objects)"""
        return hash(self.theater_id)


def _strfdelta(tdelta, fmt):
    """Format a timedelta object"""
    # Thanks to https://stackoverflow.com/questions/8906926
    d = {"days": tdelta.days}
    d["hours"], rem = divmod(tdelta.seconds, 3600)
    d["minutes"], d["seconds"] = divmod(rem, 60)
    return fmt.format(**d)


def _strip_accents(s):
    # https://stackoverflow.com/a/518232/8748757
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")
