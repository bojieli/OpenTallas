# PATH-QC-NL 10-25 A0 NL v10 (variant c: sized control corridors) = Codex combined0719 NL regions with the control fences
# rebuilt.  combined0719 GPL-0307 (iter 200 ctl_is overflow 0.85 / ctl_xm 0.92): ctl_is (1,362 regs + 4,509 cone cells,
# 897 um2) and ctl_xm (2,952 regs + 7,304 cone cells, 1,570 um2) were fenced into the SAME L (ctl_is boxes lie wholly inside
# ctl_xm's: x441-455.7/y540-658.5 + the 9.9-um ROM/LSL strip), 2,467 um2 of cells in ~4,200 um2 at GPL target 0.5 -> no
# legal spread.  Data (NK R6 3_place, where these groups are FREE and pass density + hops): ctl_is regs x 365-452 /
# y 496-665, ctl_xm x 365-453 / y 532-820 (E margin beside the tap pins y 561-660 + the ROM row gap + the ROM/LSL strip).
# v10c: two DISJOINT fences on that footprint, each at <= 32 % fill:
#   ctl_is  E margin x441-455.7 y470-640 + ROM row gap rb4|rb3 col1 x330.3-441 y528.3-537.4   (3,506 um2, 26 %)
#   ctl_xm  E margin x441-455.7 y640-900 + ROM/LSL strip x330.3-441 y658.5-668.4            (4,918 um2, 32 %)
# split_fault (318,741) <= 405 um from every ctl_is box corner reachable (top 640 -> 231 um); tap pins y 561-660 inside.
# Every other group byte-identical to combined0719.
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
# generated: gen_a0c8_regions.py nl --e-orient MY --layout v8b
# CODEX 07:19 NL combined control-corridor/reset4 successor; v8c variant nl_l3rsvm (mkvar.py): split_fault midpoint box; S L1 readers lsw/lse y 300-383; t_vout_q in the W pin pocket; GPL routability-driven off (kit.env); flt2 tile_fault/fault_q box; blockages + ctl boxes; cones: hd0 hd1 hd2 hd3 hd4 hd5 hd6 hd7 l2c ctl_is ctl_xm
set qrl_groups [list \
  [dict create name land_rq type FREE regex {g_rom_pipe\.rq_(ce|ad)_[sn]\[1\]\[} boxes {} min 1 max 100000] \
  [dict create name fltq type INCLUSIVE regex {u_me\.fault_q\[} boxes {{150.000 980.232 200.000 989.544}} min 1 max 64] \
  [dict create name sfm type INCLUSIVE regex {u_logic\.u_me\.split_fault} boxes {{316.900 740.000 319.200 760.000}} min 1 max 1] \
  [dict create name flt2 type INCLUSIVE regex {^u_ot_pr_core\.u_g\.u_tile\.(tile_fault|fault_q)\$} boxes {{200.000 980.232 255.000 989.544}} min 2 max 2] \
  [dict create name vout type INCLUSIVE regex {g_toreg\.t_vout_q} boxes {{2.160 885.000 40.000 1015.000}} min 1 max 1] \
  [dict create name land_fault type FREE regex {u_me\.(fault_q\[|g_hier\.g_sl\[[0-7]\]\.g_hd\.g_fl\.q)} boxes {} min 0 max 200] \
  [dict create name f0 type INCLUSIVE regex {g_sl\[0\]\.g_hd\.(g_tx9\.g_r\[\d+\]\.u_tx/|g_lrr\.rq)} boxes {{79.656 673.920 95.056 753.920}} min 1 max 100000] \
  [dict create name o0 type INCLUSIVE regex {g_sl\[0\]\.g_hd\.(g_out9\.u_qlw3\.|g_out9\.u_qlr3\.)} boxes {{79.656 753.920 95.056 814.320}} min 1 max 100000] \
  [dict create name f1 type INCLUSIVE regex {g_sl\[1\]\.g_hd\.(g_tx9\.g_r\[\d+\]\.u_tx/|g_lrr\.rq)} boxes {{79.656 834.432 95.056 914.432}} min 1 max 100000] \
  [dict create name o1 type INCLUSIVE regex {g_sl\[1\]\.g_hd\.(g_out9\.u_qlw3\.|g_out9\.u_qlr3\.)} boxes {{79.656 914.432 95.056 974.832}} min 1 max 100000] \
  [dict create name f2 type INCLUSIVE regex {g_sl\[2\]\.g_hd\.(g_tx9\.g_r\[\d+\]\.u_tx/|g_lrr\.rq)} boxes {{79.656 974.832 95.056 994.944} {95.056 980.232 150.000 989.544}} min 1 max 100000] \
  [dict create name o2 type INCLUSIVE regex {g_sl\[2\]\.g_hd\.(g_out9\.u_qlw3\.|g_out9\.u_qlr3\.)} boxes {{79.656 1074.944 95.056 1135.344}} min 1 max 100000] \
  [dict create name f3 type INCLUSIVE regex {g_sl\[3\]\.g_hd\.(g_tx9\.g_r\[\d+\]\.u_tx/|g_lrr\.rq)} boxes {{319.240 673.920 330.064 753.920}} min 1 max 100000] \
  [dict create name o3 type INCLUSIVE regex {g_sl\[3\]\.g_hd\.(g_out9\.u_qlw3\.)} boxes {{319.240 753.920 330.064 814.320}} min 1 max 100000] \
  [dict create name q3 type INCLUSIVE regex {g_sl\[3\]\.g_hd\.g_out9\.u_qlr3\.} boxes {{150.000 819.720 200.000 829.032}} min 1 max 100000] \
  [dict create name f4 type INCLUSIVE regex {g_sl\[4\]\.g_hd\.(g_tx9\.g_r\[\d+\]\.u_tx/|g_lrr\.rq)} boxes {{305.840 834.432 316.840 914.432}} min 1 max 100000] \
  [dict create name o4 type INCLUSIVE regex {g_sl\[4\]\.g_hd\.(g_out9\.u_qlw3\.|g_out9\.u_qlr3\.)} boxes {{305.840 914.432 316.840 974.832}} min 1 max 100000] \
  [dict create name f5 type INCLUSIVE regex {g_sl\[5\]\.g_hd\.(g_tx9\.g_r\[\d+\]\.u_tx/|g_lrr\.rq)} boxes {{260.000 980.232 305.840 989.544} {305.840 974.832 316.840 994.944}} min 1 max 100000] \
  [dict create name o5 type INCLUSIVE regex {g_sl\[5\]\.g_hd\.(g_out9\.u_qlw3\.)} boxes {{305.840 1074.944 316.840 1135.344}} min 1 max 100000] \
  [dict create name q5 type INCLUSIVE regex {g_sl\[5\]\.g_hd\.g_out9\.u_qlr3\.} boxes {{305.840 994.944 316.840 1034.944}} min 1 max 100000] \
  [dict create name f6 type INCLUSIVE regex {g_sl\[6\]\.g_hd\.(g_tx9\.g_r\[\d+\]\.u_tx/|g_lrr\.rq)} boxes {{319.240 834.432 330.064 914.432}} min 1 max 100000] \
  [dict create name o6 type INCLUSIVE regex {g_sl\[6\]\.g_hd\.(g_out9\.u_qlw3\.|g_out9\.u_qlr3\.)} boxes {{319.240 914.432 330.064 974.832}} min 1 max 100000] \
  [dict create name f7 type INCLUSIVE regex {g_sl\[7\]\.g_hd\.(g_tx9\.g_r\[\d+\]\.u_tx/|g_lrr\.rq)} boxes {{319.240 994.944 330.064 1074.944}} min 1 max 100000] \
  [dict create name o7 type INCLUSIVE regex {g_sl\[7\]\.g_hd\.(g_out9\.u_qlw3\.)} boxes {{319.240 1074.944 330.064 1135.344}} min 1 max 100000] \
  [dict create name q7 type INCLUSIVE regex {g_sl\[7\]\.g_hd\.g_out9\.u_qlr3\.} boxes {{319.240 974.832 330.064 994.944}} min 1 max 100000] \
  [dict create name hd0 type INCLUSIVE regex {g_sl\[0\]\.g_hd\.g_tx9\.(u_qlw2[we]\.|u_qlr2[cwe]\.|tc\[)} boxes {{205.848 660.640 242.845 716.771}} min 1 max 100000] \
  [dict create name hd1 type INCLUSIVE regex {g_sl\[1\]\.g_hd\.g_tx9\.(u_qlw2[we]\.|u_qlr2[cwe]\.|tc\[)} boxes {{205.848 716.771 242.845 772.901}} min 1 max 100000] \
  [dict create name hd2 type INCLUSIVE regex {g_sl\[2\]\.g_hd\.g_tx9\.(u_qlw2[we]\.|u_qlr2[cwe]\.|tc\[)} boxes {{205.848 772.901 242.845 829.032}} min 1 max 100000] \
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
  [dict create name lsw type EXCLUSIVE regex {g_col_land\.u_qlr1sw\.} boxes {{214.900 300.000 229.000 382.688}} min 1 max 100000] \
  [dict create name lse type EXCLUSIVE regex {g_col_land\.u_qlr1se\.} boxes {{229.000 300.000 243.100 382.688}} min 1 max 100000] \
  [dict create name lnw type EXCLUSIVE regex {g_col_land\.u_qlr1nw\.} boxes {{210.000 412.704 219.000 659.040}} min 1 max 100000] \
  [dict create name lne type EXCLUSIVE regex {g_col_land\.u_qlr1ne\.} boxes {{239.800 412.704 248.400 659.040}} min 1 max 100000] \
  [dict create name dw type EXCLUSIVE regex {(u_me\.s2_w\[([0-9]|[1-9][0-9]|[1-9][0-9][0-9]|10[01][0-9]|102[0-3])\]|(g_hd\.g_tx\.g_r\[0\]\.di\[(16[0-9]|17[0-5]|19[2-9]|20[0-7]|22[4-9]|23[0-9]|25[6-9]|26[0-9]|27[01])\]|u_me\.g_operand_rr\.g_lsel\.s1b_(wsrc_w|gm_w\[)|u_me\.g_operand_rr\.g_csel\.(wsrc_q|gm_q)\[([0-9]|1[0-5])\]|u_me\.mq_wrom\[([0-9]|[1-9][0-9]|[1-4][0-9][0-9]|50[0-9]|51[01])\]|g_hd\.g_tx\.tc\[(12[89]|1[3-9][0-9]|2[0-4][0-9]|25[0-5])\]))} boxes {{219.000 412.704 229.400 659.040}} min 1 max 100000] \
  [dict create name de type EXCLUSIVE regex {(u_me\.s2_w\[|(g_hd\.g_tx\.g_r\[0\]\.di\[(28[89]|29[0-9]|30[0-3]|32[0-9]|33[0-5]|35[2-9]|36[0-7]|38[4-9]|39[0-9])\]|u_me\.g_operand_rr\.g_lsel\.s1b_(wsrc_e|gm_e\[)|u_me\.g_operand_rr\.g_csel\.(wsrc_q|gm_q)\[|u_me\.mq_wrom\[|g_hd\.g_tx\.tc\[(25[6-9]|2[6-9][0-9]|3[0-7][0-9]|38[0-3])\]))} boxes {{229.400 412.704 239.800 659.040}} min 1 max 100000] \
  [dict create name ctl_is type INCLUSIVE regex {u_logic\.(u_me\.(g_issue_fast|g_rr6|g_gm_fast|u_mt|g_gbc|base_k|cur\[|ts_r|wrom_addr|base_t|k_r|ktot_r|tiles_r|e_gm|e_split|pcnt|s1_tag|s1b_tag|j\[|jsh_r|s1_gm|e_first|e_round|e_wsrc|round_r|s1_round|s1_first|s1_wsrc|s1b_first|s1b_round|s2_first|s2_tag|wrom_re|wsrc_r)|ib_i\[|g_gocp|g_tidr|g_splitcp|go_i)} boxes {{441.000 470.000 455.700 640.000} {330.300 528.300 441.000 537.400}} min 1 max 100000] \
  [dict create name ctl_xm type INCLUSIVE regex {u_logic\.(g_xm9\.u_xr\.|u_me\.(mq_x|s2_x)\[)} boxes {{441.000 640.000 455.700 900.000} {330.300 658.500 441.000 668.400}} min 1 max 100000] \
  [dict create name land_xm9 type FREE regex {\.g_xm9\.u_xr\.} boxes {} min 0 max 100000] \
  [dict create name land_top type FREE regex {^(u_ot_pr_core\.)?u_g\.u_tile\.(n_va|fault_q)$} boxes {} min 0 max 4] \
  [dict create name ctl type FREE regex {^(u_ot_pr_core\.)?u_g\.u_tile\.} boxes {} min 1 max 100000] \
]
source /src/tools/qwen_romleaf/rc14_2000/baseline/parent_regions.tcl
