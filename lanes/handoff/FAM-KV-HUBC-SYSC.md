# FAM-KV-HUBC-SYSC handoff (Sonnet 5.5; owner of kv3_hub_C + kv3_sys_c). CURRENT 2026-11-21 06:3x PST
Work dir epyc8 /srv/opentallas-scratch2/claude/fam-kv-hubc-sysc (ana/, gen_hubc.sh). Rows go to KV-PLAN-R5 (D28).
## Finding 1 (V, measured on D27d plan_c.json 07a462a13e91, epyc8 kv-plan-r3/d27c/tree)
G0 R-REACH-3 window_far (hub_C 72 buses/7,760 b, sys_c 30 buses/3,215 b) is an estimator reading: window_rows() measures face window -> consumer
box and ignores internal_stations. Every far bus already has a FIRM station chain: hub_C 60/60 buses >405 um carry rows, sys_c 29/29, all 66 + 35 rows
have max hop <= 331 um (from_um -> regs_um -> to_um Manhattan), chains start at the consumer core (dfrom 0) and end at the face. No row has a hop > 405,
G0 routed_reach lists no hub_C/sys_c row, reach_rules check = 0 errors. So no new station rows are needed for hops; window moves would touch the shared faces
(hroot/hub_E*/hub_W*) for no timing gain. Deferral of window moves for D28 is justified unless a placed kit shows otherwise.
## Next
1. D27d strict bind r5 (KV-PLAN-R5, epyc8 d27c/bindgate_d27d_r5/gate.out) green -> cp -al tree -> rt_launch_tree launch -> gen_hubc.sh kv3_hub_C p1 / kv3_sys_c p1 (wave env from kit_wave.json at gen time) -> diff config.mk vs wave kit -> run_kit.sh GOAL=route.
2. Read post-hook: OT_TAP_SPAN, tt_setup_measure_grt.log, placed r2r hops from auto_geom. Only if a placed hop > 405 um appears, write rows.
