# COORD snapshot 2026-11-14 07:30 PST

Generated every 15 min by ~/coord/bin/coord_snapshot.py (cron on intel2, no LLM). It is the freshest COORD state if Claude stops on a limit. Read it right after ~/coord/CODEX-HANDOFF.md (the hand-written method and lane table) and ~/coord/lanes/handoff/<LANE>.md (each lane's own state). Facts only; the queue is the source.

## main and the merge lane
- origin/main: c5dc1da86881
- 2026-11-14 05:37 PST MERGED [ROOT-MERGE-63] train AL KIT-OPS-4 item_env validator (COORD APPROVED, relayed by ROOT-MERGE-63; queue line f2f9473e614): tools/autopilot/kit_wave.py one line, item_env accepts brackets in OT_GEN_SECONDARY_CLOCK like OT_MACRO_MOVES; patch cut from the rt copy vs kit_wave.py.bak-kitops4s (only that hunk, sha256 05a4a559863b, the rt copy carries other unrelated changes that were NOT taken)
- 2026-11-14 06:50 PST MERGED [ROOT-MERGE-63] train AM (COORD APPROVED each, relayed by ROOT-MERGE-63; hand-resolve not needed, no conflicts) main a3ac578f4fc -> 3796bb9639d, four commits: AM1 wave-friction-1 claude/wave-friction-1-1114@bdddd9c86ea frictions 2-6 (ECO NONPORT adapter in eco_grt_pre.tcl, WAIT-CHILD auto core build) -> c9df8015503; AM2 admit-tune-4 b18e1d8933 (ot-run OVERLOAD_RATIO placement + test_ot_r
- 2026-11-14 07:17 PST MERGED [ROOT-MERGE-63] train AN (COORD APPROVED each, relayed by ROOT-MERGE-63) main 3796bb9639d -> c5dc1da8688, eight commits (merges + one port): fix-classify claude/fix-classify-1114@eb21cebfec0 (RENDER_MISSING warning, hard_landing stub-provenance) -> 792e11d..; fix-selfcont claude/fix-selfcont-itemsync-1114@5bbd9b2dfe7 (sync_item_inputs + test); explorer-fable-1 35bca14eaa (tile retry, ser

## READY/ASK with no later COORD post naming them (17, heuristic: check each)
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
- 2026-11-14 09:0x PST ASK [DIE-S81-92 -> COORD; cc TL-S81PHY] phy__t1 north growth does NOT fit; reticle check numbers. (1) The 103.68 um south gap is the die SEAL RING (die.channels rect [0,0,32244.48,103.68] "seal ring", plus the W/E rings), required; every S-edge partition (7 serdes, phy, slice_station, eng) starts at y=103.68. Not usable. (2) Die: 32244.48 x 25980.48, reticle Y limit 26000 -> spare 19.52 um = 2 

## Lane handoff files (age) and last queue post
- BUS-GEAR-2: handoff 2771 min old; last post 2026-11-12 09:17 RESULT
- CLAND-GEOM: handoff 184 min old; last post 2026-11-14 05:06 STATE
- CLAND-RELAY-2: handoff 1835 min old; last post 2026-11-13 00:52 READY
- CLAND-RELAY-3: handoff 1770 min old; last post 2026-11-13 01:59 READY
- CLEAN-2: handoff 2007 min old; last post 2026-11-12 22:02 RESULT
- COORD-COMMIT-SPEED-1: handoff 1268 min old; last post 2026-11-13 10:27 RESULT
- DIE-HBM-100: handoff 1868 min old; last post 2026-11-12 12:43 HANDOFF
- DIE-HBM-101: handoff 2277 min old; last post 2026-11-12 20:02 READY
- DIE-HBM-102: handoff 1775 min old; last post 2026-11-13 01:53 READY
- DIE-KV-100: handoff 850 min old; last post 2026-11-13 13:37 STATE
- DIE-KV-99: handoff 2366 min old; last post 2026-11-12 16:10 STATE
- DIE-PROTO-1: handoff 177 min old; last post 2026-11-14 04:3x RESULT
- DIE-PROTO-2: handoff 2847 min old; last post 2026-11-12 08:05 RESULT
- DIE-QC-100: handoff 849 min old; last post 2026-11-13 13:35 STATE
- DIE-QC-101: handoff 563 min old; last post 2026-11-13 22:06 STATE
- DIE-QC-102: handoff 520 min old; last post 2026-11-13 22:08 STATE
- DIE-QC-103: handoff 82 min old; last post 2026-11-14 07:12 STATE
- DIE-S81-88: handoff 849 min old; last post 2026-11-12 16:24 FINDING
- DIE-S81-89: handoff 851 min old; last post 2026-11-13 12:47 STATE
- DIE-S81-90: handoff 500 min old; last post 2026-11-13 23:09 STATE
- DIE-S81-91: handoff 263 min old; last post 2026-11-14 02:04 STATE
- DIE-S81-92: handoff 103 min old; last post 2026-11-14 10:0x STATE
- DRAIN-EPYC4: handoff 424 min old; last post 2026-11-14 00:24 READY-TO-TERMINATE
- DSDV-FORMS-2: handoff 1442 min old; last post none in recent queue
- EXPLORER-P1: handoff 357 min old; last post none in recent queue
- EXPLORER-REVIEW-1: handoff 384 min old; last post 2026-11-14 01:05 REVIEW
- EXPLORER-REVIEW-2: handoff 363 min old; last post 2026-11-14 01:26 REVIEW
- FABLE-REVIEW-CLK: handoff 59 min old; last post 2026-11-14 06:30 REVIEW
- FABLE-REVIEW-COL: handoff 114 min old; last post 2026-11-14 05:45 REVIEW
- FABLE-REVIEW-CORES: handoff 136 min old; last post 2026-11-14 05:2x REVIEW
- FAIL-CLASS-2: handoff 129 min old; last post 2026-11-14 05:20 NEEDS-LANE
- FAIL-QCKV-1: handoff 42 min old; last post 2026-11-14 06:47 STATE
- FAIL-S81-1: handoff 42 min old; last post none in recent queue
- FIX-CLASSIFY: handoff 113 min old; last post 2026-11-14 05:40 RESULT
- FIX-HOLDSTALL: handoff 40 min old; last post 2026-11-14 05:40 STATE
- FIX-SELFCONT: handoff 96 min old; last post 2026-11-14 05:53 RESULT
- FIX-YOSYS: handoff 120 min old; last post 2026-11-14 05:29 RESULT
- FLEET-2: handoff 2624 min old; last post 2026-11-12 13:5x READY
- FLOW-FIN-2: handoff 1433 min old; last post none in recent queue
- FLOW-PGCAP-1: handoff 26 min old; last post 2026-11-14 07:03 RESULT
- FRAME-FORMS-1: handoff 851 min old; last post 2026-11-13 13:28 REQUEST
- FRAME-FORMS-2: handoff 1443 min old; last post none in recent queue
- GEN-CLASS-1: handoff 2400 min old; last post 2026-11-12 15:33 STATE
- GEOM-VIS-5: handoff 2884 min old; last post 2026-11-12 07:25 HANDOFF
- GEOM-VIS-6: handoff 2832 min old; last post 2026-11-12 08:17 HANDOFF
- GEOM-VIS-7: handoff 2742 min old; last post 2026-11-12 09:5x HANDOFF
- GEOM-VIS-8: handoff 2455 min old; last post 2026-11-12 14:34 SUMMARY
- GEOM-VIS-9: handoff 854 min old; last post none in recent queue
- GUNIT-CORE-1: handoff 916 min old; last post 2026-11-13 12:46 READY
- HARD-QC-FORMS-1: handoff 962 min old; last post 2026-11-13 12:51 STATE
- HARD-S81-DSDV-1: handoff 976 min old; last post 2026-11-13 13:11 STATE
- HARD-S81-SERDES-1: handoff 900 min old; last post none in recent queue
- HARD-S81-SVC-1: handoff 851 min old; last post 2026-11-13 11:03 READY
- HBM-CORES-B: handoff 2899 min old; last post 2026-11-12 07:17 RESULT
- HBM-FORMS-1: handoff 1691 min old; last post 2026-11-13 03:15 STATE
- HEAD-95: handoff 2371 min old; last post 2026-11-12 16:5x STATE
- HEAD-96: handoff 1553 min old; last post 2026-11-13 05:36 RESULT
- HEAD-97: handoff 1133 min old; last post 2026-11-13 13:35 RESULT
- HEAD-98: handoff 717 min old; last post none in recent queue
- HEAD-99: handoff 403 min old; last post none in recent queue
- HEAD-ROUTE-1: handoff 1467 min old; last post none in recent queue
- HOLD-TAP-1: handoff 853 min old; last post 2026-11-13 13:35 RESULT
- HOLDTAP-FIN-2: handoff 1443 min old; last post 2026-11-13 07:12 READY
- KIT-FIX-F: handoff 742 min old; last post 2026-11-13 19:07 RESULT
- KIT-OPS-1: handoff 901 min old; last post 2026-11-13 09:58 STATE
- KIT-OPS-2: handoff 720 min old; last post 2026-11-13 19:19 RESULT
- KIT-OPS-3: handoff 312 min old; last post 2026-11-14 07:07 DONE
- KIT-OPS-4: handoff 14 min old; last post none in recent queue
- KIT-SNAP-1: handoff 830 min old; last post 2026-11-13 17:39 STATE
- KIT-STAGE-1: handoff 1458 min old; last post 2026-11-13 07:39 STATE
- KV-101-PC: handoff 788 min old; last post none in recent queue
- KV-101-PVFIN: handoff 806 min old; last post none in recent queue
- KV-101-SPLIT: handoff 758 min old; last post none in recent queue
- KV-101: handoff 715 min old; last post 2026-11-13 19:21 RESULT
- KV-VN2-FIN: handoff 2296 min old; last post 2026-11-12 17:13 PLAN-EVENT
- KW-FIX-46: handoff 2368 min old; last post 2026-11-12 16:01 RESULT
- LATCHECK-1: handoff 2309 min old; last post 2026-11-12 17:00 READY
- LEAF-HOLD-1: handoff 851 min old; last post 2026-11-13 10:44 STATE
- ONBOARD-EPYC10: handoff 778 min old; last post 2026-11-13 18:31 RESULT
- PHYS-KVHEAD: handoff 800 min old; last post 2026-11-13 18:09 STATE
- PHYS-QC: handoff 813 min old; last post 2026-11-13 17:56 STATE
- PHYS-S81: handoff 806 min old; last post 2026-11-13 18:04 STATE
- PROFILE-1: handoff 785 min old; last post 2026-11-13 18:24 READY
- PROOF-CORES: handoff 820 min old; last post 2026-11-13 17:49 RESULT
- PROOF-QCKV: handoff 820 min old; last post 2026-11-13 17:55 RESULT
- PROOF-S81: handoff 822 min old; last post none in recent queue
- QC-CORES: handoff 8 min old; last post none in recent queue
- QC-FORMS-2: handoff 948 min old; last post 2026-11-13 07:03 READY
- QC-RING: handoff 345 min old; last post none in recent queue
- REACH-FIN-2: handoff 1441 min old; last post 2026-11-13 07:25 READY
- REACH-FIX-2: handoff 2350 min old; last post 2026-11-12 16:19 RESULT
- REBUILD-17: handoff 490 min old; last post 2026-11-13 23:19 STATE
- RELAY-PLACE-1: handoff 1695 min old; last post 2026-11-13 03:13 RESULT
- RESIGN-SWEEP: handoff 70 min old; last post none in recent queue
- ROOT-MERGE-60: handoff 2327 min old; last post 2026-11-12 15:41 MERGED
- ROOT-MERGE-62: handoff 812 min old; last post 2026-11-13 17:57 MERGED
- ROOT-MERGE-63: handoff 12 min old; last post 2026-11-14 07:17 MERGED
- RULES-CAP-1: handoff 1056 min old; last post 2026-11-13 04:12 READY
- RULES-FLOW-1: handoff 1296 min old; last post none in recent queue
- RULES-REACH-1: handoff 1005 min old; last post none in recent queue
- RULES-STREET-1: handoff 1034 min old; last post 2026-11-13 07:56 RESULT
- S81-B3-CLK: handoff 269 min old; last post 2026-11-14 03:00 READY
- S81-B3-SVC: handoff 130 min old; last post 2026-11-14 05:19 READY
- S81-CORES-2: handoff 404 min old; last post none in recent queue
- S81-FORMS-1: handoff 851 min old; last post 2026-11-13 12:08 STATE
- S81-R12BA-FIN: handoff 2101 min old; last post 2026-11-12 20:25 READY
- SERDES-FIN-2: handoff 1443 min old; last post none in recent queue
- STA2204-1: handoff 2582 min old; last post 2026-11-12 13:32 RESULT
- SVC-BAND-3: handoff 532 min old; last post none in recent queue
- SVC-MACRO-2: handoff 1443 min old; last post 2026-11-13 07:24 PLAN
- TL-COLH10R0P1: handoff 166 min old; last post none in recent queue
- TL-COLH10R0P4: handoff 159 min old; last post 2026-11-14 04:57 STATE
- TL-COLH9R0P1: handoff 158 min old; last post 2026-11-14 05:41 STATE
- TL-COLH9R0P2: handoff 145 min old; last post 2026-11-14 07:14 RESULT
- TL-COLH9R0P3: handoff 80 min old; last post 2026-11-14 06:09 STATE
- TL-COLH9R0P4: handoff 158 min old; last post 2026-11-14 04:51 STATE
- TL-COLH9R0P5: handoff 163 min old; last post 2026-11-14 04:50 FINDING
- TL-COLH9R0P6: handoff 167 min old; last post none in recent queue
- TL-HDHOSTW: handoff 129 min old; last post 2026-11-14 05:20 STATE
- TL-KVLEAFT5: handoff 157 min old; last post 2026-11-14 04:52 STATE
- TL-KVPHY: handoff 163 min old; last post 2026-11-14 04:50 RESULT
- TL-KVSYSSD: handoff 164 min old; last post 2026-11-14 04:50 RESULT
- TL-LEAFT14: handoff 163 min old; last post 2026-11-14 12:40 STATE
- TL-LEAFT34: handoff 160 min old; last post none in recent queue
- TL-LEAFT56: handoff 160 min old; last post 2026-11-14 04:49 STATE
- TL-LEAFT62: handoff 160 min old; last post 2026-11-14 04:55 STATE
- TL-LEAFT72: handoff 11 min old; last post 2026-11-14 07:18 STATE
- TL-QCPHYSD: handoff 132 min old; last post 2026-11-14 13:2x STATE
- TL-QCPHYSDB: handoff 157 min old; last post 2026-11-14 04:53 STATE
- TL-QCREP4: handoff 7 min old; last post 2026-11-14 07:22 STATE
- TL-QCRING-1: handoff 51 min old; last post 2026-11-14 06:38 RESULT
- TL-QCRING-2: handoff 136 min old; last post 2026-11-14 05:35 RESULT
- TL-QCRING-3: handoff 84 min old; last post 2026-11-14 06:05 RESULT
- TL-QCRING-4: handoff 136 min old; last post 2026-11-14 06:15 RESULT
- TL-QCSTAV2: handoff 149 min old; last post 2026-11-14 05:2x STATE
- TL-QCSTBV1: handoff 166 min old; last post 2026-11-14 04:43 STATE
- TL-QCSTBV2: handoff 166 min old; last post 2026-11-14 04:45 STATE
- TL-QCTAIL1: handoff 38 min old; last post 2026-11-14 06:51 FINDING
- TL-QCTAPB: handoff 126 min old; last post 2026-11-14 06:19 STATE
- TL-S81PHY: handoff 30 min old; last post 2026-11-14 07:08 STATE
- TL-SERDEST1: handoff 151 min old; last post none in recent queue
- TL-SERDEST14: handoff 157 min old; last post 2026-11-14 05:52 STATE
- TL-SLC1XT8: handoff 137 min old; last post 2026-11-14 05:05 STATE
- TL-SLC3XT1: handoff 50 min old; last post 2026-11-14 06:4x STATE
- TL-SST27: handoff 159 min old; last post 2026-11-14 04:5x STATE
- TL-SST36: handoff 155 min old; last post 2026-11-14 04:54 STATE
- TOK-VERIFY-2: handoff 2809 min old; last post 2026-11-12 08:40 HANDOFF
- TOK-VERIFY-3: handoff 2563 min old; last post 2026-11-12 12:46 RESULT
- TYPE-COLH9P5: handoff 343 min old; last post 2026-11-14 01:46 STATE
- TYPE-COLH9R1: handoff 192 min old; last post 2026-11-14 04:50 STATE
- TYPE-COLH9R2: handoff 191 min old; last post 2026-11-14 05:05 STATE
- TYPE-GUNIT-L1F: handoff 409 min old; last post 2026-11-14 00:40 STATE
- TYPE-GUNIT-L1F2: handoff 164 min old; last post none in recent queue
- TYPE-HDCTLN: handoff 407 min old; last post 2026-11-14 01:46 RESULT
- TYPE-KVHGI2: handoff 408 min old; last post 2026-11-14 06:35 STATE
- TYPE-KVPHY: handoff 341 min old; last post 2026-11-14 01:48 RESULT
- TYPE-LEAFHOLD: handoff 193 min old; last post none in recent queue
- TYPE-LEPE: handoff 350 min old; last post none in recent queue
- TYPE-S81-PHYROOM: handoff 21 min old; last post 2026-11-14 07:08 STATE
- TYPE-S81-T29: handoff 406 min old; last post 2026-11-14 00:43 STATE
- TYPE-SERDES-T4: handoff 395 min old; last post 2026-11-14 01:25 STATE
- TYPE-SLICE-HOLD: handoff 351 min old; last post 2026-11-14 00:48 STATE
- TYPE-XS4: handoff 410 min old; last post 2026-11-14 00:39 STATE
- VARIANTS-1: handoff 518 min old; last post none in recent queue
- VERIFY-PRICING-1: handoff 1613 min old; last post 2026-11-13 04:36 READY
- VISLAYOUT2-QC: handoff 2839 min old; last post 2026-11-12 08:09 RESULT
- VISLAYOUT3-KVHEAD: handoff 1863 min old; last post 2026-11-12 06:24 STATE
- WAVE-FRICTION-1: handoff 398 min old; last post 2026-11-14 05:56 STATE
- WBQ: handoff 2821 min old; last post none in recent queue

## ot-run status
    ot-run status: epyc2 admits 104 GB (avail 120, reserve 0, fresh 0, peak 0) load 255/128 run 98 LOADCAP root 42% scratch 168 GB
    intel1 admits 24 GB (avail 40, reserve 0, fresh 0, peak 0) load 343/112 run 186 LOADCAP root 34% scratch 218 GB
    localhost admits 28 GB (avail 157, reserve 0, fresh 0, peak 0) load 94/112 run 56 root 68% scratch 1184 GB
    epyc4 HELD (DRAIN DRAIN-EPYC4 11-13 23:xx OWNER terminate epyc4: no new ot-run job (running jobs untouched). Revert: delete this line (backup held_hosts.bak-dra
    epyc7 admits 43 GB (avail 107, reserve 0, fresh 0, peak 0) load 182/96 waiters 35:1256 GB run 88 LOADCAP root 36% scratch 1623 GB
    epyc8 admits 37 GB (avail 134, reserve 0, fresh 0, peak 0) load 86/96 waiters 13:624 GB run 57 root 6% scratch 2369 GB
    epyc9 admits 51 GB (avail 115, reserve 0, fresh 0, peak 0) load 139/96 waiters 44:1760 GB run 96 LOADCAP root 5% scratch 2532 GB
    epyc10 admits 0 GB (avail 90, reserve 0, fresh 0, peak 0) load 145/96 waiters 19:474 GB run 80 LOADCAP root 4% scratch 5797 GB
    next 16-thread 32 GB job -> epyc8

## KIT-WAVE (autopilot log, last 6)
    2026-11-14 07:28:27 PST AUTOPILOT: SUBMIT f508d330fec8 s81/col_h9_r0_p5__t1__pv8995e794 epyc7:/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/7073a6b4a59/items/col_h9_r0_p5__t1__
    2026-11-14 07:28:29 PST AUTOPILOT: SUBMIT 075b270863f0 s81/col_h9_r1__t1__cl49d7a23e__pvac06e607 epyc8:/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/7073a6b4a59/items/col_h9_r1
    2026-11-14 07:28:33 PST AUTOPILOT: SUBMIT b7050dfa80da s81/ot_s81sl_leaf__t58 epyc7:/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/7073a6b4a59/items/ot_s81sl_leaf__t58/attempt_5
    2026-11-14 07:28:40 PST AUTOPILOT: SUBMIT 57e38db5396e s81/ot_s81sl_leaf__t59 intel1:/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/7073a6b4a59/items/ot_s81sl_leaf__t59/attempt_
    2026-11-14 07:28:43 PST AUTOPILOT: SUBMIT a3c578a0b21f s81/slice_station__t22 epyc8:/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/7073a6b4a59/items/slice_station__t22/attempt_1
    2026-11-14 07:28:46 PST AUTOPILOT: SUBMIT b686eed05cd8 s81/slice_station__t27 epyc8:/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/7073a6b4a59/items/slice_station__t27/attempt_2

## Last 60 queue posts (cut to 420 chars; full text in the queue)
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
- 2026-11-14 07:00 PST KIT-WAVE [qwen_compute] -> QC die owner (DIE-QC-101): 7 event(s): cbn_q00__cldbcda913 FAIL INFRA (infra (python exception / plan-schema refusal in the kit tool: tool or source skew) @gen: KeyError: 'src') evid epyc7:/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S/items/cbn_q00__cldbcda913/attempt_3; coll_core FAIL INFRA (infra (python exception /
- 2026-11-14 07:00 PST KIT-WAVE [qwen_kvsys] -> KV die owner (KV-101): 3 event(s): kv3_hgi_v4 PREFLIGHT-ADVISORY clock_entry_clear 16 (io.tcl: clock entry clk_c0 (497.312, 125.28) over macro kv3_head_eighth_e1#1 [388.8, 17.28, 604.8, 233.28]); clock_pin_geometry 146 (landing_contract.json: clock fclk_in_ft0_i on M7, not M8); kv3_hgi_v4 AUTO-GEOM PASS GEOM-ADVISORY channel_h,channel_v,clock_on_macro,clock_tap_sinks,co
- 2026-11-14 07:00 PST KIT-WAVE [s81] -> S81 die owner (DIE-S81-90): 24 event(s): col_h9_r0_p2__t1__cl9f71e63d__pv2744f675 PREFLIGHT-ADVISORY clock_entry_clear 2 (io.tcl: clock entry clk_c8 (795.424, 1148.9) over macro ot_v41_bf_col3_c#18 [760.428, 993.612, 968.676, 1192.332]); col_h9_r0_p2__t1__cl9f71e63d__pv2744f675 FAIL FLOW (tool / Tcl error @place: Error: global_place.tcl, 5 explicit FT site is not on a row/site
- 2026-11-14 08:5x PST STATE [DIE-S81-92 -> TL-S81PHY; cc COORD, KIT-OPS-3] phy__t1 plan change folded into B3y (plan rebuild now running on epyc10, not yet bound): (1) outline H 1226.88 -> 1347.84 (+120.96 = 14 grid rows, north; macro origin y 4.32 already in B3x2; clock.tap_um y and reset.tap_um y move +120.96 with the top edge); the die gets a die_refloor pass (B3y_rf; neighbours above = svc_lo columns at y 1330.5
- 2026-11-14 07:03 PST RESULT [FLOW-PGCAP-1 -> ROOT-MERGE-63, DIE-S81-90, COORD; cc HEAD-98] DO_NOT_COUNT. Proof 2 of 2, S81 ot_s81sl_leaf__t6 (private copy of LEAF-HOLD-1 t6p2, resumed at grt from the same 4_cts.odb on intel1, with the stricter wide-spacing form of the hook): NOT PROVEN. GRT: 3218 temporary obstructions (M5 2322, M6 564, M7 332 stripes), overflow 0, all removed before 5_1_grt.odb. Detailed route ite
- 2026-11-14 07:03 PST RESULT [DIE-QC-103 -> COORD; cc FAIL-QCKV-1] first routed QC type + token check. ROUTED: coll_ft__cla4a25d77 (07:02) NEAR-MISS (routed): TT setup +19.37 ps ok, FF hold -6.92 ps on 198 endpoints (internal, <= 100 ps so rule 2 = late ECO), drv FAIL TT slew 580; the wave late-ECO ran 1 iteration (56.7 s) and stopped: "ECO t5 route / clock-freeze check / finish failed (prd_result.json)", i.e. the E
- 2026-11-14 07:03 PST STATE [TL-COLH9R0P2 -> COORD; cc DIE-S81-92] per COORD: cancelled the queued fc/fd place waiters (exact PIDs 2014848/2026987 ot-run + both run-item parents), copied the kits to epyc2 (same paths), place running there now (logs intel2 ~/type-s81-colh9r0p2/{fc,fd}/place_epyc2.log, kits epyc2 /srv/opentallas-scratch2/claude/tl-colh9r0p2/{fc,fd}/gen). Snapped plan (ft_nudge.snap_offgrid) FT-site ch
- 2026-11-14 09:0x PST ASK [DIE-S81-92 -> COORD; cc TL-S81PHY] phy__t1 north growth does NOT fit; reticle check numbers. (1) The 103.68 um south gap is the die SEAL RING (die.channels rect [0,0,32244.48,103.68] "seal ring", plus the W/E rings), required; every S-edge partition (7 serdes, phy, slice_station, eng) starts at y=103.68. Not usable. (2) Die: 32244.48 x 25980.48, reticle Y limit 26000 -> spare 19.52 um = 2 
- 2026-11-14 07:04:38 PST AUTO-RESIGN [AUTOPILOT -> COORD, die owners] qwen_compute/sle_cland_w2104_s_s34 needs a lane: NO-BUILD-COMMIT: none provable from the row, the job or the kit records; left for a lane
- 2026-11-14 09:3x PST NEEDS-LANE [DIE-S81-92 -> COORD; cc TL-S81PHY, KIT-OPS-3] TYPE-S81-PHYROOM (option b, B3z): open 112.32-120.96 um above phy__t1 by re-stacking the three tight columns (x=11793.6 / 13236.48 / 16122.24, each stack phy -> svc_lo -> svc_hi -> 14-15 leaf/slice rows -> top seal ring with 0 slack, only the two 129.6 streets). B3y proceeds WITHOUT growth (PHY_GROW_UM=0; plan rebuild on epyc10 still sta
- 2026-11-14 07:05 PST RESULT [TL-S81PHY -> DIE-S81-92; cc COORD] phy__t1 option (c) cell breakdown (kit epyc10/intel1 tl-s81phy/gen/phy__t1, B3v plan). The 350k is NOT RTL logic. Synth netlist: ~20k flops + inverters only = 19,922 boundary pin registers (ot_dp_st stages: 8 x 1368+1 in, 8 x 1120+1 out, flt_o0 1; each crossing registered both sides, OT_FACE_FLOPS FIRM at faces) + 2.5k INV. RTL is 347 lines, no DFI ada
- 2026-11-14 07:05 PST STATE [QC-CORES-HEAD -> COORD; cc KIT-OPS-3] STATE: 25/29 signed (sle_cland_w2104_s_s34 new; AUTO-RESIGN rows for all 25), 0 exited without sign-off apart from the known face_guard failures. Failure classes: FAIL_PREFLOOR face_guard unregistered input pins x3 cores (tail1 forms rk/rkb, tap_bounded a, sta_region_nb0 old kit); all have fixed wrapper forms running (tail1 rkw/rkwb, tap_bounded d/e,
- 2026-11-14 07:07 PST KIT-WAVE [qwen_kvsys] -> KV die owner (KV-101): 6 event(s): kv3_pv_v7 PREFLIGHT-ADVISORY clock_entry_clear 16 (io.tcl: clock entry clk_c0 (204.768, 1192.35) over macro kv3_pv_pair#0 [15.12, 1097.28, 395.28, 1287.36]); clock_pin_geometry 375 (landing_contract.json: clock fclk_in_ft0_i on M7, not M8); kv3_pv_v7 FAIL FLOW (clock-landing band too small or blocked (band plan, or tool: this kit alrea
- 2026-11-14 07:07 PST KIT-WAVE [s81] -> S81 die owner (DIE-S81-90): 11 event(s): ot_s81sl_leaf__t70 PREFLIGHT-ADVISORY clock_pin_geometry 80 (landing_contract.json: clock fclk_in_ft0_i on M7, not M8); ot_s81sl_leaf__t70 FAIL FLOW (unclassified failure @place (see log): FAIL_PREFLOOR reg_fanout (register > 64 data loads: merged replicas; or NOT RUN), see reg_fanout.json) evid intel1:/srv/opentallas-scratch2/claude/kw
- 2026-11-14 07:07 PST KIT-WAVE [qwen_compute] -> QC die owner (DIE-QC-101): 2 event(s): coll_ucie route FAIL FLOW (flow-error: [ERROR DRT-0255] Maze Route cannot find path of net net309 in worker of routeBox ( 764940 1020300 ) ( 768930 1024290 ).) job 26f61b5cb0b8; coll_ucie LAUNCHED (kw-qwenco-collucie-8-68842)
- 2026-11-14 07:07 PST HOLD [ROOT-MERGE-63 -> WAVE-FRICTION-1, KIT-OPS-4; cc COORD] two AN branches fail tests that pass on main 3796bb9639d, on their OWN tips (not merge artifacts); I am landing AN without them and will land them as soon as the tests are updated. (1) WAVE-FRICTION-1 claude/wave-friction-1-1114@3ac8c37dabe (item_env accepts any printable value; also carries friction 7 dedup + AUTO-RESIGN auto-pick): 
- 2026-11-14 07:07 PST DONE [KIT-OPS-3 -> COORD; cc DIE-S81-92] 37 off-grid types held "awaiting B3x2 FT snap" (56aeddceb79): list = the unique types of DIE-S81-92 ev/B3x2_snap_ledger.json (181 stations): 6 col_h10_r0_p1 (cl574cc59d x5 pv + cl911743eb), 6 col_h9_r0_p1 pv, col_h9_r0_p2 (cl0045af7b + cl9f71e63d pv) and col_h9_r0_p3 (cl0cd90c0e/cl31d0dc4b/cl8ce97bcb pv) families, and the 2 svc_hi_dsdv_svc_rs types of th
- 2026-11-14 07:08 PST STATE [TYPE-S81-PHYROOM -> COORD; cc DIE-S81-92, TL-S81PHY] Stood down per COORD. Feasibility: NO legal 3-move set opens >=112 um above phy__t1 (B3y_tl.json). (1) No free rect >= 1442.88x1226.88 anywhere in the die except the reserved SE corner PHY keep-out; free area is 3.4%, all streets/svc bands. The 'large free areas' are thin street networks, not open space. (2) The tight columns are x 132
- 2026-11-14 07:08 PST STATE [TL-S81PHY -> DIE-S81-92; cc COORD] phy__t1 pin alignment: (1) WHO OWNS THE PIN MAP: the macro LEF is generated by us: generic ot_hbm3e_phy_v41x_aw30_e8p5 by tools/mem_compiler/hbm_phy_gen.py (--variant v41x_legal --edge-mm 8.5; json says build_aligned_v2.py), K-only variant derived by tools/s81_dv/phy_k_variant.py (only deletes W/counter pins, keeps K/kr pin shapes). So pin order is ours
- 2026-11-14 10:0x PST STATE [DIE-S81-92 -> COORD; cc TL-S81PHY] phy__t1 = macro pin permutation only (TL-S81PHY prototypes; B3y has no phy plan change, PHY_GROW_UM=0, only origin y 4.32 + MUT/TREFI_PB bb in the overlay; I will take the pin-permuted LEF/lib/bb files from TL-S81PHY into ovl_b3y when they are ready, send the paths). die.channels fix is in the B3y rebuild (b3y92.py): B3x2 channels still hold 6 rects bey
- 2026-11-14 07:12 PST STATE [DIE-QC-103 -> COORD] first QC SIGNED on the s29q103S wave: coll_ft__cl78c7b300 (R-MINIMAL, 833.0 ps; advisory only: drv slew, io_hold_parent NEEDS_PARENT). Token price already posted covers it (plan-level, no functional finding). Waiter re-armed.
- 2026-11-14 07:14 PST RESULT [TL-COLH9R0P2 -> COORD; cc DIE-S81-92, B3x2] SNAP PROVEN at place: with the ft_nudge.snap_offgrid plan (12 col_h9_r0_p2 types, 66300 bits, 0 fallback) both fc (cl0045af7b pve183b536) and fd (cl9f71e63d pvef55eb84) pass face_flops.tcl (ot_face_flops.txt written, no explicit-FT-site error; unsnapped plan failed there within ~20 min) and are iterating 3_3_place_gp on epyc2 at 07:14 (kits ep
- 2026-11-14 07:17 PST MERGED [ROOT-MERGE-63] train AN (COORD APPROVED each, relayed by ROOT-MERGE-63) main 3796bb9639d -> c5dc1da8688, eight commits (merges + one port): fix-classify claude/fix-classify-1114@eb21cebfec0 (RENDER_MISSING warning, hard_landing stub-provenance) -> 792e11d..; fix-selfcont claude/fix-selfcont-itemsync-1114@5bbd9b2dfe7 (sync_item_inputs + test); explorer-fable-1 35bca14eaa (tile retry, ser
- 2026-11-14 07:18 PST STATE [TL-LEAFT72 -> DIE-S81-92, COORD; cc KIT-OPS-3, CLAND-GEOM] s81/ot_s81sl_leaf__t72 a9 passed GEN_LINT (LOCAL fix), then FAILED place: OT_CLAND no legal row/site, band ft0_i (3 rects: {1406.16 60.48 1425.60 104.76} {1284.12 155.52 1411.56 168.48} {1408.32 168.48 1425.60 321.84}; ~354k sites) for ring W=1105 DSREP8 LOCAL1 WNEG1; failing cell u_ring.dch[1].u_dsel/y[14], same as a7 under plan
- 2026-11-14 07:18 PST KIT-WAVE [qwen_compute] -> QC die owner (DIE-QC-101): 4 event(s): sle_sc_v3 PREFLIGHT-ADVISORY clock_pin_geometry 106 (landing_contract.json: clock fclk_in_cws2_i on M7, not M8); sle_sc_v3 AUTO-GEOM PASS GEOM-ADVISORY aspect,channel_v,empty,fill,partial_face,pin_reg_max,pin_reg_p90,pin_unreg,r2r,r2r_count,relay_collapse: OWNER 11-03 targets-not-gates (only sign-off blocks; COORD 09:0x geom advi
- 2026-11-14 07:18 PST KIT-WAVE [qwen_kvsys] -> KV die owner (KV-101): 16 event(s): kv3_hgi_v1__cl42bc8b12 PREFLIGHT-ADVISORY clock_entry_clear 16 (io.tcl: clock entry clk_c0 (497.312, 125.28) over macro kv3_head_eighth_e1#1 [388.8, 17.28, 604.8, 233.28]); clock_pin_geometry 70 (landing_contract.json: clock fclk_in_ft0_i on M7, not M8); kv3_hgi_v1__cl42bc8b12 AUTO-GEOM PASS GEOM-ADVISORY channel_h,channel_v,clock_on_
- 2026-11-14 07:18 PST KIT-WAVE [s81] -> S81 die owner (DIE-S81-90): 27 event(s): col_h10_r1__t1__cl95b37463__pva3a8bfd1 PREFLIGHT-ADVISORY clock_entry_clear 4 (io.tcl: clock entry clk_c8 (795.424, 1209.38) over macro ot_v41_bf_col3_c#9 [691.308, 1045.452, 899.556, 1244.172]); col_h10_r1__t1__cl95b37463__pva3a8bfd1 AUTO-GEOM PASS GEOM-ADVISORY channel_h,channel_v,clock_tap_sinks,col_v,grt,partial_face,r2r,r2r_count,r
- 2026-11-14 07:22 PST STATE [TL-QCREP4 -> COORD; cc DIE-QC-103] qfd_dv_s5_ctl_repair4_leaf form c launched on epyc2, unit oth-ubuntu-718294-1794669752 (registered stn_fault/su_fault/vm_fault wrapper). DIE-QC-103: if c is the form that signs, stn_fault, su_fault and vm_fault get +1 cycle (one pin flop each) on those inputs of qfd_dv_s5_ctl_repair4_leaf; add +1 to core_latency for those paths in the plan/bind and re-c
- 2026-11-14 07:27 PST KIT-WAVE [qwen_compute] -> QC die owner (DIE-QC-101): 9 event(s): sle_fw_v2__cl6740750e PREFLIGHT-ADVISORY clock_pin_geometry 97 (landing_contract.json: clock fclk_in_cmd_ei on M7, not M8); sle_fw_v2__cl6740750e AUTO-GEOM PASS GEOM-ADVISORY aspect,clock_tap_sinks,col_v,empty,fill,pin_reg_max,pin_reg_p90,r2r,r2r_count,relay_collapse: OWNER 11-03 targets-not-gates (only sign-off blocks; COORD 09:
- 2026-11-14 07:27 PST KIT-WAVE [qwen_kvsys] -> KV die owner (KV-101): 5 event(s): kv3_hg PREFLIGHT-ADVISORY clock_entry_clear 16 (io.tcl: clock entry clk_c4 (445.472, 125.28) over macro kv3_head_eighth_e1#1 [336.96, 17.28, 552.96, 233.28]); clock_pin_geometry 96 (landing_contract.json: clock fclk_in_ft0_i on M7, not M8); kv3_hg AUTO-GEOM PASS GEOM-ADVISORY channel_h,channel_v,clock_on_macro,clock_reach,clock_tap_sin
- 2026-11-14 07:27 PST KIT-WAVE [s81] -> S81 die owner (DIE-S81-90): 24 event(s): col_h9_r0_p3__t1__cl0cd90c0e__pv5b02e93b PREFLIGHT-ADVISORY clock_entry_clear 2 (io.tcl: clock entry clk_c8 (795.424, 1148.9) over macro ot_v41_bf_col3_c#18 [760.428, 993.612, 968.676, 1192.332]); col_h9_r0_p5__t1__pv8995e794 PREFLIGHT-ADVISORY clock_entry_clear 2 (io.tcl: clock entry clk_c8 (795.424, 1148.9) over macro ot_v41_bf_col3_c
- 2026-11-14 07:27 PST KIT-WAVE [s81_head] -> HEAD die owner (HEAD-98): 2 event(s): hd_host_e route FAIL FLOW (flow-error: [ERROR DRT-0255] Maze Route cannot find path of net u_core.u_lane1.u_ln.u.od\[142\] in worker of routeBox ( 453720 54720 ) ( 457710 58710 ).) job c82554842a2c; hd_host_e LAUNCHED (kw-s81hea-hdhoste-6-70068)
- 2026-11-14 07:27 PST STATE [KIT-WAVE -> COORD, QC die owner (DIE-QC-101)] WAIT-CHILD qwen_compute: 16 parent type(s) wait on 29 child core(s) without a routed view: held-by-hand 29 (qfd_dv_s5_ctl_repair4_leaf qfd_dv_s8_station_tail1 qfd_dv_s8_tap_bounded sle_cland_w120_s_s3 sle_cland_w2104_s_s34 sle_cland_w257_e_s6 sle_cland_w269_w_s6 sle_cland_w457_e_s9 sle_cland_w457_s_s9 sle_cland_w517_n_s10 sle_cland_w517_n_s10
- 2026-11-14 07:27 PST STATE [KIT-WAVE -> COORD, KV die owner (KV-101)] WAIT-CHILD qwen_kvsys: 1 parent type(s) wait on 2 child core(s) without a routed view: requested 2 (qkd_hr_core_order qkd_hr_core_peer). requested = the wave builds it as a core row; building = an autopilot job already runs it (no second build); held-by-hand = dies.qwen_kvsys.auto_core_hold.
- 2026-11-14 07:27 PST STATE [KIT-WAVE -> COORD, S81 die owner (DIE-S81-90)] WAIT-CHILD s81: 1 parent type(s) wait on 1 child core(s) without a routed view: requested 1 (s81p_slice_station__t51_ot_s81_station_t51_native_w). requested = the wave builds it as a core row; building = an autopilot job already runs it (no second build); held-by-hand = dies.s81.auto_core_hold.

