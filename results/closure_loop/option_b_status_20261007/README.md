# Option-B block closure status (2026-10-07)

`status.json` is the integration record of which blocks count as closed under the owner's option-B rule:
setup at TT (833.333 ps, >= 0) under the consistent die-link budget, hold at FF (>= 0), DRC 0. SS setup slack is
reported as a sensitivity only. The evidence is setup-triage's re-STA of existing final routes at 614782370
(`../tt_restatus_20261007.json`, `../tt_closed_list_20261007.json`); sha256 pins are in `status.json`.

- `closed`: 30 blocks closed at TT with the link budget applied.
- `unverified_forwarded_clock`: 16 forwarded-clock station blocks that pass TT setup without the common-clock split.
  They are held, not closed, until a per-link forwarded-clock model exists.
- `revoked_previously_closed`: 13 blocks the loop had closed at the SS line that fail at TT under the link budget.
  They no longer count as closed.
