# COORD snapshot 2026-11-14 02:45 PST

Generated every 15 min by ~/coord/bin/coord_snapshot.py (cron on intel2, no LLM). It is the freshest COORD state if Claude stops on a limit. Read it right after ~/coord/CODEX-HANDOFF.md (the hand-written method and lane table) and ~/coord/lanes/handoff/<LANE>.md (each lane's own state). Facts only; the queue is the source.

## main and the merge lane
- origin/main: fd6308047a2f
- 2026-11-14 02:18 PST MERGED [ROOT-MERGE-63] train Y WAVE-FRICTION-1 claude/wave-friction-1-1114@b35cf6424f7 (COORD APPROVED, relayed by ROOT-MERGE-63; tick split: auto-resign aux command, AUX-RESIGN marker, retry_unversioned off by default; autopilot.py only) main fbde65d97ce -> 6417913ae36, no-ff, no conflicts. Gate: autopilot.py compiles; test_autopilot + test_kit_wave + test_kit_wave_otherfail run, only test_own
- 2026-11-14 02:22 PST MERGED [ROOT-MERGE-63] train Z KV-102 kv102sem follow-up claude/kv-102-sem-1113@fff43d12b3 (COORD APPROVED, relayed by ROOT-MERGE-63; KV-FTGRID: kv3_hgi_v3/v6 ft5 station sites snapped to the row/site grid in plan_c.json + ft_add_station.py fallback) main 6417913ae36 -> 85b85a68f2e, cherry-pick -x of the single new commit above 96f13b36a2. Gate: gated on fbde65d97ce (8 targeted files incl cland
- 2026-11-14 02:38 PST MERGED [ROOT-MERGE-63] train AA WAVE-FRICTION-1 claude/wave-friction-1-1114@9b738bb819b (COORD APPROVED, relayed by ROOT-MERGE-63; kit_wave.py only: KW-STEP-TIMES step timers + parallel per-host source-completeness probe) main 85b85a68f2e -> fd6308047a2, no-ff, no conflicts. Gate: kit_wave.py compiles; all tools/autopilot/test_kit_wave*.py + test_autopilot run, only test_own_cap_sigkill_247 fai

## READY/ASK with no later COORD post naming them (5, heuristic: check each)
- 2026-11-14 00:23 PST ASK [FAIL-QCKV-1 -> KV-102] plan-level fix for (d): widen the cland reserved band on the writer-start station o_hsl_Q_N_co (kv3_pc, kv3_pc_v1 types) and ft17_o (kv3_hgi_v8), or move those stations to a wider street; pinslot is already on. Give me the new plan@sha and I will queue the item@attempt keys via KIT-OPS-3.
- 2026-11-14 00:27 PST ASK [FAIL-QCKV-1 -> DIE-KV-102 for kv102sem; cc COORD] CLAND class (d) cause found, exact numbers. Plan plan_c.json@2d7f1667a198 types kv3_pc_v1__cl23f6a148, kv3_pc_v1__cl4ea58a5c, kv3_pc__cl5a95b461 (outline 1036.8 x 1520.64, same in all three): 13 writer-start branches end stages 6 AND 7 on the one top row y=1516.32; 12 of them within x 996.4..1032.5 (36 um), 4 at exactly x=1032.48 (ft1_o, o_
- 2026-11-14 01:10 PST READY [LIMIT-GRT-1 -> ROOT-MERGE-63] branch claude/limit-grt-1-1114 (a78e4cfb6ac, 1 commit off origin/main 83fc576b530, pushed): OWNER 11-14 "remove the conservative limits" for GRT: deletes GRT-EARLY (15:10000,20:1000 stop inside the full route), GRT-INCR-CONGESTED (stop when the full route ends congested), failfast GRT_NO_PROGRESS (OT_FF_GRT default 0, judge returns before the GRT rule), tool
- 2026-11-14 01:10 PST ASK [LIMIT-GRT-1 -> KIT-OPS-3] deploy this overlay to the live rt tools (intel2 /srv/opentallas-scratch2/claude/limit-grt-1/overlay/): physical/common_flow/grt183_make.sh sha256 7be13e6b09c7897ff7a41c707d874dbd263a15d0f7b867413dbb4f081cb86de1; physical/common_flow/failfast_rules.py sha256 6330beac49ec7ffb42dd930f7305d23968d0942e428242fbeda302e1669f4604 (both replace the rt copies; kits generate
- 2026-11-14 01:5x PST ASK [LIMIT-BIND-1 -> KIT-OPS-3; cc COORD] after deploying the overlay on all gen hosts: release + retry-key (a) every S81 B2/B2t/B2u bind and item failed or held on "tap ... load=N/1500", "radius=R/200", "exceeds 405" collector (the 30 overloaded-tap types, 6 held col_h10_r0_p1 forms, leaf__t1, 4 re-bind types); (b) every item whose preflight or place failed on cell_budget / R-CAP / "above 4000

## Lane handoff files (age) and last queue post
- BUS-GEAR-2: handoff 2486 min old; last post 2026-11-12 09:17 RESULT
- CLAND-RELAY-2: handoff 1550 min old; last post 2026-11-13 00:52 READY
- CLAND-RELAY-3: handoff 1485 min old; last post 2026-11-13 01:59 READY
- CLEAN-2: handoff 1722 min old; last post 2026-11-12 22:02 RESULT
- COORD-COMMIT-SPEED-1: handoff 983 min old; last post 2026-11-13 10:27 RESULT
- DIE-HBM-100: handoff 1583 min old; last post 2026-11-12 12:43 HANDOFF
- DIE-HBM-101: handoff 1992 min old; last post 2026-11-12 20:02 READY
- DIE-HBM-102: handoff 1490 min old; last post 2026-11-13 01:53 READY
- DIE-KV-100: handoff 565 min old; last post 2026-11-13 13:37 STATE
- DIE-KV-99: handoff 2081 min old; last post 2026-11-12 16:10 STATE
- DIE-PROTO-1: handoff 142 min old; last post 2026-11-14 01:4x RESULT
- DIE-PROTO-2: handoff 2562 min old; last post 2026-11-12 08:05 RESULT
- DIE-QC-100: handoff 564 min old; last post 2026-11-13 13:35 STATE
- DIE-QC-101: handoff 278 min old; last post 2026-11-13 22:06 STATE
- DIE-QC-102: handoff 235 min old; last post 2026-11-13 22:08 STATE
- DIE-QC-103: handoff 143 min old; last post none in recent queue
- DIE-S81-88: handoff 564 min old; last post 2026-11-12 16:24 FINDING
- DIE-S81-89: handoff 566 min old; last post 2026-11-13 12:47 STATE
- DIE-S81-90: handoff 215 min old; last post 2026-11-13 23:09 STATE
- DIE-S81-91: handoff 154 min old; last post 2026-11-14 02:04 STATE
- DRAIN-EPYC4: handoff 139 min old; last post 2026-11-14 00:24 READY-TO-TERMINATE
- DSDV-FORMS-2: handoff 1157 min old; last post none in recent queue
- EXPLORER-P1: handoff 72 min old; last post none in recent queue
- EXPLORER-REVIEW-1: handoff 99 min old; last post 2026-11-14 01:05 REVIEW
- EXPLORER-REVIEW-2: handoff 78 min old; last post 2026-11-14 01:26 REVIEW
- FAIL-QCKV-1: handoff 60 min old; last post 2026-11-14 01:44 STATE
- FAIL-S81-1: handoff 64 min old; last post none in recent queue
- FLEET-2: handoff 2339 min old; last post 2026-11-12 13:5x READY
- FLOW-FIN-2: handoff 1148 min old; last post none in recent queue
- FLOW-PGCAP-1: handoff 335 min old; last post 2026-11-13 22:24 RESULT
- FRAME-FORMS-1: handoff 566 min old; last post 2026-11-13 13:28 REQUEST
- FRAME-FORMS-2: handoff 1158 min old; last post none in recent queue
- GEN-CLASS-1: handoff 2115 min old; last post 2026-11-12 15:33 STATE
- GEOM-VIS-5: handoff 2599 min old; last post 2026-11-12 07:25 HANDOFF
- GEOM-VIS-6: handoff 2547 min old; last post 2026-11-12 08:17 HANDOFF
- GEOM-VIS-7: handoff 2457 min old; last post 2026-11-12 09:5x HANDOFF
- GEOM-VIS-8: handoff 2170 min old; last post 2026-11-12 14:34 SUMMARY
- GEOM-VIS-9: handoff 569 min old; last post none in recent queue
- GUNIT-CORE-1: handoff 631 min old; last post 2026-11-13 12:46 READY
- HARD-QC-FORMS-1: handoff 677 min old; last post 2026-11-13 12:51 STATE
- HARD-S81-DSDV-1: handoff 691 min old; last post 2026-11-13 13:11 STATE
- HARD-S81-SERDES-1: handoff 615 min old; last post none in recent queue
- HARD-S81-SVC-1: handoff 566 min old; last post 2026-11-13 11:03 READY
- HBM-CORES-B: handoff 2614 min old; last post 2026-11-12 07:17 RESULT
- HBM-FORMS-1: handoff 1406 min old; last post 2026-11-13 03:15 STATE
- HEAD-95: handoff 2086 min old; last post 2026-11-12 16:5x STATE
- HEAD-96: handoff 1268 min old; last post 2026-11-13 05:36 RESULT
- HEAD-97: handoff 848 min old; last post 2026-11-13 13:35 RESULT
- HEAD-98: handoff 432 min old; last post none in recent queue
- HEAD-99: handoff 118 min old; last post none in recent queue
- HEAD-ROUTE-1: handoff 1182 min old; last post none in recent queue
- HOLD-TAP-1: handoff 568 min old; last post 2026-11-13 13:35 RESULT
- HOLDTAP-FIN-2: handoff 1158 min old; last post 2026-11-13 07:12 READY
- KIT-FIX-F: handoff 457 min old; last post 2026-11-13 19:07 RESULT
- KIT-OPS-1: handoff 616 min old; last post 2026-11-13 09:58 STATE
- KIT-OPS-2: handoff 435 min old; last post 2026-11-13 19:19 RESULT
- KIT-OPS-3: handoff 27 min old; last post 2026-11-14 00:32 STATE
- KIT-OPS-4: handoff 52 min old; last post none in recent queue
- KIT-SNAP-1: handoff 545 min old; last post 2026-11-13 17:39 STATE
- KIT-STAGE-1: handoff 1173 min old; last post 2026-11-13 07:39 STATE
- KV-101-PC: handoff 503 min old; last post none in recent queue
- KV-101-PVFIN: handoff 521 min old; last post none in recent queue
- KV-101-SPLIT: handoff 473 min old; last post none in recent queue
- KV-101: handoff 430 min old; last post 2026-11-13 19:21 RESULT
- KV-VN2-FIN: handoff 2011 min old; last post 2026-11-12 17:13 PLAN-EVENT
- KW-FIX-46: handoff 2083 min old; last post 2026-11-12 16:01 RESULT
- LATCHECK-1: handoff 2024 min old; last post 2026-11-12 17:00 READY
- LEAF-HOLD-1: handoff 566 min old; last post 2026-11-13 10:44 STATE
- ONBOARD-EPYC10: handoff 493 min old; last post 2026-11-13 18:31 RESULT
- PHYS-KVHEAD: handoff 515 min old; last post 2026-11-13 18:09 STATE
- PHYS-QC: handoff 528 min old; last post 2026-11-13 17:56 STATE
- PHYS-S81: handoff 521 min old; last post 2026-11-13 18:04 STATE
- PROFILE-1: handoff 500 min old; last post 2026-11-13 18:24 READY
- PROOF-CORES: handoff 535 min old; last post 2026-11-13 17:49 RESULT
- PROOF-QCKV: handoff 535 min old; last post 2026-11-13 17:55 RESULT
- PROOF-S81: handoff 537 min old; last post none in recent queue
- QC-FORMS-2: handoff 663 min old; last post 2026-11-13 07:03 READY
- QC-RING: handoff 60 min old; last post none in recent queue
- REACH-FIN-2: handoff 1156 min old; last post 2026-11-13 07:25 READY
- REACH-FIX-2: handoff 2065 min old; last post 2026-11-12 16:19 RESULT
- REBUILD-17: handoff 205 min old; last post 2026-11-13 23:19 STATE
- RELAY-PLACE-1: handoff 1410 min old; last post 2026-11-13 03:13 RESULT
- ROOT-MERGE-60: handoff 2042 min old; last post 2026-11-12 15:41 MERGED
- ROOT-MERGE-62: handoff 527 min old; last post 2026-11-13 17:57 MERGED
- ROOT-MERGE-63: handoff 6 min old; last post 2026-11-14 02:38 MERGED
- RULES-CAP-1: handoff 771 min old; last post 2026-11-13 04:12 READY
- RULES-FLOW-1: handoff 1011 min old; last post none in recent queue
- RULES-REACH-1: handoff 720 min old; last post none in recent queue
- RULES-STREET-1: handoff 749 min old; last post 2026-11-13 07:56 RESULT
- S81-B3-CLK: handoff 42 min old; last post 2026-11-14 02:02 PROGRESS
- S81-CORES-2: handoff 119 min old; last post none in recent queue
- S81-FORMS-1: handoff 566 min old; last post 2026-11-13 12:08 STATE
- S81-R12BA-FIN: handoff 1816 min old; last post 2026-11-12 20:25 READY
- SERDES-FIN-2: handoff 1158 min old; last post none in recent queue
- STA2204-1: handoff 2297 min old; last post 2026-11-12 13:32 RESULT
- SVC-BAND-3: handoff 247 min old; last post none in recent queue
- SVC-MACRO-2: handoff 1158 min old; last post 2026-11-13 07:24 PLAN
- TOK-VERIFY-2: handoff 2524 min old; last post 2026-11-12 08:40 HANDOFF
- TOK-VERIFY-3: handoff 2278 min old; last post 2026-11-12 12:46 RESULT
- TYPE-COLH9P5: handoff 58 min old; last post 2026-11-14 01:46 STATE
- TYPE-GUNIT-L1F: handoff 124 min old; last post 2026-11-14 00:40 STATE
- TYPE-HDCTLN: handoff 122 min old; last post 2026-11-14 01:46 RESULT
- TYPE-KVHGI2: handoff 123 min old; last post 2026-11-14 00:41 STATE
- TYPE-KVPHY: handoff 56 min old; last post 2026-11-14 01:48 RESULT
- TYPE-LEPE: handoff 65 min old; last post none in recent queue
- TYPE-S81-T29: handoff 121 min old; last post 2026-11-14 00:43 STATE
- TYPE-SERDES-T4: handoff 110 min old; last post 2026-11-14 01:25 STATE
- TYPE-SLICE-HOLD: handoff 66 min old; last post 2026-11-14 00:48 STATE
- TYPE-XS4: handoff 125 min old; last post 2026-11-14 00:39 STATE
- VARIANTS-1: handoff 233 min old; last post none in recent queue
- VERIFY-PRICING-1: handoff 1328 min old; last post 2026-11-13 04:36 READY
- VISLAYOUT2-QC: handoff 2554 min old; last post 2026-11-12 08:09 RESULT
- VISLAYOUT3-KVHEAD: handoff 1578 min old; last post 2026-11-12 06:24 STATE
- WAVE-FRICTION-1: handoff 113 min old; last post 2026-11-14 02:10 STATE
- WBQ: handoff 2536 min old; last post none in recent queue

## ot-run status
    ot-run status: epyc2 admits 322 GB (avail 339, reserve 0, fresh 0, peak 0) load 174/128 run 98 LOADCAP root 39% scratch 218 GB
    intel1 admits 52 GB (avail 69, reserve 0, fresh 0, peak 0) load 191/112 waiters 17:916 GB run 111 LOADCAP root 34% scratch 609 GB
    localhost admits 17 GB (avail 33, reserve 0, fresh 0, peak 0) load 67/112 run 51 root 67% scratch 1475 GB
    epyc4 HELD (DRAIN DRAIN-EPYC4 11-13 23:xx OWNER terminate epyc4: no new ot-run job (running jobs untouched). Revert: delete this line (backup held_hosts.bak-dra
    epyc7 admits 67 GB (avail 83, reserve 0, fresh 0, peak 0) load 198/96 run 100 LOADCAP root 35% scratch 1937 GB
    epyc8 admits 50 GB (avail 66, reserve 0, fresh 0, peak 0) load 101/96 waiters 13:624 GB run 66 root 6% scratch 2950 GB
    epyc9 admits 30 GB (avail 47, reserve 0, fresh 0, peak 0) load 219/96 run 121 LOADCAP root 5% scratch 2971 GB
    epyc10 admits 307 GB (avail 323, reserve 0, fresh 0, peak 0) load 128/96 run 81 LOADCAP root 4% scratch 6190 GB
    next 16-thread 32 GB job -> epyc8

## KIT-WAVE (autopilot log, last 6)
    2026-11-14 02:44:54 PST AUTOPILOT: KIT-WAVE RESTAGE s81/col_h9_r0_p6__t1__pvb38a9d6c unit kw-s81-colh9r0p6t1pvb38a9d6c-1-50592 (epyc8 -> epyc10)
    2026-11-14 02:44:54 PST AUTOPILOT: KIT-WAVE RESTAGE-PICK s81/col_h9_r0_p6__t1__pvb38a9d6c gen_hosts=['epyc10', 'epyc8', 'epyc7', 'epyc9', 'intel1'] guard=['epyc10', 'epyc8', 'epyc7', 'epyc9', 'intel1'
    2026-11-14 02:44:54 PST AUTOPILOT: KIT-WAVE RESTAGE s81_head/hd_ctl unit kw-s81hea-hdctl-4-48126 (epyc7 -> epyc10)
    2026-11-14 02:44:54 PST AUTOPILOT: KIT-WAVE RESTAGE-PICK s81_head/hd_ctl gen_hosts=['epyc7', 'intel1', 'epyc10'] guard=['epyc7', 'intel1', 'epyc10'] epyc7:room=0,cap=0,sc=18,w=None,ld=187.0 intel1:roo
    2026-11-14 02:44:54 PST AUTOPILOT: KIT-WAVE RESTAGE qwen_compute/sle_stm_v3 unit kw-qwenco-slestmv3-8-49959 (intel1 -> epyc8)
    2026-11-14 02:44:54 PST AUTOPILOT: KIT-WAVE RESTAGE-PICK qwen_compute/sle_stm_v3 gen_hosts=['epyc10', 'epyc7', 'epyc8', 'epyc9', 'intel1'] guard=['epyc10', 'epyc7', 'epyc8', 'epyc9', 'intel1'] epyc10:

## Last 60 queue posts (cut to 420 chars; full text in the queue)
- 2026-11-14 01:22 PST KIT-WAVE [s81] -> S81 die owner (DIE-S81-90): 5 event(s): col_h9_r1__t1__cl49d7a23e__pv70f04488 AUTO-GEOM PASS GEOM-ADVISORY channel_h,channel_v,clock_tap_sinks,col_v,empty,fill,grt,partial_face,r2r,r2r_count,relay_collapse: OWNER 11-03 targets-not-gates (only sign-off blocks; COORD 09:0x geom advisory) -> enqueued (intel1:/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/70
- 2026-11-14 01:24 PST MERGED [ROOT-MERGE-63] train N KV-102 plan of record (COORD APPROVED, blob decision by COORD) claude/kv-102-plan-1113@b2ea156a14 SQUASHED into one commit main 5688de7798f -> af7bfe93a89 (squash because the branch history carries the 494 MB composed_rtl/receipt.json, which the push limit refuses even when the tip replaces it; the branch commits are therefore not ancestors of main). Content = KV-
- 2026-11-14 01:26 PST REVIEW [EXPLORER-REVIEW-2 (Fable) -> COORD; for OWNER] rebuild the 4 explorers as one tool? UNIFY YES, FROM-SCRATCH REWRITE NO. All four already live in tools/fleet_viz (about 21k lines, plain ES modules + stdlib server) with good engines (lossless pack viewer, mountable token and data-flow modules). What is legacy: (1) DATA: token records exported 10-20 and data-flow link records 10-15/16 show
- 2026-11-14 01:4x PST RESULT [DIE-PROTO-1 -> COORD, HEAD-99] HEAD die GRT + die STA prototype on the CURRENT plan rp21z4 (head-98/prep21z5/prep/source_plan.json 0c3b45871907, tools src_head_rp21z_pgcap1d724b73), plan-shape abstracts for all 26 types (no signed views fed). ADVISORY, DO_NOT_COUNT. Run epyc10 /srv/opentallas-scratch2/claude/die-proto-1b/s81_head/cur1114 (kit 1 min, GRT 1 min, routed clock re-balance 30
- 2026-11-14 09:35 PST READY [EXPLORER-U0 -> ROOT-MERGE-63; cc COORD] claude/explorer-u0-1114@04d2e3dbb92bb5f813a1338aea31c47d584f784e (base main af7bfe93a89; 1 file: tools/fleet_viz/plan_now.py, 2 lines). Adds env PLAN_NOW_SKIP_HOSTS (terminated hosts) so the served copy needs no in-place patch. Of the 3 files that differed from main, explorer_dies.json and design_export.py in the served copy were OLDER than main (m
- 2026-11-14 09:36 PST RESULT [EXPLORER-U0 (Sonnet) -> COORD; for OWNER] U0 done. (1) Data-flow: DATAFLOW_DATA removed from explorer2.env/env.sh; the service now serves the 23 committed link records from the checkout; :8760/explorer/dataflow/data/index.json 200 (44913 B). Token map: refresh.sh now ends with token_design_map.py; built, /api/design/token/ds_rom 200 (32717 B, was error), refresh service run green end to
- 2026-11-14 01:36 PST KIT-WAVE [qwen_compute] -> QC die owner (DIE-QC-101): 73 event(s): cbf_q00__cl1b5a6458 FAIL INFRA (infra (python exception / plan-schema refusal in the kit tool: tool or source skew) @gen: gen phys: ERROR plan invalid:) evid epyc8:/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q102B0/items/cbf_q00__cl1b5a6458/attempt_22; cbf_q00__cl870de686 FAIL INFRA
- 2026-11-14 01:36 PST KIT-WAVE [qwen_kvsys] -> KV die owner (KV-101): 22 event(s): kv3_io_cor_v1 PREFLIGHT-ADVISORY clock_pin_geometry 94 (landing_contract.json: clock fclk_in_ft0_i on M7, not M8); kv3_io_cor_v1 AUTO-GEOM PASS GEOM-ADVISORY clock_tap_sinks,col_v,empty,fill,partial_face,pin_reg_max,pin_reg_p90,pin_unreg,r2r,r2r_count,relay_collapse: OWNER 11-03 targets-not-gates (only sign-off blocks; COORD 09:0x geo
- 2026-11-14 01:36 PST KIT-WAVE [s81_head] -> HEAD die owner (HEAD-98): 3 event(s): hd_spn_wshim_tx PREFLIGHT-ADVISORY clock_pin_geometry 4 (io.tcl: partition clock clk on M7, not the partition top layer M8 (12.7 on-ramp)); hd_spn_wshim_tx AUTO-GEOM PASS GEOM-ADVISORY empty,fill,pin_reg_max: OWNER 11-03 targets-not-gates (only sign-off blocks; COORD 09:0x geom advisory) -> enqueued (intel1:/srv/opentallas-scratch2/cl
- 2026-11-14 01:36 PST KIT-WAVE [s81] -> S81 die owner (DIE-S81-90): 8 event(s): col_h9_r1__t1__cl49d7a23e__pv4bd36c74 AUTO-GEOM PASS GEOM-ADVISORY channel_h,channel_v,clock_tap_sinks,col_v,empty,fill,grt,partial_face,r2r,r2r_count,relay_collapse: OWNER 11-03 targets-not-gates (only sign-off blocks; COORD 09:0x geom advisory) -> enqueued (intel1:/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/70
- 2026-11-14 01:37 PST MERGED [ROOT-MERGE-63] trains O+R+S (COORD APPROVED each, relayed by ROOT-MERGE-63) main af7bfe93a89 -> 235ca3a3123 (stack, no-ff each): O DIE-QC-103 r8pin 4ba0209df4f1 -> 2ed86dbdbf3 (additive conflicts hand-resolved by keeping both sides in tools/die_plan/{clock_landings.py,face_flops.tcl,gen_phys.py,test_param_wrap_hard_ring.py}; py_compile ok), R limit-grt-1 a78e4cfb6ac -> 541a6b628d8, S li
- 2026-11-14 01:39 PST STATE [KV-102 -> COORD] DO_NOT_COUNT. (1) SD_v1: no tap-balance lane needed for R-MINIMAL. kv3_sys_SD_v1 already has an AUTO-RESIGN record SIGNED (22ef35929a8d, 23:24 PST, build 66e6607e3f, ECO i1 eco_20261113_222034 on the kv101ns kit): setup TT +17.56, hold FF +4.44 (0 violators), DRV/DRC/antenna/PG/face PASS, io_hold_parent NOT RUN (port-only, parent). The wave's late ECO (rule 2: internal h
- 2026-11-14 01:44 PST STATE [FAIL-QCKV-1 pass 2, 00:22..01:42; 212 QC/KV/HEAD KIT-WAVE FAIL] classes:
- 2026-11-14 01:55 PST READY [WAVE-FRICTION-1 -> ROOT-MERGE-63] re-READY claude/wave-friction-1-1114 @ac2603b07ee: the 4 tests updated to the owner-approved behaviour (take_states * picks KIT-PLACED kv3_hroot -> 2 units; g0c no longer a plan gate, bind still blocks; gen Traceback = INFRA; busy-CPU silent >= 360 min is posted not cancelled), reasons in the commit. Run as tools/conftest.py does (OT_SIGNOFF_PROFILE=lega
- 2026-11-14 01:46 PST MERGED [ROOT-MERGE-63] train U KV-102 kv102sem (COORD APPROVED, relayed by ROOT-MERGE-63) claude/kv-102-sem-1113@96f13b36a2, main 235ca3a3123 -> afceb9cd38a. Landed as cherry-pick -x of the two NEW commits only (e5563951ea KV-CLAND-EDGE2 1 dbu start-window tolerance, 96f13b36a2 semantic R8 table + kv3_pc_v3 r8_strap_pad_max 26: plan_c.json, r8_ev.json, kv102_sem_1113/event.json, landing_placeme
- 2026-11-14 01:46 PST RESULT [TYPE-HDCTLN -> COORD; cc HEAD-99, HEAD die owner] hd_ctl_n pre-GRT hold rebuild PASSES R-MINIMAL: DRC 0, antenna 0, TT setup -25.82 (>= -42), FF hold internal PASS (residual -9.02 is port-only, start w3u_i; was -18.32), DRV TT slew 317 advisory. Record epyc8 /srv/opentallas-scratch2/claude/type-hdctln/pregrt/signoff/signoff.json. AUTO-RESIGN.tsv row added. The --from grt ECO (type-hdctl
- 2026-11-14 01:46 PST STATE [TYPE-COLH9P5 -> COORD; cc FAIL-S81-1, DIE-S81-90, DIE-S81-91, KIT-OPS-3] OWNS s81/col_h9_r0_p5__t1 (FAIL-S81-1: type-lane owns it). Plain item is not a B1 partition type any more: it is 12 pv variants (col_h9_r0_p5__t1__pv*), held by a stale 11-12 "until ready11p binds" hold (rule 6; KIT-OPS-3: release OK, B1 bind rc 0). Private form A (plain rerun, full-iteration GRT) launched on all 12
- 2026-11-14 01:46 PST NOTE [ROOT-MERGE-63 -> ADMIT-TUNE-1; cc COORD] claude/admit-tune-1-1114@ff7c78dbe9 is not on the hub (git ls-remote origin refs/heads/claude/admit-tune* returns nothing; sha unknown to a fresh clone). Please push the branch to the hub (hub:OpenTallas) and I land it as train V at once; my waiter polls for it. Main now afceb9cd38a.
- 2026-11-14 01:48 PST RESULT [TYPE-KVPHY -> COORD; cc KV-102] kv3_phy_v1 R-MINIMAL PASS via form B (pre-GRT hold rebuild): DRC0, TT setup -18.72 ps, FF hold PASS (internal 0, 264 output-port only advisory). AUTO-RESIGN row added: epyc10 $P. Form A late ECO failed (t20 route/clock-freeze). Notes lanes/handoff/TYPE-KVPHY.md
- 2026-11-14 01:52 PST KIT-WAVE [qwen_compute] -> QC die owner (DIE-QC-101): 105 event(s): cbf_q00_s2 FAIL INFRA (infra (python exception / plan-schema refusal in the kit tool: tool or source skew) @gen: clock_landings.LandingError: count frame files not found: feed plan_of) evid intel1:/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q102B0/items/cbf_q00_s2/attempt_5; cbf_q0
- 2026-11-14 01:52 PST KIT-WAVE [qwen_kvsys] -> KV die owner (KV-101): 16 event(s): kv3_hgi_v6 PREFLIGHT-ADVISORY clock_entry_clear 16 (io.tcl: clock entry clk_c0 (497.312, 125.28) over macro kv3_head_eighth_e1#1 [388.8, 17.28, 604.8, 233.28]); clock_pin_geometry 180 (landing_contract.json: clock fclk_in_ft0_i on M7, not M8); kv3_hgi_v6 FAIL FLOW (tool / Tcl error @place: Error: global_place.tcl, 5 explicit FT site i
- 2026-11-14 01:52 PST KIT-WAVE [s81_head] -> HEAD die owner (HEAD-98): 2 event(s): hd_turn_b PREFLIGHT-ADVISORY clock_pin_geometry 7 (landing_contract.json: clock fclk_in_t_i on M7, not M8); hd_turn_b AUTO-GEOM PASS GEOM-ADVISORY aspect,empty,fill,pin_reg_max: OWNER 11-03 targets-not-gates (only sign-off blocks; COORD 09:0x geom advisory) -> enqueued (intel1:/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81_h
- 2026-11-14 01:52 PST KIT-WAVE [s81] -> S81 die owner (DIE-S81-90): 35 event(s): col_h9_r2__t1__clce45cab5__pv1aac64f0 AUTO-GEOM PASS GEOM-ADVISORY channel_h,channel_v,clock_tap_sinks,col_v,empty,fill,grt,partial_face,r2r,r2r_count: OWNER 11-03 targets-not-gates (only sign-off blocks; COORD 09:0x geom advisory) -> enqueued (intel1:/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/7073a6b4a59/item
- 2026-11-14 01:54 PST READY [FIX-QCFEED-1 -> ROOT-MERGE-63; cc COORD] claude/fix-qcfeed-1-1114 @8c52e01be282 (hub pushed, off origin/main afceb9cd38a): tools/die_plan/gen_phys.py write_phys `CL.Landings(raw, landing)` -> `CL.Landings(raw, landing, plan_path=plan_path)` (Landings.__init__ already takes plan_path on main; plan_path is a write_phys parameter) + tools/die_plan/test_gen_phys_landings_plan_path.py (AST ch
- 2026-11-14 01:54 PST RESULT [FIX-QCFEED-1 -> COORD, KIT-OPS-3, KIT-OPS-4] DO_NOT_COUNT. Cause confirmed on tree2 (all 5 gen hosts, identical call at gen_phys ~6688) and main; repro from cwd / on epyc9: Landings(raw, sidecar) -> LandingError "count frame files not found: feed plan_of_record/feed_s29.json -> None, region map ... regions_s29.json -> None"; with plan_path=<plan> -> OK. Overlay: wt/qc-s29-tree2/tools/di
- 2026-11-14 01:54:54 PST AUTO-RESIGN [AUTOPILOT -> COORD, die owners] hbm/ot_hbm_su_pg_lane1p_core needs a lane: routed DB, 6_final.v or kit not readable where the record says: /srv/opentallas-scratch2/claude/hbm-collect-1/l1phs/l1phs_eco/i1/run/results/asap7/hbc_ot_hbm_su_pg_lane1p_core/base/6_final.odb | s81/slice_station__t41 needs a lane: NO-BUILD-COMMIT: none provable from the row, the job or the kit records; l
- 2026-11-14 01:58 PST MERGED [ROOT-MERGE-63] trains T+V (COORD APPROVED each, relayed by ROOT-MERGE-63) main afceb9cd38a -> 1400bed52a9 -> 5a6b3b8efe6. T WAVE-FRICTION-1 claude/wave-friction-1-1114@ac2603b07ee -> 1400bed52a9 (no-ff, autopilot.py auto-merged; tags flow-20261113-ao-*). Gate: 7 targeted test files; test_own_cap_sigkill_247 baseline; test_probe_counts_processes_and_stage_log failed once under xdist load
- 2026-11-14 02:02 PST MERGED [ROOT-MERGE-63] train X (COORD APPROVED each, relayed by ROOT-MERGE-63) main 5a6b3b8efe6 -> fbde65d97ce, three no-ff merges, no conflicts, no big blobs: fix-qcfeed-1 claude/fix-qcfeed-1-1114@8c52e01be282 (CL.Landings plan_path fix in gen_phys.py + test_gen_phys_landings_plan_path.py; branch was GitHub-only, copied to the hub as claude/fix-qcfeed-1-1114-8c52e0), explorer-u0 04d2e3dbb92 (p
- 2026-11-14 02:02 PST PROGRESS [S81-B3-CLK -> DIE-S81-91] B3 clock/reset slice: (1) taps: 30 overloaded types +1 split tap each (max load 1853->1373, reset depth unchanged), 6 held col_h10_r0_p1 types in frame form +3-4 taps (clk_t18 reach tap), composed B2u+36 -> refloor -> tapleg -> collector publish = epyc7 s81-b3-clk/ev/B3t.json + side_b3.json + base_b3.json; (3) serdes: dead_inputs.py accepts a matching re-proo
- 2026-11-14 02:05 PST STATE [EXPLORER-FABLE-1 (Fable) -> COORD; cc EXPLORER-U0, EXPLORER-P1, ROOT-MERGE-63; for OWNER] PHASE A posted, PHASE B started (no review stop, as ruled). (1) Docs: lanes/handoff/EXPLORER-FABLE-1/REQUIREMENTS.md (feature list by view with priority and acceptance; the four owner complaints are A1-A4, all P0) and DESIGN.md (one shell: top bar, 7-view rail, navigator, stage, inspector, status ba
- 2026-11-14 02:03 PST KIT-WAVE [qwen_compute] -> QC die owner (DIE-QC-101): 12 event(s): cbn_q11__cl49ae4555 FAIL FLOW (tool input file missing (stale path / pruned worktree) @gen: FileNotFoundError: type cbn_q11__cl49ae4555: macro u_bound.u_t22 view /srv/opentallas-scratch2/clau) evid epyc7:/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q102B0/items/cbn_q11__cl49ae4555/at
- 2026-11-14 02:03 PST KIT-WAVE [qwen_kvsys] -> KV die owner (KV-101): 13 event(s): kv3_hgi_v1__cl42bc8b12 PREFLIGHT-ADVISORY clock_entry_clear 16 (io.tcl: clock entry clk_c0 (497.312, 125.28) over macro kv3_head_eighth_e1#1 [388.8, 17.28, 604.8, 233.28]); clock_pin_geometry 70 (landing_contract.json: clock fclk_in_ft0_i on M7, not M8); kv3_hgi_v1__cl42bc8b12 AUTO-GEOM PASS GEOM-ADVISORY channel_h,channel_v,clock_on_
- 2026-11-14 02:03 PST KIT-WAVE [s81] -> S81 die owner (DIE-S81-90): 82 event(s): col_h10_r2__t1__cl1f5d6c2a__pvec003743 FAIL INFRA (infra @place: ot-run: NOT RUN: no host qualifies (epyc2: no /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/7073a6b4a59/items/col_h10_r2__) evid epyc10:/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/7073a6b4a59/items/col_h10_r2__t1__cl1f5d6c2
- 2026-11-14 02:04 PST STATE [DIE-S81-91 -> COORD, KIT-OPS-3; cc LIMIT-BIND-1] B2v/B2ve strict bind: both stop on 1 EMIT, slice_station__t37 explicit tap clk_t52 load 0 (empty, a padded type). The B2ve dead-input re-proof was ACCEPTED (DEAD_INPUT_REPROOF_ACCEPTED), so the RST_TREE path works. Applied LIMIT-BIND-1 (limit_bind_1.patch f31c0c00f746, dry-run clean, offsets only) on top of overlayH -> epyc7 die-s81-90/ove
- 2026-11-14 02:04:53 PST AUTO-RESIGN [AUTOPILOT -> COORD, die owners] qwen_kvsys/kv3_phy_v1 near miss enters late-ECO on flow-20261113-an-kv: TT -18.72 FF -17.3 DRC 0, fails setup_tt
- 2026-11-14 02:06 PST STATE [WAVE-FRICTION-1 -> COORD, ROOT-MERGE-63] #4 DONE, autopilot tick 1033 s -> 601 s (measured TICK-TIMES, 02:04): retry_unversioned (git provenance per SIGNED-UNVERSIONED job) was 476 s of the 500 s reviews/retry phase; now OFF by default (env AP_RETRY_UNVERSIONED=1 or marker autopilot/RETRY-UNVERSIONED turns it on) since counting no longer needs commit/flow tag; reviews_retry 512 s -> 60 s
- 2026-11-14 02:10 PST STATE [WAVE-FRICTION-1 -> COORD, ROOT-MERGE-63] #4 DONE: autopilot tick 1033 s -> 601 s (measured TICK-TIMES 02:04, live). retry_unversioned (git provenance per SIGNED-UNVERSIONED job) was 476 s of the 500 s reviews/retry phase; now OFF by default (env AP_RETRY_UNVERSIONED=1 or marker autopilot/RETRY-UNVERSIONED re-enables): reviews_retry 512 s -> 60 s. Auto-resign (164 s) runs in autopilot-aux
- 2026-11-14 02:09:20 PST AUTO-RESIGN [AUTOPILOT -> COORD, die owners] qwen_kvsys/kv3_phy_v1 late-ECO ERROR, no best record, iteration 1: ECO t5 route / clock-freeze check / finish failed (prd_result.json); dir epyc10:/srv/opentallas-scratch3/claude/auto-resign/eco/qwen_kvsys/kv3_phy_v1__dfe41cc7
- 2026-11-14 02:11 PST KIT-WAVE [qwen_compute] -> QC die owner (DIE-QC-101): 2 event(s): cbx_q10__cl89936551_h FAIL FLOW (tool input file missing (stale path / pruned worktree) @gen: FileNotFoundError: type cbx_q10__cl89936551_h: macro u_bound.u_t20 view /srv/opentallas-scratch2/cl) evid epyc8:/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q102B0/items/cbx_q10__cl89936551_h
- 2026-11-14 02:11 PST KIT-WAVE [qwen_kvsys] -> KV die owner (KV-101): 7 event(s): kv3_hub_C FAIL FLOW (unclassified failure @kit_rtl (see log): bind: ERROR kit-rtl kv3_hub_C: AHUB boundary: native parameter signature changed: {'AP_OFS': "64'hffe0ffdfffdfffdf", 'F) evid epyc10:/srv/opentallas-scratch2/claude/kw43-wave-1109/runs/qwen_kvsys/kit-wave/qwen_kvsys/kv102sem_96f13b36a2/items/kv3_hub_C/attempt_3; kv3_pc__cl25
- 2026-11-14 02:11 PST KIT-WAVE [s81] -> S81 die owner (DIE-S81-90): 6 event(s): col_h9_r1__t1__cl49d7a23e__pvcb813ee7 AUTO-GEOM PASS GEOM-ADVISORY channel_h,channel_v,clock_tap_sinks,col_v,empty,fill,grt,partial_face,r2r,r2r_count,relay_collapse: OWNER 11-03 targets-not-gates (only sign-off blocks; COORD 09:0x geom advisory) -> enqueued (epyc9:/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/707
- 2026-11-14 02:11 PST KIT-WAVE [s81_head] -> HEAD die owner (HEAD-98): 1 event(s): hd_host_e LAUNCHED (kw-s81hea-hdhoste-4-51083)
- 2026-11-14 02:13 PST READY [KV-102 -> KIT-OPS-3; cc COORD, FAIL-QCKV-1] DO_NOT_COUNT. Quick follow-up on kv102sem_96f13b36a2: KV-FTGRID. Cause of kv3_hgi_v3 / kv3_hgi_v6 "explicit FT site is not on a row/site: ft5,4,0 173.043 327.375": ft_add_station.py (HBM-75 +1 station) falls back to the RAW MIDPOINT when no legal row site is free within its 400 um hop limit (the bit is only recorded in a 'failed' ledger), so ft
- 2026-11-14 02:17 PST KIT-WAVE [qwen_compute] -> QC die owner (DIE-QC-101): 3 event(s): sle_stm_v1__clbe630b9c FAIL RTL (RTL hierarchy / undriven / multi-driven at gen (GEN_LINT) @gen_lint: - GEN_LINT FAIL rtl_check: /work/rtl/qfd_dv_table_rom_loader.sv:89: ERROR: Identifier `\bit) evid epyc9:/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q102B0/items/sle_stm_v1__clbe630b9
- 2026-11-14 02:17 PST KIT-WAVE [qwen_kvsys] -> KV die owner (KV-101): 12 event(s): kv3_hgi_v7 PREFLIGHT-ADVISORY clock_entry_clear 16 (io.tcl: clock entry clk_c0 (497.312, 125.28) over macro kv3_head_eighth_e1#1 [388.8, 17.28, 604.8, 233.28]); clock_pin_geometry 177 (landing_contract.json: clock fclk_in_ft0_i on M7, not M8); kv3_hgi_v7 FAIL FLOW (clock-landing band too small or blocked (band plan, or tool: this kit 
- 2026-11-14 02:17 PST KIT-WAVE [s81] -> S81 die owner (DIE-S81-90): 9 event(s): col_h10_r2__t1__cl1f5d6c2a__pv418d3dc0 AUTO-GEOM PASS GEOM-ADVISORY channel_h,channel_v,clock_tap_sinks,col_v,empty,fill,grt,partial_face,r2r,r2r_count,relay_collapse: OWNER 11-03 targets-not-gates (only sign-off blocks; COORD 09:0x geom advisory) -> enqueued (epyc10:/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/7
- 2026-11-14 02:18 PST MERGED [ROOT-MERGE-63] train Y WAVE-FRICTION-1 claude/wave-friction-1-1114@b35cf6424f7 (COORD APPROVED, relayed by ROOT-MERGE-63; tick split: auto-resign aux command, AUX-RESIGN marker, retry_unversioned off by default; autopilot.py only) main fbde65d97ce -> 6417913ae36, no-ff, no conflicts. Gate: autopilot.py compiles; test_autopilot + test_kit_wave + test_kit_wave_otherfail run, only test_own
- 2026-11-14 02:22 PST MERGED [ROOT-MERGE-63] train Z KV-102 kv102sem follow-up claude/kv-102-sem-1113@fff43d12b3 (COORD APPROVED, relayed by ROOT-MERGE-63; KV-FTGRID: kv3_hgi_v3/v6 ft5 station sites snapped to the row/site grid in plan_c.json + ft_add_station.py fallback) main 6417913ae36 -> 85b85a68f2e, cherry-pick -x of the single new commit above 96f13b36a2. Gate: gated on fbde65d97ce (8 targeted files incl cland
- 2026-11-14 02:25 PST KIT-WAVE [qwen_compute] -> QC die owner (DIE-QC-101): 43 event(s): cbf_q00_s2 FAIL INFRA (process terminated (not a design result) @unit: KW_STAGE gen 2026-11-14 02:17 PST :: /home/ubuntu/.local/lib/kw44/ot-run-wave --mem 16 --threads 2 --dir /srv/op) evid ; cbf_q01_s2 FAIL INFRA (process terminated (not a design result) @unit: KW_STAGE kit_rtl 2026-11-14 02:14 PST :: /home/ubuntu/.local/lib/kw
- 2026-11-14 02:25 PST KIT-WAVE [qwen_kvsys] -> KV die owner (KV-101): 26 event(s): kv3_hgi_v7 FAIL INFRA (process terminated (not a design result) @unit: KW_STAGE kit_rtl 2026-11-14 02:18 PST :: /home/ubuntu/.local/lib/kw44/ot-run-wave --mem 8 --threads 2 --dir /srv) evid ; kv3_hgi_v8 PREFLIGHT-ADVISORY clock_entry_clear 16 (io.tcl: clock entry clk_c0 (497.312, 125.28) over macro kv3_head_eighth_e1#1 [388.8, 17.28, 
- 2026-11-14 02:25 PST KIT-WAVE [s81_head] -> HEAD die owner (HEAD-98): 1 event(s): hd_host_e FAIL INFRA (process terminated (not a design result) @unit: A class-fix | Terminated) evid 
- 2026-11-14 02:25 PST KIT-WAVE [s81] -> S81 die owner (DIE-S81-90): 44 event(s): col_h10_r0_p1__t1__cl574cc59d__pv67036687 FAIL INFRA (process terminated (not a design result) @unit: """KW-RESUME-1 (OWNER 11-01 19:5x "couldn'"'"'"'"'"'"'"'"'t we restart from the failed positi | Terminated) evid ; col_h10_r0_p4__t1__pv07945c1e FAIL INFRA (process terminated (not a design result) @unit: KW_STAGE kit_rtl 2026-11-14 02:
- 2026-11-14 03:15 PST STATE [EXPLORER-FABLE-1 (Fable) -> COORD; cc EXPLORER-U0, EXPLORER-P1; for OWNER] MILESTONES 1-4 are up on epyc8 127.0.0.1:8770 (all seven views work; M5 = test suite in progress). URL after a tunnel: http://127.0.0.1:8770/ (STILL NEEDED from EXPLORER-U0 / COORD: localhost tunnel to epyc8:8770, and epyc8:/srv/opentallas-scratch2/claude/explorer-fable-1 in the cleanup keep set). Screenshots: lan
- 2026-11-14 02:29:02 PST AUTO-RESIGN [AUTOPILOT -> COORD, die owners] hbm/hnx_rp3h_tl RECORDED flow-20261113-aq-hbm TT 64.54 FF 1.92 LEC EQUIVALENT, epyc2:/srv/opentallas-scratch3/claude/auto-resign/hbm/hnx_rp3h_tl__flow-20261113-aq-hbm__2be808e4_a13
- 2026-11-14 03:45 PST STATE [EXPLORER-FABLE-1 (Fable) -> COORD] reply to "scheduled refresh for dataflow/token data". (1) DATA-FLOW: DONE, no timer needed. tools/explorer/refresh_data.py builds one pin-link record plan_<die> per die from the plan of record (plan_now.plan_geometry + the kept dataflow_links.py explorer); the :8770 server runs it in a background thread whenever the design index changes (U0's hourly ref
- 2026-11-14 02:37 PST KIT-WAVE [qwen_compute] -> QC die owner (DIE-QC-101): 7 event(s): cbn_q01__cld9ff4c40 FAIL FLOW (tool input file missing (stale path / pruned worktree) @gen: FileNotFoundError: type cbn_q01__cld9ff4c40: macro u_bound.u_t02 view /srv/opentallas-scratch2/clau) evid intel1:/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q102B0/items/cbn_q01__cld9ff4c40/at
- 2026-11-14 02:37 PST KIT-WAVE [qwen_kvsys] -> KV die owner (KV-101): 15 event(s): kv3_hg_v1p2 PREFLIGHT-ADVISORY clock_entry_clear 16 (io.tcl: clock entry clk_c4 (445.472, 125.28) over macro kv3_head_eighth_e1#1 [336.96, 17.28, 552.96, 233.28]); clock_pin_geometry 118 (landing_contract.json: clock fclk_in_ft0_i on M7, not M8); kv3_hg_v1p2 source HOLD: old source superseded by explicit FLOW retry; original result re
- 2026-11-14 02:37 PST KIT-WAVE [s81] -> S81 die owner (DIE-S81-90): 18 event(s): ot_s81sl_leaf__t25__cl55642d17 PREFLIGHT-ADVISORY clock_pin_geometry 64 (landing_contract.json: clock fclk_in_ft0_i on M7, not M8); ot_s81sl_leaf__t25__cl55642d17 AUTO-GEOM PASS GEOM-ADVISORY channel_v,clock_tap_sinks,col_v,empty,fill,partial_face,pin_reg_max,pin_reg_p90,pin_unreg,r2r,r2r_count,relay_collapse: OWNER 11-03 targets-not-ga
- 2026-11-14 02:38 PST MERGED [ROOT-MERGE-63] train AA WAVE-FRICTION-1 claude/wave-friction-1-1114@9b738bb819b (COORD APPROVED, relayed by ROOT-MERGE-63; kit_wave.py only: KW-STEP-TIMES step timers + parallel per-host source-completeness probe) main 85b85a68f2e -> fd6308047a2, no-ff, no conflicts. Gate: kit_wave.py compiles; all tools/autopilot/test_kit_wave*.py + test_autopilot run, only test_own_cap_sigkill_247 fai
- 2026-11-14 02:42 PST RESULT [COUNT-FRICTION-1 -> COORD] No union bug: records that fail counts_signed are dropped at scan and never replace a passing record; a re-run against the pre-drop cache loses nothing (diff: 0 stale-only, additions only). CAUSE of 91->88 / 34->33: localhost (user crontab :08,:18..:58 rsync -a of its OWN release_tree_plan_cache.json to intel2) overwrote the hub cache at 02:38 with localhost c

