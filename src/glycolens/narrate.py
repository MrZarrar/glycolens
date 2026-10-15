"""Optional plain-English summary from the local Qwen model in LM Studio.

The model only rewords the findings; numbers_ok() rejects any number it did not get from them.
"""
import json
import re
import urllib.request

NUMBER = re.compile(r"\d+(?:\.\d+)?")
SYSTEM = ("Write a 3 to 5 sentence weekly summary of this type 1 diabetes pattern report for the person "
          "it is about. Use only facts and numbers from the JSON. Do not add advice beyond the listed "
          "suggestions. Plain text, no headings.")


def _numbers(text: str) -> set[str]:
    return {f"{float(n):g}" for n in NUMBER.findall(text)}


def numbers_ok(summary: str, source: str) -> bool:
    return _numbers(summary) <= _numbers(source)


def source(r: dict) -> str:
    """What the model may restate: the headline numbers and the deterministic sentences. No evidence lines or
    ids, whose many small numbers would let an invented figure pass numbers_ok."""
    return json.dumps({
        "stats": r["stats"],
        "findings": [f["text"] for f in r["findings"]],
        "suggestions": [s["text"] for s in r["suggestions"]],
        "watching": [f"{w['window']} {w['rule']}: {w['reason']}" for w in r["watching"]],
        "changes": [{k: c[k] for k in ("window", "setting", "current", "proposed", "outcome")} for c in r["changes"]],
    })


def summarise(r: dict, url: str, model: str, timeout: float = 120) -> str | None:
    source_text = source(r)
    body = {"model": model, "temperature": 0.2,
            "messages": [{"role": "system", "content": SYSTEM}, {"role": "user", "content": source_text}]}
    req = urllib.request.Request(f"{url}/v1/chat/completions", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            text = json.load(resp)["choices"][0]["message"]["content"]
    except (OSError, ValueError, KeyError, IndexError):
        return None
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.S).strip()
    return text if text and numbers_ok(text, source_text) else None


def for_config(r: dict, cfg) -> str | None:
    return summarise(r, cfg.lmstudio_url, cfg.model)
