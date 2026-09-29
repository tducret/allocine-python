"""Top-level package for Allociné."""

from importlib.metadata import version as _distribution_version

from allocine.api import AllocineApi
from allocine.client import DEFAULT_DATE_FORMAT, Allocine
from allocine.models import (
    Location,
    Movie,
    MovieVersion,
    Schedule,
    Showtime,
    Theater,
    day_str,
    get_french_month,
    get_hour_short_str,
    short_day_str,
    to_french_short_weekday,
    to_french_weekday,
)
from allocine.schedules import (
    build_program_str,
    build_weekly_schedule_str,
    check_schedules_within_week,
    create_weekdays_str,
    get_available_dates,
    get_showtimes_of_a_day,
    group_showtimes_per_schedule,
)

__author__ = "Thibault Ducret"
__email__ = "hello@tducret.com"
__version__ = _distribution_version("allocine")

__all__ = [
    "Allocine",
    "AllocineApi",
    "DEFAULT_DATE_FORMAT",
    "Location",
    "Movie",
    "MovieVersion",
    "Schedule",
    "Showtime",
    "Theater",
    "build_program_str",
    "build_weekly_schedule_str",
    "check_schedules_within_week",
    "create_weekdays_str",
    "day_str",
    "get_available_dates",
    "get_french_month",
    "get_hour_short_str",
    "get_showtimes_of_a_day",
    "group_showtimes_per_schedule",
    "short_day_str",
    "to_french_short_weekday",
    "to_french_weekday",
]
