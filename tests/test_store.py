from datetime import datetime, timedelta

from glycolens import store
from glycolens.model import Basal, Bolus, Data, Event, Glucose

T = datetime(2026, 1, 5, 7, 0)


def sample():
    return Data(
        glucose=[Glucose(T, 6.5), Glucose(T + timedelta(minutes=5), 6.8)],
        boluses=[Bolus(T, 4.5, 45.0, "meal", 10.0, 2.0)],
        basal=[Basal(T, 0.8, 1.1)],
        events=[Event(T, "site_change")],
    )


def test_save_then_load_round_trips(tmp_path):
    conn = store.open_store(tmp_path / "g.db")
    store.save(conn, sample())
    got = store.load(conn, T - timedelta(hours=1), T + timedelta(hours=1))
    assert got.glucose == sample().glucose
    assert got.boluses == sample().boluses
    assert got.basal == sample().basal
    assert got.events == sample().events


def test_saving_twice_does_not_duplicate(tmp_path):
    conn = store.open_store(tmp_path / "g.db")
    store.save(conn, sample())
    store.save(conn, sample())
    got = store.load(conn, T - timedelta(hours=1), T + timedelta(hours=1))
    assert len(got.glucose) == 2 and len(got.boluses) == 1 and len(got.events) == 1


def test_second_reading_in_same_five_minutes_is_ignored(tmp_path):
    # Two sources (or a DST fall-back hour) can report the same 5-minute slot; first one wins.
    conn = store.open_store(tmp_path / "g.db")
    store.save(conn, Data(glucose=[Glucose(T, 6.5)]))
    store.save(conn, Data(glucose=[Glucose(T + timedelta(minutes=2), 9.9)]))
    got = store.load(conn, T - timedelta(hours=1), T + timedelta(hours=1))
    assert got.glucose == [Glucose(T, 6.5)]


def test_latest_glucose(tmp_path):
    conn = store.open_store(tmp_path / "g.db")
    assert store.latest_glucose(conn) is None
    store.save(conn, sample())
    assert store.latest_glucose(conn) == T + timedelta(minutes=5)


def test_load_includes_the_basal_rate_active_before_start(tmp_path):
    conn = store.open_store(tmp_path / "g.db")
    store.save(conn, sample())
    got = store.load(conn, T + timedelta(hours=2), T + timedelta(hours=3))
    assert got.basal == [Basal(T, 0.8, 1.1)]


def test_overridden_flag_round_trips_and_old_stores_are_migrated(tmp_path):
    import sqlite3
    old = sqlite3.connect(tmp_path / "g.db")  # a store created before the overridden column existed
    old.execute("create table bolus(ts text not null, kind text not null, units real not null, carbs_g real not null,"
                " carb_ratio real not null, isf real not null, primary key (ts, kind))")
    old.commit()
    old.close()
    conn = store.open_store(tmp_path / "g.db")
    b = Bolus(T, 3.5, 0.0, "correction", 7.0, 2.0, overridden=True)
    store.save(conn, Data(boluses=[b]))
    assert store.load(conn, T - timedelta(hours=1), T + timedelta(hours=1)).boluses == [b]
    store.open_store(tmp_path / "g.db")  # reopening an up-to-date store is fine
