# Q-ROMPARENT nk c1: TX roots in LSL strips (ck_tx4/5 entered from the S face up the col1/col2 channel); RQR column halves rsw/rnw (W gutter) + rse/rne (E gutter) and ROM-word/s2_w halves dw/de each own one plain rectangle beside their ROM column; ME ck in the east block
set qrl_groups [list \
  [dict create name land_tx type FREE regex {g_hd\.g_tx\.g_r\[0\]\.u_tx/} boxes {} min 3120 max 3120] \
  [dict create name land_rq type FREE regex {g_rom_pipe\.rq_(ce|ad)_[sn]\[1\]\[} boxes {} min 1 max 64] \
  [dict create name land_fault type FREE regex {u_me\.fault_q\[} boxes {} min 1 max 5] \
  [dict create name tx0 type EXCLUSIVE regex {g_sl\[0\]\.g_hd\.(g_tx\.g_r\[1\]\.u_tx/|g_lrr\.rq)} boxes {{75.6 350.784 94.5 491.184}} min 391 max 391] \
  [dict create name tx1 type EXCLUSIVE regex {g_sl\[1\]\.g_hd\.(g_tx\.g_r\[1\]\.u_tx/|g_lrr\.rq)} boxes {{75.6 188.352 94.5 328.752}} min 391 max 391] \
  [dict create name tx2 type EXCLUSIVE regex {g_sl\[2\]\.g_hd\.(g_tx\.g_r\[1\]\.u_tx/|g_lrr\.rq)} boxes {{75.6 25.92 94.5 166.32}} min 391 max 391] \
  [dict create name tx3 type EXCLUSIVE regex {g_sl\[3\]\.g_hd\.(g_tx\.g_r\[1\]\.u_tx/|g_lrr\.rq)} boxes {{305.316 350.784 324.216 491.184}} min 391 max 391] \
  [dict create name tx4 type EXCLUSIVE regex {g_sl\[4\]\.g_hd\.(g_tx\.g_r\[1\]\.u_tx/|g_lrr\.rq)} boxes {{305.316 188.352 324.216 328.752}} min 391 max 391] \
  [dict create name tx5 type EXCLUSIVE regex {g_sl\[5\]\.g_hd\.(g_tx\.g_r\[1\]\.u_tx/|g_lrr\.rq)} boxes {{305.316 25.92 324.216 166.32}} min 391 max 391] \
  [dict create name tx6 type EXCLUSIVE regex {g_sl\[6\]\.g_hd\.(g_tx\.g_r\[1\]\.u_tx/|g_lrr\.rq)} boxes {{435.24 188.352 455.76 328.752}} min 391 max 391] \
  [dict create name tx7 type EXCLUSIVE regex {g_sl\[7\]\.g_hd\.(g_tx\.g_r\[1\]\.u_tx/|g_lrr\.rq)} boxes {{435.24 25.92 455.76 166.32}} min 391 max 391] \
  [dict create name rsw type EXCLUSIVE regex {(g_rqr\.(genblk[0-9]+\.g_col_roots\.gs|gs_q)\[([0-9]|[1-9][0-9]|[1-4][0-9][0-9]|50[0-9]|51[01])\]|g_rph\.g_rb\[[0-2]\]\.g_single\.g_col\[0\]\.g_lrr\.rq)} boxes {{3.0 600.0 45.0 760.0}} min 515 max 515] \
  [dict create name rnw type EXCLUSIVE regex {(g_rqr\.(genblk[0-9]+\.g_col_roots\.gn|gn_q)\[([0-9]|[1-9][0-9]|[1-4][0-9][0-9]|50[0-9]|51[01])\]|g_rph\.g_rb\[[34]\]\.g_single\.g_col\[0\]\.g_lrr\.rq)} boxes {{3.0 780.0 45.0 960.0}} min 514 max 514] \
  [dict create name rse type EXCLUSIVE regex {(g_rqr\.(genblk[0-9]+\.g_col_roots\.gs|gs_q)\[|g_rph\.g_rb\[[0-2]\]\.g_single\.g_col\[1\]\.g_lrr\.rq)} boxes {{413.0 600.0 452.5 760.0}} min 515 max 515] \
  [dict create name rne type EXCLUSIVE regex {(g_rqr\.(genblk[0-9]+\.g_col_roots\.gn|gn_q)\[|g_rph\.g_rb\[[34]\]\.g_single\.g_col\[1\]\.g_lrr\.rq)} boxes {{413.0 780.0 452.5 960.0}} min 514 max 514] \
  [dict create name dw type EXCLUSIVE regex {(u_me\.g_operand_rr\.g_lsel\.s1b_(wsrc_w|gm_w\[)|u_me\.mq_wrom\[([0-9]|[1-9][0-9]|[1-4][0-9][0-9]|50[0-9]|51[01])\]|g_hd\.g_tx\.tc\[(12[89]|1[3-9][0-9]|2[0-4][0-9]|25[0-5])\])} boxes {{3.0 505.0 45.0 590.0}} min 1025 max 1027] \
  [dict create name de type EXCLUSIVE regex {(u_me\.g_operand_rr\.g_lsel\.s1b_(wsrc_e|gm_e\[)|u_me\.mq_wrom\[|g_hd\.g_tx\.tc\[(25[6-9]|2[6-9][0-9]|3[0-7][0-9]|38[0-3])\])} boxes {{413.0 505.0 452.5 590.0}} min 1025 max 1027] \
  [dict create name hub type EXCLUSIVE regex {^u_g\.u_tile\.} boxes {{354.0 390.0 414.0 450.0}} min 2284 max 2348] \
]
# s2_w: Yosys names the REGROOT weight-operand flops after the TX wire they drive (g_sl[g].g_hd.g_tx.tc[b]):
# b in [128,256) = lanes of groups 0,1 = west ROM column, [256,384) = east (tx_d = {v,first,split,w_in,x}).
source /src/tools/qwen_romleaf/parent_regions.tcl
# hub = every sequential cell on root ck in the odb (NK 2348 / NL 2861, measured at GPL in gate c1r; the gate clock_rule count 3694/4207 includes non-flop clock pins)
# c1r4 (Q-ROMPARENT-2): every soft-root region EXCLUSIVE.  Every gate with an INCLUSIVE group broke RePlAce
# (b1 GPL-0305, b2 DPL stall, c1r2 NK GPL-0305 / NL 230k buffers, c1r3 cells piled in die corners and over the ROM
# leaves), while EXCLUSIVE-only b3 placed cleanly.  hub box shrunk to 60 x 60 um around the old hub centre (flop fill
# ~19 %) so the ME logic that cannot enter the box sits within ~30 um of its flops.
# c1r6 NK: gutter regions flush with the ROM-leaf halo (x 50.76 / 407.16) and core edge (2.16 / 455.76), as NL c1r5.
# c1r7 NK: flush boxes (c1r6) crashed DPL improve_placement ("bad optional access"); gutter boxes now inset with a 5.76 um channel to the ROM-leaf halo (W 3.0-45.0, E 413.0-452.5): no sliver, no coincident boundary.
# c1r8 (REGROOT 2): the ten ROM-leaf reset relays (g_rb[b].g_single.g_col[c].g_lrr.rq) join the gutter region of
# their clock root: W-south rsw (b0-2 c0), W-north rnw (b3-4 c0), E-south rse/ck_rs (b0-2 c1), E-north rne/ck_rn (b3-4 c1).
# Q-A0KIT 10-18: main RTL (ba6ef8ae1 GLUE_HARD) renamed the column RQR registers gs_q/gn_q -> g_rqr.genblk1.g_col_roots.gs/gn
# (c1r9b NL: rsw owned 3 of 515); the r-group regexes accept both spellings.  Membership checked on the c1r9b yosys netlist.
# Q-A0FIX2 10-19 (c1r9f): c1r9e --cts FAILED only cross_clock (CX-IJ-ROOT gate, 150 ps distinct-entry reserve): every
# failing entry pair was a > 405 um hop boxed at both ends (hub/gutter -> TX rung 0 in the TX box, hub ROM relay ->
# leaf pins up to 700 um, LSL fault pins -> hub fault_q 600 um).  The landing register of each hop is now FREE (claimed,
# no box: placed between its driver and loads): TX rung 0 (tx boxes keep rung 1 + relay = 391), ROM request relay
# stage 1, fault_q.  REGROOT 3 RTL: per-half S1B select copies (s1b_wsrc_*/s1b_gm_*) join dw/de (1024 + 3).  hub keeps
# the rest (old count minus the freed relay/fault flops; exact counts printed as QRL_REGION).
