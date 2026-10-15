from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal

MG_PER_MMOL = 18.0182

BolusKind = Literal["meal", "correction", "auto"]
EventKind = Literal["site_change", "exercise_start", "exercise_end"]


@dataclass(frozen=True)
class Glucose:
    ts: datetime
    mmol: float


@dataclass(frozen=True)
class Bolus:
    ts: datetime
    units: float
    carbs_g: float
    kind: BolusKind
    carb_ratio: float  # g/U used by the bolus calculator, 0 if unknown
    isf: float  # mmol/L per U used by the bolus calculator, 0 if unknown
    # The delivered dose isn't the calculator's (user override, or aborted / stopped by an alarm),
    # so it doesn't test the settings.
    overridden: bool = False


@dataclass(frozen=True)
class Basal:
    """A basal rate in force from `ts` until the next record."""

    ts: datetime
    programmed: float  # U/h from the profile
    delivered: float  # U/h actually commanded (Control-IQ, temp rate, suspend)


@dataclass(frozen=True)
class Event:
    ts: datetime
    kind: EventKind


@dataclass
class Data:
    glucose: list[Glucose] = field(default_factory=list)
    boluses: list[Bolus] = field(default_factory=list)
    basal: list[Basal] = field(default_factory=list)
    events: list[Event] = field(default_factory=list)
