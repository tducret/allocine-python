"""High-level tests for the Allocine API client."""

from dataclasses import asdict
from datetime import date

import pytest
from freezegun import freeze_time

from allocine import Allocine


@pytest.fixture(scope="session")
def allocine() -> Allocine:
    return Allocine(cache=False)


def test_get_theater(allocine: Allocine, json_snapshot, allocine_vcr):
    theater = allocine.get_theater("P0645")

    assert asdict(theater) == json_snapshot


def test_search_theaters(allocine: Allocine, json_snapshot, allocine_vcr):
    theaters = allocine.search_theaters(geocode=83178)

    assert theaters == json_snapshot


@freeze_time("2026-09-27")
def test_get_showtimes_defaults_to_today(allocine: Allocine, json_snapshot, allocine_vcr):
    showtimes = allocine.get_showtimes("G0FOX")

    assert [asdict(showtime) for showtime in showtimes] == json_snapshot


@freeze_time("2026-09-28")
def test_get_showtimes_clamps_past_from_date_to_today(allocine: Allocine, json_snapshot, allocine_vcr):
    showtimes = allocine.get_showtimes("G0FOX", from_date=date(2026, 9, 26))

    assert [asdict(showtime) for showtime in showtimes] == json_snapshot


@freeze_time("2026-09-27")
def test_get_showtimes_fetches_inclusive_date_range(allocine: Allocine, json_snapshot, allocine_vcr):
    showtimes = allocine.get_showtimes(
        "G0FOX",
        from_date=date(2026, 9, 27),
        to_date=date(2026, 9, 28),
    )

    assert [asdict(showtime) for showtime in showtimes] == json_snapshot


def test_get_showtimes_rejects_inverted_date_range(
    allocine,
):
    with pytest.raises(ValueError, match="from_date must be before or equal to to_date"):
        allocine.get_showtimes(
            "P0645",
            from_date=date(2026, 9, 27),
            to_date=date(2026, 9, 26),
        )


def test_get_showtimes_skips_entries_without_movie(
    allocine,
):
    assert allocine._parse_showtimes([{"movie": None, "showtimes": {}}]) == []


def test_get_theater_falls_back_to_page_metadata(allocine: Allocine, json_snapshot, allocine_vcr):
    theater = allocine.get_theater("G0FOX")

    assert asdict(theater) == json_snapshot
