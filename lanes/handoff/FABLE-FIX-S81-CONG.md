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

## Update 2026-11-16 ~14:30 PST (after Codex coordination 11:20-13:22)
- Rows: t34/t47/t62 are in F2s3 (adopted r331, D2 tree). t43b/t75/t28/t8 are in DIE-S81-92's F2s4strip1 (t8/t28 W-only widen composed
  by Codex). t75 proof: c_t75b (epyc8 /home/ubuntu/ot-scratch/claude/fable-fix-s81-cong/kit/c_t75b) GRT FINAL 0, 0 restarts; rows
  epyc7 fable-fix-s81-cong/t75_rows.json (READY-ROWS 5192879).
- Stall branch: merged as 631a6971d8 (claude/fable-fix-s81-cong-1116 @b6a822df86f). Main carries ONLY the observe part:
  OT_GRT_REPAIR_PASS every 600 s, OT_MAXWIRE_PASS lines, opt-in OT_MAXWIRE_PRE. Codex commits 99618079ab + b6a822df86 REMOVED the
  30-min no-progress stop and the marker skip ("observe without cancelling or bypassing"). So the 3-6 h silent repair is still
  there on main; it is only logged. My proof of the stop (m_t34 epyc9, m2_t34 epyc10: attempt 2 rc 0, FINAL 0, ~1 h 50) is for
  a7fe627571f, not for main. Decision needed from COORD: restore the stop, or accept the long repair.
- Real lever still open: OT_MAXWIRE_UM 100 on nets crossing 225-um cores (repeaters land in core channels).
- Live: c_t8 (old t8c row, OT_CELL_BUDGET_GATE=0) epyc10 run_c_t8_grt_e10b.log; c_t75b epyc8 in the old post-GRT repair;
  c_t34/c_t47/c_t62 (epyc8) and A_t65 (epyc9) were in the old repair at last read (not re-checked after 17:00 UTC).
- These are all old-tree (B6gE) proof kits: evidence only. Sign-off = wave kits from the D2 tree after F2s3 / F2s4.

## PARKED: Claude limit reset; final Codex return state

Root explicitly ordered park. No further edits or launches after the requested handoff update. Fleet jobs remain as found; nothing cancelled or live-patched.

### Final seam / PLAN4 intake
- READY result-only branch commit1c73210c0f1818937f7d3af47b799c02185f494a, existing claude/fable-fix-s81-cong-1116. Exact45slot/12type payload: results/geom_review/s81_seams_1116/rows_ours_stage6.json (same ep10 F/seam_fix_1116/rows_ours_stage6.json). Actual3PNG LOOKED and final review/audits committed.44same-depth; ONLY slice_station__t8.ft4 +1/+572FF, parent has explicit lane ctrl__s_0N_C__seqhost price. Combined with parent's2 separately owned +1 slots:873 nominal lanes PASS;47affected native seams max401.665um/over0; explicitFTduplicate0; all45own macro-clear wire constructions PASS max404.201um. Parent strip_refloor has final rows and composes/prices PLAN4 with reset/control/PG/channel changes. No model/geometry hold from CONG, no physical/adoption claim.
- Artifact normal gate NOT RUN: merge_ops found ep2 scratch36GB<50GB floor; no qualified host. Not a test/source failure. Gate/merge remains root/Claude task after actual headroom. Source b6/paired0ac already approved/main; no duplicate native VER proof needed.

