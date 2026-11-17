# QC-PLAN-G — Codex takeover 2026-11-16 22:18, current 23:06 PST

## Immediate M (owned QC-PLAN-R)
Use existing `g/pre_m_v4/apply_g.py --without-sc`. Qualified non-SC subset output `g/pre_m_v3/subset_no_sc.json` SHA `6c2a2c1d218d`: +33 summed lane cycles /19 lanes. Original +31/17 missed input st_wi on sle_fe_v2; imported per_bit FE rows also lacked leaf_um. Both fixed. Model subset_lane_model.json: +15,791 FFbits at actual die replicas, throughput1 payload+epoch/cycle, memory-port delta0. Actual kit_istations + actual ot_dp_st fullwidth lockstep PASS (4 classes,2987 edges each, all missing-stage mutants detected).

## N (SC successor after M, parent owns compose/bind)
All paths E2 `/srv/opentallas-scratch2/claude/qc-plan-r/g` unless stated.
- Current reusable FULL composer: `pre_m_v7/apply_g.py` with rows_fe.json sibling.
- Strict geometry seed: `pre_m_v2/zz_s29_qc103_s4q9m_g.json` SHA955ddcc5787e. Allocator completed exit0; no process was killed when the attempted stop found it already finished. All9 SC actual-cell halos >=8.652um; actual paired-bit worst <=367.987um, macro-free routes except explicit existing M7 over-core forms.
- Full provisional N on L2d: `pre_m_v7/provisional_n_on_l2d.json` SHA7b57a014124f. Report `.apply_g_report.json`:590 reset localizations,0 dropped, all joint dryruns PASS; reset final hops136–178um (exact2 W street types136um), same release depth and same START role. Newly added FT consumer fragments come from the actual Binder.emit_type ot_dp_st form; final actual N bind still required.
- Provisional preview used explicit --reset-seed and authored helper-dir. For final N on ACTUAL M omit --reset-seed so reset_tree.for_type derives current graphs; use actual M bound RTL with --rtl. Preserve --ft-seed: it checks outline/bus/macro/interface identity plus each bit-cell halo/hop/core-route. No new allocator needed unless physical geometry differs.
- N relative qualified M Gsubset: +90 summed lane cycles across78 lanes, +41,442 FFbits whole die replicas (+30,813 one of each SC type). Reset rewiring0 cycles. `pre_m_v7/SC_N_model.json`. Full G relative L2d123/97. Refresh final model from actual M/N bound LATCHECK.
- Review LOOKED: `results/geom_review/qc_sc_n_1116/QC_SC_N_review.png`, `review.json`: PASS-COND geometry; critical x_fw_fe_p2 goes below u_core, x_fe_stm_p1 around top/side halo; no outline/interface change. Clock/PDN not shown. No P&R launched. Exact2 holds remain until GEN street/hop + actual placement relay/pin halos + GRT0.

Example final composition (through ot-run, declare all input stages):
python3 -I pre_m_v7/apply_g.py ACTUAL_M_PLAN N_PLAN --tree ACTUAL_TOOL_TREE --rtl M_BIND/rtl --ft-seed pre_m_v2/zz_s29_qc103_s4q9m_g.json
Then kp_inject.py make FINAL_N_PLAN BASE_MANIFEST true; run normal guarded CM/KP injection/bind, latency/R8/G0/LATCHECK. KP check on bind log must exclude prior appended KP CHECK lines (they self-match KIT_ISTATION_LATENCY).

