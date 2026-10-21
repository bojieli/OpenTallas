# hbm_hcq_bank_b0_rw6 (HBM-COLLECT10/HCQB 10-21) = hbm_hcq_bank_b0_rw5 + clock-entry / register-mass co-location

HBM-COLLECT10/HCQB rw6: b0_rw5m gate (ep6, 10-21) FAILED CTS at clk_d0: pin-flop spread 316.5 ps TT (2,580 internal sinks, insertion 577). Sink dump: row-0 assembler/write/capture mass at x 360..750 (beside the SRAM row, macros at x 432 / 648) but every row entry (clk_d/e/q[/w/x]) is on the W face (b0 mirrors cb's pin faces: in-face E, row clocks W) while b0 kept cb's macro columns -> >= 360 um trunk per row root. Fix: b0 macro/child columns mirrored in x like its pins (SRAM w x 172.8, x-SRAM x 43.2 beside the W row entries; lane children x 432.0 / 604.8 beside the E in-face). Same rows (y), same channels (>= 34.6 um), 0 RTL change.

SAFE-DESIGN checklist: as b0_rw5 (below); item 7 Clock: fixed (root entry beside its register mass); item 6 Floorplan: macro columns mirrored, channels unchanged >= 34.6 um. 0 added cycles, RTL / benches / witnesses identical to b0_rw5 (ring lockstep m0 PASS, mut1/mut5 FAIL, Verilator 5.050, results/rtl/hbm_hc_ring_1021_rw5).

# hbm_hcq_bank_b0_rw5 (HC ring bank 0, H.STA.BLK.17) -- main

Owner HBM-HCBANK10 (LEAD-HBM) 10-21, branch claude/hcbank10-b0cb-1021.
top ot_hbm_hc_bankq0_rw5_static; roots clk, clk_c, clk_o, clk_w0..3, clk_x0..3, clk_d0..3, clk_e0..3, clk_q0..3, clk_s0, clk_s1.
- b0 exit relay: OT_OFLOP_PORT_RE adds s_i|s_o so sr[0] lands at the S face (clk_s0) and sr[1] at the E face (clk_s1), the RR0 intent.

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
