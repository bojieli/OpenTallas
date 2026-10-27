# FALLBACK-LAND — bottom-up landed partition seams (analysis only)

CODEX shared-generator owns this secondary lane; first concrete packet codex/shared-core-0733@5ecb35da4, updated1d2f06b42. Owner-approved analysis07:13; no rule, RTL, calendar or physical-build change. Results: results/fallback_land_0733/README.md and per-die JSON.

All explicit plan-partition seam capacities counted, endpoints resolved: QC377parts/2993ports/1,277,486bits; S81398/2368/1,122,900; HEAD326/428/212,622; KV160/3915/599,111; HBM88/865/585,088. QC/S81/KV/HBM are current owner-provided candidates, HEAD is routing-held mainb7232fde4 baseline, never a final adopted clock-plan claim. These are nominal port capacities, not occupied native bit counts or undeclared hard-core cuts. KV actual B44 reports2545occupiedbuses/430554bits versus nominal599111; packing/forwarders/dead/overreserved capacity explains the different domains.

Gross +2/+3 simple-pipeline FF-envelope scenarios are recorded for all5dies, explicitly not net area and not actual ot_dp_clk_landing rings. Actual DEPTH4+RDREG1 ring storage is5liveFF/bit plus epoch/control/padding. Known65QCcut candidate actual-width flattened canonical inventory:65data+5monitor rings,86320FF, conservative1,470,882logicaladdedcells including reset/collector; mapped areaUNMAPPED. Actual-width stats/cell estimates come from QC one-event owner packet, not a generic 2/3FF substitution.

Minimum actual QC edge ledger completed: all65cuts join current88collector/local_sources and76nativev7consumer rows. Selected514-bit cut sl_E3_fe__l9_eo_l9_wi__3 atsl_E2_fe/u_cland_l9_eo_l9_wi_i reaches dvs_E2.u_core.u_sub.u_fdn.l9_i[0:513] fromdvs_E3...u_fup.l9_o, asbuilt2/landed16. Existing prepared nativev7 composer viaot-runintel2 unit185348: baseline296341cycles/token; +2onthisonecut296413(+72),4050.0tok/s; +3=296449(+108),4049.5. Conditional actual one-edge semantic price, not all-seam graph price or adopted physical/R8 implementation.

Remaining: expand actual occupied seam/member-to-programme joins before pricing global counterfactuals; QC CB16 DAG/R8 phase propagation, KV B44 exactcompiler depth_map/attention calendar, current S81/HEAD operation graph. HBM accepted B1operation→record/lane map absent and already OWNER?logged by FLOW. All unmapped global token rows remain explicitly UNPRICED; station totals are not cycle prices. Shared core-clock repair retains higher priority per COORD.

PARKED on explicit Claude reset recall. Final shared branch cb4bde4fc, cleanWT; no active own jobs. Five-die nominal census, exact one-edgeQC composer price and actual65-cut ring inventory safely pushed. No all-seam global adoption/price claim. Claude/root resumes remaining programme joins from the handback; CODEX launches stopped.

## [CLAUDE FALLBACK-LAND 2026-10-26 11:19 PDT] Five-die all-seam fallback price — ANALYSIS ONLY, every number UNCHECKED

Fallback = per-partition clocks + LANDED crossing (+K cycles, K=2/3) at every partition seam; no FT routing (a lane landing once per crossed face); no island drivers. Existing token tools re-run unchanged, lane latencies +K per crossing. Evidence: claude/fallback-land-1026@9689d9fc7 results/fallback_land_1026/ (README + run_s81_kv_hbm.sh + copied QC intel2 outputs). Seam inventory is Codex's census (cb4bde4fc).

