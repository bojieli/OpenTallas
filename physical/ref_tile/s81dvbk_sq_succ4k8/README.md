# s81dvbk_sq_succ4k8 -- TOPK selector quarter FAN32 + ACC32 + K8 regional clock roots (dsdv_bksel_q, S81-TOPK4 2026-10-19)

RTL and geometry = s81dvbk_sq_succ3 (d72e81e31: FAN32 + ACC32, 324 x 540, 16 p192 macros on the 43.2 lattice, N pins
<= 5.6/um, ck N centre). Change: pre-CTS physical/common_flow/clock_split_km.tcl with OT_CKKM_K 8 (local BUFx24 root at
each placed register-mass centroid, one top tree balancing the roots). PARALLEL variants s81dvbk_sq_succ4 (K16, the
sq_reg recipe) and s81dvbk_sq_succ4k8 (K8: fewer region crossings); bind the first to close, cancel the rest.

Why (measured 10-19 22:55-23:05):
- succ3 gate (ot-agidock128 ref_gate/s81dvbk_sq_succ3-20261019-213502): one 42k-sink tree; post-CTS FF hold ws -109.3 ps,
  tns -56.3k, 12,968 endpoints inside the 30 ps margin (flop->flop pipeline stages u_ps/u_pi g_cst/cp, g_m2 wdata);
  hold repair stagnated at ws -87.3 / tns -27.2k after ~2,600 iterations (same gate-stall shape as succ1 / sq_reg).
  Setup is fine: placed TT (ideal clock, 3_place.odb) WNS +27.4 ps, 0 violating endpoints (ACC32 removed the acc family);
  the SS-corner -78.8 ps at u_in.g_indexed_format.f[0] is SS sensitivity only (succ2 TT 4_1_cts: 0 u_in violators).
- sq_reg (FAN32 + K16, no ACC32; ot-epyc7 20261019-175259): FF hold ws -38.9 / tns -3.2k (17x smaller), boundary pin-flop
  range TT 578.9..588.4 ps (9.5 ps); its blockers were the packer acc setup (TT -62.7 class, fixed by ACC32) and the
  14400 s gate stall in the margin chase.

Safe-design checklist: items 1-6 and 8 as s81dvbk_sq_succ3 (below). Item 7 Clock: regional roots (K8) on one phase-0
port; crossings between regions are ordinary register-to-register paths timed by STA inside a 324 x 540 tile (< 405 um,
0 added edges, no landing needed); the gate must show pin-flop spread <= 80 TT+FF and post-CTS hold converging.

---- succ3 README (unchanged RTL) ----
# s81dvbk_sq_succ3 -- TOPK selector quarter FAN32 + ACC32 (dsdv_bksel_q, S81-TOPK3 2026-10-19)

Successor of s81dvbk_sq_succ2 (d58faf9b0). Same geometry and clock recipe as succ2 (324 x 540, 16 p192 macros on the
43.2 lattice in two abutted W/E-pin stacks, full-width top band, N pins <= 5.6/um, ck N centre, CTS
-no_obstruction_aware). Opt-in defines: succ2 set + OT_S81PH_SEL_ACC32. Default RTL unchanged.

Why (measured, succ2 gate ot-epyc5 ref_gate/s81dvbk_sq_succ2-20261019-164207, review 10-19 21:30):
- clock PASS: pin-flop (boundary) spread TT 506.6..576.2 = 69.6 ps, FF 413.3..479.6 = 66.3 ps (succ2c unclustered:
  TT 216 / FF 195 FAIL, cancelled);
- kept copies survived Yosys (g_clc 512, g_gsc 128, g_frc 256, g_sl 278, g_b1c 3, g_oh 74, RST64 64 distinct flops);
- BUT placed TT reg->reg worst -62.7 ps at u_ot_pr_core.u_q.u_q.u_s.u_ps.acc[328] (SS post-CTS -124), and the textbook
  high-fanout top is the packer accumulate control: u_pi/u_ps oflush 1,219 / 1,183, rq_v 1,134 / 1,132, rq_tot decode
  OR4 1,184 loads (SAFE item 3 not met by FAN32, which covered hist/gsel/rotate only).

Change (exact, 0 added edges; OT_S81PH_SEL_ACC32 in ot_s81ph_native_sel_pack): each of the W = 32 output lanes gets
(* keep *) copies of the last-stage accumulate controls {ro_v, ro_fl, qf (LW), qc (LW+1)} on the originals' D/edge/reset
and its own oflush copy with the original update rule; the lane computes its own 38-bit acc / o_line from them. The
originals drive only o_v / o_fl / o_bv. +14 flops/lane x 32 lanes x 2 packers = +896 flops per quarter (~2 %).

Safe-design checklist (owner 10-19):
1. Pins: PASS. Source-registered QIO pin flops + io_flop_at_pins; reset_landing 2 stages.
2. Reach: PASS by construction (farthest macro capture -> band ~300 um < 405); succ2 gate reach_worst 0.4 um.
3. Fanout: FIXED. FAN32 copies (hist clr/v2 22, gsel decode <= 16 x 11, rotate shift 50) + ACC32 (accumulate controls
   <= 38 data loads per copy). Gate must show g_acl copies distinct and no >256-load register in the packer.
4. Depth: PASS. succ2 depth 420 ps / 11 levels; ACC32 removes a 1.2k-load buffer tree from the acc cone.
5. Storage: PASS (successor): FQ/OFQ in 10 SRAM, line pool in 6 SRAM.
6. Floorplan: PASS as succ2 (lattice, halos, band); fill WAIVED-with-reason (~33 % std fill, macro/pin-escape bound).
7. Clock: PASS on succ2 geometry (TT 69.6 / FF 66.3); same recipe; gate re-measures. RST64 <= 256 loads; io_hold 0.03.
8. Schedule: PASS. Static; ACC32 adds 0 cycles; INDEXED13 1037 reserved cycles already priced (S81.TOPK_FINAL).

Benches (Verilator 5.050, results/arch/s81_topk3_1019/run_suite.sh, ot-epyc8): legacy / indexed13 / ties / ninf /
zeros PASS; identity / corrupt / early FAIL; ACC32 mutant (upper-half lanes drop the running fill,
OT_S81PH_SEL_ACC32_MUT) FAIL 70 mism (legacy + indexed13; witness bench/mut_acc). Earlier mutants (SUCC one-hot,
FAN32 gsel / clear) re-run on the ACC32 define set by run_mut_prev.sh (ot-epyc9): FAIL 43 / 74 / 70 (witnesses bench/mut_{oh,gs,clr}).
