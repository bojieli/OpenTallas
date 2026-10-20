# hidx_sel_s3r_b -- FAN32 quadrant tile ot_hidx_s3_q (x4) of the landed IDX selector cluster (HBM-IDX6, 10-20)
Successor of hidx_sel_s3q_b (L2H-IDXSEL s3, fb02fa82f), which failed the mandatory native32 census (497 drivers > 32,
max 1788: fill copies into a multiply-shift barrel rotate, pack decode, line enables, histogram clears/read, reset leaf).
Same ports, PORT TIMING and arithmetic: lockstep-equivalent to the s3 original on every port (rtl/test/hbm_idx_static/
run_s3_equiv.sh, 3 x 200k random cycles incl. 30 mid-run resets each). Calendar registered_s3 unchanged (sel_in 7,
sel_in_line 2, sel_out 1, sel_choose_rt 8): no edge added. Geometry = s3q_b (259.2 x 216, 3 SRAMs on the 43.2 lattice).
Synthesis area 27,615 um2 (s3q 31,213): the two-stage one-hot rotate is smaller than the old multiply-shift.

## Native32 census (mandatory, actual-Liberty mapped netlist, origin/main native_census.py inside the gate)
iter 1 48 drv/max 63 -> iter 2 9/47 -> iter 3 11/46 -> iter 4 8/39 -> iter 5 (d0b37006f): PASS, 0 drivers > 32,
max 31, 37,199 roots (ot-agidock128 ref_gate/hidx_sel_s3r_{a,b}-20261020-032047). Fixes: kept P1 cw copies per consumer
family (11), per-chunk (13/12 b) kept flags for every line-wide select/enable, two one-hot 4:1 rotate stages with
selects loaded one edge ahead from 5 replicated fill states, per-chunk pack prefix copies in a kept module
(ot_hidx_s3_pfx), kept compare/histogram copies of the SRAM read (rawc holds the order key), kept last-valid module
(ot_hidx_s3_pri), tie budget / last_id / valid bits replicated per consumer, 15 regional reset leaves.

## SAFE-DESIGN checklist (owner 10-19)
1 Pins: PASS -- cw -> 11 kept P1 pin flops, thr -> 6, ties -> 4, in_line -> in_p1; every output a register; rst_n ->
  ot_rst_relay 2 sync + region stage (reset_landing.json).
2 Reach: PASS (as s3q) -- pin flop -> P2 copies beside consumers; <= ~260 um per hop; gate reach check.
3 Fanout: fixed -- census PASS max 31 (above); kept copies verified in the mapped netlist (census counts actual pins).
4 Depth: rotate = 2 x AO 4:1 + split/merge (~10 levels), pack = kept prefix + decode + 16:1 AND-OR; gate textbook depth.
5 Storage: PASS -- lines in 3 SRAM macros; histogram 64 x 14 b fixed-index counters (896 b < 2 kb), read by a
  registered one-hot select; no delay line >= 3 deep (op6 pack chain is a 5-flag shift per lane, 1 bit).
6 Floorplan: PASS (as s3q) -- macros on the 43.2 lattice in x, 43.2 channels on both pin faces, one std band, aspect 1.2.
7 Clock: one region root per tile (cluster ck_q<n>), crossings landed in the parent; judged on pin-flop spread <= 80
  TT+FF in this gate; io_hold_margin 0.03.
8 Schedule: PASS -- static, no credits/backpressure; zero added edges.
Benches (Verilator 5.050, results/rtl/hbm_idx_static/selector_s3_fan32): selector m0 PASS + d1 d3 d5 d6 rt7 dr3 l1 l2
FAIL; lp lockstep BENCH_EXIT 0 (MUT 1 2 4 5 FAIL, audit PASS); FAN32 equivalence m0 PASS + d1 d3 d5 c6 FAIL.
