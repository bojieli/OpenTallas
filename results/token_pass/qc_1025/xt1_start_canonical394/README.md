# QC token pass: xt1 both-cluster + die START broadcast on the CANONICAL START-plan bind (source main 394765394), 2026-10-25

Reproduces `../xt1_start_broadcast` (receipt 1a6dbd1f6, proof bind) on the fresh plan-of-record bind. PATH-QC-TOK.

## What was bound
- Plan = codex/qc-start-plan-0719@1c0e347be4 `physical/die_plan/qwen_compute/die_plan.json`, sha256
  ce2406b9ebbaa38f2632122d3634c4614c037da3ba5db1d7016c731f1be92720 (main QC plan 0719 + `reset.start = "broadcast"`).
- Source = main 394765394378 (immutable copy, `bind/rebind_plan.sh`, Codex unit oth-ubuntu-3819982-1792940294 on epyc1,
  root /srv/opentallas-scratch2/claude/codex-qc-token-current-0719/plan_canonical_394_start). probe / R8 base / final bind:
  0 errors, 377 partitions, 76 types, 1,933 crossings, 792,661 bits, 0 unbound/tied/undriven/multiply-bound.
  Verify PASS: 2,723,884 compared, 0 mismatched (14 glue_unmatched, as the proof bind), lint 0. regen_constants 22/22 OK
  (`bind/constants.json`; XT1_FILL_LEAD_OFFSET 16 -> lead 24).
- Reset/START: wavefront root sl_W0_ctl, latest partition release 128, core-pin release 129, calendar delay 130 (same as the
  proof bind). The plan-0719 wavefront moves the omitted-carrier ages (rstw/stw c_W4_tf_00 101, sl_W4_fw 72/72, sl_W4_st_b 71;
  was 90/83/75/74/72), so the carve boundary differs while the kept 22 partitions and the 108 closure files are the same.
- Carve = bind_smoke.py (main 394765394) `--clusters both`, `prep.sh`, `stage.json`, `carve/`.

## Result (epyc3 ot-run unit oth-ubuntu-2396521-1792941987, 90 GB; build 39.3 min / 75.9 GiB peak, 5 sims 23.3 min)
| run | calendar | near / far | verdict |
|-----|----------|------------|---------|
| nominal START_AT 200 | 330 | **64/64 + 64/64** | PASS |
| hr lane +1 mutant | 330 | 64/64 + 64/64 numerically | caught by the strict schedule gate (16 edge groups move) -> `results/schedule_gate.json` PASS |
| negative: calendar at S | 200 | 0/64 + 0/64 | FAIL as required |
| negative: start never rises | 330 | 0/64 + 0/64 | FAIL as required |
| margin: calendar 1 clock early | 329 | 64/64 + 64/64 | not a failure (contract delay 130 is conservative, as before) |

The xt1n edge records (log_m0/log_m1 .xt1n.json), check_m0, the margin probe and schedule_gate.json are **byte-identical** to
the proof-bind receipt: the canonical START plan computes the xt1 stage with the same cycles (0 cycles/token for START).

## Scope
xt1 carve (22 W5 partitions) of the bound top, not a whole-die token pass. It excludes glue/native59/coll_f4/ucie_kv, which
the exact-path run (PATH-QC T1 plan, lanes/PATH-QC.md) must add; that run is blocked by the START bootstrap deadlock (CLOCK)
and by the hard-PHY line side not being exported by the binder on either die.
