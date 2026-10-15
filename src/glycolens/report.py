import json
import os
from datetime import datetime, timedelta
from pathlib import Path

from glycolens.findings import Finding
from glycolens.store import iso
from glycolens.suggest import STEP, Suggestion, Watching

SCHEMA_VERSION = 1
LABELS = {"carb_ratio": ("carb ratio", "g/U"), "isf": ("correction factor", "mmol/L per U"), "basal": ("basal", "U/h")}


def _hhmm(minutes: int) -> str:
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def finding_text(f: Finding) -> str:
    w = f.window.capitalize()
    if f.rule == "carb_ratio" and f.direction == "stronger":
        return f"{w}: {f.hits} of {f.events} meals ended high (median +{f.metric:.1f} mmol/L at 4h)."
    if f.rule == "carb_ratio":
        return f"{w}: {f.hits} of {f.events} meals went low within 4h (lowest {f.metric:.1f})."
    if f.rule == "pre_bolus":
        return (f"{w}: {f.hits} of {f.events} meals spiked (median +{f.metric:.1f}) then came back down. "
                f"The ratio looks right; bolus earlier.")
    if f.rule == "isf":
        return f"{w}: corrections dropped {f.metric:.1f}x what your correction factor predicts ({f.hits} of {f.events})."
    if f.rule == "basal":
        return f"{w}: on {f.hits} of {f.events} fasting days basal ran at {f.metric:.0%} of programmed or glucose drifted."
    if f.rule == "missed_bolus":
        return f"{w}: {f.hits} rises of 3+ mmol/L in an hour with no bolus logged."
    if f.rule == "exercise_low":
        return f"Lows after {f.hits} of {f.events} exercise sessions (lowest {f.metric:.1f})."
    return f"Glucose ran {f.metric:.1f} mmol/L higher from day 3 of a site."


def suggestion_text(s: Suggestion) -> str:
    label, unit = LABELS[s.setting]
    verb = "strengthening" if s.direction == "stronger" else "weakening"
    return (f"{s.window.capitalize()}: consider {verb} your {label} from {s.current:g} to {s.proposed:g} {unit} "
            f"({STEP:.0%}).")


def build(*, now: datetime, start: datetime, end: datetime, through: datetime, stale_since: datetime | None, stats: dict,
          window_stats: dict, agp: list, findings: list[Finding], suggestions: list[Suggestion],
          statuses: dict, watching: list[Watching], changes: list[dict], windows) -> dict:
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": iso(now),
        "period": {"start": iso(start), "end": iso(end), "days": round((end - start) / timedelta(days=1))},
        "data_through": iso(through),
        "stale_since": iso(stale_since) if stale_since else None,
        "summary": "",
        "summary_source": "template",
        "stats": stats,
        "windows": [{"name": w.name, "start": _hhmm(w.start), "end": _hhmm(w.end), **window_stats[w.name]}
                    for w in windows],
        "agp": agp,
        "findings": [{"rule": f.rule, "window": f.window, "direction": f.direction, "events": f.events,
                      "hits": f.hits, "metric": f.metric, "text": finding_text(f), "evidence": list(f.evidence)}
                     for f in findings],
        "suggestions": [{"id": s.id, "window": s.window, "setting": s.setting, "direction": s.direction,
                         "current": s.current, "proposed": s.proposed, "step_pct": round(STEP * 100),
                         "text": suggestion_text(s), "evidence": list(s.evidence),
                         "status": statuses.get(s.id) or "proposed"} for s in suggestions],
        "watching": [{"window": w.window, "rule": w.rule, "reason": w.reason} for w in watching],
        "changes": changes,
    }


def template_summary(r: dict) -> str:
    st = r["stats"]
    return (f"Last {r['period']['days']} days: {st['tir']}% in range, {st['tbr']}% below. "
            f"{len(r['findings'])} findings, {len(r['suggestions'])} suggestions.")


def write_json(r: dict, path: Path) -> None:
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(r, indent=2), encoding="utf-8")
    os.replace(tmp, path)  # readers see the old or the new file, never half of one


def update_status(path: Path, sid: str, status: str) -> None:
    if not path.exists():
        return
    r = json.loads(path.read_text(encoding="utf-8"))
    for s in r["suggestions"]:
        if s["id"] == sid:
            s["status"] = status
    write_json(r, path)


def to_markdown(r: dict) -> str:
    day = r["data_through"][:10]
    st = r["stats"]
    lines = ["---", f"title: glycolens weekly {day}", "tags: [health, glycolens]", f"created: {day}",
             "source: noctis-health", "---", ""]
    if r["stale_since"]:
        lines += [f"> Data stale since {r['stale_since'][:10]}.", ""]
    lines += [r["summary"], "",
              f"**Stats:** {st['tir']}% in range, {st['tbr']}% below, GMI {st['gmi']}%, CV {st['cv']}%", ""]
    lines += ["## Findings"] + [f"- {f['text']}" for f in r["findings"]] + [""]
    lines += ["## Suggestions"] + [f"- {s['text']} ({s['status']})" for s in r["suggestions"]] + [""]
    lines += ["## Past changes"] + [f"- {c['window']} {c['setting']} {c['current']:g} → {c['proposed']:g}: "
                                    f"{c['outcome']}{'' if c['outcome_final'] else ' (provisional)'}"
                                    for c in r["changes"]]
    return "\n".join(lines) + "\n"


def write_vault_note(r: dict, vault_root: Path) -> Path:
    path = vault_root / "inbox" / f"{r['data_through'][:10]}-glycolens-weekly.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(to_markdown(r), encoding="utf-8")
    return path
