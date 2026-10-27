# TOK-SCHED: S81 vsw LR=1 (+1 cycle) in the static schedule and the price (2026-10-25)

Change: main 8d6af30b15 (codex/s81-sw-0719, RTL 5e569884d) sets `ot_s81sl_vsw` parameter `LR = 1` by default; the slice
(`ot_s81sl_slice.sv:212`) instantiates vsw without parameters, so every S81 beat leaf gets one lane-input register
stage: vsw `o_v / o_d / o_f` leave exactly one edge later (ovr delayed with it). vs consumes `sw_vi` by event (no fixed
latency in the RTL), so the function holds.

## Where the cycle sits

- vsw = the one hub SwiGLU lane of a beat leaf. Its only consumer is vs op 8 (SW). In the DAG that is the op
  `ffn.quant2` (vp SW command pin -> last vs result incl. vq act-quant, measured 191, SU.json; `ffn.swiglu` and
  `ffn.route_w` are fused into it at 0 cycles). Command -> last result becomes 191 + 1 = 192 (wr SW 195 -> 196).
- Token path: `ffn.quant2` runs 40x per token on the critical path in AR and in MTP (all 40 nodes critical, none
  overlapped). The pipeline law of record adds 5 more on MTP (wave positions): AR +40 cyc, MTP +45 cyc/step.
- Not absorbed by slack: every ffn.quant2 node is on the committed critical path, so the full +1 counts each time.

## Static schedule

- `tools/s81_dv/layer_prog/lower_vs.py`: `VS_DUR['SW'] = 4 n + 127 + VSW_LR + 4 wr` (`VSW_LR = 1`). Before, it was
  4 n + 127 + 4 wr, so the vs family bench (`tb_vs_lowered` / `tb_vs_guprop`) slot check would have flagged every SW at
  192 > 191 as SLOT_OVERRUN.
- Re-compile, `dv_layer_compile.py --layer {L0,L2,L14,L20,mtp_draft,head}` with VSW_LR = 0 and = 1: all rc 0, no clash.
  The issue edges, `prog/*` and `lowering.json` are byte-identical, so no later command of any leaf moves. The only `schedule.json` difference is the equal-latency CTL smoke path link name (1-2 entries
  per layer, `smoke/ctl_latency/path[].link`), which does not depend on VS_DUR.
- The other static calendars do not read a fixed vsw latency:
  - The quant LUT / QDELAYS (`norm_q_plan.py`, C8 col4-V) is the vn norm path built from plan lane ages, not vsw.
  - The AR50 / MTP6 MU calendars use node cycles. They were re-run here with the +1 and give 0 collisions, see below.

## Price (compose_tok_ds unchanged, run_vsw.py adds a priced-edge +1 to every ffn.quant2 node, before the calendar too)

| case | AR T (cyc) | AR tok/s | MTP T_step | MTP tok/s | AR50 agg / coll | MTP6 agg / coll |
|---|---:|---:|---:|---:|---:|---:|
| of record (I13 612), before | 1,528,913.6 | 784.87 | 1,815,440.6 | 2,749.1 | 39,243 / 0 | 16,494 / 0 |
| **of record + vsw LR=1** | **1,528,953.6** | **784.85** | **1,815,485.6** | **2,749.0** | **39,242 / 0** | **16,494 / 0** |
| pending I13 554, before | 1,528,449.6 | 785.11 | 1,814,686.6 | 2,750.2 | 39,255 / 0 | 16,501 / 0 |
| pending I13 554 + vsw LR=1 | 1,528,489.6 | 785.09 | 1,814,731.6 | 2,750.2 | 39,254 / 0 | 16,501 / 0 |
| bracket: +8 per ffn.quant2 (8 SW serial a leaf) | 1,529,233.6 | 784.71 | 1,815,800.6 | 2,748.5 | 39,235 / 0 | 16,491 / 0 |

- Delta: AR +40 cyc (-0.0026 %), MTP +45 cyc/step (-0.0025 %). It is the same on the 554 base.
- Calendars AR50 / MTP6: PASS with 0 collisions. Same-user checked. The negative controls still FAULT (injected shift
  660 / 2,748, N+1 1 / 1).
- Bracket: if the leaf's 8 SW commands were priced serially (the SU.json RISK note: 7 x 151 + 191), each would carry
  +1, giving +320 AR / +360 MTP (-0.02 %). The price of record prices the last SW only.
- Ledger: `S81.VSW_LR1` is proposed with e2e_loss_pct 0.003, binding AR. The ratio is 192 / 191 = 1.005, under 1.10.
  The row exists only to record the cycle, as COORD asked. `accepted_cost.py compute s81 --match 'ffn\.quant2$'
  --node-delta 1` on the token-path DAG agrees: 40 critical runs AR, 40 + 5 wave positions MTP.

## Evidence of the +1

`rtl/dsrom_sys/s81_dv/slice/test/run_vsw_lr_eq.sh` (iverilog lockstep LR=1 vs LR=0 + negative-control mutant):
see `eq.log` / `summary.json`. Run by ot-run on epyc1, sources = git archive of main 8d6af30b15+ (REV in summary).

## Not done / owed

- The vs family bench (`run_vs_bench.sh` on G8 layer fixtures) was not re-run, because its fixtures and schedules
  predate the current die. The SW slot now matches RTL by construction (VS_DUR + 1, eq bench). Whoever re-runs the vs
  family bench next should confirm SW_16 = 192 / wr 196.
- `ffn.quant2` stays graded measured-old-RTL (SU.json 19bf4121e). The +1 is a priced edge, not a new measurement.

Files: `run_vsw.py` (driver), `compose_1u.json` / `calendar_mu.json` (of record + vsw), `cases.json` (all five
cases + deltas), `run.log`.
