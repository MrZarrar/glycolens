"""One-off spike: log in to Tandem Source and dump the event shapes glycolens needs.

Output is private health data and goes to tests/private/ (git-ignored).
Usage: python scripts/spike_tandem.py [EU|US]
"""
import getpass
import json
import os
import sys
from collections import Counter
from datetime import date, timedelta
from pathlib import Path

# tconnectsync reads these at import: pump clock is UK time (default is America/New_York), and the
# spike must not leave cached tokens behind.
os.environ.setdefault("TIMEZONE_NAME", "Europe/London")
os.environ["CACHE_CREDENTIALS"] = "false"

import keyring
from tconnectsync.api.tandemsource import TandemSourceApi

WANT = {
    "LidCgmDataG7", "LidBolusRequestedMsg1", "LidBolusRequestedMsg2", "LidBolusCompleted",
    "LidBasalDelivery", "LidCannulaFilled", "LidAaUserModeChange",
}


def fields(e):
    out = {}
    for k in dir(e):
        if k.startswith("_"):
            continue
        try:  # computed properties (e.g. carbRatio) raise when their raw field is missing
            v = getattr(e, k)
        except Exception as exc:
            v = f"<{type(exc).__name__}>"
        if not callable(v):
            out[k] = repr(v)
    return out


def main():
    region = sys.argv[1] if len(sys.argv) > 1 else "EU"
    raw = keyring.get_password("glycolens", "tandem")  # same entry Task 11's login() writes
    if raw:
        creds = json.loads(raw)
        email, password = creds["email"], creds["password"]
    else:
        email, password = input("Tandem Source email: "), getpass.getpass("Password: ")
    api = TandemSourceApi(email, password, region)
    pumps = api.get_pumper()["pumps"]
    if not pumps:
        sys.exit("No pumps returned for this account.")
    print("pumps:", len(pumps), "keys:", sorted(pumps[0]))
    p = pumps[0]
    print("data range:", p.get("availableDataRange"), "maxDateOfEvents:", p.get("maxDateOfEvents"),
          "lastUpload:", p.get("lastUploadDate"), p.get("lastUploadClientType"))
    # The window ends at the pump's last uploaded event, not today: a pump that hasn't synced lately
    # returns nothing for "the last 3 days".
    last = p.get("maxDateOfEvents")
    end = date.fromisoformat(last[:10]) if last else date.today()
    events = list(api.pump_events(pumps[0]["assignmentId"], min_date=(end - timedelta(days=3)).isoformat(),
                                  max_date=end.isoformat(), fetch_all_event_types=True))
    print(Counter(type(e).__name__ for e in events).most_common(40))
    samples = {}
    for e in events:
        name = type(e).__name__
        if name in WANT and name not in samples:
            samples[name] = fields(e)
    print("\nBoluses (compare with the t:slim app history to spot Control-IQ auto-boluses):")
    for e in events:
        name = type(e).__name__
        if name == "LidBolusRequestedMsg1":
            print(name, e.bolusId, e.bolusTypeRaw, e.carbAmount, e.carbRatioRaw)
        elif name == "LidBolusCompleted":
            print(name, e.bolusId, e.insulinDelivered)
    out = Path("tests/private")
    out.mkdir(parents=True, exist_ok=True)
    (out / "tandem_samples.json").write_text(json.dumps(samples, indent=2))
    print("\nwrote tests/private/tandem_samples.json")


if __name__ == "__main__":
    main()
