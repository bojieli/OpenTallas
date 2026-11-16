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
