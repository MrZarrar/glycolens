from dataclasses import dataclass
from datetime import datetime, timedelta
from statistics import median

from glycolens.findings import Finding, by_window, consistent, user_boluses
from glycolens.model import Data
from glycolens.series import Series
from glycolens.windows import window_of

HORIZON = timedelta(hours=4)
HIGH_END = 2.0  # mmol/L above start at 4 h
TIMING_PEAK = 4.0  # mmol/L rise within 90 min
HIGH_SHARE = 0.7
LOW_SHARE = 0.3  # lows need less evidence than highs
TIMING_SHARE = 0.5


@dataclass(frozen=True)
class Meal:
    ts: datetime
    window: str
    carbs: float
    start: float
    peak: float
    end: float
    nadir: float  # lowest reading within 4 h

    @property
    def low(self) -> bool:
        return self.nadir < 3.9


def meals(data: Data, series: Series, windows) -> list[Meal]:
    user = user_boluses(data)
    out = []
    for b in user:
        if b.carbs_g <= 0 or any(o is not b and b.ts < o.ts < b.ts + HORIZON for o in user):
            continue
        start, end = series.at(b.ts), series.at(b.ts + HORIZON)
        early = series.between(b.ts, b.ts + timedelta(minutes=90))
        if start is None or end is None or not early:
            continue
        span = series.between(b.ts, b.ts + HORIZON + timedelta(minutes=1))
        out.append(Meal(b.ts, window_of(b.ts, windows).name, b.carbs_g, start, max(early), end, min(span)))
    return out


def is_timing(m: Meal) -> bool:
    return m.peak - m.start >= TIMING_PEAK and abs(m.end - m.start) <= HIGH_END


def _line(m: Meal) -> str:
    return f"{m.ts:%a %d %b %H:%M} {m.carbs:g}g: {m.start:.1f} → peak {m.peak:.1f} → {m.end:.1f} at 4h"


def carb_ratio(ms: list[Meal]) -> list[Finding]:
    out = []
    for window, group in by_window(ms, lambda m: m.window).items():
        rest = [m for m in group if not is_timing(m)]
        lows = [m for m in rest if m.low]
        highs = [m for m in rest if not m.low and m.end - m.start > HIGH_END]
        if rest and consistent(len(lows), len(rest), LOW_SHARE):
            out.append(Finding("carb_ratio", window, "weaker", len(rest), len(lows),
                               round(min(m.nadir for m in lows), 1), tuple(map(_line, lows))))
        elif rest and consistent(len(highs), len(rest), HIGH_SHARE):
            out.append(Finding("carb_ratio", window, "stronger", len(rest), len(highs),
                               round(median(m.end - m.start for m in highs), 1), tuple(map(_line, highs))))
    return out


def pre_bolus(ms: list[Meal]) -> list[Finding]:
    out = []
    for window, group in by_window(ms, lambda m: m.window).items():
        timing = [m for m in group if is_timing(m)]
        if consistent(len(timing), len(group), TIMING_SHARE):
            out.append(Finding("pre_bolus", window, "", len(group), len(timing),
                               round(median(m.peak - m.start for m in timing), 1), tuple(map(_line, timing))))
    return out
