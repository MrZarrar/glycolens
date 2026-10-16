from dataclasses import replace
from datetime import timedelta

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


def test_overridden_zero_carb_boluses_are_not_scored_as_corrections():
    # The owner often boluses food with 0 carbs via Override Increase; the rise after it is food.
    data = synth.make("strong_isf")
    data.boluses = [replace(b, overridden=True) if b.kind == "correction" else b for b in data.boluses]
    assert run(data) == []


def test_a_rise_after_a_correction_is_not_evidence_about_isf():
    # Glucose going up after insulin means food, the site or illness, not a weak correction factor.
    data = synth.make()
    data.boluses = [replace(b, isf=0.5) if b.kind == "correction" else b for b in data.boluses]
    rising = {b.ts for b in data.boluses if b.kind == "correction"}
    data.glucose = [replace(g, mmol=g.mmol + 3.0) if any(t < g.ts <= t + timedelta(hours=5) for t in rising) else g
                    for g in data.glucose]
    assert run(data) == []


def test_corrections_that_fall_short_ask_for_a_stronger_isf():
    (f,) = run(synth.make("weak_isf"))
    assert (f.rule, f.window, f.direction) == ("isf", "dinner", "stronger")


def test_isf_finding_carries_each_correction_curve():
    (f,) = run(synth.make("strong_isf"))
    assert len(f.traces) == 7 and all(t["expected_drop"] == 2.0 and t["units"] == 1.0 for t in f.traces)
    assert f.traces[0]["points"][-1][0] == 300
