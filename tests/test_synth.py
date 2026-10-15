from datetime import timedelta

import synth
from glycolens.series import Series
from glycolens.stats import summary


def test_clean_fixture_is_complete_and_in_range():
    d = synth.make()
    assert len(d.glucose) == synth.DAYS * 288
    s = summary([g.mmol for g in d.glucose], synth.DAYS * 1440)
    assert s["coverage"] == 1.0 and s["tbr"] == 0.0


def test_weak_breakfast_ends_three_above_start():
    d = synth.make("weak_breakfast")
    s = Series(d.glucose)
    t = synth.START.replace(hour=7)
    assert round(s.at(t + timedelta(hours=4)) - s.at(t), 1) == 3.0


def test_every_fault_builds():
    for fault in synth.FAULTS:
        assert synth.make(fault).glucose
