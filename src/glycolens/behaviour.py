from datetime import timedelta

from glycolens.findings import Finding, consistent, exercise_spans
from glycolens.model import Data
from glycolens.series import Series

AFTER_EXERCISE = timedelta(hours=6)
EXERCISE_SHARE = 0.5


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
