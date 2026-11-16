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

## UPDATE 01:4x PST (end of lane run)
- GitHub: claude/fable-genbug-1115-1 @4e7f20bccb and claude/genbug-impl-1115-1 @99185a0ba8 pushed (from localhost; fleet hosts have no GitHub access).
- G3: die pdngen KV kvgeom6: 160/160 partition grids OK, but PDN-0233 on region grid ot_pg_9 (6.48 um sliver, independent of G3); posted to FABLE-TRIAGE-HEADKV.md. Not installed. Logs epyc9 genbug-impl/g3/kit/psm/pdn_only{2,3}.log.
- G1 NEXT STEP when c1x passes (epyc8 .../proof/dsdv_slice_c1x_C__t1, still 3_3 global place at 01:4x, run_place.log): judge with fable-genbug/pq/stq_run.sh (copy 3_3_place_gp.odb as pq/in/<name>/3_place.odb with the wave kit's original istations.tcl). Install: intel2 ~/genbug-impl/inst_g1.sh + kit_istations_g1.py (= 4e7f20bccb version, sha256 prefix 3364e1a84f67e18c); on each host: scp kit_istations_g1.py to /tmp/ then `bash -s < inst_g1.sh` (copy+mv, .bak-genbug1, hash printed per tree; HEAD tree only on epyc7/10/intel1). Tree kit_istations.py == main today, so a plain replace is exact. Then re-key S81 297 / QC 26 / KV 4 under kit_wave.lock (backup kit_wave.json first), tell KIT-OPS-5 to generate those kits first.
- DLY-SPREAD r53 (claude/dly-spread-1115-1 @47010b3510): install after merge with G1. CAUTION: the die trees' gen_phys.py (S81 +267/-108 vs main, QC/KV/HEAD differ too) and schema.py (S81 +49/-71) carry die-local lines: do a 3-way merge (git merge-file tree base main) per tree, not a plain copy; dly_spread.tcl and forest_recluster.tcl are plain copies if the tree copies equal main.
- Guards flags (OT_MERGE_CENSUS, OT_HOP_CENSUS) still off; turn on after one proof each (leaf t11 kit on OT_HOP_CENSUS=1, a KV hgi kit on OT_MERGE_CENSUS=1). Wave-preflight call of hook_manifest.py check not wired.

## CODEX bound-landing physicalGEN fix 2026-11-16
- Inherited epyc9 fable-genbug/wt now on existing claude/rc-signal-1115 @d7bebc047fe1d9124f2694d738ad36f06294a192. Original claude/genbug-impl-1115-1 (13 unmerged guard files) preserved unchanged; RCsignal mainmerge was clean and content-identical to main046089 before new fix.
- Bound-only kit + declaration-only landing sidecar now skips unused whole-plan gen_rtl emission; schema/sidecar/collector/bound-ring checks retained. All generated kit files and runner byte-identical on minimum vehicle.
- Focused21/21 PASS; old-condition negative control correctly fails forbidden emitter (epyc9 genbug-impl/landing_fastpath_negative.log). Canonical READY posted. merge_ops owns normal source gate once; no duplicate focused proof.
- Existing full-shape SVC GEN jobs preserved, no published source/run patched. After normal GREEN/root approval, new private GEN sources may take fix; release waits normal tree bind gates.

## CODEX future PRD cold-preclean integration 2026-11-16
- Same inherited clone, existing claude/rc-signal-1115 @be4e664a0421c1ca435deb6a25ce1aae33e8b57d (source a48f17d4cfc + clean current-main merge). Normal source gate GREEN16/16 against main e37cb718b58; full-SHA record in intel2 ~/merge-queue/gates. Approval belongs to root; no live kit/tree patch.
- Future CLI: OT_PRD_FROM=final OT_PRD_PRECLEAN_FINAL=1 bash tools/die_plan/post_route_drv/prd_mk.sh KIT NEW m5 SO; then normal ot-run-admitted prd_run NEW CPUS MEM 1. Default and non-final staging stay unchanged.
- MK keeps immutable 4_cts_filled.odb; RUN performs cold OpenDB typed PG filler removal before DRT callbacks and verifies source/output/tool hashes, counts, and preservation manifest before routing. Every ordinary route/refill/PG/clock-freeze/STA/LEC check remains required. No hardware cycles or layer/clock budget changed.
- SDK empty-source test: intel1 genbug-impl/preclean_sdk_r2_1116, unit oth-ubuntu-335552-1794854998 exit0; default empty refusal preserved, explicit --allow-empty produced byte-identical source/output ODB and VERIFIED_FINAL_SEED receipt. First SDK fixture used obsolete dbChip.create overload; failure retained in preclean_sdk_1116, corrected constructor (db,tech) passed. Focused protocol/default/negative/pass2 checks passed.
- Native M7 global-router assertion is separate: native_e worker owns proved clock-resource inventory fix. This commit contains no routing-layer or clock-wire change and claims no routed qualification.

## CODEX preserved-clock inventory integration 2026-11-16
- Same inherited clone and existing claude/rc-signal-1115 branch now @7945f415d27e4b80d46c7155e49ac202cad913af (source d4a87c46e76 + clean current-main merge). Earlier cold-preclean be4 SHA remains intact. Normal source gate requested once, owned MERGE-QUEUE/merge_ops; approval remains root-owned.
- Future fresh route/final pass opt-in: OT_PRD_CLOCK_INVENTORY=1 when calling prd_mk.sh; may combine with OT_PRD_PRECLEAN_FINAL=1. It stages a decoder-based helper after the original pre-GRT chain and before the first global_route, registers only existing CLOCK layers, rejects above-cap data before changing ranges, and retains signal limits and frozen wire objects. Default and ordinary GRT staging stay byte-identical; later route-keeping passes retain the request. No clock period/uncertainty/signoff gate changed; no active kit edited.
- Seven staging/default/pass-two tests PASS. Actual fixture proof intel1 genbug-impl/clock_inventory_sdk_1116, unit oth-ubuntu-1911673-1794856383 exit0: clock max6to7 inferred, signal M2-M6 and all93 existing wire opcode/data pairs unchanged; end_incremental PASS. SIGNAL-labelled M7 control refused before range change; existing clock max8 retained. Reproducible test script committed as post_route_drv/test_prd_clock_inventory.sh; original native fixture kept read-only.
- Native_e worker separately owns the full-shape retry: same66 dirty data nets/109967 parked, original abort point passed, all1817 frozen clock wires retained; subsequent DRT/signoff still required. This source class does not claim routed qualification.

- Clock inventory source 7945f415d27e4b80d46c7155e49ac202cad913af normal gate GREEN16/16 on main f43d3553b62, unit1607204 exit0; full-SHA gate record in intel2 ~/merge-queue/gates. Root notified for approval. No repeat gate or current-kit patch. Source clone is clean.

## CODEX active KIT_SNAP closure and source-inode isolation 2026-11-16
- Inherited clone epyc9 fable-genbug/wt, existing claude/rc-signal-1115 branch @e2e31d8fc41db20c1676b89fa07c4ad33c9d739a; 31 focused kit_store tests pass. Normal source gate owned once by merge_ops; root owns approval/adopt. No live runtime or signed view patched.
- Actual col a4: kit_store incorrectly demanded original face_guard.netlist for ordinary BF/LLfd/LLfu children. Only hard_landing.capture consumes that synthesis netlist, and only for selected hard-landing param_wrap bases lacking portable landing evidence. Fixed scope and /work-to-original-kit resolution for real hard landings. Original signed records/hashes preserved. Actual full col_h10_r0_p1__t1__cl574cc59d__pv3d0d4d97 now has nine retained receipt/ODB dependencies, zero missing inputs.
- Actual BK topology failure: moved asbuilt base is relative; active clock_landing_table existed in D2 but was absent from mirrored snapshot. Added structured required closure, preserving JSON bytes, source table inode and exact SHA7d94d9fcedb5bcd1d4de105d44755215d0c64f4048082b019eb7254ae19bc694. Actual two-file snapshot passes byte identity and relative-path resolution; evidence epyc9 genbug-impl/snap_actual_1116/result.json.
- CAS formerly hardlinked published read-only sources, violating nlink=1. Ingestion now copies into CAS; CAS-to-snapshot dedup remains. Legacy CAS aliases are atomically detached without editing original source or any live snapshot. Tests cover fresh source isolation and pre-existing source/blob/live-consumer aliases.
- Existing D2 pollution: four exact CAS blobs were detached preserving source inode/mode/hash; each published source still nlink2. Additional aliases are not in kit-store, kw45 or s87bind by initial inode inventory; whole-scratch read-only inventory active. No arbitrary source replacement or unlink. Fleet confirms supplied failed BK jobs inactive. Remaining alias repair must wait for exact path and inactive-consumer evidence; current partial repair record epyc9 genbug-impl/snap_alias_repair_1116.json. No other repair actor known.
