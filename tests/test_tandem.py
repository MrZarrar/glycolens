from datetime import date, datetime

import pytest

from glycolens import tandem
from glycolens.model import Basal, Bolus, Event

T = datetime(2026, 1, 5, 7, 0)


class _Ts:
    def __init__(self, dt):
        self.naive = dt


def ev(name, **fields):
    return type(name, (), {"eventTimestamp": _Ts(fields.pop("ts", T)), **fields})()


def test_maps_g7_readings_and_skips_unusable_ones():
    d = tandem.to_data([ev("LidCgmDataG7", currentGlucoseDisplayValue=108, glucoseValueStatusRaw=0),
                        ev("LidCgmDataG7", currentGlucoseDisplayValue=40, glucoseValueStatusRaw=6)])
    assert [(g.ts, g.mmol) for g in d.glucose] == [(T, 5.99)]


def test_joins_bolus_request_and_completion():
    d = tandem.to_data([
        ev("LidBolusRequestedMsg1", bolusId=7, carbAmount=45, bolusTypeRaw=1, carbRatioRaw=10000),
        ev("LidBolusRequestedMsg2", bolusId=7, isf=36),
        ev("LidBolusCompleted", bolusId=7, insulinDelivered=4.5),
        ev("LidBolusRequestedMsg1", bolusId=8, carbAmount=0, bolusTypeRaw=1, carbRatioRaw=10000),
        ev("LidBolusRequestedMsg2", bolusId=8, isf=36),
        ev("LidBolusCompleted", bolusId=8, insulinDelivered=1.0),
        ev("LidBolusCompleted", bolusId=9, insulinDelivered=0.6),
        # Control-IQ auto-bolus: it has request messages too, marked bolusTypeRaw 2 (SPIKE.md)
        ev("LidBolusRequestedMsg1", bolusId=10, carbAmount=0, bolusTypeRaw=2, carbRatioRaw=0),
        ev("LidBolusRequestedMsg2", bolusId=10, isf=36),
        ev("LidBolusCompleted", bolusId=10, insulinDelivered=0.8),
    ])
    assert d.boluses == [Bolus(T, 4.5, 45.0, "meal", 10.0, 2.0), Bolus(T, 1.0, 0.0, "correction", 10.0, 2.0),
                         Bolus(T, 0.6, 0.0, "auto", 0.0, 0.0), Bolus(T, 0.8, 0.0, "auto", 0.0, 0.0)]


def test_maps_basal_and_events():
    d = tandem.to_data([
        ev("LidBasalDelivery", profileBasalRate=800, commandedRate=1120),
        ev("LidCannulaFilled", completionStatusRaw=3),
        ev("LidCannulaFilled", completionStatusRaw=0),  # user aborted: not a site change
        ev("LidAaUserModeChange", currentUserModeRaw=2, previousUserModeRaw=0),
        ev("LidAaUserModeChange", currentUserModeRaw=0, previousUserModeRaw=2),
    ])
    assert d.basal == [Basal(T, 0.8, 1.12)]
    assert d.events == [Event(T, "site_change"), Event(T, "exercise_start"), Event(T, "exercise_end")]


def test_fetch_without_login_says_what_to_do(monkeypatch):
    monkeypatch.setattr(tandem.keyring, "get_password", lambda *a: None)
    with pytest.raises(RuntimeError, match="glycolens login"):
        tandem.fetch(type("Cfg", (), {"region": "EU", "analysis_days": 14})())


def test_window_ends_at_the_pumps_last_upload():
    # A pump that hasn't synced returns nothing for "the last N days"; anchor on maxDateOfEvents.
    pump = {"maxDateOfEvents": "2026-09-26T18:05:12"}
    assert tandem.window(pump, 14) == (date(2026, 9, 12), date(2026, 9, 26))
    assert tandem.window({"maxDateOfEvents": None}, 14)[1] == date.today()


def test_cgm_reading_is_timed_by_the_sensor_not_by_arrival():
    # A back-filled G7 reading reaches the pump late; egvTimeStamp (seconds since 2008-01-01, pump
    # local time) is when it was measured. 592617669 s → 2026-10-12 00:01:09.
    d = tandem.to_data([ev("LidCgmDataG7", currentGlucoseDisplayValue=108, glucoseValueStatusRaw=0,
                           egvTimeStamp=592617669, ts=datetime(2026, 10, 12, 0, 40))])
    assert [g.ts for g in d.glucose] == [datetime(2026, 10, 12, 0, 1, 9)]


def test_bolus_where_the_user_overrode_the_calculator_is_marked():
    # Override Increase with 0 carbs is how the owner often boluses for food (SPIKE.md).
    d = tandem.to_data([
        ev("LidBolusRequestedMsg1", bolusId=11, carbAmount=0, bolusTypeRaw=1, carbRatioRaw=7000),
        ev("LidBolusRequestedMsg2", bolusId=11, isf=36, userOverrideRaw=1),
        ev("LidBolusCompleted", bolusId=11, insulinDelivered=3.5),
    ])
    assert d.boluses == [Bolus(T, 3.5, 0.0, "correction", 7.0, 2.0, overridden=True)]
