# COORD snapshot 2026-11-27 17:30 PST

Generated every 15 min by ~/coord/bin/coord_snapshot.py (cron on intel2, no LLM). It is the freshest COORD state if Claude stops on a limit. Read it right after ~/coord/CODEX-HANDOFF.md (the hand-written method and lane table) and ~/coord/lanes/handoff/<LANE>.md (each lane's own state). Facts only; the queue is the source.

## main and the merge lane
- origin/main: b8d89ecb9bae
- 2026-11-27 09:50 PST MERGED [MERGE-QUEUE -> CLASS-OWNERS-R2] native-sram-path-authority@09079a689ee: nothing to land, 09079a689ee is an ancestor of main 81f48be7e98.
- 2026-11-27 09:50 PST MERGED [MERGE-QUEUE -> CLASS-OWNERS-R2] relay-seat-stop-runtime@08917427de8: nothing to land, 08917427de8 is an ancestor of main 81f48be7e98.
- 2026-11-27 10:35 PST MERGED [MERGE-QUEUE -> LEC-R2] lec-uneven-memory@5a7729a9c34: nothing to land, 5a7729a9c34 is an ancestor of main 3d76ea4f296.

## READY/ASK with no later COORD post naming them (0, heuristic: check each)

## Lane handoff files (age) and last queue post
- CLAUDE-RESUME-1127: handoff 507 min old; last post none in recent queue
- EXPLORER-STORE-R1: handoff 1002 min old; last post 2026-11-26 22:07 STATE
- HEAD-INT-R2-HOSTW-CAPACITY-1127: handoff 820 min old; last post none in recent queue
- PCC-B1-LANE-SPEC: handoff 370 min old; last post none in recent queue
- PREPARED-PUBLICATION-PLACE: handoff 1097 min old; last post none in recent queue
- PUBLISH-GATE: handoff 1002 min old; last post 2026-11-26 23:27 READY
- QC-ALLFIX-COLL: handoff 828 min old; last post none in recent queue
- ROM-WEIGHTS-1119: handoff 1002 min old; last post 2026-11-26 23:36 STATE

## Live lanes (queue posts + LANE-STATUS + agent_ids)
- LANE-STATUS rows 195; agent_ids.tsv 132 (lists many old lanes, so liveness here = posted in the last 3 h and not stood-down): 38 live
- FLEET-OPS-R agent ? last post 2026-11-27 17:28 ALERT
- NOPROG-FIX-1115 agent ? last post 2026-11-27 17:22 STATE
- CBC-RULES-1119 agent ? last post 2026-11-27 17:17 HOURLY
- qwen_compute agent ? last post 2026-11-27 17:14 KIT-WAVE
- HOLDGEN-1115 agent ? last post 2026-11-27 17:14 ALERT
- s81_head agent ? last post 2026-11-27 17:14 KIT-WAVE
- HEAD-TILE-R3 agent ? last post 2026-11-27 17:13 DIED
- S81-INT-R3 agent ? last post 2026-11-27 17:11 DIED
- KIT-WAVE agent ? last post 2026-11-27 17:07 WAIT-STATE
- QC-INT-R3 agent ? last post 2026-11-27 17:06 STATUS
- HEAD-INT-R3 agent ? last post 2026-11-27 17:05 REVIEW
- QC-R3-VREVIEW agent ? last post 2026-11-27 17:03 REVIEW
- HEAD-PROBE-R3 agent ? last post 2026-11-27 17:02 RESULT
- HEAD-CASEAM-R4 agent ? last post 2026-11-27 17:02 RESULT
- SMELL-WATCH agent ? last post 2026-11-27 17:00 RENDER
- COMPOSE-KEYCLASH-R1 agent ? last post 2026-11-27 17:00 DIED
- S81-PGREAD-R1 agent ? last post 2026-11-27 16:57 RESULT
- MERGE-QUEUE agent ? last post 2026-11-27 16:56 KNOWN-RED
- FLEET-OPS-R5 agent ? last post 2026-11-27 16:55 DIED
- QC-DRT-ECO agent ? last post 2026-11-27 16:54 DIED
- CLASS-TRACK-R3 agent ? last post 2026-11-27 16:53 RESULT
- FLOW-HEALTH-1 agent ? last post 2026-11-27 16:40 NEEDS-ACTION
- QC-R3-SULANE agent ? last post 2026-11-27 16:33 DIED
- LEC-R3 agent ? last post 2026-11-27 16:27 RESULT
- QC-R3-DIEGAP agent ? last post 2026-11-27 16:20 ROW-READY
- QC-R3-STA agent ? last post 2026-11-27 16:15 ROW-READY
- PROGRESS-WATCH agent ? last post 2026-11-27 15:36 ALERT
- mq1 agent ? last post 2026-11-27 15:32 DIED
- NOPROG-WATCHDOG agent ? last post 2026-11-27 15:30 STATE
- kv-int-r3 agent ? last post 2026-11-27 15:24 DIED
- AUTO-CLEAN agent ? last post 2026-11-27 15:09 INFO
- HEAD-EAST-R4 agent ? last post 2026-11-27 15:05 CLASS-REQUEST
- KV-INT-R3 agent ? last post 2026-11-27 15:04 NOTE
- S81-INT-R3-VIEWS agent ? last post 2026-11-27 15:00 RESULT
- KV-INT-R3/PV-RESET agent ? last post 2026-11-27 14:56 RESULT
- PLAN-GATE-PRE-1115 agent ? last post 2026-11-27 14:54 NEEDS-ACTION
- CLASS-OWNERS-R3 agent ? last post 2026-11-27 14:42 DIED
- FAIL-ROUTE-1115 agent ? last post 2026-11-27 14:38 HANDOVER

## Per-die plan shas and gate states (RELEASE_TREE.md die clock / plan rows)
- [ ] S81.CLK Die clock 12.25 · S81 / DIE-S81-65 · PASS (kits pending) · plan dd2cd280def6 approved 10-31 21:4x: clock-tree GRT0, TT +49.70, CA 0/2330 (older pass counts, OWNER); retained FF +10.75 on 65420 pairs; remaining real-view hold pairs measured as kit

## Failure breakdown (tools/failure_breakdown.py)
## FAILURES · unsigned cores and types by class (auto, 2026-11-27 17:30 PST)
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
### STALE · unsigned plan cores/types with no live job and no kit-wave row change >= 6 h: 1 current-event (+7 on a superseded plan block, not counted) (live check: ps/systemd/docker on all hosts; wave state: hub; full list lanes/STALE.tsv)
- [ ] STALE.QC 7 (cores 0, types 7) · by owner: KIT-WAVE-1 3, QC-PLAN 2, unowned 1, QC-STALE-GEOM 1
  - type sle_ctl__cla4f6f12f · CANCELLED geom QUEUE-CANCELLED @ 2026-11-23 11:21 (102.2h) · owner QC-PLAN
  - type sle_fw_v2__cl69f5e854 · CANCELLED geom QUEUE-CANCELLED @ 2026-11-23 17:19 (96.2h) · owner QC-PLAN
  - type slw_fw_v1__clf51c11d8__cl592e3d37 · CANCELLED geom GHOST @ 2026-11-24 11:42 (77.8h) · owner unowned
  - type slw_fw_v3 · CANCELLED geom SUPERSEDED @ 2026-11-24 11:50 (77.7h) · owner KIT-WAVE-1
  - type slw_fe_v1__clfe325744__cl08d14f0d · CANCELLED geom SUPERSEDED @ 2026-11-24 20:33 (69h) · owner QC-STALE-GEOM
  - type native59 · CANCELLED geom SUPERSEDED @ 2026-11-25 19:34 (45.9h) · owner KIT-WAVE-1
  - type coll_ucie · CANCELLED geom QUEUE-CANCELLED @ 2026-11-26 09:19 (32.2h) · owner KIT-WAVE-1
- [ ] STALE.KV 1 (cores 0, types 1) · by owner: FAM-KV-HUBC-SYSC-R2 1
  - type kv3_sys_c · CANCELLED geom SUPERSEDED @ 2026-11-23 20:57 (92.6h) · owner FAM-KV-HUBC-SYSC-R2
### TOOLS-LAG · die tool fixes missing from the pinned trees
- TOOLS-LAG qwen_compute 365 commits / missing none
- TOOLS-LAG qwen_kvsys 402 commits / missing none
- TOOLS-LAG s81_head 0 commits / missing none
### TAP-INSERTION · measured per-tap insertion after CTS (advisory)
- TAP-INSERTION qwen_compute: 4733 taps in 45 types, 127 over 1650 sinks; insertion max 696 ps (p50 269, p90 284), skew max 176 ps; oversized taps: ins max 340 ps, skew max 90 ps
- TAP-INSERTION qwen_kvsys: 596 taps in 6 types, 17 over 1650 sinks; insertion max 516 ps (p50 258, p90 289), skew max 208 ps; oversized taps: ins max 412 ps, skew max 100 ps
- TAP-INSERTION s81: 3591 taps in 55 types, 130 over 1650 sinks; insertion max 1000 ps (p50 466, p90 498), skew max 313 ps; oversized taps: ins max 838 ps, skew max 175 ps
- TAP-INSERTION s81_head: 506 taps in 10 types, 9 over 1650 sinks; insertion max 613 ps (p50 458, p90 468), skew max 171 ps; oversized taps: ins max 466 ps, skew max 62 ps

## Host load and disk (latest HOST-REPORT, this host df/uptime)
    HOST-REPORT 2026-11-27 17:05 | tolera L12.49/112 units0 free830G | key-ca L13.75/112 units4 free274G | dear-c L2.66/128 units0 free353G | loved- L9.60/96 units3 free249G | outgoi L14.77/96 units1 free272G | renewe L2.12/96 units0 free1368G | civil- L3.49/96 units0 free1210G | viable L3.04/96 units1 free1617G | HOST-CAPS ok (9 owned caps); expiring (renew or revert): intel2:LOAD_CAP_FACTOR=1.2 owner=FLOW-FLEET-R2 expires=2026-12-06T00:00Z (190.9 h left); intel1:LOAD_CAP_FACTOR=1.2 owner=FLOW-FLEET-R2 expires=2026-12-06T00:00Z (190.9 h left); epyc2:LOAD_CAP_FACTOR=1.2 owner=FLOW-FLEET-R2 expires=2026-12-06T00:00Z (190.9 h left); epyc7:LOAD_CAP_FACTOR=1.2 owner=FLOW-FLEET-R2 expires=2026-12-06T00:00Z (190.9 h left); epyc8:LOAD_CAP_FACTOR=1.2 owner=FLOW-FLEET-R2 expires=2026-12-06T00:00Z (190.9 h left); epyc9:LOAD_CAP_FACTOR=1.2 owner=FLOW-FLEET-R2 expires=2026-12-06T00:00Z (190.9 h left); e
    Filesystem      Size  Used Avail Use% Mounted on | /dev/nvme1n1p2  468G  336G  109G  76% /
    17:30:17 up 34 days, 13:10, 147 users,  load average: 9.32, 13.84, 13.40

## ot-run status
    ot-run status: epyc2 admits 918 GB (avail 975, reserve 0, fresh 0, peak 0) load 10/128 run 1 threads 16/128 root 91% scratch 350 GB
    intel1 admits 899 GB (avail 977, reserve 0, fresh 0, peak 277.4) load 7/112 run 3 threads 96/112 root 21% scratch 270 GB
    localhost admits 822 GB (avail 950, reserve 0, fresh 0, peak 46.8) load 9/112 run 2 threads 30/112 root 76% scratch 822 GB
    epyc7 admits 859 GB (avail 937, reserve 0, fresh 0, peak 1.1) load 11/96 run 6 threads 164/96 root 35% scratch 245 GB
    epyc8 admits 877 GB (avail 944, reserve 0, fresh 0, peak 11.4) load 10/96 run 3 threads 198/96 root 51% scratch 303 GB
    epyc9 admits 939 GB (avail 987, reserve 0, fresh 0, peak 0) load 2/96 run 0 threads 47/96 root 40% scratch 1368 GB
    epyc10 admits 937 GB (avail 985, reserve 0, fresh 0, peak 0) load 1/96 run 0 threads 138/96 root 52% scratch 1209 GB
    epyc11 admits 939 GB (avail 988, reserve 0, fresh 0, peak 0) load 2/96 run 1 threads 144/96 root 7% scratch 1614 GB
    epyc12 admits 914 GB (avail 963, reserve 0, fresh 0, peak 73.6) load 65/96 run 1 threads 48/96 root 37% scratch 759 GB
    next 16-thread 32 GB job -> epyc2

## KIT-WAVE (autopilot log, last 6)
    2026-11-27 17:22:24 PST AUTOPILOT: KIT-WAVE WAIT-PLAN-VISUAL: BAD fresh plan image verdict for qwen_compute/sle_st_b_v2__cl14c98df5__pvcd986c42 form 1df1f5065095c1e939d2171d39f71044bad2c29eb0764a574e2
    2026-11-27 17:22:58 PST AUTOPILOT: KIT-WAVE LAUNCH-KEEP qwen_compute/sle_st_b_v1__pv0e7b1dcc: active producer kw-qwenco-slestbv1pv0e7b1dcc-1-4173
    2026-11-27 17:23:42 PST AUTOPILOT: KIT-WAVE HOLD-TERM qwen_compute: 57 hold(s), 0 without owner/eta (HOLD-NO-TERM), 0 overdue [+4 identical line(s) in the last hour]
    2026-11-27 17:23:42 PST AUTOPILOT: KIT-WAVE HOLD-TERM qwen_kvsys: 46 hold(s), 0 without owner/eta (HOLD-NO-TERM), 46 overdue: kv3_hgi [owner KV-ALLFIX] eta 11-24 11:00; kv3_hgi_v7 [owner KV-ALLFIX] et
    2026-11-27 17:23:42 PST AUTOPILOT: KIT-WAVE HOLD-AUDIT HELD-BUT-LAUNCHED=0 HOLD-LEAK=0 TERM-UNREACHABLE=0 TERM-VARIANT=0 HOLD-SUPERSEDED=0 HOLD-ZERO-MATCH=0 PROOF-HELD=0 PILOT-DEADLOCK=0
    2026-11-27 17:24:04 PST AUTOPILOT: UNDER-USE HELD SKIP-HELD 6: s81/serdes__t3 1 [owner S81-SERDES-TAPSKEW, 124.5 h, eta 11-25 00:30, FLAGGED OVERDUE]; s81/serdes__t16 1 [owner S81-SERDES-TAPSKEW, 124.

## Last 60 queue posts (cut to 420 chars; full text in the queue)
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
- 2026-11-27 17:00 PST DIED [COMPOSE-KEYCLASH-R1] ot-push-main otpush-civil-redfish-2145899 on civil-redfish: rc=3 after 5 s, ended 01:00:27, log none, cmd: ot-push-main  | class=NO-PATTERN cause=rc 3 after 5 s, no log
- 2026-11-27 17:00 PST WAIT-STATE [KIT-WAVE -> HEAD-INT-R3] WAIT-PLAN-VISUAL s81_head/hd_lep0N: missing lanes/PLAN-VISUAL-REVIEW.tsv row for form 6a0b90de13abfb8ba3c0abe6d273fda234934bff5704b17f8eb5b431d1a4b88a (request /home/ubuntu/coord/autopilot/private_specs/HEAD-EAST-R4/s81_head_hd_lep0N_1127165959/plan_visual_request.json) (a GOOD verdict on the exact plan form); reviewer lane HEAD-INT-R3 (fallback INT-R3); rea
- 2026-11-27 17:00 PST RENDER [SMELL-WATCH -> HEAD-INT-R3, HEAD-PROBE-R3; cc HEAD-INT-R3] 1 checkpoint render(s) started: hd_st_n4 PLACE-GP on epyc11: epyc11:/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81_head/kit-wave/s81_head/head_rp21z20NF15f_r18w12_1126/private/HEAD-PROBE-R3/hd_st_n4_1128003833/gen/hd_st_n4/vis_review/place-gp-1127-1700PST (floorplan.png, density.png, SMELL.txt with the GRT per-layer ov
- 2026-11-27 17:02 PST RESULT [HEAD-PROBE-R3] C-TAP-REACH-3 CTS probes (CASEAM, plan 27eee0a2f48b, rt d9b7ec5dc7f8, epyc11) all 3 types done. OT_TAP_SPAN over-300 taps: hd_st_k5 15/36 (max 482) -> 0/60 (max 296); hd_st_turn 9/36 (485) -> 0/46 (275); hd_st_n4 8/31 (398) -> 0/39 (299). Setup_ws baseline->new: k5 +123.30 -> +95.25 (tap-insertion on the u_cland_origin input-port path, new tap clk_t59 319 ps), turn +123.8
- 2026-11-27 17:02 PST RESULT [HEAD-CASEAM-R4] C-TAP-REACH-3 CTS qualification complete (HEAD-PROBE-R3 probes, plan 27eee0a2f48b, kit-local clock, place+CTS PASS on all three): OT_TAP_SPAN hd_st_k5 15/36 over (max 482) -> 0/60 (max 296); hd_st_turn 9/36 (485) -> 0/46 (275); hd_st_n4 8/31 (398) -> 0/39 (299). Tool model 295.8 / 274.6 / 299.5 vs CTS 296 / 275 / 299: within 0.5 um. Timing FF pre-repair: k5 setup_ws +123
- 2026-11-27 17:03 PST REVIEW [QC-R3-VREVIEW -> QC-INT-R3; cc COORD, QC-R3-TAPLOAD, QC-R3-VISUAL] classes C-TAP-LOAD, C-STREET, C-BANK-PILE, C-LEG405, C-PIN-REG-REACH, C-RST-RELAY-REACH. Independent Fable post-place review of the 15 WAIT-VISUAL kits on qc_2100_combined_77f2_1126, attempt_1, exact 3_place (layout.png, density.png, auto_geom.png opened for every kit). 15 GEOM VERDICT lines with kit=, image, odb_sha256 
- 2026-11-27 17:04 PST DIED [HEAD-TILE-R3] ot-run oth-ubuntu-3402581-1795827455 on open-snipe: rc=1 after 395 s, ended 01:04:07, log /srv/opentallas-scratch2/claude/HEAD-INT-R3/HEAD-TILE-R3/dieclock/kit_k4p_p3.otrun.log, cmd: --priority die --strict-host --no-spill --mem 58 --threads 24 --disk 20 --dir /srv/opentallas-scratch2/claude/HEAD-INT-R3/HEAD-TILE-R3/diecl | class=CHECKER-RC cause={"rc": 1, "stage_check": "PA
- 2026-11-27 17:04 PST STATUS [QC-INT-R3 -> COORD; cc FLEET-OPS-R5] 17:04 PST. QC WAIT-VISUAL: all 15 post-place kits reviewed (77f2 event). Reviewer: QC-R3-VREVIEW (Fable). Cross-check: auto_visual_review.decide, read-only, ACCEPT on all 15. Receipts: GEOM-REVIEW.md, hub 17cd17366c8.
- 2026-11-27 17:05 PST REVIEW [HEAD-INT-R3 -> COORD; cc HEAD-FORM-R3, HEAD-PART-R3, KIT-WAVE] Placed-render review of the 9 route-held W12f rows (event head_rp21z20NF15f_r18w12_1126 a1; the W13q/W13r only_items whose blocks are unchanged). Independent Fable review via HEAD-PROBE-R3: epyc12 HEAD-INT-R3/reviews/W12F_PLACED_9_20261128.md. Released on the placed-visual condition (8): hd_spn_wshim_tx GOOD; hd_st_m, hd_st_
- 2026-11-27 17:06 PST DIED [HEAD-TILE-R3] ot-run oth-ubuntu-3443707-1795827578 on open-snipe: rc=1 after 388 s, ended 01:06:03, log /srv/opentallas-scratch2/claude/HEAD-INT-R3/HEAD-TILE-R3/dieclock/kit_k4p_p4.otrun.log, cmd: --priority die --strict-host --no-spill --mem 58 --threads 24 --disk 20 --dir /srv/opentallas-scratch2/claude/HEAD-INT-R3/HEAD-TILE-R3/diecl | class=CHECKER-RC cause={"rc": 1, "stage_check": "PA
- 2026-11-27 17:06 PST WAIT-STATE [KIT-WAVE -> QC-INT-R3] WAIT-FORM qwen_compute/sle_hc2__cl9c4c4509__clf60c5152__pv0d63d22b: missing a changed form fingerprint for qwen_compute/sle_hc2__cl9c4c4509__clf60c5152__pv0d63d22b, or a lanes/GEOM-REVIEW.md GOOD / OK / ISSUES-ACCEPT line for the rebuilt form; reviewer lane QC-INT-R3 (fallback INT-R3); reason: WAIT-FORM: exact kit epyc7:/srv/opentallas-scratch2/claude/kw43-wav
- 2026-11-27 17:06 PST WAIT-STATE [KIT-WAVE -> QC-INT-R3] WAIT-FORM qwen_compute/sle_st_b_v1__pv0e7b1dcc: missing a changed form fingerprint for qwen_compute/sle_st_b_v1__pv0e7b1dcc, or a lanes/GEOM-REVIEW.md GOOD / OK / ISSUES-ACCEPT line for the rebuilt form; reviewer lane QC-INT-R3 (fallback INT-R3); reason: WAIT-FORM: exact kit epyc7:/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_
- 2026-11-27 17:06 PST STATUS [QC-INT-R3 -> COORD, KV-INT-R3] 17:06 PST. QC repoint CTS phase probes: both FAIL on the stock window, so the repoint is OUT of tonight's form (14:47 rule).
- 2026-11-27 17:06 PST WAIT-STATE [KIT-WAVE -> QC-INT-R3] WAIT-FORM qwen_compute/sle_st_b_v1__pvc5a85fd4__pv7b7fafb4: missing a changed form fingerprint for qwen_compute/sle_st_b_v1__pvc5a85fd4__pv7b7fafb4, or a lanes/GEOM-REVIEW.md GOOD / OK / ISSUES-ACCEPT line for the rebuilt form; reviewer lane QC-INT-R3 (fallback INT-R3); reason: WAIT-FORM: exact kit intel1:/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qw
- 2026-11-27 17:07 PST WAIT-STATE [KIT-WAVE -> QC-INT-R3] WAIT-FORM qwen_compute/sle_stm_v2__cl7b3062fa: missing a changed form fingerprint for qwen_compute/sle_stm_v2__cl7b3062fa, or a lanes/GEOM-REVIEW.md GOOD / OK / ISSUES-ACCEPT line for the rebuilt form; reviewer lane QC-INT-R3 (fallback INT-R3); reason: WAIT-FORM: exact kit epyc8:/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_co
- 2026-11-27 17:07 PST WAIT-STATE [KIT-WAVE -> QC-INT-R3] WAIT-FORM qwen_compute/slw_fw_v2__cl8537f156: missing a changed form fingerprint for qwen_compute/slw_fw_v2__cl8537f156, or a lanes/GEOM-REVIEW.md GOOD / OK / ISSUES-ACCEPT line for the rebuilt form; reviewer lane QC-INT-R3 (fallback INT-R3); reason: WAIT-FORM: exact kit intel1:/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_com
- 2026-11-27 17:07 PST WAIT-STATE [KIT-WAVE -> QC-INT-R3] WAIT-FORM qwen_compute/slw_fw_v2__cl8f84514c: missing a changed form fingerprint for qwen_compute/slw_fw_v2__cl8f84514c, or a lanes/GEOM-REVIEW.md GOOD / OK / ISSUES-ACCEPT line for the rebuilt form; reviewer lane QC-INT-R3 (fallback INT-R3); reason: WAIT-FORM: exact kit intel1:/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_com
- 2026-11-27 17:07 PST WAIT-STATE [KIT-WAVE -> QC-INT-R3] WAIT-FORM qwen_compute/slw_sc_v1__cl64543eaf__cl5e017c6f: missing a changed form fingerprint for qwen_compute/slw_sc_v1__cl64543eaf__cl5e017c6f, or a lanes/GEOM-REVIEW.md GOOD / OK / ISSUES-ACCEPT line for the rebuilt form; reviewer lane QC-INT-R3 (fallback INT-R3); reason: WAIT-FORM: exact kit intel1:/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_c
- 2026-11-27 17:11 PST DIED [S81-INT-R3] ot-run oth-ubuntu-3048977-1795826184 on open-snipe: rc=2 after 2104 s, ended 01:11:25, log /srv/opentallas-scratch2/claude/S81-INT-R3/f2100/bindX_formD3.otrun.log, cmd: --priority die --hosts epyc12 --disk 120 --mem 300 --threads 48 --dir /srv/opentallas-scratch2/claude/S81-INT-R3/f2100 -- env RTP=779cd222ef | class=NO-PATTERN cause=rc 2 after 2104 s; the log holds only ot-run
- 2026-11-27 17:12 PST DIED [HEAD-TILE-R3] ot-run oth-ubuntu-3556607-1795827946 on open-snipe: rc=1 after 390 s, ended 01:12:14, log /srv/opentallas-scratch2/claude/HEAD-INT-R3/HEAD-TILE-R3/dieclock/kit_k4p_p5.otrun.log, cmd: --priority die --strict-host --no-spill --mem 58 --threads 24 --disk 20 --dir /srv/opentallas-scratch2/claude/HEAD-INT-R3/HEAD-TILE-R3/diecl | class=CHECKER-RC cause={"rc": 1, "stage_check": "PA
- 2026-11-27 17:13 PST DIED [HEAD-TILE-R3] ot-run oth-ubuntu-3597860-1795828053 on open-snipe: rc=1 after 386 s, ended 01:13:56, log /srv/opentallas-scratch2/claude/HEAD-INT-R3/HEAD-TILE-R3/dieclock/kit_k4p_p6.otrun.log, cmd: --priority die --strict-host --no-spill --mem 58 --threads 24 --disk 20 --dir /srv/opentallas-scratch2/claude/HEAD-INT-R3/HEAD-TILE-R3/diecl | class=CHECKER-RC cause={"rc": 1, "stage_check": "PA
- 2026-11-27 17:14 PST KIT-WAVE [qwen_compute] -> QC die owner (DIE-QC-103): 19 event(s): sle_hc2__cl9c4c4509__clf60c5152__pv0d63d22b AUTO-GEOM PASS, ROUTE held: WAIT-FORM: exact kit epyc7:/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/qc_2100_combined_77f2_1126/items/sle_hc2__cl9c4c4509__clf60c5152__pv0d63d22b/gen/sle_hc2__cl9c4c4509__clf60c5152__pv0d63d22b visual verdict BAD
- 2026-11-27 17:14 PST KIT-WAVE [s81_head] -> HEAD die owner (HEAD-100): 15 event(s): hd_ctl_n AUTO-GEOM PASS, ROUTE held: WAIT-FORM: exact kit intel1:/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81_head/kit-wave/s81_head/head_rp21z20NF15f_r18w12_1126/items/hd_ctl_n/gen/hd_ctl_n visual verdict BAD; rebuild on a changed form; hd_ctl_e AUTO-GEOM PASS GEOM-ADVISORY aspect,empty,fill,pin_reg_p90: OWNER 11-03 tar
- 2026-11-27 17:14 PST HOLD-LEAK [-> HEAD die owner (HEAD-100)] s81_head/HEAD-W12F-ROUTE-HD-HOST-N: 1 launched row(s) match a hold record that blocks nothing on this die (stops_off): record HEAD-W12F-ROUTE-HD-HOST-N key hd_host_n (launched; hold_items does not carry it); items hd_host_n. Hold them with dies.s81_head.hold_items (kit_wave_edit refuses new records here).
- 2026-11-27 17:14 PST HOLD-LEAK [-> HEAD die owner (HEAD-100)] s81_head/HEAD-W12F-ROUTE-HD-SPN-WSHIM-TX: 1 launched row(s) match a hold record that blocks nothing on this die (stops_off): record HEAD-W12F-ROUTE-HD-SPN-WSHIM-TX key hd_spn_wshim_tx (launched; hold_items does not carry it); items hd_spn_wshim_tx. Hold them with dies.s81_head.hold_items (kit_wave_edit refuses new records here).
- 2026-11-27 17:14 PST HOLD-LEAK [-> HEAD die owner (HEAD-100)] s81_head/HEAD-W12F-ROUTE-HD-ST-N3-TRANSIT: 1 launched row(s) match a hold record that blocks nothing on this die (stops_off): record HEAD-W12F-ROUTE-HD-ST-N3-TRANSIT key hd_st_n3_transit (launched; hold_items does not carry it); items hd_st_n3_transit. Hold them with dies.s81_head.hold_items (kit_wave_edit refuses new records here).
- 2026-11-27 17:14 PST HOLD-LEAK [-> HEAD die owner (HEAD-100)] s81_head/HEAD-W12F-ROUTE-HD-ST-N3-TURN: 1 launched row(s) match a hold record that blocks nothing on this die (stops_off): record HEAD-W12F-ROUTE-HD-ST-N3-TURN key hd_st_n3_turn (launched; hold_items does not carry it); items hd_st_n3_turn. Hold them with dies.s81_head.hold_items (kit_wave_edit refuses new records here).
- 2026-11-27 17:14 PST HOLD-LEAK [-> HEAD die owner (HEAD-100)] s81_head/HEAD-W12F-ROUTE-HD-ST-STR: 1 launched row(s) match a hold record that blocks nothing on this die (stops_off): record HEAD-W12F-ROUTE-HD-ST-STR key hd_st_str (launched; hold_items does not carry it); items hd_st_str. Hold them with dies.s81_head.hold_items (kit_wave_edit refuses new records here).
- 2026-11-27 17:14 PST HOLD-LEAK [-> HEAD die owner (HEAD-100)] s81_head/HEAD-W12F-ROUTE-HD-TURN-A: 1 launched row(s) match a hold record that blocks nothing on this die (stops_off): record HEAD-W12F-ROUTE-HD-TURN-A key hd_turn_a (launched; hold_items does not carry it); items hd_turn_a. Hold them with dies.s81_head.hold_items (kit_wave_edit refuses new records here).
- 2026-11-27 17:14 PST ALERT [HOLDGEN-1115 -> COORD, WAVE-HOLDS-1115] hold audit {'HOLD-LEAK': 6}: HOLD-LEAK s81_head/HEAD-W12F-ROUTE-HD-HOST-N x1: record HEAD-W12F-ROUTE-HD-HOST-N key hd_host_n (launched; hold_items does not carry it) items hd_host_n; HOLD-LEAK s81_head/HEAD-W12F-ROUTE-HD-SPN-WSHIM-TX x1: record HEAD-W12F-ROUTE-HD-SPN-WSHIM-TX key hd_spn_wshim_tx (launched; hold_items does not carry it) items hd_spn
- 2026-11-27 17:17 PST HOURLY [CBC-RULES-1119 -> COORD; cc S81-INT-R3, QC-PLAN-R3, KV-D23-COMPOSE, FABLE-FIX-HEAD-MESH-O] CBC-FALLBACK unsigned S81 119 types; CBC-FALLBACK (r713: >= 2 failed design fix rounds -> close-by-construction form; die owner folds tools/die_plan/cbc_pass.py rows into the next event): S81 col_h9_r1: 60 unsigned (col_h9_r1__t1__cl49d7a23e__pv047ea3b3,col_h9_r1__t1__cl49d7a23e__pv0a45e191,col_h9
- 2026-11-27 17:22 PST STATE [NOPROG-FIX-1115 -> COORD] NOPROG hourly 2026-11-27 17:22 PST: 17 running jobs, PROGRESSING 16, PLATEAU 0, SLOW 1, NO-PROGRESS 0 (this table is advisory; the separate noprog.timer watchdog (noprog_watchdog.py) DOES ot-heavy-stop NO-PROGRESS jobs, per-host log ~/.local/state/noprog/actions.jsonl); table lanes/NOPROG.tsv
- 2026-11-27 17:28 PST ALERT [FLEET-OPS-R -> COORD] lane quota: HEAD-INT-R3 on intel1 wrote 172 GB in the last window (quota 150 GB/lane/6 h or 30 GB/1 h burst; alert only, nothing stopped); owner please prune or confirm
- 2026-11-27 17:28 PST ALERT [FLEET-OPS-R -> COORD] lane quota: kv-allfix on intel1 wrote 52 GB in the last window (quota 150 GB/lane/6 h or 30 GB/1 h burst; alert only, nothing stopped); owner please prune or confirm
- 2026-11-27 17:28 PST ALERT [FLEET-OPS-R -> COORD] lane quota: kv-int-r2 on intel1 wrote 52 GB in the last window (quota 150 GB/lane/6 h or 30 GB/1 h burst; alert only, nothing stopped); owner please prune or confirm
- 2026-11-27 17:28 PST ALERT [FLEET-OPS-R -> COORD] lane quota: s81-allfix-int on intel1 wrote 76 GB in the last window (quota 150 GB/lane/6 h or 30 GB/1 h burst; alert only, nothing stopped); owner please prune or confirm

