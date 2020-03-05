#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Tests for the Programoscope."""

# To be tested with : python3 -m pytest -vs tests/test_programoscope.py

from datetime import datetime, date

import pytest
from allocine import (
    Allocine,
    build_weekly_schedule_str,
    check_schedules_within_week,
    create_weekdays_str,
    MovieVersion,
    Schedule,
    Showtime,
)


def test_check_schedules_within_typical_week():
    schedules = [
        Schedule(
            date_time=datetime(year=2020, month=3, day=4, hour=14, minute=0),
        ),
        Schedule(
            date_time=datetime(year=2020, month=3, day=10, hour=14, minute=0),
        )
    ]
    assert check_schedules_within_week(schedules)


def test_check_schedules_within_too_long_week():
    schedules = [
        Schedule(
            date_time=datetime(year=2020, month=3, day=4, hour=14, minute=0),
        ),
        Schedule(  # one day after typical week
            date_time=datetime(year=2020, month=3, day=11, hour=14, minute=0),
        )
    ]
    with pytest.raises(ValueError):
        check_schedules_within_week(schedules)


def test_check_schedules_not_typical_week():
    schedules = [
        Schedule(  # Tuesday
            date_time=datetime(year=2020, month=3, day=3, hour=14, minute=0),
        ),
        Schedule(  # Monday the week after
            date_time=datetime(year=2020, month=3, day=9, hour=14, minute=0),
        )
    ]
    with pytest.raises(ValueError):
        check_schedules_within_week(schedules)


def test_check_schedules_single_day():
    schedules = [
        Schedule(  # Monday
            date_time=datetime(year=2020, month=3, day=2, hour=14, minute=0),
        ),
    ]
    assert check_schedules_within_week(schedules)


def test_check_schedules_not_typical_week2():
    schedules = [
        Schedule(  # Monday
            date_time=datetime(year=2020, month=3, day=2, hour=14, minute=0),
        ),
        Schedule(  # Wednesday
            date_time=datetime(year=2020, month=3, day=4, hour=14, minute=0),
        )
    ]
    with pytest.raises(ValueError):
        check_schedules_within_week(schedules)


def test_check_schedules_not_typical_week3():
    schedules = [
        Schedule(  # Tuesday
            date_time=datetime(year=2020, month=3, day=3, hour=14, minute=0),
        ),
        Schedule(  # Wednesday
            date_time=datetime(year=2020, month=3, day=4, hour=14, minute=0),
        )
    ]
    with pytest.raises(ValueError):
        check_schedules_within_week(schedules)


def test_one_day():
    schedules = [
        Schedule(date_time=datetime(year=2020, month=3, day=4, hour=14, minute=0)),
    ]
    schedule_str = build_weekly_schedule_str(schedules)
    assert schedule_str == 'Mer 14h'


def test_two_days_with_same_hour():
    schedules = [
        Schedule(date_time=datetime(year=2020, month=3, day=4, hour=14, minute=0)),
        Schedule(date_time=datetime(year=2020, month=3, day=5, hour=14, minute=0)),
    ]
    schedule_str = build_weekly_schedule_str(schedules)
    assert schedule_str == 'Mer, Jeu 14h'


def test_two_days_with_same_hour_unsorted():
    schedules = [
        Schedule(date_time=datetime(year=2020, month=3, day=5, hour=14, minute=0)),
        Schedule(date_time=datetime(year=2020, month=3, day=4, hour=14, minute=0)),
    ]
    schedule_str = build_weekly_schedule_str(schedules)
    assert schedule_str == 'Mer, Jeu 14h'


def test_one_day_with_two_showtimes():
    schedules = [
        Schedule(date_time=datetime(year=2020, month=3, day=4, hour=10, minute=15)),
        Schedule(date_time=datetime(year=2020, month=3, day=4, hour=14, minute=0)),
    ]
    schedule_str = build_weekly_schedule_str(schedules)
    assert schedule_str == 'Mer 10h15, 14h'


def test_one_day_with_two_showtimes_unsorted():
    schedules = [
        Schedule(date_time=datetime(year=2020, month=3, day=4, hour=14, minute=0)),
        Schedule(date_time=datetime(year=2020, month=3, day=4, hour=10, minute=15)),
    ]
    schedule_str = build_weekly_schedule_str(schedules)
    assert schedule_str == 'Mer 10h15, 14h'


