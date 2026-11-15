# TYPE-LEPE (Sonnet) owns S81 dsdv_slice_lepe_nh_mus_LP__t1 (taken over from FAIL-S81-1, 2026-11-14 01:39 PST)
- DRT-0073 evidence: u_bound.u_u_ln0/ck[0] (dsfd_coll_lane_e_safe8_ntf), CLASSIFY 11-09 20:18 on bad69b6bde74; kit a6 (4_cts) control showed it.
- Cause: macro ck pin had no access point (M6 OBS in abstract). Fix already exists: DIE-HBM-97 M6-PG detail view (detail_pg_layer=true, bloat 1) is first in kit_wave.json dies.s81.prov_view_sources[dsfd_coll_lane_e_safe8_ntf]; a7 (11-10) used it, gen+place+geom PASS, but a7 was never routed and its dir on epyc2 is gone.
- Current state: wave item key b227b77dd3bbb status ENQUEUED (a6 superseded-keep), blocked ONLY by hold_items B2-HOLD-1113 (KIT-OPS-2 swap; waits S81 UPDATE B2 DSDV g4 re-floor). No fresh DRT-0073 exists on the current source.
- Other keys of this item are old PLAN FAILs (a3 u_ln1/u_lnl1 no liberty on old event b1a2125433d0; a2 KIT_TOPOLOGY_BIND_STALE).
- I cannot edit kit_wave.json (KIT-OPS-3). Asked via queue: lift the B2-HOLD key for this item, retry key @7, form 2 item_env OT_CONS_KIT=1 OT_CONS_UTIL=0.25 (PLACE_DENSITY=min(kit,0.25), gen_phys) as a second row only if form 1 shows DRT-0073/0255 again.

## 2026-11-14 19:3x PST successor recovery
- lepe_nh_mus_LP__t1: attempt_4 (epyc7) died exit 11 LEC_ASYNC (fleet lec_async.sh fix df804d1a deployed 18:40). attempt_5 on epyc8 (gen done 18:17 PST) is in AUTO-GEOM GRT via ot-run (geom check 19:15), route follows. No DRT-0073 yet on current source. Not relaunched.
- Waiter: intel2 ~/typelepe/wait.sh -> ~/typelepe/wait.log (lepe lines from ap log + DRT grep on epyc8 attempt_5 route logs).
- If DRT-0073 repeats: ck[0] probe on route-input ODB, coordinate with PG-AWARE-1 (pin-on-M7-PG track / cell under M6 pair class) and HEAD-99; ask COORD for Fable review after >2 rounds.
