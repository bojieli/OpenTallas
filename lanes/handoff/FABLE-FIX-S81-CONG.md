# FABLE-FIX-S81-CONG handoff (owner of S81 routing congestion closure; S81-STRIP-O silent since 05:42 PST, S81-RINGS-O done)

Updated 2026-11-16 ~09:45 PST (17:45 UTC).

## Root cause
- Ring class: lost `ring_place: ff` (fixed r282).  Strip class: ft bundles stacked between a face and an M7 core.
- Judge a kit by FINAL overflow + count of `GRT-0273 Disabled NDR` restarts, never by it5/10/15 of one round.

## Strip types (all on fx0 = B6gE + ff; proof kits, old tree, evidence only)
| type | row | kit | GRT |
|---|---|---|---|
| t34 | ft5 band x 486..552 (epyc7 fable-fix-s81-cong/t34_rows.json) | c_t34 epyc8 | FINAL 0, 0 restarts |
| t43 | ft5 only, band x 440..600 (same dir t43_rows.json) | c_t43b epyc9 | FINAL 0, 0 restarts |
| t47 | epyc7 s81-strip-o/t47_rows.json | c_t47 epyc8 | FINAL 0 |
| t62 | epyc7 s81-strip-o/t62_rows.json | c_t62 epyc8 | FINAL 0 |
| t75 | STRIP-O ft3/ft5 rows: plateau 38k. Mine: + ft1 north detour y 700 (t75_rows.json, plan fx_t75.json) | c_t75b gen on epyc7, chain intel2 chain_gen_launch.sh -> epyc9 | pending |
| t28 | sp2 core push not enough (102k at it10); W strip 35 um holds 10 slots -> needs strip widen | c_t28 epyc8 running | open |
| t8 | STRIP-O t8c row tripled placement buffers (801k cells), withdrawn | none | open |
| t72 | none | b_t72 epyc8, GRT iteration 3 after 2.6 h | open |
READY-ROWS for t34/t43/t47/t62 posted (52fedbf) for F2s3 (DIE-S81-92).  Sign-off needs kits regenerated from the v2 tree
after adoption; nothing is routed or signed off.

## Post-GRT repair stall (flow fix)
- Measured: post-GRT `OT_MAXWIRE repair_design` (100 um) = 20-40k repeaters; each parasitics refresh legalizes and re-routes
  the touched nets in single-thread incremental FastRoute (perf 82 % mazeRouteMSMDSequential). A_t68 5.6 h between two rows.
- Tried: pitch pass BEFORE global_route (m_t34): 287 s, but full route ends at overflow 30 (c_t34: 0). Residual in the 18-um
  channel ve_m/vs/vsw where repeaters of nets crossing the 225-um vsw core land. So pre-pass is opt-in only (OT_MAXWIRE_PRE=1).
- Branch claude/fable-fix-s81-cong-1116 @a7fe627571f (lane clone epyc8 fable-fix-s81-cong/lane): grt183_make.sh prints
  OT_GRT_REPAIR_PASS every 600 s, stops a repair flat 1800 s and re-runs once with marker 5_1_grt.repair_nostall.json;
  grt_maxwire.tcl then skips the post-GRT repair (full-route result kept, stage continues). 40 related tests pass.
- Gate: intel2 ~/fable-fix-s81-cong/gate_a7fe627.log (ot-merge-queue gate). Proof: m_t34 on epyc8 with the new scripts,
  log run_m_t34_grt3.log; accept = OT_GRT_REPAIR_NO_PROGRESS attempt 2 rc 0 and FINAL overflow 0 in attempt 2. Then READY.
- Open design question: OT_MAXWIRE_UM 100 < core width; nets over wide M5 cores cannot be repeated at pitch.

## Stuck in the old repair (alive, will hit the 12 h line): c_t34, c_t47, c_t62 (epyc8), A_t65 route (epyc9, flat since 12:00 UTC).
Relaunch their grt goal with the merged flow instead of waiting.

## Cleanup done
epyc8: b_t47, b_t62, b_t75, b_t28, b_t8, c_t43 stopped (exact PID + unit) and removed.

