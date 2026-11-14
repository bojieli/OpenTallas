# COORD snapshot 2026-11-14 07:00 PST

Generated every 15 min by ~/coord/bin/coord_snapshot.py (cron on intel2, no LLM). It is the freshest COORD state if Claude stops on a limit. Read it right after ~/coord/CODEX-HANDOFF.md (the hand-written method and lane table) and ~/coord/lanes/handoff/<LANE>.md (each lane's own state). Facts only; the queue is the source.

## main and the merge lane
- origin/main: 3796bb9639d6
- 2026-11-14 05:25 PST MERGED [ROOT-MERGE-63] train AK (COORD APPROVED each, relayed by ROOT-MERGE-63) main a482236d89b -> 0ff50a33851, two no-ff merges, no conflicts: AK1 wave-friction-1 claude/wave-friction-1-1114@1495a0a3194 (3 commits: LEC_ASYNC missing becomes a warning; place probe checks all copy-back hosts; auto-ECO near-miss limit removed; kit_wave.py/eco_loop.py/gen_phys.py + test_lec_async_missing.py) -> 6
- 2026-11-14 05:37 PST MERGED [ROOT-MERGE-63] train AL KIT-OPS-4 item_env validator (COORD APPROVED, relayed by ROOT-MERGE-63; queue line f2f9473e614): tools/autopilot/kit_wave.py one line, item_env accepts brackets in OT_GEN_SECONDARY_CLOCK like OT_MACRO_MOVES; patch cut from the rt copy vs kit_wave.py.bak-kitops4s (only that hunk, sha256 05a4a559863b, the rt copy carries other unrelated changes that were NOT taken)
- 2026-11-14 06:50 PST MERGED [ROOT-MERGE-63] train AM (COORD APPROVED each, relayed by ROOT-MERGE-63; hand-resolve not needed, no conflicts) main a3ac578f4fc -> 3796bb9639d, four commits: AM1 wave-friction-1 claude/wave-friction-1-1114@bdddd9c86ea frictions 2-6 (ECO NONPORT adapter in eco_grt_pre.tcl, WAIT-CHILD auto core build) -> c9df8015503; AM2 admit-tune-4 b18e1d8933 (ot-run OVERLOAD_RATIO placement + test_ot_r

## READY/ASK with no later COORD post naming them (16, heuristic: check each)
- 2026-11-14 00:23 PST ASK [FAIL-QCKV-1 -> KV-102] plan-level fix for (d): widen the cland reserved band on the writer-start station o_hsl_Q_N_co (kv3_pc, kv3_pc_v1 types) and ft17_o (kv3_hgi_v8), or move those stations to a wider street; pinslot is already on. Give me the new plan@sha and I will queue the item@attempt keys via KIT-OPS-3.
- 2026-11-14 00:27 PST ASK [FAIL-QCKV-1 -> DIE-KV-102 for kv102sem; cc COORD] CLAND class (d) cause found, exact numbers. Plan plan_c.json@2d7f1667a198 types kv3_pc_v1__cl23f6a148, kv3_pc_v1__cl4ea58a5c, kv3_pc__cl5a95b461 (outline 1036.8 x 1520.64, same in all three): 13 writer-start branches end stages 6 AND 7 on the one top row y=1516.32; 12 of them within x 996.4..1032.5 (36 um), 4 at exactly x=1032.48 (ft1_o, o_
- 2026-11-14 01:10 PST READY [LIMIT-GRT-1 -> ROOT-MERGE-63] branch claude/limit-grt-1-1114 (a78e4cfb6ac, 1 commit off origin/main 83fc576b530, pushed): OWNER 11-14 "remove the conservative limits" for GRT: deletes GRT-EARLY (15:10000,20:1000 stop inside the full route), GRT-INCR-CONGESTED (stop when the full route ends congested), failfast GRT_NO_PROGRESS (OT_FF_GRT default 0, judge returns before the GRT rule), tool
- 2026-11-14 01:10 PST ASK [LIMIT-GRT-1 -> KIT-OPS-3] deploy this overlay to the live rt tools (intel2 /srv/opentallas-scratch2/claude/limit-grt-1/overlay/): physical/common_flow/grt183_make.sh sha256 7be13e6b09c7897ff7a41c707d874dbd263a15d0f7b867413dbb4f081cb86de1; physical/common_flow/failfast_rules.py sha256 6330beac49ec7ffb42dd930f7305d23968d0942e428242fbeda302e1669f4604 (both replace the rt copies; kits generate
- 2026-11-14 01:5x PST ASK [LIMIT-BIND-1 -> KIT-OPS-3; cc COORD] after deploying the overlay on all gen hosts: release + retry-key (a) every S81 B2/B2t/B2u bind and item failed or held on "tap ... load=N/1500", "radius=R/200", "exceeds 405" collector (the 30 overloaded-tap types, 6 held col_h10_r0_p1 forms, leaf__t1, 4 re-bind types); (b) every item whose preflight or place failed on cell_budget / R-CAP / "above 4000
- 2026-11-14 03:00 PST READY [S81-B3-CLK -> DIE-S81-91] B3 clock/reset slice binds clean: epyc7 /srv/opentallas-scratch2/claude/s81-b3-clk run/b/B3v strict bind 0 errors + LATCHECK 873/873 PASS, with OT_S81_SERDES_RST_TREE (all 14 serdes RST_TREE=1) + LIMIT-BIND-1. Plan ev/B3t.json 4b7f1e087434 (B2u + 36 types: 30 overloaded clk_t16/19/21 legs +1 split tap each, max load 1853->1373; 6 col_h10_r0_p1 in frame form with
- 2026-11-14 03:24 PST READY [DIE-S81-92 -> KIT-OPS-3; cc COORD] S81 dead-input overlay: claude/s81-dead-reproof-1114 is MERGED to main (0467a1f3c57, train AC, ROOT-MERGE-63). The dead_inputs re-proof patch part of tools overlay M/ovl_b3 can be dropped at the next S81 src refresh (main now carries it). It must stay in the live B3v src until that refresh; keep the re-proof file results/token_pass/s81_dead_inputs_2148/
- 2026-11-14 04:20 PST READY [TYPE-KVPCF -> KIT-OPS-3; cc COORD, KV-102] DO_NOT_COUNT. qkd_kvs_pcf view REBUILT-EQUIVALENT, no regeneration needed: epyc8 /srv/opentallas-scratch2/claude/dkv100/pdncls/views/qkd_kvs_pcf is the DIEKV-100 detail view of the same signed ODB (bd980c62) with detail_receipt check_ok true, problems [], M6 7564/M7 2827 OBS rects, detail_view.lef sha256 2a908d42208ee400... = the exact out sha o
- 2026-11-14 04:1x PST READY [TYPE-QCSTRAP -> DIE-QC-103; cc COORD, KIT-OPS-3, FAIL-QCKV-1] FAIL-QCKV-1 PORT_BIND bad_straps on sle_sc_v1__cl115da35f + sle_sc_v2 (12 pins each missing) = STALE PLAN STRAPS, not a missing pin: plan zz_s29_qc103_s count_straps[] still declares strap_r8pad_core_red_addr/data/we (OWNER 10-28 sites, plan_qc46+) but the bind of record (s29q103S AND s29q102B0 bind_parent_id_straps.json, pinn
- 2026-11-14 05:10 PST READY [TYPE-KVPCF -> KIT-OPS-3; cc COORD, KV-102] DO_NOT_COUNT. CLASS FIX for prov_view_sources entries whose only host was epyc4 (28 cores + pcf): 22 views staged and sha-verified on epyc8, epyc9, epyc10 under /srv/opentallas-scratch2/claude/epyc4views-1114/<core>/ (lef, _tt/_ff.lib, provenance.json, pins/gates/meta where present). MATCH RULE: the view dir's provenance/meta cites the SAME sign
- 2026-11-14 04:52 PST ASK [TL-SERDEST14 -> KIT-OPS-3, COORD; cc DIE-S81-92] s81/serdes__t14: last attempt (Codex wave attempt_7, epyc4 gone) FAIL OT_NATIVE_CELL_CAP 460859 > 400000 (native_cell_cap.tcl hard cap; owner 11-14 removes cap; LIMIT-BIND-1 overlay makes it advisory). Item is held (DIE-S81-87 ready11r hold, KW-FIX-45) and not in only_items. Please: release hold, add serdes__t14 to s81 only_items, retry key 
- 2026-11-14 05:20 PST ASK [QC-CORES-HEAD -> KIT-OPS-3; cc WAVE-FRICTION-1, COORD] DOUBLE-BUILD GUARD before 06:20 PST: add all 29 cores to kit_wave.json dies.qwen_compute.auto_core_hold (the 14 sle_cland_{w120_s_s3,w2104_s_s34,w257_e_s6,w269_w_s6,w457_e_s9,w457_s_s9,w517_n_s10,w517_n_s10_1,w517_n_s10_2,w537_e_s10,w537_s_s10,w537_w_s10,w653_w_s12,w94_s_s3}, the 11 sta_cland_{w1081_e_s18,w1574_e_s26,w1574_n_s26,w259_s
- 2026-11-14 05:19 PST READY [S81-B3-SVC -> DIE-S81-91; cc S81-B3-CLK, COORD] B3 svc patch set (private, DO_NOT_COUNT). Location: epyc7 /srv/opentallas-scratch2/claude/s81-b3-svc/patchset_b3svc/. Full plan: plan_b3svc_v2g.json sha a25bd6251dfa = H8 band plan sg1077 + delta + ft + latency; manifest: asbuilt_band_h8_b3svc.json + declared_ties_svc_h8_b3svc.json.
- 2026-11-14 05:47 PST ASK [QC-CORES-HEAD -> KIT-OPS-3] hourly registration batch 1 (prov_view_sources, the wave also auto-picks DRC-0 sign-off records so this is belt and braces): sle_cland_w94_s_s3, sta_cland_w515_s_s10_2, sta_cland_w515_s_s10_3, sta_cland_w537_s_s10_1, sta_cland_w632_e_s11 (signoff dirs in lanes/handoff/QC-CORES.md view-path column; rows already in AUTO-RESIGN.tsv). Next batch once RING-3 adds row
- 2026-11-14 06:03 PST ASK [QC-CORES-HEAD -> KIT-OPS-3; cc WAVE-FRICTION-1] registration batch 2, please add prov_view_sources now for all 14 signed cores (kit/signoff paths in lanes/handoff/QC-CORES.md view-path column): sle_cland_w120_s_s3 sle_cland_w257_e_s6 sle_cland_w269_w_s6 sle_cland_w457_s_s9 sle_cland_w517_n_s10_2 sle_cland_w94_s_s3 sta_cland_w1081_e_s18 sta_cland_w259_s_s6 sta_cland_w515_s_s10 sta_cland_w51
- 2026-11-14 06:27 PST READY [FABLE-REVIEW-CLK -> FIX-HOLDSTALL (kit SDC tool), DIE-S81-92, KIT-OPS-4; cc COORD, S81-TAPSKEW, KV-102, DIE-QC-103, ROOT-MERGE-63] R-CLOCK-7 final, with proof on leaf t42. Full text lanes/handoff/FABLE-REVIEW-CLK.md section 1b. S81-TAPSKEW's reading is PARTLY right: the kit charges every pair of a port the port's worst die damage; the two taps of a real pair differ far less. But the diff

## Lane handoff files (age) and last queue post
- BUS-GEAR-2: handoff 2741 min old; last post 2026-11-12 09:17 RESULT
- CLAND-GEOM: handoff 154 min old; last post 2026-11-14 05:06 STATE
- CLAND-RELAY-2: handoff 1805 min old; last post 2026-11-13 00:52 READY
- CLAND-RELAY-3: handoff 1740 min old; last post 2026-11-13 01:59 READY
- CLEAN-2: handoff 1977 min old; last post 2026-11-12 22:02 RESULT
- COORD-COMMIT-SPEED-1: handoff 1238 min old; last post 2026-11-13 10:27 RESULT
- DIE-HBM-100: handoff 1838 min old; last post 2026-11-12 12:43 HANDOFF
- DIE-HBM-101: handoff 2247 min old; last post 2026-11-12 20:02 READY
- DIE-HBM-102: handoff 1745 min old; last post 2026-11-13 01:53 READY
- DIE-KV-100: handoff 820 min old; last post 2026-11-13 13:37 STATE
- DIE-KV-99: handoff 2336 min old; last post 2026-11-12 16:10 STATE
- DIE-PROTO-1: handoff 147 min old; last post 2026-11-14 04:3x RESULT
- DIE-PROTO-2: handoff 2817 min old; last post 2026-11-12 08:05 RESULT
- DIE-QC-100: handoff 819 min old; last post 2026-11-13 13:35 STATE
- DIE-QC-101: handoff 533 min old; last post 2026-11-13 22:06 STATE
- DIE-QC-102: handoff 490 min old; last post 2026-11-13 22:08 STATE
- DIE-QC-103: handoff 52 min old; last post 2026-11-14 06:54 STATE
- DIE-S81-88: handoff 819 min old; last post 2026-11-12 16:24 FINDING
- DIE-S81-89: handoff 821 min old; last post 2026-11-13 12:47 STATE
- DIE-S81-90: handoff 470 min old; last post 2026-11-13 23:09 STATE
- DIE-S81-91: handoff 233 min old; last post 2026-11-14 02:04 STATE
- DIE-S81-92: handoff 73 min old; last post 2026-11-14 07:5x NEEDS-LANE
- DRAIN-EPYC4: handoff 394 min old; last post 2026-11-14 00:24 READY-TO-TERMINATE
- DSDV-FORMS-2: handoff 1412 min old; last post none in recent queue
- EXPLORER-P1: handoff 327 min old; last post none in recent queue
- EXPLORER-REVIEW-1: handoff 354 min old; last post 2026-11-14 01:05 REVIEW
- EXPLORER-REVIEW-2: handoff 333 min old; last post 2026-11-14 01:26 REVIEW
- FABLE-REVIEW-CLK: handoff 29 min old; last post 2026-11-14 06:30 REVIEW
- FABLE-REVIEW-COL: handoff 84 min old; last post 2026-11-14 05:45 REVIEW
- FABLE-REVIEW-CORES: handoff 106 min old; last post 2026-11-14 05:2x REVIEW
- FAIL-CLASS-2: handoff 99 min old; last post 2026-11-14 05:20 NEEDS-LANE
- FAIL-QCKV-1: handoff 12 min old; last post 2026-11-14 06:47 STATE
- FAIL-S81-1: handoff 12 min old; last post none in recent queue
- FIX-CLASSIFY: handoff 83 min old; last post 2026-11-14 05:40 RESULT
- FIX-HOLDSTALL: handoff 10 min old; last post 2026-11-14 05:40 STATE
- FIX-SELFCONT: handoff 66 min old; last post 2026-11-14 05:53 RESULT
- FIX-YOSYS: handoff 90 min old; last post 2026-11-14 05:29 RESULT
- FLEET-2: handoff 2594 min old; last post 2026-11-12 13:5x READY
- FLOW-FIN-2: handoff 1403 min old; last post none in recent queue
- FLOW-PGCAP-1: handoff 590 min old; last post 2026-11-13 22:24 RESULT
- FRAME-FORMS-1: handoff 821 min old; last post 2026-11-13 13:28 REQUEST
- FRAME-FORMS-2: handoff 1413 min old; last post none in recent queue
- GEN-CLASS-1: handoff 2370 min old; last post 2026-11-12 15:33 STATE
- GEOM-VIS-5: handoff 2854 min old; last post 2026-11-12 07:25 HANDOFF
- GEOM-VIS-6: handoff 2802 min old; last post 2026-11-12 08:17 HANDOFF
- GEOM-VIS-7: handoff 2712 min old; last post 2026-11-12 09:5x HANDOFF
- GEOM-VIS-8: handoff 2425 min old; last post 2026-11-12 14:34 SUMMARY
- GEOM-VIS-9: handoff 824 min old; last post none in recent queue
- GUNIT-CORE-1: handoff 886 min old; last post 2026-11-13 12:46 READY
- HARD-QC-FORMS-1: handoff 932 min old; last post 2026-11-13 12:51 STATE
- HARD-S81-DSDV-1: handoff 946 min old; last post 2026-11-13 13:11 STATE
- HARD-S81-SERDES-1: handoff 870 min old; last post none in recent queue
- HARD-S81-SVC-1: handoff 821 min old; last post 2026-11-13 11:03 READY
- HBM-CORES-B: handoff 2869 min old; last post 2026-11-12 07:17 RESULT
- HBM-FORMS-1: handoff 1661 min old; last post 2026-11-13 03:15 STATE
- HEAD-95: handoff 2341 min old; last post 2026-11-12 16:5x STATE
- HEAD-96: handoff 1523 min old; last post 2026-11-13 05:36 RESULT
- HEAD-97: handoff 1103 min old; last post 2026-11-13 13:35 RESULT
- HEAD-98: handoff 687 min old; last post none in recent queue
- HEAD-99: handoff 373 min old; last post none in recent queue
- HEAD-ROUTE-1: handoff 1437 min old; last post none in recent queue
- HOLD-TAP-1: handoff 823 min old; last post 2026-11-13 13:35 RESULT
- HOLDTAP-FIN-2: handoff 1413 min old; last post 2026-11-13 07:12 READY
- KIT-FIX-F: handoff 712 min old; last post 2026-11-13 19:07 RESULT
- KIT-OPS-1: handoff 871 min old; last post 2026-11-13 09:58 STATE
- KIT-OPS-2: handoff 690 min old; last post 2026-11-13 19:19 RESULT
- KIT-OPS-3: handoff 282 min old; last post 2026-11-14 06:26 DONE
- KIT-OPS-4: handoff 2 min old; last post none in recent queue
- KIT-SNAP-1: handoff 800 min old; last post 2026-11-13 17:39 STATE
- KIT-STAGE-1: handoff 1428 min old; last post 2026-11-13 07:39 STATE
- KV-101-PC: handoff 758 min old; last post none in recent queue
- KV-101-PVFIN: handoff 776 min old; last post none in recent queue
- KV-101-SPLIT: handoff 728 min old; last post none in recent queue
- KV-101: handoff 685 min old; last post 2026-11-13 19:21 RESULT
- KV-VN2-FIN: handoff 2266 min old; last post 2026-11-12 17:13 PLAN-EVENT
- KW-FIX-46: handoff 2338 min old; last post 2026-11-12 16:01 RESULT
- LATCHECK-1: handoff 2279 min old; last post 2026-11-12 17:00 READY
- LEAF-HOLD-1: handoff 821 min old; last post 2026-11-13 10:44 STATE
- ONBOARD-EPYC10: handoff 748 min old; last post 2026-11-13 18:31 RESULT
- PHYS-KVHEAD: handoff 770 min old; last post 2026-11-13 18:09 STATE
- PHYS-QC: handoff 783 min old; last post 2026-11-13 17:56 STATE
- PHYS-S81: handoff 776 min old; last post 2026-11-13 18:04 STATE
- PROFILE-1: handoff 755 min old; last post 2026-11-13 18:24 READY
- PROOF-CORES: handoff 790 min old; last post 2026-11-13 17:49 RESULT
- PROOF-QCKV: handoff 790 min old; last post 2026-11-13 17:55 RESULT
- PROOF-S81: handoff 792 min old; last post none in recent queue
- QC-CORES: handoff 4 min old; last post none in recent queue
- QC-FORMS-2: handoff 918 min old; last post 2026-11-13 07:03 READY
- QC-RING: handoff 315 min old; last post none in recent queue
- REACH-FIN-2: handoff 1411 min old; last post 2026-11-13 07:25 READY
- REACH-FIX-2: handoff 2320 min old; last post 2026-11-12 16:19 RESULT
- REBUILD-17: handoff 460 min old; last post 2026-11-13 23:19 STATE
- RELAY-PLACE-1: handoff 1665 min old; last post 2026-11-13 03:13 RESULT
- RESIGN-SWEEP: handoff 40 min old; last post none in recent queue
- ROOT-MERGE-60: handoff 2297 min old; last post 2026-11-12 15:41 MERGED
- ROOT-MERGE-62: handoff 782 min old; last post 2026-11-13 17:57 MERGED
- ROOT-MERGE-63: handoff 9 min old; last post 2026-11-14 06:50 MERGED
- RULES-CAP-1: handoff 1026 min old; last post 2026-11-13 04:12 READY
- RULES-FLOW-1: handoff 1266 min old; last post none in recent queue
- RULES-REACH-1: handoff 975 min old; last post none in recent queue
- RULES-STREET-1: handoff 1004 min old; last post 2026-11-13 07:56 RESULT
- S81-B3-CLK: handoff 239 min old; last post 2026-11-14 03:00 READY
- S81-B3-SVC: handoff 100 min old; last post 2026-11-14 05:19 READY
- S81-CORES-2: handoff 374 min old; last post none in recent queue
- S81-FORMS-1: handoff 821 min old; last post 2026-11-13 12:08 STATE
- S81-R12BA-FIN: handoff 2071 min old; last post 2026-11-12 20:25 READY
- SERDES-FIN-2: handoff 1413 min old; last post none in recent queue
- STA2204-1: handoff 2552 min old; last post 2026-11-12 13:32 RESULT
- SVC-BAND-3: handoff 502 min old; last post none in recent queue
- SVC-MACRO-2: handoff 1413 min old; last post 2026-11-13 07:24 PLAN
- TL-COLH10R0P1: handoff 136 min old; last post none in recent queue
- TL-COLH10R0P4: handoff 129 min old; last post 2026-11-14 04:57 STATE
- TL-COLH9R0P1: handoff 128 min old; last post 2026-11-14 05:41 STATE
- TL-COLH9R0P2: handoff 115 min old; last post 2026-11-14 06:01 FINDING
- TL-COLH9R0P3: handoff 50 min old; last post 2026-11-14 06:09 STATE
- TL-COLH9R0P4: handoff 128 min old; last post 2026-11-14 04:51 STATE
- TL-COLH9R0P5: handoff 133 min old; last post 2026-11-14 04:50 FINDING
- TL-COLH9R0P6: handoff 137 min old; last post none in recent queue
- TL-HDHOSTW: handoff 99 min old; last post 2026-11-14 05:20 STATE
- TL-KVLEAFT5: handoff 127 min old; last post 2026-11-14 04:52 STATE
- TL-KVPHY: handoff 133 min old; last post 2026-11-14 04:50 RESULT
- TL-KVSYSSD: handoff 134 min old; last post 2026-11-14 04:50 RESULT
- TL-LEAFT14: handoff 133 min old; last post 2026-11-14 12:40 STATE
- TL-LEAFT34: handoff 130 min old; last post none in recent queue
- TL-LEAFT56: handoff 130 min old; last post 2026-11-14 04:49 STATE
- TL-LEAFT62: handoff 130 min old; last post 2026-11-14 04:55 STATE
- TL-LEAFT72: handoff 120 min old; last post 2026-11-14 04:59 STATE
- TL-QCPHYSD: handoff 102 min old; last post 2026-11-14 13:2x STATE
- TL-QCPHYSDB: handoff 127 min old; last post 2026-11-14 04:53 STATE
- TL-QCREP4: handoff 98 min old; last post 2026-11-14 05:21 STATE
- TL-QCRING-1: handoff 21 min old; last post 2026-11-14 06:38 RESULT
- TL-QCRING-2: handoff 106 min old; last post 2026-11-14 05:35 RESULT
- TL-QCRING-3: handoff 54 min old; last post 2026-11-14 06:05 RESULT
- TL-QCRING-4: handoff 106 min old; last post 2026-11-14 06:15 RESULT
- TL-QCSTAV2: handoff 118 min old; last post 2026-11-14 05:2x STATE
- TL-QCSTBV1: handoff 136 min old; last post 2026-11-14 04:43 STATE
- TL-QCSTBV2: handoff 136 min old; last post 2026-11-14 04:45 STATE
- TL-QCTAIL1: handoff 8 min old; last post 2026-11-14 06:51 FINDING
- TL-QCTAPB: handoff 96 min old; last post 2026-11-14 06:19 STATE
- TL-S81PHY: handoff 0 min old; last post 2026-11-14 06:59 STATE
- TL-SERDEST1: handoff 121 min old; last post none in recent queue
- TL-SERDEST14: handoff 127 min old; last post 2026-11-14 05:52 STATE
- TL-SLC1XT8: handoff 107 min old; last post 2026-11-14 05:05 STATE
- TL-SLC3XT1: handoff 20 min old; last post 2026-11-14 06:4x STATE
- TL-SST27: handoff 129 min old; last post 2026-11-14 04:5x STATE
- TL-SST36: handoff 125 min old; last post 2026-11-14 04:54 STATE
- TOK-VERIFY-2: handoff 2779 min old; last post 2026-11-12 08:40 HANDOFF
- TOK-VERIFY-3: handoff 2533 min old; last post 2026-11-12 12:46 RESULT
- TYPE-COLH9P5: handoff 313 min old; last post 2026-11-14 01:46 STATE
- TYPE-COLH9R1: handoff 162 min old; last post 2026-11-14 04:50 STATE
- TYPE-COLH9R2: handoff 161 min old; last post 2026-11-14 05:05 STATE
- TYPE-GUNIT-L1F: handoff 379 min old; last post 2026-11-14 00:40 STATE
- TYPE-GUNIT-L1F2: handoff 134 min old; last post none in recent queue
- TYPE-HDCTLN: handoff 377 min old; last post 2026-11-14 01:46 RESULT
- TYPE-KVHGI2: handoff 378 min old; last post 2026-11-14 06:35 STATE
- TYPE-KVPHY: handoff 311 min old; last post 2026-11-14 01:48 RESULT
- TYPE-LEAFHOLD: handoff 163 min old; last post none in recent queue
- TYPE-LEPE: handoff 320 min old; last post none in recent queue
- TYPE-S81-T29: handoff 376 min old; last post 2026-11-14 00:43 STATE
- TYPE-SERDES-T4: handoff 365 min old; last post 2026-11-14 01:25 STATE
- TYPE-SLICE-HOLD: handoff 321 min old; last post 2026-11-14 00:48 STATE
- TYPE-XS4: handoff 380 min old; last post 2026-11-14 00:39 STATE
- VARIANTS-1: handoff 488 min old; last post none in recent queue
- VERIFY-PRICING-1: handoff 1583 min old; last post 2026-11-13 04:36 READY
- VISLAYOUT2-QC: handoff 2809 min old; last post 2026-11-12 08:09 RESULT
- VISLAYOUT3-KVHEAD: handoff 1833 min old; last post 2026-11-12 06:24 STATE
- WAVE-FRICTION-1: handoff 368 min old; last post 2026-11-14 05:56 STATE
- WBQ: handoff 2791 min old; last post none in recent queue

## ot-run status
    ot-run status: epyc2 admits 213 GB (avail 229, reserve 0, fresh 0, peak 0) load 258/128 run 99 LOADCAP root 41% scratch 175 GB
    intel1 admits 45 GB (avail 62, reserve 0, fresh 0, peak 0) load 367/112 run 157 LOADCAP root 34% scratch 264 GB
    localhost admits 0 GB (avail 50, reserve 0, fresh 0, peak 0) load 130/112 waiters 1:48 GB run 63 root 68% scratch 1183 GB
    epyc4 HELD (DRAIN DRAIN-EPYC4 11-13 23:xx OWNER terminate epyc4: no new ot-run job (running jobs untouched). Revert: delete this line (backup held_hosts.bak-dra
    epyc7 admits 0 GB (avail 51, reserve 0, fresh 0, peak 0) load 240/96 waiters 38:773 GB run 99 LOADCAP root 36% scratch 1569 GB
    epyc8 admits 21 GB (avail 117, reserve 0, fresh 0, peak 0) load 77/96 waiters 28:744 GB run 44 root 6% scratch 2395 GB
    epyc9 admits 1 GB (avail 66, reserve 0, fresh 0, peak 0) load 226/96 waiters 36:978 GB run 122 LOADCAP root 5% scratch 2609 GB
    epyc10 admits 28 GB (avail 125, reserve 0, fresh 0, peak 0) load 168/96 waiters 14:448 GB run 87 LOADCAP root 4% scratch 5832 GB
    next 16-thread 32 GB job -> epyc2 (would queue)

## KIT-WAVE (autopilot log, last 6)
    2026-11-14 07:00:14 PST AUTOPILOT: KIT-WAVE WAIT-CHILD qwen_compute/slw_st_a_v1__clfc5867a6__pvdf8e5ca4: no routed PROVISIONAL source yet for child core(s) qfd_dv_s8_station_tail1 (prov_require_cands)
    2026-11-14 07:00:15 PST AUTOPILOT: KIT-WAVE WAIT-CHILD qwen_compute/slw_st_a_v1__clfc5867a6__pvf82a6c28: no routed PROVISIONAL source yet for child core(s) qfd_dv_s8_station_tail1 (prov_require_cands)
    2026-11-14 07:00:15 PST AUTOPILOT: KIT-WAVE WAIT-CHILD qwen_compute/slw_st_a_v2__cl9f076a5c: no routed PROVISIONAL source yet for child core(s) sta_region_nb0 (prov_require_cands)
    2026-11-14 07:00:15 PST AUTOPILOT: KIT-WAVE WAIT-CHILD qwen_compute/slw_st_a_v2__clf4365a62: no routed PROVISIONAL source yet for child core(s) sta_region_nb0 (prov_require_cands)
    2026-11-14 07:00:15 PST AUTOPILOT: KIT-WAVE LAUNCH qwen_compute/phy_serdes (type, 2 replicas) event-key s29q103S2 plan zz_s29_qc103_s2.json@f84e7f271c14 src qc-s29-tree2 unit kw-qwenco-physerdes-2-684
    2026-11-14 07:00:16 PST AUTOPILOT: KIT-WAVE LAUNCH qwen_compute/phy_ucie_kv (type, 1 replicas) event-key s29q103S2 plan zz_s29_qc103_s2.json@f84e7f271c14 src qc-s29-tree2 unit kw-qwenco-phyuciekv-2-68

## Last 60 queue posts (cut to 420 chars; full text in the queue)
- 2026-11-14 06:09 PST STATE [TL-COLH9R0P3 -> COORD; cc DIE-S81-92, KIT-OPS-3] p3 (all 12 pv variants, cl0cd90c0e/cl8ce97bcb/cl31d0dc4b) confirmed past gen_lint after the LOCAL fix; now blocked at place by the FT off-grid class (ft0,1,0 1327.32 1251.09, 5525 bits per type). Waiting for DIE-S81-92 B3x2 (snap) adoption; no p3 relaunch on plan_h2_2249 needed (would fail the same). I will follow the first p3 row on B3x2 
- 2026-11-14 06:09 PST KIT-WAVE [qwen_compute] -> QC die owner (DIE-QC-101): 11 event(s): cbf_q11 FAIL INFRA (infra (python exception / plan-schema refusal in the kit tool: tool or source skew) @gen: AttributeError: module 'pregrt_ff_hold' has no attribute 'set_die_cloc) evid epyc7:/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S/items/cbf_q11/attempt_10; sle_stm_v1__cl
- 2026-11-14 06:09 PST KIT-WAVE [qwen_kvsys] -> KV die owner (KV-101): 6 event(s): kv3_hub_C FAIL FLOW (unclassified failure @kit_rtl (see log): bind: ERROR kit-rtl kv3_hub_C: AHUB boundary: native parameter signature changed: {'AP_OFS': "64'hffe0ffdfffdfffdf", 'F) evid epyc2:/srv/opentallas-scratch2/claude/kw43-wave-1109/runs/qwen_kvsys/kit-wave/qwen_kvsys/kv102sem_ftgrid/items/kv3_hub_C/attempt_7; kv3_pc__cl5a95b46
- 2026-11-14 06:09 PST KIT-WAVE [s81] -> S81 die owner (DIE-S81-90): 17 event(s): col_h9_r2__t1__cl774acf45__pv858fb2ba LAUNCHED (kw-s81-colh9r2t1cl774acf45pv858fb2b-2-65359); col_h9_r2__t1__cl774acf45__pve3ab90e7 LAUNCHED (kw-s81-colh9r2t1cl774acf45pve3ab90e-2-65360); col_h9_r0_p2__t1__cl9f71e63d__pv291547b4 LAUNCHED (kw-s81-colh9r0p2t1cl9f71e63dpv29154-4-65361); col_h9_r0_p3__t1__cl8ce97bcb__pvcd8810ba LAUNCHED (kw
- 2026-11-14 06:10 PST STATE [QC-CORES-HEAD -> COORD; cc KIT-OPS-3, WAVE-FRICTION-1] STATE: 21/29 signed (R-MINIMAL: DRC 0, TT +126..+199 ps, internal FF hold >=0; sle_cland_w517_n_s10_1 counted as R-MINIMAL pass: verdict LOCAL_PASS_NEEDS_PARENT, DRC 0, TT +149, internal hold PASS, -1.34 is the rst_xn port-only advisory, same as the bci00 precedent), 0 exited without sign-off, failure classes none. AUTO-RESIGN rows a
- 2026-11-14 06:15 PST RESULT [TL-QCRING-4 -> COORD; cc DIE-QC-103, QC-CORES-HEAD] ALL 6 of my ring children done, no failures, no rebuilds: SIGNED sle_cland_w269_w_s6, sle_cland_w537_w_s10, sta_cland_w515_s_s10_1, sta_cland_w537_s_s10_1, sta_cland_w1574_e_s26; sle_cland_w517_n_s10_1 = LOCAL_PASS_NEEDS_PARENT (DRC0, TT setup +149, only rst_xn port-only hold -1.3 ps) counted as R-MINIMAL pass per port-only-hold-adviso
- 2026-11-14 06:14 PST STATE [TL-QCTAIL1 -> COORD] per COORD: 3rd form of qfd_dv_s8_station_tail1 launched on epyc9 (util 0.4, same inputs as rkb, ot-run --hosts epyc9 from epyc7 client pid 1876081, admitted). intel1 forms rk/rkb stay; first to pass wins.
- 2026-11-14 06:15:31 PST AUTO-RESIGN [AUTOPILOT -> COORD, die owners] qwen_compute/sle_cland_w457_s_s9 needs a lane: NO-BUILD-COMMIT: none provable from the row, the job or the kit records; left for a lane | qwen_compute/sle_cland_w517_n_s10_2 needs a lane: NO-BUILD-COMMIT: none provable from the row, the job or the kit records; left for a lane | qwen_compute/sta_cland_w259_s_s6 needs a lane: NO-BUILD-COMMIT: none p
- 2026-11-14 06:16 PST RESULT [TL-QCRING-1 -> COORD; cc QC-CORES-HEAD, DIE-QC-103] SIGNED sle_cland_w457_e_s9 (TT +23.5, int hold +2.4) and sle_cland_w653_w_s12 (TT +25.9, int hold +0.8), DRC 0 both. AUTO-RESIGN rows added. 1 left running: sta_cland_w1574_n_s26.
- 2026-11-14 06:18 PST STATE [QC-CORES-HEAD -> COORD; cc KIT-OPS-3, WAVE-FRICTION-1] STATE: 23/29 signed, 0 exited without sign-off, failure classes none, AUTO-RESIGN rows for all 23. Remaining 6: sle_cland_w2104_s_s34, sta_cland_w1574_n_s26, sta_region_nb0 (running) and qfd_dv tail1 / tap_bounded / repair4_leaf (7 forms). WAIT-CHILD now resolves signed children: at 06:09 slw_st_a_v2 waits only on sta_cland_w1574_e_s
- 2026-11-14 06:18 PST QC-FIRST-ROUTES [DIE-QC-103 -> COORD; cc FAIL-QCKV-1] only 6 QC items have an outcome at route or later since 02:00 PST (waiter fallback, not 10): 0 SIGNED / 6 not passing. Classes: (1) 4 CRASH flow-error, slw_hc2__cl6bcaba89, sle_hc0__cl05696ed1, slw_fw_v1__cl51d45468 (exit 99, route goal, died ~5 min after SUBMIT right after 3_place; route/CTS logs never start) + slw_sc_v1__cl63e5a7a2 (exit 1
- 2026-11-14 06:19 PST STATE [TL-QCTAPB -> COORD; cc DIE-QC-103] qfd_dv_s8_tap_bounded form a (earlyoom rerun) synthesised then FAIL face_guard: 34 unregistered (hr_q[1],hr_q[452],lq_bad[31:0] feed AND/OR directly) + 15 shared-load input pins; RTL consumes inputs combinationally, b/c have same RTL so will fail the same. Form d launched (epyc2, --mem 64): wrapper registers ALL 1543 data inputs once (uniform +1 cycle o
- 2026-11-14 06:19 PST KIT-WAVE [qwen_compute] -> QC die owner (DIE-QC-101): 9 event(s): cbf_q00__cl870de686 FAIL INFRA (infra (python exception / plan-schema refusal in the kit tool: tool or source skew) @gen: AttributeError: module 'pregrt_ff_hold' has no attribute 'set_die_cloc) evid epyc7:/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S/items/cbf_q00__cl870de686/att
- 2026-11-14 06:19 PST KIT-WAVE [qwen_kvsys] -> KV die owner (KV-101): 7 event(s): kv3_hgi_v2__cl2862d491 PREFLIGHT-ADVISORY clock_entry_clear 16 (io.tcl: clock entry clk_c0 (505.952, 125.28) over macro kv3_head_eighth_e1#1 [397.44, 17.28, 613.44, 233.28]); clock_pin_geometry 84 (landing_contract.json: clock fclk_in_ft0_i on M7, not M8); kv3_hgi_v2__cl2862d491 AUTO-GEOM PASS GEOM-ADVISORY channel_h,channel_v,clock_on
- 2026-11-14 06:19 PST KIT-WAVE [s81] -> S81 die owner (DIE-S81-90): 24 event(s): col_h9_r0_p2__t1__cl0045af7b__pva2793873 PREFLIGHT-ADVISORY clock_entry_clear 2 (io.tcl: clock entry clk_c8 (795.424, 1148.9) over macro ot_v41_bf_col3_c#18 [760.428, 993.612, 968.676, 1192.332]); col_h9_r0_p2__t1__cl0045af7b__pva2793873 FAIL FLOW (tool / Tcl error @place: Error: global_place.tcl, 5 explicit FT site is not on a row/site
- 2026-11-14 06:19 PST KIT-WAVE [s81_head] -> HEAD die owner (HEAD-98): 2 event(s): hd_spn_end signoff FAIL ROUTING (routed: drc 3 late-ECO exhausted (1 it, 20443.5 s): TT 38.5->38.45 FF -6.67->-0.11 drv 0->0 drc 3->3; 1 iteration(s), still not signed: GEOMETRY + REDESIGN, no ) job 8dd2f2c5d0c8; hd_spn_end LAUNCHED (kw-s81hea-hdspnend-3-65976)
- 2026-11-14 06:19 PST STATE [KIT-WAVE -> COORD, QC die owner (DIE-QC-101)] WAIT-CHILD qwen_compute: 16 parent type(s) wait on 29 child core(s) without a routed view: held-by-hand 29 (qfd_dv_s5_ctl_repair4_leaf qfd_dv_s8_station_tail1 qfd_dv_s8_tap_bounded sle_cland_w120_s_s3 sle_cland_w2104_s_s34 sle_cland_w257_e_s6 sle_cland_w269_w_s6 sle_cland_w457_e_s9 sle_cland_w457_s_s9 sle_cland_w517_n_s10 sle_cland_w517_n_s10
- 2026-11-14 06:19 PST STATE [KIT-WAVE -> COORD, KV die owner (KV-101)] WAIT-CHILD qwen_kvsys: 1 parent type(s) wait on 2 child core(s) without a routed view: requested 2 (qkd_hr_core_order qkd_hr_core_peer). requested = the wave builds it as a core row; building = an autopilot job already runs it (no second build); held-by-hand = dies.qwen_kvsys.auto_core_hold.
- 2026-11-14 06:19 PST STATE [KIT-WAVE -> COORD, S81 die owner (DIE-S81-90)] WAIT-CHILD s81: 1 parent type(s) wait on 1 child core(s) without a routed view: requested 1 (s81p_slice_station__t51_ot_s81_station_t51_native_w). requested = the wave builds it as a core row; building = an autopilot job already runs it (no second build); held-by-hand = dies.s81.auto_core_hold.
- 2026-11-14 06:20 PST RESULT [FAIL-QCKV-1 -> COORD, KIT-OPS-4, KIT-OPS-3] QC exit 99 (slw_hc2__cl6bcaba89, sle_hc0__cl05696ed1, slw_fw_v1__cl51d45468) = YES the same class: route jobs 6c3a18958b23 (03:17), 6d98e66fb881 (03:23), 9fc109b1d1e4 (03:27) logged "ot-job: NOT RUN: input .../attempt_N/gen/run_kit.sh: not in the store, not on this host, and no host to fetch from", RAN on epyc2 exit 99 (the kits sat on epyc8):
- 2026-11-14 06:22 PST RESULT [DIE-QC-103 -> COORD; cc TL-QCTAPB] tap_bounded +1 input cycle (form d, COORD-approved): lanes + absorption, checked on bind_s29q103S2 / plan zz_s29_qc103_s2. WHERE: qfd_dv_s8_tap_bounded is u_tap in the 6 sle_ctl types (cl67434795, cl372cea1c, cla4f6f12f, cl503337ff and the two __v1). From the bound RTL (sle_ctl__cl67434795.sv:7158): inputs hr_q<-x_fw_p2_i_q[534:82], lq_bad<-x_hc0..3_i_
- 2026-11-14 08:30 PST RESULT [EXPLORER-FABLE-1 (Fable) -> COORD; cc RESIGN-SWEEP] "explorer /api/elements state stale (kv3_phy, kv3_sys_SD_v1, slice_station__t41, coll_ftm, qkd_astk_ex_s)": the stale answers came from the OLD fleet-viz element registry (now localhost:8764; it still says cancelled / flow failure / not started for those five). The new explorer already had all five SIGNED (its status chain is count cac
- 2026-11-14 06:24 PST RESULT [S81-TAPSKEW -> COORD; cc FABLE-REVIEW-CLK, DIE-S81-92, FIX-HOLDSTALL] Table lanes/S81-TAPSKEW.tsv (65 post-CTS kits: 21 S81 leaf, 34 col, 1 gunit, 1 kv_leaf, 6 KV, 2 QC; no HEAD kit reached CTS; the wave stops at place/geom, so post-CTS DBs are only these hand/proof dirs). Top findings: (1) The "182 ps" is not one thing: per-port tap window W (SDC set_clock_latency -source -early, "tap 
- 2026-11-14 06:24:14 PST AUTO-RESIGN [AUTOPILOT -> COORD, die owners] qwen_compute/sle_cland_w457_e_s9 needs a lane: NO-BUILD-COMMIT: none provable from the row, the job or the kit records; left for a lane | qwen_compute/sle_cland_w537_e_s10 needs a lane: NO-BUILD-COMMIT: none provable from the row, the job or the kit records; left for a lane | qwen_compute/sle_cland_w653_w_s12 needs a lane: NO-BUILD-COMMIT: none pr
- 2026-11-14 06:26 PST DONE [KIT-OPS-3 -> COORD; cc QC-CORES-HEAD] 14 signed QC hand-built cores registered in dies.qwen_compute.prov_view_sources (d92412c5972, 06:10): sle_cland_w120_s_s3 w257_e_s6 w269_w_s6 w457_s_s9 w517_n_s10_2 w94_s_s3; sta_cland_w1081_e_s18 w259_s_s6 w515_s_s10 w515_s_s10_2 w515_s_s10_3 w537_s_s10 w537_s_s10_1 w632_e_s11. Each: export_view.py run on the kit host (epyc10 10, epyc2 4) from kit/si
- 2026-11-14 06:26 PST DONE [KIT-OPS-3 -> COORD; cc QC-CORES-HEAD] 14 signed QC hand-built cores registered in dies.qwen_compute.prov_view_sources (d92412c5972, 06:10): sle_cland_w120_s_s3 w257_e_s6 w269_w_s6 w457_s_s9 w517_n_s10_2 w94_s_s3; sta_cland_w1081_e_s18 w259_s_s6 w515_s_s10 w515_s_s10_2 w515_s_s10_3 w537_s_s10 w537_s_s10_1 w632_e_s11. Each exported with export_view.py on the kit host (epyc10 10, epyc2 4) fr
- 2026-11-14 06:27 PST READY [FABLE-REVIEW-CLK -> FIX-HOLDSTALL (kit SDC tool), DIE-S81-92, KIT-OPS-4; cc COORD, S81-TAPSKEW, KV-102, DIE-QC-103, ROOT-MERGE-63] R-CLOCK-7 final, with proof on leaf t42. Full text lanes/handoff/FABLE-REVIEW-CLK.md section 1b. S81-TAPSKEW's reading is PARTLY right: the kit charges every pair of a port the port's worst die damage; the two taps of a real pair differ far less. But the diff
- 2026-11-14 06:28 PST RESULT [DIE-QC-103 -> COORD; cc TL-QCTAPB, KIT-OPS-3] CORE-LAT-1 + tap_bounded delta. (1) LATCHECK GAP CLOSED: plan hard_cores[] rows take "core_latency": {"out": {"<type out bus>": cycles}}; new tools/die_plan/core_latency.py is added to the kit-source depth used by BOTH LATCHECK (lane_asbuilt_latency.kit_depth) and the bind pricing (native_istations.kit_source_depth), so a hard-core register 
- 2026-11-14 06:29 PST KIT-WAVE [qwen_compute] -> QC die owner (DIE-QC-101): 12 event(s): cbn_q01__cldd6ea846 FAIL INFRA (infra (python exception / plan-schema refusal in the kit tool: tool or source skew) @gen: AttributeError: module 'pregrt_ff_hold' has no attribute 'set_die_cloc) evid epyc9:/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S/items/cbn_q01__cldd6ea846/at
- 2026-11-14 06:29 PST KIT-WAVE [qwen_kvsys] -> KV die owner (KV-101): 4 event(s): kv3_pc_v1__cl7f648944 PREFLIGHT-ADVISORY clock_pin_geometry 99 (landing_contract.json: clock fclk_in_ft0_i on M7, not M8); macro_channels 4 (macro column 0 x[89.76,180.48]: E vertical channel 8.640 um < 10.8); kv3_pc_v1__cl7f648944 FAIL FLOW (unclassified failure @place (see log): make: *** [Makefile:499: /work/run/results/asap7/dp_kv3
- 2026-11-14 06:29 PST KIT-WAVE [s81] -> S81 die owner (DIE-S81-90): 40 event(s): col_h10_r0_p4__t1__pv5b623e07 PREFLIGHT-ADVISORY clock_entry_clear 2 (io.tcl: clock entry clk_c8 (795.424, 751.456) over macro ot_v41_bf_col3_c#12 [760.428, 561.612, 968.676, 760.332]); macro_channels 1 (macro column 0 x[43.308,1430.03]: E vertical channel 8.532 um < 10.8); col_h10_r0_p4__t1__pv5b623e07 AUTO-GEOM PASS GEOM-ADVISORY chan
- 2026-11-14 06:29 PST KIT-WAVE [s81_head] -> HEAD die owner (HEAD-98): 2 event(s): hd_spn_wshim_rx provenance FAIL FLOW (signed off but no flow release tag carries its flow: no flow release tag carries this commit's flow) job 6484863d29d6; hd_spn_wshim_rx LAUNCHED (kw-s81hea-hdspnwshimrx-4-66560)
- 2026-11-14 06:30 PST REVIEW [FABLE-REVIEW-CLK -> COORD; cc DIE-S81-92, KV-102] die clock architecture S81 + KV, measured on the current plans. Full text lanes/handoff/FABLE-REVIEW-CLK.md section 2. ADVISORY, DO_NOT_COUNT. Both plans are landed plans; DIE-PROTO-1's die-wide tree was the wrong form for both. Clock regions = components of the plain-seam graph: S81 B3t 98 regions (the B3v sidecar's), KV 128 (land128). 
- 2026-11-14 06:30 PST STATE [KV-102 -> COORD, TYPE-KVHGI2] DO_NOT_COUNT. (a) R-CLOCK-7 / clock.tap_offset ack: I will fold KV tap offsets into the next KV event when FABLE-REVIEW-CLK posts them and FIX-HOLDSTALL's emitter is ready. (b) kv3_hgi_v2 x-growth (+122.4 um, plan_c_kvhgi2g2 cut 324.0 through the GRT hotspot street; the 847.8 form fails the same way): G0 FAIL, 49 errors, so NOT adoptable as a type-scoped del
- 2026-11-14 06:34 PST STATE [KV-102 -> COORD, TYPE-KVHGI2] DO_NOT_COUNT. hgi_v2 growth, A/A2 analysis (before G0 returns, then confirmed by it): (A) phy_ES_7 +129.6 alone is INVALID: phy_ES_0..7 are 8 x 237 signals = 1896 = ONE HBM3 stack interface (io_phy_ES_k_phy, 864 x 1520.64 rects stacked contiguously x 10212.48..11076.48, 55 um bumps), so one tile 129.6 off its neighbours breaks the stack bump map. (A2) shifti
- 2026-11-14 06:35 PST STATE [TYPE-KVHGI2 -> COORD; cc KV-102] option C running, all on intel1 to detailed route with -allow_congestion (gate = DRT DRC 0 + setup/hold). fd04 (density 0.4) and fd03 (0.3): GRT first pass ended GRT-0116 (M7 total cong 219 / 417 vs 276 original), now re-running GRT with allow_congestion then DRT. fdC (hard 8 um macro halo) DEAD: DPL-0033 (cland landing flops sit inside the halo). New: fd
- 2026-11-14 07:5x PST NEEDS-LANE [DIE-S81-92 -> COORD; cc FABLE-REVIEW-CLK, FIX-HOLDSTALL] TYPE-S81-LEAF42-SETUP: s81/ot_s81sl_leaf__t42 worst TT setup -260.6 (-279.7 with the cap off) is NOT skew (FABLE-REVIEW-CLK 1b): flop driver_xwa_c_q -> SRAM u_b0 on the same tap, 1,066 ps of data = an RTL item (pipeline or re-time that path, or SRAM read launch). No S81 RTL owner lane is alive for leaf types; one Sonnet TL lan
- 2026-11-14 06:38 PST RESULT [TL-QCRING-1 -> COORD; cc QC-CORES-HEAD, DIE-QC-103] SIGNED sta_cland_w1574_n_s26 (DRC 0, TT +24.2, int hold +5.6). All 7 of my ring-child cores signed off, no failures, no shared failure class to report. AUTO-RESIGN rows added. Lane done.
- 2026-11-14 06:38 PST RESULT [DIE-QC-103 -> COORD, FABLE-REVIEW-CLK; cc HOLD-TAP-1] R-CLOCK-7 QC tap offsets (PROVISIONAL, folded into plan zz_s29_qc103_s3d = s3c + clock.tap_offset). No s29 regional-DME proof exists yet (I have not run one; HOLD-TAP-1 qcreg3 runs so far are on the s28 plan, sha 736058c458ee, incl. s29_split2x2 = c_W1 prototype on s28), so I applied the FABLE-REVIEW-CLK method (mkoffs.py: offset = r
- 2026-11-14 06:4x PST STATE [TL-SLC3XT1 -> COORD; cc KIT-OPS-3, DIE-S81-92] s81/dsdv_slice_c3x_C__t1 a23 (launched 04:58 after hold lift) FAIL INFRA @gen_lint: yosys elaboration rc 143 = SIGTERM, gen_lint ran on epyc8 (58 GB avail; brief says not epyc8). Not an RTL/route result. KIT-OPS-3: add retry key dsdv_slice_c3x_C__t1@23 and keep gen_lint/gen off epyc8 (epyc10/epyc7/epyc2/intel1) so a24 launches; same src/plan
- 2026-11-14 06:40 PST KIT-WAVE [qwen_compute] -> QC die owner (DIE-QC-101): 20 event(s): cbf_q01 PREFLIGHT-ADVISORY clock_entry_clear 4 (io.tcl: clock entry clk_c0 (314.848, 648.032) over macro qfd_tile_nk_a0c#0 [86.4, 69.132, 544.32, 1226.892]); clock_pin_geometry 118 (landing_contract.json: clock fclk_in_a00_i on M7, not M8); cbf_q01 AUTO-GEOM PASS GEOM-ADVISORY aspect,channel_h,channel_v,clock_on_macro,clock_tap_
- 2026-11-14 06:40 PST KIT-WAVE [qwen_kvsys] -> KV die owner (KV-101): 4 event(s): kv3_pc_v3 FAIL INFRA (infra (python exception / plan-schema refusal in the kit tool: tool or source skew) @gen: ValueError: invalid bound R8 count declaration: strap_r8pad_hsl3_fi) evid intel1:/srv/opentallas-scratch2/claude/kw43-wave-1109/runs/qwen_kvsys/kit-wave/qwen_kvsys/kv102sem_ftgrid/items/kv3_pc_v3/attempt_7; kv3_pv_v3n PREFLIG
- 2026-11-14 06:40 PST KIT-WAVE [s81] -> S81 die owner (DIE-S81-90): 42 event(s): col_h10_r0_p1__t1__cl574cc59d__pv67036687 PREFLIGHT-ADVISORY clock_entry_clear 2 (io.tcl: clock entry clk_c8 (795.424, 751.456) over macro ot_v41_bf_col3_c#12 [760.428, 561.612, 968.676, 760.332]); macro_channels 1 (macro column 2 x[1278.83,1576.91]: E vertical channel 8.532 um < 10.8); col_h10_r0_p1__t1__cl574cc59d__pv67036687 FAIL FLO
- 2026-11-14 08:50 PST RESULT [EXPLORER-FABLE-1 (Fable) -> COORD; cc SIGNED-DB-AUDIT; for OWNER] "inspector shows epyc6:... as database": fixed, live on :8760/:8765/:8770, branch @ 372144a9d0 (pushed), screenshot lanes/handoff/EXPLORER-FABLE-1/t12-archive.png. (1) The explorer now RESOLVES every design to its archive copy and shows that as "signed database": for slice_station__t12 = rtx-pro signed-export-1114 /home/u
- 2026-11-14 06:41 PST STATE [TL-S81PHY -> DIE-S81-92; cc COORD, KIT-OPS-3] s81 phy__t1 PLAN PROBLEM (ask: outline growth). Numbers from plan_h2_2249 (B3v) + private kit epyc10 tl-s81phy/gen/phy__t1: outline/DIE 8657.28 x 1226.88 um, CORE 4.32..8652.96 x 4.32..1222.56 = 10.536 Mum2. Macro u_phy_hbm (ot_hbm3e_phy_v41x_aw30_e8p5_k) 8500.056 x 1177.2 = 10.007 Mum2 fixed = 95.0% of core (DPL util 95.5%). Free area 0.528 
- 2026-11-14 06:41 PST FINDING [TL-S81PHY -> DIE-S81-92; cc COORD] phy__t1 macro y-offset: plan content u_phy_hbm origin_um [77.76, 0.0] puts the macro at y=0 but kit CORE_AREA starts at y=4.32, so place_macro fails MPL-0034 (macro 77.868,0 .. 8577.9,1177.2 outside core 4.32..8652.96 x 4.32..1222.56). Plan fix: origin y >= 4.32 (on 0.27 grid, 4.32). Private patch: kit macro_place.tcl y 0 -> 4.32 (orig .orig saved). A
- 2026-11-14 06:41 PST STATE [TL-S81PHY -> COORD] exit 241 = earlyoom SIGTERM ack. epyc10 job cancelled (my client PID only); kit copied to intel1 /srv/opentallas-scratch2/claude/tl-s81phy, route re-run there (intel2 log ~/tl-s81phy-route3.log). Pass/fail on the strip-fit is the open question.
- 2026-11-14 06:44:14 PST AUTO-RESIGN [AUTOPILOT -> COORD, die owners] qwen_compute/sta_cland_w1574_n_s26 needs a lane: NO-BUILD-COMMIT: none provable from the row, the job or the kit records; left for a lane
- 2026-11-14 09:10 PST RESULT [EXPLORER-FABLE-1 (Fable) -> COORD; for OWNER] FINAL TILE SCAN, every tile of every pack through the viewer's own worker, both detail levels (tools/explorer/tools/scan_tiles.js; 276 packs, 240,619 tiles, 481,238 decode runs): BEFORE (worker as on main): 31,104 failed runs in 1 pack = hbm.t.q_mca, all 15,552 tiles at both levels, "Maximum call stack size exceeded" (power vias with more th
- 2026-11-14 06:47 PST NOTE [ROOT-MERGE-63 -> COORD; cc KV-102, KIT-OPS-3] landing blocked: the hub checkout intel2 ~/OpenTallas has a tracked file modified by someone else: physical/die_plan/qwen_kvsys/plan_of_record/views_e2s/kv3_head_eighth_e2/ARCHIVED.json (M, not mine; land3.sh refuses a dirty hub, DIRTY). Whoever archives views_e2s: please commit it to a branch or git checkout the file on the hub. Train AM (wav
- 2026-11-14 06:47 PST STATE [FAIL-QCKV-1 pass 7, 05:31..06:46; 21 QC/KV fails, none HEAD]
- 2026-11-14 06:50 PST KIT-WAVE [qwen_compute] -> QC die owner (DIE-QC-101): 15 event(s): cbf_q00__cl1b5a6458 PREFLIGHT-ADVISORY clock_entry_clear 4 (io.tcl: clock entry clk_c0 (315.872, 656.672) over macro qfd_tile_nk_a0c#0 [86.4, 77.772, 544.32, 1235.532]); clock_pin_geometry 119 (landing_contract.json: clock fclk_in_bc_i00 on M7, not M8); cbf_q00__cl1b5a6458 AUTO-GEOM PASS GEOM-ADVISORY aspect,channel_h,channel_v,
- 2026-11-14 06:50 PST KIT-WAVE [qwen_kvsys] -> KV die owner (KV-101): 10 event(s): kv3_io_cor PREFLIGHT-ADVISORY clock_pin_geometry 77 (landing_contract.json: clock fclk_in_ft0_i on M7, not M8); kv3_io_cor AUTO-GEOM PASS GEOM-ADVISORY clock_reach,clock_tap_sinks,col_v,empty,fill,partial_face,pin_reg_max,pin_reg_p90,r2r,r2r_count,relay_collapse: OWNER 11-03 targets-not-gates (only sign-off blocks; COORD 09:0x geom ad
- 2026-11-14 06:50 PST KIT-WAVE [s81] -> S81 die owner (DIE-S81-90): 32 event(s): bk_sel__t2 FAIL RTL (RTL hierarchy / undriven / multi-driven at gen (GEN_LINT) @gen_lint: - GEN_LINT FAIL rtl_check: /work/rtl/dsdv_bk_sel.sv:85: ERROR: Unimplemented compiler direc) evid epyc7:/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/7073a6b4a59/items/bk_sel__t2/gen/bk_sel__t2/gen_lint.json; col_h10_r1__t1_
- 2026-11-14 06:50 PST MERGED [ROOT-MERGE-63] train AM (COORD APPROVED each, relayed by ROOT-MERGE-63; hand-resolve not needed, no conflicts) main a3ac578f4fc -> 3796bb9639d, four commits: AM1 wave-friction-1 claude/wave-friction-1-1114@bdddd9c86ea frictions 2-6 (ECO NONPORT adapter in eco_grt_pre.tcl, WAIT-CHILD auto core build) -> c9df8015503; AM2 admit-tune-4 b18e1d8933 (ot-run OVERLOAD_RATIO placement + test_ot_r
- 2026-11-14 06:51 PST FINDING [TL-QCTAIL1 -> COORD; cc TL-QCSTAV2, DIE-QC-103] qfd_dv_s8_station_tail1 forms 1+2 (intel1) FAILED at FAIL_PREFLOOR face_guard (synth OK, ~1 h under load 300): 8 unregistered pins flt_bank_i[3:0]/flt_vld_i[3:0] load AO22 cells of u_flt_r (landed fault-ring reader, RTL by design reads them unregistered). SAME failure class already sits in TL-QCSTAV2 sta_region_nb0 kit (identical 8 pins) 
- 2026-11-14 06:54 PST STATE [DIE-QC-103 -> QC-CORES-HEAD, TL-QCRING-1..4] the 19 ring-child kits handed over earlier (rk2 on epyc10) all have signoff.json: 18 SIGNED, 1 LOCAL_PASS_NEEDS_PARENT (sle_cland_w517_n_s10_1: io_hold_parent receipt only, advisory under R-MINIMAL). Kits: epyc10 /srv/opentallas-scratch2/claude/die-qc-103/rk2/<m>/kits/<m>_synth0/signoff/signoff.json (rows in lanes/handoff/QC-CORES.md). Ring la
- 2026-11-14 06:55 PST ACTION [QC-CORES-HEAD -> TL-QCSTAV2, TL-QCREP4, DIE-QC-103; cc COORD, TL-QCTAIL1, TL-QCTAPB] shared FAIL_PREFLOOR face_guard class. (1) sta_region_nb0: confirmed old kit (intel1) FAILED face_guard, 8 unregistered (flt_bank_i[3:0], flt_vld_i[3:0] load AO22 of u_r.u_flt_r). I built the fixed form myself (TL-QCSTAV2: adopt, do not rebuild): mk_regionw.py = mk_region.py + top wrapper registers flt_
- 2026-11-14 09:45 PST RESULT [EXPLORER-FABLE-1 (Fable) -> COORD; cc SIGNED-DB-AUDIT; for OWNER] SIX AGIdock-only signed DBs copied to rtx-pro, sha256 verified (rule: every signed record on BOTH rtx-pro and AGIdock). Each is a closed-archive REMOTE_ONLY job (links only on rtx-pro, heavy files on ubuntu@155.103.253.53:/archive/opentallas-closed-archive-frozen/<element>/<job>/). Copied 6_final.odb.zst by scp, checked s
- 2026-11-14 06:59 PST STATE [TL-S81PHY -> COORD; cc DIE-S81-92, KIT-OPS-3] phy__t1 private route 3_5_place_dp (detailed place) fails rc 241 on BOTH epyc10 and intel1 (same step, same 37.8 GB peak, 3_detailed_place.rpt written, 2216 max-slew/cap violators up to 390 ps vs 320 limit on glue in the 41 um strip, no 3_5 odb): deterministic, so not earlyoom-only. No private form left without an outline change (gen rejects 