### Eight current leaf components and NEW generator failure
- Scoped component8 eligibility ALLYES at ep10 M/f2s4_refloor_codex/component_eligibility8.json under rootr339. Types: ot_s81sl_leaf__t8,t28,t34,t43,t47,t62,t75,t72. Complete local reset/ports/clock/PG unchanged by PLAN4;75/72 diagnostic only. Exact terminal strip3 tuple ep10 M/run/b/B6gF2s4strip3/{src,out,asbuilt_run.json,sidecar_new.json}, raw ev/B6gF2s4strip3.json SHA40d7fe8a745af473740dcceaf3970f93549b8fc1ddae972ee648090f42cd4943; BIND0/LATCHECK873PASS. GlobalG0needs PLAN4, no eventadopt.
- Original8 constructor STILL RUNNING: intel2 client1101816, ep10 admitted unitoth-ubuntu-821421-1794862805, log intel2~/fable-fix-s81-cong/gen_countable_strip3_eight.log. Helper ep10 F/gen_countable_strip3_eight.sh; W=F/countable_F2s4strip3_eight. t8 kit-rtl + topology PASS and immutable prepared files exist W/rtl/ot_s81sl_leaf__t8/kit_rtl.f; currently t28 prep. All actual native checks retained, percall OT_BIND_PLAN_PACKAGE=off only suppresses historical sibling warning census. Do not restart or patch progressing constructor.
- Early separate prepared-leaf8 GEN TERMINAL FAIL5: intel2 former client1286711, ep10 unitoth-ubuntu-1361169-1794863912. Log intel2~/fable-fix-s81-cong/gen_component_strip3_t8.log and ep10 F/component_F2s4strip3/ot_s81sl_leaf__t8/gen.log. Exact cause STALE-CORE-VIEW ot_s81sl_vsw: e37D2 TTlib actualc005b97581b1 != signedcbc77fd548ba. This is a signed-view cohort/profile mismatch, NOT RTL/geometry or physical failure. Fleet_flow/root informed. Do not bypass SHA gate or overwrite failed directory. Qualified col GEN had not exercised this leaf macro. Correct trusted cohort/profile, then reuse completed prepared8 package for fresh distinct GEN attempt; original batch will hit same issue later if unchanged. No new physical started. Transport ready eligible kits to7/8/9 after actual images reviewed; avoid new E10 physical.

### Exact inherited physical states at park
- ep8 confirmed active containers: c_t75b ebc51b3be770 (F/kit/c_t75b), c_t28 35b8051b9fe4 (s81-strip-o/kit/c_t28), c_t62 e935e2a193ba (s81-strip-o/kit/c_t62), b_t72 10c2c53e2de5 (fable-fix-s81-strip/kit/b_t72), c_t47 2e600814049f (s81-strip-o/kit/c_t47). All kit tails under kit/gen/ot_s81sl_leaf__tN/run/logs/asap7/dp_ot_s81sl_leaf__tN/base/.
- c_t75b ep8 in genuine maxwire64k nets/+29651buffers; c_t28 repeatedNDR globalroute extra11/30; b_t72 extra7/30; c_t47 setuprepair >1050steps with old fstart_ft4_o/D WNS~-592.443ps. START owner knows global writerSTART class not solved by2SerDesrows; current source proof required. No new gates/cancels.
- c_t62 still CPU-active last maxwire115k nets/+50682buffers, old24.21GiB/64GiB observation. IMPORTANT actual live old grt183_make.sh still has a killing legacy wall-cap implementation and config.mk exports OT_GRT_POST_MAX_S=43200. Future merged cap fix does NOT retroactively uncap it. No live edit/cancel performed; root/Claude must account for legacy flow-cap hazard, classify any cap as FLOW not hardware. Preserve progress.
- Original c_t34 ep8 completed genuine maxwire15096s, totalGRT18615s/22477MiB, nontap198250. GlobalRC setup+5.266ps/hold-54.262ps/slew6, not detailedFF/signoff. m_t34 ep9 andm2_t34 ep10 completed using retired skip-maxwire marker: geometry-only, NEVERclosure.
- NEW c_t43b ep9 terminalFAIL DPL-0033 after actual maxwire repair1245s (339448->402279 leafinstances), postrepair routing1887s; finalstage3h59m. detailed_placement check found overlap/padding between u_bound.u_ft_ft5_o_3/q[274] and q[267] (DFFHQNx3_ASAP7_75t_R). Full log F/kit/c_t43b/kit/gen/ot_s81sl_leaf__t43/run/logs/asap7/dp_ot_s81sl_leaf__t43/base/5_1_grt.log. This is a real late FT-bank placement failure, distinct from old native-reset recovery -707ps class; current-source resite/actual footprint-padding/hold-legalization context needs diagnosis if reproduced, no bypass. No success claim.
- Duplicate ep10 oldc_t75b: remote unitoth-ubuntu-1213475-1794851417 now inactive/dead Resultsuccess ExecMainStatus0, no active matching container observed. Its central client had SIG15 link interruption and reported remote command STILL RUNNING at that time; intel2 log run_c_t75b_grt_e10.log. Last retained GRTtmp extra6/30, no final GRT artifact or physical PASS collected. Treat as incomplete terminal collection, not a signed win.
- Oldt8 withdrawn geometry remains withdrawn; no unchanged retry. Current W-only8/28 designs and sourceVER proof remain final proposal, physical measurement pending correct signed view.

