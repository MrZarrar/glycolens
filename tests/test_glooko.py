import zipfile
from datetime import datetime

from glycolens import glooko

CSV_MMOL = "Name:Test, Date Range:01/01/2026 - 14/01/2026\nTimestamp,CGM Glucose Value (mmol/l),Serial Number\n05/01/2026 07:00,6.5,X\n05/01/2026 07:05,6.8,X\n"
CSV_MG = "Timestamp,CGM Glucose Value (mg/dl),Serial Number\n2026-01-05 07:00,117,X\n"


def test_parses_uk_mmol_export():
    got = glooko.parse_cgm_csv(CSV_MMOL)
    assert [(g.ts, g.mmol) for g in got] == [(datetime(2026, 1, 5, 7, 0), 6.5), (datetime(2026, 1, 5, 7, 5), 6.8)]


def test_converts_mgdl():
    assert glooko.parse_cgm_csv(CSV_MG)[0].mmol == 6.49


def test_drop_folder_imports_and_moves(tmp_path):
    with zipfile.ZipFile(tmp_path / "export.zip", "w") as z:
        z.writestr("cgm_data_1.csv", CSV_MMOL)
    (tmp_path / "broken.zip").write_text("not a zip")
    got = glooko.import_drop(tmp_path)
    assert len(got) == 1 and len(got[0][1].glucose) == 2
    glooko.mark_imported(got[0][0])
    assert (tmp_path / "imported" / "export.zip").exists() and (tmp_path / "broken.zip.failed").exists()


def test_a_second_export_with_the_same_name_imports_too(tmp_path):
    for _ in range(2):  # Glooko names every export the same; Windows rename refuses to overwrite
        with zipfile.ZipFile(tmp_path / "export.zip", "w") as z:
            z.writestr("cgm_data_1.csv", CSV_MMOL)
        ((path, _),) = glooko.import_drop(tmp_path)
        glooko.mark_imported(path)
    assert (tmp_path / "imported" / "export.zip").exists() and not (tmp_path / "export.zip").exists()
