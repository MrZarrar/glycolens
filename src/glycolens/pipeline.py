import sys
from datetime import datetime, timedelta

from glycolens import glooko, outcomes, report, store
from glycolens.analyse import analyse
from glycolens.config import Config
from glycolens.series import Series
from glycolens.stats import agp, summary, window_summary
from glycolens.suggest import current_settings, decide

STALE_AFTER = timedelta(days=2)


def run(cfg: Config, *, fetch, narrate, now: datetime) -> int:
    conn = store.open_store(cfg.home / "glycolens.db")
    error = None
    try:
        store.save(conn, fetch(cfg))
    except Exception as e:  # unofficial API: any failure means "carry on with what is stored"
        error = f"{type(e).__name__}: {e}"
    drop = cfg.home / "drop"
    drop.mkdir(parents=True, exist_ok=True)
    for path, data in glooko.import_drop(drop):
        store.save(conn, data)
        glooko.mark_imported(path)

    through = store.latest_glucose(conn)
    if through is None:
        print(f"glycolens: no data yet ({error or 'nothing fetched'})", file=sys.stderr)
        return 1
    if error:
        print(f"glycolens: fetch failed, using stored data: {error}", file=sys.stderr)
    stale = through if error or now - through > STALE_AFTER else None

    start, end = through - timedelta(days=cfg.analysis_days), through + timedelta(minutes=1)
    data = store.load(conn, start, end)
    series = Series(data.glucose)
    window_stats = {w.name: window_summary(series, w, start, end) for w in cfg.windows}
    findings = analyse(data, cfg.windows)
    outcomes.evaluate(conn, cfg.windows, now)
    suggestions, watching = decide(findings, window_stats, current_settings(data, cfg.windows),
                                   store.measuring_windows(conn, now), f"{through:%G-W%V}")
    for s in suggestions:
        store.add_suggestion(conn, s, now)

    r = report.build(now=now, start=start, end=end, through=through, stale_since=stale,
                     stats=summary(series.v, (end - start) / timedelta(minutes=1)), window_stats=window_stats,
                     agp=agp(series), findings=findings, suggestions=suggestions,
                     statuses={s.id: store.get_status(conn, s.id) for s in suggestions}, watching=watching,
                     changes=store.changes(conn), windows=cfg.windows)
    text = narrate(r, cfg)
    r["summary"], r["summary_source"] = (text, "qwen") if text else (report.template_summary(r), "template")
    report.write_json(r, cfg.home / "report.json")
    if cfg.vault:
        report.write_vault_note(r, cfg.vault)
    return 0


def decide_cmd(cfg: Config, sid: str, status: str, now: datetime) -> int:
    conn = store.open_store(cfg.home / "glycolens.db")
    try:
        previous = store.set_status(conn, sid, status, now)
    except KeyError:
        print(f"glycolens: no suggestion with id {sid!r}")
        return 2
    print(f"already {status}" if previous == status else f"{sid}: {previous} → {status}")
    report.update_status(cfg.home / "report.json", sid, status)
    return 0
