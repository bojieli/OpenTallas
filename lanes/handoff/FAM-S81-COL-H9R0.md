# FAM-S81-COL-H9R0 handoff (fresh lane 11-24 07:45 PST, Opus 5.5)
Job: close S81 col_h9. (1) i2 structural cause + fix; (2) t12 count check; (3) col_h9_r2 FF-LIB-RESIGN-C8.
## 08:15 PST state
- i2 = col_h9_r0_p2 cl9f71e63d pv11b73b67 (event 224567138ab) eco_20261121_154936_3396612 i2 TT -173.92; checkpoint E11 fam-s81-col-h9r0-r4/e10_checkpoint_1124; live job dir epyc10 ot-jobs/col_h9_r0_p2__t1__cl9f71e63d__pv11b73b67-route-civil-redfish-3353389-1795233999 (i3t DRT iter 39, 1212 viol; keep, no cancel rule).
  Classes (i2 signoff/tt/ep_tt.tsv): xo3_1->bout_xo_o0 -174; xo g_rsreg.rq recovery -123; e1_u_w -103; bs0 -103. All fixed in J8+ (xo depth 3, OT_KEEP_WIRES ot_s81_rly:rq + ot_dp_dly:r, J9 v3 rows).
  J8+keep probe (epyc8 ..._1122205226) residual: src_3880_q -> u_t0.c0 GRT TT -165.02.
- ROW COL-H9R0-SRCSTAGE b08411015f11: intel2+epyc9 /srv/opentallas-scratch2/claude/fam-s81-col-h9r0/rows_COL-H9R0-SRCSTAGE_c8.json (gen srcstage_rows.py + h9r0_j9_rows.py there). 240 relay_sites adds, 60 types, legs 401/401/267. Asked INT for c9/c10 intake. Not yet PRE-gated (relay_sites add only).
- Live epyc8 pva4376595 ECO i2 (prd i2, R5-adopted) still running: read its signoff when it ends (i1 was bs0 -225, e1_u_w -94 = pre-keep kit, J9 fixes).
- t12 = slice_station__t12 record e5b40f88: SIGNED, counts (already counted, 485 unchanged).
- FF-LIB: both col_h9_r2 types (clce45cab5 pv7a260fc0, cl774acf45 pv11b6518d) in c8 LAUNCH class (epyc9 s81-allfix-int/tmp/c8_launch_classes.json idx 185/154); asked INT to launch them first at C8 KITS GO. Then: read signoff (internal FF hold >= 0 on corrected libs).
## Next
1. Watch INT for C8 KITS GO; verify the 2 r2 kits launch first; read their sign-off.
2. Get SRCSTAGE into an intake; verify next col_h9_r0 kit log "OT_RELAY_SITES ... unmatched" has 0 src keys missing, and that the t0.c0 TT is >= -42.
## 08:4x PST (COORD: gate the row myself)
- Done: old i3t cancelled (unit oth-ubuntu-3352969-1795233997, AP_RC 143); stray INT tmp/h9r0_insp.py ot-deleted.
- Fork c8seal_tree -> epyc11 /srv/opentallas-scratch2/claude/fam-s81-col-h9r0/c8_tree: ot-tree-fork pid 2707180 on intel2 (log ~/fam-s81-col-h9r0/fork_c8.log; ot-run refused ISOLATION so run direct per rules).
- Then: ot-run --hosts epyc11 --dir <lane dir> bash gate_src.sh (apply rows -> PRE baseline c8 -> elab strict -> scoped strict 60 col_h9_r0). Log gate_src/.
- Then rep kit p2 col_h9_r0_p2__t1__cl9f71e63d__pva4376595 via kit_wave private-spec (template intel2 fam-s81-col-h9r0-r4/tmp/sealed_launch.sh; --tree c8_tree --bind-out .../native_bind/srcstage_out --goal route --src-manifest seal).
- Then post ROW-REBASED to INT (flag p3/p6 names from placed_scan).
- 08:5x: E11-IO-STALL: first fork (jobs 8) stopped at 7.2 GB, partial ot-deleted; re-fork --jobs 2 OT_TREE_FORK_STREAMS=2 intel2 pid 3271368 log ~/fam-s81-col-h9r0/fork_c8_j2.log. Never fork at high parallelism (one fork per source disk).
- 09:0x: fork RETARGETED to epyc7 (COORD: E11 saturated). E11 fork stopped (exact PIDs), partial ot-deleted. Fork now runs ON epyc7 (pid 1282367, OT_TREE_FORK_STREAMS=2 set locally: with --host the env is not passed, so 12 streams ran), log epyc7 fam-s81-col-h9r0/fork_c8_e7.log. Gate + rep kit on epyc7. gate_src.sh + rows copied to epyc7 lane dir.
- 09:2x FF-LIB: CTB epyc7 CORE-TAP-BUDGET/romhw_hold_1124: clce45cab5 -36.47 (u_e13w.u_view, corrected lib), cl774acf45 -11.43 (s12/cfg->bs12/i_cfg, old libs too). Sign-off record d4e02e42 own census core_n 0; CTB uses 6_final.sdc, sign-off used golden.sdc + core_taps_ff.sdc -> constraint artefact likely. Ruling posted: record stands; both re-sign via fresh c8 kits (front of list); watch cl774acf45 hold in that kit.
- 09:58 fork done (epyc7 c8_tree 103.46 GB, 2 streams, 65 min). Gate launched: intel2 ot-run client 1176777 (log ~/fam-s81-col-h9r0/gate_src.otrun.log), queued on epyc7 load; outputs epyc7 fam-s81-col-h9r0/gate_src/{pre,elab,scope_bind}.log, bind_out c8_tree/.../native_bind/srcstage_out. Waiter b2f0a40xi.
- 11-24 11:32 P3-PILE posted: p3 pv1489a898 GRT overflow = POINT-seated u_lpad_xo_i0 1104-bit rank at (1442.88,653.96) beside u_cf NE corner; c8 RANK-SEAT puts it on 122-180 um 45-deg lines (checked rl2.py on epyc7 lane dir). TODO at p2 kit place: grep RANK-SEAT xo_i0 in istations.tcl + lpad spread in ot_face_flops.txt. Gate gate_src running on epyc7 (PRE stage), waiter b2f0a40xi.
- 11-24 11:36 SEATLIFT not needed: p4-p6 seats y662.556 sit 14.6 um above their u_cf (top 648.0); seatchk.py (epyc7 lane dir) 0 BAD on c8 and c8+SRCSTAGE. Draft rows_COL-H9R0-SEATLIFT_c8.json (epyc7) is NOT for INT: it shortens the lines to 86 um. TODO: p2 kit RANK-SEAT/spread check; relaunch p3 on c8 GO.
- 11-24 14:53 STATE: 48/60 col_h9_r0 in INT c8s_sent (stream PAUSED kit_rtl 14:32); p6 x12 missing -> list handed to INT. p2 private runitem waits on gate_src PRE (epyc7 oth-ubuntu-1113861, waiter b2f0a40xi).
