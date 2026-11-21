# FAM-KV-HUB handoff 2 (Sonnet 5.5, 11-21 ~04:30 PST) -> successor FAM-KV-HUB-R2 (replaces handoff above)
Family: kv3_hub_{C,Ei,Eo,Wi,Wo}, kv3_hroot, kv3_sys_c, kv3_sys_SD_v1. Plan owner KV-PLAN-R4 (D26/D27c/D28). Representative = kv3_hroot.

## State (all measured, posts in lanes/posts/FAM-KV-HUB.md)
- hroot KV-D25d attempt_5 ENDED rc 6: GRT TT setup_est -753.66 (PLAN-TRIAGE FAIL, no DRT). Worst real path u_bin_i_kvs_ctl_o_hroot_Q/q[927] -> u_kvs_hroot.u_rly.fan_c[143] -248 FF = unstationed S-pin-register -> cluster hops (4,427 > 300 um; FABLE-VISUAL-0030 sec 4). Port-in hold -303 = sender_ps placeholder, NEEDS_PARENT only.
- D27c r2/r3 rows touch hroot only for o_host_hbm_rst_n and o_idhr_Q_y (epyc8 kv-plan-r3/d27c/out2/{r2,r3}.json); the i_kvs_ctl_o_hroot_Q / i_kvpc_Q_N_o_next / i_slg_Q_N_o_ctl internal hops have NO rows. These are the work.
- Plan of record is plan_of_record/plan_c.json (NOT qwen_kvsys/die_plan.json, stale). It already has clock.ring_hold {sender_ps -385, sender_ps_types io_cor/io_cor_v1/sys_SD_v1 -50}. hub_C already has 19 hard cores (15 rings + pvfin pair); hub_C 210,883 generic cells shell (synth/hc), hub_Eo 227,520 (synth/eo): no split/ring rows needed.
- hub_Wi / sys_c: deliberate holds posted (D26 hub_Wi pilot by KV-PLAN-R4; sys_c relaunch on D27c after r4d bind).
- My live units: none. Waiters: none needed (hroot job ended).

## COORD order 04:3x (do it, private, in parallel with D28 rows)
1. Private plan delta on the D27c base (epyc8 kv-plan-r3/d27c/tree, read-only; copy to my lane tree, tools = main with the BIND-GEN-TOOLSKEW check; bind and gen on the SAME rt): (a) station / relay_depth rows ceil(len/300)-1, every hop <= 405 um, on i_kvs_ctl_o_hroot_Q, i_kvpc_Q_N_o_next, i_slg_Q_N_o_ctl hops (hop geometry: epyc8 /srv/opentallas-scratch2/claude/fable-visual-0030/out/kv_hroot/geom.tsv + mirror 4_cts.odb; templates: rows/r13_pv_relay_depth.py, r2_fwd300.py, d27lib.py in d27c/rows); (b) drop the 12 sparse west taps (TAP-GRID-R2 form); (c) clock.ring_hold.sender_ps_types.kv3_hroot (measured min over drivers; -50 placeholder, +20 ps margin, FABLE-HARD-KV recipe).
2. Private strict bind + LATCHECK + G0 (epyc7/8/10, NOT epyc9; ot-run, --priority plan only for bind*/g0*/latcheck* script names).
3. hroot kit to route (run_kit.sh GOAL=route, --priority plan), ot-wait + run_in_background waiter, read post-hook GRT TT (4_cts_post_hook.rpt / tt_setup_measure_grt.log); sign-off gate TT >= -42, DRC 0, FF hold >= 0 (port-in only = LOCAL_PASS_NEEDS_PARENT), LEC.
4. Same rows to KV-PLAN-R4 for D28 (post, cc COORD). Carry the proven fix to hub_Ei/Wo/Eo, sys_c.
## Rules reminders: no git in owner checkouts (lane clone via ot-lane-clone: mine is epyc8 /srv/opentallas-scratch2/claude/fam-kv-hub/wt, tools cone only, branch claude/kv-hubc-split-1117 stale), ot-delete only, post via bin/post.sh FAM-KV-HUB-R2.
