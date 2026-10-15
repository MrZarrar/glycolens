from bisect import bisect_left
from datetime import datetime, timedelta

from glycolens.model import Glucose


class Series:
    """Glucose readings sorted by time, with nearest-reading lookup."""

    def __init__(self, glucose: list[Glucose]):
        pts = sorted((g.ts, g.mmol) for g in glucose)
        self.ts = [t for t, _ in pts]
        self.v = [v for _, v in pts]

    def at(self, t: datetime, tol: timedelta = timedelta(minutes=10)) -> float | None:
        i = bisect_left(self.ts, t)
        near = [j for j in (i - 1, i) if 0 <= j < len(self.ts) and abs(self.ts[j] - t) <= tol]
        return self.v[min(near, key=lambda j: abs(self.ts[j] - t))] if near else None

    def between(self, a: datetime, b: datetime) -> list[float]:
        return self.v[bisect_left(self.ts, a):bisect_left(self.ts, b)]

    def items(self, a: datetime, b: datetime) -> list[tuple[datetime, float]]:
        i, j = bisect_left(self.ts, a), bisect_left(self.ts, b)
        return list(zip(self.ts[i:j], self.v[i:j]))