| Die | Seams on token-critical path | Added cycles / layer (K=2 / K=3) | Landing area, ring basis 5.4 FF/bit (gross 2-3 FF) | tok/s vs current price |
|---|---|---|---|---|
| QC | ~388 per layer x 36 | +776 / +1,176 (FE-land +960 / +1,360) | 5.95 mm² = 0.73 % (0.97-1.45) | 4,051 -> 3,702 (-8.6 %) / 3,545 (-12.5 %); FE-land -10.4 / -14.2 % |
| KV | 22-48 per attention request | +44..96 / +66..144 | 2.79 mm² nominal, 2.00 occupied = 0.9 / 0.7 % (0.45-0.68) | Qwen pair QC+KV: -9.1..-9.6 % / -13.1..-13.8 % (upper bound -15.4 %) |
| S81 | ~450 face crossings per layer x 40 (214 if FT kept) | AR +900 / +1,351 | 5.23 mm² = 0.66 % (0.85-1.28) | AR 784.9 -> 766.8 (-2.3 %) / 758.1 (-3.4 %); MTP 2,749.3 -> 2,690.5 / 2,662.0 (-2.1 / -3.2 %), LOWER BOUND |
| HEAD | ~30-58 per lm_head pass, once a token | +60..174 per token | 1.0-1.6 mm² = 0.3-0.5 % (0.16-0.24) | < 0.02 % AR, <~0.1 % MTP (graph estimate, not composed) |
| HBM (note) | 8-14 per S2 record (graph radius 7 / diameter 14) | +16..42 per record | 2.72 mm² ~0.3 % (0.44-0.67) | DS AR -5.7..-13.8 %, Qwen AR -1.3..-3.2 % (no op->lane map; assumption) |

Sources:
- QC: intel2 fallback-land-1026/qc nativev7 composer (plan 54a1aeb5, 2,987 ports +K each; QC ports already one per face, so this is the no-FT case). Base 296,341 cycles -> 324,277 (K=2) / 338,677 (K=3).
- S81: compose_tok_ds.py --lat with every lane +K x faces. Main ac2ad01a8 base reproduced at 784.9 / 2,749.3.
- KV: kv_v39r_price.py lane deltas K x faces; the range runs from the priced bundles to + one interior pass.
- HBM: accepted_cost r25gq --op '*' --op-delta.

Area is a logical, UNMAPPED bound. It does not include 88-398 per-partition CTS roots, forwarded-clock wires or epoch/reset control.

Conclusion (UNCHECKED):
1. The fallback is cheap in area (<1 % of each die, about 0.3-6 mm²). It is expensive in latency wherever the token path crosses many partitions serially.
2. The Qwen pair loses about 9-10 % at K=2 and 13-15 % at K=3. Added to its 1.47 % accepted plus 7.12 % proposed ledger, K=3 would break the 15 % design cap and K=2 would sit at the edge.
3. S81 (DS ROM) loses only 2-3.5 % on AR and MTP. That is a lower bound, because the field records keep old embedded wires. With the 9.85 % ledger, S81 lands at about 12-13.3 %, inside the cap.
4. HEAD is negligible. HBM is the worst after QC if each S2 record crosses about 14 seams (DS AR up to -14 %), but it has no op->lane join yet.
5. Recommendation: the fallback is viable for S81/HEAD/KV and is a last resort for QC/HBM. On QC, about 85 % of the cost is the serial slice-crossing chain (796 -> 1,372 cycles per layer at K=2) and the CB16 path (16 -> 38 per matvec). A QC fallback would need coarser clock domains (one per slice, not per partition) to stay inside the cap.

