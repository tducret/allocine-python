#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Tests for `allocine` package."""

# To be tested with : python3 -m pytest -vs tests/test_allocine.py

import pytest
from allocine import Movie, Theater, Showtime


def test_class_Movie():
    movie = Movie(title="Titanic", id=12345)
    assert movie.title == "Titanic"
    assert movie.id == 12345


def test_class_Movie_by_dict():
    movie = Movie(**{'title': 'Titanic', 'id': 12345})
    assert movie.title == "Titanic"
    assert movie.id == 12345


def test_class_Movie_errors():
    with pytest.raises(TypeError):
        Movie(title="Titanic")  # Missing id
    with pytest.raises(TypeError):
        Movie(id=12345)  # Missing title


def test_class_Theater():
    theater = Theater(name="Cinema", id=7890)
    assert theater.name == "Cinema"
    assert theater.id == 7890


def test_class_Theater_by_dict():
    theater = Theater(**{'name': 'Cinema', 'id': 7890})
    assert theater.name == "Cinema"
    assert theater.id == 7890


def test_class_Theater_errors():
    with pytest.raises(TypeError):
        Theater(name="Cinema")  # Missing id
    with pytest.raises(TypeError):
        Theater(id=12345)  # Missing name


def test_class_Showtime():
    showtime = Showtime(datetime_str="2018-12-15T17:15:00.000Z")
    assert showtime.datetime_str == "2018-12-15T17:15:00.000Z"
    assert showtime.hour == "17:15"


def test_class_Showtime_errors():
    with pytest.raises(ValueError):
        Showtime(datetime_str="This is not a date")
