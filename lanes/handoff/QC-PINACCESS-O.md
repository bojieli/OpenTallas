# QC-PINACCESS-O handoff (Opus successor of FABLE-FIX-QC-PINACCESS)

Updated 2026-11-16 06:4x PST.

## Done
- r281 kit_topology snapshot re-root: claude/qc-pinaccess-o-1116@79aa99dd618 MERGED (main 12264006dce). Fixes FAIL-CLASS 07f8439040.
- Class B (DRT-0073): STALE, no code/rows (predecessor RESULT 02:31).
- coll_n repeat DRT-0255 (RESULT 06:4x): NOT pin access. All 6 failures are old-tree runs. Same net net25397, same box (62.70,653.22)-(66.69,657.21) um, same 12,732 violations after iteration 0. Pin access is clean (NoAp 0). Failing pin = worker-boundary M8 pin inside SRAM g_bank[2] (dense core_pg_M4 macro PG grid). This is the C3b PG-track class. coll_n has never routed on the new tree.
- ACKed c344a406fe (SELFCONT comment path) and b2d012998c (SRC_MANIFEST v1 tree vs main). Both are fixed by the QC v2 tree marker.

## Watch / next
1. QC v2 marker (lanes/handoff/tree_switch_qwen_compute.json, TOOLS-CONVERGE). Then coll_n + sle_sc_v1__cl115da35f/__cl7479a5ec + slw_su_l1__cla2a78701/__clcc9d0155 relaunch on v2 (KIT-OPS-5).
2. Proof routes: 5_2_route.log in the kit gen dirs (s29q103S4Q6D/items/<i>/... or ot-jobs/<i>-route-*/work/run/logs/asap7/dp_<i>/base/). A class-A proof that routes with no DRT-0255 -> post "RESULT PASS proof:DRT0255 ..." so HOLDGEN-1115 releases the hold records.
3. If coll_n fails again at net25397/box on v2: keep the route-input DB and run a PG-over-SRAM A/B (core_pg_M4 connect density / M5 strap pitch over macros).
4. Class-B real-route proofs: epyc2 /srv/opentallas-scratch2/claude/ot-jobs/{cbn_q00__cld7bf7197,cbn_q01__clab6e67f2,cbn_q01__cldd6ea846,cbn_q11__cl49ae4555,cbx_q10__cl94a12200_h}-route-dear-crayfish-*/work. In 5_1_grt at 06:35. Look for DRT-0073 (class B) and DRT-0255 (old tree, class A expected).

## CODEX notes 2026-11-16 10:0x PST
- Took over QC kit_topology failures directly in inherited epyc2 qc-pinaccess-o/r2.
- Driver audit fix pushed claude/qc-pinaccess-o-1116 @0551428f55bee5deb5d916fb0a9fbd7782421ab6. Recognizes canonical packed receiver as q/eq DRIVER after packed_input_delay validates whole instance. Tests 33/33 plus original S4Q6D clcc9d0155 attempt10 real isolated kit replay PASS. Normal remote source gate owned by MERGE-QUEUE.
- leaf_um classes a8f8a2534c, e21636a9ba, 49b4dc3d74, 09805db76e: S4q9c/d/e/f metadata complete; counts sle_sc_v1 x2=5, slw_sc_v2=5, sle_fe_v1 x2=24, sle_fe_v3=8, sle_fe_v2=25; missing0. Wait for actual new event, no old S4Q6D retries.
- 96c681d4b6 su_l1 has second cause in new candidate: x_su_c_i core chain [3,3,4]. Whole-plan audit: exactly clcc9d0155 + cla2a78701 affected. Canonical rows QC-PINACCESS-O-sul1equal-rows.json equalize first2 chains3->4; native pricing already max4, cycle delta0. epyc2 qc-pinaccess-o/zz_s29_qc103_s4q9e_sul1equal.json sha8241ff47f180; full knee988 FAIL0; actual both failed RTL copies now kit_istations RC0 in proof_sul1_equal{,2}. KNEE owns compose into next event and bind/LATCHECK.
- Evidence/scripts epyc2 /srv/opentallas-scratch2/claude/qc-pinaccess-o/{istation_metadata_1116.txt,depths.txt,sul1_equal.report.json,proof_sul1_old.log,proof_sul1_equal.log,proof_sul1_equal2.log,sul1equal_knee.tsv}; no route started, no running kit/tree modified.


