# S81-STALE-RELAUNCH handoff (2026-11-14 18:1x PST)

## Cause
94 STALE.S81 types (plan 7073a6b4a59, B3x2b) were all rows cancelled at 09:17 "superseded plan block (plan_current=no)" (or DEDUP twins).
select() never relaunched them: their OWNERS parent rows (col_h9_r1/r2, col_h10_r1/r2, col_h9_r0_p3..p6) sit in state ROUTING, which was not in s81 take_states, so the parent only expanded into released retries and the 83 classes with no row on the current key stayed unlaunched.
Dry-run (kit_wave.py select via plan_dies, probe) with take_states * : 83 of the 94 become eligible (162 s81 launches, 62 other leaf/slice rows too).

## Action
- kit_wave.json s81 take_states -> ["*"] (WF-1 default; prev list kept in take_states_prev_s81stale1; backup autopilot/kit_wave.json.bak-s81stale1). coord-commit done.
- kit_wave.json s81 hold_items += col_h10_r2__t1__* (COORD: leave col_h10_r2 to S81-COL-INHERIT; backup .bak-s81stale2). Lift = delete the key.
- No launch outside the wave. Launch check pending next wave tick (grep KIT-WAVE LAUNCH s81/col_h9_r1__t1 in autopilot/log.txt).

## Classes (94)
- (a) live successor: 9 DEDUP twins whose keeper has a live unit (checked systemctl --user is-active): pv3d0d4d97, pvc9270d09, pvcc166a6d, pvd11cc58b, col_h9_r0_p1 pvb3e2a60a/pvb49c16c8, col_h9_r0_p3 cl0cd90c0e pv5b02e93b/pv8d734760, col_h9_r0_p6 pv87853a7e.
- DEDUP release needed: 1 -> col_h10_r0_p4__t1__pvd8c0565f; keeper col_h10_r0_p4__t1__pv07945c1e att10 is RUNNING/geom in the state but its unit kw-s81-colh10r0p4t1pv07945c1e-10-85693 is inactive (stale record). REAP-DEAD should reap it; the twin then releases. Check at next pass; if still RUNNING, ask KIT-OPS to reap att10.
- (b) not in counted plan: 0 (all 94 are in the B3x2b plan, 395 types).
- (c) launch via wave (take_states *): 80 (col_h9_r1 41, col_h9_r2 35 minus none held, col_h10_r1 4, col_h10_r0_p4 3, col_h9_r0_p1 0.. see list; exact set = todo from dry run minus hold).
- (d) waiting on event: dsdv_slice_kv512_C__t1 -> hold B2-HOLD-1113 (S81 UPDATE B2: r0/h10 frame forms, joint216 re-floor, DSDV g4); col_h10_r2 x3 -> S81-COL-INHERIT (hold key added).

## COORD scope addition (10 items)
- ot_s81sl_leaf__t9: RUNNING gen_lint on current key (a); no legal leaf form (t9 ve_m face-clear no spot) -> expect fail until B4L4 (S81-LEAF-PLAN).
- t26 t31 t32 t36 t52, ot_s81sl_kv_leaf__t1, ot_s81sl_leaf__t59: current key has an ENQUEUED/geom row (wave relaunched since the sweep) (a). t36 is also listed in S81-LEAF-PLAN as blocked by bands (B4L4).
- slice_station__t42__clcf44e680: ENQUEUED att12 updated <1 h (a).
- col_h10_r2__t1__cl8b686b3e: (d) S81-COL-INHERIT.

