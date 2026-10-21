# hbm_hcq_bank_cb_rw6 (HBM-COLLECT10/HCQB 10-21) = hbm_hcq_bank_cb_rw5 + clock-entry / register-mass co-location

HBM-COLLECT10/HCQB rw6: the cb_rw5/rw5m gates (ep6, 10-21) FAILED CTS at glue root clk_c: pin-flop spread 104.1 / 102.2 ps TT (263 internal sinks, insertion 641 ps). 3_place sink dump: the cv/cd chain (252 cd + 9 cv + fin_q/f_o) sits at x 8..204 y 7..240 (SW corner, between the d_* in-pins W y130..140 and the o_* out-pins S x130..140) while the clk_c entry was on the E face y 374.7 -> ~700 um trunk. Fix: clk_c entry -> S face x 100..101 (free S segment 0..130, beside the chain). Pin move only; 0 RTL change.

SAFE-DESIGN checklist: as cb_rw5 (below); item 7 Clock: fixed (root entry beside its register mass); item 6 Floorplan: unchanged (one S-face pin added in the free 0..130 segment). 0 added cycles, RTL / benches / witnesses identical to cb_rw5 (ring lockstep m0 PASS, mut1/mut5 FAIL, Verilator 5.050, results/rtl/hbm_hc_ring_1021_rw5).

# hbm_hcq_bank_cb_rw5 (HC ring corner bank, H.STA.BLK.17) -- main

Owner HBM-HCBANK10 (LEAD-HBM) 10-21, branch claude/hcbank10-b0cb-1021.
top ot_hbm_hc_bankq_rw5_static; roots clk, clk_c, clk_o, clk_w0..3, clk_x0..3, clk_d0..3, clk_e0..3, clk_i0..3, clk_q0..3 (clk_a port removed).

## Why (gate evidence, f4230cae1 rw2 and predecessors)
- b0_rw2 clk FAIL 140.6 ps TT (hold/asm 1.8 k on the in-face root); b0_rl clk 82.8 (pin flops only, kept beat copies free);
  cb_rl/cb_rm/cb_rw2 clk 355..421 ps TT with only 355 pin flops: CTS sink region x 3..452 um -> the 48 kept copies vq_c/bq_c
  (xb_v/xb_beat not in OT_OFLOP_PORT_RE) were pulled 450 um off the in face toward the hold mass.
- e2_rw4 clk_c 432.1 (stage chain + SRAM addr/lane-enable fanout spread over 535x472 um); e2_rw4c (clk_c merged into clk)
  clk 461.7 (boundary 930/1169): merging a spread mass into the face root ruins it -> lesson: never merge, make each root compact.

## Structure (0 added edges, same register ages; clk_a eliminated)
- WROW 2 (rw4): row-local hold/asm/bad per SRAM row on clk_d<r> together with the row's per-SRAM write copies (anchored at wd_in).
- STG 1 (new): stage-control long-reach registers copied per row from the same chain taps on the same edge:
  w_re/w_addr on the row weight-capture root, x_re/x_addr on the row x-capture root, cvc/nvc/ssc + leaf go (ov) on clk_e<r>.
  clk_c keeps only the cv/cd chain + fin_q/f_o. Row copies reset from a 3rd kept relay leaf (fanout 16).
- clk = in-face pin flops only: OT_OFLOP_PORT_RE adds xb_v|xb_beat so the kept copies land at the pins.

## SAFE-DESIGN checklist
1 pins: RTL pin flops unchanged (CPI/CPO, landing, write port), reset 2-stage landing on clk: PASS
2 reach: in-tile cross-root hops unchanged in kind vs rw2/rw4 (face -> row write data as rw4); exit relay face-to-face hop (b0) per the RR0 design: guidance (rule freeze), judged by gate STA
3 fanout: kept copies unchanged (<=32); new row copies: cv[0] 9 loads, cd taps 5, rn_g 16: PASS by construction (native census in the gate)
4 depth: unchanged logic per stage (copies are plain registers): PASS
5 storage: SRAM macros unchanged: PASS
6 floorplan: rw2 outline/macros/children/pins unchanged (777.6 x 734.4, lattice macros): PASS
7 clock: each root one compact anchored mass (fix for the FAILs above); io_hold_margin 0.03: fixed
8 schedule: 0 added edges, no schedule change: PASS
Benches: ring lockstep m0 / mut1 / mut5 under HC_BANK_RW5[M] (Verilator 5.050) launched with the gate; witnesses go to results/rtl/hbm_hc_ring_1021_rw5/.
