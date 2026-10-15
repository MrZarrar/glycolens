from datetime import datetime

import synth
from glycolens.basal import basal, delivered_ratio
from glycolens.model import Basal
from glycolens.series import Series
from glycolens.windows import DEFAULT_WINDOWS


def run(data):
    return basal(data, Series(data.glucose), DEFAULT_WINDOWS)


def test_clean_basal_is_quiet():
    assert run(synth.make()) == []


def test_control_iq_pushing_overnight_asks_for_more_basal():
    (f,) = run(synth.make("night_basal_low"))
    assert (f.rule, f.window, f.direction, f.events, f.hits) == ("basal", "overnight", "stronger", 14, 14)
    assert f.metric == 1.4


def test_delivered_ratio_is_time_weighted():
    a = datetime(2026, 1, 5, 0, 0)
    records = [Basal(a.replace(hour=0), 1.0, 2.0), Basal(a.replace(hour=1), 1.0, 1.0)]
    assert delivered_ratio(records, a, a.replace(hour=4)) == 1.25


def test_exercise_nights_are_not_fasting():
    assert run(synth.make("exercise_lows")) == []


def test_glucose_drift_alone_is_not_a_basal_finding():
    # A rise with basal delivered as programmed could be late digestion, exercise or illness.
    data = synth.make("night_basal_low")
    data.basal = [Basal(b.ts, b.programmed, b.programmed) for b in data.basal]
    assert run(data) == []
