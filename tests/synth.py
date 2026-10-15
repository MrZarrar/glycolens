"""Synthetic 14-day datasets with one known, injected fault each.

Shapes are piecewise-linear [(minutes after start, mmol delta)] added to a flat 6.5 baseline.
"""
from datetime import datetime, timedelta

from glycolens.model import Basal, Bolus, Data, Event, Glucose

START = datetime(2026, 1, 5)
DAYS = 14
BASE = 6.5

CLEAN_MEAL = [(0, 0.0), (60, 2.5), (240, 0.5), (300, 0.0)]
WEAK_MEAL = [(0, 0.0), (60, 3.5), (240, 3.0), (420, 0.0)]
LATE_BOLUS_MEAL = [(0, 0.0), (60, 5.0), (240, 0.5), (300, 0.0)]
LOW_MEAL = [(0, 0.0), (45, 1.0), (180, -3.3), (240, -1.5), (330, 0.0)]

FAULTS = ("weak_breakfast", "late_prebolus", "lunch_lows", "strong_isf", "weak_isf", "night_basal_low",
          "exercise_lows")


def _bump(off: dict, t0: datetime, shape: list[tuple[int, float]]) -> None:
    for (m0, d0), (m1, d1) in zip(shape, shape[1:]):
        for m in range(m0, m1, 5):
            t = t0 + timedelta(minutes=m)
            off[t] = off.get(t, 0.0) + d0 + (d1 - d0) * (m - m0) / (m1 - m0)


def _meal(off, boluses, t, carbs, shape):
    _bump(off, t, shape)
    boluses.append(Bolus(t, carbs / 10, float(carbs), "meal", 10.0, 2.0))


def make(fault: str | None = None) -> Data:
    off, boluses, basal, events = {}, [], [], []
    for day in range(DAYS):
        d = START + timedelta(days=day)
        odd = day % 2 == 1
        breakfast = {"weak_breakfast": WEAK_MEAL, "late_prebolus": LATE_BOLUS_MEAL}.get(fault, CLEAN_MEAL)
        _meal(off, boluses, d.replace(hour=7), 45, breakfast)
        _meal(off, boluses, d.replace(hour=12), 60, LOW_MEAL if fault == "lunch_lows" else CLEAN_MEAL)
        if odd:
            _meal(off, boluses, d.replace(hour=18, minute=30), 70, CLEAN_MEAL)
        else:
            drop = {"strong_isf": 3.2, "weak_isf": 1.2}.get(fault, 2.0)
            _bump(off, d.replace(hour=16), [(0, 0.0), (180, 4.0), (480, 4.0 - drop), (570, 0.0)])
            boluses.append(Bolus(d.replace(hour=19), 1.0, 0.0, "correction", 10.0, 2.0))
        if fault == "exercise_lows" and odd:
            events += [Event(d.replace(hour=21, minute=30), "exercise_start"),
                       Event(d.replace(hour=22, minute=30), "exercise_end")]
            _bump(off, d.replace(hour=22, minute=30), [(0, 0.0), (60, -3.1), (150, 0.0)])
        if fault == "night_basal_low":
            _bump(off, d, [(0, 0.0), (360, 2.0), (420, 0.0)])
        if day % 3 == 0:
            events.append(Event(d.replace(hour=8), "site_change"))
        for h in range(24):
            low_night = fault == "night_basal_low" and h < 6
            basal.append(Basal(d.replace(hour=h), 0.8, 1.12 if low_night else 0.8))
    grid = [START + timedelta(minutes=5 * i) for i in range(DAYS * 288)]
    glucose = [Glucose(t, round(BASE + off.get(t, 0.0), 2)) for t in grid]
    return Data(glucose=glucose, boluses=sorted(boluses, key=lambda b: b.ts), basal=basal,
                events=sorted(events, key=lambda e: e.ts))
