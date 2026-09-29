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


def test_get_theater_without_current_showtimes(allocine: Allocine, json_snapshot, allocine_vcr):
    theater = allocine.get_theater("W1021")

    assert asdict(theater) == json_snapshot


def test_search_theaters(allocine: Allocine, json_snapshot, allocine_vcr):
    theaters = allocine.search_theaters(geocode=83178)

    assert theaters == json_snapshot


def test_get_geocodes_lists_departments(allocine: Allocine, json_snapshot, allocine_vcr):
    locations = allocine.get_geocodes()

    assert [asdict(location) for location in locations] == json_snapshot


def test_get_geocodes_lists_department_cities(allocine: Allocine, json_snapshot, allocine_vcr):
    locations = allocine.get_geocodes(dept=29)

    assert [asdict(location) for location in locations] == json_snapshot


def test_search_theaters_by_department(allocine: Allocine, json_snapshot, allocine_vcr):
    theaters = allocine.search_theaters(dept=53)

    assert [asdict(theater) for theater in theaters] == json_snapshot


def test_search_theaters_by_zipcode(allocine: Allocine, json_snapshot, allocine_vcr):
    theaters = allocine.search_theaters(zipcode=29200)

    assert [asdict(theater) for theater in theaters] == json_snapshot


@pytest.mark.parametrize("kwargs", [{}, {"geocode": 95171, "dept": 29}])
def test_search_theaters_requires_one_location_filter(allocine: Allocine, kwargs):
    with pytest.raises(ValueError, match="Exactly one"):
        allocine.search_theaters(**kwargs)


def test_search_theaters_rejects_unknown_zipcode(allocine: Allocine, allocine_vcr):
    with pytest.raises(ValueError, match="No location found for zipcode '99999'"):
        allocine.search_theaters(zipcode=99999)


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


@freeze_time("2026-09-28")
def test_get_showtimes_treats_not_found_as_empty_without_retry(allocine: Allocine, allocine_vcr):
    assert allocine.get_showtimes("C0125", from_date=date(2026, 9, 29)) == []


@freeze_time("2026-09-29")
def test_get_showtimes_stops_after_no_showtime_error(allocine: Allocine, json_snapshot, allocine_vcr):
    showtimes = allocine.get_showtimes("W0746", to_date=date(2026, 10, 5))

    assert [asdict(showtime) for showtime in showtimes] == json_snapshot


@freeze_time("2026-09-26")
def test_get_showtimes_skips_to_next_showtime_date(allocine: Allocine, json_snapshot, allocine_vcr):
    showtimes = allocine.get_showtimes("W1021", to_date=date(2026, 10, 2))

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


@freeze_time("2026-09-29")
def test_get_showtimes_ignores_null_screen_formats(allocine, json_snapshot, allocine_vcr):
    showtimes = allocine.get_showtimes(
        "P0535",
        from_date=date(2026, 9, 30),
        to_date=date(2026, 9, 30),
    )

    assert [asdict(showtime) for showtime in showtimes] == json_snapshot


def test_get_theater_falls_back_to_page_metadata(allocine: Allocine, json_snapshot, allocine_vcr):
    theater = allocine.get_theater("G0FOX")

    assert asdict(theater) == json_snapshot
