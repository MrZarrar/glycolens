from datetime import datetime, time, timedelta
from statistics import median

from glycolens.findings import Finding, consistent, exercise_spans, user_boluses
from glycolens.model import Basal, Data
from glycolens.series import Series

FAST_BEFORE = timedelta(hours=4)
HIGH_RATIO = 1.25
LOW_RATIO = 0.75
DRIFT = 1.5
SHARE = 0.7


def delivered_ratio(records: list[Basal], a: datetime, b: datetime) -> float | None:
    rs = sorted(records, key=lambda r: r.ts)
    given = planned = 0.0
    for r, nxt in zip(rs, rs[1:] + [None]):
        lo, hi = max(r.ts, a), min(nxt.ts if nxt else b, b)
        if hi <= lo:
            continue
        hours = (hi - lo) / timedelta(hours=1)
        given += r.delivered * hours
        planned += r.programmed * hours
    return round(given / planned, 2) if planned > 0 else None


def basal(data: Data, series: Series, windows) -> list[Finding]:
    user = user_boluses(data)
    spans = exercise_spans(data)
    days = sorted({g.ts.date() for g in data.glucose})
    out = []
    for w in windows:
        under, over, n, ratios = [], [], 0, []
        for d in days:
            a = datetime.combine(d, time()) + timedelta(minutes=w.start)
            b = datetime.combine(d, time()) + timedelta(minutes=w.end)
            if any(a - FAST_BEFORE <= o.ts < b for o in user):
                continue
            if any(s < b and e > a - FAST_BEFORE for s, e in spans):
                continue
            ga, gb, ratio = series.at(a), series.at(b), delivered_ratio(data.basal, a, b)
            if ga is None or gb is None or ratio is None:
                continue
            n += 1
            ratios.append(ratio)
            line = f"{a:%a %d %b} {w.name}: basal ran at {ratio:.0%} of programmed, glucose {ga:.1f} → {gb:.1f}"
            if ratio >= HIGH_RATIO or gb - ga > DRIFT:
                under.append(line)
            elif ratio <= LOW_RATIO or gb - ga < -DRIFT:
                over.append(line)
        if n and consistent(len(over), n, SHARE):
            out.append(Finding("basal", w.name, "weaker", n, len(over), round(median(ratios), 2), tuple(over)))
        elif n and consistent(len(under), n, SHARE):
            out.append(Finding("basal", w.name, "stronger", n, len(under), round(median(ratios), 2), tuple(under)))
    return out
