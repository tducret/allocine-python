# -*- coding: utf-8 -*-

"""Top-level package for Allociné."""

from dataclasses import dataclass
from datetime import datetime, timedelta, date
from json import loads
from typing import List, Optional

import jmespath
import requests

__author__ = """Thibault Ducret"""
__email__ = 'hello@tducret.com'
__version__ = '0.0.6'

DEFAULT_DATE_FORMAT = '%Y-%m-%dT%H:%M:%S'
BASE_URL = 'http://api.allocine.fr/rest/v3'
PARTNER_KEY = '000042532791'


# === Models ===
@dataclass
class Movie:
    movie_id: int
    title: str
    rating: Optional[float]
    duration: Optional[timedelta]

    @property
    def duration_str(self):
        if self.duration is not None:
            return _strfdelta(self.duration, '{hours:02d}h{minutes:02d}')
        else:
            return 'HH:MM'

    @property
    def rating_str(self):
        return '{0:.1f}'.format(self.rating) if self.rating else ''

    def __str__(self):
        return f'{self.title} [{self.movie_id}] ({self.duration_str})'


@dataclass
class MovieVersion(Movie):
    language: str
    screen_format: str

    @property
    def version(self):
        version = 'VF' if self.language != 'Français' else 'VOST'
        if self.screen_format != 'Numérique':
            version += f' {self.screen_format}'
        return version

    def __str__(self):
        movie_str = super().__str__()
        return f'{movie_str} ({self.version})'

    def __eq__(self, other):
        return (self.movie_id, self.version) == (other.movie_id, other.version)

    def __hash__(self):
        """ This function allows us
        to do a set(list_of_MovieVersion_objects) """
        return hash((self.movie_id, self.version))


@dataclass
class Showtime:
    date_time: datetime
    movie: MovieVersion

    @property
    def date(self) -> date:
        return self.date_time.date()

    @property
    def hour(self) -> str:
        return str(self.date_time.strftime('%H:%M'))

    def __str__(self):
        return f'{self.date} : {self.movie}'

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
        return f'{self.address}, {self.zipcode} {self.city}'

    def get_showtimes_of_a_movie(self, movie_version: MovieVersion, date: date=None):
        movie_showtimes = [showtime for showtime in self.showtimes
                           if showtime.movie == movie_version]
        if date:
            return [showtime for showtime in movie_showtimes
                    if showtime.date == date]
        else:
            return movie_showtimes

    def get_showtimes_of_a_day(self, date: date):
        return [showtime for showtime in self.showtimes
                if showtime.date == date]

    def get_movies_available_for_a_day(self, date: date):
        """ Returns a list of movies available on a specified day """
        movies = [showtime.movie for showtime in self.get_showtimes_of_a_day(date)]
        return list(set(movies))

