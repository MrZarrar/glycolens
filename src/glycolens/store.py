import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

from glycolens.model import Basal, Bolus, Data, Event, Glucose

SCHEMA = """
create table if not exists glucose(bucket text primary key, ts text not null, mmol real not null);
create table if not exists bolus(ts text not null, kind text not null, units real not null,
  carbs_g real not null, carb_ratio real not null, isf real not null, primary key (ts, kind));
create table if not exists basal(ts text primary key, programmed real not null, delivered real not null);
create table if not exists event(ts text not null, kind text not null, primary key (ts, kind));
"""


def open_store(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    return conn


def iso(ts: datetime) -> str:
    return ts.isoformat(timespec="seconds")


def _bucket(ts: datetime) -> str:
    return iso(ts.replace(minute=ts.minute - ts.minute % 5, second=0, microsecond=0))


def save(conn: sqlite3.Connection, data: Data) -> None:
    with conn:
        conn.executemany("insert or ignore into glucose values (?, ?, ?)",
                         [(_bucket(g.ts), iso(g.ts), g.mmol) for g in data.glucose])
        conn.executemany("insert or replace into bolus values (?, ?, ?, ?, ?, ?)",
                         [(iso(b.ts), b.kind, b.units, b.carbs_g, b.carb_ratio, b.isf) for b in data.boluses])
        conn.executemany("insert or replace into basal values (?, ?, ?)",
                         [(iso(b.ts), b.programmed, b.delivered) for b in data.basal])
        conn.executemany("insert or ignore into event values (?, ?)", [(iso(e.ts), e.kind) for e in data.events])


def load(conn: sqlite3.Connection, start: datetime, end: datetime) -> Data:
    def rows(sql, a=start):
        return conn.execute(sql, (iso(a), iso(end))).fetchall()

    when = datetime.fromisoformat
    # ponytail: basal looks back a day for the rate already in force at `start`; a rate older than a
    # day is missed. Upgrade: select the last record before `start` explicitly.
    return Data(
        glucose=[Glucose(when(r["ts"]), r["mmol"])
                 for r in rows("select ts, mmol from glucose where ts >= ? and ts < ? order by ts")],
        boluses=[Bolus(when(r["ts"]), r["units"], r["carbs_g"], r["kind"], r["carb_ratio"], r["isf"])
                 for r in rows("select * from bolus where ts >= ? and ts < ? order by ts")],
        basal=[Basal(when(r["ts"]), r["programmed"], r["delivered"])
               for r in rows("select * from basal where ts >= ? and ts < ? order by ts", start - timedelta(days=1))],
        events=[Event(when(r["ts"]), r["kind"])
                for r in rows("select * from event where ts >= ? and ts < ? order by ts")],
    )


def latest_glucose(conn: sqlite3.Connection) -> datetime | None:
    ts = conn.execute("select max(ts) from glucose").fetchone()[0]
    return None if ts is None else datetime.fromisoformat(ts)
