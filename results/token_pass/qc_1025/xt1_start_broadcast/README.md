# QC token pass: xt1 both-cluster on the START-broadcast bound top (2026-10-25)

Owner decision 13c: the static schedule starts on an explicit START broadcast after the reset wavefront.

## Bind used
- epyc3:/srv/opentallas-scratch2/claude/clock-reset/start/qc_bind (CLOCK-RESET, claude/clock-reset-1025@e84452a8fd;
  `bind_report.json`, `bind_reset.json`, `qc_recipe.json` copied here). 377 partitions, 1,933 crossings, 0 errors.
- Plan = main's `physical/die_plan/qwen_compute/die_plan.json` + `reset.start = "broadcast"` only (diffed: one key).
  Recipe = wavefront_r3 `recipe.json` except `base` (the clock-reset source tree).
- `bind_reset.json` start block: die pin `start`, one START 2-flop synchroniser beside the root reset synchroniser,
  start_i / start_o_<k> beside arst_n / rst_o_<k>, run relays on the reset relay sites, every tap = registered reset AND
  run. Reset wavefront unchanged: latest partition release 128, latest hard-core pin 129.

## Vehicle (tools/die_plan/bind_smoke.py, claude/qc-tok-start-1025)
- Same carve as `../xt1_wavefront_r3` (22 W5 partitions, 32 ROM tiles, 108 closure files, same source rev bc11ef2db,
  same inputs/bench, lead 24 gap 4); the only source difference is the START-bound partition RTL.
- New when the bind has a start block: carve input `start`; the 5 omitted START carriers (stw_*) are the start pin
  delayed by the published age of the reset carrier beside them (72/74/75/83/90, same as the reset prefixes); bench lane
  epoch = rst_n AND start. tb: rst_n deasserts after 16 cycles, **start rises S = 200 cycles later**, calendar begins at
  **S + CALENDAR_START_DELAY = 200 + 130 = 330** cycles after rst_n (130 = latest pin release 129 + 1).
- Binds without a start block: carve / tb / run_smoke.sh byte-identical to the wavefront_r3 staging (regressed).

## Result (epyc3, ot-run unit oth-ubuntu-4108029-1792930541)
| run | calendar start (after rst_n) | numeric near / far | verdict |
|-----|------------------------------|--------------------|---------|
| nominal | 330 (= S + 130) | **64/64 + 64/64 exact** | PASS |
| hr lane +1 mutant | 330 | 64/64 + 64/64 | **caught** by xt1_schedule_gate (fixed consumer edges differ): `results/schedule_gate.json` PASS |
| NEG calendar at S | 200 (= S, before START wavefront) | 0/64 + 0/64, FAULT heads at cycle 200 | **FAIL as required** |
| NEG start never raised | 330 | 0/64 + 0/64 (no outputs at all) | **FAIL as required** |
| probe: calendar 1 early | 329 (= S + 129, = S + latest pin release) | 64/64 + 64/64 | PASS: not "before the release"; shows the +1 in CALENDAR_START_DELAY is margin (same as the wavefront pass) |

Cycles vs the wavefront pass: the per-op edge record (`log_m0.txt.xt1n.json`, `log_m1.txt.xt1n.json`) is byte-identical
to `../xt1_wavefront_r3` (QKV first_final 261, O 213..252, GU 453..460, down 245..348 calendar cycles; mutant +1).
START adds exactly S cycles of boot (calendar at S + 130 instead of 130) and 0 cycles per token; with S = 0 it is the
old wavefront.

Build 2,751 s wall / 79.5 GB peak (epyc3 at ~2.4x cores load); sims 4.7-9.7 min each.
Run dir: epyc3:/srv/opentallas-scratch2/claude/qc-tok-start-1025/both (obj kept for reruns at other S).
