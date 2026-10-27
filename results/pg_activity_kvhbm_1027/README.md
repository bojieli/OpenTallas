# PG-ACTIVITY-KVHBM (2026-10-27): KV + HBM PG on measured activity, 150-um bumps, 70-um pads

Basis: HEAD-5 pad model (bs_psm / infra_pg.window_kit pad_um, src = claude/infra-head5-1027 tools), PDNSim VDD+VSS,
metric = co-located VDD drop + VSS bounce, interior >= 450 um from open window edges; grid G12 = M8 0.48@4.32 / M9 12.96@34.56;
H8 = M8 0.96@4.32 / same M9. Gate 35 mV. Plans: KV main qwen_kvsys; HBM main hbm_arch/B2r2 (the current unified c11b plan is unadopted).
PDNSim numbers = this lane's run outputs (pad_fallback 0, PG_CHECK OK both nets, EXIT 0). Power basis = UNCHECKED.

## Activity (task 1; HEAD-4 method: Verilator VCD -> per-bit toggle -> OpenSTA report_power with regs/inputs annotated)
* KV: head_eighth_e1 (tb_qkh_head_r4_s, 1648 cycles, $random K data) measured 0.1168 W vs vectorless 0.2015 (x0.580);
  pv_pair (tb_qwen_tp8_pv_wide_pair cols 0-1, active window 218 cycles) 0.1050 vs 0.2020 (x0.520; 42% regs unmatched -> matched mean).
  Types: kv3_hg 2.054 -> 1.191, kv3_hgi 1.971 -> 1.143, kv3_pv 1.257 -> 0.654 W/mm2. Other head eighths use the e1 ratio, other types 0.55 (UNCHECKED-ESTIMATE).
* HBM: SM bench tb_hgi_sm_e2e --ds still running (build >30 min); the SM rects of the 10-24 map (2.1787) = 16 x hnx_rp3lp3h S+N halves.
  On the real half odbs (3_place, + CTS factor 1.189 from BDC): vectorless 0.755, FLAT 0.5 1.366 W/mm2 (0.63x the old 2.18).
  Measured will lie between; the PDNSim gate uses FLAT 0.5 as the upper bound. Non-SM blocks keep their 10-24 values.

## PDNSim, 150 um / 70-um pads (task 2), mV
| die | window W/mm2 | above M7 interior | below M7 | total | verdict |
|---|---|---|---|---|---|
| KV old (vectorless) | 1.818 | 37.6 | - | - | FAIL (survey) |
| KV measured | 1.050 | 21.8 | 6.05 (e1 slice, PDNSim-charged 0.182 W; 3.88 scaled to measured) | 27.9 | PASS |
| HBM old (10-24 map) | 2.179 | 39.8 | - | - | FAIL (survey) |
| HBM SM flat 0.5 (upper) | 1.366 | 25.0 | 5.13 (HEAD-5 slice, UNCHECKED-ESTIMATE: no SM final odb) | 30.1 | PASS |
| HBM SM vectorless (lower) | 0.755 | 13.8 | | | |
Linear-scaling cross-check: KV 37.59 x 9.276/16.063 W = 21.7 vs PDNSim 21.8.

## HBM die-edge strip (task 3)
Centred lattice leaves the first column 147.12 um from the W/E die edge. EDGE-FILL lattice (tools/pg_activity/pg_meas_psm.py
--edge-margin 60: n = floor((L-120)/150)+1, centred, pitch 150 kept) = 168 columns, first column 72.12 um from the edge (pad edge 37 um).
Old map: die-edge band 112.3 -> 38.5 (edge inner 39.5, = interior). Flat-0.5 map: edge band 24.2 / inner 24.7 / interior 25.0.
Render hbm_edge_lattice.png (viewed). KV: edge windows are cold (0.23 W/mm2), no edge issue.

## Denser M8 H8 (task 4), old maps, 96 GB
KV 37.6 -> 28.4; HBM 39.8 -> 30.6. Costs M8 PG 29% -> 88% tracks: not needed once activity is measured. KV H8 on the measured map is still running.
