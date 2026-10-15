import synth
from glycolens import behaviour
from glycolens.series import Series
from glycolens.windows import DEFAULT_WINDOWS


def test_missed_boluses_found_late_evening():
    d = synth.make("missed_bolus")
    (f,) = behaviour.missed_bolus(d, Series(d.glucose), DEFAULT_WINDOWS)
    assert (f.rule, f.window, f.hits) == ("missed_bolus", "late", 3)


def test_exercise_lows_found():
    d = synth.make("exercise_lows")
    (f,) = behaviour.exercise_low(d, Series(d.glucose))
    assert (f.events, f.hits, f.metric) == (7, 7, 3.4)


def test_site_day_three_highs_found():
    d = synth.make("site_day3")
    (f,) = behaviour.site_age(d, Series(d.glucose))
    assert f.metric >= 1.5
