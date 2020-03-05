# -*- coding: utf-8 -*-

"""Top-level package for Allociné."""

from collections import OrderedDict
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

    def __eq__(self, other):
        return (self.movie_id) == (other.movie_id)

    def __hash__(self):
        """ This function allows us
        to do a set(list_of_Movie_objects) """
        return hash(self.movie_id)

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

    def get_movie(self):
        return Movie(
            movie_id=self.movie_id,
            title=self.title,
            rating=self.rating,
            duration=self.duration
        )

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
class Schedule:
    date_time: datetime

    @property
    def date(self) -> date:
        return self.date_time.date()

    @property
    def hour(self) -> datetime.time:
        return self.date_time.time()

    @property
    def hour_str(self) -> str:
        return self.date_time.strftime('%H:%M')

    @property
    def hour_short_str(self) -> str:
        return get_hour_short_str(self.hour)

    @property
    def date_str(self) -> date:
        return self.date_time.strftime('%d/%m/%Y %H:%M')

    @property
    def day_str(self) -> str:
        return day_str(self.date)

    @property
    def short_day_str(self) -> str:
        return short_day_str(self.date)


def get_hour_short_str(hour: datetime.time) -> str:
    # Ex: 11h, 23h30
    return hour.strftime('%Hh%M').replace('h00', 'h')


@dataclass
class Showtime(Schedule):
    movie: MovieVersion

    def __str__(self):
        return f'{self.date_str} : {self.movie}'


def day_str(date: date) -> str:
    return to_french_weekday(date.weekday())


def to_french_weekday(weekday: int) -> str:
    DAYS = ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi', 'Dimanche']
    return DAYS[weekday]


def to_french_short_weekday(weekday: int) -> str:
    return to_french_weekday(weekday)[:3]


def short_day_str(date: date) -> str:
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
        address_str = f'{self.address}, ' if self.address else ''
        address_str += f'{self.zipcode} {self.city}'
        return address_str

    def get_showtimes_of_a_movie(self, movie_version: MovieVersion, date: date=None):
        movie_showtimes = [showtime for showtime in self.showtimes
                           if showtime.movie == movie_version]
        if date:
            return [showtime for showtime in movie_showtimes
                    if showtime.date == date]
        else:
            return movie_showtimes

    def get_showtimes_of_a_day(self, date: date):
        return get_showtimes_of_a_day(showtimes=self.showtimes, date=date)

    def get_movies_available_for_a_day(self, date: date):
        """ Returns a list of movies available on a specified day """
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
    
    def filter_showtimes(self, date_min: date = None, date_max: date = None):
        if date_min:
            self.showtimes = [s for s in self.showtimes if s.date >= date_min]
        if date_max:
            self.showtimes = [s for s in self.showtimes if s.date <= date_max]


# == Utils ==
def get_available_dates(showtimes: List[Showtime]):
    dates = [s.date for s in showtimes]
    return sorted(list(set(dates)))


def group_showtimes_per_schedule(showtimes: List[Showtime]):
    showtimes_per_date = {}
    available_dates = get_available_dates(showtimes=showtimes)
    for date in available_dates:
        showtimes_per_date[date] = get_showtimes_of_a_day(showtimes=showtimes, date=date)

    grouped_showtimes = {}
    for date in available_dates:
        hours = [s.hour_short_str for s in showtimes_per_date[date]]
        hours_str = ', '.join(hours)
        if grouped_showtimes.get(hours_str) is None:
            grouped_showtimes[hours_str] = []
        grouped_showtimes[hours_str].append(date)
    return grouped_showtimes


def build_program_str(showtimes: List[Showtime]):
    schedules = [Schedule(s.date_time) for s in showtimes]
    return build_weekly_schedule_str(schedules)

