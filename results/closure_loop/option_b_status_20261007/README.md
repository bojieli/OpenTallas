# Option-B block closure status (2026-10-07, v2)

`status.json` records which blocks count as closed under the owner's option-B rule: setup at TT (833.333 ps, >= 0)
under the consistent die-link budget (per-link source-synchronous model for forwarded-clock station links), hold at FF
(>= 0), DRC 0. SS setup is a sensitivity only. Evidence: setup-triage 254ef7315 (`../tt_restatus_20261007.json`,
`../tt_closed_list_20261007.json`, v2 with the corrected link-budget check); sha256 pins in `status.json`.

- `closed`: 42 blocks (31 common-clock with the consistent split, 11 forwarded-clock stations under the per-link model).
- `unverified_forwarded_clock`: forwarded-clock blocks not yet decided by the per-link model.
- `revoked_previously_closed`: 17 blocks the loop had closed at the SS line that are not closed at TT; they no longer
  count as closed.

v1 (fc5ee68fd: 30 closed / 16 held / 13 revoked) is superseded.
