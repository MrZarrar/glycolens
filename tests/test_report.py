import json
from datetime import timedelta

import pytest

import synth
from glycolens import report
from glycolens.analyse import analyse
from glycolens.series import Series
from glycolens.stats import agp, summary, window_summary
from glycolens.suggest import current_settings, decide
from glycolens.windows import DEFAULT_WINDOWS

END = synth.START + timedelta(days=synth.DAYS)


def make_report(fault="weak_breakfast", stale=None):
    d = synth.make(fault)
    s = Series(d.glucose)
    ws = {w.name: window_summary(s, w, synth.START, END) for w in DEFAULT_WINDOWS}
    findings = analyse(d, DEFAULT_WINDOWS)
    sugg, watching = decide(findings, ws, current_settings(d, DEFAULT_WINDOWS), set(), "2026-W03")
    return report.build(now=END, start=synth.START, end=END, through=END, stale_since=stale,
                        stats=summary([g.mmol for g in d.glucose], synth.DAYS * 1440), window_stats=ws, agp=agp(s),
                        findings=findings, suggestions=sugg, statuses={}, watching=watching, changes=[],
                        windows=DEFAULT_WINDOWS)


def test_report_shape_and_text():
    r = make_report()
    assert r["schema_version"] == 1 and r["period"]["days"] == 14 and r["stale_since"] is None
    (s,) = r["suggestions"]
    assert s["status"] == "proposed" and "10 to 9" in s["text"]
    assert "14 of 14 meals ended high" in r["findings"][0]["text"]
    assert len(r["windows"]) == 6 and len(r["agp"]) == 24
    json.dumps(r)  # serialisable


def test_write_json_is_atomic(tmp_path, monkeypatch):
    path = tmp_path / "report.json"
    report.write_json({"schema_version": 1, "old": True}, path)

    def boom(*a):
        raise OSError("disk full")

    monkeypatch.setattr(report.os, "replace", boom)
    with pytest.raises(OSError):
        report.write_json(make_report(), path)
    assert json.loads(path.read_text()) == {"schema_version": 1, "old": True}


def test_update_status_rewrites_one_suggestion(tmp_path):
    path = tmp_path / "report.json"
    r = make_report()
    report.write_json(r, path)
    report.update_status(path, r["suggestions"][0]["id"], "applied")
    assert json.loads(path.read_text())["suggestions"][0]["status"] == "applied"


def test_markdown_is_summary_only(tmp_path):
    r = make_report(stale=END - timedelta(days=3))
    r["summary"] = report.template_summary(r)
    md = report.to_markdown(r)
    assert md.startswith("---\n") and "source: noctis-health" in md and "Data stale since" in md
    assert len(md) < 6000
    note = report.write_vault_note(r, tmp_path)
    assert note.parent == tmp_path / "inbox" and note.read_text(encoding="utf-8") == md