# === Main class ===
class Allocine:
    def __init__(self):
        self.__client = Client()

    def get_theater(self, theater_id: str):
        ret = self.__client.get_showtimelist_by_theater_id(theater_id=theater_id)
        if jmespath.search('feed.totalResults', ret) == 0:
            raise ValueError(f'Theater not found. Is theater id {theater_id!r} correct?')
        
        theaters = self.__get_theaters_from_raw_showtimelist(raw_showtimelist=ret)
        if len(theaters) != 1:
            raise ValueError('Expecting 1 theater but received {}'.format(len(theaters)))
 
        return theaters[0]

    def __get_theaters_from_raw_showtimelist(
        self, raw_showtimelist: dict, distance_max_inclusive: int=0):
        theaters = []
        for theater_showtime in jmespath.search('feed.theaterShowtimes', raw_showtimelist):
            raw_theater = jmespath.search('place.theater', theater_showtime)

            if raw_theater.get('distance') is not None:
                  # distance is not present when theater ids were used for search
                if raw_theater.get('distance') > distance_max_inclusive:
                    # Skip theaters that are above the max distance specified
                    continue

            raw_showtimes = jmespath.search('movieShowtimes', theater_showtime)
            showtimes = self.__parse_showtimes(raw_showtimes=raw_showtimes)
            theater = Theater(
                theater_id=raw_theater.get('code'),
                name=raw_theater.get('name'),
                address=raw_theater.get('address'),
                zipcode=raw_theater.get('postalCode'),
                city=raw_theater.get('city'),
                showtimes=showtimes
            )
            theaters.append(theater)
        return theaters

    def search_theaters(self, geocode: int):
        theaters = []
        page = 1
        while True:
            ret = self.__client.get_showtimelist_from_geocode(geocode=geocode, page=page)
            total_results = jmespath.search('feed.totalResults', ret)
            if total_results == 0:
                raise ValueError(f'Theater not found. Is geocode {geocode!r} correct?')

            theaters_to_parse = jmespath.search('feed.theaterShowtimes', ret)
            if theaters_to_parse:
                theaters += self.__get_theaters_from_raw_showtimelist(
                    raw_showtimelist=ret,
                    distance_max_inclusive=0
                )
                page += 1
            else:
                break
        
        return theaters

    def __parse_showtimes(self, raw_showtimes: dict):
        showtimes = []
        for s in raw_showtimes:
            raw_movie = jmespath.search('onShow.movie', s)
            language = jmespath.search('version."$"', s)
            screen_format = jmespath.search('screenFormat."$"', s)
            duration=raw_movie.get('runtime')
            duration_obj = timedelta(seconds=duration) if duration else None
    
            rating = jmespath.search('statistics.userRating', raw_movie)
            try:
                rating = float(rating)
            except:
                rating = None
    
            movie = MovieVersion(
                movie_id=raw_movie.get('code'),
                title=raw_movie.get('title'),
                rating=rating,
                language=language,
                screen_format=screen_format,
                duration=duration_obj)
            for showtimes_of_day in s.get('scr'):
                day = showtimes_of_day.get('d')
                for one_showtime in showtimes_of_day.get('t'):
                    datetime_str = '{}T{}:00'.format(day, one_showtime.get('$'))
                    datetime_obj = _str_datetime_to_datetime_obj(datetime_str)
                    showtime = Showtime(
                        date_time=datetime_obj,
                        movie=movie,
                    )
                    showtimes.append(showtime)
        return showtimes


# === Client to execute requests with Allociné APIs ===
class SingletonMeta(type):
    _instance = None

    def __call__(self):
        if self._instance is None:
            self._instance = super().__call__()
        return self._instance


class Client(metaclass=SingletonMeta):
    """ Client to process the requests with allocine APIs.
    This is a singleton to avoid the creation of a new session for every theater.
    """
    def __init__(self):
        headers = {
                    # 'Host': 'www.allocine.fr',
                    'User-Agent': 'Mozilla/5.0 (Macintosh; \
                                   Intel Mac OS X 10.14; rv:63.0) \
                                   Gecko/20100101 Firefox/63.0',
                    }
        self.session = requests.session()
        self.session.headers.update(headers)

    def _get(self, url: str, expected_status: int=200, *args, **kwargs):
        ret = self.session.get(url, *args, **kwargs)
        if ret.status_code != expected_status:
            raise ValueError('{!r} : expected status {}, received {}'.format(
                url, expected_status, ret.status_code))
        return ret.json()

    def get_showtimelist_by_theater_id(self, theater_id: str, page: int=1, count: int=10):
        url = (
                f'{BASE_URL}/showtimelist?partner={PARTNER_KEY}&format=json'
                f'&theaters={theater_id}&page={page}&count={count}'
        )
        return self._get(url=url)

    def get_theater_info_by_id(self, theater_id: str):
        url = f'{BASE_URL}/theater?partner={PARTNER_KEY}&format=json&code={theater_id}'
        return self._get(url=url)

    def get_showtimelist_from_geocode(self, geocode: int, page: int=1, count: int=10):
        url = (
                f'{BASE_URL}/showtimelist?partner={PARTNER_KEY}&format=json'
                f'&geocode={geocode}&page={page}&count={count}'
        )
        return self._get(url=url)


def _strfdelta(tdelta, fmt):
    """ Format a timedelta object """
    # Thanks to https://stackoverflow.com/questions/8906926
    d = {"days": tdelta.days}
    d["hours"], rem = divmod(tdelta.seconds, 3600)
    d["minutes"], d["seconds"] = divmod(rem, 60)
    return fmt.format(**d)


def _str_datetime_to_datetime_obj(datetime_str, date_format=DEFAULT_DATE_FORMAT):
    return datetime.strptime(datetime_str, date_format)
