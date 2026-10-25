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

## cut_7 (TOK-DS3, 2026-10-25 06:40 PDT)
- Build: inherited make (ot-vl-jcap capped it to -j4 at the 30 GB/cc1plus default) stopped by exact PID and resumed in the same
  obj dir at -j32 (OT_VL_JCAP=0, --mem 230 = 32 x measured 6.85 GB cc1plus peak), epyc3 unit oth-ubuntu-738007-1792934347, make rc 0.
- Replay: replay_dsk.sh nx cuts cut_7, PROOF=entry_ec43c/entry_replay.json, epyc3 unit oth-ubuntu-1044559-1792935140.
  base: sim PASS, 2,513 cycles, 4,103 input events, 15/15 out checks, 0 mismatches; strict check PASS (15/15 ports, 4,863
  expected changes, xrt_runtime_proof ENTRY entry_ec43c). mut_in corrupt:xrE_6S_l0:91:14: sim FAIL, 2 mismatches, first fault 2268
  = CAUGHT (13/15 ports ok). mut_ex expect-shift:NX:1: 32 trace mismatches = CAUGHT (11/15 ports ok). Sim wall 2:42, RSS 0.7 GB.
- The first check pass crashed (TypeError: keywords must be strings) in the WIP check tool of epyc3 worktree codex-tok-ds-1025
  (uncommitted on 7e0b8a97a): the link-framing branch built dict(exp, **{tuple keys}). One-line fix (cut_7_check_fix.diff,
  {**exp, **{...}}; only the expected-count bookkeeping) applied there; checks rerun on the same sim runs (no new sims).
  main's dv_cut_replay.py does not have this line. cut_7 is the first cut whose ports carry link framing.
- Scope unchanged: component evidence, pre-adopt178 deskew cuts, full_token false.
