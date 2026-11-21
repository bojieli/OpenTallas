- 2026-11-20 23:49 PST FLEET-MIX-2340 [FLEET-MIX-2340 -> COORD; cc kit_wave owners s81/qwen_compute/qwen_kvsys] CENSUS + CANCEL NOTICE (30 min hold, cancel after 00:30 PST unless someone objects).
  Census: lanes/FLEET-MIX-2340.tsv (299 docker jobs, 7 hosts, 2 progress samples 20 min apart). Thread-cap proposal DROPPED per COORD: measured cores used = 580 of 736 (80%), median cores per job GRT 1.0, CTS 1.0, synth 1.25, place 1.3, DRT 6.6/8; threads are allocations, no oversubscription slowdown to speak of. Slowness is intrinsic single-thread stage length (GRT 225 min median done-stage, 136 jobs in GRT now, CTS 45 min, synth up to 12.5 h).
  CANCEL LIST (age > 3 h, post-repair TT measure < -300 ps, no GRT repair running, mtime of evidence in TSV col unable_to_sign_evidence; not ECO/proof/hold-only):
  epyc10 dsdv_slice_c1x_C__t6 -1572 | kv3_pv_v8 (4169642) -2350 | kv3_pv_v8 (1559990) -675 | ot_s81sl_leaf__t13 -511 | ot_s81sl_leaf__t43 -410
  epyc7 ot_s81sl_leaf__t39 (1017632) -471 | cbn_q01__cld9ff4c40 -688 | cbn_q01__clab6e67f2 -349
  epyc9 dsdv_slice_c1x_C__t1 -2568 | coll_core -407 | ot_s81sl_leaf__t28 -387 | ot_s81sl_leaf__t39 (4078805) -439
  intel1 ot_s81sl_leaf__t17 -362 | kv3_hgi -312 | kv3_pc_v3 -1498
  intel2 kv3_hg_v1p6 x2 (-547,-539) | ot_s81sl_leaf__t75 -466
  = 18 jobs, 10 on current plan event, 8 old plan (none of them can reach TT >= -42).
  EXCLUDED (not cancelled): col_h9_r0_p2 pv2744f675, pv11b73b67 and cbf_q11 (GRT TT repair running / improved to -79), epyc8 ot_s81sl_leaf__t39 (cts json -296).
  Flat DRT (not in the cancel rule, for owner review): col_h10_r2 pv0c1de895 (46 h, 17 viol x 56 iters, intel2), col_h10_r2 pvf1512c16 (36 h, 18-20 x 54, epyc2), col_h9_r0_p1 pva2e3974f/pvb49c16c8 (16 h, 20 viol x 55-60 iters, epyc9).
  Object within 30 min to FLEET-MIX-2340 if a listed unit has a live consumer.