### Four oldwave image holds
qc_pack holds only hubcontrollers slice_station14a6/45a6/46a7/8a32, actual remoteGEN continues. Exact ledger intel2 coord/autopilot/codex_s81_gen_review_freeze_1116.json; source waveed968/oldF2s3, separate from new proposals/fresh8leaf. CONG has NOT yet viewed actual4wave images and sent NO approval. Do not unfreeze by assuming proposalPNG3 is identical; it is not. qc_pack SIGCONTs exact controllers after actual scoped image approval; other25 ownedplans/clock_reach. Root/Claude takes release-owner role now.

## Update 2026-11-16 ~14:15 PST (COORD r341)
- Stop restored: claude/fable-fix-s81-cong-stop-1116 @827bba3961cc (revert of 99618079ab on main, OT_GRT_POST_MAX_S default 0 kept),
  GATE main=96cae5872b9 23/23 GREEN (intel2 ~/fable-fix-s81-cong/gate_827bba3.log). READY posted; COORD approves on GREEN.
- After merge: relaunch t34/t47/t62/t65 as D2-tree (F2s3) kits, NOT the old c_* kits. Old kits still alive at last read: c_t62 (epyc8),
  c_t75b (epyc8 root scratch), c_t8 (epyc10); stop by exact PID once the D2 kits run.
- 4 CONG-held controllers (slice_station t14/t45/t46/t8) reviewed on plan geometry (no cores, hops <= 389) and released by kill -CONT
  (post ae75524). Image: rtx-pro scratchpad rvdir/ss4.png.
- Codex notes to carry: (a) old c_t43b ended DPL-0033 after the real max-wire repair (ft5_o stage 3 bits 274/267 overlap): check the
  t43 ft5 band row for two bit sites on one legal site before F2s4strip1 binds; (b) leaf8 GEN STALE-CORE-VIEW on ot_s81sl_vsw
  (D2 TT lib c005b97581b1 vs signed cbc77fd548ba): needs the signed-view cohort fixed, never a hash-gate bypass.
- NOT DONE (r341): structural fix (pitch on placement parasitics before ONE full GRT without the overflow-30 regression, or threaded
  incremental GRT); t34 -99 ps at GRT RC; GRT proof of the t28/t8 W-widen forms; t43/t75 rows handed as files (READY-ROWS posted, in
  F2s4strip1 list per DIE-S81-92).

## Update 2026-11-16 ~13:45 PST (COORD r351)
- Stop branch 827bba3961cc approved (r351); NOT on main at 21:43 UTC. After merge: D2-tree kits for t34/t47/t62/t65 (blocked too by
  the vsw STALE-CORE-VIEW, handed to TOOLS-CONVERGE-1115, post 5cd86c5).
- t43: posted row is site-legal; DPL-0033 = stage-3 station in the 9-um vsw/rxsf gap. Fix row epyc7 fable-fix-s81-cong/t43d_rows.json
  (ft5 band x 440..500), FIX-ROW d45b382 to DIE-S81-92 for B6gF2s4 (strip4 plan is already composed: needs a correction row).
  Robust form: u_vq -25 um y. Proof kit c_t43d: gen on epyc7, chain intel2 chain_gen_launch.sh (OT_HOSTS=epyc10), log run_c_t43d_grt.log.