## Codex park: Claude reset, 2026-11-16

Root instructed immediate park. No new build/route/verification/retry after this point. All completed failures and baseline evidence remain immutable. No coll_n hold pilot was launched.

### N43 actual emitter: exact current handoff

Source is epyc2 `/srv/opentallas-scratch3/claude/fable-fix-qc-knee-hc/treeN43_44868`, pinned to `44868df838a11577adfe2bf02b7df99313ed11c6`, derived from full immutable J plus exact18 overlays. Fleet qc_pack owns source inventory: initial49 selected ASB full/lib dependencies match J; eligible initial elaboration cache is recorded beside runtime AB. No fresh full elaboration was needed. New native32 SRAM registration is included in44868. Old views/sourceJ/N remain untouched; new m44s1 group views are unsigned/unqualified.

Runtime AB: `/srv/opentallas-scratch3/claude/fable-fix-qc-knee-hc/n43_runtime_v2/asbuilt_n43_scoped_v2.json`, SHA256 `4c94c85bea6bfd36b3ab3f53593f710491bd5f5583d48dd48a6cce9e103abff2`. It rewrites clock/R8/three old extras to candidate-contained assets and appends the normalization owner extra LAST. `scoped_elab_cache.json` beside it contains six canonical cached files/full hashes and49 source identity proofs.

LATEST prospective plan (outside immutable N, on dedicated scratch2): `/srv/opentallas-scratch2/claude/qc-pinaccess-o/n43_event_v5/physical/die_plan/qwen_compute/plan_of_record/zz_s29_qc103_s4q9k_sunorm43_private44868_pinv5.json`. Preserve full canonical hierarchy: clock count-frame discovery expects `plan_of_record/feed_s29.json` and `regions_s29.json`. v5 preserves canonical cores/cells/census/macro_pins/sink_bins/r8, direct plan references and feed/regions; unused historical derived plan variants were removed, with sourceN retaining their immutable backup. `n43_event_v5/trim_receipt.json` records exact plan hash/removed files; `prep_receipt.json` records native_contract and real clock_count_frame constructor PASS before trim. A final cheap native/count-frame check after trim was started (local exec session52880); result was not collected at park. It is not a build/emitter.

v5 restores the36 original full semantic-ABI `pins_file` tables solely as provisional pin-coordinate reservations, preserving planned reset targets. Old LEF/lib were NOT restored; unsigned new master views remain missing. Canonical ABI files and8 reference masters are inside immutable N runtime/su_norm43_abi with source-root-relative contracts. Extra metadata MEM44/SEG1, all480 field loops normalized safely at receiver to43, including shared WROM launch correction and bit0 skew; new master names `_m44s1`.9 types share identical alias semantics within each type. Related proposed pad geometry is in P/results/geom_review/su_normalize43_pad_proposal_all9.{json,png}. Receiver pads104436FF,39589.599um2; selected tag implementation is separately six32x64 SRAM/head plus twoTLS and ~792FF/head upper. Rejected extended-flop473760 tag estimate is historical, not combined with selected SRAM model.

Actual emitter orchestration: `/srv/opentallas-scratch2/claude/qc-pinaccess-o/scoped_qc_emit_44868.py`. It calls real cmd_bind preparation, invokes original Binder.emit for only `sle_su_l0__cl7a55c676` and `slw_su_l1__cla2a78701`, and stops before die-top emission. It records all prep errors/gaps and actual frame hashes. It never claims strict-bind or physical PASS. Output targets are new P/n43_emitN, never overwrite earlier failures.

