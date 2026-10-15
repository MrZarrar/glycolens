from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Window:
    name: str
    start: int  # minute of day, inclusive
    end: int  # minute of day, exclusive (1440 = midnight)

    def contains(self, ts: datetime) -> bool:
        return self.start <= ts.hour * 60 + ts.minute < self.end


DEFAULT_WINDOWS = (
    Window("overnight", 0, 360),
    Window("breakfast", 360, 600),
    Window("lunch", 600, 840),
    Window("afternoon", 840, 1080),
    Window("dinner", 1080, 1320),
    Window("late", 1320, 1440),
)


def window_of(ts: datetime, windows) -> Window:
    return next(w for w in windows if w.contains(ts))


def _minutes(hhmm: str) -> int:
    h, m = hhmm.split(":")
    return int(h) * 60 + int(m)


def parse_windows(rows: list[dict]) -> tuple[Window, ...]:
    out = tuple(Window(r["name"], _minutes(r["start"]), _minutes(r["end"])) for r in rows)
    edges = [0] + [w.end for w in out]
    if [w.start for w in out] != edges[:-1] or edges[-1] != 1440:
        raise ValueError("windows must run back to back from 00:00 to 24:00")
    return out
