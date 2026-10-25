#
# v7 -> v8 (same outline, pins, RTL body, cycles):
#   * per head g, ONE hub sub-box hd<g> holds the head's ring WRITERS (u_qlw2w/e) AND its READERS (u_qlr2c/w/e,
#     including the reader output flops that Yosys names g_tx9.tc[..]): the 4-slot banks (2 x 512 b + the shared 600-b
#     l2c bank) never leave the hub.  Only the rung-1 word (XW = 390 b, reader q -> leaf round/mask -> g_r[1].u_tx at
#     the head's pin face) crosses to the face, register -> wire -> register.
#   * hub sub-boxes are a 3 x 3 array that mirrors the LSL array (head column / row -> sub-box column / row); the empty
#     slot's own position (middle column, row 0) holds the shared l2c writer u_qlw2c.
#   * each head's face box f<g> holds its rung-1 register, its result-ring writer u_qlw3 (captures the leaf pins) and
#     the leaf reset relay g_lrr.rq; --qlr3 face also puts the result-ring reader u_qlr3 there (only the 73-b result
#     word leaves the face), --qlr3 hub puts it into hd<g> for the heads whose face is not on the W side.
#   * regex fix: v7 matched only '/'-separated names (g_r\[1\]\.u_tx/) and missed the flattened reader flops
#     g_tx9.tc[..] (1,024 / tile), which fell into the catch-all 'hub' box; v8 matches the flattened names.
#   * the catch-all EXCLUSIVE 'hub' box (and its 4-um seam to the writer boxes) is gone: the remaining control
#     registers (u_me issue / operand control, ib_i, ...) are FREE (claimed, not boxed: GPL places them between their
#     drivers and loads), as are the x-operand landing ring g_xm9 and the request / fault landings (as in v7).
#   * all top-zone groups are INCLUSIVE (members fenced in, their combinational cones may share the box; v7's
#     EXCLUSIVE boxes pushed the reader muxes / enables out into the seams).
#   * ROM-zone groups (L1 rings rsw/rnw/rse/rne, readers lsw..lne, operand dw/de) are v7 unchanged.
# --e-orient MY (default): the E LSL column (sl3/6/7) is mirrored so its pin face looks W into the 35-um channel at
# x 300.24-335.66 (beside the hub) instead of the 20-um E die margin: no head word crosses the E column.
# generated: gen_a0c8_regions.py nl --e-orient MY --qlr3 mix
set qrl_groups [list \
  [dict create name land_rq type FREE regex {g_rom_pipe\.rq_(ce|ad)_[sn]\[1\]\[} boxes {} min 1 max 100000] \
  [dict create name land_fault type FREE regex {u_me\.(fault_q\[|g_hier\.g_sl\[[0-7]\]\.g_hd\.g_fl\.q)} boxes {} min 0 max 200] \
  [dict create name f0 type INCLUSIVE regex {g_sl\[0\]\.g_hd\.(g_tx9\.g_r\[\d+\]\.u_tx/|g_out9\.u_qlw3\.|g_lrr\.rq|g_out9\.u_qlr3\.)} boxes {{79.656 673.920 95.056 814.320}} min 1 max 100000] \
  [dict create name f1 type INCLUSIVE regex {g_sl\[1\]\.g_hd\.(g_tx9\.g_r\[\d+\]\.u_tx/|g_out9\.u_qlw3\.|g_lrr\.rq|g_out9\.u_qlr3\.)} boxes {{79.656 834.432 95.056 974.832}} min 1 max 100000] \
  [dict create name f2 type INCLUSIVE regex {g_sl\[2\]\.g_hd\.(g_tx9\.g_r\[\d+\]\.u_tx/|g_out9\.u_qlw3\.|g_lrr\.rq|g_out9\.u_qlr3\.)} boxes {{79.656 994.944 95.056 1135.344}} min 1 max 100000] \
  [dict create name f3 type INCLUSIVE regex {g_sl\[3\]\.g_hd\.(g_tx9\.g_r\[\d+\]\.u_tx/|g_out9\.u_qlw3\.|g_lrr\.rq)} boxes {{319.240 673.920 330.064 814.320}} min 1 max 100000] \
  [dict create name f4 type INCLUSIVE regex {g_sl\[4\]\.g_hd\.(g_tx9\.g_r\[\d+\]\.u_tx/|g_out9\.u_qlw3\.|g_lrr\.rq|g_out9\.u_qlr3\.)} boxes {{305.840 834.432 316.840 974.832}} min 1 max 100000] \
  [dict create name f5 type INCLUSIVE regex {g_sl\[5\]\.g_hd\.(g_tx9\.g_r\[\d+\]\.u_tx/|g_out9\.u_qlw3\.|g_lrr\.rq|g_out9\.u_qlr3\.)} boxes {{305.840 994.944 316.840 1135.344}} min 1 max 100000] \
  [dict create name f6 type INCLUSIVE regex {g_sl\[6\]\.g_hd\.(g_tx9\.g_r\[\d+\]\.u_tx/|g_out9\.u_qlw3\.|g_lrr\.rq|g_out9\.u_qlr3\.)} boxes {{319.240 834.432 330.064 974.832}} min 1 max 100000] \
  [dict create name f7 type INCLUSIVE regex {g_sl\[7\]\.g_hd\.(g_tx9\.g_r\[\d+\]\.u_tx/|g_out9\.u_qlw3\.|g_lrr\.rq|g_out9\.u_qlr3\.)} boxes {{319.240 994.944 330.064 1135.344}} min 1 max 100000] \
  [dict create name hd0 type INCLUSIVE regex {g_sl\[0\]\.g_hd\.g_tx9\.(u_qlw2[we]\.|u_qlr2[cwe]\.|tc\[)} boxes {{205.848 660.640 242.845 716.771}} min 1 max 100000] \
  [dict create name hd1 type INCLUSIVE regex {g_sl\[1\]\.g_hd\.g_tx9\.(u_qlw2[we]\.|u_qlr2[cwe]\.|tc\[)} boxes {{205.848 716.771 242.845 772.901}} min 1 max 100000] \
  [dict create name hd2 type INCLUSIVE regex {(g_sl\[2\]\.g_hd\.g_tx9\.(u_qlw2[we]\.|u_qlr2[cwe]\.|tc\[)|g_sl\[[3]\]\.g_hd\.g_out9\.u_qlr3\.)} boxes {{205.848 772.901 242.845 829.032}} min 1 max 100000] \
  [dict create name hd3 type INCLUSIVE regex {g_sl\[3\]\.g_hd\.g_tx9\.(u_qlw2[we]\.|u_qlr2[cwe]\.|tc\[)} boxes {{279.843 660.640 316.840 716.771}} min 1 max 100000] \
  [dict create name hd4 type INCLUSIVE regex {g_sl\[4\]\.g_hd\.g_tx9\.(u_qlw2[we]\.|u_qlr2[cwe]\.|tc\[)} boxes {{242.845 716.771 279.843 772.901}} min 1 max 100000] \
  [dict create name hd5 type INCLUSIVE regex {g_sl\[5\]\.g_hd\.g_tx9\.(u_qlw2[we]\.|u_qlr2[cwe]\.|tc\[)} boxes {{242.845 772.901 279.843 829.032}} min 1 max 100000] \
  [dict create name hd6 type INCLUSIVE regex {g_sl\[6\]\.g_hd\.g_tx9\.(u_qlw2[we]\.|u_qlr2[cwe]\.|tc\[)} boxes {{279.843 716.771 316.840 772.901}} min 1 max 100000] \
  [dict create name hd7 type INCLUSIVE regex {g_sl\[7\]\.g_hd\.g_tx9\.(u_qlw2[we]\.|u_qlr2[cwe]\.|tc\[)} boxes {{279.843 772.901 316.840 829.032}} min 1 max 100000] \
  [dict create name l2c type INCLUSIVE regex {\.g_l2c\.u_qlw2c\.} boxes {{242.845 660.640 279.843 716.771}} min 1 max 100000] \
  [dict create name rsw type EXCLUSIVE regex {(g_col_land\.u_qlw1sw\.|(g_rqr\.(genblk[0-9]+\.g_col_roots\.gs|gs_q)\[([0-9]|[1-9][0-9]|[1-4][0-9][0-9]|50[0-9]|51[01])\]|g_rph\.g_rb\[[0-2]\]\.g_single\.g_col\[0\]\.g_lrr\.rq))} boxes {{200.800 32.176 214.900 382.688}} min 1 max 100000] \
  [dict create name rnw type EXCLUSIVE regex {(g_col_land\.u_qlw1nw\.|(g_rqr\.(genblk[0-9]+\.g_col_roots\.gn|gn_q)\[([0-9]|[1-9][0-9]|[1-4][0-9][0-9]|50[0-9]|51[01])\]|g_rph\.g_rb\[[34]\]\.g_single\.g_col\[0\]\.g_lrr\.rq))} boxes {{200.800 396.688 210.000 659.040}} min 1 max 100000] \
  [dict create name rse type EXCLUSIVE regex {(g_col_land\.u_qlw1se\.|(g_rqr\.(genblk[0-9]+\.g_col_roots\.gs|gs_q)\[|g_rph\.g_rb\[[0-2]\]\.g_single\.g_col\[1\]\.g_lrr\.rq))} boxes {{243.100 32.176 257.200 382.688}} min 1 max 100000] \
  [dict create name rne type EXCLUSIVE regex {(g_col_land\.u_qlw1ne\.|(g_rqr\.(genblk[0-9]+\.g_col_roots\.gn|gn_q)\[|g_rph\.g_rb\[[34]\]\.g_single\.g_col\[1\]\.g_lrr\.rq))} boxes {{248.400 396.688 257.200 659.040}} min 1 max 100000] \
  [dict create name lsw type EXCLUSIVE regex {g_col_land\.u_qlr1sw\.} boxes {{214.900 32.176 229.000 382.688}} min 1 max 100000] \
  [dict create name lse type EXCLUSIVE regex {g_col_land\.u_qlr1se\.} boxes {{229.000 32.176 243.100 382.688}} min 1 max 100000] \
  [dict create name lnw type EXCLUSIVE regex {g_col_land\.u_qlr1nw\.} boxes {{210.000 412.704 219.000 659.040}} min 1 max 100000] \
  [dict create name lne type EXCLUSIVE regex {g_col_land\.u_qlr1ne\.} boxes {{239.800 412.704 248.400 659.040}} min 1 max 100000] \
  [dict create name dw type EXCLUSIVE regex {(u_me\.s2_w\[([0-9]|[1-9][0-9]|[1-9][0-9][0-9]|10[01][0-9]|102[0-3])\]|(g_hd\.g_tx\.g_r\[0\]\.di\[(16[0-9]|17[0-5]|19[2-9]|20[0-7]|22[4-9]|23[0-9]|25[6-9]|26[0-9]|27[01])\]|u_me\.g_operand_rr\.g_lsel\.s1b_(wsrc_w|gm_w\[)|u_me\.g_operand_rr\.g_csel\.(wsrc_q|gm_q)\[([0-9]|1[0-5])\]|u_me\.mq_wrom\[([0-9]|[1-9][0-9]|[1-4][0-9][0-9]|50[0-9]|51[01])\]|g_hd\.g_tx\.tc\[(12[89]|1[3-9][0-9]|2[0-4][0-9]|25[0-5])\]))} boxes {{219.000 412.704 229.400 659.040}} min 1 max 100000] \
  [dict create name de type EXCLUSIVE regex {(u_me\.s2_w\[|(g_hd\.g_tx\.g_r\[0\]\.di\[(28[89]|29[0-9]|30[0-3]|32[0-9]|33[0-5]|35[2-9]|36[0-7]|38[4-9]|39[0-9])\]|u_me\.g_operand_rr\.g_lsel\.s1b_(wsrc_e|gm_e\[)|u_me\.g_operand_rr\.g_csel\.(wsrc_q|gm_q)\[|u_me\.mq_wrom\[|g_hd\.g_tx\.tc\[(25[6-9]|2[6-9][0-9]|3[0-7][0-9]|38[0-3])\]))} boxes {{229.400 412.704 239.800 659.040}} min 1 max 100000] \
  [dict create name land_xm9 type FREE regex {\.g_xm9\.u_xr\.} boxes {} min 1 max 100000] \
  [dict create name land_top type FREE regex {^(u_ot_pr_core\.)?u_g\.u_tile\.(n_va|fault_q)$} boxes {} min 0 max 4] \
  [dict create name ctl type FREE regex {^(u_ot_pr_core\.)?u_g\.u_tile\.} boxes {} min 1 max 100000] \
]
source /src/tools/qwen_romleaf/rc14_2000/baseline/parent_regions.tcl
