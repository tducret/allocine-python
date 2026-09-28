"""High-level tests for the Allocine API client."""

from dataclasses import asdict
from datetime import date

import pytest
from freezegun import freeze_time

from allocine import Allocine


def test_get_theater(json_snapshot, allocine_vcr):
    theater = Allocine().get_theater("P0645")

    assert asdict(theater) == json_snapshot


def test_search_theaters(json_snapshot, allocine_vcr):
    theaters = Allocine().search_theaters(geocode=83178)

    assert theaters == json_snapshot


@freeze_time("2026-09-27")
def test_get_showtimes_defaults_to_today(json_snapshot, allocine_vcr):
    showtimes = Allocine().get_showtimes("G0FOX")

    assert [asdict(showtime) for showtime in showtimes] == json_snapshot


def test_get_showtimes_fetches_inclusive_date_range(json_snapshot, allocine_vcr):
    showtimes = Allocine().get_showtimes(
        "G0FOX",
        from_date=date(2026, 9, 27),
        to_date=date(2026, 9, 28),
    )

    assert [asdict(showtime) for showtime in showtimes] == json_snapshot


def test_get_showtimes_rejects_inverted_date_range():
    with pytest.raises(ValueError, match="from_date must be before or equal to to_date"):
        Allocine().get_showtimes(
            "P0645",
            from_date=date(2026, 9, 27),
            to_date=date(2026, 9, 26),
        )


def test_get_showtimes_skips_entries_without_movie():
    assert Allocine()._parse_showtimes([{"movie": None, "showtimes": {}}]) == []


def test_get_theater_falls_back_to_page_metadata(json_snapshot, allocine_vcr):
    theater = Allocine().get_theater("G0FOX")

    assert asdict(theater) == json_snapshot