## Authored helper, adoption N only
`claude/qc-reset-syncroot-1116 @bd0dc4f939865c3aa87a17dc01fe368a890cf2c7`, existing E2 `/srv/opentallas-scratch2/claude/qc-pinaccess-o/r2`, clean. Physical worker released clone; original physical branch0fa20f991c6 preserved.
- Exact declared sync-entry root support in reset_consumers.py: sync_stages2 and actual canonical same-clock ot_dp_rsync_s2 u_rst_root, exact ports/source/output and unique driver. Declared START root checked similarly. Same-depth/role/lineage remain; normal relayed-root behavior retained.
- Focused41 PASS. Actual production SC root slw_sc_v1__cl63e5a7a2:86-tap graph,83 mission targets equal2979 cycles, missing-stage mutant361 detections; root clock/module/entry mutants rejected. Actual tree + PASS committed in results/rtl/qc_reset_sync_root_1116.
- NORMAL GREEN4/4 main419279e2843. Intel2 client1020263 completed; log ~/qc-plan-g-codex-logs/gate_reset_syncroot.log; gate record ~/merge-queue/gates/bd0dc4f939865c3aa87a17dc01fe368a890cf2c7.json. READY posted via QC-PLAN-G. Root approves/merge queue merges; does not block M.
- Packaging delta `g/reset_syncroot_authored.patch` SHAd6a00b953043, old helper2c1aaaf08cf2 -> new163ad8cc2f46. One production file, engineRTL0. Parent owns N stage; no M stage mutation.

## Diagnosed failures kept
- Original G0 baseline/G failed same unresolved SU relative pin table. Use actual in-tree plan context. Old G0r processes were retained; no new wide sweep launched.
- Original reset rows vacuous empty PASS: stale published relay numbering vs actual emitted graph. Fixed by authoritative reset_tree.for_type/rtl_lines and new FT consumers.
- New targets must have same START role: raw/bootstrap tap126 emits rr_t126, not mission rst_n_t126. Role filter fixes failed lineage.
- SC root uses sync cell, not u_rst_in relay: authored helper above closes class; v6 failure kept.
- V5 own superseded process2232760 stopped only after exact cmdline check; STOPPED_INVALID_1116.json records role-filter defect. V2 finished normally.
- Station fixture failures (filename contract then missing leaf_um) retained; successful r3 proves actual emitter.

No current wave/holds/source tuple edited by this worker. No owner questions. No live worker jobs remain from G at this checkpoint.

## 23:2x private N source preparation
- DONE cp-a event source E2 `/srv/opentallas-scratch3/claude/qc-plan-r/n1116/event_tree_N1116`; admitted unit2596099-1794899702 exit0 in115s, intel2 client1202278, log ~/qc-plan-g-codex-logs/n_event_copy.log.
- Source actual inventory63,266,750,464B, scratch3 free813GB before copy (>750GB after). Scratch2 had111GB, so not used.
- Actual M plan copy `plan_of_record/zz_s29_qc103_s4q9m_d8.json` SHAbeaa07b778ce233b9608c48ee0c843c59e03a1490ae57a0e917e4091d27702ad. Source M treeJ and its helper unchanged. N-only exact authored helper patchd6a00 input2c1aa ->163ad applied; engineRTL0. Receipt n1116/N_BASE_COPY.json.
- Source is private experimental, NOT published/adopted/bound. No final N composition until first valid actual M report plus explicit runtime R8 seed; never borrow L2 RTL proof.
- Prepared `n1116/prepare_n_from_actual_m.py` (NOT run). Required --m-bind-dir ACTUAL_S4Q9M_BIND --m-r8 EXPLICIT_ACTUAL_M_SEED. It checks report errors0/unbound0, plan/helper hashes, reads actual M RTL explicitly, copies R8 to N-only unique seed, calls full v7 with Ntree and FT seed while OMITTING reset seed, and records actual M-to-N lane/boot deltas. It never binds or adopts. Launch through ot-run on E2; declare source Mbind/R8 and scratch2 qc-plan-r/g as --stage.
- Actual final M gate chain is parent QC-PLAN-R scope; unit2541142-1794899426. As of last check no valid M bind_report existed. All G/N jobs from this worker finished; awaiting M prerequisite, no watcher consuming admission.