Known terminal attempts:
- P/n43_emit1: outside-base absolute J clock table rejected before preparation. Fixed in runtimev2.
- P/n43_emit2, unit `oth-ubuntu-2269698-1794861050`: zero preparation errors, actual E_l0 frame emitted, then `group has no planned reset target u_lane0`. My prospective plan had removed pins_file with views; fixed by restoring explicit reference ABI pin reservations in new versions, without signed-view reuse.
- P/n43_emit3, unit `oth-ubuntu-3983486-1794862166`: external short plan folder lacked unchanged signed VMR pin table. Fixed by canonical sibling closure.
- P/n43_emit4, unit `oth-ubuntu-971084-1794862920`: clock landing count-frame feed/regions discovery refused noncanonical external plan hierarchy. Fixed by canonical-depth v5, constructor PASS before trim.
- n43_emit5 launch DID NOT RUN: resource guard saw scratch2 only35GB free, below50GB floor. No emitter5 process/output was created. After pruning own11GB derived history, last observed free space45937127424 bytes (~42.8GiB), still below floor; fleet_flow was asked for safe reclamation. Do NOT override floor or fall back to root. No progressing emitter remained at park.

Storage finding: epyc2 scratch3 is SAME device66307 as `/` (3.5TB filesystem), despite612GB free. Existing J/N are immutable/live legacy inputs; do not remove/mutate them. My new completed/unbound v5 plan snapshot was moved to dedicated scratch2. Cross-filesystem mv copied read-only files but could not unlink read-only source dirs; exact new disposable duplicate was then made removable and deleted after distinct-inode/source backup checks. No active source touched. All new emitter outputs and v5 package are on scratch2. A separate overly broad read-only reset comparison remote Python PID3459757 was stopped via exact remote SIGINT; confirmed absent. It was not an ot-run client, no detached diagnostic remains.

Clock C delta: worker clock_pair_diag proved ALL468 changed diagnostic C rows are same physical region in actualN and intentionally absent from native2525 CA sidecar. `allowed_n43_port_updates={}` and `allowed_n43_root_clock_updates={}`. No K4 additions/counterregen/token delta from that diagnostic. Receipts under epyc2 `/srv/opentallas-scratch2/claude/fable-die-qc/delta/ca_pair_diag_1116/planner_fixed/{ca_row_field_delta.json,n43_applicability_receipt.json}`. Do not inject hypothetical virtual-region rings. Separate old-view midrange/window/seam proposal remains unadopted.

### coll_n a22: DRT proof PASS, terminal hold FAIL, concrete next candidate

Actual route source job epyc10 `/srv/opentallas-scratch2/claude/ot-jobs/coll_n-route-civil-redfish-3443740-1794846925/work`. coll_n RTL eb1e/eventS4Q6D is unchanged by r301. Actual detailed_route completed DRC0, no DRT0255, antenna0, LECasyncRC0. Narrow PASS proof:DRT0255 canonical post commit `1bd2d1802b11e73245b264a4f4b5313b03a6d104`. Route runtime10969.42s, peak20885.49MB. Source GRT checkpoint and TT PG-repair logs were already preserved; no same failing PG form rerun.

Terminal ordinary sign-off: NOT SIGNED; nominal TT setup -1.09ps (academic threshold pass), FF hold -58.19ps with64 endpoints (63 internal/one input). Latest canonical OWNER12.24c is setup0/hold25; root withdrew stale TT60 direction. No TT60 rerun. Related pair TT330ps/FF288.43ps is INFORMATION under latest rule, not a new80ps gate. Failure/result post commit `400c303ab8b3452abfec43ab714d223128c6f7c8`. No SIGNED export.

Worst FF path bank0 hit_age1→dout15: clk_t18 launch arrival146.46ps, clk_t17 capture407.43ps, CPPR0; dataarrival385.85 vs required444.04. Rootports only21.632um apart but independent CTS trees differ sharply. Pair affinity had64um/depth2/group64/merge128, left185 short cross-tap pairs and11 frozen oversized components. Tapbal fixed250ps target left t17 mean448ps while padding t18 only to218ps. This is actual cross-tap clock ownership/hold, not recurrence of PG/DRT0255.

