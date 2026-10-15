import sqlite3
from datetime import datetime, timedelta

from glycolens import store
from glycolens.series import Series
from glycolens.stats import window_summary

MIN_AFTER = timedelta(days=7)
FULL = timedelta(days=14)
TIR_DELTA = 5.0  # percentage points
TBR_DELTA = 1.0


def judge(before: dict, after: dict) -> str:
    if after["tbr"] - before["tbr"] > TBR_DELTA or before["tir"] - after["tir"] >= TIR_DELTA:
        return "worse"
    if after["tir"] - before["tir"] >= TIR_DELTA:
        return "helped"
    return "no_change"


def evaluate(conn: sqlite3.Connection, windows, now: datetime) -> None:
    for c in store.changes(conn):
        if c["outcome_final"]:
            continue
        at = datetime.fromisoformat(c["applied_at"])
        w = next((w for w in windows if w.name == c["window"]), None)
        if w is None or now - at < MIN_AFTER:
            continue
        stop = min(now, at + FULL)
        series = Series(store.load(conn, at - FULL, stop).glucose)
        before, after = window_summary(series, w, at - FULL, at), window_summary(series, w, at, stop)
        if before["mean"] is None or after["mean"] is None:
            continue
        store.set_outcome(conn, c["id"], judge(before, after), now - at >= FULL, before, after)
