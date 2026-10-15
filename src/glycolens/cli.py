import argparse
from datetime import datetime
from pathlib import Path

from glycolens import narrate, pipeline, tandem
from glycolens.config import load_config

STATUS = {"mark-applied": "applied", "dismiss": "dismissed", "reset": "proposed"}


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="glycolens", description="Weekly t:slim X2 + G7 pattern finder.")
    p.add_argument("--config", type=Path, default=Path.home() / ".glycolens" / "config.toml")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("run", help="fetch, analyse and write report.json")
    sub.add_parser("login", help="save the Tandem Source login to Windows Credential Manager")
    for name in STATUS:
        sub.add_parser(name).add_argument("id")
    a = p.parse_args(argv)
    cfg = load_config(a.config)
    if a.cmd == "run":
        return pipeline.run(cfg, fetch=tandem.fetch, narrate=narrate.for_config, now=datetime.now())
    if a.cmd == "login":
        tandem.login()
        return 0
    return pipeline.decide_cmd(cfg, a.id, STATUS[a.cmd], datetime.now())


if __name__ == "__main__":
    raise SystemExit(main())
