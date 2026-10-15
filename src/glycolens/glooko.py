"""Glooko 'Export to CSV' zip, dropped into ~/.glycolens/drop/ by hand. CGM only."""
import csv
import os
import sys
import zipfile
from datetime import datetime
from pathlib import Path

from glycolens.model import MG_PER_MMOL, Data, Glucose

FORMATS = ("%d/%m/%Y %H:%M", "%Y-%m-%d %H:%M", "%d/%m/%Y %H:%M:%S", "%Y-%m-%d %H:%M:%S")


def _parse_ts(text: str) -> datetime:
    for fmt in FORMATS:
        try:
            return datetime.strptime(text.strip(), fmt)
        except ValueError:
            pass
    raise ValueError(f"unrecognised Glooko timestamp: {text!r}")


def parse_cgm_csv(text: str) -> list[Glucose]:
    lines = text.splitlines()
    start = next(i for i, line in enumerate(lines) if line.startswith("Timestamp"))
    reader = csv.DictReader(lines[start:])
    column = next(c for c in reader.fieldnames if "Glucose" in c)
    mmol = "mmol" in column.lower()
    return [Glucose(_parse_ts(row["Timestamp"]),
                    round(float(row[column]) if mmol else float(row[column]) / MG_PER_MMOL, 2))
            for row in reader if row[column]]


def read_zip(path: Path) -> Data:
    out = Data()
    with zipfile.ZipFile(path) as z:
        for name in z.namelist():
            if "cgm" in name.lower() and name.endswith(".csv"):
                out.glucose += parse_cgm_csv(z.read(name).decode("utf-8-sig"))
    return out


def import_drop(folder: Path) -> list[tuple[Path, Data]]:
    out = []
    for path in sorted(folder.glob("*.zip")):
        try:
            out.append((path, read_zip(path)))
        except (zipfile.BadZipFile, ValueError, StopIteration) as e:
            print(f"glycolens: could not read {path.name}: {e}", file=sys.stderr)
            os.replace(path, path.with_name(path.name + ".failed"))  # Glooko reuses names
    return out


def mark_imported(path: Path) -> None:
    done = path.parent / "imported"
    done.mkdir(exist_ok=True)
    os.replace(path, done / path.name)  # Glooko names every export the same
