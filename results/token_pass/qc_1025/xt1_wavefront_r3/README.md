# QC token pass: xt1 both-cluster on the WAVEFRONT-reset bound top (2026-10-25)

Collected by QC-TOK from Codex's run epyc3:/srv/opentallas-scratch2/claude/codex-qc-wavefront-run-1025/both (no rerun of
the nominal/hr-skew simulations; the strict schedule gate was applied by QC-TOK to the untouched logs).

## What was bound
- Bind = epyc3:/srv/opentallas-scratch2/claude/codex-qc-bind-1025/wavefront_r3 (`recipe.json`, `bind_report.json`,
  `bind_reset.json` copied here): plan `physical/die_plan/qwen_compute/die_plan.json` sha256 d27c37880fe8d824 = **main's
  plan** (7c33a7a81), `tools/die_plan/bind.py` with the raw wavefront emitter = main af5cd532c (cherry of 36b9fb79b; the
  r3 source branch codex/qc-wavefront-bind-1025@c7f22a62f is patch-identical to main). 377 partitions, 1,933 crossings,
  792,661 bits, 0 errors.
- Reset (owner decision 13): `bind_reset.json` release = wavefront, one 2-flop root synchroniser at sl_W0_ctl, neighbour
  relays (hop 405 um, longest die hop 377.3 um, 0 unreachable / 0 long hops), latest partition release 128 clocks,
  latest published hard-core pin release 129 clocks after die rst_n deasserts.
- Carve (`carve.json`, `tb_smoke.sv`, `stage.json`: 108 closure files, 0 unresolved): both W5 clusters (22 partitions,
  32 ROM tiles) with their real partition reset RTL kept live; the 5 omitted-carrier boundary reset pins are driven at
  their published ages (72/74/75/83/90). The calendar starts on an explicit start 130 clocks after die rst_n
  (CALENDAR_START_DELAY = latest core pin 129 + 1), not on the reset edge (decision 13c).

## Result
| run | numeric (near / far) | schedule |
|-----|----------------------|----------|
| nominal lead 24 / gap 4 | **64/64 + 64/64 exact** (QKV/O/GU/down) | reference |
| hr lane +1 mutant (`SMOKE_MUT_SKEW=1`) | 64/64 + 64/64 (numerically insensitive, as before) | **caught**: all 16 fixed-consumer edge groups move (cw_go + result edges, 4 ops x 2 clusters) |

`results/schedule_gate.json` (tools/die_plan/xt1_schedule_gate.py): **PASS**. Relative to the calendar start every
cw_go / result edge is identical to the no-wavefront methodology pass (`../../qc_1024/xt1_meth`): the wavefront costs
130 one-time boot clocks (vs 2 for the old raw rst_n fan-out = +128 clocks, ~107 ns at 833 ps) and 0 cycles per token.
Build 2,217 s wall / 78.6 GB peak (Verilator 5.050, 366 modules); each sim 4.5 min / 0.4 GB.

## Scope / open
- `../xt1_wf_early` (QC-TOK): negative control. Calendar start at the reset edge (0) FAILS 0/64 + 0/64 (fault at
  sl_W5_fw, release 88); start 100 still PASSES (first words reach the late tiles after their release 101..116).
- tp8 with the published offsets: sub-lane, see `../tp8_wavefront` when it lands.
- This is the xt1 carve of the bound top, not a whole-die token pass; KV side (KV-TOK) still lacks a die-wide START after
  its wavefront (r16 retirement proof keyed to RST_HOLD 273).