- t34 -99 ps (TT, GRT RC), from postcts_gate_TT.log of m2_t34 (epyc10): launch u_bound.g_u_vp_driver_x_qd_q[12] (std tap clk_t33,
  insertion 437 ps) -> hard core u_u_vs/x_qd[12] (core tap clk_c6, insertion 149 ps). Skew -288 ps + setup 43 leaves 502 ps;
  data 687 ps = 7 repeaters on a ~600-um wire from the vp field to vs. Class: std-tap "driver" flop feeding a hard-core input whose
  clock leads by ~290 ps, flop left at the source. Fix (no cycle): place every *_driver_*_q flop that feeds a core input within
  ~100 um of its core pin (input-side twin of core_out_land.tcl), so the long wire is flop-to-flop in one tap domain. Fallback:
  clock those flops from the core tap, or +1 stage at the pin with a LATCHECK row. Only the worst path was read (one path per group).
- t28/t8 strip4 widen: no GRT proof yet; needs kits from B6gF2s4strip4 (bind running at Codex) on D2. c_t8 (old row, gate off) at CTS on epyc10.

## Codex handback after resumed takeover; Claude reset now

No new jobs, edits, or merges after root reset notice. Preserve all admitted jobs. This addendum records last observed state; no result is inferred from stale logs.

CURRENT ADOPTED TUPLE / EIGHT CONSTRUCTOR
- Parent adopted actual819/D3. Canonical receipt: ~/coord/lanes/handoff/s81_atomic_apply_1794875248640116069.json. E10 /srv/opentallas-scratch2/claude/s81-b3-clk/run/b/B6gF2s4tapfix1/{src,out,asbuilt_run.json,sidecar_new.json}; raw src/physical/die_plan/s81/plan_h2_2249.json SHA819037bbe371ad99945d4a9b3f11a536060280b59bd1c4ac48167d9cf77b140d. BIND0, LATCHECK873/873 PASS, leafCS509PASS, newG0errors0. All physical holds remain.
- LIVE single constructor: intel2 client3945840, E10 unit oth-ubuntu-1354323-1794875694, log ~/fable-fix-s81-cong/gen_countable_f2s4tapfix1_eight.log. Normal admission64GB/8threads/disk8, admitted after1s. Last actual observation: leaf8 kit-rtl0 and prepare-stations0; leaf28 kit-rtl underway. No GEN terminal observed yet. Do not duplicate/restart.
- Script E10 /srv/opentallas-scratch2/claude/fable-fix-s81-cong/gen_countable_f2s4tapfix1_eight.sh; outputs /srv/opentallas-scratch2/claude/fable-fix-s81-cong/countable_F2s4tapfix1_eight. Types leaf8/28/34/43/47/62/75/72. First type failure/result should be collected promptly; generated images MUST be reviewed before physical. Transport eligible finished kits to normal E7/8/9 headroom; E10 constructor only. t75/t72 current diagnostics, no proposed-row adoption.
- Actual immutable private CODE: E10 /srv/opentallas-scratch2/claude/fable-fix-s81-cong/code_2ef_ac601. D3 tools copied, exact approved ac60199 BG helper overlaid; runtime imported file verified SHA2729c29414e2af31e5d9641c087c2af913fb42a83573104ea95f1de17b4646cc;18 actual fixture/control tests PASS. code_profile.json SHAac78f42b90ce228f9ece738f793e6593c23584786b437ef9358e7ffc2920da4d, qualification.json records import path. Tools/profile readonly. Separate RTL_ROOT remains /srv/opentallas-scratch2/claude/kw45/src_s81_pin_3c913dbdfb23_f2s4_cohort_d3 manifest35eaaa5d65dae530b163ca2fba251d2dfd309006d6b61ab22fa126e79cdaea59. Do not patch D3/profile/active helper.
- Helper clears prototype allow-congestion and CONS/M9 overrides, retains normal PG/coretap/plan grant and POST_MAX_S0. No oldstrip3 AB/e37 scaffold. Old failed strip3 prep artifacts remain intact.

