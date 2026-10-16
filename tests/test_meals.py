from dataclasses import replace
from datetime import time, timedelta

import synth
from glycolens import meals
from glycolens.series import Series
from glycolens.windows import DEFAULT_WINDOWS


def run(data):
    ms = meals.meals(data, Series(data.glucose), DEFAULT_WINDOWS)
    return {(f.rule, f.window, f.direction) for f in meals.carb_ratio(ms) + meals.pre_bolus(ms)}


def test_clean_has_no_meal_findings():
    assert run(synth.make()) == set()


def test_weak_breakfast_asks_for_a_stronger_breakfast_ratio():
    assert run(synth.make("weak_breakfast")) == {("carb_ratio", "breakfast", "stronger")}


def test_late_prebolus_is_timing_not_ratio():
    assert run(synth.make("late_prebolus")) == {("pre_bolus", "breakfast", "")}


def test_lunch_lows_ask_for_a_weaker_lunch_ratio():
    assert run(synth.make("lunch_lows")) == {("carb_ratio", "lunch", "weaker")}


def test_meal_with_no_reading_near_four_hours_is_skipped():
    data = synth.make("weak_breakfast")
    data.glucose = [g for g in data.glucose if not time(10, 45) <= g.ts.time() <= time(11, 15)]
    assert run(data) == set()


def test_finding_carries_evidence():
    data = synth.make("weak_breakfast")
    ms = meals.meals(data, Series(data.glucose), DEFAULT_WINDOWS)
    (f,) = meals.carb_ratio(ms)
    assert f.events == 14 and f.hits == 14 and f.metric == 3.0 and len(f.evidence) == 14


def test_meals_dosed_by_override_do_not_judge_the_ratio():
    data = synth.make("weak_breakfast")
    data.boluses = [replace(b, overridden=True) for b in data.boluses]
    assert run(data) == set()


def test_only_meals_dosed_with_the_current_ratio_count():
    # After a change from 10 to 9 g/U, meals dosed at 10 say nothing about 9.
    data = synth.make("weak_breakfast")
    late = synth.START + timedelta(days=10)
    data.boluses = [replace(b, carb_ratio=9.0) if b.ts >= late else b for b in data.boluses]
    ms = meals.meals(data, Series(data.glucose), DEFAULT_WINDOWS)
    (f,) = meals.carb_ratio(ms)
    assert f.events == 4


def test_carb_ratio_finding_carries_a_curve_per_meal():
    data = synth.make("weak_breakfast")
    (f,) = meals.carb_ratio(meals.meals(data, Series(data.glucose), DEFAULT_WINDOWS))
    assert len(f.traces) == 14 and all(t["hit"] and t["carbs"] == 45.0 for t in f.traces)
    pts = f.traces[0]["points"]
    assert pts[0] == [0, 6.5] and pts[-1][0] == 240 and len(pts) == 49
