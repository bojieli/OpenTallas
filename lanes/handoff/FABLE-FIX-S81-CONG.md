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
