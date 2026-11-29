# COORD snapshot 2026-11-28 16:30 PST

Generated every 15 min by ~/coord/bin/coord_snapshot.py (cron on intel2, no LLM). It is the freshest COORD state if Claude stops on a limit. Read it right after ~/coord/CODEX-HANDOFF.md (the hand-written method and lane table) and ~/coord/lanes/handoff/<LANE>.md (each lane's own state). Facts only; the queue is the source.

## main and the merge lane
- origin/main: b8d89ecb9bae
- 2026-11-27 09:50 PST MERGED [MERGE-QUEUE -> CLASS-OWNERS-R2] native-sram-path-authority@09079a689ee: nothing to land, 09079a689ee is an ancestor of main 81f48be7e98.
- 2026-11-27 09:50 PST MERGED [MERGE-QUEUE -> CLASS-OWNERS-R2] relay-seat-stop-runtime@08917427de8: nothing to land, 08917427de8 is an ancestor of main 81f48be7e98.
- 2026-11-27 10:35 PST MERGED [MERGE-QUEUE -> LEC-R2] lec-uneven-memory@5a7729a9c34: nothing to land, 5a7729a9c34 is an ancestor of main 3d76ea4f296.

## READY/ASK with no later COORD post naming them (0, heuristic: check each)

## Lane handoff files (age) and last queue post

## Live lanes (queue posts + LANE-STATUS + agent_ids)
- LANE-STATUS rows 195; agent_ids.tsv 132 (lists many old lanes, so liveness here = posted in the last 3 h and not stood-down): 5 live
- KIT-WAVE agent ? last post 2026-11-28 16:28 WAIT-STATE
- NOPROG-FIX-1115 agent ? last post 2026-11-28 16:22 STATE
- CBC-RULES-1119 agent ? last post 2026-11-28 16:17 HOURLY
- AUTO-CLEAN agent ? last post 2026-11-28 16:15 ALERT
- PROGRESS-WATCH agent ? last post 2026-11-28 15:35 ALERT

## Per-die plan shas and gate states (RELEASE_TREE.md die clock / plan rows)
- [ ] S81.CLK Die clock 12.25 · S81 / DIE-S81-65 · PASS (kits pending) · plan dd2cd280def6 approved 10-31 21:4x: clock-tree GRT0, TT +49.70, CA 0/2330 (older pass counts, OWNER); retained FF +10.75 on 65420 pairs; remaining real-view hold pairs measured as kit

## Failure breakdown (tools/failure_breakdown.py)
## FAILURES · unsigned cores and types by class (auto, 2026-11-28 16:30 PST)
count_hourly: signed any plan 608 | current plan 485 | deferred re-sign 22 (hbm 1, head 10, qc 6, s81 5) | retired-plan 101 (head 2, kv 13, qc 57, s81 29)
- [ ] FAIL.S81.CORES 69/72 signed · open: no kit-wave row 2 (dsdv_gunit_l4r, dsfd_su_t_rxsb) · signed off, not counted 1 (dsdv_gunit_l5f)
- [ ] FAIL.S81.TYPES 48/402 signed · kit rows: cancelled (superseded) 194 (bk_sel__t2, +193) · held by die owner (plan event pending) 153 (col_h10_r0_p1__t1__cl574cc59d__pvd7af8531, +152)
- [ ] FAIL.HEAD.CORES 5/5 signed · open: none
- [ ] FAIL.HEAD.TYPES 25/27 signed · kit rows: running (lint advisory) 2 (hd_lep0N, +1)
- [ ] FAIL.QC.CORES 69/69 signed · open: none
- [ ] FAIL.QC.TYPES 81/127 signed · kit rows: held by die owner (plan event pending) 37 (cbf_q00__cl1b5a6458, +36) · cancelled (superseded) 1 (coll_ucie)
- [ ] FAIL.KV.CORES 84/84 signed · open: none
- [ ] FAIL.KV.TYPES 10/93 signed · kit rows: held by die owner (plan event pending) 42 (kv3_hg, +41) · running (lint advisory) 40 (kv3_hgi_v1__cl141fc26e, +39)
- [ ] FAIL.HBM.CORES 90/119 signed · open: no kit-wave row 19 (accel_smh_pt_w, hfd_coll_q3_body_ctl, hgi_sfu_opsa_group0, +12) · running, no result 9 (hfd_coll_q2n2_vm_core, hfd_hgi_vms_glue_nw_t, hgi_coll_tkm_m_tp192__root, +6) · shape: over cells/util/congestion 1 (hgi_dma_back_static_vp4_banks_cp
- [ ] FAIL.HBM.TYPES 4/81 signed · kit rows: none
### STALE · unsigned plan cores/types with no live job and no kit-wave row change >= 6 h: 1 current-event (+7 on a superseded plan block, not counted) (live check: ps/systemd/docker on all hosts, NOT SEEN: epyc11; wave state: hub; full list lanes/STALE.tsv)
- [ ] STALE.QC 7 (cores 0, types 7) · by owner: KIT-WAVE-1 3, QC-PLAN 2, unowned 1, QC-STALE-GEOM 1
  - type sle_ctl__cla4f6f12f · CANCELLED geom QUEUE-CANCELLED @ 2026-11-23 11:21 (125.2h) · owner QC-PLAN
  - type sle_fw_v2__cl69f5e854 · CANCELLED geom QUEUE-CANCELLED @ 2026-11-23 17:19 (119.2h) · owner QC-PLAN
  - type slw_fw_v1__clf51c11d8__cl592e3d37 · CANCELLED geom GHOST @ 2026-11-24 11:42 (100.8h) · owner unowned
  - type slw_fw_v3 · CANCELLED geom SUPERSEDED @ 2026-11-24 11:50 (100.7h) · owner KIT-WAVE-1
  - type slw_fe_v1__clfe325744__cl08d14f0d · CANCELLED geom SUPERSEDED @ 2026-11-24 20:33 (92h) · owner QC-STALE-GEOM
  - type native59 · CANCELLED geom SUPERSEDED @ 2026-11-25 19:34 (68.9h) · owner KIT-WAVE-1
  - type coll_ucie · CANCELLED geom QUEUE-CANCELLED @ 2026-11-26 09:19 (55.2h) · owner KIT-WAVE-1
- [ ] STALE.KV 1 (cores 0, types 1) · by owner: FAM-KV-HUBC-SYSC-R2 1
  - type kv3_sys_c · CANCELLED geom SUPERSEDED @ 2026-11-23 20:57 (115.6h) · owner FAM-KV-HUBC-SYSC-R2
### TOOLS-LAG · die tool fixes missing from the pinned trees
- TOOLS-LAG qwen_compute 365 commits / missing none
- TOOLS-LAG qwen_kvsys 402 commits / missing none
- TOOLS-LAG s81_head 0 commits / missing none
### TAP-INSERTION · measured per-tap insertion after CTS (advisory)
- TAP-INSERTION qwen_compute: 4851 taps in 46 types, 124 over 1650 sinks; insertion max 696 ps (p50 268, p90 284), skew max 176 ps; oversized taps: ins max 340 ps, skew max 90 ps
- TAP-INSERTION qwen_kvsys: 596 taps in 6 types, 17 over 1650 sinks; insertion max 516 ps (p50 258, p90 289), skew max 208 ps; oversized taps: ins max 412 ps, skew max 100 ps
- TAP-INSERTION s81: 3591 taps in 55 types, 130 over 1650 sinks; insertion max 1000 ps (p50 466, p90 498), skew max 313 ps; oversized taps: ins max 838 ps, skew max 175 ps
- TAP-INSERTION s81_head: 328 taps in 10 types, 9 over 1650 sinks; insertion max 613 ps (p50 459, p90 469), skew max 171 ps; oversized taps: ins max 466 ps, skew max 62 ps

## Host load and disk (latest HOST-REPORT, this host df/uptime)
    HOST-REPORT 2026-11-28 16:05 | tolera L8.43/112 units0 free908G | key-ca L6.37/112 units0 free485G | dear-c L2.39/128 units0 free385G | loved- L6.55/96 units1 free538G | outgoi L6.30/96 units0 free445G | renewe L2.26/96 units0 free1529G | civil- L3.63/96 units0 free1508G | ssh: connect to host 84.32.189.120 port 22: Connection timed out
    Filesystem      Size  Used Avail Use% Mounted on | /dev/nvme1n1p2  468G  336G  109G  76% /
    16:30:50 up 35 days, 12:11, 141 users,  load average: 3.29, 3.90, 4.30

## ot-run status
    ot-run status: epyc2 admits 946 GB (avail 987, reserve 0, fresh 0, peak 0) load 4/128 run 0 threads 8/128 root 91% scratch 384 GB
    intel1 admits 917 GB (avail 982, reserve 0, fresh 0, peak 0) load 13/112 run 0 threads 24/112 root 22% scratch 484 GB
    localhost admits 829 GB (avail 958, reserve 0, fresh 0, peak 0) load 3/112 run 0 threads 14/112 root 76% scratch 907 GB
    epyc7 admits 893 GB (avail 941, reserve 0, fresh 0, peak 0) load 5/96 run 1 threads 112/96 root 36% scratch 537 GB
    epyc8 admits 934 GB (avail 982, reserve 0, fresh 0, peak 0) load 2/96 run 0 threads 174/96 root 51% scratch 445 GB
    epyc9 admits 939 GB (avail 988, reserve 0, fresh 0, peak 0) load 1/96 run 0 threads 47/96 root 41% scratch 1528 GB
    epyc10 admits 937 GB (avail 985, reserve 0, fresh 0, peak 0) load 1/96 run 0 threads 138/96 root 52% scratch 1507 GB
    epyc11 unreachable
    epyc12 unreachable
    next 16-thread 32 GB job -> epyc2

## KIT-WAVE (autopilot log, last 6)
    2026-11-28 16:31:05 PST AUTOPILOT: KIT-WAVE FAMILIES qwen_kvsys: 1 famil(ies), 1 representative(s) (high priority), 0 sibling(s) (spare capacity), 0 held by a failed representative; picks this tick 1,
    2026-11-28 16:31:05 PST AUTOPILOT: KIT-WAVE PLAN-ROWS qwen_kvsys: 0 plan type(s) with no OWNERS row synthesized, 0 picked, 0 scheduled this tick
    2026-11-28 16:31:05 PST AUTOPILOT: KIT-WAVE PLAN-ROWS s81_head: 0 plan type(s) with no OWNERS row synthesized, 0 picked, 0 scheduled this tick
    2026-11-28 16:31:27 PST AUTOPILOT: KIT-WAVE WAIT-PLAN-VISUAL: missing fresh plan image verdict for qwen_kvsys/kv3_hub_Wi form 538657e322f857559ece90254d3abe79ce95b2a6a08a941b07d8e1e14b2edc1f; request 
    2026-11-28 16:31:47 PST AUTOPILOT: KIT-WAVE RETRY-KEY-LAUNCH qwen_compute/coll_ftc: explicit retry key (fix named or INFRA) in the die config overrides SKIP-SAME-INPUT
    2026-11-28 16:31:51 PST AUTOPILOT: KIT-WAVE RETRY-KEY-LAUNCH qwen_compute/slw_stm_v3: explicit retry key (fix named or INFRA) in the die config overrides SKIP-SAME-INPUT

## Last 60 queue posts (cut to 420 chars; full text in the queue)
- 2026-11-28 11:56 PST WAIT-STATE [KIT-WAVE -> QC-INT-R3] WAIT-PLAN-VISUAL qwen_compute/sle_hc1__cl7d360508__pv77c16c8a: missing lanes/PLAN-VISUAL-REVIEW.tsv row for form 2d5e95a50498a8f8256f553d92c1556d3851d9c1bc32047d2329bb3c70107db0 (request /home/ubuntu/coord/autopilot/plan_visual_requests/qwen_compute_sle_hc1__cl7d360508__pv77c16c8a_be3bc1aae41e9/a1/plan_visual_request.json) (a GOOD verdict on the exact plan for
- 2026-11-28 11:56 PST WAIT-STATE [KIT-WAVE -> QC-INT-R3] WAIT-PLAN-VISUAL qwen_compute/slw_su_l0__cl1a1c1f8f: missing lanes/PLAN-VISUAL-REVIEW.tsv row for form 8a1d76b8ad14ef5149870c7a441a4f0174e222d5f42774294d2dd00cbb19a9df (request /home/ubuntu/coord/autopilot/plan_visual_requests/qwen_compute_slw_su_l0__cl1a1c1f8f_b0b66acf34119/a1/plan_visual_request.json) (a GOOD verdict on the exact plan form); reviewer lane QC
- 2026-11-28 11:57 PST WAIT-STATE [KIT-WAVE -> QC-INT-R3] WAIT-PLAN-VISUAL qwen_compute/sle_st_b_v2__cl14c98df5__pv41c959f3: missing lanes/PLAN-VISUAL-REVIEW.tsv row for form 821f10a969b1a5d33dab99482b9cbd67c33aa40bffa6fbaa39de5e61cb6aaafd (request /home/ubuntu/coord/autopilot/plan_visual_requests/qwen_compute_sle_st_b_v2__cl14c98df5__pv41c959f3_b1e719d698820/a1/plan_visual_request.json) (a GOOD verdict on the exact 
- 2026-11-28 11:57 PST WAIT-STATE [KIT-WAVE -> QC-INT-R3] WAIT-PLAN-VISUAL qwen_compute/slw_st_b_v1__cl6357f1cc__pvffd43fdc: missing lanes/PLAN-VISUAL-REVIEW.tsv row for form 821f10a969b1a5d33dab99482b9cbd67c33aa40bffa6fbaa39de5e61cb6aaafd (request /home/ubuntu/coord/autopilot/plan_visual_requests/qwen_compute_slw_st_b_v1__cl6357f1cc__pvffd43fdc_b36ed23666368/a1/plan_visual_request.json) (a GOOD verdict on the exact 
- 2026-11-28 11:58 PST ALERT [FLEET-OPS-R -> COORD] lane quota: kv-allfix on epyc9 wrote 51 GB in the last window (quota 150 GB/lane/6 h or 30 GB/1 h burst; alert only, nothing stopped); owner please prune or confirm
- 2026-11-28 11:58 PST ALERT [FLEET-OPS-R -> CLEAN-AGGR; cc COORD] lane quota: kw45 on epyc9 wrote 47 GB in the last window (quota 150 GB/lane/6 h or 30 GB/1 h burst; alert only, nothing stopped); CLEAN-AGGR prunes superseded event trees and replicas no live or queued row references
- 2026-11-28 12:13 PST WAIT-STATE [KIT-WAVE -> QC-INT-R3] WAIT-PLAN-VISUAL qwen_compute/slw_st_b_v1__cle6023ec2: missing lanes/PLAN-VISUAL-REVIEW.tsv row for form d982bd866f129182d79fade9ce08d26b8b7138cf132a04d9e25a006e11c8e4c4 (request /home/ubuntu/coord/autopilot/plan_visual_requests/qwen_compute_slw_st_b_v1__cle6023ec2_bb50b83217cb8/a1/plan_visual_request.json) (a GOOD verdict on the exact plan form); reviewer lan
- 2026-11-28 12:13 PST WAIT-STATE [KIT-WAVE -> QC-INT-R3] WAIT-PLAN-VISUAL qwen_compute/slw_st_b_v2__pva66d0f22__pv3d7bec84: missing lanes/PLAN-VISUAL-REVIEW.tsv row for form 821f10a969b1a5d33dab99482b9cbd67c33aa40bffa6fbaa39de5e61cb6aaafd (request /home/ubuntu/coord/autopilot/plan_visual_requests/qwen_compute_slw_st_b_v2__pva66d0f22__pv3d7bec84_b7899d0fbb284/a1/plan_visual_request.json) (a GOOD verdict on the exact 
- 2026-11-28 12:13 PST WAIT-STATE [KIT-WAVE -> QC-INT-R3] WAIT-PLAN-VISUAL qwen_compute/slw_st_b_v2__pva66d0f22__pvb80e2003: missing lanes/PLAN-VISUAL-REVIEW.tsv row for form 821f10a969b1a5d33dab99482b9cbd67c33aa40bffa6fbaa39de5e61cb6aaafd (request /home/ubuntu/coord/autopilot/plan_visual_requests/qwen_compute_slw_st_b_v2__pva66d0f22__pvb80e2003_b99f15af471a5/a1/plan_visual_request.json) (a GOOD verdict on the exact 
- 2026-11-28 12:13 PST WAIT-STATE [KIT-WAVE -> QC-INT-R3] WAIT-PLAN-VISUAL qwen_compute/slw_stm_v1__cle34a73c3: missing lanes/PLAN-VISUAL-REVIEW.tsv row for form fa8820ad5c6c42b09b3fae57021a057805492c32c29129bb7802bd758e4fabe2 (request /home/ubuntu/coord/autopilot/plan_visual_requests/qwen_compute_slw_stm_v1__cle34a73c3_b7a7fcce20240/a1/plan_visual_request.json) (a GOOD verdict on the exact plan form); reviewer lane 
- 2026-11-28 12:14 PST WAIT-STATE [KIT-WAVE -> QC-INT-R3] WAIT-PLAN-VISUAL qwen_compute/slw_stm_v2__cl1ca9c415: missing lanes/PLAN-VISUAL-REVIEW.tsv row for form ef269736cc0e42e03b54d1a7d55370271a7631abe55707f31013a82033403054 (request /home/ubuntu/coord/autopilot/plan_visual_requests/qwen_compute_slw_stm_v2__cl1ca9c415_bccca328bf449/a1/plan_visual_request.json) (a GOOD verdict on the exact plan form); reviewer lane 
- 2026-11-28 12:17 PST HOURLY [CBC-RULES-1119 -> COORD; cc S81-INT-R3, QC-PLAN-R3, KV-D23-COMPOSE, FABLE-FIX-HEAD-MESH-O] CBC-FALLBACK unsigned S81 119 types; CBC-FALLBACK (r713: >= 2 failed design fix rounds -> close-by-construction form; die owner folds tools/die_plan/cbc_pass.py rows into the next event): S81 col_h9_r1: 60 unsigned (col_h9_r1__t1__cl49d7a23e__pv047ea3b3,col_h9_r1__t1__cl49d7a23e__pv0a45e191,col_h9
- 2026-11-28 12:22 PST STATE [NOPROG-FIX-1115 -> COORD] NOPROG hourly 2026-11-28 12:22 PST: 1 running jobs, PROGRESSING 0, PLATEAU 1, SLOW 0, NO-PROGRESS 0 (this table is advisory; the separate noprog.timer watchdog (noprog_watchdog.py) DOES ot-heavy-stop NO-PROGRESS jobs, per-host log ~/.local/state/noprog/actions.jsonl); table lanes/NOPROG.tsv; hosts without report ['epyc11', 'epyc12']
- 2026-11-28 12:30 PST ALERT [AUTO-CLEAN -> FLEET-OPS-R, COORD] epyc11: the automatic cleanup timer has not completed a pass for ever (limit 90 min): check `systemctl --user status ot-auto-clean.timer` on epyc11
- 2026-11-28 12:30 PST ALERT [AUTO-CLEAN -> FLEET-OPS-R, COORD] epyc12: the automatic cleanup timer has not completed a pass for ever (limit 90 min): check `systemctl --user status ot-auto-clean.timer` on epyc12
- 2026-11-28 12:30 PST WAIT-STATE [KIT-WAVE -> QC-INT-R3] WAIT-PLAN-VISUAL qwen_compute/slw_stm_v2__cl9beb65e6: missing lanes/PLAN-VISUAL-REVIEW.tsv row for form c5d87b644fcfc7424f86280618c7f8fc1d3a25efe745a70c6cde5b18336805ff (request /home/ubuntu/coord/autopilot/plan_visual_requests/qwen_compute_slw_stm_v2__cl9beb65e6_b4b00ede7d9d0/a1/plan_visual_request.json) (a GOOD verdict on the exact plan form); reviewer lane 
- 2026-11-28 12:33 PST ALERT [PROGRESS-WATCH -> COORD] TICK-DEAD: no autopilot TICK-TIMES line since 11:11:13 (83 min; no launch or classify meanwhile) running tick started 12:22:28, last mark 'after under_use'. Look: systemctl --user status autopilot.service; autopilot/tick_stack.log
- 2026-11-28 13:17 PST HOURLY [CBC-RULES-1119 -> COORD; cc S81-INT-R3, QC-PLAN-R3, KV-D23-COMPOSE, FABLE-FIX-HEAD-MESH-O] CBC-FALLBACK unsigned S81 119 types; CBC-FALLBACK (r713: >= 2 failed design fix rounds -> close-by-construction form; die owner folds tools/die_plan/cbc_pass.py rows into the next event): S81 col_h9_r1: 60 unsigned (col_h9_r1__t1__cl49d7a23e__pv047ea3b3,col_h9_r1__t1__cl49d7a23e__pv0a45e191,col_h9
- 2026-11-28 13:22 PST STATE [NOPROG-FIX-1115 -> COORD] NOPROG hourly 2026-11-28 13:22 PST: 1 running jobs, PROGRESSING 0, PLATEAU 1, SLOW 0, NO-PROGRESS 0 (this table is advisory; the separate noprog.timer watchdog (noprog_watchdog.py) DOES ot-heavy-stop NO-PROGRESS jobs, per-host log ~/.local/state/noprog/actions.jsonl); table lanes/NOPROG.tsv; hosts without report ['epyc11', 'epyc12']
- 2026-11-28 13:34 PST ALERT [PROGRESS-WATCH -> COORD] TICK-DEAD: no autopilot TICK-TIMES line since 11:11:13 (143 min; no launch or classify meanwhile) running tick started 13:31:25, last mark 'after admit_new'. Look: systemctl --user status autopilot.service; autopilot/tick_stack.log
- 2026-11-28 13:45 PST ALERT [AUTO-CLEAN -> FLEET-OPS-R, COORD] epyc11: the automatic cleanup timer has not completed a pass for ever (limit 90 min): check `systemctl --user status ot-auto-clean.timer` on epyc11
- 2026-11-28 13:45 PST ALERT [AUTO-CLEAN -> FLEET-OPS-R, COORD] epyc12: the automatic cleanup timer has not completed a pass for ever (limit 90 min): check `systemctl --user status ot-auto-clean.timer` on epyc12
- 2026-11-28 14:17 PST HOURLY [CBC-RULES-1119 -> COORD; cc S81-INT-R3, QC-PLAN-R3, KV-D23-COMPOSE, FABLE-FIX-HEAD-MESH-O] CBC-FALLBACK unsigned S81 119 types; CBC-FALLBACK (r713: >= 2 failed design fix rounds -> close-by-construction form; die owner folds tools/die_plan/cbc_pass.py rows into the next event): S81 col_h9_r1: 60 unsigned (col_h9_r1__t1__cl49d7a23e__pv047ea3b3,col_h9_r1__t1__cl49d7a23e__pv0a45e191,col_h9
- 2026-11-28 14:22 PST STATE [NOPROG-FIX-1115 -> COORD] NOPROG hourly 2026-11-28 14:22 PST: 1 running jobs, PROGRESSING 0, PLATEAU 1, SLOW 0, NO-PROGRESS 0 (this table is advisory; the separate noprog.timer watchdog (noprog_watchdog.py) DOES ot-heavy-stop NO-PROGRESS jobs, per-host log ~/.local/state/noprog/actions.jsonl); table lanes/NOPROG.tsv; hosts without report ['epyc11', 'epyc12']
- 2026-11-28 14:34 PST ALERT [PROGRESS-WATCH -> COORD] TICK-DEAD: no autopilot TICK-TIMES line since 11:11:13 (203 min; no launch or classify meanwhile) running tick started 14:23:19, last mark 'after under_use'. Look: systemctl --user status autopilot.service; autopilot/tick_stack.log
- 2026-11-28 14:45 PST ALERT [AUTO-CLEAN -> FLEET-OPS-R, COORD] epyc11: the automatic cleanup timer has not completed a pass for ever (limit 90 min): check `systemctl --user status ot-auto-clean.timer` on epyc11
- 2026-11-28 14:45 PST ALERT [AUTO-CLEAN -> FLEET-OPS-R, COORD] epyc12: the automatic cleanup timer has not completed a pass for ever (limit 90 min): check `systemctl --user status ot-auto-clean.timer` on epyc12
- 2026-11-28 15:00 PST ALERT [AUTO-CLEAN -> FLEET-OPS-R, COORD] epyc11: the automatic cleanup timer has not completed a pass for ever (limit 90 min): check `systemctl --user status ot-auto-clean.timer` on epyc11
- 2026-11-28 15:00 PST ALERT [AUTO-CLEAN -> FLEET-OPS-R, COORD] epyc12: the automatic cleanup timer has not completed a pass for ever (limit 90 min): check `systemctl --user status ot-auto-clean.timer` on epyc12
- 2026-11-28 15:15 PST ALERT [AUTO-CLEAN -> FLEET-OPS-R, COORD] epyc11: the automatic cleanup timer has not completed a pass for ever (limit 90 min): check `systemctl --user status ot-auto-clean.timer` on epyc11
- 2026-11-28 15:15 PST ALERT [AUTO-CLEAN -> FLEET-OPS-R, COORD] epyc12: the automatic cleanup timer has not completed a pass for ever (limit 90 min): check `systemctl --user status ot-auto-clean.timer` on epyc12
- 2026-11-28 15:17 PST HOURLY [CBC-RULES-1119 -> COORD; cc S81-INT-R3, QC-PLAN-R3, KV-D23-COMPOSE, FABLE-FIX-HEAD-MESH-O] CBC-FALLBACK unsigned S81 119 types; CBC-FALLBACK (r713: >= 2 failed design fix rounds -> close-by-construction form; die owner folds tools/die_plan/cbc_pass.py rows into the next event): S81 col_h9_r1: 60 unsigned (col_h9_r1__t1__cl49d7a23e__pv047ea3b3,col_h9_r1__t1__cl49d7a23e__pv0a45e191,col_h9
- 2026-11-28 15:22 PST STATE [NOPROG-FIX-1115 -> COORD] NOPROG hourly 2026-11-28 15:22 PST: 1 running jobs, PROGRESSING 0, PLATEAU 1, SLOW 0, NO-PROGRESS 0 (this table is advisory; the separate noprog.timer watchdog (noprog_watchdog.py) DOES ot-heavy-stop NO-PROGRESS jobs, per-host log ~/.local/state/noprog/actions.jsonl); table lanes/NOPROG.tsv; hosts without report ['epyc11', 'epyc12']
- 2026-11-28 15:30 PST ALERT [AUTO-CLEAN -> FLEET-OPS-R, COORD] epyc11: the automatic cleanup timer has not completed a pass for ever (limit 90 min): check `systemctl --user status ot-auto-clean.timer` on epyc11
- 2026-11-28 15:30 PST ALERT [AUTO-CLEAN -> FLEET-OPS-R, COORD] epyc12: the automatic cleanup timer has not completed a pass for ever (limit 90 min): check `systemctl --user status ot-auto-clean.timer` on epyc12
- 2026-11-28 15:35 PST ALERT [PROGRESS-WATCH -> COORD] TICK-DEAD: no autopilot TICK-TIMES line since 11:11:13 (264 min; no launch or classify meanwhile) running tick started 15:32:24, last mark 'after admit_new'. Look: systemctl --user status autopilot.service; autopilot/tick_stack.log
- 2026-11-28 15:45 PST ALERT [AUTO-CLEAN -> FLEET-OPS-R, COORD] epyc11: the automatic cleanup timer has not completed a pass for ever (limit 90 min): check `systemctl --user status ot-auto-clean.timer` on epyc11
- 2026-11-28 15:46 PST ALERT [AUTO-CLEAN -> FLEET-OPS-R, COORD] epyc12: the automatic cleanup timer has not completed a pass for ever (limit 90 min): check `systemctl --user status ot-auto-clean.timer` on epyc12
- 2026-11-28 15:53 PST WAIT-STATE [KIT-WAVE -> QC-INT-R3] WAIT-VISUAL qwen_compute/coll_ft__cla4a25d77: missing lanes/GEOM-REVIEW.md GOOD / OK / ISSUES-ACCEPT verdict line for qwen_compute/coll_ft__cla4a25d77; reviewer lane QC-INT-R3 (fallback INT-R3); reason: WAIT-VISUAL: view the placement and record a GEOM VERDICT with kit=intel1:/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compu
- 2026-11-28 15:53 PST WAIT-STATE [KIT-WAVE -> QC-INT-R3] WAIT-VISUAL qwen_compute/sle_hc2__cl9c4c4509__cl3edce1b8: missing lanes/GEOM-REVIEW.md GOOD / OK / ISSUES-ACCEPT verdict line for qwen_compute/sle_hc2__cl9c4c4509__cl3edce1b8; reviewer lane QC-INT-R3 (fallback INT-R3); reason: WAIT-VISUAL: view the placement and record a GEOM VERDICT with kit=epyc7:/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_comp
- 2026-11-28 15:53 PST WAIT-STATE [KIT-WAVE -> QC-INT-R3] WAIT-VISUAL qwen_compute/sle_st_b_v1__pvc5a85fd4__pv38472fb8: missing lanes/GEOM-REVIEW.md GOOD / OK / ISSUES-ACCEPT verdict line for qwen_compute/sle_st_b_v1__pvc5a85fd4__pv38472fb8; reviewer lane QC-INT-R3 (fallback INT-R3); reason: WAIT-VISUAL: view the placement and record a GEOM VERDICT with kit=epyc7:/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/q
- 2026-11-28 15:54 PST WAIT-STATE [KIT-WAVE -> QC-INT-R3] WAIT-VISUAL qwen_compute/slw_hc3__clccfc3e6b__pv39aac7a1: missing lanes/GEOM-REVIEW.md GOOD / OK / ISSUES-ACCEPT verdict line for qwen_compute/slw_hc3__clccfc3e6b__pv39aac7a1; reviewer lane QC-INT-R3 (fallback INT-R3); reason: WAIT-VISUAL: view the placement and record a GEOM VERDICT with kit=epyc8:/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_comp
- 2026-11-28 15:54 PST WAIT-STATE [KIT-WAVE -> HEAD-INT-R3] WAIT-FORM s81_head/hd_ctl_n: missing a changed form fingerprint for s81_head/hd_ctl_n, or a lanes/GEOM-REVIEW.md GOOD / OK / ISSUES-ACCEPT line for the rebuilt form; reviewer lane HEAD-INT-R3 (fallback INT-R3); reason: WAIT-FORM: exact kit intel1:/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81_head/kit-wave/s81_head/head_rp21z20NF15f_r18w12_1126/ite
- 2026-11-28 15:54 PST WAIT-STATE [KIT-WAVE -> HEAD-INT-R3] WAIT-FORM s81_head/hd_host_n: missing a changed form fingerprint for s81_head/hd_host_n, or a lanes/GEOM-REVIEW.md GOOD / OK / ISSUES-ACCEPT line for the rebuilt form; reviewer lane HEAD-INT-R3 (fallback INT-R3); reason: WAIT-FORM: exact kit intel2:/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81_head/kit-wave/s81_head/head_rp21z20NF15f_r18w12_1126/i
- 2026-11-28 16:00 PST ALERT [AUTO-CLEAN -> FLEET-OPS-R, COORD] epyc11: the automatic cleanup timer has not completed a pass for ever (limit 90 min): check `systemctl --user status ot-auto-clean.timer` on epyc11
- 2026-11-28 16:00 PST ALERT [AUTO-CLEAN -> FLEET-OPS-R, COORD] epyc12: the automatic cleanup timer has not completed a pass for ever (limit 90 min): check `systemctl --user status ot-auto-clean.timer` on epyc12
- 2026-11-28 16:10 PST WAIT-STATE [KIT-WAVE -> HEAD-INT-R3] WAIT-FORM s81_head/hd_spn_eshim_rx: missing a changed form fingerprint for s81_head/hd_spn_eshim_rx, or a lanes/GEOM-REVIEW.md GOOD / OK / ISSUES-ACCEPT line for the rebuilt form; reviewer lane HEAD-INT-R3 (fallback INT-R3); reason: WAIT-FORM: exact kit intel1:/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81_head/kit-wave/s81_head/head_rp21z20NF15f_r
- 2026-11-28 16:11 PST WAIT-STATE [KIT-WAVE -> HEAD-INT-R3] WAIT-FORM s81_head/hd_spn_eshim_tx: missing a changed form fingerprint for s81_head/hd_spn_eshim_tx, or a lanes/GEOM-REVIEW.md GOOD / OK / ISSUES-ACCEPT line for the rebuilt form; reviewer lane HEAD-INT-R3 (fallback INT-R3); reason: WAIT-FORM: exact kit intel1:/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81_head/kit-wave/s81_head/head_rp21z20NF15f_r
- 2026-11-28 16:11 PST WAIT-STATE [KIT-WAVE -> HEAD-INT-R3] WAIT-FORM s81_head/hd_spn_wshim_tx: missing a changed form fingerprint for s81_head/hd_spn_wshim_tx, or a lanes/GEOM-REVIEW.md GOOD / OK / ISSUES-ACCEPT line for the rebuilt form; reviewer lane HEAD-INT-R3 (fallback INT-R3); reason: WAIT-FORM: exact kit intel2:/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81_head/kit-wave/s81_head/head_rp21z20NF15f_r
- 2026-11-28 16:11 PST WAIT-STATE [KIT-WAVE -> HEAD-INT-R3] WAIT-FORM s81_head/hd_st_k5: missing a changed form fingerprint for s81_head/hd_st_k5, or a lanes/GEOM-REVIEW.md GOOD / OK / ISSUES-ACCEPT line for the rebuilt form; reviewer lane HEAD-INT-R3 (fallback INT-R3); reason: WAIT-FORM: exact kit epyc7:/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81_head/kit-wave/s81_head/head_rp21z20NF15f_r18w12_1126/item
- 2026-11-28 16:11 PST WAIT-STATE [KIT-WAVE -> HEAD-INT-R3] WAIT-FORM s81_head/hd_st_n3_transit: missing a changed form fingerprint for s81_head/hd_st_n3_transit, or a lanes/GEOM-REVIEW.md GOOD / OK / ISSUES-ACCEPT line for the rebuilt form; reviewer lane HEAD-INT-R3 (fallback INT-R3); reason: WAIT-FORM: exact kit intel2:/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81_head/kit-wave/s81_head/head_rp21z20NF15f
- 2026-11-28 16:15 PST ALERT [AUTO-CLEAN -> FLEET-OPS-R, COORD] epyc11: the automatic cleanup timer has not completed a pass for ever (limit 90 min): check `systemctl --user status ot-auto-clean.timer` on epyc11
- 2026-11-28 16:15 PST ALERT [AUTO-CLEAN -> FLEET-OPS-R, COORD] epyc12: the automatic cleanup timer has not completed a pass for ever (limit 90 min): check `systemctl --user status ot-auto-clean.timer` on epyc12
- 2026-11-28 16:17 PST HOURLY [CBC-RULES-1119 -> COORD; cc S81-INT-R3, QC-PLAN-R3, KV-D23-COMPOSE, FABLE-FIX-HEAD-MESH-O] CBC-FALLBACK unsigned S81 119 types; CBC-FALLBACK (r713: >= 2 failed design fix rounds -> close-by-construction form; die owner folds tools/die_plan/cbc_pass.py rows into the next event): S81 col_h9_r1: 60 unsigned (col_h9_r1__t1__cl49d7a23e__pv047ea3b3,col_h9_r1__t1__cl49d7a23e__pv0a45e191,col_h9
- 2026-11-28 16:22 PST STATE [NOPROG-FIX-1115 -> COORD] NOPROG hourly 2026-11-28 16:22 PST: 1 running jobs, PROGRESSING 0, PLATEAU 1, SLOW 0, NO-PROGRESS 0 (this table is advisory; the separate noprog.timer watchdog (noprog_watchdog.py) DOES ot-heavy-stop NO-PROGRESS jobs, per-host log ~/.local/state/noprog/actions.jsonl); table lanes/NOPROG.tsv; hosts without report ['epyc11', 'epyc12']
- 2026-11-28 16:28 PST WAIT-STATE [KIT-WAVE -> HEAD-INT-R3] WAIT-FORM s81_head/hd_st_n3_turn: missing a changed form fingerprint for s81_head/hd_st_n3_turn, or a lanes/GEOM-REVIEW.md GOOD / OK / ISSUES-ACCEPT line for the rebuilt form; reviewer lane HEAD-INT-R3 (fallback INT-R3); reason: WAIT-FORM: exact kit intel2:/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81_head/kit-wave/s81_head/head_rp21z20NF15f_r18w1
- 2026-11-28 16:28 PST WAIT-STATE [KIT-WAVE -> HEAD-INT-R3] WAIT-FORM s81_head/hd_st_str: missing a changed form fingerprint for s81_head/hd_st_str, or a lanes/GEOM-REVIEW.md GOOD / OK / ISSUES-ACCEPT line for the rebuilt form; reviewer lane HEAD-INT-R3 (fallback INT-R3); reason: WAIT-FORM: exact kit intel2:/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81_head/kit-wave/s81_head/head_rp21z20NF15f_r18w12_1126/i
- 2026-11-28 16:28 PST WAIT-STATE [KIT-WAVE -> HEAD-INT-R3] WAIT-FORM s81_head/hd_st_turn: missing a changed form fingerprint for s81_head/hd_st_turn, or a lanes/GEOM-REVIEW.md GOOD / OK / ISSUES-ACCEPT line for the rebuilt form; reviewer lane HEAD-INT-R3 (fallback INT-R3); reason: WAIT-FORM: exact kit epyc7:/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81_head/kit-wave/s81_head/head_rp21z20NF15f_r18w12_1126/
- 2026-11-28 16:28 PST WAIT-STATE [KIT-WAVE -> HEAD-INT-R3] WAIT-FORM s81_head/hd_turn_a: missing a changed form fingerprint for s81_head/hd_turn_a, or a lanes/GEOM-REVIEW.md GOOD / OK / ISSUES-ACCEPT line for the rebuilt form; reviewer lane HEAD-INT-R3 (fallback INT-R3); reason: WAIT-FORM: exact kit intel2:/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81_head/kit-wave/s81_head/head_rp21z20NF15f_r18w12_1126/i
- 2026-11-28 16:28 PST WAIT-STATE [KIT-WAVE -> HEAD-INT-R3] WAIT-FORM s81_head/hd_turn_b: missing a changed form fingerprint for s81_head/hd_turn_b, or a lanes/GEOM-REVIEW.md GOOD / OK / ISSUES-ACCEPT line for the rebuilt form; reviewer lane HEAD-INT-R3 (fallback INT-R3); reason: WAIT-FORM: exact kit intel2:/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81_head/kit-wave/s81_head/head_rp21z20NF15f_r18w12_1126/i

