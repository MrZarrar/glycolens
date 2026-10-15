# Spike results (2026-10-15)

Field names, scales, units and status codes only. No readings, doses or settings values.

- Interpreter that works: .venv (py -3.14 -m venv; pip install -e ".[dev]" and pytest ran under Smart App Control, 2026-10-15)
- tconnectsync version: 3.0.3
- Region that logs in: EU
- Pumps returned: 1 (`get_pumper()["pumps"]`; keys include `assignmentId`, `availableDataRange`, `maxDateOfEvents`, `lastUploadDate`)
- Sync window: end it at the pump's `maxDateOfEvents`, not today. A pump that has not uploaded returns no events of any type for "the last N days". A late USB upload back-fills old days, so re-fetch recent days and de-duplicate on `seqNum`.
- Timestamp: `eventTimestamp` is a tz-aware Arrow in `TIMEZONE_NAME` (Europe/London; it shows `+01:00` in BST). `.naive` gives the pump's local wall-clock time. Set `TIMEZONE_NAME` before importing tconnectsync.
- `carbRatioRaw` scale: 1000 (raw ÷ 1000 = g/U; the `carbRatio` property already applies it; owner confirmed the values match their pump ratios). `carbRatioRaw` is 0 on auto-boluses.
- `LidBolusRequestedMsg2.isf` unit: mg/dL per U (stored alongside `targetBg` in mg/dL, whatever unit the pump displays).
- Control-IQ auto-bolus: it has a request message. `LidBolusRequestedMsg1.bolusTypeRaw == 2` ("Automatic Correction"; 0 Insulin, 1 Carb, 3 Remote). It is a plain enum, not bits. `LidBolusRequestedMsg2.optionsRaw == 3` ("Automatic Bolus") also marks it. User boluses are type 1. With `carbAmount > 0`, Tandem Source shows them as Food, Food + Correction or Override Decrease. With `carbAmount == 0`, it shows them as Override Increase, which is the owner's manual correction. Checked by the owner against Tandem Source for one full day (2026-10-12): every type 2 bolus showed as "Automatic Correction". Tandem's "(2)" markers are an auto-bolus and a user bolus at the same time.
- `LidBolusCompleted.completionStatusRaw`: 3 = Completed (0 User Aborted, 1 Terminated by Alarm, 2 Terminated by Malfunction). `insulinDelivered` is in U.
- `LidCannulaFilled.completionStatusRaw` on a successful fill: 3 (same map as bolus completion).
- `LidAaUserModeChange` present when exercise mode is used? Events are present (sleep start/stop seen). `currentUserModeRaw` / `previousUserModeRaw`: 0 Normal, 1 Sleeping, 2 Exercising, 3 Eating Soon. The owner doesn't use exercise mode yet, so `2` comes from tconnectsync's enum and hasn't been seen in real data.
- Basal (`LidBasalDelivery`): `profileBasalRate`, `commandedRate`, `algorithmRate` are in milli-units/h (÷ 1000 = U/h). `tempRate == 65535` means no temp rate. `commandedRateSourceRaw`: 0 Suspended, 1 Profile, 2 Temp Rate, 3 Algorithm.
- CGM (`LidCgmDataG7`): `currentGlucoseDisplayValue` is in mg/dL. `glucoseValueStatusRaw`: 0 Precise, 1 Special High, 2 Special Low, 6 Do Not Show. `cgmDataTypeRaw` bit 0 = five-minute reading, bit 1 = backfill.
- Every event carries `seqNum` (a monotonic pump sequence number), which is a natural de-duplication key.

## Acceptance (2026-10-15, owner's real data)

Stats match Tandem Source's own report for the same fortnight within about 2 points (TIR, TBR, GMI, CV, CGM use).
Corrections made after the first real run:

- CGM time comes from `LidCgmDataG7.egvTimeStamp`: seconds since 2008-01-01, pump local time (`timestampRaw` uses the same epoch). Back-filled readings reach the pump late, and `eventTimestamp` is their arrival time. Using `eventTimestamp` lost about 10% of readings.
- `glucoseValueStatusRaw` 1/2 (G7 shows HIGH/LOW) count as 22.2 / 2.2 mmol/L instead of being dropped.
- `LidBolusRequestedMsg2.userOverrideRaw == 1` means the user changed the calculated dose. The owner often boluses food as an Override Increase with 0 carbs. Overridden boluses don't judge carb ratio or correction factor.
- Correction factor is scored at 5 h, the pump's insulin duration.
- Rules dropped because they inferred a cause from glucose alone (food, illness and anaerobic exercise look the same): missed bolus, site age, and basal judged on glucose drift.
- Open: the owner trains on weekday evenings without exercise mode, so dinner and late findings may be confounded.
