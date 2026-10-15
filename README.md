# glycolens

Weekly pattern finder for my own t:slim X2 + Dexcom G7 data. Personal, non-commercial, not medical
advice. Design: `docs/design.md`.

## Use

From the repo, with the venv (`py -3.14 -m venv .venv; .\.venv\Scripts\python -m pip install -e .`):

    .\.venv\Scripts\python -m glycolens.cli login            # once: saves the Tandem Source login to Windows Credential Manager
    .\.venv\Scripts\python -m glycolens.cli run              # fetch the last 14 days, analyse, write ~/.glycolens/report.json
    .\.venv\Scripts\python -m glycolens.cli mark-applied ID  # after changing the pump setting; dismiss ID / reset ID also exist

Manual fallback: drop a Glooko "Export to CSV" zip into `~/.glycolens/drop/`.
Weekly: Noctis runs it from its home node. Without Noctis, `scripts/register-weekly.ps1` registers a
Windows Task Scheduler job (Sundays 20:00).

## How it decides

Deterministic rules over 14 days of data (carb ratio, correction factor, basal vs Control-IQ delivery,
pre-bolus timing, exercise lows). Guardrails: lows win, steps of at most 10%,
one change per window at a time, at least 4 qualifying events, 70% CGM coverage. A local LLM may reword
the summary; any number it did not get from the findings discards its text.

Personal tool, not medical advice.
