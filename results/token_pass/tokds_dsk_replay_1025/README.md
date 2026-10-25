# TOK-DS deskew-cut NX replays (2026-10-25)

L0 entry/norm NX arithmetic phase on the fc31 deskew cuts (XRT `ec43bbd4`). Mechanism evidence only: the cuts predate the
adopt178 plan (7c33a7a81). Verdicts: `verdict.json`. Scripts: `replay_dsk.sh`, `entry_ec43.sh` (run on epyc3 via ot-run).

- Recompiled L0 against `root31dsk` (root30 + the ec43 XRT, the only file that differs from the kit). The extracted phase is
  identical to Codex's `codex_nx138` vehicle (4298 events, 240 NX), and only the XRT contract changes (`nx_compare.json`).
- cut_0S on ec43: the base sim passes with 15/15 NX words at 2517 cycles and 0 mismatches. The input-corrupt mutant is caught
  (2 mismatches, 248 fault cycles).
- cut_0N on ec43: base 15/15 NX words at 2518 cycles, 0 mismatches; input-corrupt mutant caught (2 mismatches, 249 fault cycles).
- The strict check on every run is blocked by the guard `HOST/control runtime proof remains PENDING`. The native ec43 entry
  proof is blocked: the entry mechanism receipt pins TB files that exist on no fleet host.
- 05:53 STRICT RESULT: fresh ec43 native-HOST entry proof (receipt from benches regenerated in-repo on claude/tok-ds-entry-1025,
  strict entry_boot, jobs 15/16/17/20/21/22 PASS, hf_7N bit33 control CAUGHT -> `entry_ec43c/entry_replay.json`).
  With it as OT_S81_XRT_RUNTIME_PROOF the strict check COUNTS: cut_0S base PASS (15/15 NX, 2,517 cyc), cut_0N base PASS
  (15/15, 2,518 cyc); input-corrupt and expect-shift controls FAIL on both (`strict/`). Scope unchanged: L0 NX arithmetic
  phase on the fc31 deskew cuts (pre-adopt178), mechanism evidence, not a full layer/token.
