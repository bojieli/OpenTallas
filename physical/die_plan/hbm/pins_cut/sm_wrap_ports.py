#!/usr/bin/env python3
"""HBM-P5-PINS: port lists of the SM synthetic cores lx / tp = the wrapper modules ot_hbm_sm_attn_leafh_lx /
ot_hbm_sm_attn_tile_tp (rtl/hbm_accel/sm/attn/qsplit/), at the r18h5 view parameters (LBS 2, LSB 16, TAGW 16, XD 128,
NBEAT 13, A1B 9, A2B 7, RPT 2, SUB 4; OT_SMH_RSTPIN not set).  Cross-checked against the hierarchical r18h5 SM netlist
cut (netcut.py: lx 3022 in (= the wrapper) / 595 out, tp 3909 / 9707 incl. the 2-bit attn_row strap adder that tp no longer carries).

    python3 sm_wrap_ports.py OUT.json
"""
import json, sys
TAGW, LBS, LSB, XD, NBEAT, A1B, A2B, RPT, SUB = 16, 2, 16, 128, 13, 9, 7, 2, 4
XW = (XD - 1).bit_length()
RBW = 6 + TAGW + LBS * 266 + LSB * 16 + 1 + XW
BBW = 1 + XW + NBEAT + 2048
GLW = 2 + 32 + TAGW
I, O = 'input', 'output'
lx = [['clk', I, 1], ['rst_n', I, 1], ['attn_column', I, 3], ['attn_row', I, 2], ['xs_a1', I, A1B], ['xs_g1', I, 5],
      ['xs_a2', I, A2B], ['xs_g2', I, 5], ['rl1', I, RBW], ['bk1', I, BBW], ['ohl1', I, NBEAT],
      ['gv', O, 1], ['gf', O, 1], ['gy', O, 32], ['gt', O, TAGW],
      ['tcc_i_v', O, 1], ['tcc_i_first', O, 1], ['tcc_i_qk_last', O, 1], ['tcc_i_pv_last', O, 1],
      ['tcc_i_run_first', O, 1], ['tcc_i_run_last', O, 1], ['tcc_i_tag', O, TAGW], ['tcc_i_w', O, 256],
      ['tcc_i_x', O, 256], ['tcc_pub_start', O, 1], ['tcc_pub_slot', O, 3], ['tcc_fold_start', O, 1],
      ['tcc_fold_a', O, 3], ['tcc_fold_b', O, 3],
      ['tcc_ov', I, 1], ['tcc_y', I, 32], ['tcc_otag', I, TAGW], ['tcc_fault', I, 1], ['tcc_pub_v', I, 1],
      ['tcc_pub_data', I, 32], ['tcc_pub_word', I, 4], ['tcc_pub_out_slot', I, 2]]
tp = [['clk', I, 1], ['rst_n', I, 1], ['rin', I, RPT * RBW], ['bin', I, BBW], ['rout', O, RPT * RBW], ['bout', O, BBW],
      ['gin', I, (SUB - RPT) * GLW], ['gout', O, SUB * GLW],
      ['lh_rl1', O, RPT * RBW], ['lh_bk1', O, RPT * BBW], ['lh_ohl1', O, RPT * NBEAT],
      ['lh_gv', I, RPT], ['lh_gf', I, RPT], ['lh_gy', I, RPT * 32], ['lh_gt', I, RPT * TAGW]]
out = {'ot_hbm_sm_attn_leafh_lx': {'ot_hbm_sm_attn_leafh_lx': [p + [0] for p in lx]},
       'ot_hbm_sm_attn_tile_tp': {'ot_hbm_sm_attn_tile_tp': [p + [0] for p in tp]}}
for k, v in out.items():
    pl = v[k]
    print(k, 'in', sum(p[2] for p in pl if p[1] == I), 'out', sum(p[2] for p in pl if p[1] == O))
json.dump(out, open(sys.argv[1], 'w'), indent=0)
