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
