# DIE-QC-4 (2026-10-28): QC clock-first, per-region DME fallback, rebuilt landing plan

All numbers are OWN runs and UNCHECKED (no independent NUMBER-CHECK yet). ASAP7, 833 ps.
Spice clock calibration is x1.0485 TT and x1.0552 FF. Die STA is main `die_sta_related` with
`--cppr-lca --clock-ocv table --clock-droop shared`.

## Flow
1. Plan: grp region map with the PHYs merged into their feed parents (`maps/regions_grpP.json`, 313 regions).
   - Merges: io_serdes->coll_n, io_serdes_1->coll_s, io_serdes_2->c_W5_bf_01, ucie_kv->glue.
   - `clock_landing_plan.compose` (`scripts/compose_qc.py`), then `gen.py latency`, gives
     `qc_grpP_event.json.gz` (sha in `qc_grpP_event.sha`).
   - G0C PASS: 0 errors, 160 warnings, 98/98 types clean (`g0c_report.json`).
   - The render `g0c_die_plan.png` was viewed: no G0 error marks.
2. Clock kit: `die_trial kit --tree-form link_htree --rep-um 250 --leaf-um 200 --tree-site-legal --tree-site-slide`
   plus the NEW opt-in `--region-dme delay --region-dme-only c_W5_bf_01` (commit fb85083883).
3. Clock-first GRT (`scripts/mk_clkfirst_qc.py`, `runC.sh`, `runSig.sh`):
   - Stage 1 routes the clock alone with NDR CK2W2S (M8/M9 w 0.08, s 0.32) for 50 iterations.
   - Stage 2 runs the kit signal GRT with the frozen clock guides as obstructions.
4. Die STA uses the scaled routed arrivals (`runS.sh` none/HB4). The CA chain is `runCA.sh`.

## Results
| run | tree | region max TT/FF (nominal x spice) | die STA intra skew TT/FF | seam skew TT/FF |
|---|---|---|---|---|
| stock (grp map, sliceclk plan) | stock link_htree | 122 / 106 | 135.39 / 117.43 | 38.64 / 34.85 |
| K1 (grpP, event plan) | stock link_htree | 246 / 207 (c_W5_bf_01+io_serdes_2) | 257.53 / 217.14 | 141.35 / 124.54 |
| P0d (grpP, all DME delay) | DME | 261 (sl_*_su_c) | - | - |
| **K2 (grpP, event plan)** | **htree + DME only c_W5_bf_01** | **122 / 106 (c_W5_bf_01 63 / 56)** | **135.39 / 117.43** | **52.58 / 42.65** |

K2 other measures:
- Die STA intra TT setup is +475.43.
- FF hold raw is -162.18. With HB4 it is 0, at a cost of 7.91M cells and TT setup +289.04.
- Seam HB4 needs 268k cells.
- GRT stage 1 (clock alone) has 0 overflow; 0.32 % usage; 8.01 m wire.
- GRT stage 2 (signal with frozen clock) has 0 overflow; 2.89 % usage.

## Landed and count-aligned crossings
- The landed TT -3174 / FF -4987 (K2) is an artefact. The plan's half-period window of 416.67 is applied
  to cross-region pairs that are count-aligned.
- CA plan (`ca_spice`): 2537 crossings, of which D4 2357 and D8 174.
  - 6 FAIL: ambiguous start-tree edges on c_E4_tf_11, c_W0_bf_11 and c_W0_tf_11 (ports a00/b12).
- INFO bind with those 6 dropped (it is never a gate number):
  - CA lag margin lo 121.7 TT / 116.8 FF; 0 slot or guard fails.
  - START-SKEW fails on 31/260 tree ports TT and 21/260 FF. For example, c_E4_bn_00__a22__0 has limit 21.9 against clk-q skew 55-87 ps.
- Blocker for the freeze gate: the CA start tree (ambiguous edges and start-skew). This belongs to the
  shared/MESO count-align planner, not to the clock tree.