def test_same_day_two_showtimes():
    schedules = []
    schedules += [Schedule(date_time=datetime(year=2020, month=3, day=day, hour=14, minute=0))
         for day in range(5, 11)]
    schedules += [Schedule(date_time=datetime(year=2020, month=3, day=day, hour=16, minute=0))
         for day in range(5, 11)]
    schedule_str = build_weekly_schedule_str(schedules)
    assert schedule_str == 'sf Mer 14h, 16h'


def test_real_case_1():
    schedules = []
    schedules += [Schedule(date_time=datetime(year=2020, month=3, day=day, hour=14, minute=10))
         for day in range(4, 11)]
    schedules += [Schedule(date_time=datetime(year=2020, month=3, day=day, hour=17, minute=0))
         for day in range(4, 11)]
    schedules += [Schedule(date_time=datetime(year=2020, month=3, day=day, hour=20, minute=30))
         for day in (4, 5, 8, 9, 10)]
    schedules += [Schedule(date_time=datetime(year=2020, month=3, day=day, hour=21, minute=0))
         for day in (6, 7)]
    schedule_str = build_weekly_schedule_str(schedules)
    assert schedule_str == '14h10, 17h, 20h30 (sf Ven, Sam), 21h (Ven, Sam)'


def test_real_case_2():
    schedules = []
    schedules += [Schedule(date_time=datetime(year=2020, month=3, day=day, hour=13, minute=50))
         for day in range(4, 11)]
    schedules += [Schedule(date_time=datetime(year=2020, month=3, day=8, hour=10, minute=40))]
    schedule_str = build_weekly_schedule_str(schedules)
    assert schedule_str == '10h40 (Dim), 13h50'


def test_real_case_3():
    schedules = []
    schedules += [Schedule(date_time=datetime(year=2020, month=3, day=day, hour=18, minute=15))
         for day in (4, 7)]
    schedules += [Schedule(date_time=datetime(year=2020, month=3, day=day, hour=21, minute=0))
         for day in (6, 9, 10)]
    schedule_str = build_weekly_schedule_str(schedules)
    assert schedule_str == 'Mer, Sam 18h15; Ven, Lun, Mar 21h'


def test_real_case_4():
    schedules = []
    schedules += [Schedule(date_time=datetime(year=2020, month=3, day=day, hour=11, minute=15))
         for day in range(4, 11)]
    schedules += [Schedule(date_time=datetime(year=2020, month=3, day=day, hour=20, minute=0))
         for day in range(4, 10)]
    schedules += [Schedule(date_time=datetime(year=2020, month=3, day=day, hour=22, minute=0))
         for day in range(4, 11)]
    schedule_str = build_weekly_schedule_str(schedules)
    assert schedule_str == '11h15, 20h (sf Mar), 22h'


def test_real_case_5():
    schedules = []
    schedules += [Schedule(date_time=datetime(year=2020, month=3, day=day, hour=22, minute=00))
                  for day in range(4, 11)]
    schedules += [Schedule(date_time=datetime(year=2020, month=3, day=7, hour=0, minute=30))]
    schedule_str = build_weekly_schedule_str(schedules)
    assert schedule_str == '22h, 0h30 (Sam)'


def test_real_case_6():
    schedules = []
    schedules += [Schedule(date_time=datetime(year=2020, month=3, day=day, hour=9, minute=30))
                  for day in range(4, 11)]
    schedule_str = build_weekly_schedule_str(schedules)
    assert schedule_str == '9h30'


def test_create_weekdays_str():
    dates = [date(year=2020, month=3, day=4)]
    assert create_weekdays_str(dates) == 'Mer'

    dates.append(date(year=2020, month=3, day=5))
    assert create_weekdays_str(dates) == 'Mer, Jeu'

    dates.append(date(year=2020, month=3, day=7))
    assert create_weekdays_str(dates) == 'Mer, Jeu, Sam'

    dates.append(date(year=2020, month=3, day=9))
    assert create_weekdays_str(dates) == 'Mer, Jeu, Sam, Lun'

    dates.append(date(year=2020, month=3, day=10))
    assert create_weekdays_str(dates) == 'sf Ven, Dim'

    dates.append(date(year=2020, month=3, day=6))
    assert create_weekdays_str(dates) == 'sf Dim'

    dates.append(date(year=2020, month=3, day=8))
    assert create_weekdays_str(dates) == ''
