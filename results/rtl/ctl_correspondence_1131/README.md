CTL source aliases and correspondence replay

This opt-in hint plan closes the actual ctlin_C mapped comparison without another random correspondence search. Its preseed entries are untrusted candidates from the earlier twelve-hint run; the 505 post entries preserve the source aliases after that context is proved. `discovery_rounds: 0` runs ordinary initialization, reset filtering, induction and refinement. Every post hint and final compare/KEEP obligation is still checked. Unknown or invalid candidates are skipped or dropped by the existing prover.

Use `gen_core_kit_kv.py --lec-hints hint_plan.json` with a tool advertising `hint_plan_schema: opentallas.lec_hint_plan.v1`. The generator already stages this as `KIT/lec_hints.json`; no extra environment option or wrapper is required.

Actual standard CLI control: EPYC2 `/srv/opentallas-scratch2/claude/codex-kv-ctl-hintplan-1131`.

- Positive: EQUIVALENT, 46453/46453 normal compare points, 171.7 s.
- Negative: invert only mapped output-capture D for `o_hroot_EN[20]`; NOT EQUIVALENT, exactly that normal output differs, 46452/46453 proved, 150.0 s.
- Parser compatibility and rejection tests: 8 passed.

The source profile is the concrete boot+2/mission+0 ctlin_C RTL SHA256 `153b42177610e6839691156cd0c8d9169ba07feac7e087cdf162fcfe3f16c73a`, with 6849 pins. These are diagnostic mapped receipts; their experimental freeze is invalid. A fresh production GEN/freeze and the current reset-base/cons soundness fixes are required before physical qualification or signoff. Parent native-to-profile composition remains a separate held obligation.
