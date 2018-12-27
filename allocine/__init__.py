# -*- coding: utf-8 -*-

"""Top-level package for Allociné."""

import requests
from datetime import datetime
from bs4 import BeautifulSoup
from json import loads

__author__ = """Thibault Ducret"""
__email__ = 'hello@tducret.com'
__version__ = '0.0.1'

_DEFAULT_DATE_FORMAT = '%Y-%m-%dT%H:%M:%S.%f%z'
_DEFAULT_BEAUTIFULSOUP_PARSER = "html.parser"


class Allocine:
    def __init__(self, theater_id):
        """ theater_id is the Allociné theater identifier.
        It can be found in the showtimes url
        http://www.allocine.fr/seance/salle_gen_csalle=[theater_id].html
        For example : theater_id="C0159" for UGC Ciné Cité Les Halles"""
        self.theater_id = theater_id
        self.allocine_dict = self._get_showtimes_dict()
        self.movies = self._get_movies()
        self.theater = self._get_theater_info()
        showtimes = self._get_showtimes()
        self.theater.program.add_showtimes(showtimes)

    def _get_showtimes_dict(self):
        """ Get the `data-movies-showtimes` dict from Allociné webpage.
        It contains all the information about the theater, the movies and
        the showtimes.
        Returns a dict."""
        session = requests.session()
        headers = {
                    'Host': 'www.allocine.fr',
                    'User-Agent': 'Mozilla/5.0 (Macintosh; \
                                   Intel Mac OS X 10.14; rv:63.0) \
                                   Gecko/20100101 Firefox/63.0',
                    }
        url = "http://www.allocine.fr/seance/salle_gen_csalle={}.html".format(
            self.theater_id)
        ret = session.get(url=url, headers=headers)
        html_page = ret.text
        soup = BeautifulSoup(html_page, _DEFAULT_BEAUTIFULSOUP_PARSER)
        section = soup.select("section.js-movie-list")
        if len(section) == 0:
            raise ValueError(
                "Showtimes not found. Is theater id correct : '{}' ?".format(
                    self.theater_id))
        return loads(section[0].get("data-movies-showtimes"))

    def _get_movies(self):
        """ From the Allociné dict, returns a list of Movie objects"""
        movies = self.allocine_dict['movies']
        movie_list = []
        for movie_id, movie_details in movies.items():
            title = movie_details.get('title')
            rating = movie_details.get('social').get('user_review_rating')
            movie_list.append(Movie(id=movie_id, title=title, rating=rating))
        return movie_list

    def _get_theater_info(self):
        """ From the Allociné dict, returns a Theater object"""
        theaters = self.allocine_dict.get('theaters')
        t = theaters.get(self.theater_id)
        return Theater(id=self.theater_id, name=t.get('name'),
                       address=t.get('address').get('city'))

    def _get_movie_obj_from_id(self, movie_id):
        """ Returns a Movie object from its id """
        found_movie = None
        for movie in self.movies:
            if movie.id == movie_id:
                found_movie = movie
                break
        return found_movie

    def _get_showtimes(self):
        """ From the Allociné dict, returns a list of Showtime objects
        """
        showtimes = []
        showtimes_per_day = self.allocine_dict.get(
            'showtimes').get(self.theater_id)
        for date, movies in showtimes_per_day.items():
            for movie_id, movie_versions in movies.items():
                # movie_version is a kind of display for the movie
                # (language, 3D/2D...)
                movie_obj = self._get_movie_obj_from_id(movie_id=movie_id)

                for movie_version in movie_versions:

                    if movie_version.get("version") == "translated":
                        version = "VF"
                    else:
                        version = "VOST"

                    format = movie_version.get("format").get("name")
                    if format != "Numérique":
                        version += " {}".format(format)

                    if movie_version.get("fourdx") == True:
                        version += ", Salle 4DX"

                    movie_version_obj = MovieVersion(title=movie_obj.title,
                                                     id=movie_obj.id,
                                                     rating=movie_obj.rating,
                                                     version=version)

                    for showtime in movie_version.get('showtimes'):

                        showtime_obj = Showtime(
                            datetime_str=showtime.get("movieStart"),
                            movie_version=movie_version_obj,
                            end_datetime_str=showtime.get("movieEnd"))

                        showtimes.append(showtime_obj)
        return showtimes


class Movie:
    def __init__(self, id, title, rating):
        self.id = id
        self.title = title
        self.rating = rating

        if self.rating is not None:
            f_rating = float(self.rating)
            if f_rating == 0.0:  # The movie has not been reviewed yet
                self.rating = None
            else:
                self.rating = "{0:.1f}".format(f_rating)

    def __str__(self):
        return "{} [{}]".format(self.title, self.id)


class MovieVersion(Movie):
    def __init__(self, id, title, rating, version):
        super().__init__(id, title, rating)
        self.version = version  # VF, VOST, VF 3D...

    def set_duration(self, duration):
        self.duration = duration

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
    def __init__(self, datetime_str, movie_version, end_datetime_str=None):
        self.datetime_str = datetime_str
        self.movie_version = movie_version
        self.end_datetime_str = end_datetime_str
        datetime_obj = self._str_datetime_to_datetime_obj(
            datetime_str=self.datetime_str)
        if self.end_datetime_str is not None:
            end_datetime_obj = self._str_datetime_to_datetime_obj(
                datetime_str=self.end_datetime_str)
            duration_obj = end_datetime_obj - datetime_obj
            self.duration = self._strfdelta(duration_obj,
                                            "{hours:02d}h{minutes:02d}")
            self.movie_version.set_duration(self.duration)
        else:
            self.duration = "HH:MM"
            self.movie_version.set_duration(self.duration)

        self.hour = str(datetime_obj.strftime("%H:%M"))
        self.datetime = str(datetime_obj.strftime("%d/%m/%Y %H:%M"))
        self.date = str(datetime_obj.strftime("%d/%m/%Y"))

    def __str__(self):
        return "{} {} : {} ({})".format(self.date, self.hour,
                                        self.movie_version,
                                        self.duration)

    @staticmethod
    def _str_datetime_to_datetime_obj(datetime_str,
                                      date_format=_DEFAULT_DATE_FORMAT):
        return datetime.strptime(datetime_str, date_format)

    @staticmethod
    def _strfdelta(tdelta, fmt):
        """ Format a timedelta object """
        # Thanks to https://stackoverflow.com/questions/8906926
        d = {"days": tdelta.days}
        d["hours"], rem = divmod(tdelta.seconds, 3600)
        d["minutes"], d["seconds"] = divmod(rem, 60)
        return fmt.format(**d)


class Program:
    """ A program is a list of showtimes """
    def __init__(self, showtimes=[]):
        self.showtimes = showtimes

    def add_showtime(self, showtime):
        self.showtimes.append(showtime)

    def add_showtimes(self, showtimes):
        self.showtimes.extend(showtimes)

    def get_movies_available_for_a_day(self, date):
        """ Returns a list of movies available on a specified day """
        showtimes = self.get_showtimes(date=date)
        movie_versions = [showtime.movie_version for showtime in showtimes]
        return list(set(movie_versions))

    def get_movie_duration(self, movie_version):
        showtimes = self.get_showtimes(movie_version=movie_version)
        return showtimes[0].duration

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


class Theater:
    def __init__(self, id, name, address):
        self.id = id
        self.name = name
        self.address = address
        self.program = Program(showtimes=[])

    def __str__(self):
        return "{} [{}] : {} - {} showtime(s) available".format(
            self.name, self.id, self.address, len(self.program.showtimes))
