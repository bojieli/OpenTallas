# S81-OPEN-DEMAND handoff (Opus 5.5; from 11-23 19:11 PST). FAMILY lane under S81-ALLFIX-INT. Brief: localhost scratchpad s81_open_brief.txt (+ allfix_brief, rules, resume_1123b).
Rows: hg-S81-GLOBAL-DEMAND, hg-S81-LOGIC-DEPTH (+DEPTH PRE), hg-S81-REPAIR-CAP, rc37, rc67. Deadline 22:00 -> c8.
Work dir E9 /srv/opentallas-scratch2/claude/s81-open-demand (wt = main lane clone 3e1a2180cc; an*.py/json analysis; ld/ = LD-LAND5 row; depth.json).
## Posted
- 19:3x IN-BASE hg-S81-GLOBAL-DEMAND (SSTRIP: sites y<25 134->0 / 4->0, payload core y 43.2->69.12 at hot x 570; XGARRAY-2 u_xr x 388.8->440.64). Asked INT: cl774 pvea45273b in c8 probe set.
- 19:3x IN-BASE rc37 (F2 li3 D2, RS1, RIP3/ROS3, R1, trial4 taps clk_t55/56 all in B1; LP-PROFILE-1b c6). Residual = LD-LAND5.
- 19:4x IN-BASE hg-S81-REPAIR-CAP (base + c6 RHI tap_reset_split/macro_follow on all 8 types, PT1 on mu_LP t2; FLOW-OPS measured reason, FABLE 14/16 ACCEPT).
## In progress
- LD-LAND5 ops ld/ops_ld_land5.json efc89aac2d22: mu_LP t2 relay_depth[0] u_land rst_n D 4->5. B1+row plan ld/out/01_ld_land5.json 396fa520d75a; PRE (amd1_tree tools 70b6, asbuilt_allfix) ld/pre_ld.log.
- DEPTH PRE (main e8e1621 logic_depth via plan_gate_pre.check_depth): S81 B1/c6 with asbuilt_allfix reach 0 generated netlists (469 modules; 69/71 hard-core modules indexed, ot_v41_bf16_half/bf_col3_c not). Plan-only mode (no --asbuilt) FAILs on 10 qwen_* generated netlists S81 never uses = false FAIL class.
- rc67: worker fork running (adv_hop_gap on B1 vs c6 with B1 bind OUT); posts as S81-OPEN-DEMAND "rc67 ...".
## 20:5x
- LD-LAND5 ROW-REBASED posted (PRE FAIL set identical to B1: 12 p5 ANCHORDRY + DEADIN). Scoped strict blocked: ELAB fails dsdv_svc_land_mem unknown (hi4:668), with and without OT_BIND_TYPE_DEFINES; ALERT + CORRECTION posted to INT.
- rc67 ROW-REBASED by worker: RC67-HOPSITE-1 ops cf14e170d0df (E9 rc67/), PRE 0, scoped strict rc0 (epyc10). Leaf c6 regression handed to SLICE. Temp file intel2 ~/coord/tmp/s81-open-demand-rc67-post.txt -> ot-delete.
- REPORT to COORD posted. Next: re-run LD scoped strict once INT fixes ELAB; c8 probe read on mu_LP t2 / cl774 pvea45273b.
