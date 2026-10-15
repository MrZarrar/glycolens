from datetime import timedelta

import pytest

import synth
from glycolens import store
from glycolens.model import Data
from glycolens.outcomes import evaluate, judge
from glycolens.suggest import Suggestion
from glycolens.windows import DEFAULT_WINDOWS

CUT = synth.START + timedelta(days=7)
NOW = synth.START + timedelta(days=14)
# The lunch_lows fixture's lows land 14:40-15:20, inside the afternoon window.
S = Suggestion("w-afternoon-carb_ratio", "afternoon", "carb_ratio", "stronger", 10.0, 9.0, ("e",))


def test_judge():
    assert judge({"tir": 70, "tbr": 1}, {"tir": 80, "tbr": 1}) == "helped"
    assert judge({"tir": 70, "tbr": 1}, {"tir": 72, "tbr": 1}) == "no_change"
    assert judge({"tir": 70, "tbr": 1}, {"tir": 75, "tbr": 3}) == "worse"
    assert judge({"tir": 70, "tbr": 1}, {"tir": 64, "tbr": 1}) == "worse"


def test_status_lifecycle(tmp_path):
    conn = store.open_store(tmp_path / "g.db")
    store.add_suggestion(conn, S, synth.START)
    store.add_suggestion(conn, S, synth.START)  # rerun: no duplicate, no reset
    assert store.set_status(conn, S.id, "applied", CUT) == "proposed"
    assert store.get_status(conn, S.id) == "applied"
    assert store.measuring_windows(conn, CUT + timedelta(days=3)) == {"afternoon"}
    assert store.measuring_windows(conn, CUT + timedelta(days=8)) == set()
    assert store.set_status(conn, S.id, "proposed", CUT) == "applied"
    assert store.changes(conn) == []
    with pytest.raises(KeyError):
        store.set_status(conn, "nope", "applied", CUT)


def test_a_change_followed_by_lows_is_judged_worse(tmp_path):
    conn = store.open_store(tmp_path / "g.db")
    clean, lows = synth.make(), synth.make("lunch_lows")
    store.save(conn, Data(glucose=[g for g in clean.glucose if g.ts < CUT] + [g for g in lows.glucose if g.ts >= CUT]))
    store.add_suggestion(conn, S, synth.START)
    store.set_status(conn, S.id, "applied", CUT)
    evaluate(conn, DEFAULT_WINDOWS, NOW)
    (c,) = store.changes(conn)
    assert c["outcome"] == "worse" and c["outcome_final"] is False and c["after"]["tbr"] > c["before"]["tbr"]


def test_nothing_measured_before_seven_days(tmp_path):
    conn = store.open_store(tmp_path / "g.db")
    store.save(conn, synth.make())
    store.add_suggestion(conn, S, synth.START)
    store.set_status(conn, S.id, "applied", NOW - timedelta(days=3))
    evaluate(conn, DEFAULT_WINDOWS, NOW)
    assert store.changes(conn)[0]["outcome"] == "pending"
