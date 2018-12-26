# -*- coding: utf-8 -*-

"""Top-level package for Allociné."""

import requests
from dataclasses import dataclass, field
from typing import List
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
        self.theater.add_showtimes(showtimes)

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
            movie_list.append(Movie(id=movie_id, title=title))
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

                    movie_version_obj = MovieVersion(title=movie_obj.title,
                                                     id=movie_obj.id,
                                                     version=version)

                    for showtime in movie_version.get('showtimes'):

                        showtime_obj = Showtime(
                            datetime_str=showtime.get("movieStart"),
                            movie_version=movie_version_obj)

                        showtimes.append(showtime_obj)
        return showtimes


@dataclass
class Movie:
    id: int
    title: str

    def __str__(self):
        return "{} [{}]".format(self.title, self.id)


@dataclass
class MovieVersion(Movie):
    version: str  # VF, VOST

    def __str__(self):
        return "{} ({})".format(super().__str__(), self.version)

    def __hash__(self):
        """ This function allows us
        to do a set(list_of_MovieVersion_objects) """
        return hash((self.title, self.id, self.version))


@dataclass
class Showtime:
    datetime_str: str
    # hour: str (see __post_init__)
    # date: str (see __post_init__)
    # datetime: str (see __post_init__)
    movie_version: MovieVersion

    def __post_init__(self):
        self.datetime_obj = self._str_datetime_to_datetime_obj(
            datetime_str=self.datetime_str)
        self.hour = str(self.datetime_obj.strftime("%H:%M"))
        self.datetime = str(self.datetime_obj.strftime("%d/%m/%Y %H:%M"))
        self.date = str(self.datetime_obj.strftime("%d/%m/%Y"))

    def __str__(self):
        return "{} {} : {}".format(self.date, self.hour, self.movie_version)

    @staticmethod
    def _str_datetime_to_datetime_obj(datetime_str,
                                      date_format=_DEFAULT_DATE_FORMAT):
        return datetime.strptime(datetime_str, date_format)


@dataclass
class Theater:
    id: int
    name: str
    address: str
    showtimes: List[Showtime] = field(default_factory=list)

    def add_showtime(self, showtime):
        self.showtimes.append(showtime)

    def add_showtimes(self, showtimes):
        self.showtimes.extend(showtimes)

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
        return "{} [{}] : {} - {} showtime(s) available".format(
            self.name, self.id, self.address, len(self.showtimes))

