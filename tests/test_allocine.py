#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Tests for `allocine` package."""

# To be tested with : python3 -m pytest -vs tests/test_allocine.py

import pytest
from allocine import Movie, Theater, Showtime, MovieVersion, Allocine


def test_class_Movie():
    movie = Movie(title="Titanic", id=12345, rating=4.50209)
    assert movie.title == "Titanic"
    assert movie.id == 12345
    assert movie.rating == '4.5'
    print()
    print(movie)


def test_class_Movie_by_dict():
    movie = Movie(**{'title': 'Titanic', 'id': 12345, 'rating': 4.50209})
    assert movie.title == "Titanic"
    assert movie.id == 12345
    assert movie.rating == '4.5'
    print()
    print(movie)


def test_Movie_rating():
    movie = Movie(title="Titanic", id=12345, rating=0)
    assert movie.rating is None
    movie = Movie(title="Titanic", id=12345, rating=1)
    assert movie.rating == '1.0'
    movie = Movie(title="Titanic", id=12345, rating='1.20')
    assert movie.rating == '1.2'


def test_class_Movie_errors():
    with pytest.raises(TypeError):
        Movie(title="Titanic")  # Missing id
    with pytest.raises(TypeError):
        Movie(id=12345)  # Missing title


def test_class_MovieVersion():
    movie_version = MovieVersion(title="Titanic", id=12345,
                                 version="VOST", rating=4.50209)
    assert movie_version.title == "Titanic"
    assert movie_version.id == 12345
    assert movie_version.version == "VOST"
    print()
    print(movie_version)


def test_class_Theater():
    theater = Theater(name="Cinema", id="A7890", address="2 rue lilas, Albi")
    assert theater.name == "Cinema"
    assert theater.id == "A7890"
    assert theater.address == "2 rue lilas, Albi"
    print()
    print(theater)


def test_class_Theater_by_dict():
    theater = Theater(**{'name': 'Cinema', 'id': 'A7890',
                         'address': '2 rue lilas, Albi'})
    assert theater.name == "Cinema"
    assert theater.id == "A7890"
    assert theater.address == "2 rue lilas, Albi"
    print()
    print(theater)


def test_Theater_add_showtime():
    theater = Theater(name="Cinema", id="A7890", address="2 rue lilas, Albi")
    movie_version = MovieVersion(title="Titanic", id=12345,
                                 version="VOST", rating=4.50209)
    showtime = Showtime(datetime_str="2018-12-15T17:15:00.000Z",
                        movie_version=movie_version)
    showtime2 = Showtime(datetime_str="2018-12-15T20:15:00.000Z",
                         movie_version=movie_version)
    assert len(theater.program.showtimes) == 0
    theater.program.add_showtime(showtime=showtime)
    assert len(theater.program.showtimes) == 1
    theater.program.add_showtimes(showtimes=[showtime, showtime2])
    assert len(theater.program.showtimes) == 3
    print()
    print(theater)


def test_class_Theater_errors():
    with pytest.raises(TypeError):
        Theater(name="Cinema")  # Missing id
    with pytest.raises(TypeError):
        Theater(id=12345)  # Missing name


def test_class_Showtime():
    movie_version = MovieVersion(title="Titanic", id=12345,
                                 version="VOST", rating=4.50209)
    showtime = Showtime(datetime_str="2018-12-15T17:15:00.000Z",
                        end_datetime_str="2018-12-15T19:15:00.000Z",
                        movie_version=movie_version)
    assert showtime.datetime_str == "2018-12-15T17:15:00.000Z"
    assert showtime.hour == "17:15"
    assert showtime.datetime == "15/12/2018 17:15"
    assert showtime.date == "15/12/2018"
    assert showtime.duration == "02h00"
    assert showtime.movie_version.title == "Titanic"
    assert showtime.movie_version.id == 12345
    assert showtime.movie_version.version == "VOST"
    assert showtime.movie_version.duration == "02h00"
    print()
    print(showtime)


def test_class_Showtime_errors():
    with pytest.raises(ValueError):
        movie_version = MovieVersion(title="Titanic", id=12345,
                                     version="VOST", rating=4.50209)
        Showtime(datetime_str="This is not a date",
                 movie_version=movie_version)


def test_class_Allocine():
    a = Allocine(theater_id="P2235")
    print()
    for showtime in a.theater.program.showtimes:
        print(showtime)


def test_class_Allocine_errors():
    with pytest.raises(ValueError):
        Allocine(theater_id="UNKOWN")


def init_theater_object():
    theater = Theater(name="Cinema", id="A7890", address="2 rue lilas, Albi")
    movie_version = MovieVersion(title="Titanic", id=12345,
                                 version="VOST", rating=4.50209)
    showtime = Showtime(datetime_str="2018-12-15T17:15:00.000Z",
                        movie_version=movie_version)
    movie_version2 = MovieVersion(title="Titanic", id=12345, version="VF",
                                  rating=4.50209)
    showtime2 = Showtime(datetime_str="2018-12-15T20:15:00.000Z",
                         movie_version=movie_version2)
    movie_version3 = MovieVersion(title="Avatar", id=6789, version="VF",
                                  rating=4.6356)
    showtime3 = Showtime(datetime_str="2018-12-15T10:30:00.000Z",
                         movie_version=movie_version3)
    showtime4 = Showtime(datetime_str="2018-12-16T10:30:00.000Z",
                         movie_version=movie_version3)
    theater.program.add_showtimes(showtimes=[showtime, showtime2,
                                             showtime3, showtime4])
    return theater


def test_get_showtimes_for_a_day():
    theater = init_theater_object()
    assert len(theater.program.showtimes) == 4

    showtimes_for_a_day = theater.program.get_showtimes(date="15/12/2018")
    assert len(showtimes_for_a_day) == 3
    print()
    for showtime in showtimes_for_a_day:
        print(showtime)


def test_get_movies_available_for_a_day():
    theater = init_theater_object()
    movie_versions = theater.program.get_movies_available_for_a_day(
        date="15/12/2018")
    assert len(movie_versions) == 3
    print()
    for movie_version in movie_versions:
        print(movie_version)


def test_get_showtimes_for_a_specific_movie():
    theater = init_theater_object()
    movie_version = MovieVersion(title="Avatar", id=6789, version="VF",
                                 rating=4.6356)
    showtimes_for_a_movie = theater.program.get_showtimes(
        movie_version=movie_version)
    assert len(showtimes_for_a_movie) == 2
    print()
    for showtime in showtimes_for_a_movie:
        print(showtime)


def test_get_showtimes_for_a_specific_movie_and_day():
    theater = init_theater_object()
    movie_version = MovieVersion(title="Avatar", id=6789, version="VF",
                                 rating=4.6356)
    showtimes_for_a_movie = theater.program.get_showtimes(
        movie_version=movie_version, date="15/12/2018")
    assert len(showtimes_for_a_movie) == 1
    print()
    for showtime in showtimes_for_a_movie:
        print(showtime)
