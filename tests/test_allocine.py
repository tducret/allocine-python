"""High-level tests for the Allocine API client."""

from dataclasses import asdict

from allocine import Allocine


def test_get_theater(json_snapshot, allocine_vcr):
    theater = Allocine().get_theater("P0645")

    assert asdict(theater) == json_snapshot


def test_search_theaters(json_snapshot, allocine_vcr):
    theaters = Allocine().search_theaters(geocode=83178)

    assert theaters == json_snapshot
