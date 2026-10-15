# glycolens rules

- Public repo. Never commit health data, credentials, tokens or real readings: `tests/private/`,
  `~/.glycolens/`, `*.db` and `.creds_cache` stay out of git. Committed fixtures are synthetic.
- Plan: `docs/plans/2026-10-15-glycolens.md`. Spec: `docs/design.md`. Execution ledger (git-ignored):
  `.superpowers/sdd/2026-10-15-glycolens/progress.md` — tasks with a `complete` line are done.
- Python 3.14 via `.venv` (works under Smart App Control). Run tests with `.\.venv\Scripts\python -m pytest -q`.
- TDD per task: failing test, red, minimal code, green, commit. Commit and push to `origin/main` after
  each task passes; never force-push or rewrite history.
- glycolens never imports Noctis code. Noctis integration is a separate plan in the Noctis-OS repo.
- tconnectsync defaults to America/New_York and caches tokens on disk: set `TIMEZONE_NAME=Europe/London`
  and `CACHE_CREDENTIALS=false` before importing it. Credentials live only in Windows Credential Manager.
- The owner runs anything that needs their credentials or real data.