## CODEX notes 2026-11-16 10:17 PST

CODEX took over CONG/STRIP/LEAF-PLAN strip work directly; root worker s81_plans owns the coherent F2s4 compose/refloor/bind. No inherited job cancelled or kit patched.

- Flow correction committed+pushed claude/fable-fix-s81-cong-1116 @99618079ab5: progress observation only, no1800s repair timeout, no automatic max-wire bypass, legacy bypass marker has no effect. Targeted6/6 tests and normal remote22/22 gate GREEN (merge_ops record intel2 merge-queue/gates/99618079ab58999dda2a03e404453da034f8bcca.json). Approval/merge root-owned.
- t8 original c_t8 withdrawn: placement233689->801215 nontap, RSZ buffer passes98435+240730+289767; local density1.024. Copied run only failed RESYNTH-GUARD after cap disabled; no unchanged retry launched. New south form allocated all20slots: epyc7 /srv/opentallas-scratch2/claude/fable-fix-s81-cong/{t8s_rows.json,fx_t8s_corr.json,t8s_review.png}. H1278.72->1494.72 (+216,16.89%area); core field/internal stations+216Y, shapes/distances same. FT11 5->6(+1cycle,+1105FTflops), otherssame. Max per-bit hop392um<394.9; allM7sites/wire intersections0. Picture LOOKED PASS-COND; record epyc8 lane/results/geom_review/s81_cong_1116_t8_south.json. Parent Nedge changes; E/W windowcoords stay. Post7f0842db6a16.
- t28 final W/S form allocated all13slots: same epyc7 dir {t28ws_rows.json,fx_t28ws_corr.json,t28ws_review.png}. Outline1442.88x1278.72->1589.76x1386.72 (W+146.88/S+108,~19.5%area), existing sp2 pushes retained then field/internal stations shifted[146.88,108]. FT0 7->9(+2) andFT1 6->8(+2),+2676FTflops; otherdepthssame. Max per-bit hop390.4um; allM7sites/wire intersections0. PictureLOOKED PASS-COND record epyc8 lane/results/geom_review/s81_cong_1116_t28_ws.json. Parent N/Swindows+146.88X,E/Wwindows+108Y MUSTcompose; type-only replacement insufficient. Earlier drafts failed allocator (logs intel2 fable-fix-s81-cong/t28w_auto_stage.log,t28ws2/3/4_corr.log retained); no READY for those. Final logt28ws5_corr.log; admitted unit epcy7 oth-ubuntu-2330865-1794852818 exit0. No jobstillrunningfromtheseallocations.
- All new rows are CANDIDATES, no timing/signoff/adoption claim. Next: s81_plans rebase against current type, refloor die slots/ports, republish clock/reset/collector, attribute FTcycle costs, then strictbind/LATCHECK/G0 and generate matching fresh proof kits. OldB6gE bind cannot coherently qualify newFTdepths.
- Inherited jobs retained: t75b epyc8 detailedplace +epyc10 GPL (both preexisting); t28 c_t28 epyc8 GRT newround after28+NDRdisabledclocks; t72 b_t72 epyc8 GRT iteration4; t43b epyc9 postGRT timingrepair (initialgeometry0 does not establish wholekitPASS); t34/t47/t62 still postGRT maxwire incrementalrepair. No terminal new signoff from these jobs at collection.

## CODEX current handoff 2026-11-16 (supersedes intermediate south forms above)

Final active W-only candidates on epyc7 /srv/opentallas-scratch2/claude/fable-fix-s81-cong: t8w_rows.json W1598.40/H1278.72, t28wh_rows.json W1589.76/H1278.72. Images t8w_review.png/t28wh_review.png actually reviewed; all20/13 FT allocations PASS, max hops374.5/376.4um, no M7 sites/wire-band hits. Earlier south-growth forms preserved as composition-failure history.

