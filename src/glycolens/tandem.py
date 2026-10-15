"""Tandem Source adapter on top of tconnectsync (unofficial API).

Event field names come from tconnectsync.eventparser.events; the constants below were confirmed
against a real account in the Task 1 spike (see SPIKE.md).
"""
import getpass
import json
import os
from datetime import date, timedelta
from typing import Iterable

import keyring

from glycolens.model import MG_PER_MMOL, Basal, Bolus, Data, Event, Glucose

CARB_RATIO_SCALE = 1000  # carbRatioRaw 7000 → 7 g/U
ISF_IS_MGDL = True  # LidBolusRequestedMsg2.isf is mg/dL per U
AUTO_BOLUS_TYPE = 2  # LidBolusRequestedMsg1.bolusTypeRaw "Automatic Correction" (Control-IQ); an enum, not bits
CANNULA_OK = 3  # LidCannulaFilled.completionStatusRaw "Completed"
GLUCOSE_OK = 0  # glucoseValueStatusRaw "precise value"
EXERCISE, NORMAL = 2, 0


def _ts(e):
    return e.eventTimestamp.naive


def _mode_events(e) -> list[Event]:
    cur, prev = e.currentUserModeRaw, e.previousUserModeRaw
    if cur == EXERCISE and prev != EXERCISE:
        return [Event(_ts(e), "exercise_start")]
    if prev == EXERCISE and cur != EXERCISE:
        return [Event(_ts(e), "exercise_end")]
    return []


def to_data(events: Iterable) -> Data:
    out, requests, completed = Data(), {}, []
    for e in events:
        name = type(e).__name__
        if name in ("LidCgmDataG7", "LidCgmDataGxb"):
            if e.glucoseValueStatusRaw == GLUCOSE_OK:
                out.glucose.append(Glucose(_ts(e), round(e.currentGlucoseDisplayValue / MG_PER_MMOL, 2)))
        elif name == "LidBolusRequestedMsg1":
            requests.setdefault(e.bolusId, {}).update(
                carbs=float(e.carbAmount), type=e.bolusTypeRaw, cr=e.carbRatioRaw / CARB_RATIO_SCALE)
        elif name == "LidBolusRequestedMsg2":
            requests.setdefault(e.bolusId, {})["isf"] = e.isf / MG_PER_MMOL if ISF_IS_MGDL else float(e.isf)
        elif name == "LidBolusCompleted":
            completed.append((_ts(e), e.bolusId, e.insulinDelivered))
        elif name == "LidBasalDelivery":
            out.basal.append(Basal(_ts(e), e.profileBasalRate / 1000, e.commandedRate / 1000))
        elif name == "LidCannulaFilled" and e.completionStatusRaw == CANNULA_OK:
            out.events.append(Event(_ts(e), "site_change"))
        elif name == "LidAaUserModeChange":
            out.events += _mode_events(e)
    for ts, bolus_id, units in completed:
        if units <= 0:
            continue
        r = requests.get(bolus_id)
        if r is None or "type" not in r or r["type"] == AUTO_BOLUS_TYPE:
            out.boluses.append(Bolus(ts, round(units, 2), 0.0, "auto", 0.0, 0.0))
            continue
        kind = "meal" if r["carbs"] > 0 else "correction"
        out.boluses.append(Bolus(ts, round(units, 2), r["carbs"], kind, round(r["cr"], 1), round(r.get("isf", 0.0), 1)))
    return out


def login() -> None:
    email = input("Tandem Source email: ")
    password = getpass.getpass("Tandem Source password: ")
    keyring.set_password("glycolens", "tandem", json.dumps({"email": email, "password": password}))
    print("saved to Windows Credential Manager")


def fetch(cfg) -> Data:
    raw = keyring.get_password("glycolens", "tandem")
    if raw is None:
        raise RuntimeError("no Tandem Source login saved: run `glycolens login` first")
    creds = json.loads(raw)
    # tconnectsync reads these at import: it defaults to America/New_York and caches tokens on disk.
    os.environ.setdefault("TIMEZONE_NAME", "Europe/London")
    os.environ["CACHE_CREDENTIALS"] = "false"
    from tconnectsync.api.tandemsource import TandemSourceApi  # slow import; only when fetching

    api = TandemSourceApi(creds["email"], creds["password"], cfg.region)
    pump = api.get_pumper()["pumps"][0]
    start, end = window(pump, cfg.analysis_days)
    return to_data(api.pump_events(pump["assignmentId"], min_date=start.isoformat(), max_date=end.isoformat(),
                                   fetch_all_event_types=True))


def window(pump: dict, days: int) -> tuple[date, date]:
    """Days to fetch, ending at the pump's last uploaded event (an unsynced pump has nothing for today)."""
    last = pump.get("maxDateOfEvents")
    end = date.fromisoformat(last[:10]) if last else date.today()
    return end - timedelta(days=days), end
