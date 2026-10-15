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


def summarise(r: dict, url: str, model: str, timeout: float = 120) -> str | None:
    source = json.dumps({k: r[k] for k in ("stats", "findings", "suggestions", "watching", "changes")})
    body = {"model": model, "temperature": 0.2,
            "messages": [{"role": "system", "content": SYSTEM}, {"role": "user", "content": source}]}
    req = urllib.request.Request(f"{url}/v1/chat/completions", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            text = json.load(resp)["choices"][0]["message"]["content"]
    except (OSError, ValueError, KeyError, IndexError):
        return None
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.S).strip()
    return text if text and numbers_ok(text, source) else None


def for_config(r: dict, cfg) -> str | None:
    return summarise(r, cfg.lmstudio_url, cfg.model)
