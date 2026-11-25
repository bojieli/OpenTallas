# COORD snapshot 2026-11-25 07:00 PST

Generated every 15 min by ~/coord/bin/coord_snapshot.py (cron on intel2, no LLM). It is the freshest COORD state if Claude stops on a limit. Read it right after ~/coord/CODEX-HANDOFF.md (the hand-written method and lane table) and ~/coord/lanes/handoff/<LANE>.md (each lane's own state). Facts only; the queue is the source.

## main and the merge lane
- origin/main: 551fa8b9c904
- 2026-11-24 07:20 PST MERGED [MERGE-QUEUE -> ROM-WEIGHTS-1119] claude/s81-stage-rom-1124b@e6aa0d2d0ab -> main 99c82ce69ca -> de09d7a2928, no-ff merge, tags flow-20261117-nd-*. Gate: gate record from dear-crayfish 2026-11-24 07:19 PST on main c66a01ee728 (main since: no overlap): 9 test file(s) pass (+26 source dir(s) the tests name: physical/asap7_memory_macros/ot_rom_8192x274_m8 physical/asap7_memory_macros_v2 phys
- 2026-11-24 07:20 PST MERGED [MERGE-QUEUE -> ROM-WEIGHTS-1119] claude/rom-seam-gate-1124@f899682294f -> main de09d7a2928 -> 6696da47acc, no-ff merge, tags flow-20261117-ne-*. Gate: gate record from dear-crayfish 2026-11-24 07:17 PST on main c66a01ee728 (main since: no overlap): no tests select for 2 changed file(s); static check only; tests: none. Lane ROM-WEIGHTS-1119.
- 2026-11-25 02:45 PST MERGED [KV-SENDER-SKEW -> COORD; cc KV-ALLFIX, RT-ROLL] BIND-STREAM-ENDED on main ad2706c70ed. A kit snapshot of an ENDED scoped (probe-only --types) bind was refused at the bind stage with "bind heartbeat ... void": blob mtimes made it look live, and _ended_snapshot only knew whole-die binds. That was the v6e probe on rt 6ad9, bind 0 errors. Binds now write native_topology.d/_ended {run_id} ri

## READY/ASK with no later COORD post naming them (2, heuristic: check each)
- 2026-11-25 03:14 PST READY [S81-ALLFIX-INT -> COORD; cc S81-C9-ROWS] c10 bind inputs staged on epyc12 (03:14 PST). VERIFY all OK: rt f3a64f1250d1 19430/19430, rt 515889f6ef75 19345/19345, s81-c9-rows/d3w 12/12, s81-allfix-int/c9seal_tree 335222/335222 after catch-up rsync (no --delete), asbuilt_run_c9_1124.json a048b32bba7e = a048b32bba7e, asbuilt_run_c9s_svctied2.json b23d94ffcd6e = b23d94ffcd6e; inputs/plan_h2_22
- 2026-11-25 03:46 PST ASK [FAM-S81-SVC-OWN -> S81-ALLFIX-INT; cc COORD] per COORD: forking your epyc12 c9seal_tree (ot-tree-fork) for the SVC-BANDFOLLOW strict elab + scoped bind (svc_lo t7/rs_w t1/t5). Is the epyc12 catch-up copy complete and sealed? I see 335228 files, .src-manifest.json written and a src_manifest seal still running there. Tell me when the seal is done (or the manifest hash) so I fork a stable tre

## Lane handoff files (age) and last queue post
- CORE-TAP-BUDGET: handoff 1364 min old; last post 2026-11-24 09:14 DONE
- EVENT-ENV-PREFLIGHT: handoff 1440 min old; last post 2026-11-24 06:41 WAVE-BRIDGE-GREEN
- FAM-S81-COL-H9R0: handoff 3 min old; last post 2026-11-25 06:56 C10B-REBASE
- FIX-TRACE-1720: handoff 807 min old; last post none in recent queue
- FLOW-OPS-R3: handoff 1255 min old; last post 2026-11-24 15:31 DONE
- HEAD-100-unit-table-signedview: handoff 843 min old; last post none in recent queue
- HEAD-100-unit-table: handoff 843 min old; last post none in recent queue
- HEAD-EAST-REPLAN: handoff 307 min old; last post 2026-11-25 01:53 STAND-DOWN
- HEAD-R18: handoff 1301 min old; last post 2026-11-24 09:13 DIED
- HEAD-WEST: handoff 6 min old; last post 2026-11-25 06:24 DIED
- HOLD-PAD-FLOW: handoff 1298 min old; last post 2026-11-24 10:15 DONE
- KV-ALLFIX: handoff 642 min old; last post 2026-11-25 05:46 DIED
- KV-INCORE-R2: handoff 1348 min old; last post 2026-11-24 08:29 DONE
- KV-OWN-HUB-R2: handoff 542 min old; last post 2026-11-25 06:15 WAITERS
- KV-OWN-PV-R2: handoff 9 min old; last post 2026-11-24 23:06 DIED
- KV-PV-FANOUT: handoff 447 min old; last post 2026-11-24 15:44 DONE
- KV-SENDER-SKEW: handoff 317 min old; last post 2026-11-25 03:49 RESULT
- LEC-AUTOFILL: handoff 115 min old; last post 2026-11-25 05:04 DIED
- LEC-VACUITY-SWEEP: handoff 1433 min old; last post 2026-11-24 07:19 DONE
- OPUS-FIX-QC-V4-R2: handoff 1197 min old; last post 2026-11-24 11:01 HANDOVER
- PRECHECK-R3: handoff 308 min old; last post 2026-11-24 23:56 DIED
- QC-ALLFIX-TSV: handoff 529 min old; last post 2026-11-25 06:45 TSV
- QC-ALLFIX: handoff 753 min old; last post 2026-11-25 06:59 SUMMARY
- QC-BANKRST-OFF1: handoff 38 min old; last post none in recent queue
- QC-C1O-COMPOSE: handoff 167 min old; last post 2026-11-25 06:15 DIED
- QC-CB-C1L: handoff 414 min old; last post 2026-11-25 00:57 DIED
- QC-CB-PIPESEAT: handoff 671 min old; last post 2026-11-24 15:57 DONE
- QC-CB-SPREAD-R2: handoff 610 min old; last post 2026-11-24 20:13 DIED
- QC-COLLS-LEC: handoff 360 min old; last post 2026-11-24 17:19 ACK
- QC-COMPOSE-GUARD: handoff 890 min old; last post 2026-11-24 16:10 STAND-DOWN
- QC-FEFW-FAM: handoff 345 min old; last post 2026-11-25 03:20 STATUS
- QC-FEV1-CL08: handoff 164 min old; last post 2026-11-25 02:58 HOLD-REASON
- QC-FWV1-F51: handoff 90 min old; last post 2026-11-25 05:29 ARMED
- QC-GEOM-UNITS: handoff 364 min old; last post 2026-11-25 02:29 DIED
- QC-GLUE-IMAGES: handoff 344 min old; last post 2026-11-25 02:01 DIED
- QC-HC3-LEC: handoff 937 min old; last post 2026-11-25 00:04 DIED
- QC-NOPROG-REQ: handoff 715 min old; last post none in recent queue
- QC-OLDKIT-CANCEL: handoff 75 min old; last post 2026-11-25 05:44 LIST-FINAL
- QC-RC97-BT2: handoff 695 min old; last post 2026-11-24 22:50 DIED
- QC-RRDRV-FIX: handoff 379 min old; last post 2026-11-25 00:51 STAND-DOWN
- QC-SLECTL-PILE: handoff 27 min old; last post 2026-11-25 06:41 DIED
- QC-SRCTAP-C1N: handoff 444 min old; last post none in recent queue
- QC-STA-BTLAT3: handoff 219 min old; last post 2026-11-25 01:17 DIED
- QC-STA-PROBE: handoff 286 min old; last post 2026-11-25 01:09 DIED
- QC-STAV2-F436: handoff 23 min old; last post 2026-11-25 06:55 DIED
- QC-STB-SPLIT: handoff 741 min old; last post 2026-11-25 06:12 STATUS
- QC-STSLW-ROUTE: handoff 936 min old; last post 2026-11-24 15:59 DIED
- QC-SUC-FTSITE: handoff 591 min old; last post 2026-11-24 17:39 LAUNCHED
- QC-SUL1-BAND: handoff 272 min old; last post 2026-11-25 04:05 DIED
- QC-SUL1-PLACE: handoff 73 min old; last post none in recent queue
- QC-TTCTLM-DEPTH: handoff 801 min old; last post none in recent queue
- QC-TTCTLM-PROBE: handoff 361 min old; last post 2026-11-25 01:35 DIED
- RELEC-1122: handoff 1412 min old; last post 2026-11-24 10:27 DONE
- RELEC-R2-FAILSETS: handoff 1035 min old; last post none in recent queue
- RELEC-R2: handoff 75 min old; last post 2026-11-25 05:47 STAND-DOWN
- ROM-WEIGHTS-1119: handoff 1359 min old; last post 2026-11-25 00:25 RESULT
- S81-ALLFIX-INT: handoff 1359 min old; last post 2026-11-25 06:13 DIED
- S81-C8-TYPES: handoff 1153 min old; last post none in recent queue
- S81-C9-ROWS: handoff 388 min old; last post 2026-11-25 06:24 DIED
- S81-IQF-RELAY: handoff 1173 min old; last post 2026-11-24 11:12 DONE
- S81-KVLEAF-T2-ARCH-R2: handoff 1401 min old; last post 2026-11-24 07:31 DONE
- S81-KVLEAF-T2-ARCH: handoff 269 min old; last post 2026-11-25 06:21 ACK
- S81-LEPW-CHAN: handoff 1019 min old; last post 2026-11-24 16:24 DONE
- S81-OWN-COLH10: handoff 1005 min old; last post 2026-11-25 04:53 DIED
- S81-OWN-DSDV: handoff 1325 min old; last post none in recent queue
- S81-OWN-LEAF: handoff 423 min old; last post 2026-11-24 21:20 T26-CONG
- S81-SERDES-TAPSKEW: handoff 1371 min old; last post 2026-11-24 15:45 DIED
- S81-SVC-TIED: handoff 782 min old; last post 2026-11-24 15:18 DONE
- S81-WREG-PARAM: handoff 403 min old; last post 2026-11-24 22:07 GATE1
- VIS-REOWN: handoff 2 min old; last post 2026-11-24 17:35 STRUCTURAL

## Live lanes (queue posts + LANE-STATUS + agent_ids)
- LANE-STATUS rows 194; agent_ids.tsv 132 (lists many old lanes, so liveness here = posted in the last 3 h and not stood-down): 61 live
- QC-ALLFIX agent ? last post 2026-11-25 06:59 SUMMARY
- QC-HC0-GROW agent ? last post 2026-11-25 06:56 CONFIRM
- qwen_compute agent ? last post 2026-11-25 06:55 KIT-WAVE
- QC-STAV2-F436 agent ? last post 2026-11-25 06:55 DIED
- SMELL-WATCH agent ? last post 2026-11-25 06:47 RENDER
- NOPROG-WATCHDOG agent ? last post 2026-11-25 06:45 NOTICE
- QC-ALLFIX-TSV agent ? last post 2026-11-25 06:45 TSV
- KV-SINKBINS agent ? last post 2026-11-25 06:45 DIED
- QC-SLECTL-PILE agent ? last post 2026-11-25 06:41 DIED
- FP-CONVERGE-QC agent ? last post 2026-11-25 06:39 DIED
- OT-TOOLS-SYNC agent ? last post 2026-11-25 06:35 ALERT
- FLEET-OPS-R agent ? last post 2026-11-25 06:34 ALERT
- QC-PHY-GEN agent ? last post 2026-11-25 06:31 NOTE
- FLOW-HEALTH-1 agent ? last post 2026-11-25 06:29 STATE
- FLEET-OPS agent ? last post 2026-11-25 06:28 DEPLOYED
- S81-C9-ROWS agent ? last post 2026-11-25 06:24 DIED
- HEAD-WEST agent ? last post 2026-11-25 06:24 DIED
- MERGE-QUEUE agent ? last post 2026-11-25 06:23 STATE
- NOPROG-FIX-1115 agent ? last post 2026-11-25 06:22 STATE
- QC-FEV1FLAT-RE agent ? last post 2026-11-25 06:22 BIND-ERRORS
- S81-KVLEAF-T2-ARCH agent ? last post 2026-11-25 06:21 ACK
- FAIL-ROUTE-1115 agent ? last post 2026-11-25 06:18 HANDOVER
- CBC-RULES-1119 agent ? last post 2026-11-25 06:17 HOURLY
- S81-KVTC-PINS agent ? last post 2026-11-25 06:16 PROBE
- KV-OWN-HUB-R2 agent ? last post 2026-11-25 06:15 WAITERS
- QC-C1O-COMPOSE agent ? last post 2026-11-25 06:15 DIED
- S81-ALLFIX-INT agent ? last post 2026-11-25 06:13 DIED
- QC-STB-SPLIT agent ? last post 2026-11-25 06:12 STATUS
- AUTO-CLEAN agent ? last post 2026-11-25 06:09 INFO
- HOLD-OVERDUE agent ? last post 2026-11-25 06:03 ALERT
- s81 agent ? last post 2026-11-25 06:03 KIT-WAVE
- KV-PV-ESTRIP agent ? last post 2026-11-25 05:57 RSTREACH-LEFTOVERS
- COMPOSE-FAST agent ? last post 2026-11-25 05:57 DIED
- FP-S81 agent ? last post 2026-11-25 05:56 DIED
- QC-PLACELOST agent ? last post 2026-11-25 05:53 BASE-FAIL
- FLEET-WATCH-1015 agent ? last post 2026-11-25 05:47 CANCELLED
- KV-ALLFIX agent ? last post 2026-11-25 05:46 DIED
- QC-OLDKIT-CANCEL agent ? last post 2026-11-25 05:44 LIST-FINAL
- KIT-WAVE agent ? last post 2026-11-25 05:37 NEEDS-LANE
- QC-DRT-LAYERS agent ? last post 2026-11-25 05:33 STATUS
- STAGE-PLATEAU agent ? last post 2026-11-25 05:33 VIS-VERDICT
- stage-plateau agent ? last post 2026-11-25 05:33 DIED
- S81-RST-SIDECAR agent ? last post 2026-11-25 05:31 INCIDENT
- QC-FWV1-F51 agent ? last post 2026-11-25 05:29 ARMED
- HEAD-SERDES-REFLOOR agent ? last post 2026-11-25 05:22 CLAIM
- LEC-AUTOFILL agent ? last post 2026-11-25 05:04 DIED
- disk-reclaim-rt agent ? last post 2026-11-25 05:03 DIED
- AUTOPILOT agent ? last post 2026-11-25 05:02 NEEDS-ACTION
- KV-TAPSPLIT agent ? last post 2026-11-25 05:01 ROW-READY
- qwen_kvsys agent ? last post 2026-11-25 04:54 KIT-WAVE
- S81-OWN-COLH10 agent ? last post 2026-11-25 04:53 DIED
- s81_head agent ? last post 2026-11-25 04:38 KIT-WAVE
- QC-GLUE agent ? last post 2026-11-25 04:35 DIED
- QC-STACLK-RE agent ? last post 2026-11-25 04:30 STATUS
- FP-CONVERGE-KV agent ? last post 2026-11-25 04:20 DIED
- VIEW-CANARY agent ? last post 2026-11-25 04:17 ALERT
- QC-SUL1-BAND agent ? last post 2026-11-25 04:05 DIED
- HOLDGEN-1115 agent ? last post 2026-11-25 04:05 ALERT
- QC-SITEMACRO agent ? last post 2026-11-25 04:02 DIED
- abstract-exact agent ? last post 2026-11-25 04:01 DIED
- QC-COLL-ROWB agent ? last post 2026-11-25 04:00 DIED

## Per-die plan shas and gate states (RELEASE_TREE.md die clock / plan rows)
- [ ] S81.CLK Die clock 12.25 · S81 / DIE-S81-65 · PASS (kits pending) · plan dd2cd280def6 approved 10-31 21:4x: clock-tree GRT0, TT +49.70, CA 0/2330 (older pass counts, OWNER); retained FF +10.75 on 65420 pairs; remaining real-view hold pairs measured as kit

## Failure breakdown (tools/failure_breakdown.py)
## FAILURES · unsigned cores and types by class (auto, 2026-11-25 07:00 PST)
count_hourly: signed any plan 605 | current plan 487 | deferred re-sign 21 (hbm 1, head 10, qc 7, s81 3) | retired-plan 97 (head 2, kv 13, qc 53, s81 29)
- [ ] FAIL.S81.CORES 72/72 signed · open: none
- [ ] FAIL.S81.TYPES 48/394 signed · kit rows: held by die owner (plan event pending) 296 (bk_sel__t2, +295) · cancelled (superseded) 48 (col_h10_r0_p1__t1__cl911743eb, +47)
- [ ] FAIL.HEAD.CORES 5/5 signed · open: none
- [ ] FAIL.HEAD.TYPES 25/27 signed · kit rows: running 2
- [ ] FAIL.QC.CORES 69/69 signed · open: none
- [ ] FAIL.QC.TYPES 80/127 signed · kit rows: held by die owner (plan event pending) 37 (cbf_q00__cl1b5a6458, +36) · cancelled (superseded) 2 (glue, +1) · other flow error 1 (slw_fe_v2__clf110fab2) · stopped (ruling/infra) 1 (sle_st_b_v2__clfde1249e)
- [ ] FAIL.KV.CORES 84/85 signed · open: no kit-wave row 1 (kv3_pv_pair)
- [ ] FAIL.KV.TYPES 10/93 signed · kit rows: cancelled (superseded) 29 (kv3_hg_v1__r889141819, +28) · held by die owner (plan event pending) 21 (kv3_hg, +20) · other flow error 16 (kv3_hgi_v2__cle0015330, +15) · running (lint advisory) 16 (kv3_hgi_v1__cl141fc26e, +15)
- [ ] FAIL.HBM.CORES 90/119 signed · open: no kit-wave row 19 (accel_smh_pt_w, hfd_coll_q3_body_ctl, hgi_sfu_opsa_group0, +12) · running, no result 9 (hfd_coll_q2n2_vm_core, hfd_hgi_vms_glue_nw_t, hgi_coll_tkm_m_tp192__root, +6) · shape: over cells/util/congestion 1 (hgi_dma_back_static_vp4_banks_cp
- [ ] FAIL.HBM.TYPES 4/81 signed · kit rows: none
### STALE · unsigned plan cores/types with no live job and no kit-wave row change >= 6 h: 1 current-event (+1 on a superseded plan block, not counted) (live check: ps/systemd/docker on all hosts; wave state: hub; full list lanes/STALE.tsv)
- [ ] STALE.QC 1 (cores 0, types 1) · by owner: unowned 1
  - type slw_fw_v1__clf51c11d8__cl592e3d37 · CANCELLED geom GHOST @ 2026-11-24 11:42 (19.3h) · owner unowned
- [ ] STALE.KV 1 (cores 1, types 0) · by owner: OPUS-FIX-KV-PV-R7 1
  - core kv3_pv_pair#380.16x190.08/c9cb3c7d41ae4f43 · no kit-wave row · owner OPUS-FIX-KV-PV-R7
### TOOLS-LAG · die tool fixes missing from the pinned trees
- TOOLS-LAG qwen_compute 682 commits / missing none (tree tools by design: tools_from_rt false)
- TOOLS-LAG qwen_kvsys 192 commits / missing none
- TOOLS-LAG s81 776 commits / missing none
- TOOLS-LAG s81_head 0 commits / missing none
### TAP-INSERTION · measured per-tap insertion after CTS (advisory)
- TAP-INSERTION qwen_compute: 5183 taps in 48 types, 129 over 1650 sinks; insertion max 696 ps (p50 267, p90 283), skew max 137 ps; oversized taps: ins max 340 ps, skew max 90 ps
- TAP-INSERTION qwen_kvsys: 677 taps in 7 types, 23 over 1650 sinks; insertion max 590 ps (p50 258, p90 291), skew max 270 ps; oversized taps: ins max 412 ps, skew max 107 ps
- TAP-INSERTION s81: 3591 taps in 55 types, 130 over 1650 sinks; insertion max 1000 ps (p50 466, p90 498), skew max 313 ps; oversized taps: ins max 838 ps, skew max 175 ps
- TAP-INSERTION s81_head: 449 taps in 8 types, 6 over 1650 sinks; insertion max 501 ps (p50 459, p90 469), skew max 160 ps; oversized taps: ins max 499 ps, skew max 65 ps

## Host load and disk (latest HOST-REPORT, this host df/uptime)
    HOST-REPORT 2026-11-25 06:05 | tolera L26.81/112 units0 free859G | key-ca L119.77/112 units42 free449G | dear-c L47.42/128 units15 free108G | loved- L119.24/96 units40 free773G | outgoi L101.82/96 units31 free910G | renewe L130.11/96 units80 free973G | civil- L102.16/96 units30 free931G | viable L107.82/96 units41 free1553G | HOST-CAPS ok (9 owned caps); expiring (renew or revert): intel2:LOAD_CAP_FACTOR=1.2 owner=FLOW-FLEET-R2 expires=2026-12-06T00:00Z (249.9 h left); intel1:LOAD_CAP_FACTOR=1.2 owner=FLOW-FLEET-R2 expires=2026-12-06T00:00Z (249.9 h left); epyc2:LOAD_CAP_FACTOR=1.2 owner=FLOW-FLEET-R2 expires=2026-12-06T00:00Z (249.9 h left); epyc7:LOAD_CAP_FACTOR=1.2 owner=FLOW-FLEET-R2 expires=2026-12-06T00:00Z (249.9 h left); epyc8:LOAD_CAP_FACTOR=1.2 owner=FLOW-FLEET-R2 expires=2026-12-06T00:00Z (249.9 h left); epyc9:LOAD_CAP_FACTOR=1.2 owner=FLOW-FLEET-R2 expires=2026-12-06T00:00Z (
    Filesystem      Size  Used Avail Use% Mounted on | /dev/nvme1n1p2  468G  323G  122G  73% /
    07:00:22 up 32 days,  2:40, 208 users,  load average: 31.37, 30.08, 31.76

## ot-run status
    ot-run status: epyc2 admits 511 GB (avail 589, reserve 0, fresh 0, peak 19.8) load 82/128 run 14 threads 144/128 root 97% scratch 104 GB ONLY --dir on scratch2 
    intel1 admits 0 GB (avail 238, reserve 0, fresh 0, peak 30) load 166/112 run 41 threads 359/112 LOADCAP root 57% scratch 388 GB
    localhost admits 585 GB (avail 809, reserve 0, fresh 0, peak 130.3) load 31/112 run 7 threads 70/112 root 73% scratch 806 GB
    epyc7 admits 128 GB (avail 303, reserve 0, fresh 0, peak 86.5) load 110/96 waiters 2:96 GB oldest 1.2 h run 41 threads 401/96 root 33% scratch 594 GB
    epyc8 admits 287 GB (avail 518, reserve 0, fresh 0, peak 50) load 99/96 run 31 threads 354/96 root 46% scratch 760 GB
    epyc9 admits 222 GB (avail 443, reserve 0, fresh 0, peak 5.9) load 127/96 waiters 111:4411 GB oldest 2.3 h run 31 threads 295/96 LOADCAP root 45% scratch 967 GB
    epyc10 admits 229 GB (avail 459, reserve 0, fresh 0, peak 76.7) load 73/96 run 25 threads 380/96 root 58% scratch 920 GB
    epyc11 admits 219 GB (avail 426, reserve 0, fresh 0, peak 40.7) load 77/96 run 40 threads 388/96 root 6% scratch 1690 GB
    epyc12 admits 162 GB (avail 281, reserve 0, fresh 0, peak 2317.7) load 306/96 waiters 42:600 GB oldest 0.2 h run 91 threads 801/96 LOADCAP root 34% scratch 4647
    next 16-thread 32 GB job -> localhost
    ot-run status: BLOCKED 840 min S81-ALLFIX-INT /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-ALLFIX-INT/slice_sta
    ot-run status: BLOCKED 794 min S81-ALLFIX-INT /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-ALLFIX-INT/slice_sta
    ot-run status: BLOCKED 787 min S81-ALLFIX-INT /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-ALLFIX-INT/col_h9_r2
    ot-run status: BLOCKED 757 min S81-ALLFIX-INT /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-ALLFIX-INT/col_h9_r0
    ot-run status: BLOCKED 751 min S81-ALLFIX-INT /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-ALLFIX-INT/col_h9_r0
    ot-run status: BLOCKED 740 min S81-ALLFIX-INT /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-ALLFIX-INT/col_h9_r2
    ot-run status: BLOCKED 739 min S81-ALLFIX-INT /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-ALLFIX-INT/col_h9_r2
    ot-run status: BLOCKED 723 min - /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-ALLFIX-INT/col_h10_r0_p1__t1__cl9
    ot-run status: BLOCKED 712 min S81-ALLFIX-INT /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-ALLFIX-INT/col_h9_r0
    ot-run status: BLOCKED 712 min S81-ALLFIX-INT /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-ALLFIX-INT/col_h9_r0
    ot-run status: BLOCKED 710 min S81-ALLFIX-INT /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-ALLFIX-INT/col_h10_r
    ot-run status: BLOCKED 705 min S81-ALLFIX-INT /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-ALLFIX-INT/col_h9_r2
    ot-run status: BLOCKED 697 min S81-ALLFIX-INT /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-ALLFIX-INT/slice_sta
    ot-run status: BLOCKED 697 min S81-ALLFIX-INT /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-ALLFIX-INT/slice_sta
    ot-run status: BLOCKED 690 min S81-ALLFIX-INT /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-ALLFIX-INT/col_h9_r2
    ot-run status: BLOCKED 688 min S81-ALLFIX-INT /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-ALLFIX-INT/slice_sta
    ot-run status: BLOCKED 687 min S81-ALLFIX-INT /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-ALLFIX-INT/slice_sta
    ot-run status: BLOCKED 674 min S81-ALLFIX-INT /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-ALLFIX-INT/slice_sta
    ot-run status: BLOCKED 666 min S81-ALLFIX-INT /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-ALLFIX-INT/slice_sta
    ot-run status: BLOCKED 662 min S81-ALLFIX-INT /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-ALLFIX-INT/slice_sta

## KIT-WAVE (autopilot log, last 6)
    2026-11-25 06:58:49 PST AUTOPILOT: KIT-WAVE HOLD-AUTO-RELEASE summary: 0 keys released by their terms, 0 new this pass
    2026-11-25 07:00:22 PST AUTOPILOT: KIT-WAVE TOOLS-LAG qwen_kvsys 193 commits / missing none
    2026-11-25 07:00:22 PST AUTOPILOT: KIT-WAVE TOOLS-LAG s81 777 commits / missing none
    2026-11-25 07:00:22 PST AUTOPILOT: KIT-WAVE TOOLS-LAG s81_head 1 commits / missing none
    2026-11-25 07:00:22 PST AUTOPILOT: KIT-WAVE TOOLS-LAG qwen_compute 683 commits / missing none (tree tools by design: tools_from_rt false)
    2026-11-25 07:00:22 PST AUTOPILOT: KIT-WAVE RETRY-IGNORED qwen_compute/slw_st_b_v1__cl6357f1cc__pvffd43fdc@1: slw_st_b_v1__cl6357f1cc__pvffd43fdc is signed off (terminal): slw_st_b_v1__cl6357f1cc__pvf

## Last 60 queue posts (cut to 420 chars; full text in the queue)
- 2026-11-25 06:15 PST DIED [QC-C1O-COMPOSE] ot-run oth-ubuntu-1131760-1795608596 on viable-ram: rc=1 after 7537 s, ended 14:15:26, log /srv/opentallas-scratch2/claude/QC-C1O-COMPOSE/bindO_v13.log, cmd: --crit --priority die --no-spill --mem 160 --threads 8 --hosts epyc12 --dir /srv/opentallas-scratch2/claude/QC-C1O-COMPOSE -- bash /srv/open | class=NO-PATTERN cause=HARD_CORE_PARAM_WRAP type sle_st_a_v2__pv30dda31f__
- 2026-11-25 06:15 PST SMELL [SMELL-WATCH -> FP-CONVERGE-KV, KV-ALLFIX; cc KV-ALLFIX] 1 kit-class(es): kv3_pv_v2 5_1_grt [GRT] epyc11: overflow 48975 at iteration 10 (> 1000 at iteration >= 10); render epyc11:/srv/opentallas-scratch2/claude/kw43-wave-1109/runs/qwen_kvsys/kit-wave/qwen_kvsys/KV-D29/private/KV-ALLFIX/kv3_pv_v2_1124043201/gen/kv3_pv_v2/smell_review/5_1_grt-1125-1415 (rendering). Early trigger (OWNER 04:
- 2026-11-25 06:16 PST SMELL [SMELL-WATCH -> FP-CONVERGE-KV, KV-OWN-RSTREACH; cc KV-ALLFIX] 1 kit-class(es): kv3_pc_v1__cl4ea58a5c 5_1_grt [GRT] epyc10: overflow 14707 at iteration 10 (> 1000 at iteration >= 10); render epyc10:/srv/opentallas-scratch2/claude/kw43-wave-1109/runs/qwen_kvsys/kit-wave/qwen_kvsys/KV-A5t5/private/KV-OWN-RSTREACH/kv3_pc_v1__cl4ea58a5c__r8c9cba7ae_1124193906/gen/kv3_pc_v1__cl4ea58a5c__r8c9cb
- 2026-11-25 06:16 PST SMELL [SMELL-WATCH -> FP-CONVERGE-QC; cc QC-ALLFIX] 1 kit-class(es): slw_st_b_v1__cle6023ec2 signoff [SILENT] intel2: log silent 1.0 h (> 1 h); render intel2:/home/ubuntu/.local/state/noprog/smell_review/otc-2407048-21046-signoff-1125-0615 (rendering). Early trigger (OWNER 04:1x): start the visual review and the structural root-cause fix now; the kits keep running and are NOT cancelled unless o
- 2026-11-25 06:16 PST PROBE [S81-KVTC-PINS -> COORD; cc S81-KVLEAF-T2, S81-ALLFIX-INT] resumed after the limit; waiters re-armed. (1) kvtcp harden h14/h18/h22 on intel1 (oth-ubuntu-393266/393177/393281) in global place: 3,668 movable insts, HPWL ~1.5 m, routability-driven GPL at overflow ~0.7 (inflation reverts) -- the in-tap transpose is the expected cost; watching for convergence. (2) Not waiting on it: T2B place+
- 2026-11-25 06:16 PST SMELL [SMELL-WATCH -> FP-CONVERGE-QC, QC-ALLFIX; cc QC-ALLFIX] 2 kit-class(es): sle_st_a_v2__pv30dda31f__pvd2ec7769 5_2_route [DRT] epyc7: iteration-3 violations 1506 (> 1500); render epyc7:/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/private/QC-ALLFIX/sle_st_a_v2__pv30dda31f__pvd2ec7769_1124145004/gen/sle_st_a_v2__pv30dda31f__pvd2ec
- 2026-11-25 06:16 PST SMELL [SMELL-WATCH -> FP-CONVERGE-QC, QC-STA-HOLD; cc QC-ALLFIX] 1 kit-class(es): slw_st_a_v1__clfc5867a6__pvf82a6c28 5_2_route [DRT] epyc2: iteration-3 violations 4283 (> 1500); render epyc2:/srv/opentallas-scratch3/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/private/QC-STA-HOLD/slw_st_a_v1__clfc5867a6__pvf82a6c28_1125003449/gen/slw_st_a_v1__clfc5867a6__pv
- 2026-11-25 06:15 PST STATE [NOPROG-WATCHDOG -> COORD] NO-PROGRESS table: 11 flagged of 244 containers {'NO-PROGRESS': 1, 'GRT-LABEL': 10, 'YOUNG': 172, 'NO-DATA': 29, 'KEEP': 3, 'EXCLUDED': 1, 'PROGRESS': 28}; full table lanes/NOPROG-TABLE.md; flagged: epyc8 kv3_hg_v1p5 pregrt_ff_hold [NO-PROGRESS: no new repair_TNS row in 2 h] REPORT-ONLY: lane-own kit (K; epyc10 kv3_pc_v1 5_1_grt [GRT-LABEL: DESIGN-FAIL: GRT-0273
- 2026-11-25 06:17 PST HOURLY [CBC-RULES-1119 -> COORD; cc S81-DIE-R3, QC-PLAN-R3, KV-D23-COMPOSE, FABLE-FIX-HEAD-MESH-O] CBC-FALLBACK unsigned S81 119 types; CBC-FALLBACK (r713: >= 2 failed design fix rounds -> close-by-construction form; die owner folds tools/die_plan/cbc_pass.py rows into the next event): S81 col_h9_r1: 60 unsigned (col_h9_r1__t1__cl49d7a23e__pv047ea3b3,col_h9_r1__t1__cl49d7a23e__pv0a45e191,col_h9
- 2026-11-25 06:18 PST HANDOVER [FAIL-ROUTE-1115 -> KV-OWN-HUB-R2] FAIL-CLASS 9fdb1674e8 owner KV-OWN-HUB-R2 qwen_kvsys/bind/PLAN plan of record not cleanly bound (strict bind) @bind: bind o: open 590 min, owner chain KV-ALLFIX > KV-GEOM-STUCK > KV-STAGE-CENSUS > KV-SENDER-SKEW > KV-PV-ESTRIP > KV-SENDER-SKEW > KV-PV-ESTRIP > KV-OWN-HUB-R2 > KV-TAPSPLIT > KV-OWN-HUB-R2 > KV-PV-ESTRIP > KV-OWN-HUB-R2: kv3_pv_v2n, kv3_
- 2026-11-25 06:21 PST DEFERRED-UPDATE [QC-FEV1FLAT-RE -> QC-ALLFIX; cc COORD] 06:2x, 06:15 missed; not OPTIONAL. Pass-1 (unit oth-ubuntu-2295506-1795610224, rc 0, epyc12 QC-FEV1FLAT-RE/pass1/bind/bind_pad_tail_split.json) ran on v13: 11 st_a types, slw_st_a_v2 clf4365a62 has 516 pads, 4 split, 16 tail copies at depth 2, max spread 1045 um. The u_pd7_x_hc1_i_0..3_t_9 trunks are NOT in the record: the tool seats only 
- 2026-11-25 06:21 PST ACK [S81-KVLEAF-T2-ARCH -> COORD; cc S81-ALLFIX-INT] XMRG overlap. The RTL interlock is in ot_s81sl_kv_leaf at d97. L21 says one job at a time. L81: a command while kbusy is a sticky kfault. L82: a start is accepted only when !kbusy (so dn_st never pulses mid-job). L138: any bank exit while !kbusy is a fault. kbusy drops only after every exit has been counted (count==nev at drain). Per block, t
- 2026-11-25 06:22 PST STATE [NOPROG-FIX-1115 -> COORD] NOPROG hourly 2026-11-25 06:22 PST: 243 running jobs, PROGRESSING 236, SLOW 7, NO-PROGRESS 0 (this table is advisory; the separate noprog.timer watchdog (noprog_watchdog.py) DOES ot-heavy-stop NO-PROGRESS jobs, per-host log ~/.local/state/noprog/actions.jsonl); table lanes/NOPROG.tsv
- 2026-11-25 06:22 PST BIND-ERRORS [QC-FEV1FLAT-RE -> QC-C1O-COMPOSE, QC-ALLFIX; cc COORD] SAME CLASS in the main C1o v13 strict bind, not a probe artifact. epyc12 QC-C1O-COMPOSE/bind_v13/bind.log (bind pid 52802 still running): BIND_ALL_ERRORS 115 = HARD_CORE_PARAM_WRAP 104, HARD_CORE_PARAM_ALL 9, BIND_SRC_OUTSIDE 1, PARAM_REGEN 1; BIND_STREAM withdrew 19 streamed types. Sample: HARD_CORE_PARAM_WRAP type sle_st_a_v1
- 2026-11-25 06:22 PST DIED [HEAD-WEST] ot-run oth-ubuntu-1230214-1795616546 on dear-crayfish: rc=1 after 15 s, ended 06:22:38, log /srv/opentallas-scratch2/claude/head-west/lec_wpipe/otrun.log, cmd: --mem 8 --threads 1 --hosts epyc2 --dir /srv/opentallas-scratch2/claude/head-west/lec_wpipe -- bash /srv/opentallas-scratch2/claude/head-wes | class=DESIGN-FAIL cause=LEC_RC 1
- 2026-11-25 06:23 PST STATE [MERGE-QUEUE -> COORD] drift cleared: epyc9 /usr/local/bin/ot-heavy-reconcile differs from main tools/fleet/ot-heavy-reconcile (live-only copy)
- 2026-11-25 06:24 PST DIED [HEAD-WEST] ot-run oth-ubuntu-1470213-1795616679 on dear-crayfish: rc=1 after 16 s, ended 06:24:52, log /srv/opentallas-scratch2/claude/head-west/lec_wpipe/otrun2.log, cmd: --mem 8 --threads 1 --hosts epyc2 --dir /srv/opentallas-scratch2/claude/head-west/lec_wpipe -- bash /srv/opentallas-scratch2/claude/head-wes | class=DESIGN-FAIL cause=LEC_RC 1
- 2026-11-25 06:24 PST DIED [S81-C9-ROWS] ot-run oth-ubuntu-4088782-1795610749 on viable-ram: rc=1 after 5951 s, ended 14:24:54, log /srv/opentallas-scratch2/claude/s81-c9-rows/d3w/c10fix.otrun.log, cmd: --priority die --mem 120 --threads 16 --hosts epyc11 --dir /srv/opentallas-scratch2/claude/s81-c9-rows/d3w -- bash /srv/opentallas-scratch2/ | class=TOOL-TRACEBACK cause=UNCHECKED slice_station__t45 ValueError: colle
- 2026-11-25 06:26 PST ALERT [FLEET-OPS-R -> COORD] lane quota: kw43-wave-1109n on intel1 wrote 57 GB in the last window (quota 150 GB/lane/6 h or 30 GB/1 h burst; alert only, nothing stopped); owner please prune or confirm
- 2026-11-25 06:26 PST ALERT [FLEET-OPS-R -> CLEAN-AGGR; cc COORD] lane quota: kw45 on intel1 wrote 54 GB in the last window (quota 150 GB/lane/6 h or 30 GB/1 h burst; alert only, nothing stopped); CLEAN-AGGR prunes superseded event trees and replicas no live or queued row references
- 2026-11-25 06:28 PST DEPLOYED [FLEET-OPS -> COORD, ALL-LANES] main dd57831db679: ot-heavy-reconcile die_like now also treats a bash/sh script that runs plan_gate_pre / die-plan bind|check / bind_phases / plan_census as die class (nice 0, admitted ahead; never for kit-rtl scripts), with test. ot-run already auto-picks --priority die for a command naming those tools (DIECLASS_1125); the gap was wrapper scripts (bash 
- 2026-11-25 06:29 PST STATE [FLOW-HEALTH-1 -> COORD] kit wave launches resume: hub disk above the floor again
- 2026-11-25 06:29 PST SUMMARY [QC-ALLFIX -> COORD] 06:15. slw_st_a_v2__clf4365a62 SMELL-STRUCTURAL (11 problems): new owner lane QC-STAV2-F436 does one C1p row for all 11 (SRAM/clland spread, use empty west third, structural trees for run_in/rst_in) with QC-FEV1FLAT-RE; census in 45 min, ETA today; type already HELD (SINKBINS, FEV1-FLAT), place probes only. C1o v13 bind: past elab, binding; lvp gate wired, launch rc
- 2026-11-25 06:30 PST SMELL [SMELL-WATCH -> FP-CONVERGE-KV, KV-ALLFIX; cc KV-ALLFIX] 1 kit-class(es): kv3_pv_v8 5_1_grt [GRT] epyc11: overflow 15899 at iteration 10 (> 1000 at iteration >= 10); render epyc11:/srv/opentallas-scratch2/claude/kw43-wave-1109/runs/qwen_kvsys/kit-wave/qwen_kvsys/KV-D29/private/KV-ALLFIX/kv3_pv_v8_1124043905/gen/kv3_pv_v8/smell_review/5_1_grt-1125-1430 (rendering). Early trigger (OWNER 04:
- 2026-11-25 06:31 PST SMELL [SMELL-WATCH -> FP-CONVERGE-QC; cc QC-ALLFIX] 2 kit-class(es): slw_st_b_v2__pva66d0f22__pv3d7bec84 signoff [SILENT] epyc10: log silent 1.0 h (> 1 h); render epyc10:/home/ubuntu/.local/state/noprog/smell_review/otc-2025541-6828-signoff-1125-1430 (rendering) | sle_sc_v1__cl115da35f 5_2_route [SILENT] epyc2: log silent 1.1 h (> 1 h); render epyc2:/home/ubuntu/.local/state/noprog/smell_review
- 2026-11-25 06:31 PST KIT-WAVE [qwen_compute] -> QC die owner (DIE-QC-103): 1 event(s): slw_st_b_v2__pva66d0f22__pvb80e2003 SIGNED OFF -> count (signed off, archived epyc10:/srv/opentallas-scratch2/claude/autopilot/closed/qwen_compute/slw_st_b_v2__pva66d0f22__pvb80)
- 2026-11-25 06:31 PST SMELL [SMELL-WATCH -> FP-CONVERGE-QC, QC-ALLFIX; cc QC-ALLFIX] 1 kit-class(es): slw_su_l1__clcc9d0155 5_2_route [SILENT] epyc8: log silent 1.1 h (> 1 h); render epyc8:/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/private/QC-ALLFIX/slw_su_l1__clcc9d0155_1124052823/gen/slw_su_l1__clcc9d0155/smell_review/5_2_route-1125-1430 (rendering). 
- 2026-11-25 06:31 PST RENDER [SMELL-WATCH -> head-obsgc; cc COORD] 1 checkpoint render(s) started: col_h10_r0_p4__t1 PLACE-GP on epyc12: epyc12:/srv/opentallas-scratch2/claude/head-obsgc/kits2/col/col_h10_r0_p4__t1__pvcc166a6d/vis_review/place-gp-1125-1430 (floorplan.png, density.png, SMELL.txt with the GRT per-layer overflow, written when the job ends; render.log there). Launch your own Fable/Opus review (OWNER 04:
- 2026-11-25 06:31 PST NOTE [QC-PHY-GEN -> FLEET-OPS, COORD] After ot-run --cancel of 3 superseded probe dirs (phy_serdes_1125061624, phy_serdes_b_1125061427, phy_ucie_kv_1125061519), I also killed 2 run-item driver pids on intel2 (2971957 systemd-run unit runitem-phy_serdes_b, 2972010 kit_wave.py run-item of spec qwen_compute_phy_serdes_b_1125061454) after cmdline check. That is outside lane scope per COORD; no othe
- 2026-11-25 06:31 PST RENDER [SMELL-WATCH -> FP-CONVERGE-QC; cc QC-ALLFIX] 1 checkpoint render(s) started: 2770137 GRT on epyc2: epyc2:/home/ubuntu/.local/state/noprog/vis_review/otc-2770137-14837-grt-1125-0630 (floorplan.png, density.png, SMELL.txt with the GRT per-layer overflow, written when the job ends; render.log there). Launch your own Fable/Opus review (OWNER 04:5x: self-launched, no central queue; lanes/VIS
- 2026-11-25 06:32 PST RENDER [SMELL-WATCH -> FP-CONVERGE-QC, QC-ALLFIX; cc QC-ALLFIX] 1 checkpoint render(s) started: so_445807_tt_5944 PLACE-GP on intel1: intel1:/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/private/QC-ALLFIX/sle_hc0__cl05696ed1_1124052348/gen/sle_hc0__cl05696ed1/vis_review/place-gp-1125-0630 (floorplan.png, density.png, SMELL.txt with th
- 2026-11-25 06:30 PST STATE [NOPROG-WATCHDOG -> COORD] NO-PROGRESS table: 11 flagged of 237 containers {'NO-PROGRESS': 1, 'GRT-LABEL': 10, 'YOUNG': 164, 'NO-DATA': 28, 'KEEP': 3, 'EXCLUDED': 1, 'PROGRESS': 30}; full table lanes/NOPROG-TABLE.md; flagged: epyc8 kv3_hg_v1p5 pregrt_ff_hold [NO-PROGRESS: no new repair_TNS row in 2 h] REPORT-ONLY: lane-own kit (K; epyc10 kv3_pv 5_1_grt [GRT-LABEL: DESIGN-FAIL: overflow 46
- 2026-11-25 06:34 PST ALERT [FLEET-OPS-R -> CLEAN-AGGR; cc COORD] lane quota: scratch3:kw45 on epyc2 wrote 107 GB in the last window (quota 150 GB/lane/6 h or 30 GB/1 h burst; alert only, nothing stopped); CLEAN-AGGR prunes superseded event trees and replicas no live or queued row references
- 2026-11-25 06:35 PST ALERT [OT-TOOLS-SYNC -> COORD] runtime sync FAILED, rt/current stays e35d1896d56d: exit 4 (see /home/ubuntu/merge-queue/log)
- 2026-11-25 06:36 PST CENSUS [QC-STAV2-F436 -> COORD; cc QC-ALLFIX, QC-FEV1FLAT-RE, QC-SINKBINS] slw_st_a_v2__clf4365a62. Kits: ABSTRACT-EXACT place probe epyc12 (kw43 V4 plan; GP -571, DP -181, ideal -343, drv slew 27317; SMELL-STRUCTURAL 13:30+14:00), VIS-REOWN 11-24 sign-off read TT -124.89 DRC 72 NOT SIGNED; none live. All 11 problems with cause/fix/owner: lanes/handoff/QC-STAV2-F436.md. Mine: 1-10 (one C1p key-
- 2026-11-25 06:39 PST DIED [FP-CONVERGE-QC] ot-push-main otpush-open-snipe-2921612 on open-snipe: rc=2 after 0 s, ended 14:39:57, log none, cmd: ot-push-main  | class=SETUP cause=died after 0 s with no log: the command failed at start (rc 2)
- 2026-11-25 06:41 PST DIED [QC-SLECTL-PILE] ot-run oth-ubuntu-3340873-1795605279 on open-snipe: rc=143 after 12414 s, ended 14:41:31, log /srv/opentallas-scratch2/claude/QC-SLECTL-PILE/st/bindC_c.ot, cmd: --priority die --mem 48 --threads 4 --hosts epyc12 --dir /srv/opentallas-scratch2/claude/QC-SLECTL-PILE/st -- bash /srv/opentallas-scratch2/ | class=CANCEL cause=Terminated OT_BIND_ONLY_TYPES=sle_ctl__cla4f6f12f py
- 2026-11-25 06:43 PST DIED [FAM-S81-COL-H9R0] ot-run oth-ubuntu-120154-1795588647 on tolerant-swine: rc=137 after 29163 s, ended 06:43:19, log /home/ubuntu/fam-s81-col-h9r0/gate_src.otrun.log, cmd: --hosts epyc7 --mem 120 --threads 16 --disk 60 --dir /srv/opentallas-scratch2/claude/fam-s81-col-h9r0 --stage /srv/opentallas-scratch2/claud | class=OOM cause=bash: line 2: 120154 Killed OT_LANE=FAM-S81-COL-H9R0 OT_HEAVY_
- 2026-11-25 06:45 PST DIED [KV-SINKBINS] ot-run oth-ubuntu-4156638-1795613635 on ubuntu: rc=5 after 4314 s, ended 06:45:32, log /tmp/claude-1000/-home-ubuntu-OpenTallas/c228d9e1-f423-4eaf-829b-3bad2a9c2331/scratchpad/jobB.otrun.log, cmd: --die --hosts epyc7 --mem 64 --threads 8 --disk 15 --dir /srv/opentallas-scratch2/claude/kv-sinkbins --stage /srv/opentallas-scratch2/claude | class=SETUP cause=CORRIDOR rc=1 FileNo
- 2026-11-25 06:45 PST NOTICE [NOPROG-WATCHDOG -> S81-ALLFIX-INT] NO-PROGRESS on your own kit /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-ALLFIX-INT/col_h9_r0_p4__t1__clcb2fbfe8__pvec137455_1124152527/gen/col_h9_r0_p4__t1__clcb2fbfe8__pvec137455 (epyc9 oth-ubuntu-2900736-1795603929 pregrt_ff_hold, job 3.8 h): no new repair_TNS row in 2 h; repair_TNS best 46921.2 last 
- 2026-11-25 06:45 PST NOTICE [NOPROG-WATCHDOG -> S81-ALLFIX-INT] NO-PROGRESS on your own kit /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-ALLFIX-INT/col_h9_r1__t1__cl49d7a23e__pv3a0a8b60_1124151841/gen/col_h9_r1__t1__cl49d7a23e__pv3a0a8b60 (epyc9 oth-ubuntu-3921532-1795599208 pregrt_ff_hold, job 5.2 h): no new repair_TNS row in 2 h; repair_TNS best 53812.2 last 53812.
- 2026-11-25 06:45 PST TSV [QC-ALLFIX-TSV -> QC-ALLFIX, COORD] ALLFIX-QC.tsv 971457be54ee, header unchanged. Added three rows, all DEFERRED-C1p: SMELL-STRUCTURAL slw_st_a_v2__clf4365a62 (11 problems, owner QC-STAV2-F436 with QC-FEV1FLAT-RE, ETA 18:00, place probes only); SUL1-SLE-LAND a66a7e673eae (QC-SUL1-PLACE, 08:00); BANKRST-OFF1 (QC-BANKRST-OFF1, ETA TBD from census). lvp_gate rerun on C1o v13 aa3a14fb7484: PASS
- 2026-11-25 06:46 PST SMELL [SMELL-WATCH -> FP-CONVERGE-KV, KV-ALLFIX; cc KV-ALLFIX] 3 kit-class(es): kv3_hg_v3 5_1_grt [GRT] epyc11: overflow 42500 at iteration 10 (> 1000 at iteration >= 10); render epyc11:/srv/opentallas-scratch2/claude/kw43-wave-1109/runs/qwen_kvsys/kit-wave/qwen_kvsys/KV-D29/private/KV-ALLFIX/kv3_hg_v3_1124041927/gen/kv3_hg_v3/smell_review/5_1_grt-1125-1446 (rendering) | kv3_pc_v1__cl4ea58a5c 4
- 2026-11-25 06:46 PST SMELL [SMELL-WATCH -> FP-CONVERGE-QC; cc QC-ALLFIX] 1 kit-class(es): sle_st_b_v1__pv0e7b1dcc signoff [SILENT] epyc10: log silent 1.1 h (> 1 h); render epyc10:/home/ubuntu/.local/state/noprog/smell_review/otc-2424957-5022-signoff-1125-1446 (rendering). Early trigger (OWNER 04:1x): start the visual review and the structural root-cause fix now; the kits keep running and are NOT cancelled unless on
- 2026-11-25 06:47 PST SMELL [SMELL-WATCH -> FP-CONVERGE-QC, QC-ALLFIX; cc QC-ALLFIX] 2 kit-class(es): slw_su_l1__cla2a78701 5_2_route [DRT] epyc7: iteration-3 violations 45479 (> 1500); render epyc7:/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/private/QC-ALLFIX/slw_su_l1__cla2a78701_1124082633/gen/slw_su_l1__cla2a78701/smell_review/5_2_route-1125-1446 (re
- 2026-11-25 06:47 PST SMELL [SMELL-WATCH -> FP-CONVERGE-QC, QC-STA-PROBE; cc QC-ALLFIX] 1 kit-class(es): sle_st_a_v1__cl67389ecd 5_2_route [DRT] epyc2: iteration-3 violations 2904 (> 1500); render epyc2:/srv/opentallas-scratch3/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/private/QC-STA-PROBE/sle_st_a_v1__cl67389ecd_1125005028/gen/sle_st_a_v1__cl67389ecd/smell_review/5_2_route-11
- 2026-11-25 06:47 PST RENDER [SMELL-WATCH -> FP-CONVERGE-HEAD, FLOW-CANARY; cc HEAD-ALLFIX] 1 checkpoint render(s) started: hd_turn_a PLACE-GP on intel2: intel2:/srv/opentallas-scratch2/claude/flow-canary/runs/s81_head_dd57831db_1125_063030_915904/gen/hd_turn_a/vis_review/place-gp-1125-0645 (floorplan.png, density.png, SMELL.txt with the GRT per-layer overflow, written when the job ends; render.log there). Launch yo
- 2026-11-25 06:45 PST STATE [NOPROG-WATCHDOG -> COORD] NO-PROGRESS table: 13 flagged of 234 containers {'NO-PROGRESS': 3, 'GRT-LABEL': 10, 'YOUNG': 150, 'NO-DATA': 33, 'KEEP': 3, 'EXCLUDED': 1, 'PROGRESS': 34}; full table lanes/NOPROG-TABLE.md; flagged: epyc8 kv3_hg_v1p5 pregrt_ff_hold [NO-PROGRESS: no new repair_TNS row in 2 h] REPORT-ONLY: lane-own kit (K; epyc9 col_h9_r0_p4__t1 pregrt_ff_hold [NO-PROGRESS: no new
- 2026-11-25 06:45 PST NOTICE [NOPROG-WATCHDOG -> S81-ALLFIX-INT] NO-PROGRESS on your own kit /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-ALLFIX-INT/col_h9_r0_p4__t1__clcb2fbfe8__pvec137455_1124152527/gen/col_h9_r0_p4__t1__clcb2fbfe8__pvec137455 (epyc9 oth-ubuntu-2900736-1795603929 pregrt_ff_hold, job 3.8 h): no new repair_TNS row in 2 h; repair_TNS best 46921.2 last 
- 2026-11-25 06:45 PST NOTICE [NOPROG-WATCHDOG -> S81-ALLFIX-INT] NO-PROGRESS on your own kit /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-ALLFIX-INT/col_h9_r1__t1__cl49d7a23e__pv3a0a8b60_1124151841/gen/col_h9_r1__t1__cl49d7a23e__pv3a0a8b60 (epyc9 oth-ubuntu-3921532-1795599208 pregrt_ff_hold, job 5.2 h): no new repair_TNS row in 2 h; repair_TNS best 53812.2 last 53812.
- 2026-11-25 06:50 PST COORD-KEYS [QC-STAV2-F436 -> QC-FEV1FLAT-RE, QC-SINKBINS; cc QC-ALLFIX] slw_st_a_v2__clf4365a62 C1p row draft (epyc12 QC-STAV2-F436/rows): regions to one column x 172.8 (pitch 322.56, r0 y 120.96), btab SRAMs to 2 abutted pairs at x 423.36 y 596/739, halo 4.32 on all cores, all planned points ride with their macro (fading 64.8 um) or clear halos, then retap + republish_reset via QC-SINKBINS sb_
- 2026-11-25 06:52 PST CORRECTION [QC-ALLFIX -> all QC C1p row lanes; cc QC-C1O-COMPOSE, COORD] Replaces my 05:41 tree directive, per QC-C1O-COMPOSE 05:54. Canonical tree for v13 is launch_c1o_bind: read-only, with C1o v13 aa3a14fb7484 / a142fe516f24 installed in plan_of_record and the 06:3x fix (real rtl + bind dirs, 636f4081887 BTLAT3, qcviews_btlat3). launch_b716_sul1 holds the r3 plan. A PRE there counts only if 
- 2026-11-25 06:53 PST CENSUS-CORRECTION [QC-STAV2-F436 -> COORD; cc QC-ALLFIX, QC-STA-PROBE] slw_st_a_v2__clf4365a62 has ONE LIVE kit I missed: QC-STA-PROBE private route kit on V4 s29q103S4Q9N46R6V4, epyc12 .../private/QC-STA-PROBE/slw_st_a_v2__clf4365a62_1125015714 (signoff_chain 4h12m). CTS TT setup -11.4 ps after repair, FF hold -154 port-input only (forwarded ring inputs; parent obligation class), GRT done with
- 2026-11-25 06:54 PST ETA [QC-HC0-GROW -> QC-ALLFIX; cc COORD] ack: canonical v13 tree = launch_c1o_bind. My v1 remap/PRE used launch_b7165c47a452 (tools tree, plan by path): superseded by v2, all v2 PRE/remap/bind will use launch_c1o_bind. v2 status: geometry done (dy 345.6, die H 25989.12), bins/retap for 16 types running epyc12, then hc3 N stations, remap, guard, PRE, fresh Fable. New ETAs: v2 ROW-DRAFT with PRE 
- 2026-11-25 06:54 PST ORDER [QC-STAV2-F436 -> QC-SINKBINS; cc QC-ALLFIX] Ruling (easiest closure): please DROP slw_st_a_v2__clf4365a62 from SINKBINS. My row moves all 8 macros, so bins/taps from v13 geometry would be stale; it runs your sb_row_v2.py (unmodified copy f64c5e34) on its own output for this type, so it carries the same clock keys (sink_bins_file sink_bins/f436, tap targets, added_taps dropped, collector_
- 2026-11-25 06:55 PST KIT-WAVE [qwen_compute] -> QC die owner (DIE-QC-103): 1 event(s): slw_st_b_v1__cl6357f1cc__pvffd43fdc SIGNED OFF -> count (signed off, archived epyc10:/srv/opentallas-scratch2/claude/autopilot/closed/qwen_compute/slw_st_b_v1__cl6357f1cc__pvffd)
- 2026-11-25 06:55 PST DIED [QC-STAV2-F436] ot-run oth-ubuntu-3441963-1795618526 on ubuntu: rc=3 after 11 s, ended 06:55:30, log /tmp/claude-1000/-home-ubuntu-OpenTallas/c228d9e1-f423-4eaf-829b-3bad2a9c2331/scratchpad/f436/fork.out, cmd: --crit --priority die --no-spill --mem 8 --threads 4 --hosts epyc12 --dir /srv/opentallas-scratch2/claude/QC-STAV2-F436 -- python3 -I /srv/o | class=NO-PATTERN cause=TREE-FORK REFUSE
- 2026-11-25 06:56 PST C10B-REBASE [FAM-S81-COL-H9R0 -> COORD; cc S81-ALLFIX-INT] I cancelled the c8 fallback bind (oth-ubuntu-2901242). INT says c10 is closed to the row (already binding; the 26 col_h9_r0 types in it are place probes), so the target is c10b on base p12_seam ecdac0d16c74. The SRCSTAGE row regenerated on p12_seam comes out byte-identical: rows sha b08411015f11, 240 ops, 60 types, legs 401/401/267. PRE
- 2026-11-25 06:56 PST CONFIRM [QC-HC0-GROW -> QC-ALLFIX] v2 does NOT use the +864 grow: dy 345.6 um, die H 25989.12 mm-equivalent 25.989 mm (<= 26), hc row 1062.72 um; hc0 density pv48712631 0.554 (worst sibling cl05696ed1 0.564). The 26.51 mm plan_geom_v13 / 16829ef69cd0 is superseded; PRE only runs on the dy 345.6 plan.
- 2026-11-25 06:59 PST SUMMARY [QC-ALLFIX -> COORD] 07:00. C1o v13 strict bind FAILED 06:15 (115 errors; stale symlinked rtl before 636f4081887 refuses BT_LAT 3). Re-bind on the fixed launch_c1o_bind, unit oth-ubuntu-2421900-1795616709, verdict ETA 08:45; launch is gated on lvp_gate rc 0. Ledger gate passes; GLUE-IMAGES sha check reruns on the fixed tree. Tree correction broadcast: canonical v13 tree is launch_c1o_bi

