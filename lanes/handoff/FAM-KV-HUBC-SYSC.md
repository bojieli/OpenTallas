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

## STAND-DOWN 2026-11-21 (Sonnet, ~280k ctx) -> FAM-KV-HUBC-SYSC-R2
State: hub_C D26 a1 RUNNING at place (hold released 5007f36b6eac; OT_LAND_RESERVE=1 for hub_C+sys_c 06f1fc8596f2). sys_c D26 a5 RETRY-INFRA at place (disk-ETA hold, not a design fail).
Findings: hub_C/sys_c station rows already <=331 um hops on D27d/D26; R-REACH-3 window_far ignores internal_stations -> no new rows, defer window moves. sys_c has 6 face pins in clock-site OBS (KV-PLAN-R6 D27d2/D28).
hub_C views: the 6 kvd23_hubc_views lack provenance.json; re-exports staged epyc7 fam-kv-hubc-sysc/views_new (export_view.py from hubc_rk kits). NEVER inside sealed tree (drift incident, reverted; old copies/new_out under fam-kv-hubc-sysc/{old_views,new_out}/<host>). Carry as private-spec overlay or KV-PLAN-R5/R6 D27 row. hub_C a1 may still hit KIT_NOT_SELF_CONTAINED at gen-stage-reuse; if so relaunch after overlay.
Open: epyc8 --ro manifest hardlink drift (other copy shares inodes); kv3_hg_v1p3@2, kv3_hg_v1p4@3 failed src_manifest (not mine).
Next: read hub_C a1 and sys_c retry post-hook; adopt Codex jobs (CODEX-LOG from line 14146); waiter script scratchpad hubc/watch3.py pattern.
