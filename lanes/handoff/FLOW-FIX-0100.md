# FLOW-FIX-0100 handoff (from FABLE-FLOW-2350)

Lane clone: intel2 /srv/opentallas-scratch2/claude/lanes/flow-fix-0100 (sparse worktree, tools rtl tests physical/common_flow).

| Item | State |
|---|---|
| 1 (f) GRT loop | PUSHED 851bfded63: gen_phys emits -congestion_iterations 10 (OT_GRT_CONG_ITERS=30 or 0 reverts); failfast_rules OT_GRT_ROUND_WALL_S (14400 s) and repair_timing no-progress (OT_FF_RT_*: pass = 100 rows, 2 passes under 5 percent WNS/TNS gain). Both stops print the existing OT_GRT_NOCONVERGE class line (PLAN design:grt_flat_overflow, no retry). Applies to kits generated after the push. |
| 2 (d) retry key | push4 running (ot-push-main log intel2 /tmp/ff0100-push4.log): `item@N:fix=<sha or row>` normalised in load_config into die field _retry_fix; plain item@N honoured only for INFRA failures; same input digest refused (RETRY-SAME-INPUT) and key dropped; Fixes-Items and pending rows carry their sha. |
| 3 watchdog | DONE. Cause: hub noprog-stage tick ran from ~/.local/lib/noprog and pushed its own stale copy to every host. noprog_stage now pushes rt/current pair (639df6b7b2). Lib pair installed on 7 hosts (copy+mv), 0 stage_odb_cap rows. Launcher ot-noprog-watchdog already execs rt/current (fixed). |
| 4 cancel-rows | Already on main (d475d5db47, FLEET-WATCH-2000): --event/--attempt. Test test_cancel_rows_exact.py PUSHED 4bd5db2a1a. |
| 5 (b) post routing | DONE in ~/coord (6fcaee7588): resolve_lane() in tools/post_redirect.py (case fold, LANE-STATUS, existing posts file), post.sh uses it (ot-run/ot-wait posts go through post.sh). Six lowercase twins merged into upper files; the lowercase files are now one-line pointers (ot-delete is tree-only; git rm them when allowed). |
| COORD extra | face_flops.tcl (the PRE_GLOBAL_PLACE hook cons_gpl_pre.tcl sources) now prints OT_FF_TIME per section (712cd5e5b4). Log evidence: face_flops.tcl 1582 s on dsdv_slice_c1x_C t3 (11097 pin regs) includes the hooks istations, reset_tree, reset_taps, core_out_land, place_regions. cons_gpl_pre.tcl itself only calls gpl::get_global_placement_uniform_density (cheap). Next: read OT_FF_TIME lines of the next S81 leaf kit, cut the dominant section. No cut made without a profile. |
