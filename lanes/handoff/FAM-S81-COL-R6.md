# FAM-S81-COL-R6 handoff (Sonnet 5.5, started 2026-11-21 19:5x PST)
Scope (COORD correction 19:5x): I own stale col_h9_r0_*, bk_sel__t2 and S81-GEOM-OPUS rows. col_h10 rows and private builds stay with FAM-S81-COL-H10-R4 (live); I take only its results, plus any col_h10 row it confirms dropped.
J6 event applied 11-21 04:14; J7 (a6771d121e95) applies 11-22 04:15; J7 col volume is held (j7-col-held-until-view-1122) until proofs J7COL_UCF_VIEW, J7COL_PLACED_READ, J7COL_XO_KEEP_AB, tree_has_sha ae660e1299.

## Triage (26 rows)
(a) still running via private proof: bk_sel__t2 -> S81-BKSEL-R7 run-item pid 733860 (spec s81_bk_sel__t2_1121185210, r7a spread); col_h9_r0_p2 cl9f71e63d pva4376595 (rq keep A/B, run-item 1597702) and cl0045af7b pva2793873 (STAGGER, run-item 1597703), both on sealed J7 tree, gen epyc8, preflight done 19:40.
(b) failed with known class: none in my scope (GRT-0116 xo class is already in J7c/a6771d: 3 stations per xo chain).
(c) superseded, never start old-plan kit: 22 rows (all CANCELLED).
(d) keep: 3 ROUTE-HELD (pv622a6f97, pv110cabb8, pv5b02e93b), not started, not cancelled.

