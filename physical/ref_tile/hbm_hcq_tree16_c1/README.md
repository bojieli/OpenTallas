# hbm_hcq_tree16_c1: HC quarter-hub tree slice (hard child x4 of hbm_hcq_hub_c1) -- HBM-HCBANK6 10-20, H.STA.BLK.17.2

Top `ot_hbm_hc_qtree16_static`: levels 1..4 of the quarter subtree over 16 chunk sums (15 of the 63 LAT-7 adders), every
adder the reviewed native-fanout graph `ot_hdc_fp32_add_lat_fan32` SAFE_DIST 1 (520dbea3a). One master, instanced x4 in
`ot_hbm_hc_qcen_static` SAFE 2 (`u_cen.g_hard.g_qt[c].u_t`), each with its own clock entry `clk_t[c]` of the hub.
Why: the SAFE 1 hub (s1/s1b/s2/s2b) put 51,337 flops on ONE root over 734.4 um; the --cts gates stalled 4 h in
repair_timing -hold (28,269 hold endpoints, sink arrival 566..849 ps) and the netlist failed native32 (960-1,057 > 32).

Outline 129.6 x 97.2 (1.33:1), util 47 % of the measured 5,947 um2, W face 515 pins = 5.3/um.
First gates (10-20 03:40, 129.6 x 108.0 / 151.2 x 129.6) FAILED in timing-driven GPL: RSZ-3006, the native graph's
(* dont_touch *) cells block buffering. Fix: kit-local PRE_GLOBAL_PLACE hook physical/hbm_hc_hub/native_untouch.tcl clears the
physical dont_touch on the graph (logic unchanged; buffers are transparent to the census).

## SAFE-DESIGN checklist
1 Pins: PASS -- every input lands in RTL flops (s_q 512 b = the SAFE 1 s_i pin register slice, vq leaf valid), every output is
  an adder output register; rst_n lands in 2 stages (reset_landing), then ot_rst_relay 8 kept regions (14 clears a copy).
2 Reach: PASS -- 130 um tile; the parent places it beside its W-face s_i pins (<= ~200 um).
3 Fanout: PASS -- native32 census of the mapped slice (plain yosys + ASAP7 TT libs): 0 violations, max 24 loads, 43,638 roots.
4 Depth: PASS -- native graph estimate 288 ps / 9 levels per stage (gate textbook 288.4 ps).
5 Storage: PASS -- no storage > 2 kb (pipeline registers only).
6 Floorplan: PASS -- no macros, full-width std-cell rows, aspect <= 1.33.
7 Clock: own CTS root (~9.96k sinks over 130 um); the parent clocks it from its own entry (hybrid_entries, die compensates
  the measured insertion); io_hold_margin 0.03.
8 Schedule: 0 added edges (same edges as SAFE 1: the parent hands the leaf valid one edge early, vl[VD-2]).
Benches (Verilator 5.050): tb_hbm_hc_qtree16 vs the SAFE 1 subtree slice: MUT 0 PASS (19,986 edge checks incl. an in-flight
reset), MUT 4 FAIL (witness results/rtl/hbm_hcq_hub_c1/qtree16_mut4.log).
