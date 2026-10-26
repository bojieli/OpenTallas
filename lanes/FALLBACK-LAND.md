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
