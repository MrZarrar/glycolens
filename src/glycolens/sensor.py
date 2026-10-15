"""False CGM lows: a sensor peeling off or pressed on (lying on the arm) plunges out of a choppy patch.

A real low falls through continuous readings (6 → 4 → 3.5 → 3 …); a false one drops straight down after
missing readings. If the sensor then goes silent (dead), the plunge is certainly false and is removed.
If it recovers, it might be real, so it is kept and only flagged.
"""
from datetime import datetime, timedelta

from glycolens.model import Glucose

LOW = 3.9
PLUNGE = 2.0  # mmol/L below the reading before it
CHOPPY = 4  # at most this many of the 6 readings expected in the 30 min before
DEAD = timedelta(hours=2)  # no readings after it for this long
RUN_GAP = timedelta(minutes=15)


def sensor_lows(glucose: list[Glucose]) -> tuple[list[Glucose], list[datetime]]:
    """Returns (readings without plunges into a dead sensor, start of each plunge the sensor recovered from)."""
    g = sorted(glucose, key=lambda r: r.ts)
    drop, suspect, i = set(), [], 0
    while i < len(g):
        if g[i].mmol >= LOW or i == 0:
            i += 1
            continue
        j = i  # the run of lows is g[i..j]
        while j + 1 < len(g) and g[j + 1].mmol < LOW and g[j + 1].ts - g[j].ts <= RUN_GAP:
            j += 1
        recent = sum(1 for r in g[max(0, i - 6):i] if r.ts >= g[i].ts - timedelta(minutes=30))
        if g[i - 1].mmol - g[i].mmol >= PLUNGE and recent <= CHOPPY:
            if j + 1 < len(g) and g[j + 1].ts - g[j].ts >= DEAD:
                drop.update(range(i, j + 1))
            else:
                suspect.append(g[i].ts)
        i = j + 1
    return [r for k, r in enumerate(g) if k not in drop], suspect