t8 FT0 depth6->9 (+3cycles,+3315flops), other FT depths unchanged. Native CS_VER_D0->1 for19 reciprocal rows/235 weighted bits (231 distinct native flops);332 station depths preserved/resited. t28 MUST apply t28wh_core_station_amendment.json AFTER t28wh_rows.json plus t28wh_bus_lane_delta.json; all8 sp2 core pushes retained,335 station rows resited. dn_s_2N_L1 fixed_cycles3->4/table5->6 after R8. FT0+2,FT1+2,FT4/5+6each,FT7+3,FT8..12+2each;16859flops. Primary S windows+146.88X, E/W windowY unchanged.

Parent strip_refloor owns full mutation: combined die32693.76x25980.48um, +1.39335%area,338 movers,1470 portface equalities. Generic added t8 taps relegalized preserving names/count/caps; core taps follow exact owners. No route before coherent bind/current clock rows/image review.

Source canonical one-byte VER nibble358ca85935a; fresh F2s4 uses F2s3-derived die_b178_lfcs_t8w_ver1.v SHA2561d7f96f951f9f23c52ea1a663825109e6a2dc3ac55bb0c4ead007a0356f403e2. Repo overlay has different unrelated forward-clock/reset rows; do not substitute.

Native actual CST VER runtime proof3ded0e33f19 PASS:200000cycles/402428checks/1214warm resets/100000dense cycles; all231bits/235weighted terminal views. Valid-skew mutant caught cycle0; missing-reset mutant caught warm-reset1018. Failed first wrapper compile preserved. Actual unchanged modules; no whole-array sim. Result epyc7 fable-fix-s81-cong/native_ver_1116/result.json; committed results/geom_review/s81_cong_1116/native_ver/.

Latest b6a822df86fe0866d4b9fdbaecbc7fc69a0811bc existing claude/fable-fix-s81-cong-1116: wrapper already advisory only; default OT_GRT_POST_MAX_S now0 not43200 and stale docs corrected. Historical OT_GRT_TIMECAP classified FAIL/FLOW, records immutable. Actual core_flow.stage_grt183 staged-wrapper tests confirm positive diagnostic threshold never stops progress and default/env/config0 work;12 focused tests PASS, bash-n PASS. merge_ops owns normal gate; no duplicate/live kit edits. Matching fresh full-shape physical proofs pending parent bind. Old t43b stale reset recovery -707ps/core skew -446ps requires current reset/taps. Never skip maxwire or impose arbitrary repair deadline.

## CODEX active continuation: strict strip3 and eight current types

Current selected plan: ep10 s81-b3-clk/ev/B6gF2s4strip3.json SHA40d7fe8a745af473740dcceaf3970f93549b8fc1ddae972ee648090f42cd4943; parent strip_refloor owns it. Strict bind run/b/B6gF2s4strip3 is LIVE; no terminal bind/LATCHECK yet. Its src/out/asbuilt_run.json/sidecar_new.json are the only future current tuple, subject to parent terminal release. Current whole-die clock worker F2s4k1b runs on this exact plan. Obsolete strip1 was canceled AFTER ELAB0 success with exact processes, termination143 is supersession, not functional failure.

Ready own helper ep10 fable-fix-s81-cong/gen_countable_strip3_eight.sh, output countable_F2s4strip3_eight. ONE shared GEN prepares current types8,28,34,43,47,62 and CURRENT diagnostic-only75,72; do not use unused pair/six helper drafts. Current t75 FT1/3/5 actual sites DIFFER from proposer t75_rows.json, so no candidate qualification or silent intake. Explicit future model+bind needed to adopt correction. Parent authorizes per-call OT_BIND_PLAN_PACKAGE=off only for future kit-rtl AFTER exact contract verified, skipping87 historical warning siblings (otherwise~6min/type), actual native/source checks retained. Script clears old bypass/CONS/tapcap/reach/PG/col filters and OT_RFLOW; reapplies exact normal S81 PG flags and owner advisory policy. No new time limits. e37 executable ep10 tools-converge/s81/gen_e37_D2_exec is actually qualified productionshape GENexit0/997s/RSS0.95GB, proof gen_e37_probe/proof_exec1.json; contains d7 fastpath already. No RFLOW0: e37 normalS81 defaults honor PGtruth; later nonCONS explicitPG fix matters RFLOW0 only. NO GEN LAUNCHED yet; await parent release then image-review all8 before normal routed flow, collect CTS context while it progresses. Negative CTS WNS alone is advisory, no invented stop/reject. Root gates unchanged.

