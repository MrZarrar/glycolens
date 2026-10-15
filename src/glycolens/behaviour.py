from datetime import timedelta
from statistics import fmean

from glycolens.findings import Finding, consistent, exercise_spans
from glycolens.model import Data
from glycolens.series import Series

AFTER_EXERCISE = timedelta(hours=6)
EXERCISE_SHARE = 0.5
SITE_DIFF = 1.5


def exercise_low(data: Data, series: Series) -> list[Finding]:
    sessions = exercise_spans(data)
    lows = []
    for s, e in sessions:
        after = series.between(s, e + AFTER_EXERCISE)
        if after and min(after) < 3.9:
            lows.append((s, min(after)))
    if not consistent(len(lows), len(sessions) or 1, EXERCISE_SHARE):
        return []
    return [Finding("exercise_low", "all", "", len(sessions), len(lows), round(min(m for _, m in lows), 1),
                    tuple(f"{s:%a %d %b %H:%M}: low of {m:.1f} within 6h" for s, m in lows))]


def site_age(data: Data, series: Series) -> list[Finding]:
    changes = sorted(e.ts for e in data.events if e.kind == "site_change")
    early, late = [], []
    for t, v in zip(series.ts, series.v):
        since = [c for c in changes if c <= t]
        if not since:
            continue
        (late if (t - since[-1]) >= timedelta(days=2) else early).append(v)
    if len(late) < 288 or not early:
        return []
    diff = round(fmean(late) - fmean(early), 1)
    if diff < SITE_DIFF:
        return []
    return [Finding("site_age", "all", "", len(changes), len(changes), diff,
                    (f"day 3+ mean {fmean(late):.1f} vs days 1–2 mean {fmean(early):.1f}",))]
