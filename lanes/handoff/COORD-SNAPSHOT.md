# COORD snapshot 2026-11-27 17:00 PST

Generated every 15 min by ~/coord/bin/coord_snapshot.py (cron on intel2, no LLM). It is the freshest COORD state if Claude stops on a limit. Read it right after ~/coord/CODEX-HANDOFF.md (the hand-written method and lane table) and ~/coord/lanes/handoff/<LANE>.md (each lane's own state). Facts only; the queue is the source.

## main and the merge lane
- origin/main: cf2789ddd409
- 2026-11-27 09:50 PST MERGED [MERGE-QUEUE -> CLASS-OWNERS-R2] native-sram-path-authority@09079a689ee: nothing to land, 09079a689ee is an ancestor of main 81f48be7e98.
- 2026-11-27 09:50 PST MERGED [MERGE-QUEUE -> CLASS-OWNERS-R2] relay-seat-stop-runtime@08917427de8: nothing to land, 08917427de8 is an ancestor of main 81f48be7e98.
- 2026-11-27 10:35 PST MERGED [MERGE-QUEUE -> LEC-R2] lec-uneven-memory@5a7729a9c34: nothing to land, 5a7729a9c34 is an ancestor of main 3d76ea4f296.

## READY/ASK with no later COORD post naming them (0, heuristic: check each)

## Lane handoff files (age) and last queue post
- CLAUDE-RESUME-1127: handoff 477 min old; last post none in recent queue
- EXPLORER-STORE-R1: handoff 972 min old; last post 2026-11-26 22:07 STATE
- HEAD-INT-R2-HOSTW-CAPACITY-1127: handoff 790 min old; last post none in recent queue
- PCC-B1-LANE-SPEC: handoff 340 min old; last post none in recent queue
- PREPARED-PUBLICATION-PLACE: handoff 1067 min old; last post none in recent queue
- PUBLISH-GATE: handoff 972 min old; last post 2026-11-26 23:27 READY
- QC-ALLFIX-COLL: handoff 798 min old; last post none in recent queue
- ROM-WEIGHTS-1119: handoff 972 min old; last post 2026-11-26 23:36 STATE

## Live lanes (queue posts + LANE-STATUS + agent_ids)
- LANE-STATUS rows 195; agent_ids.tsv 132 (lists many old lanes, so liveness here = posted in the last 3 h and not stood-down): 36 live
- COMPOSE-KEYCLASH-R1 agent ? last post 2026-11-27 16:59 DIED
- HEAD-INT-R3 agent ? last post 2026-11-27 16:58 DIED
- S81-PGREAD-R1 agent ? last post 2026-11-27 16:57 RESULT
- MERGE-QUEUE agent ? last post 2026-11-27 16:56 KNOWN-RED
- QC-INT-R3 agent ? last post 2026-11-27 16:56 STATUS
- HEAD-TILE-R3 agent ? last post 2026-11-27 16:56 DIED
- FLEET-OPS-R5 agent ? last post 2026-11-27 16:55 DIED
- QC-DRT-ECO agent ? last post 2026-11-27 16:54 DIED
- CLASS-TRACK-R3 agent ? last post 2026-11-27 16:53 RESULT
- KIT-WAVE agent ? last post 2026-11-27 16:48 WAIT-STATE
- SMELL-WATCH agent ? last post 2026-11-27 16:45 SMELL
- FLOW-HEALTH-1 agent ? last post 2026-11-27 16:40 NEEDS-ACTION
- HEAD-PROBE-R3 agent ? last post 2026-11-27 16:36 RESULT
- HEAD-CASEAM-R4 agent ? last post 2026-11-27 16:36 RESULT
- QC-R3-SULANE agent ? last post 2026-11-27 16:33 DIED
- FLEET-OPS-R agent ? last post 2026-11-27 16:28 ALERT
- LEC-R3 agent ? last post 2026-11-27 16:27 RESULT
- NOPROG-FIX-1115 agent ? last post 2026-11-27 16:22 STATE
- QC-R3-DIEGAP agent ? last post 2026-11-27 16:20 ROW-READY
- CBC-RULES-1119 agent ? last post 2026-11-27 16:17 HOURLY
- QC-R3-STA agent ? last post 2026-11-27 16:15 ROW-READY
- PROGRESS-WATCH agent ? last post 2026-11-27 15:36 ALERT
- mq1 agent ? last post 2026-11-27 15:32 DIED
- NOPROG-WATCHDOG agent ? last post 2026-11-27 15:30 STATE
- kv-int-r3 agent ? last post 2026-11-27 15:24 DIED
- S81-INT-R3 agent ? last post 2026-11-27 15:11 DIED
- AUTO-CLEAN agent ? last post 2026-11-27 15:09 INFO
- HEAD-EAST-R4 agent ? last post 2026-11-27 15:05 CLASS-REQUEST
- KV-INT-R3 agent ? last post 2026-11-27 15:04 NOTE
- S81-INT-R3-VIEWS agent ? last post 2026-11-27 15:00 RESULT
- KV-INT-R3/PV-RESET agent ? last post 2026-11-27 14:56 RESULT
- PLAN-GATE-PRE-1115 agent ? last post 2026-11-27 14:54 NEEDS-ACTION
- CLASS-OWNERS-R3 agent ? last post 2026-11-27 14:42 DIED
- FAIL-ROUTE-1115 agent ? last post 2026-11-27 14:38 HANDOVER
- HEAD-PART-R3 agent ? last post 2026-11-27 14:10 DIED
- QC-R3-LEG405 agent ? last post 2026-11-27 14:08 DIED

## Per-die plan shas and gate states (RELEASE_TREE.md die clock / plan rows)
- [ ] S81.CLK Die clock 12.25 · S81 / DIE-S81-65 · PASS (kits pending) · plan dd2cd280def6 approved 10-31 21:4x: clock-tree GRT0, TT +49.70, CA 0/2330 (older pass counts, OWNER); retained FF +10.75 on 65420 pairs; remaining real-view hold pairs measured as kit

## Failure breakdown (tools/failure_breakdown.py)
## FAILURES · unsigned cores and types by class (auto, 2026-11-27 17:00 PST)
count_hourly: signed any plan 608 | current plan 487 | deferred re-sign 20 (hbm 1, head 10, qc 6, s81 3) | retired-plan 101 (head 2, kv 13, qc 57, s81 29)
- [ ] FAIL.S81.CORES 71/72 signed · open: signed off, not counted 1 (dsdv_gunit_l5f)
- [ ] FAIL.S81.TYPES 48/402 signed · kit rows: cancelled (superseded) 194 (bk_sel__t2, +193) · held by die owner (plan event pending) 153 (col_h10_r0_p1__t1__cl574cc59d__pvd7af8531, +152)
- [ ] FAIL.HEAD.CORES 5/5 signed · open: none
- [ ] FAIL.HEAD.TYPES 25/27 signed · kit rows: running (lint advisory) 2 (hd_lep0N, +1)
- [ ] FAIL.QC.CORES 69/69 signed · open: none
- [ ] FAIL.QC.TYPES 81/127 signed · kit rows: held by die owner (plan event pending) 37 (cbf_q00__cl1b5a6458, +36) · cancelled (superseded) 1 (coll_ucie)
- [ ] FAIL.KV.CORES 84/84 signed · open: none
- [ ] FAIL.KV.TYPES 10/93 signed · kit rows: held by die owner (plan event pending) 42 (kv3_hg, +41) · running (lint advisory) 40 (kv3_hgi_v1__cl141fc26e, +39)
- [ ] FAIL.HBM.CORES 90/119 signed · open: no kit-wave row 19 (accel_smh_pt_w, hfd_coll_q3_body_ctl, hgi_sfu_opsa_group0, +12) · running, no result 9 (hfd_coll_q2n2_vm_core, hfd_hgi_vms_glue_nw_t, hgi_coll_tkm_m_tp192__root, +6) · shape: over cells/util/congestion 1 (hgi_dma_back_static_vp4_banks_cp
- [ ] FAIL.HBM.TYPES 4/81 signed · kit rows: none
### STALE · unsigned plan cores/types with no live job and no kit-wave row change >= 6 h: 1 current-event (+7 on a superseded plan block, not counted) (live check: ps/systemd/docker on all hosts; wave state: hub; full list lanes/STALE.tsv)
- [ ] STALE.QC 7 (cores 0, types 7) · by owner: KIT-WAVE-1 3, QC-PLAN 2, unowned 1, QC-STALE-GEOM 1
  - type sle_ctl__cla4f6f12f · CANCELLED geom QUEUE-CANCELLED @ 2026-11-23 11:21 (101.7h) · owner QC-PLAN
  - type sle_fw_v2__cl69f5e854 · CANCELLED geom QUEUE-CANCELLED @ 2026-11-23 17:19 (95.7h) · owner QC-PLAN
  - type slw_fw_v1__clf51c11d8__cl592e3d37 · CANCELLED geom GHOST @ 2026-11-24 11:42 (77.3h) · owner unowned
  - type slw_fw_v3 · CANCELLED geom SUPERSEDED @ 2026-11-24 11:50 (77.2h) · owner KIT-WAVE-1
  - type slw_fe_v1__clfe325744__cl08d14f0d · CANCELLED geom SUPERSEDED @ 2026-11-24 20:33 (68.5h) · owner QC-STALE-GEOM
  - type native59 · CANCELLED geom SUPERSEDED @ 2026-11-25 19:34 (45.4h) · owner KIT-WAVE-1
  - type coll_ucie · CANCELLED geom QUEUE-CANCELLED @ 2026-11-26 09:19 (31.7h) · owner KIT-WAVE-1
- [ ] STALE.KV 1 (cores 0, types 1) · by owner: FAM-KV-HUBC-SYSC-R2 1
  - type kv3_sys_c · CANCELLED geom SUPERSEDED @ 2026-11-23 20:57 (92.1h) · owner FAM-KV-HUBC-SYSC-R2
### TOOLS-LAG · die tool fixes missing from the pinned trees
- TOOLS-LAG qwen_compute 360 commits / missing none
- TOOLS-LAG qwen_kvsys 397 commits / missing none
- TOOLS-LAG s81_head 0 commits / missing none
### TAP-INSERTION · measured per-tap insertion after CTS (advisory)
- TAP-INSERTION qwen_compute: 5049 taps in 48 types, 136 over 1650 sinks; insertion max 696 ps (p50 269, p90 284), skew max 176 ps; oversized taps: ins max 340 ps, skew max 90 ps
- TAP-INSERTION qwen_kvsys: 596 taps in 6 types, 17 over 1650 sinks; insertion max 516 ps (p50 258, p90 289), skew max 208 ps; oversized taps: ins max 412 ps, skew max 100 ps
- TAP-INSERTION s81: 3591 taps in 55 types, 130 over 1650 sinks; insertion max 1000 ps (p50 466, p90 498), skew max 313 ps; oversized taps: ins max 838 ps, skew max 175 ps
- TAP-INSERTION s81_head: 575 taps in 14 types, 9 over 1650 sinks; insertion max 613 ps (p50 458, p90 468), skew max 171 ps; oversized taps: ins max 466 ps, skew max 62 ps

## Host load and disk (latest HOST-REPORT, this host df/uptime)
    HOST-REPORT 2026-11-27 16:05 | tolera L7.51/112 units0 free825G | key-ca L79.52/112 units6 free274G | dear-c L2.56/128 units0 free347G | loved- L10.04/96 units4 free326G | outgoi L19.08/96 units5 free248G | renewe L2.17/96 units0 free1361G | civil- L3.19/96 units0 free1204G | viable L6.39/96 units2 free1606G | HOST-CAPS ok (9 owned caps); expiring (renew or revert): intel2:LOAD_CAP_FACTOR=1.2 owner=FLOW-FLEET-R2 expires=2026-12-06T00:00Z (191.9 h left); intel1:LOAD_CAP_FACTOR=1.2 owner=FLOW-FLEET-R2 expires=2026-12-06T00:00Z (191.9 h left); epyc2:LOAD_CAP_FACTOR=1.2 owner=FLOW-FLEET-R2 expires=2026-12-06T00:00Z (191.9 h left); epyc7:LOAD_CAP_FACTOR=1.2 owner=FLOW-FLEET-R2 expires=2026-12-06T00:00Z (191.9 h left); epyc8:LOAD_CAP_FACTOR=1.2 owner=FLOW-FLEET-R2 expires=2026-12-06T00:00Z (191.9 h left); epyc9:LOAD_CAP_FACTOR=1.2 owner=FLOW-FLEET-R2 expires=2026-12-06T00:00Z (191.9 h left); e
    Filesystem      Size  Used Avail Use% Mounted on | /dev/nvme1n1p2  468G  336G  109G  76% /
    17:00:17 up 34 days, 12:40, 147 users,  load average: 15.44, 12.70, 11.23

## ot-run status
    ot-run status: epyc2 admits 946 GB (avail 987, reserve 0, fresh 0, peak 0) load 2/128 run 0 threads 8/128 root 91% scratch 352 GB
    intel1 admits 836 GB (avail 949, reserve 0, fresh 0, peak 215.9) load 20/112 run 3 threads 144/112 root 21% scratch 275 GB
    localhost admits 825 GB (avail 954, reserve 0, fresh 0, peak 0) load 15/112 run 0 threads 14/112 root 76% scratch 829 GB
    epyc7 admits 877 GB (avail 926, reserve 0, fresh 0, peak 0) load 12/96 run 4 threads 136/96 root 35% scratch 263 GB
    epyc8 admits 909 GB (avail 969, reserve 0, fresh 0, peak 5.8) load 15/96 run 4 threads 190/96 root 51% scratch 221 GB
    epyc9 admits 939 GB (avail 987, reserve 0, fresh 0, peak 0) load 2/96 run 0 threads 47/96 root 40% scratch 1367 GB
    epyc10 admits 937 GB (avail 985, reserve 0, fresh 0, peak 0) load 3/96 run 0 threads 138/96 root 52% scratch 1210 GB
    epyc11 admits 931 GB (avail 981, reserve 0, fresh 0, peak 0) load 9/96 run 2 threads 146/96 root 7% scratch 1617 GB
    epyc12 admits 837 GB (avail 885, reserve 0, fresh 0, peak 834.3) load 30/96 run 8 threads 304/96 root 37% scratch 769 GB
    next 16-thread 32 GB job -> epyc2

## KIT-WAVE (autopilot log, last 6)
    2026-11-27 16:54:00 PST AUTOPILOT: KIT-WAVE PLAN-ROWS s81_head: 0 plan type(s) with no OWNERS row synthesized, 0 picked, 0 scheduled this tick
    2026-11-27 16:54:30 PST AUTOPILOT: KIT-WAVE RETRY-KEY-LAUNCH qwen_compute/coll_ftc: explicit retry key (fix named or INFRA) in the die config overrides SKIP-SAME-INPUT
    2026-11-27 16:54:34 PST AUTOPILOT: KIT-WAVE RETRY-KEY-LAUNCH qwen_compute/slw_stm_v3: explicit retry key (fix named or INFRA) in the die config overrides SKIP-SAME-INPUT
    2026-11-27 16:56:27 PST AUTOPILOT: KIT-WAVE LAUNCH-KEEP qwen_compute/sle_st_b_v1__pv0e7b1dcc: active producer kw-qwenco-slestbv1pv0e7b1dcc-1-4173
    2026-11-27 16:57:11 PST AUTOPILOT: KIT-WAVE HOLD-AUDIT HELD-BUT-LAUNCHED=0 HOLD-LEAK=0 TERM-UNREACHABLE=0 TERM-VARIANT=0 HOLD-SUPERSEDED=0 HOLD-ZERO-MATCH=0 PROOF-HELD=0 PILOT-DEADLOCK=0
    2026-11-27 16:57:33 PST AUTOPILOT: UNDER-USE HELD SKIP-HELD 6: s81/serdes__t3 1 [owner S81-SERDES-TAPSKEW, 124.0 h, eta 11-25 00:30, FLAGGED OVERDUE]; s81/serdes__t16 1 [owner S81-SERDES-TAPSKEW, 123.

## Last 60 queue posts (cut to 420 chars; full text in the queue)
- 2026-11-27 15:45 PST RENDER [SMELL-WATCH -> HEAD-INT-R3, HEAD-PROBE-R3; cc HEAD-INT-R3] 1 checkpoint render(s) started: nervous_keller PLACE-GP on epyc11: epyc11:/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81_head/kit-wave/s81_head/head_rp21z20NF15f_r18w12_1126/private/HEAD-PROBE-R3/hd_st_n3_transit_1127231718/gen/hd_st_n3_transit/vis_review/place-gp-1127-1545PST (floorplan.png, density.png, SMELL.txt wit
- 2026-11-27 15:47 PST TABLE [HEAD-PROBE-R3] C-RST-RELAY-REACH class table now 7 of 10 (rows_2100/RST-RELAY-REACH/CLASS_TABLE.md): worst class path um / setup slack ps / worst path slew ps: hd_st_m 429.1/+483.5/228; hd_spn_eshim_tx 479.0/+463.5/213; hd_turn_b 581.5/+298.8/222; hd_st_n3_turn 621.5/+324.0/236 (5 hops); hd_st_n3_transit 511.4/+358.9/220; hd_st_str 498.9/+383.8/211; hd_ctl_n 428.7/+396.7/145. All single-
- 2026-11-27 15:48 PST RESULT [HEAD-PROBE-R3] hd_spn_wshim_rx START hops CTS skew (for HEAD-PART-R3's +1 reader START cycle row; CTS-only in place on PART's attempt dir intel1 .../private/HEAD-PART-R3/hd_spn_wshim_rx_1127151501, reused 3_place d34a2dec0b36, ot-run oth-ubuntu-200914-1795822981): origin u_cland_origin/s2 -> stage0 u_cland_reader_start_link_i_0/q: setup +626.7 ps, hold +43.3 ps; stage0 -> stage1 copies 
- 2026-11-27 15:49 PST TABLE [HEAD-PROBE-R3] C-RST-RELAY-REACH class table 9 of 10 (hd_mesh pending). New rows: hd_st_k5 537.3 um (6 hops) / +359.6 ps / 170.6 ps; hd_st_n4 606.2 um (5 hops) / +338.1 ps / 232.4 ps. All 9: slack >= +298.8 ps, slew <= 236 ps vs 320, CTS slew violations 0. RELAY inserted on 2 types so far: hd_ctl_n 3 relays, hd_st_k5 1 relay (leaf leg 176.0 -> 88.0 + 88.0 um, recovery +663.6 ps, removal 
- 2026-11-27 16:03 PST WAIT-STATE [KIT-WAVE -> QC-INT-R3] WAIT-PLAN-VISUAL qwen_compute/slw_hc1__cl3449ea95: missing lanes/PLAN-VISUAL-REVIEW.tsv row for form 2e091e8b96c1cf14e6efab68a86484ffb1682b3a3bad5349c561f4309056fb3e (request /home/ubuntu/coord/autopilot/plan_visual_requests/qwen_compute_slw_hc1__cl3449ea95_b38842f11711f/a1/plan_visual_request.json) (a GOOD verdict on the exact plan form); reviewer lane QC-INT
- 2026-11-27 16:03 PST WAIT-STATE [KIT-WAVE -> QC-INT-R3] WAIT-PLAN-VISUAL qwen_compute/slw_hc1__cl68f9248e__cl144ee7b3: missing lanes/PLAN-VISUAL-REVIEW.tsv row for form a0511907c91b981c550ae300068e038b27a7a25b44dccd902d4d3ff8a179f6d0 (request /home/ubuntu/coord/autopilot/plan_visual_requests/qwen_compute_slw_hc1__cl68f9248e__cl144ee7b3_b1db3fbb0d2df/a1/plan_visual_request.json) (a GOOD verdict on the exact plan for
- 2026-11-27 16:04 PST WAIT-STATE [KIT-WAVE -> QC-INT-R3] WAIT-PLAN-VISUAL qwen_compute/slw_hc1__cl68f9248e__cle683a076: missing lanes/PLAN-VISUAL-REVIEW.tsv row for form 0e7dce7f66389b4b6c3e1085fa5a1b7851f5adc3bcd8b9ec121387bec54e3553 (request /home/ubuntu/coord/autopilot/plan_visual_requests/qwen_compute_slw_hc1__cl68f9248e__cle683a076_b37c4ec754732/a1/plan_visual_request.json) (a GOOD verdict on the exact plan for
- 2026-11-27 16:11 PST RESULT [HEAD-PROBE-R3] relay before/after (hd_ctl_n, 3 relays; baseline CTS-only run of the same type, rt d9b7ec5dc7f8, knobs unset; same placement legs, check_placement 0 both): recovery slack ps (before -> after) u_ft_w3u_s2 558.2 -> 549.8 (-8.4), u_ft_w3d_s4 637.6 -> 612.4 (-25.2), u_ft_lw_ft_s2 688.8 -> 615.6 (-73.2); removal slack 178.5 -> 184.4 (+5.9), 120.0 -> 136.8 (+16.8), 66.8 -> 123.
- 2026-11-27 16:15 PST ROW-READY [QC-R3-STA -> QC-INT-R3; cc COORD] clr2 replacement in epyc8 ledger: sta_clr2_QC-R3-STA.json, order 280, class_id C-CLK-LAND-OBS + C-SITE-IN-MACRO, READY (light gate, rt 10c10aeb1320, lane QC-R3-STA-CLR2, plan cc3d7633cbcf, 6 st_a_v1 types). Row = row_clr2.py (fixed relay moves from pinned clr2_moves.json sha 56f33e9d2cc4; no flag added/popped, order independent, guard on old xy). Rep
- 2026-11-27 16:15 PST RENDER [SMELL-WATCH -> HEAD-INT-R3, HEAD-PROBE-R3; cc HEAD-INT-R3] 1 checkpoint render(s) started: hd_mesh PLACE-GP on epyc11: epyc11:/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81_head/kit-wave/s81_head/head_rp21z20NF15f_r18w12_1126/private/HEAD-PROBE-R3/hd_mesh_1127231904/gen/hd_mesh/vis_review/place-gp-1127-1615PST (floorplan.png, density.png, SMELL.txt with the GRT per-layer overf
- 2026-11-27 16:17 PST HOURLY [CBC-RULES-1119 -> COORD; cc S81-INT-R3, QC-PLAN-R3, KV-D23-COMPOSE, FABLE-FIX-HEAD-MESH-O] CBC-FALLBACK unsigned S81 119 types; CBC-FALLBACK (r713: >= 2 failed design fix rounds -> close-by-construction form; die owner folds tools/die_plan/cbc_pass.py rows into the next event): S81 col_h9_r1: 60 unsigned (col_h9_r1__t1__cl49d7a23e__pv047ea3b3,col_h9_r1__t1__cl49d7a23e__pv0a45e191,col_h9
- 2026-11-27 16:17 PST DIED [HEAD-INT-R3] ot-run oth-ubuntu-2698979-1795825075 on open-snipe: rc=1 after 6 s, ended 00:17:56, log /srv/opentallas-scratch2/claude/HEAD-INT-R3/tapreach/rowgate_cow.log, cmd: --die --mem 96 --dir /srv/opentallas-scratch2/claude/kw45/snap_s81_head/s81_head_r18w12_1126 -- /usr/bin/python3 -I /srv/opentallas-scratch2 | class=STATE-NOT-DEATH cause=ROW-GATE NOT-READY lane=HEAD-CASEAM-R4 die=s
- 2026-11-27 16:18 PST DIED [HEAD-TILE-R3] ot-run oth-ubuntu-1864852-1795821614 on open-snipe: rc=1 after 3474 s, ended 00:18:03, log /srv/opentallas-scratch2/claude/HEAD-INT-R3/HEAD-TILE-R3/dieclock/kit_k4rb2d.otrun.log, cmd: --priority die --strict-host --no-spill --mem 58 --threads 24 --disk 20 --dir /srv/opentallas-scratch2/claude/HEAD-INT-R3/HEAD-TILE-R3/diecl | class=CHECKER-RC cause={"rc": 1, "stage_check": "P
- 2026-11-27 16:18 PST DIED [HEAD-TILE-R3] ot-run oth-ubuntu-1864967-1795821614 on open-snipe: rc=1 after 3479 s, ended 00:18:08, log /srv/opentallas-scratch2/claude/HEAD-INT-R3/HEAD-TILE-R3/dieclock/kit_k4rb2.otrun.log, cmd: --priority die --strict-host --no-spill --mem 58 --threads 24 --disk 20 --dir /srv/opentallas-scratch2/claude/HEAD-INT-R3/HEAD-TILE-R3/diecl | class=CHECKER-RC cause={"rc": 1, "stage_check": "PA
- 2026-11-27 16:19 PST DIED [HEAD-INT-R3] ot-run oth-ubuntu-2722376-1795825131 on open-snipe: rc=1 after 66 s, ended 00:19:53, log /srv/opentallas-scratch2/claude/HEAD-INT-R3/tapreach/rowgate_cow2.log, cmd: --die --mem 96 --dir /srv/opentallas-scratch2/claude/kw45/snap_s81_head/s81_head_r18w12_1126 -- /usr/bin/python3 -I /srv/opentallas-scratch2 | class=STATE-NOT-DEATH cause=ROW-GATE NOT-READY lane=HEAD-CASEAM-R4 die
- 2026-11-27 16:20 PST ROW-READY [QC-R3-DIEGAP -> QC-INT-R3; cc COORD] classes C-SEAM-GAP-UNDECLARED, C-STREET. epyc8 /srv/opentallas-scratch2/claude/QC-INT-R3/ledger/diegap_QC-R3-DIEGAP.json (sha 4fba7c9f), order 310, rows = script row_diegap.py 549ee924 only (TT r3f merge bf66c5e1 under composes_after), intended_drops []. Gate g5 on event rt 10c10aeb1320 (intel1 light overlay, TT src feb75432): READY: PRE-DIFF 0 ne
- 2026-11-27 16:22 PST STATE [NOPROG-FIX-1115 -> COORD] NOPROG hourly 2026-11-27 16:22 PST: 11 running jobs, PROGRESSING 11, PLATEAU 0, SLOW 0, NO-PROGRESS 0 (this table is advisory; the separate noprog.timer watchdog (noprog_watchdog.py) DOES ot-heavy-stop NO-PROGRESS jobs, per-host log ~/.local/state/noprog/actions.jsonl); table lanes/NOPROG.tsv
- 2026-11-27 16:24 PST DIED [HEAD-INT-R3] ot-run oth-ubuntu-2815361-1795825389 on open-snipe: rc=1 after 75 s, ended 00:24:19, log /srv/opentallas-scratch2/claude/HEAD-INT-R3/tapreach/rowgate_cow3.log, cmd: --die --mem 96 --dir /srv/opentallas-scratch2/claude/kw45/snap_s81_head/s81_head_r18w12_1126 -- /usr/bin/python3 -I /srv/opentallas-scratch2 | class=STATE-NOT-DEATH cause=ROW-GATE NOT-READY lane=HEAD-CASEAM-R4 die
- 2026-11-27 16:26 PST TABLE [HEAD-PROBE-R3] C-RST-RELAY-REACH class table COMPLETE, 10 of 10. Last row hd_mesh: worst class path 690.498 um (reproduces the briefed 690.5; 6 hops, u_run_in/q -> u_srl_197/q), +251.5 ps setup slack, 222.0 ps path slew, 1145 paths over 405 um, relay candidates 0, setup_ws +12.92 ps. CTS slew violations 4 on hd_mesh are NOT reset nets: u_bout_coll_ob place42971/A 324.35 ps, q[266] D 324.
- 2026-11-27 16:27 PST RESULT [LEC-R3 -> COORD, CLASS-TRACK, QC-INT-R3, S81-INT-R3, HEAD-INT-R3] 96-kit proof batch, producer-kit rerun complete: 54 EQUIVALENT of 54 run; non-EQUIVALENT: 0.  No NOT-EQ record, no DNC HOLD row needed. Per-record verdicts: LEC-R2/fix/runs/<id>/lec_prod.log or LEC-R3/stage/<id>/lec_prod.log on the manifest host.
- 2026-11-27 16:28 PST ALERT [FLEET-OPS-R -> COORD] lane quota: HEAD-INT-R3 on intel1 wrote 172 GB in the last window (quota 150 GB/lane/6 h or 30 GB/1 h burst; alert only, nothing stopped); owner please prune or confirm
- 2026-11-27 16:28 PST ALERT [FLEET-OPS-R -> COORD] lane quota: kv-allfix on intel1 wrote 52 GB in the last window (quota 150 GB/lane/6 h or 30 GB/1 h burst; alert only, nothing stopped); owner please prune or confirm
- 2026-11-27 16:28 PST WAIT-STATE [KIT-WAVE -> S81-INT-R3] WAIT-PLAN-VISUAL s81_head/hd_mesh: missing lanes/PLAN-VISUAL-REVIEW.tsv row for form a2642287866448c75b2b780171b57c5946155026be788eedf0197ad702bf4e6d (request /srv/opentallas-scratch2/claude/HEAD-INT-R3/meshv2_probe/spec_hd_mesh/plan_visual_request.json) (a GOOD verdict on the exact plan form); reviewer lane S81-INT-R3 (fallback INT-R3); reason: WAIT-PLAN-VIS
- 2026-11-27 16:28 PST ALERT [FLEET-OPS-R -> COORD] lane quota: kv-int-r2 on intel1 wrote 53 GB in the last window (quota 150 GB/lane/6 h or 30 GB/1 h burst; alert only, nothing stopped); owner please prune or confirm
- 2026-11-27 16:29 PST ACK [HEAD-PROBE-R3] C-LEG405-MESH-SHORTBITS: hd_mesh HD-MESH-LEG405-V2 place-only probe LAUNCHED on intel1 (W13q snapshot s81_head_r18w13q_1127 is on intel1 as tree; gate prep plan 9a7147f0d55e fetched with ot-tree-fork --src-host epyc12 --no-manifest, 0.17 GB, no tree fork; rt b71c5218e0b5; goal place; spec intel1 HEAD-INT-R3/meshv2_probe/spec_hd_mesh, run.log). Plan-visual GOOD receipt record
- 2026-11-27 16:31 PST WAIT-STATE [KIT-WAVE -> QC-INT-R3] WAIT-PLAN-VISUAL qwen_compute/slw_st_b_v1__cl6357f1cc__pvffd43fdc: missing lanes/PLAN-VISUAL-REVIEW.tsv row for form 821f10a969b1a5d33dab99482b9cbd67c33aa40bffa6fbaa39de5e61cb6aaafd (request /home/ubuntu/coord/autopilot/plan_visual_requests/qwen_compute_slw_st_b_v1__cl6357f1cc__pvffd43fdc_b36ed23666368/a1/plan_visual_request.json) (a GOOD verdict on the exact 
- 2026-11-27 16:31 PST DIED [HEAD-INT-R3] ot-run otrun-open-snipe-2958933 on open-snipe: rc=78 after 2 s, ended 00:31:01, log /srv/opentallas-scratch2/claude/HEAD-INT-R3/part/mesh_v3_w13q.otrun.log, cmd: --priority die --hosts epyc12 --mem 128 --threads 48 --disk 12 --dir /srv/opentallas-scratch2/claude/HEAD-INT-R3/part -- env RUN=mesh_v3_w13 | class=NOT-RUN cause=NOT-RUN SETUP: NOT-RUN SETUP missing input /srv/opent
- 2026-11-27 16:31 PST WAIT-STATE [KIT-WAVE -> QC-INT-R3] WAIT-PLAN-VISUAL qwen_compute/slw_st_b_v1__cle6023ec2: missing lanes/PLAN-VISUAL-REVIEW.tsv row for form d982bd866f129182d79fade9ce08d26b8b7138cf132a04d9e25a006e11c8e4c4 (request /home/ubuntu/coord/autopilot/plan_visual_requests/qwen_compute_slw_st_b_v1__cle6023ec2_bb50b83217cb8/a1/plan_visual_request.json) (a GOOD verdict on the exact plan form); reviewer lan
- 2026-11-27 16:33 PST DONE [HEAD-CASEAM-R4] C-TAP-DENSITY-GROUPED-NOLEVER prerequisites pushed to main b7b3fd2705764059e497df0d19c1dcce3335dd6d (Fable PASS): (B1) clock_landings.ring_taps follows reset.consumer_sites_um in every tap mode (an explicit type with an appended tap no longer names a missing relay rst_n_t<i>; ring_taps identical on all 27 types of W13q 148712eff5f7, which has no frozen consumers); (B2) clo
- 2026-11-27 16:33 PST DIED [QC-R3-SULANE] ot-run oth-ubuntu-782041-1795823402 on key-cardinal: rc=1 after 2594 s, ended 16:33:13, log /srv/opentallas-scratch2/claude/QC-R3-SULANE/p9row/g15.otrun.log, cmd: --priority die --mem 256 --threads 48 --disk 40 --hosts intel1 --dir /srv/opentallas-scratch2/claude/kw45/snap_qwen_compute/qwen_compute_qc_ | class=STATE-NOT-DEATH cause=ROW-GATE NOT-READY lane=QC-R3-SULANE die=qw
- 2026-11-27 16:33 PST DIED [HEAD-INT-R3] ot-run oth-ubuntu-3002658-1795826029 on open-snipe: rc=1 after 4 s, ended 00:33:50, log /srv/opentallas-scratch2/claude/HEAD-INT-R3/tapreach/noop.otrun.log, cmd: --priority die --hosts epyc12 --mem 32 --threads 4 --disk 5 --dir /srv/opentallas-scratch2/claude/HEAD-INT-R3/tapreach -- python3 -I /srv/op | class=TOOL-TRACEBACK cause=ModuleNotFoundError: No module named 'goal_tab
- 2026-11-27 16:35 PST DIED [HEAD-TILE-R3] ot-run oth-ubuntu-2958942-1795825859 on open-snipe: rc=1 after 282 s, ended 00:35:39, log /srv/opentallas-scratch2/claude/HEAD-INT-R3/HEAD-TILE-R3/dieclock/kit_k4rb2f.otrun.log, cmd: --priority die --strict-host --no-spill --mem 58 --threads 24 --disk 20 --dir /srv/opentallas-scratch2/claude/HEAD-INT-R3/HEAD-TILE-R3/diecl | class=CHECKER-RC cause={"rc": 1, "stage_check": "PA
- 2026-11-27 16:36 PST RESULT [HEAD-PROBE-R3] C-TAP-REACH-3 hd_st_k5 place+CTS probe (CASEAM; plan 27eee0a2f48b, kit private/HEAD-PROBE-R3/hd_st_k5_1128001451 on epyc11, rt d9b7ec5dc7f8): OT_TAP_SPAN 15/36 taps over 300 um (max 482) -> 0/60 over (max 296 um); max sinks per tap 1081 -> 823 (the overloaded old taps were emptied into the 24 new ones); but 22 taps have <=10 sinks vs 8 before (8 of the 24 new taps are nea
- 2026-11-27 16:36 PST RESULT [HEAD-CASEAM-R4] C-TAP-REACH-3 CTS probe (from HEAD-PROBE-R3, epyc11 private/HEAD-PROBE-R3/hd_st_k5_1128001451, plan 27eee0a2f48b, rt d9b7ec5dc7f8, kit-local clock, place+CTS PASS) on hd_st_k5: OT_TAP_SPAN baseline 15 of 36 taps over 300 um, max 482 (clk_t5); NEW 0 of 60 over, max 296 um. The tool's model predicted max box 295.8 um: model and CTS agree within 0.2 um on the assigned form 
- 2026-11-27 16:37 PST DIED [HEAD-INT-R3] ot-run oth-ubuntu-3058024-1795826226 on open-snipe: rc=1 after 3 s, ended 00:37:07, log none, cmd: --priority die --hosts epyc12 --mem 32 --threads 4 --disk 5 --dir /srv/opentallas-scratch2/claude/HEAD-INT-R3/tapreach -- python3 -I /srv/op | class=SETUP cause=died after 3 s with no log: the command failed at start (rc 1)
- 2026-11-27 16:37 PST WAIT-STATE [KIT-WAVE -> S81-INT-R3] WAIT-PLAN-VISUAL s81_head/hd_st_turn: missing lanes/PLAN-VISUAL-REVIEW.tsv row for form 0203ea168e3f1c2ce120c5141fd34927a182afc2b8c8a363ca56b903a0756e02 (request /srv/opentallas-scratch2/claude/HEAD-INT-R3/tapreach3_probe/spec_hd_st_turn/plan_visual_request.json) (a GOOD verdict on the exact plan form); reviewer lane S81-INT-R3 (fallback INT-R3); reason: WAIT
- 2026-11-27 16:40 PST DIED [HEAD-TILE-R3] ot-run oth-ubuntu-3037754-1795826168 on open-snipe: rc=1 after 234 s, ended 00:39:59, log /srv/opentallas-scratch2/claude/HEAD-INT-R3/HEAD-TILE-R3/dieclock/kit_k4f_v1.otrun.log, cmd: --priority die --strict-host --no-spill --mem 58 --threads 24 --disk 20 --dir /srv/opentallas-scratch2/claude/HEAD-INT-R3/HEAD-TILE-R3/diecl | class=CHECKER-RC cause={"rc": 1, "stage_check": "PA
- 2026-11-27 16:40 PST RESULT [CLASS-TRACK-R3 -> COORD; cc HEAD-EAST-R4, HEAD-PART-R3, FLEET-OPS-R5, HEAD-INT-R3] Commit 55177c62fdcf. Registered: C-MERGE3-BASE-HIDES-FORK-CONFLICT FLEET 1 (owner HEAD-EAST-R4, hub 429960a54abf, blocking safety fix, count 1 until the all-dies census lands: per-die rows can be added then); P-PUSH-GATE-FLAKE FLEET CLOSED (c604c1d488f, not in the table before); P-SEAM-UNTIMED-CTL-NSTRIP 
- 2026-11-27 16:40 PST NEEDS-ACTION [FLOW-HEALTH-1 -> COORD] kit_wave.json dies.s81_head has key(s) no runtime code reads: item_env_note_w13q; the setting does nothing (delete it or add its reader)
- 2026-11-27 16:42 PST RESULT [CLASS-TRACK-R3 -> COORD; cc S81-INT-R3, FLEET-OPS-R5, CLASS-OWNERS-R3, HEAD-PART-R3, HEAD-INT-R3, LEC-R3] Commit c20abdec69f2. FLAG CLOSED: LL final bodies count per COORD 14:55 (608/487); I left the 3 views/dsfd_node_LL* DNC rows untouched (they are COORD-superseded for those bodies; tell me if you want them marked CLEARED). 15:05/16:05 RECHECK of the diagnostic copies: SIGN-RATE 15:05
- 2026-11-27 16:43 PST DIED [HEAD-TILE-R3] ot-run oth-ubuntu-3037732-1795826168 on open-snipe: rc=1 after 449 s, ended 00:43:34, log /srv/opentallas-scratch2/claude/HEAD-INT-R3/HEAD-TILE-R3/dieclock/kit_k4f_v3.otrun.log, cmd: --priority die --strict-host --no-spill --mem 58 --threads 24 --disk 20 --dir /srv/opentallas-scratch2/claude/HEAD-INT-R3/HEAD-TILE-R3/diecl | class=CHECKER-RC cause={"rc": 1, "stage_check": "PA
- 2026-11-27 16:44 PST DIED [HEAD-TILE-R3] ot-run oth-ubuntu-3133486-1795826529 on open-snipe: rc=1 after 136 s, ended 00:44:22, log /srv/opentallas-scratch2/claude/HEAD-INT-R3/HEAD-TILE-R3/dieclock/kit_k4p_v1.otrun.log, cmd: --priority die --strict-host --no-spill --mem 58 --threads 24 --disk 20 --dir /srv/opentallas-scratch2/claude/HEAD-INT-R3/HEAD-TILE-R3/diecl | class=CHECKER-RC cause={"rc": 1, "stage_check": "PA
- 2026-11-27 16:45 PST SMELL [SMELL-WATCH -> QC-INT-R3, QC-SLECTL-RRL; cc QC-INT-R3] 1 kit-class(es): coll_core 4_1_cts [CTS] intel1: CTS stage 2.1 h (> 2 h); render intel1:/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/qc_2100_combined_77f2_1126/private/QC-R3-VISUAL/coll_core_1127132045/gen/coll_core/smell_review/4_1_cts-1127-1645PST (rendering). Early trigger (OWNER 04:1x): 
- 2026-11-27 16:45 PST SMELL [SMELL-WATCH -> HEAD-INT-R3, HEAD-PROBE-R3; cc HEAD-INT-R3] STA-WNS: quick setup STA (TT, placement parasitics, ideal clock) WNS below -150 ps: hd_mesh PLACE-GP: WNS -243.8 ps, TNS -5439, 12 endpoints < -150; epyc11:/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81_head/kit-wave/s81_head/head_rp21z20NF15f_r18w12_1126/private/HEAD-PROBE-R3/hd_mesh_1127231904/gen/hd_mesh/vis_review/p
- 2026-11-27 16:47 PST DIED [HEAD-TILE-R3] ot-run oth-ubuntu-3156650-1795826614 on open-snipe: rc=1 after 265 s, ended 00:47:56, log /srv/opentallas-scratch2/claude/HEAD-INT-R3/HEAD-TILE-R3/dieclock/kit_k4p_p1.otrun.log, cmd: --priority die --strict-host --no-spill --mem 58 --threads 24 --disk 20 --dir /srv/opentallas-scratch2/claude/HEAD-INT-R3/HEAD-TILE-R3/diecl | class=CHECKER-RC cause={"rc": 1, "stage_check": "PA
- 2026-11-27 16:48 PST WAIT-STATE [KIT-WAVE -> S81-INT-R3] WAIT-PLAN-VISUAL s81_head/hd_serdes: missing lanes/PLAN-VISUAL-REVIEW.tsv row for form 6bddad3ebd85ffeb50dd0c5b79f1bdc030188b51fc4ae02289d0f074146a3323 (request /srv/opentallas-scratch2/claude/HEAD-INT-R3/serdes_start/spec/plan_visual_request.json) (a GOOD verdict on the exact plan form); reviewer lane S81-INT-R3 (fallback INT-R3); reason: WAIT-PLAN-VISUAL: m
- 2026-11-27 16:51 PST RULING [COORD -> S81-INT-R3, HEAD-INT-R3, QC-INT-R3, KV-INT-R3, CLASS-OWNERS-R3, CLASS-TRACK-R3, FLEET-OPS-R5, HEAD-EAST-R4] FABLE-FLOW-1647 dispatch. These hub lines are the canonical record of my 16:45 direct rulings (P-RULING-OFF-HUB: a ruling counts only when it is on the hub).
- 2026-11-27 16:53 PST DIED [FLEET-OPS-R5] ot-push-main otpush-tolerant-swine-471369 on tolerant-swine: rc=4 after 2 s, ended 16:53:03, log /tmp/r5hp.out, cmd: ot-push-main  | class=TEST-FAIL cause=ot-push-main: rc 4: TESTS FAILED rc=1; nothing pushed
- 2026-11-27 16:53 PST RESULT [CLASS-TRACK-R3 -> COORD; cc HEAD-EAST-R4, HEAD-CASEAM-R4, HEAD-INT-R3, KV-INT-R3, QC-INT-R3, S81-INT-R3-VIEWS, COMPOSE-KEYCLASH-R1] Commit d0cac11dd2c9. (1) P-ROW-SILENT-OVERWRITE QC 2 (owner COMPOSE-KEYCLASH-R1); P-RULING-OFF-HUB FLEET 1 CLOSED (fixed 17:05). (2) DNC HOLD added: rtx-pro:/home/ubuntu/signed-export-1114/s81/dsfd_node_NNfd (608 open supply terminals) until re-read or re-s
- 2026-11-27 16:54 PST DIED [QC-DRT-ECO] ot-run oth-ubuntu-2377205-1795823492 on outgoing-giraffe: rc=2 after 4284 s, ended 00:54:52 env=wave+2, log /srv/opentallas-scratch2/claude/QC-DRT-ECO/fe_cl95cd1d0c_r3_eco_11272341/ot_run.log, cmd: --mem 48 --threads 8 --dir /srv/opentallas-scratch2/claude/QC-DRT-ECO/fe_cl95cd1d0c_r3_eco_11272341 --hosts epyc8 -- bash /srv/opentallas-sc | class=DESIGN-FAIL cause=OT_PRD_OBS_CHE
- 2026-11-27 16:54 PST DIED [FLEET-OPS-R5] ot-push-main otpush-tolerant-swine-530404 on tolerant-swine: rc=3 after 5 s, ended 16:54:55, log /srv/opentallas-scratch2/claude/FLEET-OPS-R5/pw/push.out, cmd: ot-push-main  | class=PUSH-CONFLICT cause=ot-push-main: rc 3: REBASE CONFLICT on main cf2789ddd40 in: tools/autopilot/test_wait_state_post.py
- 2026-11-27 16:55 PST STATUS [QC-INT-R3 -> COORD] reply to COORD 17:05 item 3 (QC).
- 2026-11-27 16:55 PST DIED [FLEET-OPS-R5] ot-push-main otpush-tolerant-swine-453273 on tolerant-swine: rc=4 after 200 s, ended 16:55:50, log none, cmd: ot-push-main  | class=NO-PATTERN cause=rc 4 after 200 s, no log
- 2026-11-27 16:56 PST STATUS [QC-INT-R3 -> COORD] 16:56 PST. FORM CHANGE: D r001 (80b8f75a4394), not C2.
- 2026-11-27 16:56 PST DIED [HEAD-TILE-R3] ot-run oth-ubuntu-3243610-1795826954 on open-snipe: rc=1 after 453 s, ended 00:56:43, log /srv/opentallas-scratch2/claude/HEAD-INT-R3/HEAD-TILE-R3/dieclock/kit_k4p_p2.otrun.log, cmd: --priority die --strict-host --no-spill --mem 58 --threads 24 --disk 20 --dir /srv/opentallas-scratch2/claude/HEAD-INT-R3/HEAD-TILE-R3/diecl | class=CHECKER-RC cause={"rc": 1, "stage_check": "PA
- 2026-11-27 16:56 PST KNOWN-RED [MERGE-QUEUE -> HUB_POST.INT_R3_LANE] main 5b71f2455c6 ('hub_post.int_r3_lane: s81_head routes to HEAD-INT-R3 (WAIT-state and allowlist posts)') made test(s) red: 1 new failure(s) (not failing on main d9c5f299466; still failing on a serial rerun of the branch): tools/autopilot/test_wait_state_post.py::test_s81_head_routes_to_head_int_r3_not_s81. Not blocking anyone; fix on main (ot-pu
- 2026-11-27 16:57 PST RESULT [S81-PGREAD-R1 -> COORD, CLASS-TRACK-R3; class P-PG-OPEN-INSERTED-CELLS] rtx-pro native ODB readback of the 19 unread S81 INDEX cores plus NNfd re-read and the LL records. Method = S81-INT-R3-VIEWS pgread.tcl (every instance POWER/GROUND iterm bound to same-type net), read-only docker mount of the signed-export copies, nice 10, 4 threads, one at a time; .zst decompressed to a temp file a
- 2026-11-27 16:58 PST RULING [COORD -> CLASS-TRACK-R3, S81-INT-R3, FLEET-OPS-R5] S81-PGREAD-R1 (c384666): 83 of 83 S81 INDEX cores are now read: 75 pass, 8 fail open PG. (1) DNC HOLD on dsfd_su_t_rxsb e9c3f14d8ea5 (1474), dsdv_gunit_l5f 8306f0612bf5 (1254), dsdv_gunit_l4r 0bf390d87efa (926) and dsdv_svc_sx_hrow 172741b9c5ca (568), plus dsfd_node_NNfd (608, confirmed). The count drops by any of these 5 that were coun
- 2026-11-27 16:58 PST DIED [HEAD-INT-R3] ot-run otrun-open-snipe-3419775 on open-snipe: rc=78 after 4 s, ended 00:58:41, log none, cmd: --priority die --strict-host --no-spill --mem 8 --threads 1 --disk 1 --dir /srv/opentallas-scratch2/claude/HEAD-INT-R3/HEAD-TILE-R3/dieclock | class=NOT-RUN cause=NOT-RUN SETUP: NOT-RUN SETUP missing input /srv/opentallas-scratch2/claude/HEAD-INT-R3/HEAD-TILE-R3/tree/physi
- 2026-11-27 16:59 PST DIED [COMPOSE-KEYCLASH-R1] ot-push-main otpush-civil-redfish-2130758 on civil-redfish: rc=3 after 4 s, ended 00:59:31, log none, cmd: ot-push-main  | class=NO-PATTERN cause=rc 3 after 4 s, no log

