# QC token pass: xt1 both-cluster with the die START broadcast (OWNER DECISION 13c), 2026-10-25

Collected by QC-TOK3 from the run QC-TOK2 launched (epyc3:/srv/opentallas-scratch2/claude/qc-tok-start-1025/both,
`prep.sh`, ot-run unit `bash run_smoke.sh`, 90 GB). Nothing was rerun; the strict schedule gate was applied to the untouched logs.

## What was bound
- Plan = main's `physical/die_plan/qwen_compute/die_plan.json` (sha256 d27c3788...) **plus `reset.start = "broadcast"`**
  (sha256 61d89c14...; a JSON diff shows only `/reset/start`). This is the per-die delta CLOCK-RESET posted (READY 05:01); the
  QC plan owner still has to fold it into the committed plan.
- Bind = CLOCK-RESET proof epyc3:/srv/opentallas-scratch2/claude/clock-reset/start/qc_bind (`bind/`: recipe = the CB16 r3
  recipe with a new base, bind_report, bind_reset, verify_report). Tools = claude/clock-reset-1025 (the e84452a8fd opt-in START
  is in main; d2d03fe94 ot_dp_rgate gated taps is on that branch). 377 partitions, 1,933 crossings, 792,661 bits, 0 errors,
  0 unbound/tied/undriven; verify PASS (2,723,884 compared, 0 mismatched). 373 soft partitions get start_i; the 4 hard PHYs keep
  raw reset.
- Reset/START (`bind/bind_reset.json`): wavefront root sl_W0_ctl, latest partition release 128, latest core-pin release 129;
  start block = mode broadcast, die pin `start`, 2-flop sync. A partition's control state releases at S + its published release.
- Carve (`carve/`, tool = bind_smoke.py e0e0da544, `stage.json`: 87 closure files, 0 unresolved): both W5 clusters
  (22 partitions) with live partition reset AND run RTL. The 5 omitted carriers are driven at their published ages, the reset
  and START carriers alike (rstw_*/stw_* 72/74/75/83/90 edges). The carve fails closed: a start_i with no start block, a kept
  partition missing start_i, a START carrier that is not beside its reset carrier, or any rstw_/stw_ net with no age is a hard
  error, never tied to zero (unit tests in tools/die_plan/test_bind_smoke_wavefront.py, 10/10 PASS). The bench-lane epoch loads
  rst_n AND start.
- Bench: rst_n deasserts, the die start pin rises S = 200 clocks later, and the calendar begins at S + 130 = 330
  (latest published release 129 + 1).

## Result
| run | calendar | near / far | verdict |
|-----|----------|------------|---------|
| nominal (START_AT 200) | 330 | **64/64 + 64/64 exact** | PASS |
| hr lane +1 mutant | 330 | 64/64 + 64/64 numerically | **caught** by the strict schedule gate (fixed-consumer edges move) -> `results/schedule_gate.json` PASS |
| negative: calendar at S (start broadcast ignored) | 200 | **0/64 + 0/64** | FAIL as required (FAULT heads at 200) |
| negative: start pin never rises | 330 | **0/64 + 0/64** | FAIL as required |
| margin probe: calendar 1 clock early | 329 | 64/64 + 64/64, edges unchanged | not a failure: the contract delay of 130 is conservative on this carve, as `../xt1_wf_early` showed (calendar 100 after reset passed) |

Measured relative to the calendar start, every cw_go and result edge is identical to the wavefront r3 pass (`../xt1_wavefront_r3`).
START therefore costs 0 cycles per token; the only cost is the one-time boot of S + 130 clocks.
Build 45.9 min wall / 79.5 GB peak (Verilator 5.050); each sim takes about 4.5 min.

## Scope
This is the xt1 carve of the bound top, not a whole-die token pass. tp8 with the START pin is in `../tp8_wavefront` (S=60 3/3
PASS + 2/2 early-start FAIL). Before this counts as the plan of record, the QC plan must carry `reset.start = "broadcast"` (plan
owner batch), and the soft types must be re-kitted once.
