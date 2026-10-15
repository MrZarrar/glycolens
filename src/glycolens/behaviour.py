from datetime import timedelta
from statistics import fmean

from glycolens.findings import Finding, by_window, consistent, exercise_spans, user_boluses
from glycolens.model import Data
from glycolens.series import Series
from glycolens.windows import window_of

RISE = 3.0  # mmol/L within an hour
RISE_SPAN = timedelta(hours=1)
REFRACTORY = timedelta(hours=3)
AFTER_EXERCISE = timedelta(hours=6)
EXERCISE_SHARE = 0.5
SITE_DIFF = 1.5


def missed_bolus(data: Data, series: Series, windows) -> list[Finding]:
    user = user_boluses(data)
    hits, last = [], None
    for t, v in zip(series.ts, series.v):
        later = series.at(t + RISE_SPAN, tol=timedelta(minutes=5))
        if later is None or later - v < RISE or (last and t - last < REFRACTORY):
            continue
        if any(t - RISE_SPAN <= o.ts <= t + RISE_SPAN for o in user):
            continue
        hits.append((t, v, later))
        last = t
    out = []
    for window, group in by_window(hits, lambda h: window_of(h[0], windows).name).items():
        if len(group) >= 2:
            out.append(Finding("missed_bolus", window, "", len(group), len(group), float(len(group)),
                               tuple(f"{t:%a %d %b %H:%M}: {v:.1f} → {u:.1f} in an hour, no bolus" for t, v, u in group)))
    return out


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
