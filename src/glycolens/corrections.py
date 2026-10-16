from datetime import timedelta
from statistics import median

from glycolens.findings import Finding, by_window, consistent, exercise_spans, latest, trace, user_boluses
from glycolens.model import Data
from glycolens.series import Series
from glycolens.windows import window_of

HORIZON = timedelta(hours=5)  # the pump's insulin duration: at 3 h only ~70% of the drop has happened
NO_CARBS = timedelta(hours=2)
TOO_STRONG = 1.3
TOO_WEAK = 0.7
SHARE = 0.7


def _traces(group, hits) -> tuple[dict, ...]:
    return tuple({**s[3], "hit": s in hits} for s in group)


def isf(data: Data, series: Series, windows) -> list[Finding]:
    user = user_boluses(data)
    spans = exercise_spans(data)
    now = latest(user, windows, "isf")  # corrections dosed with an older ISF say nothing about it
    scored = []  # (window, ratio, line)
    for b in user:
        if b.kind != "correction" or b.overridden or b.isf <= 0 or b.units <= 0:
            continue
        if b.isf != now.get(window_of(b.ts, windows).name):
            continue
        if any(o.carbs_g > 0 and abs(o.ts - b.ts) <= NO_CARBS for o in user):
            continue
        if any(o is not b and b.ts < o.ts < b.ts + HORIZON for o in user):
            continue
        if any(s <= b.ts <= e for s, e in spans):
            continue
        start, end = series.at(b.ts), series.at(b.ts + HORIZON)
        if start is None or end is None:
            continue
        expected = b.units * b.isf
        ratio = (start - end) / expected
        if ratio < 0:
            continue  # glucose rose after insulin: food, the site or illness, not the correction factor
        line = f"{b.ts:%a %d %b %H:%M} {b.units:g}U: {start:.1f} → {end:.1f} (expected −{expected:.1f})"
        tr = {"t0": b.ts, "units": b.units, "expected_drop": round(expected, 1), "points": trace(series, b.ts, 300)}
        scored.append((window_of(b.ts, windows).name, ratio, line, tr))
    out = []
    for window, group in by_window(scored, lambda s: s[0]).items():
        ratios = [s[1] for s in group]
        strong = [s for s in group if s[1] > TOO_STRONG]
        weak = [s for s in group if s[1] < TOO_WEAK]
        if consistent(len(strong), len(group), SHARE):
            out.append(Finding("isf", window, "weaker", len(group), len(strong), round(median(ratios), 1),
                               tuple(s[2] for s in strong), _traces(group, strong)))
        elif consistent(len(weak), len(group), SHARE):
            out.append(Finding("isf", window, "stronger", len(group), len(weak), round(median(ratios), 1),
                               tuple(s[2] for s in weak), _traces(group, weak)))
    return out
