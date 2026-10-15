from datetime import datetime, timedelta

import pytest

from glycolens.model import Glucose
from glycolens.series import Series
from glycolens.stats import agp, summary, window_summary
from glycolens.windows import DEFAULT_WINDOWS, Window, parse_windows, window_of

T = datetime(2026, 1, 5, 7, 0)


def test_summary_numbers():
    s = summary([3.0, 5.0, 11.0, 15.0], minutes=20)
    assert s == {"coverage": 1.0, "mean": 8.5, "tir": 25.0, "tbr": 25.0, "tbr_severe": 0.0,
                 "tar": 50.0, "tar_severe": 25.0, "gmi": 7.0, "cv": 56.1, "min": 3.0}


def test_summary_of_nothing_has_zero_coverage():
    s = summary([], minutes=60)
    assert s["coverage"] == 0.0 and s["mean"] is None


def test_series_at_finds_nearest_within_tolerance():
    s = Series([Glucose(T, 6.0), Glucose(T + timedelta(minutes=5), 7.0)])
    assert s.at(T + timedelta(minutes=4)) == 7.0
    assert s.at(T + timedelta(minutes=30)) is None


def test_series_tolerates_duplicate_timestamps():
    s = Series([Glucose(T, 6.0), Glucose(T, 6.1)])
    assert s.at(T) in (6.0, 6.1)


def test_window_of_and_contains():
    assert window_of(T, DEFAULT_WINDOWS).name == "breakfast"
    assert window_of(T.replace(hour=23, minute=59), DEFAULT_WINDOWS).name == "late"


def test_parse_windows_rejects_gaps():
    with pytest.raises(ValueError):
        parse_windows([{"name": "a", "start": "00:00", "end": "06:00"},
                       {"name": "b", "start": "07:00", "end": "24:00"}])
    assert parse_windows([{"name": "all", "start": "00:00", "end": "24:00"}]) == (Window("all", 0, 1440),)


def test_window_summary_and_agp_on_a_flat_day():
    day = [Glucose(T.replace(hour=0) + timedelta(minutes=5 * i), 6.5) for i in range(288)]
    s = Series(day)
    start = T.replace(hour=0)
    breakfast = next(w for w in DEFAULT_WINDOWS if w.name == "breakfast")
    ws = window_summary(s, breakfast, start, start + timedelta(days=1))
    assert ws["coverage"] == 1.0 and ws["tir"] == 100.0
    rows = agp(s)
    assert len(rows) == 24 and rows[7]["p50"] == 6.5
