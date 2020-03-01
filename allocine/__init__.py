# -*- coding: utf-8 -*-

"""Top-level package for Allociné."""

import requests
from datetime import datetime, timedelta
from json import loads

__author__ = """Thibault Ducret"""
__email__ = 'hello@tducret.com'
__version__ = '0.0.4'

_DEFAULT_DATE_FORMAT = '%Y-%m-%dT%H:%M:%S'
_BASE_URL = 'http://api.allocine.fr/rest/v3'
_PARTNER_KEY = '000042532791'


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

    def _get(self, url, expected_status=200, *args, **kwargs):
        ret = self.session.get(url, *args, **kwargs)
        if ret.status_code != expected_status:
            raise ValueError('{!r} : expected status {}, received {}'.format(
                url, expected_status, ret.status_code))
        return ret

    def get_theater_info(self, theater_id):
        url = '{base_url}/theater?partner={partner_key}&format=json&code={theater_id}'.format(
            base_url=_BASE_URL,
            partner_key=_PARTNER_KEY,
            theater_id=theater_id
        )
        ret = self._get(url=url)
        info = ret.json().get('theater')
        if info is None:
            raise ValueError(
                "Theater not found. Is theater id correct : '{}' ?".format(
                    theater_id)
            )
        return info

    def get_showtimes(self, theater_id):
        url = '{base_url}/showtimelist?partner={partner_key}&format=json&theaters={theater_id}'.format(
            base_url=_BASE_URL,
            partner_key=_PARTNER_KEY,
            theater_id=theater_id
        )
        ret = self._get(url=url)
        raw_showtimes = ret.json().get('feed').get('theaterShowtimes')[0].get('movieShowtimes')
        return self.__parse_showtimes(raw_showtimes)

    def __parse_showtimes(self, raw_showtimes):
        showtimes = []
        for s in raw_showtimes:
            raw_movie = s.get('onShow').get('movie')
            raw_version = s.get('version').get('$')
            screen_format = s.get('screenFormat').get('$')
            version = 'VF' if raw_version == 'Français' else 'VOST'
            if screen_format != 'Numérique':
                version += ' {}'.format(screen_format)
            movie_version = MovieVersion(
                id=raw_movie.get('code'),
                title=raw_movie.get('title'),
                rating=raw_movie.get('statistics').get('userRating'),
                version=version,
                duration=raw_movie.get('runtime'))
            for showtimes_of_day in s.get('scr'):
                day = showtimes_of_day.get('d')
                for one_showtime in showtimes_of_day.get('t'):
                    datetime_str = '{}T{}:00'.format(day, one_showtime.get('$'))
                    showtime = Showtime(
                        datetime_str=datetime_str,
                        movie_version=movie_version,
                    )
                    showtimes.append(showtime)
        return showtimes

class Movie:
    def __init__(self, *, id, title, rating, duration):
        self.id = id
        self.title = title
 
        if duration is not None:
            duration_obj = timedelta(seconds=duration)
            self.duration = _strfdelta(duration_obj, "{hours:02d}h{minutes:02d}")
        else:
            self.duration = 'HH:MM'

        if rating is not None:
            f_rating = float(rating)
            if f_rating == 0.0:  # The movie has not been reviewed yet
                self.rating = ''
            else:
                self.rating = "{0:.1f}".format(f_rating)
        else:
            self.rating = ''

    def __str__(self):
        return "{} [{}] ({})".format(self.title, self.id, self.duration)


class MovieVersion(Movie):
    """ A movie + the language and kind of screening (3D, IMAX...) used """
    def __init__(self, *, id, title, rating, duration, version):
        super().__init__(id=id, title=title, rating=rating, duration=duration)
        self.version = version  # VF, VOST, VF 3D...

    def __str__(self):
        return "{} ({})".format(super().__str__(), self.version)

    def __eq__(self, other):
        return (self.title, self.id, self.version)\
         == (other.title, other.id, other.version)

    def __hash__(self):
        """ This function allows us
        to do a set(list_of_MovieVersion_objects) """
        return hash((self.title, self.id, self.version))


class Showtime:
    def __init__(self, datetime_str, movie_version: MovieVersion):
        self.movie_version = movie_version
        datetime_obj = _str_datetime_to_datetime_obj(datetime_str)
        self.hour = str(datetime_obj.strftime("%H:%M"))
        self.datetime = str(datetime_obj.strftime("%d/%m/%Y %H:%M"))
        self.date = str(datetime_obj.strftime("%d/%m/%Y"))

    def __str__(self):
        return "{} {} : {}".format(self.date, self.hour, self.movie_version)


def _strfdelta(tdelta, fmt):
    """ Format a timedelta object """
    # Thanks to https://stackoverflow.com/questions/8906926
    d = {"days": tdelta.days}
    d["hours"], rem = divmod(tdelta.seconds, 3600)
    d["minutes"], d["seconds"] = divmod(rem, 60)
    return fmt.format(**d)


def _str_datetime_to_datetime_obj(datetime_str, date_format=_DEFAULT_DATE_FORMAT):
    return datetime.strptime(datetime_str, date_format)


class Program:
    """ A program is a list of showtimes """
    def __init__(self, theater_id):
        self.__client = Client()
        self.theater_id = theater_id
        self.showtimes = self.__client.get_showtimes(theater_id)

    def get_movies_available_for_a_day(self, date):
        """ Returns a list of movies available on a specified day """
        showtimes = self.get_showtimes(date=date)
        movie_versions = [showtime.movie_version for showtime in showtimes]
        return list(set(movie_versions))

    def get_showtimes(self, date=None, movie_version=None):
        """ Returns a list of showtimes filtered """
        if date is not None:
            showtimes = [showtime for showtime in self.showtimes
                         if showtime.date == date]
        else:
            showtimes = self.showtimes
        if movie_version is not None:
            showtimes = [showtime for showtime in showtimes
                         if showtime.movie_version == movie_version]
        return showtimes

    def __str__(self):
        s = ""
        for showtime in self.showtimes:
            s += "{}\n".format(str(showtime))
        return s


class Theater:
    def __init__(self, theater_id):
        """ ``theater_id`` is the Allociné theater identifier.
        It can be found in the showtimes url
        http://www.allocine.fr/seance/salle_gen_csalle=[theater_id].html
        For example : theater_id="C0159" for UGC Ciné Cité Les Halles"""
        self.__client = Client()
        self.theater_id = theater_id
        self.info = self.__client.get_theater_info(theater_id)
        self.name = self.info.get('name')
        self.program = Program(theater_id)


    def __str__(self):
        return "{} [{}] : {} - {} showtime(s) available".format(
            self.name, self.theater_id, self.address, len(self.program.showtimes))
