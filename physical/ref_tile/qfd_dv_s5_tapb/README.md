# qfd_dv_s5_tapb (QW-SLICE6-HEADS 10-19, Q.STA.SLICE.2 head band)

Top `qfd_dv_s5_tap` (rtl/qwen_dv/s5/qfd_dv_s5_leaves.sv, rtl/qwen_sys/dvm_20261014/ot_qfd_xslice.sv, rtl/hdc/ot_hdc_delay.sv); outline 345.6 x 172.8 um, layer cap M5, one centre-fed TritonCTS root, recipe 4.
Purpose: QW-SLICE6 parallel fallback of qfd_dv_s5_tap: 345.6 x 172.8, hr on W, x beat alone on S.

Fallback: fallback: 345.6 x 172.8 (2:1), hr_q moved to W so S carries only the x beat (3.0 pins/um).

Faces (pin_ranges spread each face's ports over the whole face, in proportion to bits):

- N: hw
- S: xt_v, xt_a, xt_d, xt_bad
- W: ck, rst_n, sid, hr_q, tap_fault
- E: lq_bad, cid

## SAFE-DESIGN checklist

- 1_pins: PASS: ot_qfd_xs_tap registers its inputs (E1 pin registers) and launches hw from flops; cid HARD 1 register; lq_bad OR -> fault join is sticky status; rst_n 2-stage landing
- 2_reach: PASS: < 405 um across the tile
- 3_fanout: gate textbook_lint high_fanout (hw broadcast: one copy, the parent lands 4 column copies)
- 4_depth: inherited ot_qfd_xs_tap STATIC_SCHEDULE 1 (closed in the heads cluster)
- 5_storage: PASS: no indexed flop array > 2 kb (tap queue <= 2 entries)
- 6_floorplan: pin-bound (util ~5%: 2.4k um2 std, 6.2k flops, 3.1k pins): hw 1,567 over the whole N face (5.3/um), hr+xt 1,503 over S (5.0/um) by pin_ranges; aspect 2:1; no macros
- 7_clock: one centre-fed root; io_hold_margin 0.03
- 8_schedule: HARD 1: cid (4 sid + c, static after SETID) +1 edge = 0 steady cycles; everything else as qfd_dv_heads

Benches: run_s5.sh eq 0 (lockstep vs qfd_dv_slice2, 4 modes) and b2 0 (dv_bench2 FACE 3) PASS; mutant s5_eq_mut_d9 must FAIL (witness results/arch/qw_slice6_1019/witness/tap_d9.log).
Gate records: results/arch/qw_slice6_1019/heads/ (gate1 = unranged pins, superseded).