def check_schedules_within_week(schedule_list: List[Schedule]) -> bool:
    schedule_dates = [s.date for s in schedule_list]
    min_date = min(schedule_dates)
    max_date = max(schedule_dates)
    delta = (max_date - min_date)
    if delta >= timedelta(days=7):
        raise ValueError(
            'Schedule list contains more days than the typical movie week')
    # Check that the week is not from Mon/Tue to Wed/Thu/Fri/Sat/Sun
    # because a typical week is from Wed to Tue
    # but we need to handle the case of a schedule_list with only a few day
    # ex: Wed, Mon = OK ; Tue = OK ; Mon, Wed : NOK
    MONDAY = 0
    TUESDAY = 1
    WEDNESDAY = 2
    if delta > timedelta(days=0):
        if (min_date.weekday() == MONDAY and max_date.weekday() >= WEDNESDAY) \
           or (min_date.weekday() == TUESDAY):
            raise ValueError(
                'Schedule list should not start before wednesday or end after tuesday')
    
    return True

def create_weekdays_str(dates: List[datetime.date]) -> str:
    """ Returns a compact string from a list of dates.
        Examples:
            - [0,1] -> 'Lun, Mar'
            - [0,1,2,3,4] -> 'sf Sam, Dim'
            - [0,1,2,3,4,5,6] -> ''  # Everyday is empty string
            - [0,2] -> 'Mer, Lun'  # And not 'Lun, Mer' because we sort chrologically
    """
    FULL_WEEK = range(0,7)
    unique_dates = sorted(list(set(dates)))
    week_days = [d.weekday() for d in unique_dates]

    if len(unique_dates) == 7:
        return ''
    elif len(unique_dates) <= 4:
        return ', '.join([to_french_short_weekday(d) for d in week_days])
    else:
        missing_days = list(set(week_days).symmetric_difference(FULL_WEEK))
        return 'sf {}'.format(', '.join([to_french_short_weekday(d) for d in missing_days]))


def __earliest_time(d):
        earliest = min(d[1])
        return earliest


def build_weekly_schedule_str(schedule_list: List[Schedule]) -> str:
    check_schedules_within_week(schedule_list)
 
    _hours_hashmap = {}  # ex: {16h: [Lun, Mar], 17h: [Lun], 17h30: [Lun]}
    _grouped_date_hashmap = {}  # ex: {[Lun]: [16h, 17h30], [Lun, Mar]: [17h]}

    for s in schedule_list:
        
        if _hours_hashmap.get(s.hour) is None:
            _hours_hashmap[s.hour] = []
        _hours_hashmap[s.hour].append(s.date)

    for hour, grouped_dates in _hours_hashmap.items():
        grouped_dates_str = create_weekdays_str(grouped_dates)
        if _grouped_date_hashmap.get(grouped_dates_str) is None:
            _grouped_date_hashmap[grouped_dates_str] = []
        _grouped_date_hashmap[grouped_dates_str].append(hour)

    # Then sort it chronologically
    for grouped_dates_str, hours in _grouped_date_hashmap.items():
        # Sort the hours inside
        hours = list(set(hours))
        hours.sort()
        _grouped_date_hashmap[grouped_dates_str] = hours

    _grouped_date_hashmap = sorted(_grouped_date_hashmap.items(), key=__earliest_time)
    grouped_date_hashmap = OrderedDict(_grouped_date_hashmap)

    different_showtimes = len(grouped_date_hashmap)
 
    weekly_schedule = ''
    for grouped_dates, hours in grouped_date_hashmap.items():
        hours_str = ', '.join([get_hour_short_str(h) for h in hours])
        if not grouped_dates:  # Here, it is available everyday at this hour
            weekly_schedule += f'{hours_str}, '
        else:
            if different_showtimes == 1:
                weekly_schedule += f'{grouped_dates} {hours_str}, '
            else:
                if len(hours) > 1:
                    weekly_schedule += f'{grouped_dates} {hours_str}; '
                else:
                    weekly_schedule += f'{hours_str} ({grouped_dates}), '

    if weekly_schedule:
        weekly_schedule = weekly_schedule[:-2]  # Remove trailing comma
    return weekly_schedule


def get_showtimes_of_a_day(showtimes: List[Showtime], *, date: date):
        return [showtime for showtime in showtimes
                if showtime.date == date]


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
            for showtimes_of_day in s.get('scr') or []:
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
