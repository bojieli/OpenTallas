# GENBUG-IMPL handoff (2026-11-15 ~01:0x PST)

Work clone: epyc9 /srv/opentallas-scratch2/claude/fable-genbug/wt, branch claude/genbug-impl-1115-1 (off claude/fable-genbug-1115-1 @4e7f20bccb), pushed. Commits 57abcc87e9 (guards wiring), 99185a0ba8 (G7/G9 coverage lines). Tests pass: test_genbug_guards, test_merged_replica_census, test_istation_packed_last_stage, test_die_pg_parts_region, test_kit_istations, test_relay_mid*.

## G1 (kit_istations last pad stage): PROOF RUNNING, NOT INSTALLED
c1x_C__t1 place proof: epyc8 /srv/opentallas-scratch2/claude/fable-genbug/proof/dsdv_slice_c1x_C__t1 (started 08:17 UTC, place goal). Pass = OT_HOOK_COVERAGE hook=istations missing=0 + last stage q90 <= 30 um + hops <= reach (judge via fable-genbug/pq/stq_run.sh, section 3 of FABLE-GENBUG.md). On pass: install kit_istations.py to the 4 die srcs, all hosts, copy+mv, .bak-genbug1, then re-key S81 297 / QC 26 / KV 4 under kit_wave.lock with backup; KIT-OPS-5 informed via queue line. leaf t11 proof already passed.

## G3 (partition PG grids): die pdngen run in progress
epyc9 /srv/opentallas-scratch2/claude/genbug-impl/g3 (die_trial.py kit on kvgeom6 plan_c with branch die_trial.py, then pdngen only). Not installed.

## G4 (hook sync): DONE for the stale hooks
Installed by copy+mv, backup <file>.bak-genbug4, on epyc2/7/8/9/10 + intel1 (6 hosts):
- QC tree wt/qc-s29-tree2: core_input_anchor.tcl core_input_chain.tcl hold_gate.tcl hold_repair_pre.tcl lec.py pair_slack_gate.py reset_tree.py signoff.py (all were identical to their base commit 1e3b302be8, main newer: pure fast-forward).
- KV tree kw45/src_kv_kvgeom6_pgL: core_input_chain.tcl lec.py pair_slack_gate.py reset_tree.py signoff.py (same rule).
- S81: nothing stale (every differing hook carries die-local edits). HEAD tree: base commit fb5f5a8db8 not in the clone, NOT synced; HEAD differs in 15 hook files (list below).
Not installed, to be landed or merged by the merge lane (die-local lines not on main; 3-way merge of main into the tree is conflict-free for these, staged in epyc9 genbug-impl/g4/<die>/): landing_placement.tcl (S81 +186 / QC +155 / KV +152 / HEAD +152 lines), postcts_gate.tcl, subtree_balance.tcl (8), clock_taps.tcl (2), m8_grant.py (QC/KV +171, HEAD +171). CONFLICT with main (need a human merge): cell_census.tcl, grt_pre.tcl, grt_post.tcl in S81/QC/KV; face_flops.tcl in QC and KV (QC 42 main-only lines, KV 21); die_sta_related.py (all, tree +157 / main +134).
Diff table: epyc9 genbug-impl/g4 and scratchpad g4merge.txt; per-die classification in lanes post.

## Guards (branch claude/genbug-impl-1115-1)
- OT_HOOK_COVERAGE: istations and die_pg_parts fail closed by default (branch 4e7f20bccb); gen env OT_HOOK_COVERAGE=warn exports the downgrade into config.mk. relay_sites, relay_mid, leaf_affinity print coverage lines (advisory); relay_mid gate by env OT_RELAY_FALLBACK_MAX_FRAC (off).
- merged_replica_census.py after synth: gen env OT_MERGE_CENSUS=1 (gate 64 flops) | warn writes K/merge_census.on; run_kit.sh runs it after reg_fanout, rc 7 FAIL_PREFLOOR. OFF by default.
- hop_census.py placed-DB preflight (crossing <= 20, over reach <= 1 % of zero-logic hops): gen env OT_HOP_CENSUS=1|warn writes K/hop_census.on; runs `M place` + openroad -python before CTS. OFF by default.
- hooks.manifest: written in every kit; `hook_manifest.py check KIT --main DIR [--strict]` classes stale / local. Wave preflight call not wired yet (needs a main checkout path on the wave host).
Turn flags on after one proof each: pick one cheap kit (e.g. S81 leaf t11 and a KV hgi kit) for OT_MERGE_CENSUS=1 / OT_HOP_CENSUS=1.

## G7 / G9
G7 and G9 fix = coverage line + optional gate, implemented advisory (above). G7 true gate (fail at > 5 % fallback) not turned on: 15 of 18 S81 col kits sit above it, needs FABLE-TRIAGE-S81 decision. G9 advisory only, per table.
