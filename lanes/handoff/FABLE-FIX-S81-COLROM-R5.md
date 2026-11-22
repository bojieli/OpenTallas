# FABLE-FIX-S81-COLROM-R5 handoff (started 11-21 18:3x PST; successor of FABLE-FIX-S81-COLROM-R4)
Lane dir intel2 /srv/opentallas-scratch2/claude/fable-fix-s81-colrom-r5 (clone/ = lane clone cone tools, tmp/).
History: lanes/handoff/FABLE-FIX-S81-COLROM-R4.md (J7 stage+guard GREEN in a6771d121e95; nothing owed for J7).

## Done
- src_manifest walk_tree dir-symlink bug FIXED on main b0e55c17a3fd (DIRLINK-1121; tests test_src_manifest_dirlink.py). Legacy manifests still verify.

## Step 5 rep kit col_h10_r1__t1__cld01bb4ae (also the "one placed J7-form col read" J7 col-release proof)
- Spec (use THIS one): intel2 ~/coord/autopilot/private_specs/FABLE-FIX-S81-COLROM-R5/s81_col_h10_r1__t1__cld01bb4ae_1121184834/spec.json
  on the sealed J7 tree intel2 /srv/opentallas-scratch2/claude/kw45/src_s81_pin_3c913dbdfb23_d8j7_1117_work (plan a6771d121e95, manifest 12af64d4f18d,
  src_manifest on, --rt 404887a342b0, --host intel2). R4 candJ7cG spec/stage (fable-fix-s81-colrom-r4/stage) is superseded, not launched.
- NOT LAUNCHED yet: run-item on intel2 dies at kit_rtl "KW-FIX-45 hub guard" (kit_wave.py otrun target_hosts + place_async G==hub); other gen hosts DRAINING.
  COORD told FLEET-WATCH-R8 to allow intel2 heavy ot-run units within cap / epyc9 admit / undrain. Launch on first admitting host:
  python3 -I /srv/opentallas-scratch2/claude/rt/current/tools/autopilot/kit_wave.py run-item <spec>   (other host: re-run private-spec --host H, tree must exist there)
- After place: post placed read to S81-J6-ASSEMBLY-R5. Read ROM pval -> bn output stage FIRST (~160 ps late clock needed, else add a pipeline stage, no skew).
  No TT repair on ROM-pin ends (COORD lever 3). FAM-S81-COL-H9R0-R4 owns col_h9_r0 rep: do not duplicate.
## Cleanup owed
- epyc10 /srv/opentallas-scratch3/claude/fable-fix-s81-colrom-r4/{candJ7cG,gate_j7g} via ot-delete after J7 applies (04:15 PST 11-22).
- intel2 fable-fix-s81-colrom-r4/stage (candJ7cG copy, superseded) via ot-delete once the J7-tree kit has passed gen.