Original c_t34 ep8 now really completed maxwire (no bypass): repair15096s, GRT18615s/22477MiB, nontap198250, globalRC setup+5.266ps hold-54.262ps/1224 violations/slew6; not detailedFF signoff. m_t34/m2_t34 remain bypassed geometry-only. t75b ep8 reached maxwire64k nets/29651buffers. t47 old fstart/D belongs global writerSTART data-plane; existing two SerDes rows DO NOT cover it. t43 reset recovery is local-copy/reset_regions, NOT fixed by genericclockR3. START/parent owners preserve typed holds and await actual coherent current reads before remedy. Source b6 normal gate GREEN165/165 on main6eebdee6211, two baseline failures also main; root/merge_ops own approval and source merge. Active clone/drafts preserved.

## CODEX latest continuation: seam fixes READY, scoped physical work progressing

Own seam payload committed/pushed existing CONG branch @1c73210c0f1818937f7d3af47b799c02185f494a (result-only; merge_ops owns minimum gate). results/geom_review/s81_seams_1116 contains exact45slot/12type rows,3 actually LOOKED PNGs, finalmodel/native/M7 coverage and preserved initial failures. Ep10 F/seam_fix_1116/rows_ours_stage6.json is same payload.44slot depths retained; ONLY slice_station__t8.ft4 (notleaf8) 3->4 +572FF; native lowerbound1071.120+155.5205=1226.6405 >3x405=1215. Parent separately owns serdes__t12.ft4 and C1x_C10 dn +1 each; own rows exclude those2, combined candidate audits include them exactly. All873nominal lanes PASS, all47affected native seams max401.665um/over0, explicitFTduplicate0;45own final macro-clear wire constructions PASS max404.201um. Eleven initially obstructed RT routes now use real top corridors; wide leaf16.ft2 remains5stages with392.58um max using actual left field (75.26um clear vs50.609um demand). Physical/context/signoff still required, no eventADOPT.

Parent PLAN4 composer has rows/price, plus own channel/PG/reset/control fixes. Full strip3 bind is terminal BIND0/LATCHECK873/873PASS; G0global368 remains pending PLAN4, but rootr339 explicitly authorizes independent unchanged local component work. Refloor exact component_eligibility8.json confirms LEAF8/28/34/43/47/62/75/72 ALLYES: complete local native reset/depth/ports/clock/PG unchanged by PLAN4 work. source/output/asbuilt/sidecar exact ep10 M/run/b/B6gF2s4strip3; raw40d7fe plan. E37D2exec root is actually qualified and defaultRFLOW normalS81 PG valid. Current eight constructor running via intel2 client1101816, unit821421, log fable-fix-s81-cong/gen_countable_strip3_eight.log;64GBreservation, current t8 prep done and t28 progressing. No active script/source/kit changed.

To avoid holding first ready type behind7 independent preps, actual prepared t8 GEN now running via intel2 client1286711, log gen_component_strip3_t8.log, separate output ep10 F/component_F2s4strip3/ot_s81sl_leaf__t8/gen. Same exact approved strict env/profile, no new RTL variant. Original constructor untouched; no physical duplicate. Early ready components must be transported immediately to7/8/9 (measured headroom), actual generated images LOOKED, normal admitted routedflow; no new physical on overloadedE10. Negative CTS WNS advisory under owner profile, no arbitrary reject/cancel/time limit. Never sign t75/t72 oldproposer from current diagnostic geometry.

Wave29 D2 ed968 source is separate oldF2s3 component tuple. Original CONG8leaf types intersect none; new seam ownership overlaps slice_station14/45/46/8. qc_pack owns targeted reversible controller freezes while exactremoteGEN continues; send actual image review approval for these4 when images ready. No prior byte-identical CONG review exists; current proposalPNG3 does NOT qualify oldwave images. Other25 ownedplans clock_reach. No globalpause, live patches or cancels.
