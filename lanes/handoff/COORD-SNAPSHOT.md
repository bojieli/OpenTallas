# COORD snapshot 2026-11-14 06:00 PST

Generated every 15 min by ~/coord/bin/coord_snapshot.py (cron on intel2, no LLM). It is the freshest COORD state if Claude stops on a limit. Read it right after ~/coord/CODEX-HANDOFF.md (the hand-written method and lane table) and ~/coord/lanes/handoff/<LANE>.md (each lane's own state). Facts only; the queue is the source.

## main and the merge lane
- origin/main: a3ac578f4fc8
- 2026-11-14 05:11 PST MERGED [ROOT-MERGE-63] train AJ = AF+AG+AH+AI combined (COORD APPROVED each, relayed by ROOT-MERGE-63; one branch, four commits, disjoint files, one xdist gate) main c8268117c6f -> a482236d89b. AF CLAND-GEOM stage inset patch sha256 4ee0dc8e619d (new tools/die_plan/cland_stage_inset.py + test_cland_stage_inset.py) -> 776262fa9a4; AG wave-friction-1 kit-busy claude/wave-friction-1-1114@85b11cdf4
- 2026-11-14 05:25 PST MERGED [ROOT-MERGE-63] train AK (COORD APPROVED each, relayed by ROOT-MERGE-63) main a482236d89b -> 0ff50a33851, two no-ff merges, no conflicts: AK1 wave-friction-1 claude/wave-friction-1-1114@1495a0a3194 (3 commits: LEC_ASYNC missing becomes a warning; place probe checks all copy-back hosts; auto-ECO near-miss limit removed; kit_wave.py/eco_loop.py/gen_phys.py + test_lec_async_missing.py) -> 6
- 2026-11-14 05:37 PST MERGED [ROOT-MERGE-63] train AL KIT-OPS-4 item_env validator (COORD APPROVED, relayed by ROOT-MERGE-63; queue line f2f9473e614): tools/autopilot/kit_wave.py one line, item_env accepts brackets in OT_GEN_SECONDARY_CLOCK like OT_MACRO_MOVES; patch cut from the rt copy vs kit_wave.py.bak-kitops4s (only that hunk, sha256 05a4a559863b, the rt copy carries other unrelated changes that were NOT taken)

## READY/ASK with no later COORD post naming them (15, heuristic: check each)
- 2026-11-14 00:23 PST ASK [FAIL-QCKV-1 -> KV-102] plan-level fix for (d): widen the cland reserved band on the writer-start station o_hsl_Q_N_co (kv3_pc, kv3_pc_v1 types) and ft17_o (kv3_hgi_v8), or move those stations to a wider street; pinslot is already on. Give me the new plan@sha and I will queue the item@attempt keys via KIT-OPS-3.
- 2026-11-14 00:27 PST ASK [FAIL-QCKV-1 -> DIE-KV-102 for kv102sem; cc COORD] CLAND class (d) cause found, exact numbers. Plan plan_c.json@2d7f1667a198 types kv3_pc_v1__cl23f6a148, kv3_pc_v1__cl4ea58a5c, kv3_pc__cl5a95b461 (outline 1036.8 x 1520.64, same in all three): 13 writer-start branches end stages 6 AND 7 on the one top row y=1516.32; 12 of them within x 996.4..1032.5 (36 um), 4 at exactly x=1032.48 (ft1_o, o_
- 2026-11-14 01:10 PST READY [LIMIT-GRT-1 -> ROOT-MERGE-63] branch claude/limit-grt-1-1114 (a78e4cfb6ac, 1 commit off origin/main 83fc576b530, pushed): OWNER 11-14 "remove the conservative limits" for GRT: deletes GRT-EARLY (15:10000,20:1000 stop inside the full route), GRT-INCR-CONGESTED (stop when the full route ends congested), failfast GRT_NO_PROGRESS (OT_FF_GRT default 0, judge returns before the GRT rule), tool
- 2026-11-14 01:10 PST ASK [LIMIT-GRT-1 -> KIT-OPS-3] deploy this overlay to the live rt tools (intel2 /srv/opentallas-scratch2/claude/limit-grt-1/overlay/): physical/common_flow/grt183_make.sh sha256 7be13e6b09c7897ff7a41c707d874dbd263a15d0f7b867413dbb4f081cb86de1; physical/common_flow/failfast_rules.py sha256 6330beac49ec7ffb42dd930f7305d23968d0942e428242fbeda302e1669f4604 (both replace the rt copies; kits generate
- 2026-11-14 01:5x PST ASK [LIMIT-BIND-1 -> KIT-OPS-3; cc COORD] after deploying the overlay on all gen hosts: release + retry-key (a) every S81 B2/B2t/B2u bind and item failed or held on "tap ... load=N/1500", "radius=R/200", "exceeds 405" collector (the 30 overloaded-tap types, 6 held col_h10_r0_p1 forms, leaf__t1, 4 re-bind types); (b) every item whose preflight or place failed on cell_budget / R-CAP / "above 4000
- 2026-11-14 03:00 PST READY [S81-B3-CLK -> DIE-S81-91] B3 clock/reset slice binds clean: epyc7 /srv/opentallas-scratch2/claude/s81-b3-clk run/b/B3v strict bind 0 errors + LATCHECK 873/873 PASS, with OT_S81_SERDES_RST_TREE (all 14 serdes RST_TREE=1) + LIMIT-BIND-1. Plan ev/B3t.json 4b7f1e087434 (B2u + 36 types: 30 overloaded clk_t16/19/21 legs +1 split tap each, max load 1853->1373; 6 col_h10_r0_p1 in frame form with
- 2026-11-14 03:24 PST READY [DIE-S81-92 -> KIT-OPS-3; cc COORD] S81 dead-input overlay: claude/s81-dead-reproof-1114 is MERGED to main (0467a1f3c57, train AC, ROOT-MERGE-63). The dead_inputs re-proof patch part of tools overlay M/ovl_b3 can be dropped at the next S81 src refresh (main now carries it). It must stay in the live B3v src until that refresh; keep the re-proof file results/token_pass/s81_dead_inputs_2148/
- 2026-11-14 04:20 PST READY [TYPE-KVPCF -> KIT-OPS-3; cc COORD, KV-102] DO_NOT_COUNT. qkd_kvs_pcf view REBUILT-EQUIVALENT, no regeneration needed: epyc8 /srv/opentallas-scratch2/claude/dkv100/pdncls/views/qkd_kvs_pcf is the DIEKV-100 detail view of the same signed ODB (bd980c62) with detail_receipt check_ok true, problems [], M6 7564/M7 2827 OBS rects, detail_view.lef sha256 2a908d42208ee400... = the exact out sha o
- 2026-11-14 04:1x PST READY [TYPE-QCSTRAP -> DIE-QC-103; cc COORD, KIT-OPS-3, FAIL-QCKV-1] FAIL-QCKV-1 PORT_BIND bad_straps on sle_sc_v1__cl115da35f + sle_sc_v2 (12 pins each missing) = STALE PLAN STRAPS, not a missing pin: plan zz_s29_qc103_s count_straps[] still declares strap_r8pad_core_red_addr/data/we (OWNER 10-28 sites, plan_qc46+) but the bind of record (s29q103S AND s29q102B0 bind_parent_id_straps.json, pinn
- 2026-11-14 04:03 PST ASK [KIT-OPS-3 -> DIE-QC-103; cc COORD, TYPE-QCSTRAP] s29q103S2 NOT swapped: kit_topology.bind_matches on plan zz_s29_qc103_s2.json (f84e7f271c14, copied in tree2 on epyc9) vs the unchanged bind bind_s29q103S + asbuilt zz_manifest_iso_s29q103S.json: 130 types, 128 match, STALE = exactly sle_sc_v2 and sle_sc_v1__cl115da35f (the two types whose count_straps changed). With the wave strict-bind gat
- 2026-11-14 05:10 PST READY [TYPE-KVPCF -> KIT-OPS-3; cc COORD, KV-102] DO_NOT_COUNT. CLASS FIX for prov_view_sources entries whose only host was epyc4 (28 cores + pcf): 22 views staged and sha-verified on epyc8, epyc9, epyc10 under /srv/opentallas-scratch2/claude/epyc4views-1114/<core>/ (lef, _tt/_ff.lib, provenance.json, pins/gates/meta where present). MATCH RULE: the view dir's provenance/meta cites the SAME sign
- 2026-11-14 04:52 PST ASK [TL-SERDEST14 -> KIT-OPS-3, COORD; cc DIE-S81-92] s81/serdes__t14: last attempt (Codex wave attempt_7, epyc4 gone) FAIL OT_NATIVE_CELL_CAP 460859 > 400000 (native_cell_cap.tcl hard cap; owner 11-14 removes cap; LIMIT-BIND-1 overlay makes it advisory). Item is held (DIE-S81-87 ready11r hold, KW-FIX-45) and not in only_items. Please: release hold, add serdes__t14 to s81 only_items, retry key 
- 2026-11-14 05:20 PST ASK [QC-CORES-HEAD -> KIT-OPS-3; cc WAVE-FRICTION-1, COORD] DOUBLE-BUILD GUARD before 06:20 PST: add all 29 cores to kit_wave.json dies.qwen_compute.auto_core_hold (the 14 sle_cland_{w120_s_s3,w2104_s_s34,w257_e_s6,w269_w_s6,w457_e_s9,w457_s_s9,w517_n_s10,w517_n_s10_1,w517_n_s10_2,w537_e_s10,w537_s_s10,w537_w_s10,w653_w_s12,w94_s_s3}, the 11 sta_cland_{w1081_e_s18,w1574_e_s26,w1574_n_s26,w259_s
- 2026-11-14 05:19 PST READY [S81-B3-SVC -> DIE-S81-91; cc S81-B3-CLK, COORD] B3 svc patch set (private, DO_NOT_COUNT). Location: epyc7 /srv/opentallas-scratch2/claude/s81-b3-svc/patchset_b3svc/. Full plan: plan_b3svc_v2g.json sha a25bd6251dfa = H8 band plan sg1077 + delta + ft + latency; manifest: asbuilt_band_h8_b3svc.json + declared_ties_svc_h8_b3svc.json.
- 2026-11-14 05:47 PST ASK [QC-CORES-HEAD -> KIT-OPS-3] hourly registration batch 1 (prov_view_sources, the wave also auto-picks DRC-0 sign-off records so this is belt and braces): sle_cland_w94_s_s3, sta_cland_w515_s_s10_2, sta_cland_w515_s_s10_3, sta_cland_w537_s_s10_1, sta_cland_w632_e_s11 (signoff dirs in lanes/handoff/QC-CORES.md view-path column; rows already in AUTO-RESIGN.tsv). Next batch once RING-3 adds row

## Lane handoff files (age) and last queue post
- BUS-GEAR-2: handoff 2681 min old; last post 2026-11-12 09:17 RESULT
- CLAND-GEOM: handoff 94 min old; last post 2026-11-14 05:06 STATE
- CLAND-RELAY-2: handoff 1745 min old; last post 2026-11-13 00:52 READY
- CLAND-RELAY-3: handoff 1680 min old; last post 2026-11-13 01:59 READY
- CLEAN-2: handoff 1917 min old; last post 2026-11-12 22:02 RESULT
- COORD-COMMIT-SPEED-1: handoff 1178 min old; last post 2026-11-13 10:27 RESULT
- DIE-HBM-100: handoff 1778 min old; last post 2026-11-12 12:43 HANDOFF
- DIE-HBM-101: handoff 2187 min old; last post 2026-11-12 20:02 READY
- DIE-HBM-102: handoff 1685 min old; last post 2026-11-13 01:53 READY
- DIE-KV-100: handoff 760 min old; last post 2026-11-13 13:37 STATE
- DIE-KV-99: handoff 2276 min old; last post 2026-11-12 16:10 STATE
- DIE-PROTO-1: handoff 87 min old; last post 2026-11-14 04:3x RESULT
- DIE-PROTO-2: handoff 2757 min old; last post 2026-11-12 08:05 RESULT
- DIE-QC-100: handoff 759 min old; last post 2026-11-13 13:35 STATE
- DIE-QC-101: handoff 473 min old; last post 2026-11-13 22:06 STATE
- DIE-QC-102: handoff 430 min old; last post 2026-11-13 22:08 STATE
- DIE-QC-103: handoff 338 min old; last post 2026-11-14 05:12 STATE
- DIE-S81-88: handoff 759 min old; last post 2026-11-12 16:24 FINDING
- DIE-S81-89: handoff 761 min old; last post 2026-11-13 12:47 STATE
- DIE-S81-90: handoff 410 min old; last post 2026-11-13 23:09 STATE
- DIE-S81-91: handoff 173 min old; last post 2026-11-14 02:04 STATE
- DIE-S81-92: handoff 13 min old; last post 2026-11-14 06:3x STATE
- DRAIN-EPYC4: handoff 334 min old; last post 2026-11-14 00:24 READY-TO-TERMINATE
- DSDV-FORMS-2: handoff 1352 min old; last post none in recent queue
- EXPLORER-P1: handoff 267 min old; last post none in recent queue
- EXPLORER-REVIEW-1: handoff 294 min old; last post 2026-11-14 01:05 REVIEW
- EXPLORER-REVIEW-2: handoff 273 min old; last post 2026-11-14 01:26 REVIEW
- FABLE-REVIEW-CLK: handoff 5 min old; last post 2026-11-14 05:54 REVIEW
- FABLE-REVIEW-COL: handoff 24 min old; last post 2026-11-14 05:45 REVIEW
- FABLE-REVIEW-CORES: handoff 46 min old; last post 2026-11-14 05:2x REVIEW
- FAIL-CLASS-2: handoff 39 min old; last post 2026-11-14 05:20 NEEDS-LANE
- FAIL-QCKV-1: handoff 28 min old; last post 2026-11-14 05:31 STATE
- FAIL-S81-1: handoff 29 min old; last post none in recent queue
- FIX-CLASSIFY: handoff 23 min old; last post 2026-11-14 05:40 RESULT
- FIX-HOLDSTALL: handoff 6 min old; last post 2026-11-14 05:40 STATE
- FIX-SELFCONT: handoff 6 min old; last post 2026-11-14 05:53 RESULT
- FIX-YOSYS: handoff 30 min old; last post 2026-11-14 05:29 RESULT
- FLEET-2: handoff 2534 min old; last post 2026-11-12 13:5x READY
- FLOW-FIN-2: handoff 1343 min old; last post none in recent queue
- FLOW-PGCAP-1: handoff 530 min old; last post 2026-11-13 22:24 RESULT
- FRAME-FORMS-1: handoff 761 min old; last post 2026-11-13 13:28 REQUEST
- FRAME-FORMS-2: handoff 1353 min old; last post none in recent queue
- GEN-CLASS-1: handoff 2310 min old; last post 2026-11-12 15:33 STATE
- GEOM-VIS-5: handoff 2794 min old; last post 2026-11-12 07:25 HANDOFF
- GEOM-VIS-6: handoff 2742 min old; last post 2026-11-12 08:17 HANDOFF
- GEOM-VIS-7: handoff 2652 min old; last post 2026-11-12 09:5x HANDOFF
- GEOM-VIS-8: handoff 2365 min old; last post 2026-11-12 14:34 SUMMARY
- GEOM-VIS-9: handoff 764 min old; last post none in recent queue
- GUNIT-CORE-1: handoff 826 min old; last post 2026-11-13 12:46 READY
- HARD-QC-FORMS-1: handoff 872 min old; last post 2026-11-13 12:51 STATE
- HARD-S81-DSDV-1: handoff 886 min old; last post 2026-11-13 13:11 STATE
- HARD-S81-SERDES-1: handoff 810 min old; last post none in recent queue
- HARD-S81-SVC-1: handoff 761 min old; last post 2026-11-13 11:03 READY
- HBM-CORES-B: handoff 2809 min old; last post 2026-11-12 07:17 RESULT
- HBM-FORMS-1: handoff 1601 min old; last post 2026-11-13 03:15 STATE
- HEAD-95: handoff 2281 min old; last post 2026-11-12 16:5x STATE
- HEAD-96: handoff 1463 min old; last post 2026-11-13 05:36 RESULT
- HEAD-97: handoff 1043 min old; last post 2026-11-13 13:35 RESULT
- HEAD-98: handoff 627 min old; last post none in recent queue
- HEAD-99: handoff 313 min old; last post none in recent queue
- HEAD-ROUTE-1: handoff 1377 min old; last post none in recent queue
- HOLD-TAP-1: handoff 763 min old; last post 2026-11-13 13:35 RESULT
- HOLDTAP-FIN-2: handoff 1353 min old; last post 2026-11-13 07:12 READY
- KIT-FIX-F: handoff 652 min old; last post 2026-11-13 19:07 RESULT
- KIT-OPS-1: handoff 811 min old; last post 2026-11-13 09:58 STATE
- KIT-OPS-2: handoff 630 min old; last post 2026-11-13 19:19 RESULT
- KIT-OPS-3: handoff 222 min old; last post 2026-11-14 05:45 ANSWER
- KIT-OPS-4: handoff 2 min old; last post none in recent queue
- KIT-SNAP-1: handoff 740 min old; last post 2026-11-13 17:39 STATE
- KIT-STAGE-1: handoff 1368 min old; last post 2026-11-13 07:39 STATE
- KV-101-PC: handoff 698 min old; last post none in recent queue
- KV-101-PVFIN: handoff 716 min old; last post none in recent queue
- KV-101-SPLIT: handoff 668 min old; last post none in recent queue
- KV-101: handoff 625 min old; last post 2026-11-13 19:21 RESULT
- KV-VN2-FIN: handoff 2206 min old; last post 2026-11-12 17:13 PLAN-EVENT
- KW-FIX-46: handoff 2278 min old; last post 2026-11-12 16:01 RESULT
- LATCHECK-1: handoff 2219 min old; last post 2026-11-12 17:00 READY
- LEAF-HOLD-1: handoff 761 min old; last post 2026-11-13 10:44 STATE
- ONBOARD-EPYC10: handoff 688 min old; last post 2026-11-13 18:31 RESULT
- PHYS-KVHEAD: handoff 710 min old; last post 2026-11-13 18:09 STATE
- PHYS-QC: handoff 723 min old; last post 2026-11-13 17:56 STATE
- PHYS-S81: handoff 716 min old; last post 2026-11-13 18:04 STATE
- PROFILE-1: handoff 695 min old; last post 2026-11-13 18:24 READY
- PROOF-CORES: handoff 730 min old; last post 2026-11-13 17:49 RESULT
- PROOF-QCKV: handoff 730 min old; last post 2026-11-13 17:55 RESULT
- PROOF-S81: handoff 732 min old; last post none in recent queue
- QC-CORES: handoff 4 min old; last post none in recent queue
- QC-FORMS-2: handoff 858 min old; last post 2026-11-13 07:03 READY
- QC-RING: handoff 255 min old; last post none in recent queue
- REACH-FIN-2: handoff 1351 min old; last post 2026-11-13 07:25 READY
- REACH-FIX-2: handoff 2260 min old; last post 2026-11-12 16:19 RESULT
- REBUILD-17: handoff 400 min old; last post 2026-11-13 23:19 STATE
- RELAY-PLACE-1: handoff 1605 min old; last post 2026-11-13 03:13 RESULT
- ROOT-MERGE-60: handoff 2237 min old; last post 2026-11-12 15:41 MERGED
- ROOT-MERGE-62: handoff 722 min old; last post 2026-11-13 17:57 MERGED
- ROOT-MERGE-63: handoff 34 min old; last post 2026-11-14 05:37 MERGED
- RULES-CAP-1: handoff 966 min old; last post 2026-11-13 04:12 READY
- RULES-FLOW-1: handoff 1206 min old; last post none in recent queue
- RULES-REACH-1: handoff 915 min old; last post none in recent queue
- RULES-STREET-1: handoff 944 min old; last post 2026-11-13 07:56 RESULT
- S81-B3-CLK: handoff 179 min old; last post 2026-11-14 03:00 READY
- S81-B3-SVC: handoff 40 min old; last post 2026-11-14 05:19 READY
- S81-CORES-2: handoff 314 min old; last post none in recent queue
- S81-FORMS-1: handoff 761 min old; last post 2026-11-13 12:08 STATE
- S81-R12BA-FIN: handoff 2011 min old; last post 2026-11-12 20:25 READY
- SERDES-FIN-2: handoff 1353 min old; last post none in recent queue
- STA2204-1: handoff 2492 min old; last post 2026-11-12 13:32 RESULT
- SVC-BAND-3: handoff 442 min old; last post none in recent queue
- SVC-MACRO-2: handoff 1353 min old; last post 2026-11-13 07:24 PLAN
- TL-COLH10R0P1: handoff 76 min old; last post none in recent queue
- TL-COLH10R0P4: handoff 69 min old; last post 2026-11-14 04:57 STATE
- TL-COLH9R0P1: handoff 68 min old; last post 2026-11-14 05:41 STATE
- TL-COLH9R0P2: handoff 55 min old; last post 2026-11-14 05:28 STATE
- TL-COLH9R0P3: handoff 69 min old; last post 2026-11-14 04:50 STATE
- TL-COLH9R0P4: handoff 68 min old; last post 2026-11-14 04:51 STATE
- TL-COLH9R0P5: handoff 73 min old; last post 2026-11-14 04:50 FINDING
- TL-COLH9R0P6: handoff 77 min old; last post none in recent queue
- TL-HDHOSTW: handoff 39 min old; last post 2026-11-14 05:20 STATE
- TL-KVLEAFT5: handoff 67 min old; last post 2026-11-14 04:52 STATE
- TL-KVPHY: handoff 73 min old; last post 2026-11-14 04:50 RESULT
- TL-KVSYSSD: handoff 74 min old; last post 2026-11-14 04:50 RESULT
- TL-LEAFT14: handoff 73 min old; last post 2026-11-14 12:40 STATE
- TL-LEAFT34: handoff 70 min old; last post none in recent queue
- TL-LEAFT56: handoff 70 min old; last post 2026-11-14 04:49 STATE
- TL-LEAFT62: handoff 70 min old; last post 2026-11-14 04:55 STATE
- TL-LEAFT72: handoff 60 min old; last post 2026-11-14 04:59 STATE
- TL-QCPHYSD: handoff 42 min old; last post 2026-11-14 13:2x STATE
- TL-QCPHYSDB: handoff 67 min old; last post 2026-11-14 04:53 STATE
- TL-QCREP4: handoff 38 min old; last post 2026-11-14 05:21 STATE
- TL-QCRING-1: handoff 45 min old; last post 2026-11-14 05:55 RESULT
- TL-QCRING-2: handoff 46 min old; last post 2026-11-14 05:35 RESULT
- TL-QCRING-4: handoff 46 min old; last post 2026-11-14 05:56 RESULT
- TL-QCSTAV2: handoff 59 min old; last post 2026-11-14 05:2x STATE
- TL-QCSTBV1: handoff 76 min old; last post 2026-11-14 04:43 STATE
- TL-QCSTBV2: handoff 76 min old; last post 2026-11-14 04:45 STATE
- TL-QCTAIL1: handoff 46 min old; last post none in recent queue
- TL-QCTAPB: handoff 36 min old; last post 2026-11-14 05:40 STATE
- TL-S81PHY: handoff 69 min old; last post 2026-11-14 05:38 STATE
- TL-SERDEST1: handoff 61 min old; last post none in recent queue
- TL-SERDEST14: handoff 67 min old; last post 2026-11-14 05:52 STATE
- TL-SLC1XT8: handoff 47 min old; last post 2026-11-14 05:05 STATE
- TL-SLC3XT1: handoff 72 min old; last post 2026-11-14 04:5x STATE
- TL-SST27: handoff 69 min old; last post 2026-11-14 04:5x STATE
- TL-SST36: handoff 65 min old; last post 2026-11-14 04:54 STATE
- TOK-VERIFY-2: handoff 2719 min old; last post 2026-11-12 08:40 HANDOFF
- TOK-VERIFY-3: handoff 2473 min old; last post 2026-11-12 12:46 RESULT
- TYPE-COLH9P5: handoff 253 min old; last post 2026-11-14 01:46 STATE
- TYPE-COLH9R1: handoff 102 min old; last post 2026-11-14 04:50 STATE
- TYPE-COLH9R2: handoff 101 min old; last post 2026-11-14 05:05 STATE
- TYPE-GUNIT-L1F: handoff 319 min old; last post 2026-11-14 00:40 STATE
- TYPE-GUNIT-L1F2: handoff 74 min old; last post none in recent queue
- TYPE-HDCTLN: handoff 317 min old; last post 2026-11-14 01:46 RESULT
- TYPE-KVHGI2: handoff 318 min old; last post 2026-11-14 03:55 STATE
- TYPE-KVPHY: handoff 251 min old; last post 2026-11-14 01:48 RESULT
- TYPE-LEAFHOLD: handoff 103 min old; last post none in recent queue
- TYPE-LEPE: handoff 260 min old; last post none in recent queue
- TYPE-S81-T29: handoff 316 min old; last post 2026-11-14 00:43 STATE
- TYPE-SERDES-T4: handoff 305 min old; last post 2026-11-14 01:25 STATE
- TYPE-SLICE-HOLD: handoff 261 min old; last post 2026-11-14 00:48 STATE
- TYPE-XS4: handoff 320 min old; last post 2026-11-14 00:39 STATE
- VARIANTS-1: handoff 428 min old; last post none in recent queue
- VERIFY-PRICING-1: handoff 1523 min old; last post 2026-11-13 04:36 READY
- VISLAYOUT2-QC: handoff 2749 min old; last post 2026-11-12 08:09 RESULT
- VISLAYOUT3-KVHEAD: handoff 1773 min old; last post 2026-11-12 06:24 STATE
- WAVE-FRICTION-1: handoff 308 min old; last post 2026-11-14 05:22 STATE
- WBQ: handoff 2731 min old; last post none in recent queue

## ot-run status
    ot-run status: epyc2 admits 166 GB (avail 183, reserve 0, fresh 0, peak 0) load 243/128 run 104 LOADCAP root 42% scratch 180 GB
    intel1 admits 165 GB (avail 182, reserve 0, fresh 0, peak 0) load 293/112 run 141 LOADCAP root 34% scratch 352 GB
    localhost admits 5 GB (avail 133, reserve 0, fresh 0, peak 0) load 168/112 run 81 LOADCAP root 68% scratch 1224 GB
    epyc4 HELD (DRAIN DRAIN-EPYC4 11-13 23:xx OWNER terminate epyc4: no new ot-run job (running jobs untouched). Revert: delete this line (backup held_hosts.bak-dra
    epyc7 admits 30 GB (avail 71, reserve 0, fresh 0, peak 0) load 217/96 waiters 8:400 GB run 111 LOADCAP root 36% scratch 1692 GB
    epyc8 admits 1 GB (avail 65, reserve 0, fresh 0, peak 0) load 86/96 waiters 22:433 GB run 59 root 6% scratch 2243 GB
    epyc9 admits 154 GB (avail 218, reserve 0, fresh 0, peak 0) load 196/96 run 134 LOADCAP root 5% scratch 2709 GB
    epyc10 admits 11 GB (avail 75, reserve 0, fresh 0, peak 0) load 332/96 waiters 14:472 GB run 109 LOADCAP root 4% scratch 5888 GB
    next 16-thread 32 GB job -> epyc2 (would queue)

## KIT-WAVE (autopilot log, last 6)
    2026-11-14 05:57:39 PST AUTOPILOT: SUBMIT 499e158eefe3 qwen_compute/slw_fe_v1__clfe325744__cl08d14f0d intel1:/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29
    2026-11-14 05:57:43 PST AUTOPILOT: SUBMIT 9166b9006415 qwen_compute/slw_fe_v2__clf110fab2 epyc10:/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S/items/
    2026-11-14 05:57:47 PST AUTOPILOT: SUBMIT dba75ab22753 qwen_compute/slw_fw_v1__cl51d45468 epyc9:/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S/items/s
    2026-11-14 05:57:51 PST AUTOPILOT: SUBMIT 156b7a886b57 qwen_compute/slw_hc2__cla3497502__cldc737267 epyc9:/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q10
    2026-11-14 05:57:55 PST AUTOPILOT: SUBMIT 5a2c889df7c7 qwen_compute/slw_sc_v3 intel1:/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q102B0/items/slw_sc_v3/a
    2026-11-14 05:58:01 PST AUTOPILOT: SUBMIT 0fe7cf80a499 s81_head/hd_ctl_n epyc7:/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81_head/kit-wave/s81_head/head_rp21z4_1113/items/hd_ctl_n/attempt_5

## Last 60 queue posts (cut to 420 chars; full text in the queue)
- 2026-11-14 05:20 PST STATE [QC-CORES-HEAD -> TL-QCRING-1, TL-QCRING-2, TL-QCRING-3, TL-QCRING-4, TL-QCSTAV2, TL-QCTAIL1, TL-QCTAPB, TL-QCREP4; cc COORD, KIT-OPS-3, WAVE-FRICTION-1] QC-CORES.md is now the single table (29 cores: lane, form, host, kit, stage, verdict, view path, registered). Ring split (sorted, i mod 4 +1): sle_cland w120_s_s3, w457_e_s9, w517_n_s10_2, w653_w_s12, sta w1574_n_s26, w515_s_s10_2, w632_
- 2026-11-14 05:20 PST ASK [QC-CORES-HEAD -> KIT-OPS-3; cc WAVE-FRICTION-1, COORD] DOUBLE-BUILD GUARD before 06:20 PST: add all 29 cores to kit_wave.json dies.qwen_compute.auto_core_hold (the 14 sle_cland_{w120_s_s3,w2104_s_s34,w257_e_s6,w269_w_s6,w457_e_s9,w457_s_s9,w517_n_s10,w517_n_s10_1,w517_n_s10_2,w537_e_s10,w537_s_s10,w537_w_s10,w653_w_s12,w94_s_s3}, the 11 sta_cland_{w1081_e_s18,w1574_e_s26,w1574_n_s26,w259_s
- 2026-11-14 13:2x PST STATE [TL-QCPHYSD -> COORD; cc DIE-QC-103, KIT-OPS-3] QC phy_serdes/phy_serdes_b/phy_ucie_kv never launched on s29: wave hold_items phy_* since KW-FIX-45 11-11 (only attempt: gen 'hard wrapper requires a placed macro with LEF and TT/FF views'). Real cause: plan contents have lib only, no lef/origin_um/outline_um (LEFs exist in physical/qwen_missing_phy). Private patched plan gets past that; nex
- 2026-11-14 05:18 PST KIT-WAVE [qwen_compute] -> QC die owner (DIE-QC-101): 9 event(s): sle_hc0__cl05696ed1 PLAN-CHANGE (rule C) density 0.7801 cells/um2 >= 0.42: PLAN-CHANGE sle_hc0__cl05696ed1: outline 622.08 x 717.12 (soft 446106 um2) carries 347989 cells; grow the soft area x1.86 (to 828545 um2) or split into 2 types (rule C, advisory; die owner ranks a plan change first); sle_hc0__cl05696ed1 PREFLIGHT-ADVISORY 
- 2026-11-14 05:18 PST KIT-WAVE [qwen_kvsys] -> KV die owner (KV-101): 3 event(s): kv3_hgi_v3 PREFLIGHT-ADVISORY clock_entry_clear 16 (io.tcl: clock entry clk_c0 (497.312, 125.28) over macro kv3_head_eighth_e1#1 [388.8, 17.28, 604.8, 233.28]); clock_pin_geometry 174 (landing_contract.json: clock fclk_in_ft0_i on M7, not M8); kv3_hgi_v3 AUTO-GEOM PASS GEOM-ADVISORY channel_h,channel_v,clock_on_macro,clock_tap_sinks,co
- 2026-11-14 05:18 PST KIT-WAVE [s81] -> S81 die owner (DIE-S81-90): 21 event(s): col_h10_r1__t1__cl95b37463__pv1a6ec9c2 PREFLIGHT-ADVISORY clock_entry_clear 4 (io.tcl: clock entry clk_c8 (795.424, 1209.38) over macro ot_v41_bf_col3_c#9 [691.308, 1045.452, 899.556, 1244.172]); col_h10_r1__t1__cl95b37463__pv1a6ec9c2 AUTO-GEOM PASS GEOM-ADVISORY channel_h,channel_v,clock_tap_sinks,col_v,grt,partial_face,r2r,r2r_count: 
- 2026-11-14 05:18 PST STATE [KIT-WAVE -> COORD, QC die owner (DIE-QC-101)] WAIT-CHILD qwen_compute: 16 parent type(s) wait on 29 child core(s) without a routed view: waiting 29 (qfd_dv_s5_ctl_repair4_leaf qfd_dv_s8_station_tail1 qfd_dv_s8_tap_bounded sle_cland_w120_s_s3 sle_cland_w2104_s_s34 sle_cland_w257_e_s6 sle_cland_w269_w_s6 sle_cland_w457_e_s9 sle_cland_w457_s_s9 sle_cland_w517_n_s10 sle_cland_w517_n_s10_1 sl
- 2026-11-14 05:18 PST STATE [KIT-WAVE -> COORD, KV die owner (KV-101)] WAIT-CHILD qwen_kvsys: 1 parent type(s) wait on 2 child core(s) without a routed view: waiting 2 (qkd_hr_core_order qkd_hr_core_peer). requested = the wave builds it as a core row; building = an autopilot job already runs it (no second build); held-by-hand = dies.qwen_kvsys.auto_core_hold.
- 2026-11-14 05:18 PST STATE [KIT-WAVE -> COORD, S81 die owner (DIE-S81-90)] WAIT-CHILD s81: 1 parent type(s) wait on 1 child core(s) without a routed view: waiting 1 (s81p_slice_station__t51_ot_s81_station_t51_native_w). requested = the wave builds it as a core row; building = an autopilot job already runs it (no second build); held-by-hand = dies.s81.auto_core_hold.
- 2026-11-14 05:19 PST READY [S81-B3-SVC -> DIE-S81-91; cc S81-B3-CLK, COORD] B3 svc patch set (private, DO_NOT_COUNT). Location: epyc7 /srv/opentallas-scratch2/claude/s81-b3-svc/patchset_b3svc/. Full plan: plan_b3svc_v2g.json sha a25bd6251dfa = H8 band plan sg1077 + delta + ft + latency; manifest: asbuilt_band_h8_b3svc.json + declared_ties_svc_h8_b3svc.json.
- 2026-11-14 05:20 PST RESULT [FAIL-CLASS-2 -> COORD; cc KIT-OPS-3, KIT-OPS-4, WAVE-FRICTION-1] Answer to "all class-blocking flow failures identified and fixed?": NO, identified yes, fixed not all. Table lanes/FAIL-CLASS-1114.tsv (46 classes, 12 h from 11-13 17:15, S81/HEAD/QC/KV, HBM skipped, 860 KIT-WAVE FAIL lines, real error strings, distinct items; route-stage from CLASSIFY lines). Cleared with no recurrence af
- 2026-11-14 05:20 PST NEEDS-LANE [FAIL-CLASS-2 -> COORD; cc KIT-OPS-3] unowned flow classes, error / items / example: (a) KIT_NOT_SELF_CONTAINED + FileNotFound kit-ops-1/drt73-aor3/landed_sidecar_aor3.json: 9 items QC/S81, last 04:12, ex cbn_q00__cldbcda913, ot_s81sl_leaf__t62 (kit recipe must copy sidecar into the kit); (b) OT_HOLD_STRUCTURAL/HOLD_STALL NEEDS_RTL: 16 items S81/KV, last 04:52, ex eng__t1, leaf t25 (
- 2026-11-14 05:20 PST STATE [TL-HDHOSTW -> COORD; cc HEAD-99] hd_host_w form B BLOCKED as a private kit: ANY outline growth (even +170.64 um north with nothing else moved) regrows the density clock-tap set (12 -> 11 taps), so the kit PORT_BIND fails (netlist clk_t11 extra, 2734 vs 2733 bits), and re-exporting kit RTL fails (published wrapper cohort check; landing raw reset rst_rl_36 has no wavefront driver). Growth 
- 2026-11-14 05:20 PST DONE [KIT-OPS-3 -> COORD; cc DIE-QC-103, QC-CORES-HEAD, WAVE-FRICTION-1] (1) QC s29q103S2 swapped 70fe25e5294: bind_out bind_s29q103S2, asbuilt zz_manifest_iso_s29q103S2.json, sidecar zz_sidecar_s29q103S2.json, plan zz_s29_qc103_s2.json f84e7f271c14, event s29q103S2 (gate_events_extra); bind_matches 130/130 0 stale; bind dir + bind.f inputs + tree2 additions synced to epyc7/8/intel1/epyc10; bot
- 2026-11-14 05:22 PST STATE [WAVE-FRICTION-1 -> COORD, KIT-OPS-3] auto_core_hold shape OK: the live code reads dies.<die>.auto_core_hold as a plain list of module names (set(d.get("auto_core_hold") or [])); on qwen_compute it is a list of 29 and all 29 modules in state wait_child[qwen_compute] are in it (29 of 29 held, 0 unheld), so the wave requests none of them; core wave rows started on qwen_compute after the fir
- 2026-11-14 05:21 PST STATE [TL-QCREP4 -> COORD; cc DIE-QC-103, KIT-OPS-3] qfd_dv_s5_ctl_repair4_leaf: 2 private kits (util 0.5/0.3) running via ot-run on epyc7 fleet; waiter armed; handoff TL-QCREP4.md
- 2026-11-14 05:23 PST STATE [TL-QCTAPB -> COORD; cc DIE-QC-103] qfd_dv_s8_tap_bounded: 2 private forms (a util .5, b util .35) launched via ot-run on epyc9, kits tl-qcstap/rk; will AUTO-RESIGN + ask KIT-OPS-3 on pass
- 2026-11-14 05:25 PST MERGED [ROOT-MERGE-63] train AK (COORD APPROVED each, relayed by ROOT-MERGE-63) main a482236d89b -> 0ff50a33851, two no-ff merges, no conflicts: AK1 wave-friction-1 claude/wave-friction-1-1114@1495a0a3194 (3 commits: LEC_ASYNC missing becomes a warning; place probe checks all copy-back hosts; auto-ECO near-miss limit removed; kit_wave.py/eco_loop.py/gen_phys.py + test_lec_async_missing.py) -> 6
- 2026-11-14 05:28 PST STATE [TL-COLH9R0P2 -> COORD; cc DIE-S81-92, KIT-OPS-3] CONFIRMED: with main ot_dp_clk_landing.sv in the src overlay, col_h9_r0_p2__t1__cl0045af7b__pve183b536 passes gen_lint (rc 0) and proceeds to place (fa, ~/type-s81-colh9r0p2/fa); fb (cl9f71e63d pvef55eb84) still in gen. Wave fix for ALL s81 pv GEN_LINT LOCAL failures: put that one file into the wave src (KIT-OPS-3). Will report place/route
- 2026-11-14 05:29 PST RESULT [FIX-YOSYS -> COORD; cc KIT-OPS-4, ROOT-MERGE-63] (a) svc_hi_dsdv_svc_rs t2-t4 do-yosys Error 241 = earlyoom SIGTERM on epyc10 (mem 3%, yosys 10-12 GB), not RTL, already INFRA and relaunched 05:08; root = host memory admission (ADMIT-TUNE-1 owns). (b) yosys rc143 = earlyoom SIGTERM at gen_lint (epyc9/intel1), was misclassified RTL: kit_wave.py rule now INFRA for rc 143 (live in kw38/rt, 
- 2026-11-14 05:31 PST KIT-WAVE [qwen_compute] -> QC die owner (DIE-QC-101): 15 event(s): sle_sc_v1__cl115da35f FAIL FLOW (unclassified failure @unit (see log): KW_STAGE preflight 2026-11-14 04:56 PST :: /home/ubuntu/.local/lib/kw44/ot-run-wave --mem 8 --threads 2 --dir /srv/opental) evid ; sle_sc_v2 FAIL FLOW (unclassified failure @unit (see log): KW_STAGE preflight 2026-11-14 05:04 PST :: /home/ubuntu/.local/lib/kw
- 2026-11-14 05:31 PST KIT-WAVE [qwen_kvsys] -> KV die owner (KV-101): 6 event(s): kv3_hub_C FAIL FLOW (unclassified failure @kit_rtl (see log): bind: ERROR kit-rtl kv3_hub_C: AHUB boundary: native parameter signature changed: {'AP_OFS': "64'hffe0ffdfffdfffdf", 'F) evid epyc2:/srv/opentallas-scratch2/claude/kw43-wave-1109/runs/qwen_kvsys/kit-wave/qwen_kvsys/kv102sem_ftgrid/items/kv3_hub_C/attempt_6; kv3_pc_v3 FAIL IN
- 2026-11-14 05:31 PST KIT-WAVE [s81_head] -> HEAD die owner (HEAD-98): 1 event(s): hd_turn_b FAIL PLAN (gen wrote no kit (hard / skipped type in the plan) @gen: GEN_NO_KIT: gen.py exit 0 but wrote no kit for this type (hard type? see gen --hard-wrappers)) evid epyc7:/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81_head/kit-wave/s81_head/head_rp21z4_1113/items/hd_turn_b/attempt_6
- 2026-11-14 05:31 PST KIT-WAVE [s81] -> S81 die owner (DIE-S81-90): 46 event(s): col_h10_r0_p1__t1__cl574cc59d__pvb095fa2f FAIL PLAN (gen wrote no kit (hard / skipped type in the plan) @gen: GEN_NO_KIT: gen.py exit 0 but wrote no kit for this type (hard type? see gen --hard-wrappers)) evid epyc7:/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/7073a6b4a59/items/col_h10_r0_p1__t1__cl574cc59d__pvb
- 2026-11-14 05:31 PST STATE [FAIL-QCKV-1 pass 6, 05:03..05:31; 8 fails] No CLAND failure this window. New, one type each (real design/plan, not infra):
- 2026-11-14 05:33 PST STATE [KV-102 -> COORD, FAIL-QCKV-1, TYPE-KVAHUB] DO_NOT_COUNT. (1) kv3_pc_v3 gen "invalid bound R8 count declaration: strap_r8pad_hsl3_fi": NOT a stale plan_c count_straps entry (no r8pad entry exists in any KV type's count_straps; scanned all 56). It is a TOOL hard-code: tools/die_plan/bound_r8_straps.py declared() requires every r8pad strap to be exactly 4 bits (width != 4, ports != ('input'
- 2026-11-14 05:45 PST REVIEW [FABLE-REVIEW-COL -> COORD; cc DIE-S81-92, TYPE-COLH9R1, TYPE-COLH9R2, KIT-OPS-3] S81 ROM column family (216 types, col_h9/col_h10 r0 r1 r2). Full text lanes/handoff/FABLE-REVIEW-COL.md; renders epyc7 /srv/opentallas-scratch2/claude/fable-review-col/png/ and intel2 ~/fable-review-col/png/ (col_h9_r1_B3v.png, col_h9_r0_p2_B3v.png, col_h10_r2_B3v.png, col_h10_r1_B3w_plan.png, col_h9_r1_B3w
- 2026-11-14 05:35 PST RESULT [TL-QCRING-2 -> QC-CORES-HEAD; cc DIE-QC-103, TL-QCSTAV2] SIGNED: sle_cland_w94_s_s3 (epyc10) and sta_cland_w515_s_s10_3 (epyc2); AUTO-RESIGN rows added. Other 4 (sle w2104_s_s34, w457_s_s9, w537_e_s10, sta w259_s_s6) still in route/DRT; waiter re-armed.
- 2026-11-14 05:40 PST STATE [FIX-HOLDSTALL -> COORD; cc KIT-OPS-4, KIT-OPS-3, DIE-S81-92, TYPE-LEAFHOLD] OT_HOLD_STALL class (16 items S81/KV) is REAL internal FF hold, not port-only: S81 leaf t42 post-CTS hold has 2923 reg>reg endpoints (ws -206, cross-tap 2882 from tap window 182) + 597 input-port (-54); 0 output-port. Stall cause: in-flow GRT hold repair re-routes per buffer (200 buffers/1400 s, 7 chunks, viol 31
- 2026-11-14 05:40 PST RESULT [FIX-CLASSIFY -> COORD; cc KIT-OPS-4, ROOT-MERGE-63, KV-102, QC-CORES-HEAD] (a)+(b) are ONE class: the 5+1 items (HEAD hd_ctl a3, hd_turn_b a2, hd_spn_wshim_rx a2, hd_spn_wshim_tx a2; QC tt_ctlm a2/a4) all failed with kit_wave place RENDER_MISSING; the "finished 3_5_place .odb" log tail is just the stage's timing table. Resumed attempts reuse the finished place DB so they have no run/lay
- 2026-11-14 05:37 PST MERGED [ROOT-MERGE-63] train AL KIT-OPS-4 item_env validator (COORD APPROVED, relayed by ROOT-MERGE-63; queue line f2f9473e614): tools/autopilot/kit_wave.py one line, item_env accepts brackets in OT_GEN_SECONDARY_CLOCK like OT_MACRO_MOVES; patch cut from the rt copy vs kit_wave.py.bak-kitops4s (only that hunk, sha256 05a4a559863b, the rt copy carries other unrelated changes that were NOT taken)
- 2026-11-14 05:38 PST STATE [TL-S81PHY -> COORD; cc DIE-S81-92, KIT-OPS-3] phy__t1 private kit generated (epyc10 tl-s81phy/gen/phy__t1, hard-wrappers). FINDING: bound RTL s81p_phy__t1_bound instantiates u_core with #(.MUT(0),.TREFI_PB(240)) but the K-only macro blackbox ot_hbm3e_phy_v41x_aw30_e8p5_k_bb.v declares no parameters -> RTL_LINT FAIL (so the wave kit will hit the same). Private patch: added parameter MUT/T
- 2026-11-14 05:39 PST KIT-WAVE [qwen_compute] -> QC die owner (DIE-QC-101): 3 event(s): sle_st_b_v2__cl14c98df5__pvcd986c42 PLAN-CHANGE (rule C) density 0.4409 cells/um2 >= 0.42: PLAN-CHANGE sle_st_b_v2__cl14c98df5__pvcd986c42: outline 622.08 x 1339.2 (soft 822041 um2) carries 362444 cells; grow the soft area x1.05 (to 862962 um2) or split into 2 types (rule C, advisory; die owner ranks a plan change first); sle_st_
- 2026-11-14 05:39 PST KIT-WAVE [qwen_kvsys] -> KV die owner (KV-101): 4 event(s): kv3_hgi_v8 PREFLIGHT-ADVISORY clock_entry_clear 16 (io.tcl: clock entry clk_c0 (497.312, 125.28) over macro kv3_head_eighth_e1#1 [388.8, 17.28, 604.8, 233.28]); clock_pin_geometry 161 (landing_contract.json: clock fclk_in_ft0_i on M7, not M8); kv3_hgi_v8 FAIL FLOW (clock-landing band too small or blocked (band plan, or tool: this kit a
- 2026-11-14 05:39 PST KIT-WAVE [s81] -> S81 die owner (DIE-S81-90): 35 event(s): col_h10_r1__t1__cl95b37463__pv74ebbc00 PREFLIGHT-ADVISORY clock_entry_clear 4 (io.tcl: clock entry clk_c8 (795.424, 1209.38) over macro ot_v41_bf_col3_c#9 [691.308, 1045.452, 899.556, 1244.172]); col_h10_r1__t1__cl95b37463__pv74ebbc00 AUTO-GEOM PASS GEOM-ADVISORY channel_h,channel_v,clock_tap_sinks,col_v,grt,partial_face,r2r,r2r_count: 
- 2026-11-14 05:40 PST STATE [TL-QCTAPB -> COORD; cc DIE-QC-103] qfd_dv_s8_tap_bounded form a do-yosys 241 = earlyoom SIGTERM on epyc9 13:33 UTC (yosys pid 2123560, host mem 3%); not a netlist fault. Reran a unchanged with --mem 64 (epyc2) beside b (intel1) and c (no keep_hierarchy, epyc2)
- 2026-11-14 05:40 PST DONE [KIT-OPS-3 -> COORD; cc FABLE-REVIEW-COL, TYPE-COLH9R1, WAVE-FRICTION-1, COUNT-FRICTION-1] (1) R-COL-3 canary armed 8734f0d15a4: gen_phys had RELAY_MID_RE as a hard constant (item_env could not reach config.mk), so overlay = one line reading OT_RELAY_MID_RE from the gen env (default unchanged) in S81 B3v/src (epyc7/8/9/intel1/epyc10) + B3w/src (epyc7); item_env OT_RELAY_MID_RE=^(.*[._]u_y_
- 2026-11-14 05:41 PST STATE [TL-COLH9R0P1 -> COORD; cc DIE-S81-92, KIT-OPS-3] confirmed: col_h9_r0_p1 pv fa_b49c16c8 on B1 src_pgL passes GEN_LINT (rtl_check PASS) -> LOCAL param cause confirmed; 6 forms in gen/preflight, continuing to route.
- 2026-11-14 06:1x PST STATE [DIE-S81-92 -> COORD; cc FABLE-REVIEW-COL, KIT-OPS-3, TL-S81PHY] B3x opened (queued on epyc7, 22 of 48 GB admitted; chainY92.sh, log M/log/B3x.log, out run/b/B3x; B3w bind still running, B4 svc bind result still pending, all parallel). B3x = B3w + (1) R-COL-2 via the EXISTING plan lever budgets.gutter_block_um=12 + gutter_block_min_span_um=50 + gutter_block_types = the 12 col bases (216 c
- 2026-11-14 05:45 PST RESULT [TL-QCRING-4 -> COORD; cc DIE-QC-103, QC-CORES-HEAD] sta_cland_w537_s_s10_1 SIGNED (R-MINIMAL) on epyc2 kit (TL-QCSTAV2 build, no rebuild); AUTO-RESIGN row added. Remaining 5 (sle_cland_w269_w_s6, sle_cland_w517_n_s10_1, sle_cland_w537_w_s10, sta_cland_w1574_e_s26, sta_cland_w515_s_s10_1) still running; waiter re-armed (signoff or unit exit).
- 2026-11-14 05:45:00 PST AUTO-RESIGN [AUTOPILOT -> COORD, die owners] qwen_compute/sle_cland_w94_s_s3 needs a lane: NO-BUILD-COMMIT: none provable from the row, the job or the kit records; left for a lane | qwen_compute/sta_cland_w515_s_s10_3 needs a lane: NO-BUILD-COMMIT: none provable from the row, the job or the kit records; left for a lane
- 2026-11-14 05:45 PST RESULT [TL-QCRING-1 -> COORD; cc QC-CORES-HEAD, TL-QCSTAV2] SIGNED (DRC 0, TT wns +27/+30, internal hold >=+2; FF sdc-min -22/-28 is port-only, advisory): sta_cland_w515_s_s10_2, sta_cland_w632_e_s11 (epyc2 tl-qcstav2). AUTO-RESIGN rows added. 5 more (sle w120_s_s3, w457_e_s9, w517_n_s10_2, w653_w_s12, sta w1574_n_s26) still running on epyc10.
- 2026-11-14 05:45 PST ANSWER [KIT-OPS-3 -> HEAD-99; cc COORD] HEAD in the wave has NO strict-bind out and NO as-built netlist dir: s81_head kit_rtl.mode is "script" (not "bind"), and kit_wave.json carries no bind_out/asbuilt for it. What the wave runs per type (cwd = the wave src, TYPE/OUT/PLAN set by kit_wave): bash /srv/opentallas-scratch2/claude/kw45/src_head_rp21z_pgcap1d724b73/physical/die_plan/s81_head/kit_wav
- 2026-11-14 05:47 PST STATE [QC-CORES-HEAD -> COORD; cc KIT-OPS-3, TL-QCRING-3, TL-QCSTAV2] STATE: 7/29 signed, 0 exited without sign-off, 22 not signed (19 running; sta_region_nb0 and the 3 qfd_dv cores still without a kit in the table: tail1/tapb/rep4 in progress per TL-QCTAPB, region_nb0 queued 64 GB on intel1). Signed: sle_cland_w257_e_s6, sle_cland_w94_s_s3, sta_cland_w1081_e_s18, w515_s_s10_2, w515_s_s10_3, w5
- 2026-11-14 05:47 PST ASK [QC-CORES-HEAD -> KIT-OPS-3] hourly registration batch 1 (prov_view_sources, the wave also auto-picks DRC-0 sign-off records so this is belt and braces): sle_cland_w94_s_s3, sta_cland_w515_s_s10_2, sta_cland_w515_s_s10_3, sta_cland_w537_s_s10_1, sta_cland_w632_e_s11 (signoff dirs in lanes/handoff/QC-CORES.md view-path column; rows already in AUTO-RESIGN.tsv). Next batch once RING-3 adds row
- 2026-11-14 06:3x PST STATE [DIE-S81-92 -> COORD; cc KIT-OPS-3, FIX-RELAYPOLY] (1) B3x was already ADMITTED on epyc7 (oth-ubuntu-4001904) before the move order and is past G0 setup; the bind inputs (B3s elab out 7.5 GB, kw45 src 48 GB, r12bA out 7.6 GB) live on epyc7 scratch, so moving to epyc9/intel1 means a ~60 GB copy = slower than staying. Not moved. (2) FIX-RELAYPOLY: plan key + r1 polyline written in lanes/han
- 2026-11-14 05:47 PST STATE [QC-CORES-HEAD -> COORD; cc KIT-OPS-3] auto_core_hold item closed (confirmed). QC-CORES.md now lists the 4 non-ring cores with their forms/hosts (tail1 rk+rkb intel1; tapb a,c epyc2 + b intel1; rep4 a,b intel1; sta_region_nb0 intel1) and shows DRC / TT WNS / FF hold from signoff.json per core. STATE: 8/29 signed (+sle_cland_w... see table), 0 exited without sign-off, 0 failure classes.
- 2026-11-14 05:48 PST RESULT [TL-QCRING-3 -> COORD; cc DIE-QC-103, QC-CORES-HEAD] sle_cland_w257_e_s6 SIGNED (TT setup +141 ps, FF hold +11.35, DRC 0; epyc10 die-qc-103/rk2) and sta_cland_w1081_e_s18 SIGNED (TT +199, hold +5.25, DRC 0; epyc2 tl-qcstav2/rk); AUTO-RESIGN rows added. Other 4 (sle_w517_n_s10, sle_w537_s_s10, sta_w515_s_s10, sta_w537_s_s10) still running.
- 2026-11-14 05:52 PST STATE [TL-SERDEST14 -> COORD; cc KIT-OPS-3, DIE-S81-92] serdes__t14 attempt_1 (wave unit kw-s81-serdest14-1, epyc8) passed preflight with cap advisory and then died in yosys ABC (do-yosys Error 241, peak 1.4 GB, 7 min; epyc8 had 37 GB available of 1007 at the time) = host memory kill, INFRA not design. Attempt_2 launched 05:39 on the same inputs (justified: infra class, host pressure). Followin
- 2026-11-14 05:53 PST RESULT [FIX-SELFCONT -> COORD, KIT-OPS-3, KIT-OPS-4; cc S81 die owner] t62 a8 (epyc7) got PAST the sidecar-missing point (kit_rtl, kit_topology OK, gen read the sidecar) but FAILED gen with clock_landings.LandingError: clock landing lk_WN0: expected one whole-partition region. Cause = the stale type_args: the aor3 sidecar (made for plan_Aor3, plan overlay since reverted) is applied as the 2nd -
- 2026-11-14 05:54 PST REVIEW [FABLE-REVIEW-CLK -> COORD; cc DIE-S81-92, S81-TAPSKEW, FIX-HOLDSTALL, KIT-OPS-3] S81 leaf cross-tap hold: cause measured, rule R-CLOCK-7. Full text lanes/handoff/FABLE-REVIEW-CLK.md section 1. MEASURED on ot_s81sl_leaf__t42 4_cts.odb (FF, before hold repair; intel1 /srv/opentallas-scratch2/claude/fable-review-clk/hs): 2,923 reg-to-reg endpoints, worst -206.2; 2,882 cross-tap, only 41 sa
- 2026-11-14 14:00 PST STATE [TYPE-KVAHUB -> KV-102; cc COORD] DO_NOT_COUNT. qkd_ahub k1 first pass: LEC EQUIVALENT (exit 0) with the new AP_OFS; place stopped at 3_5 (detail_place): the ahub_pre_dpl.tcl anchor u_leaf.u_core.lm_b[1] no longer exists (with AP_OFS lanes 0-2 all -33, yosys merges lm_b[1]; LEC proves function equal). Dropped only that anchor (1 of 252; orig kept as ahub_pre_dpl.tcl.orig) and relaunched u
- 2026-11-14 07:55 PST RESULT [EXPLORER-FABLE-1 (Fable) -> COORD; for OWNER; READY -> ROOT-MERGE-63] "slice_station__t12: many tiles could not be decoded": ROOT CAUSE FOUND AND FIXED, live on :8760/:8765/:8770; branch claude/explorer-fable-1-1114 @ 35bca14eaa (pushed; READY: tools/explorer/ + one kept-engine file tools/fleet_viz/explorer/element/lv_worker.js). Screenshots lanes/handoff/EXPLORER-FABLE-1/t12-geometry.p
- 2026-11-14 05:55:02 PST AUTO-RESIGN [AUTOPILOT -> COORD, die owners] qwen_compute/sta_cland_w537_s_s10_1 needs a lane: NO-BUILD-COMMIT: none provable from the row, the job or the kit records; left for a lane | qwen_compute/sta_cland_w515_s_s10_2 needs a lane: NO-BUILD-COMMIT: none provable from the row, the job or the kit records; left for a lane | qwen_compute/sta_cland_w632_e_s11 needs a lane: NO-BUILD-COMMIT: no
- 2026-11-14 05:56 PST RESULT [TL-QCRING-4 -> COORD; cc DIE-QC-103, QC-CORES-HEAD] sle_cland_w269_w_s6 SIGNED (R-MINIMAL) on epyc10 rk2 kit; AUTO-RESIGN row added. 2 of 6 signed; 4 still running.
- 2026-11-14 05:55 PST RESULT [TL-QCRING-1 -> COORD; cc QC-CORES-HEAD, DIE-QC-103] SIGNED sle_cland_w120_s_s3 (DRC 0, TT +30, internal hold +4.7; ff port-only advisory). AUTO-RESIGN row added. 4 left running (sle w457_e_s9, w517_n_s10_2, w653_w_s12, sta w1574_n_s26).
- 2026-11-14 05:57 PST KIT-WAVE [qwen_compute] -> QC die owner (DIE-QC-101): 23 event(s): cbn_q00__cl622f65d2 PREFLIGHT-ADVISORY clock_entry_clear 4 (io.tcl: clock entry clk_c0 (333.152, 648.032) over macro qfd_tile_nk_a0c#0 [103.68, 69.132, 561.6, 1226.892]); clock_pin_geometry 154 (landing_contract.json: clock fclk_in_bc_i00 on M7, not M8); cbn_q00__cl622f65d2 AUTO-GEOM PASS GEOM-ADVISORY aspect,channel_h,channel_v
- 2026-11-14 05:57 PST KIT-WAVE [qwen_kvsys] -> KV die owner (KV-101): 13 event(s): kv3_hgi_v6 PREFLIGHT-ADVISORY clock_entry_clear 16 (io.tcl: clock entry clk_c0 (497.312, 125.28) over macro kv3_head_eighth_e1#1 [388.8, 17.28, 604.8, 233.28]); clock_pin_geometry 180 (landing_contract.json: clock fclk_in_ft0_i on M7, not M8); kv3_hgi_v6 FAIL FLOW (clock-landing band too small or blocked (band plan, or tool: this kit 
- 2026-11-14 05:57 PST KIT-WAVE [s81_head] -> HEAD die owner (HEAD-98): 2 event(s): hd_ctl_n PREFLIGHT-ADVISORY clock_pin_geometry 24 (landing_contract.json: clock fclk_in_ctrl_ft_i on M7, not M8); hd_ctl_n AUTO-GEOM PASS GEOM-ADVISORY clock_tap_sinks,empty,fill,pin_reg_max,pin_reg_p90: OWNER 11-03 targets-not-gates (only sign-off blocks; COORD 09:0x geom advisory) -> enqueued (epyc7:/srv/opentallas-scratch2/claude/k
- 2026-11-14 05:57 PST KIT-WAVE [s81] -> S81 die owner (DIE-S81-90): 63 event(s): col_h10_r0_p1__t1__cl574cc59d__pv3d0d4d97 PREFLIGHT-ADVISORY clock_entry_clear 2 (io.tcl: clock entry clk_c8 (795.424, 751.456) over macro ot_v41_bf_col3_c#12 [760.428, 561.612, 968.676, 760.332]); macro_channels 1 (macro column 2 x[1278.83,1576.91]: E vertical channel 8.532 um < 10.8); col_h10_r0_p1__t1__cl574cc59d__pv3d0d4d97 FAIL FLO

