#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Tests for `allocine` package."""

# To be tested with : python3 -m pytest -vs tests/test_allocine.py

import pytest
from allocine import Movie, Theater, Showtime, MovieVersion, Allocine


def test_class_Movie():
    movie = Movie(title="Titanic", id=12345)
    assert movie.title == "Titanic"
    assert movie.id == 12345
    print()
    print(movie)


def test_class_Movie_by_dict():
    movie = Movie(**{'title': 'Titanic', 'id': 12345})
    assert movie.title == "Titanic"
    assert movie.id == 12345
    print()
    print(movie)


def test_class_Movie_errors():
    with pytest.raises(TypeError):
        Movie(title="Titanic")  # Missing id
    with pytest.raises(TypeError):
        Movie(id=12345)  # Missing title


def test_class_MovieVersion():
    movieversion = MovieVersion(title="Titanic", id=12345, version="VOST")
    assert movieversion.title == "Titanic"
    assert movieversion.id == 12345
    assert movieversion.version == "VOST"
    print()
    print(movieversion)


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


def test_class_Theater_errors():
    with pytest.raises(TypeError):
        Theater(name="Cinema")  # Missing id
    with pytest.raises(TypeError):
        Theater(id=12345)  # Missing name


def test_class_Showtime():
    movieversion = MovieVersion(title="Titanic", id=12345, version="VOST")
    showtime = Showtime(datetime_str="2018-12-15T17:15:00.000Z",
                        movie=movieversion)
    assert showtime.datetime_str == "2018-12-15T17:15:00.000Z"
    assert showtime.hour == "17:15"
    assert showtime.datetime == "15/12/2018 17:15"
    assert showtime.date == "15/12/2018"
    assert showtime.movie.title == "Titanic"
    assert showtime.movie.id == 12345
    assert showtime.movie.version == "VOST"
    print()
    print(showtime)


def test_class_Showtime_errors():
    with pytest.raises(ValueError):
        movieversion = MovieVersion(title="Titanic", id=12345, version="VOST")
        Showtime(datetime_str="This is not a date", movie=movieversion)


def test_class_Allocine():
    a = Allocine(theater_id="P0645")
    # print(a.movies)
    # print(a.theater)
    print()
    for showtime in a.showtimes:
        print(showtime)
