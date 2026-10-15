from datetime import datetime, timedelta

from glycolens.model import Glucose
from glycolens.sensor import sensor_lows

T = datetime(2026, 10, 13, 20, 0)


def steady(until_min, mmol=5.9):
    return [Glucose(T + timedelta(minutes=m), mmol) for m in range(0, until_min + 1, 5)]


def test_plunge_out_of_a_gap_before_a_dead_sensor_is_removed():
    # 5.9 every 5 min to 21:15, three readings missing, LOW at 21:36, then nothing until a new sensor.
    low = Glucose(T + timedelta(minutes=96), 2.2)
    new_sensor = Glucose(T + timedelta(hours=23), 6.0)
    kept, suspect = sensor_lows(steady(75) + [low, new_sensor])
    assert low not in kept and new_sensor in kept and suspect == []


def test_plunge_the_sensor_recovers_from_is_kept_and_flagged():
    low = Glucose(T + timedelta(minutes=96), 2.2)
    after = [Glucose(T + timedelta(minutes=m), 5.5) for m in (101, 106)]
    kept, suspect = sensor_lows(steady(75) + [low] + after)
    assert low in kept and suspect == [low.ts]


def test_a_continuous_real_fall_is_never_touched_even_if_the_sensor_then_dies():
    fall = [Glucose(T + timedelta(minutes=80 + 5 * i), v) for i, v in enumerate((4.4, 3.9, 3.5, 3.0, 2.5, 2.2))]
    data = steady(75, 5.0) + fall + [Glucose(T + timedelta(hours=23), 6.0)]
    kept, suspect = sensor_lows(data)
    assert kept == data and suspect == []


def test_a_sudden_drop_without_missing_readings_is_not_flagged():
    data = steady(75) + [Glucose(T + timedelta(minutes=80), 3.5), Glucose(T + timedelta(minutes=85), 3.6)]
    assert sensor_lows(data) == (data, [])
