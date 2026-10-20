# qfd_dv_s5_xheadb (QW-SLICE6-HEADS 10-19, Q.STA.SLICE.2 head band)

Top `qfd_dv_s5_xhead` (rtl/qwen_dv/s5/qfd_dv_s5_leaves.sv, rtl/qwen_sys/dvm_20261014/ot_qfd_xslice.sv, rtl/hdc/ot_hdc_delay.sv); outline 259.2 x 432.0 um, layer cap M5, one centre-fed TritonCTS root, recipe 4.
Purpose: QW-SLICE6 parallel fallback of qfd_dv_s5_xhead: 259.2-wide head, corridor words both N, {ib,go}+fill S.

Fallback: fallback: 259.2 x 432 (+20% width, N 4.0 / S 6.0 pins/um) with n_d + s_d on N and a_ib + a_f on S.

Faces (pin_ranges spread each face's ports over the whole face, in proportion to bits):

- N: n_d, cid, ck, rst_n, s_d
- W: w0_v, w0_ep, w0_off, w0_m, w0_d, w0_ctl, c0_v, c0_ep, r0_v, r0_t, r0_ep, r0_p, q0, q0_v, q0_bad, fault, l_rst_n
- E: w1_v, w1_ep, w1_off, w1_m, w1_d, w1_ctl, c1_v, c1_ep, r1_v, r1_t, r1_ep, r1_p, q1, q1_v, q1_bad, fault_i
- S: a_ib, a_f

## SAFE-DESIGN checklist

- 1_pins: PASS: every input lands in one pin flop (g_pin/ib_pin/f_q/tid_q/fi_q/lqp/lqvp/lqbp), every output is flop Q (lw/lc face regs, lr0, n_q/s_q, fault); rst_n 2-stage landing (qfd_dv_s5_rst2)
- 2_reach: PASS: 216 x 432 tile, every hop < 405 um; the leaf buses leave W (chain 0) / E (chain 1) to leaves beside it
- 3_fanout: checked by the gate textbook_lint high_fanout (fd rotate 6 levels of 2:1; tids constant after SETID)
- 4_depth: inherited ot_qfd_xhead (closed in qfd_dv_heads_w130 at 0.77 ns); --cts path classes confirm
- 5_storage: PASS: largest indexed arrays wb/wbp/wbm/wo/ro [2][16] (<= 608 b), first_abs [2][16][4] x 8 = 1,024 b: all < 2 kb
- 6_floorplan: pin-bound (util ~6%: 5.7k um2 std for 5.8k pins): pins spread over whole faces by pin_ranges (W 3.7, E 4.6, S 5.7, N 4.8 pins/um); aspect 2:1; no macros; full std-cell band; chain write bundles low on W/E beside the S fill input (reach)
- 7_clock: one centre-fed TritonCTS root (8.1k sinks); io_hold_margin 0.03
- 8_schedule: 0 added cycles (qfd_dv_heads w130 timing: FILL_LEAD 5, DX 14, LEAF_READ_PIN_PIPE 1); reset release +2 (= the slice synchroniser)

Benches: run_s5.sh eq 0 (lockstep vs qfd_dv_slice2, 4 modes) and b2 0 (dv_bench2 FACE 3) PASS; mutant s5_eq_mut_xh must FAIL (witness results/arch/qw_slice6_1019/witness/xhead_xh.log).
Gate records: results/arch/qw_slice6_1019/heads/ (gate1 = unranged pins, superseded).
