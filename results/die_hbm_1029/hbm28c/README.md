# DIE-HBM-28-C (2026-10-29): token price of the HBM scorer row-1 feed hop chain (HBM-004 V-R1 + HBM-055 residual)

Model: SAME ds S2 schedule model as TOK-HBM-11 tok_hbm11.py / DIE-HBM-10 tok_rerun_c22.py (accepted_cost g25 rank0,
NativeCost, T.schedule). IDX cycles added serially to every IDX record (48/token), as DIE-HBM-10 added IDX +17.
Base 576,702.4 cyc = 1906 (guarded); TOK-HBM-11 A+B op-aware reproduced 5.163 % = 1812.4 tok/s (CHECKED).

| case | cost vs 1906 | tok/s | delta vs 1812.4 |
|---|---|---|---|
| IDX +30 alone | 0.250 % | 1901.3 | - |
| A+B + IDX +22 | 5.346 % | 1809.3 | -0.174 % |
| A+B + IDX +30 (estimate of record: feed chain ~28 st) | 5.412 % | 1808.1 | -0.237 % |
| A+B + IDX +32 (feed 30 + result return ~2) | 5.429 % | 1807.9 | -0.253 % |
| A+B + IDX +34 | 5.446 % | 1807.6 | -0.269 % |
| A+B + IDX +60 (bound) | 5.662 % | 1803.9 | -0.475 % |

Exactly linear: 48 IDX records x N cycles, all on the critical path (no overlap in S2). Cycle counts (~28 stations,
~30 cyc over 11.2 mm) are plan arithmetic from HBM004_VR_ESTIMATE.md section 3 (ESTIMATE); model runs CHECKED.
Run: repo root, PYTHONPATH=src python3 tok_hbm28c.py OUT.json (~3 min, intel1). Sparse checkout needs tools/, src/,
results/arch/hgi_sim_20261010/, results/rtl/*.json, results/rtl/dshbm_*/, results/rtl/dsrom_1m_allmeasured_20261004/.
