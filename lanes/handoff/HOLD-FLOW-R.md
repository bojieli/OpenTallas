# HOLD-FLOW-R handoff (closure lever 1, routed internal hold)

Branch claude/hold-flow-internal-1116 (own clone /home/ubuntu/wt/hold-flow-internal-1116 on rtx-pro; mirror on intel2 git).

## RESET section (read first)
State is in this file only. No live job of QC-TYPES-R / HEAD-TYPES-R was touched. HEAD hw4 eco_hw4/i1t is live and untouched.

## What the branch does
1. tools/die_plan/hold_eco_internal.py: `plan` sizes one targeted HB4 insert per internal capture pin for +10 ps
   (1 cell up to 25 ps need, else ceil(need/29.8) and >= 2, max 4); ports and non-capture pins are never padded; count is cut to
   the TT slack the endpoint can pay (HB4 132.8 ps TT, gate -42), partial cuts are counted, endpoints that cannot pay one cell
   are listed. `gate` = DRC 0, TT >= -42, internal FF hold >= 0, no worse than before.
2. post_route_drv: OT_PRD_HOLD_PLAN=<plan.tsv> makes prd_hook.tcl run hold_eco_internal_insert.tcl (free sites / filler within
   7.2 um of the capture PIN, macro rows and row-segment ends respected) instead of the global repair_timing -hold; the existing
   incremental GRT + route-keep DRT re-routes only the touched nets. prd_mk.sh stages the file and plan, prd_run.sh passes it.
   hold_eco_internal_dump.tcl writes the endpoint table in an STA session; hold_eco_internal_route.tcl is the standalone route form.
3. Pre-route margin: core_flow / gen_phys / gen.py HOLD_FF_MARGIN_DEFAULT 0 -> 10 ps (the in-flow repair scope is reg2reg, so
   it is internal endpoints only; port starts / output ends excluded). eco_loop HOLD_MARGIN_PS 5 -> 10. Never 20: P3's 20 ps
   picked 26,258 endpoints for 6; run P3 with margin 10 and an insert of its 6.
4. Tests: tools/die_plan/test_hold_eco_internal.py (12) + updated margin assertions.

## Proof on coll_n (copy of the a22 routed DB, epyc2 /srv/opentallas-scratch2/claude/hold-flow-r/proof1)
- plan from the 64-endpoint FF table of the hand pilot: 63 endpoints, 86 HB4 (pilot 80, target +10 not 0), 1 port path skipped.
- insert on final_state/6_final.odb: 86 HB4 at 63 pins, 115 fillers removed, check_placement OK (MEASURED).
- bug found by the proof and fixed (da21443): a kept filler handle was destroyed after reuse and took 4 new HB4 with it; the
  insert now fails closed on a lost cell / census mismatch. After the fix: 86 of 86 present, check_placement OK.
- route (hold_eco_internal_route.tcl, same recipe as the pilot, only nets of the new cells ripped) launched on epyc2 via ot-run,
  log proof1/route.log; then sign-off sessions (copy of coll_n signoff2 ff/tt sessions, /base = routed DB). RESULT pending.

## Gate / READY
Branch claude/hold-flow-internal-1116 @da21443c369 on main 8f5fed38bce: GATE pass=113/113 GREEN (ot-gate-remote, record
intel2 merge-queue/gates/da21443c369b8365c465733e163a02bc0c452a4b.json). Pre-existing py3.10-only failures
(gen_core_kit_hbm f-string, estimate_parasitics list) are not from this branch.

## Next steps
- when the proof route ends: DRC count from route/hei_drc.rpt, run the two sign-off sessions, run `hold_eco_internal.py gate`.
- QC-TYPES-R: W0 (858) / H16 (171) / H17 (327): produce the endpoint table with hold_eco_internal_dump.tcl in the type's routed
  FF+TT session, `hold_eco_internal.py plan`, then OT_PRD_HOLD_PLAN=plan.tsv through eco_loop / prd_mk. P3: insert of its 6.
- HEAD-TYPES-R: hw4 (31) the same way; his live eco_hw4/i1t is not touched.


## CTS scope follow-up (COORD 11-16 18:4x)
Branch claude/hold-cts-scope-1116 @36f8f872e51 on main 9b0fa68ec7f, GATE 37/37 GREEN, READY posted. ot_hold_repair_scope accepts
3_place.sdc + 4_cts.sdc; OT_CTS_HOLD_PAD=HB2|HB4 (ot_cts_hold_pad). Test tools/test_cts_hold_scope.py (44 -> 2 endpoints on a 40-port fixture).
Affected = two-mode kits (override export OT_HOLD_MM = 1) whose CTS repair is not skipped: core kits via core_flow (no SKIP_CTS_REPAIR_TIMING)
and hand-driven ref_tile / abi3 / closure_loop builds like headseg44. gen_phys type kits with a hold_ff_margin skip CTS repair (unaffected).
Live count NOT measured: fleet find scans of config.mk returned nothing within limits.

## CODEX explicit BC library source fix (2026-11-16 23:0x PST)
Inherited clone /home/ubuntu/wt/hold-flow-internal-1116 (rtx-pro), new same-clone branch claude/hold-prd-explicit-bc-1116.
Final29e7dd25e6b8052a066e7ed804ae4d8c40173243 pushedGitHub+intel2bare, cloneclean. Root may reclaim clone after source handback.
Only owned3files: prd_mk.sh, test_post_route_drv.py, test_prd_mk_marker.py; inheritede2d47macroplanner5files unchanged.

Cause: prd_mk synthesized ML_FF from ADDITIONAL_LIBS TT suffix, ignoring explicit correct BC_LIB_FILES. Custom pk2_tc.lib stayedTT in appendedBCrow despite pk2_BC.lib alreadydeclared.
Actualbksel source line36 correct BC_NLDM+3FFlibs+ot_s81ph_hq_pk2_BC.lib; oldgeneratedline142 wrong. S81owner restoredsignedconfig before sign/export, so all actual signed evidence/archives alreadycorrect and untouched.

Fix preserves explicit declaredBC RHS/list exactly, validates literal/work declaredFFfiles, refusesmissingBC even whenTCexists.
Only absentBC uses old suffixfallback. No corner/timing waiver, no hardware or model latency change (0cycles).
Focused actualmk6PASS (customRHS with/withoutBC_NLDM, missingBC refusal, legacyfallback tests); extractedmarker4PASS.
Originalscript negativecontrols catch both customwrongTTrow and missingdeclaredBC falsepass.
Firstf867normalRED4 was extractedmarkerfixture missingnew precomputedBC_RHS; successor fixesfixtureenvonly, failedoutputretained E7slot2/mq/failure-output/gc-f867*.log.

FINALnormalGREEN15/15 onmain419279e2843, E7unit3914954-1794898814 DONE0.
Record intel2 ~/merge-queue/gates/29e7dd25e6b8052a066e7ed804ae4d8c40173243.json.
Log intel2 /srv/opentallas-scratch2/claude/mq1/tmp/rg/hold-prd-bc-final-codex-1116-2300.out.
Rootapproval/mergeowned. No livejob modified and no component proof rerun.