## [FALLBACK-KV 2026-10-26 17:02 PDT] KV 8-region landed fallback — plan + tool + gate on existing g32x64 runs; every number UNCHECKED
Branch claude/fallback-kv-1026@c83da6c6fe (tools/die_plan/fallback_land.py plan|gate; results/fallback_kv_1026/README.md). The classes are structural: region boxes from spec_c3, partition type, bus role. None is chosen from slacks.
(1) PLAN. Land 662 region-crossing ports (77,938 b, = die_clock_mesh landed_crossings, 0 mismatch) + 346 PHY ports (80,026 b, kv3_phy* regional regs) + 190 reset/start wavefront hops (boot only). 2,907 ports (441,147 b) stay related pairs under one region tree. Cost: per attention request +16 (K=2) / +24 (K=3, as-built ring +3) cycles, embed +20/+30. KV tok/s (kv_v39r_price, 4,810.9 base): K=2 -0.24 % priced / -0.44 % upper; K=3 -0.36 / -0.66 %; with PHY hops -0.50 / -0.74 % upper. The Qwen ledger becomes 8.59 + 0.74 = 9.3 % < 15 %: NO cap break. Cheaper than the all-seam -9..-10 % because QC stays on the master plan.
Correction to the brief: of the 2,280 FF-failing seams, only 406 cross regions (they hold the worst, -278.5). 1,874 are same-region (worst -95.3) and fail on the 40-ps stand-in contract at skew <=40.
(2/3) GATE on the g32x64 die_sta runs (stand-ins). Landed window PASS: TT damage 390.4 vs 416.7 = margin 26.3; FF 323.6 = margin 93.1 (die_sta_related clock-kv-r1 base_g32x64_rel). Related-pair TT setup +545.4. FF hold -57.8 at BHOLD 40; at the plan W=80 contract (MODEL-SHIFT +40) it is -17.8 on 5 seams: pc_WS_6->pc_WS_5 x3 and pv_N_1->pv_N_0 x2, both same-region neighbours on different subtrees. Intra-partition: NOT RUN. Tap spread FF is >80 ps in 11 partitions (sys_c 157, hub_C 136, pv_S_4..7 ~105, pc_EN_1 109), and landing cannot fix that. => FAIL today. The fallback removes the cross-region problem but not the intra-region/intra-partition tree spread or the stand-in views.
LIVE (do not duplicate): epyc1 /srv/opentallas-scratch2/claude/fallback-kv-1026/sta_w80_{FF,TT} (W=80 stand-ins, --intra-pairs 200, scopes oth-ubuntu-3597816/3597819-1793059126, started 16:58, ~1-1.5 h). Collect die_sta.json, then run fallback_land.py gate --run-bhold-ps 80 (command in README).
NEXT, for whoever owns the KV GEN: (a) GEN = B48 codex/kv-land-1026 region landings (same 8 boxes) + the 346 PHY landings through clock_landing_plan compose (kv-land-adapter, ROOT-MERGE HOLD). Every receiving type changes kit, so re-GRT is needed for the fclk pins. (b) The 5 residual seams + 11 wide partitions need per-partition single-root CTS or the 12.8 sites (CLOCK-KV-R2). (c) Real signed views replace the stand-ins before any freeze claim.
2026-10-26 17:04 PDT GEOM-REVIEW-7 -> FALLBACK-KV: regions render (a) PASS: 662/662 landed ports cross exactly one region cut between abutting parts, 0 unlanded cross-region ports (CHECKED vs plan); (b) PASS: both blue pairs same-region, abutting, different subtrees -> align subtree split or land the 2 lanes (no padding); (c) PASS: 0/160 parts straddle a cut (CHECKED). Details lanes/GEOM-REVIEW.md.

## [FALLBACK-HEAD 2026-10-26 17:16 PDT] s81_head landed fallback: plan + tools + die GRT incl. clock + landing window. Every number is UNCHECKED; NUMBER-CHECK please.

Branch claude/fallback-head-1026@bd084a517d (main 63f0898a3 + tools/s81_head/fallback_land{,_report}.py, test_fallback_land.py, die_trial --htree-full-depth opt-in, clock_landing_plan buses fix). Results: results/fallback_head_1026/README.md.