## 00:xx M first-bind failure: STB reset anchors + collector sidecar repaired
Parent's actual MBR failed162; no qualification/use as N input. G owns3 RESET_ANCHOR +1 EMIT, other classes separately owned.
- Exact M plan beaa07b778ce233b9608c48ee0c843c59e03a1490ae57a0e917e4091d27702ad; D8 side846056c27104994dc72dab8f242224d0da8d49f8448340a5280c687c0e664fa2 unchanged.
- Cause: street_rule.reset_resel renumbers raw relay refs and republishes collector_tree, but the apply_g integration retained stale clock.reset_tree_anchor and stale clock table collector children. Actual pv0e collector child rst_n_t124 no longer exists.
- E2 `/srv/opentallas-scratch2/claude/qc-plan-r/g/m_stb_reset_fix_1116/plan_field_delta.json` ONLY three STB clock.reset_tree_anchor values, recorded from actual street solve's published tree,9relays/10refs pertype,original405um tolerance. No refs/geometry/clock/seam changes.
- `side_collector_delta.json`:3 matching collector type rows, tree republished and CRA.sync_sidecar applied. Existing children128→114 for pvc5a two clones;124→113 for pv0e; exactsame reset depth,part/xy/seam/ready/fault unchanged. Sources2fields/type synced. All7 local sources retain actual resetdepth5.
- Existing RT.rtl_lines and landing_collector.build_local on actual published tree:PASS all3,8real sources each,depth6,maxhop378.048um,data_cycles0; missing-node mutants rejected. Anchor.resolve on same exact solve snapshot keeps all9 and no remaps. Final fresh bind remains required; no failed-M provisional workaround.
- Complete prospective plan_candidate SHA744d13c3b328416558dd62cabd1c3b90b8854b935d03ddb8a9964f357744236b, side_candidate SHA0e369e5598c7f7fbb33889433fd92f0c428cffa210c89eba589484eb470dcd74. Parent composes exact field deltas with parallel M repairs. Script `g/qc_m_stb_reset_fix.py`;receipt.json records guards,depth/seam and mutants. No heavy newjob.
- N composition remains pending genuinely qualifying M and clockworker NB delta. M failed output preserved, no source/currentwave/hold edit.

## N preparer corrected for actual successor M and collector sidecar
`n1116/prepare_n_from_actual_m.py` now explicitly requires --m-plan --m-plan-sha --m-sidecar --m-bind-dir --m-r8 --nb-plan. Actual M bind log must pin supplied corrected plan SHA; only strict0 or ONLY-R8_STALE with tag-correct fresh derived seed accepted. The failed162-error MBR is rejected. Wrapper syntax checked; not executed on actualN.
After SC composition, it reattaches source/children on actualM→N snapshots via CRA.reattach_plan, rejects nonzero added collector cycles or source overreach, replaces changed tree rows in the supplied actual-M clock table, calls CRA.sync_sidecar, then actual collector emitter dryruns every changed type. Outputs N_sidecar_after_SC1116.json and N_collector_reattach_receipt.json. This closes the same stale-sidecar integration class for nine SC families.
Minimal existing-fixture check (4s, no solver or allocator) on provisional L2d→N: all9 SC reattachments no overreach;17–20 real sources/type;depth6 exceptsyncroot11;max actual collector hop400.624um; emitter PASS all9. These are fixture preparation only, not currentM or N qualification. Corrected M strict bind + NB frame pending, then one combined actual N compose/bind.

N wrapper final input addition: --nb-sidecar is also mandatory (clockworker's guarded NB sidepatch from corrected actual M side/M plan to combined N NB plan). N collector updates start from this patched sidecar, preserving NB band deltas; --m-sidecar recorded separately. Clockworker final NB proposal d99a1840f308 (eight deltas with derived hop metadata). Do not substitute an old-M full-frame NB candidate for corrected M; parent composes guarded NB deltas onto corrected M first. No N composition/bind run yet; exact actual M remains sole prerequisite.
