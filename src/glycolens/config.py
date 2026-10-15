import tomllib
from dataclasses import dataclass, field
from pathlib import Path

from glycolens.windows import DEFAULT_WINDOWS, Window, parse_windows


@dataclass
class Config:
    home: Path = field(default_factory=lambda: Path.home() / ".glycolens")
    region: str = "EU"
    analysis_days: int = 14
    windows: tuple[Window, ...] = DEFAULT_WINDOWS
    lmstudio_url: str = "http://localhost:1234"
    model: str = "qwen3.5-9b"
    vault: Path | None = None  # off by default: the owner turns Vault notes on


def load_config(path: Path) -> Config:
    if not path.exists():
        return Config()
    raw = tomllib.loads(path.read_text(encoding="utf-8"))
    cfg = Config()
    for key in ("region", "analysis_days", "lmstudio_url", "model"):
        if key in raw:
            setattr(cfg, key, raw[key])
    if "home" in raw:
        cfg.home = Path(raw["home"])
    if "vault" in raw:
        cfg.vault = Path(raw["vault"])
    if "windows" in raw:
        cfg.windows = parse_windows(raw["windows"])
    return cfg
