from collections import defaultdict
from datetime import datetime, timedelta
from statistics import fmean, pstdev, quantiles

from glycolens.model import MG_PER_MMOL
from glycolens.series import Series
from glycolens.windows import Window

EMPTY = {"mean": None, "tir": None, "tbr": None, "tbr_severe": None, "tar": None,
         "tar_severe": None, "gmi": None, "cv": None, "min": None}


def summary(values: list[float], minutes: float) -> dict:
    if not values:
        return {"coverage": 0.0, **EMPTY}
    n, mean = len(values), fmean(values)

    def pct(k):
        return round(100 * k / n, 1)

    return {
        "coverage": round(min(1.0, n / max(minutes / 5, 1)), 3),
        "mean": round(mean, 1),
        "tir": pct(sum(3.9 <= v <= 10.0 for v in values)),
        "tbr": pct(sum(v < 3.9 for v in values)),
        "tbr_severe": pct(sum(v < 3.0 for v in values)),
        "tar": pct(sum(v > 10.0 for v in values)),
        "tar_severe": pct(sum(v > 13.9 for v in values)),
        "gmi": round(3.31 + 0.02392 * mean * MG_PER_MMOL, 1),
        "cv": round(pstdev(values) / mean * 100, 1),
        "min": round(min(values), 1),
    }


def window_summary(series: Series, window: Window, start: datetime, end: datetime) -> dict:
    values = [v for t, v in series.items(start, end) if window.contains(t)]
    return summary(values, (end - start) / timedelta(days=1) * (window.end - window.start))


def agp(series: Series) -> list[dict]:
    by_hour = defaultdict(list)
    for t, v in zip(series.ts, series.v):
        by_hour[t.hour].append(v)
    rows = []
    for h in range(24):
        vs = by_hour[h]
        if len(vs) < 2:
            rows.append({"hour": h, "p5": None, "p25": None, "p50": None, "p75": None, "p95": None})
            continue
        q = quantiles(vs, n=20, method="inclusive")
        rows.append({"hour": h, "p5": round(q[0], 1), "p25": round(q[4], 1), "p50": round(q[9], 1),
                     "p75": round(q[14], 1), "p95": round(q[18], 1)})
    return rows
