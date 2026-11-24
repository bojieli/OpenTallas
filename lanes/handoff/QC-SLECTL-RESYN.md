# QC-SLECTL-RESYN handoff (lane memory)
Job (COORD 20:25): sle_ctl__cla4f6f12f (12 partitions) depth row per FABLE-RC-QC b839f90a; method = QC-TTC-RETIME (comb ABC resynth, flops kept, comb LEC, un-keep), place+CTS probe epyc11, pass CTS post-hook TT >= -42.
Parent QC-ALLFIX; row goes back to QC-ALLFIX (base C1c 3b12251bfd6c epyc7 QC-ALLFIX/rows_c/plan_c1_fix2s.json).
Findings 20:3x:
- In the C1b/compose-A kit u_bound.u_u_ctl (qfd_dv_s5_ctl_repair4_leaf) and u_bound.u_u_tap (qfd_dv_s8_tap_bounded) are HARD MACROS (LEF+lib in kit macros/), signed standalone 11-14: repair4_leaf TT +57.15 / hold +5.03 (epyc2 qc-cores-head/eco_rep4v/i1, form d), tap_bounded TT +15.3 (epyc9 tl-qcstap, form e). Their internal depth is invisible to sle_ctl STA except via lib arcs.
- V2+lockup proof (epyc7 lockup-station-r3/qcproof, 4_cts_post_hook.rpt) worst paths: r8b_strap_r8pad_u_rp_chd_q_1 -> ist_x_su_c_p1_o_0 (-93.27), start_i/arst_n port->reg (-86.7), x_hc1_st_b_i -> cland (-55.8), cws2_i -> cland (-40). None touch u_u_ctl/u_u_tap.
- Full endpoint STA on 4_1_cts.odb: epyc7 /srv/opentallas-scratch2/claude/QC-SLECTL-RESYN/sta_v2 (sta_ep.sh, read-only kit mount).
- Compose-A sle_ctl probe: epyc8 ot-job sle_ctl__cla4f6f12f-place-outgoing-giraffe-2746461-1795488783/work, in GPL at 20:2x.
RESULT 1 posted 20:26 (hub a18704f8): no resynth row. V2 4_1_cts.odb STA (platform RC, WS -134 vs rpt -93.27): 1179 viol endpoints, 0 u_ctl (worst u_ctl pin +4.65), 1 u_tap (rst_n -106, reset reach + macro ck -18 vs 253). Worst 20: 15 r8b_strap_r8pad_u_rp_chd_q_1 -> u_u_rp wgrp -> ist_x_su_c_p1/p2; 4 x_hc1_st_b_i -> cland.
Tools: epyc7 /srv/opentallas-scratch2/claude/QC-SLECTL-RESYN/{sta_ep.sh KIT ODB SDC OUTDIR TAG, classify.py PATHSFILE}.
Next: compose-A probe CTS -> run sta_ep.sh + classify on its 4_1_cts.odb (waiter on hub spec dir).
20:28 FABLE-RC-QC DROPPED the depth row; asked for full census grouped + C1c coverage + compose-A side by side.
RESULT 2 posted 20:32 (b05a7814): census on kit rcx (sta_sum_rcx.sh KIT ODB SDC OUTDIR TAG -> TAG.rcx.sum/.hold; census.py SUM [TH]); locs.sh KIT ODB OUTDIR (locs.tcl instance bboxes).
Groups: rp chd_q pad -> ist_x_su_c_p1 (58, -93) / p2 (262, -46); x_hc1_st_b_i->cland (404, -56); cws2_i->cland (181, -40); rrl_254->u_tap rst_n (-61).
Pending: compose-A probe CTS (epyc8 ot-job ...place-outgoing-giraffe-2746461...), run sta_sum_rcx + census + locs on its 4_1_cts.odb (results dir name dp_sle_ctl__cla4f6f12f?).
