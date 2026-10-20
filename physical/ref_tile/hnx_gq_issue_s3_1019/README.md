# hnx_gq_issue_s3_1019 (LEAD2-HBM/L2H-P3/GQ 10-19) -- next-release HBM (P=3) COLL gather master ISSUE leaf, structurally safe successor

Predecessor: hnx_gq_issue_1019 n2 (72d501b02) NEEDS_RTL: TT -53.69 ps on u_aq0.s8_e[0] -> u_aq0.s9_rs (exponent broadcast,
signed exponent subtract, clamp and shift count in one stage, 16 cells / ~737 ps) and FF -12.95 ps hold on u_aq1.q -> aq_q_q
(zero-logic capture register behind the quantiser's own output register); diagnosis
codex/hbm-p3-terminal-model-1019 results/arch/hbm_p3_terminal_model_1019. One failed route = structural redesign:

Source (branch claude/hnx-gq-s3-1019): rtl/hbm_next/coll/ot_hnx_coll_gq.sv (ot_hnx_coll_gq_issue) + rtl/hbm_next/coll/ot_hnx_coll_aq14.sv
+ rtl/hbm_next/coll/ot_hnx_coll_aq_scale13r.sv; geometry = LH-SU K kits (hcoll_gq_issue_k1/k2_1019: 432 x 345.6, 8 SRAM on the 43.2 lattice).
- Quantiser ot_hnx_coll_aq14: S9 split into (a) signed element exponent Ev = exponent(x) - e and (b) dd / grid g / clamped shift
  count; e formed as 32 KEPT per-element copies (each loads one subtractor), shift count as 3 kept copies per element (one per
  shifter chunk), encode-stage {fp4,e} 16 kept copies; LATENCY 13 -> 14, II 1, numerics exactly ot_hdc_actquant (same
  expressions, only cut at a register; no algebraic rewrite).
- 1,024 b x 9-edge element line per quantiser on a 16-slot SRAM ring (4 x ot_sram_1r1w_128x256_m1_r2c2, distinct read/write rows,
  full-cycle read capture) = 8 macros; the S9 -> S10 significand pass is 2 registers (no >= 3-deep flop line).
- Output: the zero-logic aq_q_q / aq_eb_q capture is removed; P (code assembly) reads the quantiser output registers through its
  registered one-hot AND-OR (logic on the hop), the biased exponent byte e + 127 is formed in the quantiser output registers
  (4 kept copies). The +1 quantiser edge is absorbed: x @9, S0 @10, output @23, P @24 = n2 (no data-calendar change).
- Descriptor row file 16 x 137 b: ONE registered read port (one-hot AND-OR on 5 kept row one-hot copies, <= 28 loads per bit),
  every reader uses the registered current row R or base row B; the n2 launch read rf[p_sb] is gone (launch lands one edge).
- Select fan-out: feed one-hots 8 kept copies per 256-b word, P selects 8 kept copies per ring (<= 32 loads); reset relay 24 kept
  regions + flow split OT_RST_COPIES_MAX 32.
- CTS: TritonCTS with route.cts_sink {"sink_clustering": false} (short local leaves; precedent qkd_d2d_static; LH-SU k1). Parallel variant: hnx_gq_issue_s3b_1019 (same source, 16-sink / 40 um CTS clusters).

Benches (fleet ot-epyc8, Verilator 5.050, bundle 7a7f7112a; results/arch/hbm_next_1019/units/coll/bench_s3/main_7a7f7112a.log):
s0 (d4g rows) / s1 (trains N 1..6) / s2 (cycles(N) scan) COLLQ PASS, faults f1..f5 FAULT PASS, schedule checks 0 conflicts,
AQ14 lockstep vs ot_hdc_actquant (one edge later, 1,024 FP8+FP4 blocks, warm resets, eb copies) AQ14_EXACT_PASS.
Mutants FAIL with committed witnesses (results/arch/hbm_next_1019/units/coll/witness_s3/): m9 SRAM ring one slot short
(COLLQ FAIL errors=600), m2 exponent bias 126 (errors=64), m8 row-local k never restarts (errors=22037), aqec exponent copy
(AQ14_NUMERIC_MISMATCH), aqrs shift-count copy (AQ14_NUMERIC_MISMATCH), aql ring slot (AQ14_NUMERIC_MISMATCH).

## SAFE-DESIGN checklist (owner 10-19)
1 Pins: PASS -- every input is captured by a flop at the pin and every output is a flop Q (stage table unchanged from n2; auto pin
  registers opted out, keep_pin_regs); reset lands in 2 registered face stages (reset_landing, rst_n x4 copies), then the 24-region
  kept relay (flow split <= 32 loads).
2 Reach: PASS by stage plan -- each transport (read face -> feed register -> quantiser S0 at the macros -> output registers -> P at
  the east face) is a registered hop on a 432 x 345.6 tile; the gate's netlist lint (> 500 um per stage) and the placement PNG
  are the check; any > 405 um hop found there gets a relay.
3 Fanout: FIXED -- the n2 worst path's single s8_e register broadcast is now 32 per-element kept copies; shift count 3 kept copies
  per element; feed / P / row one-hots in kept copies <= 32 loads (ot_hnx_coll_aq_cff: keep_hierarchy + keep/dont_touch, not
  merged by Yosys); the gate's high-fanout lint on the mapped netlist confirms.
4 Depth: FIXED -- S9 (8-b field select + 11-b subtract) | S10 (11-b subtract, compare, 5-b add, mux) | S11 (13-b chunk shift, sticky
  OR, 5-b round add); scale stage 4 rebalanced (scale13r); descriptor consumers read registered rows; no combinational in->out path.
5 Storage: FIXED for the element lines (2 x 9,216 b in 8 SRAM rings). Waived with reason: descriptor file 2,192 b (just over the
  ~2 kb guidance) stays a config-written flop file with ONE registered read port (no runtime-indexed mux, no combinational
  consumer; brief option "registered single-read design"); the 40 x 21 b event line is the static schedule itself (9 taps), narrow.
6 Floorplan: PASS -- 8 macros on the 43.2 lattice (K geometry: x 43.2/172.8/302.4, y 43.2/129.6/216), halos 16.2 x / 2.16 y,
  channels 34.8 / 45.4 um, full-face pins (<= 6/um), one full-width std-cell band, aspect 1.25. Fill below 40% expected (macro- and
  channel-limited outline, 31.1k um2 hard area): the safe side, measured by the gate.
7 Clock: single centre-reachable root on a small tile, TritonCTS with route.cts_sink {"sink_clustering": false} (short local leaves; precedent qkd_d2d_static; LH-SU k1); the gate must show pin-flop spread <= 80 ps at TT and FF;
  io_hold_margin 0.03 (>= 0.025).
8 Schedule: PASS -- static, no credits; quantiser +1 edge absorbed (data calendar unchanged); +1 launch -> fire edge
  (FIRE_FROM_LAUNCH 3 -> 4, tools/hbm_next/hnx_coll_gq_train.py) and the rule "no descriptor row rewrite in the edge before its
  fire" handed to HNEXT.CMTP (lane L2H-P3.md); cost one edge per programme launch, not per gather.

## PRE-GATE NATIVE CENSUS (HNX-UNITS/GQ 10-20 06:34) -- FAIL, kit NOT gateable until the RTL is rebuilt
Gate 6f36e797b (tools/closure_loop, ref_tile, textbook_lint, common_flow from main 315a46596) refused at floorplan:
PRE_GATE_NATIVE_CENSUS_REFUSED, mapped netlist sha 9e0850c7..., 115,826 roots, 683 drivers > 32 loads, max 1,351
(evidence results/arch/hbm_next_1019/units/coll/census_s3/: census_summary.json, violations.tsv with source registers per net).
Checklist item 3 (fanout) was NOT met by the s3 RTL; items 1/2/5/6/7/8 above are unchanged, item 3 -> FAIL. Classes:
- A descriptor row-file write (p_we && p_wa < 16 decode): shared term 1,351, row enables 134-148 x16, B load 117-119, p_wa 53.
- B fire (run, rv, cur < lim, tl == R[18:3]) 885 (+81/83); C wrap / wrap_ld (tl, per, lps, lq, run) 129/122/81.
- D lq 246, p_sv 88; E ev_in_v (iss, iph) 167/110, i_adv (kx, g_kn, ir, g_n) 86/92/60/55; F sfv/scd 97/71/71.
- G a1[290] (ra_lp_data select) 514, g_r2 155, g_rsa 100 (x11), qa 94, R 83, ev_k 74, g_src 44.
- H lib ot_static_program_target (u_target): reset_live 293, scan_row 136-261, install_open 159, address/data_q match 133-151.
- I ot_hnx_coll_aq14 x2: shift-count kept copies g_s10[].g_c[].u_ff 576 nets up to 71 loads (3 copies/element too few),
  s0_x 60, s2a_m 59, u_scale s1_power 52/33.
Fix plan (structural, next RTL agent): kept copies (ot_hnx_coll_aq_cff) of every listed register sized loads/32; replicated
kept compare modules for fire / wrap / ev_in_v / i_adv per consumer group (or register them one edge early and price the
edge); registered row-write one-hot x5 kept copies per row (config path only); HNX-local safe copy of the program target
(do not edit the shared lib); aq14 shift count 1 kept copy per <= 32 shifter inputs. Then bench + mutant witnesses again,
then the census-first gate.