Complete terminal state preserved directly under resource admission, no local bulk: epyc2 P/coll_n_a22_route_input/final_state/{6_final.odb,sdc,spef,v},837260667bytes, all4 hashes match; PRESERVATION_RECEIPT.json and SHA256SUMS alongside. Terminal signoff logs/cornerJSON under P/coll_n_a22_route_input/terminal_signoff; DRT0 log/metrics snapshots alongside. Wrapper `/work/resume.json` line155 error did not block abstract, pin audit or terminal sign-off; do not reroute to repair bookkeeping.

All64 FF failure paths and actual TT all-launch setup margins collected read-only on epyc10 P/coll_n_clock_diag:
- ff2/hold_paths.tsv and hold_paths.rpt: actual64 failed paths; min -58.189316ps.
- tt/hold_pairs_tt_setup.tsv: same-pair margins only; do NOT use alone to qualify capture pad.
- tt_endpoint/endpoint_tt_setup.tsv: ALL launches into each capture, min301.099426ps (bank0hit_age1→bank1dout72).
- tt_load/capture_loads.tsv: actual TT capture slew max104.519814ps, pin caps.558822..619900fF, HB4 inputcap.721778fF.
First FF query under ff/ crashed139 from PathEnd lifetime invalidation (nested timing query invalidated outer path objects); retained. Corrected ff2 snapshots primitive strings before subsequent searches and exits0. All read-only TT/FF diagnostic units completed; no constraints/netlist changes.

The deterministic alternative to new clock root is fully modeled and geometrically reviewed, NOT implemented/launched: P/hold64_priced_candidate.json on epyc2, same under ep10 P/coll_n_clock_diag.80 HB4 (53single,6double,5triple),8.1648um2,0pipelinecycles/0clock sinks. Actual rows/macro rectangles respected, filler removal only; no functional-cell relocation. Reviewed render/model BOTH hosts P/results/geom_review/coll_n_clock/coll_n_hold64_HB4_reservation.{json,png}. Detailed raw ODB pin/row inventory `hold64_physical.json` may be retained only on ep10 (do not assume ep2copy exists).

Electrical model from exact actual Liberty: HB4 FF minimum29.8081ps over conservatively extrapolated0..320ps/0..2.88fF; TT max132.796ps at0..160ps/0..2.88fF, self-cascade output slew<=52.6803ps. Capture-pin loads confirm small physical load; simple RC scaling predicts initial HB4 slew<=134.998ps vs160 bound. Local reserved stubs/interstage<=5um; .22fF/um estimate yields load<=1.822fF vs2.88 envelope. Conditional predicted worst FF hold+5.605ps, TT setup+52.980ps for all64 endpoints, area8.1648um2, nominal dynamic power upper~.135mW at0.7V/1.2GHz. These are model bounds conditional on actual newnet slew/load/upstream timing; physical measurement still mandatory, not signoff.

Clock-cohort alternative evaluated before choosing pads: bank0 has415FF over7roots; none of26existing roots reaches entire bank within200um L1. Deterministic minimax row anchor[132.57,520.155] reaches199.125um and replaces only2fillers; repurposing emptytap22 would need root/pin/parent-clock-model changes. It cannot repair all64 cross-bank/TX/macro paths alone. Detailed reviewed artifacts P/results/geom_review/coll_n_clock/{coll_n_clock_geometry_model_L1.json,coll_n_clock_ownership_L1.png,coll_n_anchor_row_review.png,coll_n_alltap_radius.json,coll_n_anchor_legal.json}.

NEXT: do not blindly launch a route. No insertion Tcl or physical pilot has yet been implemented. Prepare deterministic exact64 capture-pin insert_buffer operations and structural audit preserving clocks/reset/all other nets, using modeled80-cell reservation and completed DRC0 state. Installed OpenROAD6cb3 detailed_route has NO `-incremental` option; global_route has -start_incremental/-end_incremental. Confirm supported saved-route/new-net flow before physical pilot, then ordinary DRC/TT/FF/LEC and load/slew envelope measurements. No ideal timing pads, no constraint relaxation, no post-STA clock-offset tuning. Root parked this work for Claude reset.