## Full item list (sweep: exclude these)
- col_h10_r0_p1__t1__cl574cc59d__pv3d0d4d97
- col_h10_r0_p4__t1__pvc9270d09
- col_h10_r0_p4__t1__pvcc166a6d
- col_h10_r0_p4__t1__pvd11cc58b
- col_h10_r0_p4__t1__pvd8c0565f
- col_h10_r1__t1__cl95b37463__pv0713a75a
- col_h10_r1__t1__cl95b37463__pv1a6ec9c2
- col_h10_r1__t1__cl95b37463__pva3a8bfd1
- col_h10_r1__t1__cl95b37463__pvce76611c
- col_h10_r2__t1__cl1f5d6c2a__pv0c1de895
- col_h10_r2__t1__cl1f5d6c2a__pvcd889288
- col_h10_r2__t1__cl99efd374__pv1619ecc6
- col_h9_r0_p1__t1__pvb3e2a60a
- col_h9_r0_p1__t1__pvb49c16c8
- col_h9_r0_p3__t1__cl0cd90c0e__pv5b02e93b
- col_h9_r0_p3__t1__cl0cd90c0e__pv8d734760
- col_h9_r0_p6__t1__pv87853a7e
- col_h9_r1__t1__cl49d7a23e__pv047ea3b3
- col_h9_r1__t1__cl49d7a23e__pv0bab1162
- col_h9_r1__t1__cl49d7a23e__pv15cef3f7
- col_h9_r1__t1__cl49d7a23e__pv1c15776f
- col_h9_r1__t1__cl49d7a23e__pv2cabd9a9
- col_h9_r1__t1__cl49d7a23e__pv2ec9c8a9
- col_h9_r1__t1__cl49d7a23e__pv2f96c04f
- col_h9_r1__t1__cl49d7a23e__pv3a0a8b60
- col_h9_r1__t1__cl49d7a23e__pv4108910d
- col_h9_r1__t1__cl49d7a23e__pv461b5256
- col_h9_r1__t1__cl49d7a23e__pv49636389
- col_h9_r1__t1__cl49d7a23e__pv49f0ba38
- col_h9_r1__t1__cl49d7a23e__pv4bd36c74
- col_h9_r1__t1__cl49d7a23e__pv4ef1b59c
- col_h9_r1__t1__cl49d7a23e__pv58f6356d
- col_h9_r1__t1__cl49d7a23e__pv5ffbfb8b
- col_h9_r1__t1__cl49d7a23e__pv62bca836
- col_h9_r1__t1__cl49d7a23e__pv6c1e320a
- col_h9_r1__t1__cl49d7a23e__pv70f04488
- col_h9_r1__t1__cl49d7a23e__pv7466df46
- col_h9_r1__t1__cl49d7a23e__pv87d52780
- col_h9_r1__t1__cl49d7a23e__pv88891f20
- col_h9_r1__t1__cl49d7a23e__pv8ea75ee5
- col_h9_r1__t1__cl49d7a23e__pv9a5bd576
- col_h9_r1__t1__cl49d7a23e__pv9c5966b7
- col_h9_r1__t1__cl49d7a23e__pva7e46565
- col_h9_r1__t1__cl49d7a23e__pvadb6c679
- col_h9_r1__t1__cl49d7a23e__pvadbd1880
- col_h9_r1__t1__cl49d7a23e__pvafa6f454
- col_h9_r1__t1__cl49d7a23e__pvb2dac3cf
- col_h9_r1__t1__cl49d7a23e__pvbb600efe
- col_h9_r1__t1__cl49d7a23e__pvc22584f3
- col_h9_r1__t1__cl49d7a23e__pvc382fb14
- col_h9_r1__t1__cl49d7a23e__pvcb813ee7
- col_h9_r1__t1__cl49d7a23e__pve273b259
- col_h9_r1__t1__cl49d7a23e__pvebe696ff
- col_h9_r1__t1__cl49d7a23e__pvf0f1ccb2
- col_h9_r1__t1__cl49d7a23e__pvfed9fee6
- col_h9_r1__t1__clf32cde8d__pv3b9ba75c
- col_h9_r1__t1__clf32cde8d__pv63f488e9
- col_h9_r1__t1__clf32cde8d__pvee46d7b8
- col_h9_r2__t1__cl774acf45__pv858fb2ba
- col_h9_r2__t1__cl774acf45__pve3ab90e7
- col_h9_r2__t1__cl774acf45__pvea45273b
- col_h9_r2__t1__cl774acf45__pvf8d9f9e5
- col_h9_r2__t1__clb8d86cd5__pv6a2b031b
- col_h9_r2__t1__clb8d86cd5__pvf1445dce
- col_h9_r2__t1__clc9ad8f7e__pv45d0c698
- col_h9_r2__t1__clc9ad8f7e__pv81a5dbf4
- col_h9_r2__t1__clc9ad8f7e__pvcf44b14c
- col_h9_r2__t1__clc9ad8f7e__pvf079625b
- col_h9_r2__t1__clc9ad8f7e__pvfef7c177
- col_h9_r2__t1__clce45cab5__pv2f87774f
- col_h9_r2__t1__clce45cab5__pv37074264
- col_h9_r2__t1__clce45cab5__pv40e9fb5a
- col_h9_r2__t1__clce45cab5__pv467913cc
- col_h9_r2__t1__clce45cab5__pv6827937d
- col_h9_r2__t1__clce45cab5__pv7a260fc0
- col_h9_r2__t1__clce45cab5__pv7b8853b5
- col_h9_r2__t1__clce45cab5__pv8b5a5980
- col_h9_r2__t1__clce45cab5__pv9cc104a8
- col_h9_r2__t1__clce45cab5__pv9e92407b
- col_h9_r2__t1__clce45cab5__pva119e808
- col_h9_r2__t1__clce45cab5__pvaa9a1324
- col_h9_r2__t1__clce45cab5__pvb3f647ea
- col_h9_r2__t1__clce45cab5__pvb6ec679e
- col_h9_r2__t1__clce45cab5__pvb7e88dd2
- col_h9_r2__t1__clce45cab5__pvc6132d1e
- col_h9_r2__t1__clce45cab5__pvcd1d9f5f
- col_h9_r2__t1__clce45cab5__pvd2454d1a
- col_h9_r2__t1__clce45cab5__pvd60e699f
- col_h9_r2__t1__clce45cab5__pvdc7d4221
- col_h9_r2__t1__clce45cab5__pve0486b40
- col_h9_r2__t1__clce45cab5__pve0bffaf8
- col_h9_r2__t1__clce45cab5__pvf390b1f5
- col_h9_r2__t1__clce45cab5__pvf9c773d5
- dsdv_slice_kv512_C__t1
- ot_s81sl_leaf__t9
- ot_s81sl_leaf__t26
- ot_s81sl_leaf__t31
- ot_s81sl_leaf__t32
- ot_s81sl_leaf__t36
- ot_s81sl_leaf__t52
- ot_s81sl_kv_leaf__t1
- slice_station__t42__clcf44e680
- ot_s81sl_leaf__t59
- col_h10_r2__t1__cl8b686b3e