| item | state | class | decision |
|---|---|---|---|
| bk_sel__t2 | cancelled (superseded) | CANCELLED geom SUPERSEDED | (c) superseded: cancelled on the J6/older event; never START old-plan kit; J7 row (a6771d121e95, 11-22 04:15) replaces it |
| col_h9_r0_p1__t1__pv697f40c9 | cancelled (superseded) | CANCELLED gen SUPERSEDED | (c) superseded: cancelled on the J6/older event; never START old-plan kit; J7 row (a6771d121e95, 11-22 04:15) replaces it |
| col_h9_r0_p1__t1__pv8c197f8e | cancelled (superseded) | CANCELLED geom PLAN | (c) superseded: cancelled on the J6/older event; never START old-plan kit; J7 row (a6771d121e95, 11-22 04:15) replaces it |
| col_h9_r0_p1__t1__pvb49c16c8 | cancelled (superseded) | CANCELLED geom PLAN | (c) superseded: cancelled on the J6/older event; never START old-plan kit; J7 row (a6771d121e95, 11-22 04:15) replaces it |
| col_h9_r0_p1__t1__pvf9acce4c | cancelled (superseded) | CANCELLED geom PLAN | (c) superseded: cancelled on the J6/older event; never START old-plan kit; J7 row (a6771d121e95, 11-22 04:15) replaces it |
| col_h9_r0_p2__t1__cl0045af7b__pv622a6f97 | held by die owner (plan event pending) | ROUTE-HELD geom | (d) keep: ROUTE-HELD geom-PASS kit stays held (J6-representatives hold); never started; J7 col volume held until proofs |
| col_h9_r0_p2__t1__cl0045af7b__pva2793873 | cancelled (superseded) | CANCELLED geom SUPERSEDED | (c) superseded: cancelled on the J6/older event; never START old-plan kit; J7 row (a6771d121e95, 11-22 04:15) replaces it |
| col_h9_r0_p2__t1__cl9f71e63d__pv2744f675 | cancelled (superseded) | CANCELLED geom SUPERSEDED | (c) superseded: cancelled on the J6/older event; never START old-plan kit; J7 row (a6771d121e95, 11-22 04:15) replaces it |
| col_h9_r0_p2__t1__cl9f71e63d__pva4376595 | cancelled (superseded) | CANCELLED geom QUEUE-CANCELLED | (c) superseded: cancelled on the J6/older event; never START old-plan kit; J7 row (a6771d121e95, 11-22 04:15) replaces it |
| col_h9_r0_p3__t1__cl0cd90c0e__pv110cabb8 | held by die owner (plan event pending) | ROUTE-HELD geom | (d) keep: ROUTE-HELD geom-PASS kit stays held (J6-representatives hold); never started; J7 col volume held until proofs |
| col_h9_r0_p3__t1__cl0cd90c0e__pv13474472 | cancelled (superseded) | CANCELLED geom_run SUPERSEDED | (c) superseded: cancelled on the J6/older event; never START old-plan kit; J7 row (a6771d121e95, 11-22 04:15) replaces it |
| col_h9_r0_p3__t1__cl0cd90c0e__pv5b02e93b | held by die owner (plan event pending) | ROUTE-HELD geom | (d) keep: ROUTE-HELD geom-PASS kit stays held (J6-representatives hold); never started; J7 col volume held until proofs |
| col_h9_r0_p3__t1__cl0cd90c0e__pv8d734760 | cancelled (superseded) | CANCELLED place SUPERSEDED | (c) superseded: cancelled on the J6/older event; never START old-plan kit; J7 row (a6771d121e95, 11-22 04:15) replaces it |
| col_h9_r0_p3__t1__cl0cd90c0e__pvcb7f0079 | cancelled (superseded) | CANCELLED place SUPERSEDED | (c) superseded: cancelled on the J6/older event; never START old-plan kit; J7 row (a6771d121e95, 11-22 04:15) replaces it |
| col_h9_r0_p3__t1__cl31d0dc4b | cancelled (superseded) | CANCELLED geom PLAN | (c) superseded: cancelled on the J6/older event; never START old-plan kit; J7 row (a6771d121e95, 11-22 04:15) replaces it |
| col_h9_r0_p3__t1__cl8ce97bcb__pv625eef47 | cancelled (superseded) | CANCELLED geom SUPERSEDED | (c) superseded: cancelled on the J6/older event; never START old-plan kit; J7 row (a6771d121e95, 11-22 04:15) replaces it |
| col_h9_r0_p3__t1__cl8ce97bcb__pvc11684b5 | cancelled (superseded) | CANCELLED geom PLAN | (c) superseded: cancelled on the J6/older event; never START old-plan kit; J7 row (a6771d121e95, 11-22 04:15) replaces it |
| col_h9_r0_p4__t1__cl8ef405e8__pv70731479 | cancelled (superseded) | CANCELLED geom PLAN | (c) superseded: cancelled on the J6/older event; never START old-plan kit; J7 row (a6771d121e95, 11-22 04:15) replaces it |
| col_h9_r0_p4__t1__clcb2fbfe8__pv3544fb31 | cancelled (superseded) | CANCELLED geom PLAN | (c) superseded: cancelled on the J6/older event; never START old-plan kit; J7 row (a6771d121e95, 11-22 04:15) replaces it |
| col_h9_r0_p5__t1__pv35382794 | cancelled (superseded) | CANCELLED geom PLAN | (c) superseded: cancelled on the J6/older event; never START old-plan kit; J7 row (a6771d121e95, 11-22 04:15) replaces it |
| col_h9_r0_p5__t1__pv5c8f2166 | cancelled (superseded) | CANCELLED geom PLAN | (c) superseded: cancelled on the J6/older event; never START old-plan kit; J7 row (a6771d121e95, 11-22 04:15) replaces it |
| col_h9_r0_p5__t1__pvbca8d846 | cancelled (superseded) | CANCELLED geom PLAN | (c) superseded: cancelled on the J6/older event; never START old-plan kit; J7 row (a6771d121e95, 11-22 04:15) replaces it |
| col_h9_r0_p5__t1__pvc1b82625 | cancelled (superseded) | CANCELLED geom PLAN | (c) superseded: cancelled on the J6/older event; never START old-plan kit; J7 row (a6771d121e95, 11-22 04:15) replaces it |
| col_h9_r0_p5__t1__pvc6e5797f | cancelled (superseded) | CANCELLED geom SUPERSEDED | (c) superseded: cancelled on the J6/older event; never START old-plan kit; J7 row (a6771d121e95, 11-22 04:15) replaces it |
| col_h9_r0_p5__t1__pveda1ecc9 | cancelled (superseded) | CANCELLED geom SUPERSEDED | (c) superseded: cancelled on the J6/older event; never START old-plan kit; J7 row (a6771d121e95, 11-22 04:15) replaces it |
| col_h9_r0_p6__t1__pv0012ba28 | cancelled (superseded) | CANCELLED geom SUPERSEDED | (c) superseded: cancelled on the J6/older event; never START old-plan kit; J7 row (a6771d121e95, 11-22 04:15) replaces it |

## Live waiters
col_h9_r0 keep + STAGGER proofs: ot-wait --kit <work> --stage place (then cts/grt). bk_sel__t2 r7a proof: BKSEL-R7 spec run-item.
## Next
Representative: col_h9_r0_p2 cl9f71e63d pva4376595 (keep proof, closest: has placed J7 form). Read rq flop count in synth, post-hook CTS, final 5_1_grt.odb TT. Coordinate with H10-R4 (u_cf view, cld01bb4ae ROM-input) and FABLE-FIX-S81-LEAF-R8 (leaf/t39 hold); no duplicate builds.
