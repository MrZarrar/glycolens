from datetime import timedelta

import pytest

import synth
from glycolens.analyse import analyse
from glycolens.findings import Finding
from glycolens.series import Series
from glycolens.stats import summary, window_summary
from glycolens.suggest import current_settings, decide, step
from glycolens.windows import DEFAULT_WINDOWS

END = synth.START + timedelta(days=synth.DAYS)


def inputs(fault):
    d = synth.make(fault)
    s = Series(d.glucose)
    ws = {w.name: window_summary(s, w, synth.START, END) for w in DEFAULT_WINDOWS}
    return analyse(d, DEFAULT_WINDOWS), ws, current_settings(d, DEFAULT_WINDOWS)


def f(rule, window, direction, events=10):
    return Finding(rule, window, direction, events, events, 0.0, ("e",))


def test_weak_breakfast_suggests_ten_percent_stronger_ratio():
    findings, ws, cur = inputs("weak_breakfast")
    (s,), watching = decide(findings, ws, cur, set(), "2026-W03")
    assert (s.id, s.setting, s.current, s.proposed) == ("2026-W03-breakfast-carb_ratio", "carb_ratio", 10.0, 9.0)
    assert watching == []


def test_lunch_lows_suggest_weaker_ratio():
    findings, ws, cur = inputs("lunch_lows")
    (s,), _ = decide(findings, ws, cur, set(), "w")
    assert (s.window, s.direction, s.proposed) == ("lunch", "weaker", 11.0)


@pytest.mark.parametrize("lows", [{"tbr": 6.0}, {"min": 2.8}])
def test_lows_win_blocks_a_stronger_change(lows):
    _, ws, cur = inputs(None)
    ws["lunch"] = {**ws["lunch"], **lows}
    sugg, watching = decide([f("carb_ratio", "lunch", "stronger")], ws, cur, set(), "w")
    assert sugg == [] and watching[0].reason == "lows in this window"


def test_too_few_events_only_watches():
    _, ws, cur = inputs(None)
    sugg, watching = decide([f("carb_ratio", "breakfast", "stronger", events=3)], ws, cur, set(), "w")
    assert sugg == [] and "only 3" in watching[0].reason


def test_low_coverage_only_watches():
    _, ws, cur = inputs(None)
    ws["breakfast"] = {**ws["breakfast"], "coverage": 0.5}
    sugg, watching = decide([f("carb_ratio", "breakfast", "stronger")], ws, cur, set(), "w")
    assert sugg == [] and watching[0].reason == "insufficient CGM data"


def test_window_under_measurement_gets_nothing_new():
    _, ws, cur = inputs(None)
    sugg, watching = decide([f("carb_ratio", "breakfast", "stronger")], ws, cur, {"breakfast"}, "w")
    assert sugg == [] and watching[0].reason == "measuring an applied change"


def test_one_change_per_window_and_weaker_goes_first():
    _, ws, cur = inputs(None)
    sugg, watching = decide([f("isf", "dinner", "stronger"), f("carb_ratio", "dinner", "weaker")], ws, cur, set(), "w")
    assert [(s.setting, s.direction) for s in sugg] == [("carb_ratio", "weaker")]
    assert watching[0].reason == "one change per window per week"


def test_unknown_current_setting_only_watches():
    _, ws, _ = inputs(None)
    sugg, watching = decide([f("carb_ratio", "breakfast", "stronger")], ws, {}, set(), "w")
    assert sugg == [] and watching[0].reason == "current setting unknown"


def test_behaviour_findings_never_become_suggestions():
    findings, ws, cur = inputs("late_prebolus")
    assert decide(findings, ws, cur, set(), "w") == ([], [])


@pytest.mark.parametrize("setting,direction,current,expected", [
    ("carb_ratio", "stronger", 10.0, 9.0), ("carb_ratio", "weaker", 10.0, 11.0),
    ("isf", "stronger", 2.0, 1.8), ("isf", "weaker", 2.0, 2.2),
    ("basal", "stronger", 0.8, 0.88), ("basal", "weaker", 0.8, 0.72),
])
def test_step_is_at_most_ten_percent_in_the_right_direction(setting, direction, current, expected):
    assert step(setting, direction, current) == expected


@pytest.mark.parametrize("window,next_window", [("overnight", "breakfast"), ("late", "overnight")])
def test_lows_in_the_next_window_block_a_stronger_change(window, next_window):
    # Insulin keeps acting for up to 5 h, so more basal late in a window lands in the next one.
    _, ws, cur = inputs(None)
    ws[next_window] = {**ws[next_window], "tbr": 6.0}
    sugg, watching = decide([f("basal", window, "stronger")], ws, cur, set(), "w")
    assert sugg == [] and watching[0].reason == "lows in the next window"


def test_a_next_window_without_cgm_data_blocks_a_stronger_change():
    _, ws, cur = inputs(None)
    ws["breakfast"] = summary([], 60)
    sugg, watching = decide([f("basal", "overnight", "stronger")], ws, cur, set(), "w")
    assert sugg == [] and watching[0].reason == "too little CGM data in the next window"
