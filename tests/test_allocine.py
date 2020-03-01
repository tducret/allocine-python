#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Tests for `allocine` package."""

# To be tested with : python3 -m pytest -vs tests/test_allocine.py

import pytest
from allocine import Theater


def test_class_Theater():
    theater = Theater(theater_id="P0645")
    assert len(theater.program.showtimes) > 0

    date = theater.program.showtimes[0].date
    movies = theater.program.get_movies_available_for_a_day(date)
    assert len(movies) > 0


def test_class_Allocine_errors():
    with pytest.raises(ValueError):
        Theater(theater_id="UNKOWN")
