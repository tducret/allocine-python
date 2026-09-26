from collections import OrderedDict
from datetime import date as Date
from datetime import time as Time
from datetime import timedelta
from typing import List, Tuple

from allocine.models import Schedule, Showtime, get_hour_short_str, to_french_short_weekday


def get_available_dates(showtimes: List[Showtime]):
    dates = [s.date for s in showtimes]
    return sorted(list(set(dates)))


def group_showtimes_per_schedule(showtimes: List[Showtime]):
    showtimes_per_date = {}
    available_dates = get_available_dates(showtimes=showtimes)
    for available_date in available_dates:
        showtimes_per_date[available_date] = get_showtimes_of_a_day(showtimes=showtimes, date=available_date)

    grouped_showtimes = {}
    for available_date in available_dates:
        hours = [s.hour_short_str for s in showtimes_per_date[available_date]]
        hours_str = ", ".join(hours)
        if grouped_showtimes.get(hours_str) is None:
            grouped_showtimes[hours_str] = []
        grouped_showtimes[hours_str].append(available_date)
    return grouped_showtimes


def build_program_str(showtimes: List[Showtime]):
    schedules = [Schedule(s.date_time) for s in showtimes]
    return build_weekly_schedule_str(schedules)


def check_schedules_within_week(schedule_list: List[Schedule]) -> bool:
    schedule_dates = [s.date for s in schedule_list]
    min_date = min(schedule_dates)
    max_date = max(schedule_dates)
    delta = max_date - min_date
    if delta >= timedelta(days=7):
        raise ValueError("Schedule list contains more days than the typical movie week")
    # Check that the week is not from Mon/Tue to Wed/Thu/Fri/Sat/Sun
    # because a typical week is from Wed to Tue
    # but we need to handle the case of a schedule_list with only a few day
    # ex: Wed, Mon = OK ; Tue = OK ; Mon, Wed : NOK
    monday = 0
    tuesday = 1
    wednesday = 2
    if delta > timedelta(days=0):
        if (min_date.weekday() == monday and max_date.weekday() >= wednesday) or (min_date.weekday() == tuesday):
            raise ValueError("Schedule list should not start before wednesday or end after tuesday")

    return True


def create_weekdays_str(dates: List[Date]) -> str:
    """
    Returns a compact string from a list of dates.
    Examples:
        - [0,1] -> 'Lun, Mar'
        - [0,1,2,3,4] -> 'sf Sam, Dim'
        - [0,1,2,3,4,5,6] -> ''  # Everyday is empty string
        - [0,2] -> 'Mer, Lun'  # And not 'Lun, Mer' because we sort chrologically
    """
    full_week = range(0, 7)
    unique_dates = sorted(list(set(dates)))
    week_days = [d.weekday() for d in unique_dates]

    if len(unique_dates) == 7:
        return ""
    elif len(unique_dates) <= 4:
        return ", ".join([to_french_short_weekday(d) for d in week_days])
    else:
        missing_days = list(set(week_days).symmetric_difference(full_week))
        return "sf {}".format(", ".join([to_french_short_weekday(d) for d in missing_days]))


def __get_time_weight_in_list(item: Tuple[str, List[Time]]) -> timedelta:
    """Returns the minimum time weight from the time list contained in the dict values
    ex: {'key': [time(hour=12), time(hour=9)]} => timedelta(hour=9)
    """
    weights = [__get_time_weight(t) for t in item[1]]
    return min(weights)


def __get_time_weight(t: Time) -> timedelta:
    """Return a timedelta taking into account night time.
    Basically, it allows to sort a list of times 18h>23h>0h30
    and not 0h30>18h>23h
    """
    night_time = [Time(hour=0), Time(hour=5)]
    delta = timedelta(hours=t.hour, minutes=t.minute)
    if t >= min(night_time) and t <= max(night_time):
        delta += timedelta(days=1)
    return delta


def build_weekly_schedule_str(schedule_list: List[Schedule]) -> str:
    check_schedules_within_week(schedule_list)

    hours_hashmap_raw = {}  # ex: {16h: [Lun, Mar], 17h: [Lun], 17h30: [Lun]}
    grouped_date_hashmap_raw = {}  # ex: {[Lun]: [16h, 17h30], [Lun, Mar]: [17h]}

    for schedule in schedule_list:
        if hours_hashmap_raw.get(schedule.hour) is None:
            hours_hashmap_raw[schedule.hour] = []
        hours_hashmap_raw[schedule.hour].append(schedule.date)

    for hour, grouped_dates in hours_hashmap_raw.items():
        grouped_dates_str = create_weekdays_str(grouped_dates)
        if grouped_date_hashmap_raw.get(grouped_dates_str) is None:
            grouped_date_hashmap_raw[grouped_dates_str] = []
        grouped_date_hashmap_raw[grouped_dates_str].append(hour)

    # Then sort it chronologically
    for grouped_dates_str, hours in grouped_date_hashmap_raw.items():
        # Sort the hours inside
        hours = list(set(hours))
        hours.sort()
        grouped_date_hashmap_raw[grouped_dates_str] = hours

    grouped_date_hashmap_raw = sorted(grouped_date_hashmap_raw.items(), key=__get_time_weight_in_list)
    grouped_date_hashmap = OrderedDict(grouped_date_hashmap_raw)

    hours_hashmap = OrderedDict()
    for hour in sorted(hours_hashmap_raw.keys(), key=__get_time_weight):
        hours_hashmap[hour] = hours_hashmap_raw.get(hour)

    different_showtimes = len(grouped_date_hashmap)

    # True if at least one schedule is available everyday
    some_schedules_available_everyday = grouped_date_hashmap.get("") is not None

    weekly_schedule = ""

    if some_schedules_available_everyday:
        for hour, grouped_dates in hours_hashmap.items():
            hour_str = get_hour_short_str(hour)
            grouped_dates_str = create_weekdays_str(grouped_dates)
            if grouped_dates_str:
                weekly_schedule += f"{hour_str} ({grouped_dates_str}), "
            else:  # Available everyday
                weekly_schedule += f"{hour_str}, "
    else:
        for grouped_dates, hours in grouped_date_hashmap.items():
            hours_str = ", ".join([get_hour_short_str(h) for h in hours])
            if different_showtimes == 1:
                weekly_schedule += f"{grouped_dates} {hours_str}, "
            else:
                if some_schedules_available_everyday:
                    weekly_schedule += f"{hours_str} ({grouped_dates}), "
                else:
                    weekly_schedule += f"{grouped_dates} {hours_str}; "

    if weekly_schedule:
        weekly_schedule = weekly_schedule[:-2]  # Remove trailing comma
    return weekly_schedule


def get_showtimes_of_a_day(showtimes: List[Showtime], *, date: Date):
    return [showtime for showtime in showtimes if showtime.date == date]
