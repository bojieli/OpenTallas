# dsdv_bksel_q HLAT (S81-ARCH-RTL-2 11-12, DIE-S81-87 / COORD bksel hold, structural fix)

The fix adds 0 cycles: no plan latency rows, lanes or ports change, so it has no TOK impact.

**Form.** `ot_s81ph_hlk` is a negative-level lockup latch (transparent while ck is LOW). Each instance `u_fl_*` sits on
the launch side of the zero-logic or near-zero-logic intra-core hops measured in vC4r HOLD_SPLIT (4_cts.odb FF, placement
RC, pre-repair: 1581 violators, ws -128.97):

| Latch | Hop |
|---|---|
| u_fl_x | b_* -> x_* (tile) |
| u_fl_i0 | x_* -> i0_* |
| u_fl_r1 | r1 q -> c1_p |
| u_fl_r1s | rpb / memb -> r1 q |
| u_fl_c1 | c1_* -> c2_* |
| u_fl_pend | pend_d1 -> pend_eff |
| u_fl_pe | e1 / e0 -> pend_eff |
| u_fl_o0m | o0_m -> o_in / ofq wd |
| u_fl_o0p | o0_p -> o_in / ofq wd |
| u_fl_o0s | sm / sp -> o_in / ofq wd |
| u_fl_row | hist g_row v / en / dg -> g_bank stage |
| u_fl_g1 | hist g1 -> s_g |

HLAT 0 is the old circuit (yosys: 0 $dlatch). HLAT 1 gives 93 $dlatch cells, about 4.95k latch bits.

**Legality.** The latch must be clocked from its launch flop's tap. Source `hlat_follow_d.tcl` after `regional_taps.tcl`
(PRE_CTS). It re-hangs each u_fl_ latch on the clock net of its D-driver flop, and fails closed on any latch without a
flop driver. The launch -> latch check is then intra-tap, and latch -> capture gains ~T/2 (416 ps at 833 ps) minus skew.
Same form as tools/die_plan/clock_taps.tcl TYPE-SAFE-1 and kit_zl_lockup.py (ot_dp_lk).

**Gates** (`run_hlat_gates.sh <kit rtl> <out>`, evidence_1112/gates.log): `HLAT_GATES PASS`.
- q bench, HLAT 1 vs 0 under random stimulus: outputs bit-exact, and no latch moves in the high phase.
- Mutant OT_S81PH_HLK_MUT (positive-level latch) FAILs: 790 high-phase errors.
- Layer bench tb_bk_layer, 6 compiler stimulus sets: HLAT 1 trace == HLAT 0 trace (6/6), and all 372 latch instances
  toggle (HLK_COV).
- Lint: 0 errors. One new warning, COMBDLY on the always_latch `<=`, the same form as dsdv_bk_oll.
- Note: the 1019 stimulus sets report BK_LAYER FAIL for this profile quarter in BOTH forms, identically. The profile quarter
  has a different edge schedule from the 1019 compiler stimulus. This is a pre-existing difference, not an HLAT effect.

**Kit (one iteration, bksel lane, vC4r kit).**
- Copy rtl/{dsdv_bksel_c, ot_s81ph_hq_slice, ot_s81ph_hq_tile, ot_s81ph_hq_parts}.sv into the kit rtl/.
- Add `HLAT 1` to VERILOG_TOP_PARAMS (`OLL 2 RFH 2 HLAT 1`).
- Source hlat_follow_d.tcl after regional_taps.tcl.
- Resume from synth; keep the floorplan and macro placement.

**Estimate** (`hold_cover.py` on vC4r pa_hold/hold_all.rpt):
- 1247 of 1581 violators are on latched hops. The worst internal residue is -48.1 ps, and 334 endpoints are left.
- The 18 lane[] -> ot_fcap port captures (-108.6) are fed by input ports, so they cannot be latched. This is an IO-contract
  or face-flop clock item.
- New launch -> latch checks are intra-tap, so their slack is roughly clk-q + wire - local skew. Expected >= 0.
- Setup cost: one latch D->Q (~30 ps TT) on each latched hop, now inside a half-cycle window (~416 ps + borrow). These hops
  were zero- or near-zero-logic, so the setup margin stays large.
