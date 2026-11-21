# FAM-S81-COL-R4 handoff (STAND-DOWN 2026-11-21 10:4x PST, Opus, context limit) -> FAM-S81-COL-R5
Scope: col_h9_r1 + col_h9_r2 (60 + 60 types on J5, held for J7) + shared J7 col rows. Lever 1 (RDX/ROM, OT_S81_CFG7_RDX) = FABLE-FIX-S81-COLROM-R4 (gen_colrom_rows.py, tree1). h9_r0 = FAM-S81-COL-H9R0-R2. h10 = FAM-S81-COL-H10-R3. J7 = S81-J6-ASSEMBLY-R4.
Work: epyc10 + epyc8 /srv/opentallas-scratch2/claude/fam-s81-col-r4 (same paths; epyc8 holds REAL copies of src_rb, src_tc, bind_rb, bind_tc). Hub chains in intel2 same dir.
## Done (all posted)
- XALIGN proven (bind4 strict+LAT, L02 e1 aligned, G0 0 new). RLYBR rows (h9_r1 xa/xb_4/5, cc_4/5; h9_r2 xa/xb_7/8, cc_7): bind_rb strict 0 + LATCHECK 873/873.
- J7 GEN steps posted to S81-J6-ASSEMBLY-R4: (1) `GEN mkrlybr ... rb/mkrlybr.py {IN} {OUT} <rows_out> rb/rows_rb_r1all.json rb/rows_rb_r2all.json` between mkdepth405 and mkxalign (660 rows / 120 types); (2) `GEN mkresite ... rb/mkresite.py {IN} {OUT}` (reset.relay_resite_crossing on h9_r0_p1/p3/h9_r2, 317 other types skipped; J7 v4 dry run detour>405 reset hops 464 -> 146, depth unchanged). Caveat: col kits use captured bound_native_reset.json; verify bound max hop after J7 bind; else use clock.landing_contract.bound_reset_placement overlay (reset_tree.native_resite_sites, PASS image review needed).
- Main: 1ba6a4eb948 relay_branch.merge_branch_rows; a2796eb39ed + d032c72040226 cbc_rules.detour_um / reach_leg_um (core-crossing legs at detour length; kit_scan LEG_RULE core-detour-1121; relay_branch measured length). COORD: these counts are an ESTIMATE, never a gate; checked: no kit stage / kit_wave / hub script reads legs_over or reach_leg to refuse (only kit_scan posts, relay_branch --fix support, plan_geom_census estimator).
- Recount (109 col kits, J5/J6 scans): over-405 247,565 -> 684,576; rc/rc_<host>.json on epyc7/8/9/10. rrl detour legs per type: rc/rrl_<host>.json; J7 plan dry run rc/rrl_try.json (epyc10).
- Bank taps <=1000: tc/solve.py; rows tc/rows_tc_r1.json, rows_tc_r2a.json, rows_tc_r2b.json (epyc10); re-solve positions on J7 placement.
- Private kits MUST come from `kit_wave.py private-spec` (copied spec fails ENV-PROVENANCE). epyc10 scratch2 98%: do not stage there.
## Running (hub chain_e8.sh = waiter: run-item -> route on the placing host -> post)
- RLYBR rep: spec wave_rb_e8 (epyc8, work kits/rb_e8), log chain_rb_e8.log. Read t4/xai, t5/xbi, t4/cci at sign-off final db.
- Bank-tap proof (RLYBR + taps, cascade dropped: J5 tree schema): spec wave_tc_e8 (work kits/tc_e8), log chain_tc_e8.log. Compare CTS post-hook + TT/FF vs the RLYBR kit.
## Next (COORD 11-21 rulings)
- Ruling 2a: rank the newly counted core legs by MEASURED setup on routed/placed DBs, rows only for legs on failing paths; start h9_r1 (247k). The old rep routed DB is gone; use the two epyc8 proof routes (their sign-off endpoint slacks) + any routed h9_r1 kits behind the KIT-SCAN scans (~/.local/state/precheck-kit-scan/col_h9_r1*.placed_raw.json name the kits).
- Residual 146 reset hops (rrl_try.json 'resite' mode bad lists) need added relays / sites.
- Signable rep: stack RLYBR rows + bank taps on COLROM tree1 once its 216-type gate passes.
- h9_r2 x2_8 -> t8_payload (11 core legs); h9_r2 FF hold -25 (22) after setup.
- Stray: epyc10 /tmp/claude_r4_j7rb*.json (95 MB, ot-delete refused files); src4x/physical/die_plan/s81/plan_j7v4_try.json, plan_j7v4_resite.json (dry-run copies); tc/col_h9_r0_*.json extra regs; epyc10 src_rb/src_tc/kits no longer needed once epyc8 kits run.
