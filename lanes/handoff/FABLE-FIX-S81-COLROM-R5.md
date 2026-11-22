# FABLE-FIX-S81-COLROM-R5 handoff (started 11-21 18:3x PST; successor of FABLE-FIX-S81-COLROM-R4)
Lane dir intel2 /srv/opentallas-scratch2/claude/fable-fix-s81-colrom-r5 (clone/ = lane clone cone tools, tmp/, runitem_e9.log/.pid).
History: lanes/handoff/FABLE-FIX-S81-COLROM-R4.md (J7 stage+guard GREEN in a6771d121e95; nothing owed for J7).

## Done
- src_manifest walk_tree dir-symlink bug FIXED on main b0e55c17a3fd (DIRLINK-1121; tests test_src_manifest_dirlink.py). Legacy manifests still verify.
- COORD STOP 18:5x: never replicate sealed trees with --link-from/--link-dest. Hardlinked epyc9 .part killed + ot-deleted. epyc9 now holds a REAL copy of
  sealed J7 kw45/src_s81_pin_3c913dbdfb23_d8j7_1117_work (replicate --tar; find -links +1 = 0; verify --ro OK 12af64d4f18d).

## Step 5 rep kit col_h10_r1__t1__cld01bb4ae (the "one placed J7-form col read") - RUNNING on epyc9
- Spec intel2 ~/coord/autopilot/private_specs/FABLE-FIX-S81-COLROM-R5/s81_col_h10_r1__t1__cld01bb4ae_1121190100/spec.json (sealed J7 tree, plan a6771d121e95,
  src_manifest on, rt 404887a342b0, --host epyc9). Older specs _1121184834 (intel2) and R4 candJ7cG were never launched.
- run-item: intel2 pid in fable-fix-s81-colrom-r5/runitem_e9.pid, log runitem_e9.log. Kit epyc9
  /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/a9ed808a98d/private/FABLE-FIX-S81-COLROM-R5/col_h10_r1__t1__cld01bb4ae_1121190100/gen/col_h10_r1__t1__cld01bb4ae
- PLACED 19:55. Placed read posted 20:1x (TT, placement RC, ideal clocks): WNS -2.33 (2 ends: cfg ROM u_c10_5 rd_out -> seq_bfp u_s10 q5, bfp has no q stage),
  ROM pval -> bn8 stage +69.58 (no late clock needed at ideal), ROM-pin ends +233.30, internal hold >= +4.2. Read script epyc9+intel2 fable-fix-s81-colrom-r5/tmp
  (placed_read.tcl/.sh; rerun on any stage odb by editing the ODB line; kit mounted read-only).
- NEXT: follow run-item through geom -> CTS -> GRT -> route -> sign-off. At post-hook CTS re-read pval stage with real clocks (ROM q lands late: if the bn8 stage
  fails with real clock add a pipeline stage, no skew). Read GRT timing from final 5_1_grt.odb only. No TT repair on ROM-pin ends. Gates DRC0, TT >= -42, FF hold >= 0, LEC.
  Sign-off -> standard export (AGIdock + rtx-pro), report COORD, hand the proof to S81-J6-ASSEMBLY-R5.
- FAM-S81-COL-H9R0-R4 owns col_h9_r0 rep: do not duplicate.
## Cleanup owed (ot-delete only)
- epyc10 /srv/opentallas-scratch3/claude/fable-fix-s81-colrom-r4/{candJ7cG,gate_j7g} after J7 applies (04:15 PST 11-22).
- intel2 fable-fix-s81-colrom-r4/stage (candJ7cG copy, superseded, never used).
- epyc9 J7 tree copy stays (wave gen host candidate for J7); tell FLEET/ASSEMBLY rather than delete.
