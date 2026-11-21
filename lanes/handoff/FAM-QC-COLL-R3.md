# FAM-QC-COLL-R3 handoff (successor of FAM-QC-COLL-R2; started 11-21 12:4x PST)
Family: QC coll unsigned = coll_core (rep), coll_ftc. Plan rows -> QC-PLAN-R11 (V3, row cut 11-22 06:00 PST).
Read FAM-QC-COLL-R2.md first (R2 rows: rows_bcd.json, rows_reset_v3.json, fix14.json).

## Live units / waiters (13:3x)
1. pkit7 (coll_core private, V2 + 6 defines, wave env): run-item intel2 pid 973964 (spec fam-qc-coll/pspec7). Place DONE rc 0 12:59
   (2_2_floorplan_macro passed: aaa1dcff ring-path fix holds, no MPL-0020). Geom stage on epyc10 since 12:59. Kit epyc10 fam-qc-coll/pkit7/gen/coll_core.
   Waiter: ot-wait 973964 --cmdline run-item (out FAM-QC-COLL-R3/pkit7_runitem.wait on intel2). run-item ends at geom; route is queued after it.
2. V2 coll_ftc wave a1: run-item ended 13:18 at geom (result PASS, place_async). The KIT MOVED TO epyc8 (copy-back), not epyc7:
   epyc8 .../s29q103S4Q9N46R6V2/items/coll_ftc/gen/coll_ftc. R2's epyc7 waiters will never fire. Waiter: ot-wait --kit <that> --host epyc8 --stage grt (intel2).
   Auto-geom FAIL (advisory): fill 0.035, pin_reg_p90 257, pin_reg_max 497, r2r 881 um x66, partial_face 1; REACH scan 5 bits over 405 (2 fclk_out forwarded clocks = R2 fix14 rule-4 rows; u_rrl_70 reset leg).
3. A/B pkit8 LIVE 13:4x: pkit7 + OT_KEEP_WIRES += ot_reset_sync:reset_pipe qfd_static_ch546:r_reset_meta. Spec intel2 fam-qc-coll/pspec8, run-item intel2 pid 911570
   (log fam-qc-coll/pkit8_run.log), kit epyc8 fam-qc-coll/pkit8 (epyc10 DRAINING). Tree recomposed on epyc8 from R2 packs pk5/pk6 (epyc8 fam-qc-coll/mktree_e8.sh; TREE_OK, sha = epyc10).
   Waiter: ot-wait 911570 --cmdline run-item. Check after synth: no reset_pipe merge (face_0 u_rx.r_reset_q[0] loads 719 -> ~6).

## Findings
- MERGED FLOPS (coll_core, pkit7 synth 1_2_yosys.v): opt_merge folded every ot_reset_sync reset_pipe (async_reg, no keep) - the 4 qfd_static_ch546 u_wreset
  (face0/1 rx/tx) + face/linkcal syncs - into face_0 u_rx.r_reset_q[0] (the kept copy). One flop drives 719 RESETN pins across both faces
  (published/seen of all 4 channels + rxcal), against the RTL intent "one reset capture point per domain". No u_wreset flop survives.
  Not merged: reset relay tree (871 ot_dp_rrelay + 138 ot_dp_rgate = all 508 tree relays + srl), ot_dp_st stations (kept hierarchy), ot_dp_dly pads (14,405/14,434; the 29 missing are constant bits).
  Class fix belongs in FLOW-OPS-1300 no-merge default (async_reg => keep). Kit-level fix = the pkit8 A/B env.
- GEOM (coll_core advisory FAIL macro_channels, W channel 4.33 um): this is FABLE-PD-QC-1230 11-19 sec 1 root cause, still unfixed in V2: fold slices
  g_xf_0 / g_pf_3 at x 8.64 (512 src pins on W face, M4, 4.3 um to edge), g_xf_1 at 203.04 (4.3 um slot), g_xf_2/3 at 406.08 (13 um slot).
  V3 rows: lanes/handoff/FAM-QC-COLL-R3-rows_wall_v3.json (g_xf_0+g_pf_3 x 51.84, g_xf_1 289.92, g_xf_2+g_xf_3 528.0, g_sring column 449.28 -> 530 (needed: sring[4] would overlap g_xf_1),
  lpad_rec_rx_s0 site x 200 re-derived). No overlaps, inside core. Needs a private bind + kit proof (next build after pkit7/pkit8 read).
- Reset reach: R2 rows_reset_v3.json stands (stale raw names; every hop <= 405). If the V3 bind re-solves resets at the 300 um default for new binds (OWNER 11-20 #6),
  8 coll_ftc local hops at 306-400 um (start_0/23 354.5, start_2/3/16 400.3, start_13 379.5, start_18 339.5, start_22 306.5) get re-solved: re-check names after the V3 bind.
