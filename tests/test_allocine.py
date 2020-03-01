#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Tests for `allocine` package."""

# To be tested with : python3 -m pytest -vs tests/test_allocine.py

import pytest
from allocine import Allocine


def test_class_Theater():
    allocine = Allocine()
    theater = allocine.get_theater(theater_id='P0645')
    assert len(theater.showtimes) > 0

    date = theater.showtimes[0].date
    movies = theater.get_movies_available_for_a_day(date)
    assert len(movies) > 0


def test_class_Allocine_errors():
    allocine = Allocine()
    with pytest.raises(ValueError):
        allocine.get_theater(theater_id="UNKOWN")