SOURCE / BARE ALIAS
- ac60199a9f99a8740648ebd4464992b67e469680 on existing branch claude/fable-fix-s81-cong-1116 normal gateGREEN2/2, no baseline; rootr377 approved, merged main1ac6e2d75bd16:28; normal six-host sync c390869fd3e2 completed16:34:28rc0. Source includes earlier1c45seamartifact. No duplicate gate.
- Fix exact-name-first unique indexed image prefix, simple known-width/equal-width sliced/concat assign tracing. Actual t43 IN69/595 andOUT410/668 resolved; IN526/OUT258 remain unresolved, no wholebus qualification inferred.
- NEW known case: current819 leaf34 native names are bare u_u_vs/g_u_cst_*; approved indexed-prefix fix leaves those unresolved. Root authorized absent-prefix extension with actual595/668 leaf34 fixture, exact-name-first/single-candidate and bare/indexed ambiguity refusal. NEXT PROFILE ONLY, normal gate; NEVER patch running profile/job. Candidate only in local /tmp/codex-s81-cong/bg_bare.py; not copied to source clone, not tested/committed. Current source fixture /tmp/codex-s81-cong/t34_current819_unprepared.sv, compressed /tmp/codex-s81-cong/kit_bus_t34_current819.sv.gz. Complete candidate/tests before sourceREADY.
- Owned clone E8 /srv/opentallas-scratch2/claude/fable-fix-s81-cong/lane remains branch ac60199; old stop827 branch separate. Preserve four untracked geometry drafts, including minimal_stage3. No timer/skip propagation.

OWNER SCOPE RESOLVED r378
- Existing OWNER11-11 verbatim grant leftoverM8 all dies after frozen PG/clock/reset/inter-type routes; canonical COORD-REVIEW-QUEUE11497(11-14 18:4x): types may use leftoverM8/M9 if kits import frozen infrastructure as obstructions. Current819 M8grant enabled/no types filter covers eight parent leaf types, not hardened child internals or bareM9. Retain normal actual grant, no blanketM7/new waiver. Prior M7-only t43 capacity reasoning is conservative and must not force unnecessary macro moves. No pending owner question from CONG.

T43 NEXT MODEL / HOLDS
- Actual source: VS.g35 direct IN; VS.s_d156/s_v from VP soft producers/PVS_D0, not raw facebus. OUT mixed VS99/VQ278/VP257/VN33/control. Existing bus MAX1 each. If direct g/OUT reach requires MAX2, book full596+669=1265FF and actual dn/up+1 after regenerated source, not endpoint292 subset. Packed oldD1 helper respreads but does not realizeD2; fresh source/bind required. Fullwidth banks/source mapping incomplete, no typedREADY.
- Scratch E7 /srv/opentallas-scratch2/claude/fable-fix-s81-cong/t43v_current. Conservative cluster candidate VQ-25.11Y, VS/VSW/RXSF+25.92Y; FT5 bank4 resited598FF still8stations, bodyhop<=305.91;27 declared rows excluding VP-source holds79/80 allocated. t43cluster_wire_audit.json all actual declared-pin/bank pairs constructiveM<=7 max394.323. This is NOT full source/wholebus/capacity proof; actual M8 grant may remove need for extra cluster translations.
- E8 same lane scratch/t43v_current/t43cluster_clock_legalized_rows.json official legalizer moves only generic clk_t21 [356.4,617.68]->[356.4,631.18], names/counts retained; core-owned taps follow moves. Fullclock/source inventory still held.
- IMPORTANT draft reports copied mission_cycle_delta0 from old script: correct to SOURCE_HOLD/null pending actual bus/source pricing BEFORE publishing. Some old metadata duplicates/misnames native ports; do not claim literal metadata equals actual RTL connectivity. Current actual native t43 U271, M11, VER231 vs ten-row endpoint count274. Source fixture logical extraction available from cores.

