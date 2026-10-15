import synth
from glycolens.corrections import isf
from glycolens.model import Bolus
from glycolens.series import Series
from glycolens.windows import DEFAULT_WINDOWS


def run(data):
    return isf(data, Series(data.glucose), DEFAULT_WINDOWS)


def test_clean_corrections_match_isf():
    assert run(synth.make()) == []


def test_overshooting_corrections_ask_for_a_weaker_isf():
    (f,) = run(synth.make("strong_isf"))
    assert (f.rule, f.window, f.direction, f.events) == ("isf", "dinner", "weaker", 7)
    assert f.metric == 1.6


def test_auto_boluses_are_never_scored_as_corrections():
    data = synth.make("strong_isf")
    data.boluses = [Bolus(b.ts, b.units, b.carbs_g, "auto", b.carb_ratio, b.isf) if b.kind == "correction" else b
                    for b in data.boluses]
    assert run(data) == []
