import pytest

import synth
from glycolens.analyse import analyse
from glycolens.windows import DEFAULT_WINDOWS

EXPECTED = {
    None: set(),
    "weak_breakfast": {("carb_ratio", "breakfast", "stronger")},
    "late_prebolus": {("pre_bolus", "breakfast", "")},
    "lunch_lows": {("carb_ratio", "lunch", "weaker")},
    "strong_isf": {("isf", "dinner", "weaker")},
    "weak_isf": {("isf", "dinner", "stronger")},
    "night_basal_low": {("basal", "overnight", "stronger")},
    "exercise_lows": {("exercise_low", "all", "")},
}


def test_matrix_covers_every_fault():
    assert set(EXPECTED) - {None} == set(synth.FAULTS)


@pytest.mark.parametrize("fault", list(EXPECTED))
def test_each_fault_triggers_only_its_own_rule(fault):
    got = {(f.rule, f.window, f.direction) for f in analyse(synth.make(fault), DEFAULT_WINDOWS)}
    assert got == EXPECTED[fault]
