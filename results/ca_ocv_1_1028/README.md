# CA-OCV-1: count-aligned crossing interval = STA phase + one clock variation term (2026-10-28)

The DIE-S81-8 finding (CHECKED there and here) was this. The count-aligned (CA) row of `tools/die_plan/die_sta_related.py`
rebuilt the crossing phase d from the OpenSTA tap late/early (with CPPR) and used it in place of the bind's
OCV-derated d. It never added the clock AOCV/droop term that the intra/seam/landed classes get from `clock_ocv_fn`.
The CA margin therefore had no clock variation in it, against METHODOLOGY 12.14a ("crossing margin counted after
OCV + droop").

## (a) NUMBER-CHECK: does the OpenSTA late/early spread already hold variation? NO (CHECKED)

- **Exports.** The S81 packed-G proof (`codex-s81-owner-0359/clock_body/route_TT/combo.tcl`, die_trial) has
  0 `set_timing_derate`/OCV/AOCV/CRPR commands. late = 833.333 - slack_max_rise and early = slack_min_rise on a
  data-path view of the clock. The die_clock_mesh exporter says the same in its docstring (CLOCK-MESH-2).
- **Libraries.** The ASAP7 RVT TT NLDM libs (orfs:asap7lock) have 0 ocv/lvf/sigma groups.
- **Where the spread comes from.** It is the liberty pin-capacitance range. For example, BUFx24 has
  `rise_capacitance_range (1.76355, 2.34978)`; OpenSTA uses the min cap for min arrivals and the max cap for max
  arrivals. That is a deterministic load-state bound, not process variation.
- **The AOCV term.** `clk_aocv.branch_pessimism` is a fractional derate of the nominal branch delay below the
  last common node. It never uses the late-early difference.
- **Verdict.** Adding the term once is not a double count. That holds as long as an export never carries a
  derate itself, and none of the five dies' proofs does today.

**Hand trace** (`scripts/hand_trace.py`): it reads only the raw tap JSON and the table JSON, and imports nothing
from die_sta_related or clk_aocv.

- **S81 TT**, `coll__lk_WN0__s_0N_LP__0` (lk_WN0->lk_WN3, K 4, depth 4). Worst pair t_lk_WN0__clk_t6 ->
  t_lk_WN3__clk_t21:
  - launch late 7530.0, capture early 6385.7, CPPR 130.84 at the LCA;
  - branches 1439.4 / 426.0 ps over 26 / 10 stages, bbox 1.558 mm, cross-region droop 5.11 %;
  - d_lo -1013.4, OCV(setup) 114.2, so d_lo -1127.7;
  - margin_lo 164.3 -> 50.1. This equals the tool's 164.3 / 50.1 exactly.
- **KV TT**, `L2197_2` (hgi_WS_1->pv_S_1). Branches 7.42 / 5.38 ns, 11.3 mm. OCV 563.2, so margin_lo
  501.0 -> -62.2, which equals the tool.

## (b) Fix (claude/ca-ocv-1-1028)

`count_align_d_intervals(..., ocv=)` takes the SAME callable that main() hands the related-pair classes:
`--clock-ocv table|flat` with the `--clock-droop` rule, plus the `--mesh-signoff` U, or `--pair-unc`.

- d_lo -= ocv(setup): launch late, capture early.
- d_hi += ocv(hold): capture late, launch early.

The start-skew sync distance uses the same interval. The SS info row scales the term by the SS factor.

Records now carry:

- `clock_variation`, `ocv_max_lo_ps` / `ocv_max_hi_ps` and `below_need`;
- per row, `ocv_lo_ps` / `ocv_hi_ps`;
- `summary.landed.clock_variation`.

Without a variation model, the interval stays unchanged; the record says `none` and a WARNING is printed. This is
not a new gate (12.14a rule freeze). `sta_d_intervals` and the `count_align_plan` / `count_align_bind`
`--sta-proof` hull take the same term through the opt-in `--sta-clock-ocv table --sta-clock-droop shared
--sta-droop-regions F --sta-core-latency-ff X` (default none = unchanged). With those flags the planner adds
K/PAD where the gate would fail.

Tests: `tools/die_plan/test_ca_ocv.py` has 7 tests.

- **Exact term.** The interval gets exactly one term, with asymmetric setup/hold values.
- **Margins.** Margins drop by exactly the OCV.
- **Pre-fix mutant.** The no-variation mutant PASSes a crossing that the fixed gate FAILs.
- **Swapped-side mutant.** It is rejected.
- **Planner CLI.** The flags reach the planner.
- **Table mode.** `sta_d_intervals` and main() with table mode match an independent clk_aocv recomputation.

Mutation runs: dropping the term or swapping the sides fails 6 of 7 tests. All 160 tests across the 13 suites that
import die_sta_related, count_align_* or clk_aocv PASS.

## (c) Cross-die sweep: CA rows with OCV (estimate-only, no builds)

Every row uses `--clock-cal spice`, `--count-align-key region`, `--cppr-lca` (all proofs carry tree_path),
`--clock-ocv table --clock-droop shared` with the proof's droop_regions.json, and core latency 250 TT / 202.5 FF
(12.3). The without-OCV baselines reproduce each die's own gate run (CHECKED). Script: `scripts/ca_sweep.py`.

| die | gate inputs | crossings (STA-timed) | <100 ps after OCV TT / FF | worst margin TT / FF (lo, hi) | without OCV TT / FF lo | start-skew FAIL TT / FF (base) |
|---|---|---|---|---|---|---|
| S81 | packed-G proof_body, plan_s5, die-s81-8 gate_sspice bind | 2306 (2287) | 10 / 13 | lo 50.1 / 59.0, hi 208.6 / 236.3 | 164.3 / 122.9 | 26 / 24 of 397 (0 / 0) |
| HEAD | sp5 die-head-5 sta_ival proof, die_plan_root_sp5, die-head-7 sta_qc5 bind_idreg | 427 (427) | 4 / 0 | lo 78.6 / 112.4 (host_rx__3) | 249.6 / 264.2 | 1 / 0 of 325 (0 / 0) |
| QC | K2 tree-parent: die-qc4 K2 CA_2w2s proof, grpP event, die-qc6 G_tp bind | 2537 (2438) | 37 / 4 | lo -14.1 / -48.7, hi 153.5 / 108.8 | 121.7 / 116.8 | 76 / 75 of 312 (37 / 24) |
| KV | proofpad2, hm_r26q9c, codex-meso-kv-ectl (RT20 full-hull) bind | 3595 (3569) | 38 / 54 | lo -62.2 / -66.7, hi 159.4 / 11.5 | 136.6 / 127.2 | 4 / 5 of 127 (0 / 0) |
| HBM | none | - | - | - | - | - |

- **HBM.** No gate-form CA row exists. There is no bind on built arrivals. The only built arrivals are the
  HBM-RISK-1 R2/R4 placement-RC clock-only proof, whose STA-hull CA plan was already 200 FAIL / 333 before OCV.
- **Slot/guard after OCV.**
  - KV: slot 2 / 3, guard 0 / 20.
  - QC: slot 4 / 3, guard 0 / 0.
  - S81 and HEAD: 0.
- **QC and KV core latency.** Their own runs used 250 FF; the 202.5 FF used here changes the class-B term by
  about 3 ps.

Data: intel2, intel1 and epyc2 under `/srv/opentallas-scratch2/claude/ca-ocv-1/`; copies are in `data/`.
