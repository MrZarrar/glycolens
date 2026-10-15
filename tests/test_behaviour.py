import synth
from glycolens import behaviour
from glycolens.series import Series
from glycolens.windows import DEFAULT_WINDOWS


def test_exercise_lows_found():
    d = synth.make("exercise_lows")
    (f,) = behaviour.exercise_low(d, Series(d.glucose))
    assert (f.events, f.hits, f.metric) == (7, 7, 3.4)
