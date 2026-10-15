from dataclasses import dataclass
from statistics import median

from glycolens.findings import Finding, latest, user_boluses
from glycolens.model import Data

SETTINGS = ("carb_ratio", "isf", "basal")
STEP = 0.10
MIN_EVENTS = 4
MIN_COVERAGE = 0.7
LOW_TBR = 4.0  # % below 3.9
SEVERE_MIN = 3.0


@dataclass(frozen=True)
class Suggestion:
    id: str
    window: str
    setting: str
    direction: str
    current: float
    proposed: float
    evidence: tuple[str, ...]


@dataclass(frozen=True)
class Watching:
    window: str
    rule: str
    reason: str


def step(setting: str, direction: str, current: float) -> float:
    # Carb ratio and ISF: a smaller number is more insulin. Basal: a bigger number is.
    up = (direction == "stronger") == (setting == "basal")
    return round(current * (1 + STEP if up else 1 - STEP), 2 if setting == "basal" else 1)


def current_settings(data: Data, windows) -> dict[tuple[str, str], float]:
    user = user_boluses(data)
    cur = {(w, s): v for s in ("carb_ratio", "isf") for w, v in latest(user, windows, s).items()}
    for w in windows:
        # ponytail: median of programmed rates that start inside the window; a window with no rate
        # change of its own reports "current setting unknown". Upgrade: carry the rate in force.
        rates = [r.programmed for r in data.basal if w.contains(r.ts)]
        if rates:
            cur[(w.name, "basal")] = round(median(rates), 2)
    return cur


def _lows(st: dict) -> bool:
    return st["tbr"] > LOW_TBR or st["min"] < SEVERE_MIN


def _next(window_stats: dict, name: str) -> str:
    names = list(window_stats)  # in time order; the last window runs into the first
    return names[(names.index(name) + 1) % len(names)]


def decide(findings: list[Finding], window_stats: dict[str, dict], current: dict, measuring: set[str],
           week_id: str) -> tuple[list[Suggestion], list[Watching]]:
    order = sorted((f for f in findings if f.rule in SETTINGS),
                   key=lambda f: (f.direction != "weaker", SETTINGS.index(f.rule)))
    out, watching, taken = [], [], set()
    for f in order:
        st = window_stats[f.window]
        cur = current.get((f.window, f.rule))
        if f.window in measuring:
            reason = "measuring an applied change"
        elif st["coverage"] < MIN_COVERAGE:
            reason = "insufficient CGM data"
        elif f.events < MIN_EVENTS:
            reason = f"only {f.events} qualifying events"
        elif f.direction == "stronger" and _lows(st):
            reason = "lows in this window"
        elif f.direction == "stronger" and window_stats[_next(window_stats, f.window)]["coverage"] < MIN_COVERAGE:
            reason = "too little CGM data in the next window"
        elif f.direction == "stronger" and _lows(window_stats[_next(window_stats, f.window)]):
            reason = "lows in the next window"  # insulin keeps acting for up to 5 h
        elif f.window in taken:
            reason = "one change per window per week"
        elif cur is None:
            reason = "current setting unknown"
        else:
            reason = None
        if reason:
            watching.append(Watching(f.window, f.rule, reason))
            continue
        taken.add(f.window)
        out.append(Suggestion(f"{week_id}-{f.window}-{f.rule}", f.window, f.rule, f.direction, cur,
                              step(f.rule, f.direction, cur), f.evidence))
    return out, watching
