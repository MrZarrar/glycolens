from dataclasses import dataclass
from datetime import datetime, timedelta

from glycolens.model import Bolus, Data


@dataclass(frozen=True)
class Finding:
    rule: str
    window: str
    direction: str  # "stronger" (more insulin), "weaker", or "" for behaviour
    events: int  # qualifying events
    hits: int  # events showing the pattern
    metric: float  # the rule's headline number
    evidence: tuple[str, ...]


def consistent(hits: int, events: int, share: float) -> bool:
    return hits >= 2 and hits / events >= share


def user_boluses(data: Data) -> list[Bolus]:
    return [b for b in data.boluses if b.kind != "auto"]


def exercise_spans(data: Data) -> list[tuple[datetime, datetime]]:
    spans, start = [], None
    for e in sorted(data.events, key=lambda e: e.ts):
        if e.kind == "exercise_start":
            start = e.ts
        elif e.kind == "exercise_end" and start is not None:
            spans.append((start, e.ts))
            start = None
    if start is not None:
        spans.append((start, start + timedelta(hours=2)))  # no end logged: assume 2 h
    return spans


def by_window(items, key) -> dict[str, list]:
    out: dict[str, list] = {}
    for item in items:
        out.setdefault(key(item), []).append(item)
    return out