T34 PRIMARY STRUCTURAL MODEL (NO VSW/RXSB MOVE)
- Root primary remains VQ+43.2Y only, shape/outline unchanged; zero explicit FT cells covered on actual819. No VSW/RXSB relocation merely for obsolete100um repeater target. Root allows prospective disabling100um ADVISORY repair with real405/TT/FF/capacity/source model, not old timeout-skip or livekit patch.
- Immutable OLD B6gE 3_3 packet is provisional model vehicle, NOT current819 equivalence: intel2 /srv/opentallas-scratch2/claude/fable-genbug/core_in_land_1116/cone_packet_v2.json contains256FF,859upstreamcomb,1128outputBUF/full edges/roots/shared fanouts. Existing comb/buf182.6874um2, FF74.6496um2. Actual VSWOBS M1-M5 supports legalM6/M7 overflight.
- Pure necessary placement: fixedroot/capture405 with actualD/Q offsets/FF dimensions, zero-halo macroBODIES leaves10/256 impossible; conservative unproved8.64guard leaves122, NOT an architectural122 claim. VQ+34.56 frees body domains; +43.2 frees all conditional8.64 domains. Files intel2 ~/fable-fix-s81-cong/cone_model_1116/{necessary_ff_regions_macro_body.json,vq_shift_43.2_guard8.64.json}.
- Disjoint256FF pack with VQ+43.2 and common mux790,575 has min necessary endpoint margin7.937um. Shared outside-family upstream ancestor closure336cells, cloning adds18.19584um2,0FF/0cycles. Artifact samefolder/vq43_ff_pack_and_clone_area.json. NOT YET full comb/output-cell packing or DAG routed lengths; no clock/FT/IS source qualification or image/route. Leave original outside cones untouched; electrical load changes still need full context TT/FF.
- Current819 t34 exact native banks U271/Y132/M11+11=425FF, source copied current emitted bound; E10 F/t34_native_banks_current.json. Old physical packet M21 differs currentM22. Do not invent missing old stage0 control pose. E8 /srv/opentallas-scratch2/claude/fable-genbug/core_in_land_1116/ff_coordinates.json actual35562DFF pins/poses, filtered427. Worker source extraction only; noSTA/PNR/ODBwrite.
- Current native t34 candidate inputs E10 /srv/opentallas-scratch2/claude/fable-fix-s81-cong/t34_vq_current/native_inputs.json from actual819/D3, VQ+43.2; source scriptF/t34_vq_inputs.py. Need source-exact all affected IS including bare core captures, real CST U/Y/M banks, taps/clock, fullwidth bus source mapping and image before source helper/physical build. Old metadata contains duplicated/reversed fields and nonexistent VN_a y_i/y_v; native_banks(actual emitted source) is authoritative.
- Cores logical mapping: OUT VPlo256 bits34..289 from g_u_lf1_u_vp_driver_lo_d_q; validbit290; controlbit0 ORtree multi-source. IN trace to first registered consumer/memory capture frontier, stop register barriers; unknown expressions remain unknown. Existing BG.Netlist APIs useful, no guessed nativeVP core.

OLD JOBS / FAILURE COLLECTION (last observation, preserve all live)
- E8 c75 Docker ebc51b3be770 CPU100%/24.44GB, maxwire64000/+29651buffers lastlog20:05UTC; no arbitrary kill. E8 c62 e935e2a193ba advanced pastmaxwire tosetuprepair220 WNS-73.315, CPU100%/24.5GB. E8 c28 extraNDR17/30. Paths c62/c28 /srv/opentallas-scratch2/claude/s81-strip-o/kit/.
- E8 c47 globalGRT terminal35977s/25GB, TTglobalRC-841.07/hold-76.11, congestion100%/53077gcells>90; notfinalsignoff. START producer remedy remains owned, no old rerun.
- E10 old c43d c1cf02fbc76d, oldc43v ff637309685f, oldc8 3a6367b75e85 running last observed; no new launch by Codex. Preserve. Old c43b DPL overlap failure remains immutable.
- E10 duplicate c75 exact durable completion /var/tmp/ot-heavy/completions/oth-ubuntu-1213475-1794851417 = start1794851419/end1794864254/RC143 at21:24:14UTC. SIGTERM, not hardware verdict; partialGRT6/30 retained. Client signal15 sender1351501bash; do not infer who. IndependentE8 c75 running so no duplicate retry. ot-heavy units are --user .scope; missing-unit defaultResultsuccess is not measuredexit0.
- Inherited cut flags leaf2/3/57 are explicit CONG next model ownership, not solved by baseline inheritance; leaf43 active bucket. Four old review-held controllers already released by Claude13:36/r351 and ledger reconciled0: no repeat signals/reviews.