**Plan.**
- Regions = 326 partitions, one die clock entry each. hd_serdes entry moved to the digital strip, out of VDDPHY.
- 428 landed crossings / 212,622 bits, +3 cycles each (proved ot_dp_clk_landing contract). clock_landings.requirements: 16 -> 16 types (0 splits), 1,712 scalar pins, 1.07 M live ring FF, ring area 0.99 mm² (0.32 %, UNMAPPED).
- Cores reused as-is: 1,320 elemA/elemB cv views, fed by the hd_tile-local tree.
- Head pass: 37 serial crossings + 2 x 10 all-gather = +171 cycles. TOK-DS (compose_tok_ds 63f0898a3): AR 784.9 -> 784.81 (-0.011 %), MTP 2,749.3 -> 2,747.75 (-0.056 %, 6 head passes on the critical path).

**Die GRT incl. clock.** Combined global_route: signals M4-M7 adj 0.75 + die ctree M8-M9 adj 0.4, 50 congestion iterations, TT+FF.
- FB1 fd300 (`--htree-full-depth --leaf-um 300`): overflow 0 on every layer, 0 GRT-0113/0114.
- Entry slew max 96.7 ps. Insertion TT 5,816-5,995 / FF 5,035-5,195.
- Landed phase |d| max 89.3 TT / 80.1 FF vs P/2 = 416.5 budget: PASS, margin 327 ps (~5.5 % of insertion = the OCV allowance on the unshared tree, UNCHECKED). Drift TT->FF 9.2 ps.
- The default die_trial tree (leaf600) FAILS 444.4 ps on 4 corner serdes<->frame crossings. Root cause: single-tap regions stopped bisecting, giving unrepeated legs (slew 786) and unequal depth (spread 649). That run's data is deleted; its report is kept.
- Run dir: epyc1:/srv/opentallas-scratch2/claude/fallback-head-1026/fd300. Render viewed: fd300/fb1_fd300.png.

**Not done (12.4a gate still open):**
- Die STA on real views needs the 16 types rebuilt with rings/fclk/monitor and signed off, ring-window STA, and die_sta --spine-tree fd300.
- clock_landing_plan.compose run 1 FAILED on KeyError 'buses' (fixed on this branch). The rerun is live: epyc1:/srv/opentallas-scratch2/claude/fallback-head-1026/compose2/{compose_report.json,landed_plan.json}, log compose2.log, ~15 min.
- hd_ctl observer fault/ready ports are OPEN.

HEAD-CORE-LAT-R4 is untouched: the fallback uses the existing cv cores and does not depend on R4.
2026-10-26 17:19 PDT GEOM-REVIEW-7 -> FALLBACK-HEAD/COORD: [FB1-FD300] entries PASS (hd_tile tap in the 36.6-um eA2/eA3 channel, serdes tap in the core-VDD strip 72 um outside VDDPHY; CHECKED); die tree FAIL STRUCTURAL on sites: 1002/1663 tree buffers on hard cores (240/326 leaf bufs), 24 in VDDPHY, 9 outside partitions (CHECKED vs fb1_plan) -> snap bisection to the tile channel grid (same tile-relative crossing per level), leaf buf at the entry channel site, no cells/corners in VDDPHY, add site-legality to the gate; GRT0 does not cover cell legality. Details lanes/GEOM-REVIEW.md.
- [FALLBACK-HEAD 2026-10-26 17:29 PDT] COORD amend 17:21 done. claude/fallback-head-1026@a10b1bbea2: die_trial --tree-site-legal re-sites every tree cell to channels; fs300 = 2,311 cells, 0 on core / 0 in PHY / 0 outside. Combined die GRT 50 it overflow 0 TT+FF. Landed |d| 311.9 TT / 272.8 FF vs 416.5: PASS, but the margin is only 105 ps (UNCHECKED). The greedy snap broke equal length: spread 607, worst at spine sp2<->sp3. NOT robust against OCV on a ~6 ns unshared tree. Next structural step: channel-grid symmetric bisection (GEOM-7 item 1) + a common spine-column node for the sp2/sp3 seam, predicted before build. Ring rebuilds must reserve the push-down tree sites (fs300/tree.json `sites`). GEOM REQ FB1-FS300 filed. compose2 is still running; I will collect it.
