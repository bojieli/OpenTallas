# Q-ROMPARENT nk c1: TX roots in LSL strips (ck_tx4/5 entered from the S face up the col1/col2 channel); RQR column halves rsw/rnw (W gutter) + rse/rne (E gutter) and ROM-word/s2_w halves dw/de each own one plain rectangle beside their ROM column; ME ck in the east block
set qrl_groups [list \
  [dict create name tx0 type EXCLUSIVE regex {g_sl\[0\]\.g_hd\.(g_tx\.g_r\[[01]\]\.u_tx/|g_lrr\.rq)} boxes {{75.6 350.784 94.5 491.184}} min 781 max 781] \
  [dict create name tx1 type EXCLUSIVE regex {g_sl\[1\]\.g_hd\.(g_tx\.g_r\[[01]\]\.u_tx/|g_lrr\.rq)} boxes {{75.6 188.352 94.5 328.752}} min 781 max 781] \
  [dict create name tx2 type EXCLUSIVE regex {g_sl\[2\]\.g_hd\.(g_tx\.g_r\[[01]\]\.u_tx/|g_lrr\.rq)} boxes {{75.6 25.92 94.5 166.32}} min 781 max 781] \
  [dict create name tx3 type EXCLUSIVE regex {g_sl\[3\]\.g_hd\.(g_tx\.g_r\[[01]\]\.u_tx/|g_lrr\.rq)} boxes {{305.316 350.784 324.216 491.184}} min 781 max 781] \
  [dict create name tx4 type EXCLUSIVE regex {g_sl\[4\]\.g_hd\.(g_tx\.g_r\[[01]\]\.u_tx/|g_lrr\.rq)} boxes {{305.316 188.352 324.216 328.752}} min 781 max 781] \
  [dict create name tx5 type EXCLUSIVE regex {g_sl\[5\]\.g_hd\.(g_tx\.g_r\[[01]\]\.u_tx/|g_lrr\.rq)} boxes {{305.316 25.92 324.216 166.32}} min 781 max 781] \
  [dict create name tx6 type EXCLUSIVE regex {g_sl\[6\]\.g_hd\.(g_tx\.g_r\[[01]\]\.u_tx/|g_lrr\.rq)} boxes {{435.24 188.352 455.76 328.752}} min 781 max 781] \
  [dict create name tx7 type EXCLUSIVE regex {g_sl\[7\]\.g_hd\.(g_tx\.g_r\[[01]\]\.u_tx/|g_lrr\.rq)} boxes {{435.24 25.92 455.76 166.32}} min 781 max 781] \
  [dict create name rsw type EXCLUSIVE regex {g_rqr\.gs_q\[([0-9]|[1-9][0-9]|[1-4][0-9][0-9]|50[0-9]|51[01])\]} boxes {{3.0 600.0 50.0 760.0}} min 512 max 512] \
  [dict create name rnw type EXCLUSIVE regex {g_rqr\.gn_q\[([0-9]|[1-9][0-9]|[1-4][0-9][0-9]|50[0-9]|51[01])\]} boxes {{3.0 780.0 50.0 960.0}} min 512 max 512] \
  [dict create name rse type EXCLUSIVE regex {g_rqr\.gs_q\[} boxes {{407.5 600.0 452.5 760.0}} min 512 max 512] \
  [dict create name rne type EXCLUSIVE regex {g_rqr\.gn_q\[} boxes {{407.5 780.0 452.5 960.0}} min 512 max 512] \
  [dict create name dw type EXCLUSIVE regex {(u_me\.mq_wrom\[([0-9]|[1-9][0-9]|[1-4][0-9][0-9]|50[0-9]|51[01])\]|g_hd\.g_tx\.tc\[(12[89]|1[3-9][0-9]|2[0-4][0-9]|25[0-5])\])} boxes {{3.0 505.0 50.0 590.0}} min 1024 max 1024] \
  [dict create name de type EXCLUSIVE regex {(u_me\.mq_wrom\[|g_hd\.g_tx\.tc\[(25[6-9]|2[6-9][0-9]|3[0-7][0-9]|38[0-3])\])} boxes {{407.5 505.0 452.5 590.0}} min 1024 max 1024] \
  [dict create name hub type EXCLUSIVE regex {^u_g\.u_tile\.} boxes {{354.0 390.0 414.0 450.0}} min 2348 max 2348] \
]
# s2_w: Yosys names the REGROOT weight-operand flops after the TX wire they drive (g_sl[g].g_hd.g_tx.tc[b]):
# b in [128,256) = lanes of groups 0,1 = west ROM column, [256,384) = east (tx_d = {v,first,split,w_in,x}).
source /src/tools/qwen_romleaf/parent_regions.tcl
# hub = every sequential cell on root ck in the odb (NK 2348 / NL 2861, measured at GPL in gate c1r; the gate clock_rule count 3694/4207 includes non-flop clock pins)
# c1r4 (Q-ROMPARENT-2): every soft-root region EXCLUSIVE.  Every gate with an INCLUSIVE group broke RePlAce
# (b1 GPL-0305, b2 DPL stall, c1r2 NK GPL-0305 / NL 230k buffers, c1r3 cells piled in die corners and over the ROM
# leaves), while EXCLUSIVE-only b3 placed cleanly.  hub box shrunk to 60 x 60 um around the old hub centre (flop fill
# ~19 %) so the ME logic that cannot enter the box sits within ~30 um of its flops.
