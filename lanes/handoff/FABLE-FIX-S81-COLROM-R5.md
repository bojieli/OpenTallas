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

## UPDATE 11-21 21:5x PST (state for resume; lane does NOT stand down for context)
Pushed to main: b0e55c17a3fd (src_manifest dir symlinks), 650916ebb262 (KEEP-RC: TT repair keep verdict masked by tee), 643ffb9932 (RELAY-INST: station
relay_sites keys seat all registers), 4dac1ad0b7 (RELAY-NORM lf/generate forms + SEAT-MISS stop, waiver OT_RELAY_SITES_UNMATCHED_MAX).
ROOT CAUSE of J7 col thin margins: plan relay_sites keys of the xd stages are STATION names; rs_place_all matched flop names only -> 140/166 unmatched,
stages unseated, relay_mid moved 27 up to 409 um (bn8_e_r0 pval hop 415 um). On J7 tools 52 u_w-side stations are also merged away by Yosys.
J7 tools pin CANNOT bump without rebind (bind stamp: reset_replicate.py differs). Seat fix = J8. J7 fallback = env row only if kit B proves it.
Kits on epyc9 (work root .../kit-wave/s81/a9ed808a98d/private/FABLE-FIX-S81-COLROM-R5/):
- BASE _1121190100: GOAL=route unit oth-ubuntu-2288963-1795320570 (client pid file route_e9.pid, log route_e9.otrun.log). CTS real clock WNS -1.98 before
  TT repair, kept DB -21.04 (KEEP-RC bug). Was in pre-GRT hold repair at 21:17. Judge on final 5_1_grt.odb.
- B _1121212057: A/B OT_RELAY_MID_RE=^(.*[._]u_y_(?!xd_)[A-Za-z0-9_]+)[.] on J7 tools; run-item pid file runitem_ab.pid, log runitem_ab.log.
- D _112121413x/_1121214146 spec: private plan fable-fix-s81-colrom-r5/planD/plan_h2_2249.json (xd seats keyed per flop), J7 tools; runitem_d.pid/.log.
  New run-item continues to sign-off chain by itself (goal auto).
- C (new tools) refused by bind stamp; never launched.
Read tools on epyc9+intel2 fable-fix-s81-colrom-r5/tmp: placed_read.tcl + stage_read.sh KIT OUT <stage>.odb IDEAL(0|1); pval_geom.py/.sh; seat_census.py; key_class4.py.
Census: tmp/census_*.tsv (319 placed kits), tmp/kc4_*.txt (58 kits with unmatched keys, forms).
OWED before 02:00: placed/CTS reads of B and D to S81-J6-ASSEMBLY-R5 (J7 env row proven or withdrawn; J8 rows = seat fix via tools + no-merge), base kit GRT/route verdict.
