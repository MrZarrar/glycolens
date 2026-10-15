import json
from datetime import timedelta

import synth
from glycolens import pipeline, store
from glycolens.config import Config, load_config

NOW = synth.START + timedelta(days=synth.DAYS)


def cfg(tmp_path, **kw):
    return Config(home=tmp_path, **kw)


def no_summary(r, c):
    return None


def failing_fetch(c):
    raise ConnectionError("Tandem said no")


def test_run_writes_a_report_with_a_suggestion(tmp_path):
    assert pipeline.run(cfg(tmp_path), fetch=lambda c: synth.make("weak_breakfast"), narrate=no_summary, now=NOW) == 0
    r = json.loads((tmp_path / "report.json").read_text())
    assert r["stale_since"] is None and r["summary_source"] == "template"
    assert [s["id"] for s in r["suggestions"]] == ["2026-W03-breakfast-carb_ratio"]


def test_rerun_keeps_status_and_does_not_duplicate(tmp_path):
    c = cfg(tmp_path)
    pipeline.run(c, fetch=lambda c: synth.make("weak_breakfast"), narrate=no_summary, now=NOW)
    assert pipeline.decide_cmd(c, "2026-W03-breakfast-carb_ratio", "applied", NOW) == 0
    pipeline.run(c, fetch=lambda c: synth.make("weak_breakfast"), narrate=no_summary, now=NOW)
    r = json.loads((tmp_path / "report.json").read_text())
    assert r["suggestions"] == [] and r["watching"][0]["reason"] == "measuring an applied change"
    conn = store.open_store(tmp_path / "glycolens.db")
    assert conn.execute("select count(*) from suggestion").fetchone()[0] == 1


def test_decide_updates_the_report_and_rejects_unknown_ids(tmp_path, capsys):
    c = cfg(tmp_path)
    pipeline.run(c, fetch=lambda c: synth.make("weak_breakfast"), narrate=no_summary, now=NOW)
    assert pipeline.decide_cmd(c, "2026-W03-breakfast-carb_ratio", "applied", NOW) == 0
    assert json.loads((tmp_path / "report.json").read_text())["suggestions"][0]["status"] == "applied"
    assert pipeline.decide_cmd(c, "2026-W03-breakfast-carb_ratio", "applied", NOW) == 0
    assert "already applied" in capsys.readouterr().out
    assert pipeline.decide_cmd(c, "typo", "applied", NOW) == 2


def test_first_run_with_failing_fetch_writes_nothing(tmp_path, capsys):
    assert pipeline.run(cfg(tmp_path), fetch=failing_fetch, narrate=no_summary, now=NOW) == 1
    assert not (tmp_path / "report.json").exists()
    assert "Tandem said no" in capsys.readouterr().err


def test_failing_fetch_with_stored_data_marks_report_stale(tmp_path):
    c = cfg(tmp_path)
    pipeline.run(c, fetch=lambda c: synth.make(), narrate=no_summary, now=NOW)
    pipeline.run(c, fetch=failing_fetch, narrate=no_summary, now=NOW + timedelta(days=7))
    r = json.loads((tmp_path / "report.json").read_text())
    assert r["stale_since"] == r["data_through"]


def test_qwen_summary_used_when_it_passes(tmp_path):
    pipeline.run(cfg(tmp_path), fetch=lambda c: synth.make(), narrate=lambda r, c: "All steady.", now=NOW)
    r = json.loads((tmp_path / "report.json").read_text())
    assert (r["summary"], r["summary_source"]) == ("All steady.", "qwen")


def test_vault_note_only_when_configured(tmp_path):
    vault = tmp_path / "vault"
    pipeline.run(cfg(tmp_path / "a"), fetch=lambda c: synth.make(), narrate=no_summary, now=NOW)
    assert not vault.exists()
    pipeline.run(cfg(tmp_path / "b", vault=vault), fetch=lambda c: synth.make(), narrate=no_summary, now=NOW)
    assert len(list((vault / "inbox").glob("*-glycolens-weekly.md"))) == 1


def test_config_defaults_and_windows(tmp_path):
    assert load_config(tmp_path / "missing.toml").analysis_days == 14
    p = tmp_path / "c.toml"
    p.write_text('region = "US"\n[[windows]]\nname = "all"\nstart = "00:00"\nend = "24:00"\n')
    c = load_config(p)
    assert c.region == "US" and [w.name for w in c.windows] == ["all"]


def test_cli_output_survives_a_piped_windows_console(tmp_path):
    # Noctis and the scheduled task read glycolens through a pipe, where Windows defaults to cp1252.
    import os
    import subprocess
    import sys
    pipeline.run(cfg(tmp_path), fetch=lambda c: synth.make("weak_breakfast"), narrate=no_summary, now=NOW)
    (tmp_path / "c.toml").write_text(f'home = "{tmp_path.as_posix()}"\n')
    env = {k: v for k, v in os.environ.items() if k not in ("PYTHONIOENCODING", "PYTHONUTF8")}
    done = subprocess.run([sys.executable, "-m", "glycolens.cli", "--config", str(tmp_path / "c.toml"),
                           "mark-applied", "2026-W03-breakfast-carb_ratio"], capture_output=True, env=env)
    assert done.returncode == 0, done.stderr.decode(errors="replace")
    assert "→" in done.stdout.decode("utf-8")


def test_run_lists_a_recovered_sensor_plunge(tmp_path):
    from glycolens.model import Glucose
    d = synth.make()
    t = synth.START + timedelta(days=3, hours=14)
    gap = {t - timedelta(minutes=m) for m in (5, 10, 15)}
    d.glucose = [Glucose(g.ts, 2.4) if g.ts == t else g for g in d.glucose if g.ts not in gap]
    pipeline.run(cfg(tmp_path), fetch=lambda c: d, narrate=no_summary, now=NOW)
    r = json.loads((tmp_path / "report.json").read_text())
    assert r["possible_sensor_lows"] == [t.isoformat(timespec="seconds")]
