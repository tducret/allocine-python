"""High-level tests for the Allocine API client."""

from dataclasses import asdict
from datetime import date

from allocine import Allocine


def test_get_theater(json_snapshot, allocine_vcr):
    theater = Allocine().get_theater("P0645", date=date(2026, 9, 26))

    assert asdict(theater) == json_snapshot
