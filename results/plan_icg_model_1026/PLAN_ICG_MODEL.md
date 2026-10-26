# PLAN-ICG-MODEL 2026-10-26: plan latency through ICGs + CTS-open subtrees

Code: tools/die_plan/core_infra_plan.py (`icg_lib_cells`, `open_subtree`, `region_reach`, `gated_leaf_region`, `OPEN_SUBTREE_CAL`, `predict_tree` gated/cts_open leaves) and tools/die_plan/core_infra_sta.py (`emit_model` writes the real ICG master + one CTS root buffer per open domain; `combine_arrivals` adds the subtree model to the plan-STA arrival at that buffer).

## Model (plan-only, deterministic)
- ICG stage = liberty CLK->GCLK positive-unate rise arc (ASAP7 SEQ RVT NLDM) at the plan input slew and a load of one `BUFx24_ASAP7_75t_R` CTS root buffer next to the gate. Measured: TritonCTS put the subtree root buffer(s) next to the ICG (ICG -> mean first-level buffer Manhattan: qxpq median 1.1 um, 1,009/1,025 <= 3 um, max 26.9; bf_col median 2.2 um, 11/18 <= 3 um, max 61.0), and every first-level buffer below a qxpq ICG was BUFx24 (1,026/1,026).
- CTS-open subtree, measured from the root-buffer input pin: mean = stage_ps x k + region_ps_per_um x D; min = mean - lo x D; max = mean + hi x D. k = ceil(log24 N) (core_infra._cts_levels), D = Manhattan distance from the driver to the farthest corner of the leaf region (`region_rect_um`, else the gate `island_rect_um`, else the listed sinks' bbox for cts_open leaves; a gate with no region is refused).
- Coefficients (fitted once, weighted LS through the origin, each core = equal weight, 1,043 single-level gated domains):

| corner | stage_ps | region_ps_per_um | lo_ps_per_um | hi_ps_per_um |
|---|---|---|---|---|
| TT | 24.93 | 0.636 | 0.092 | 0.270 |
| FF | 19.06 | 0.518 | 0.086 | 0.239 |

## Data (CHECKED-BY-LANE: read from routed 6_final ODB + SPEF with OpenSTA, propagated clock, icg_measure.tcl; sha256 prefixes match the archive)
- S81 `ot_v41_rom_elem_q_qxpq_w10` closed_archive dsrom-qelem-qs5f-cpr-tc-hm25-cl-ffacf68cd (odb 3c54776d34f52311, spef e3bc7dc69572ed01): 53,111 clock sinks, 1,025 ICGx1 (root gate + 1,024 cg-pushdown clones of 37 sinks each), all-sink TT 481.8 (425.8-506.6) / FF 381.3 (337.3-399.5).
- S81 `ot_v41_bf_col` closed bfh_compact199_col_kreg_a1200_05a8d46ee-cl (odb 566cbef44a3e3e35, spef d4c438b9723cb2d1, restored from the frozen archive): 53,495 sinks, 18 ICGx1 (tile 16,213, lane 13,994, 16 x ~1,400), all-sink TT 564.6 (523.8-681.0) / FF 446.3 (413.7-548.0).
- Every ICG in both cores hangs from the CTS-grown root tree (no ICG below another ICG in the netlist), so every domain is single-level.

## Validation (ps; prediction starts from the MEASURED arrival/slew at each ICG CLK pin, because the upstream trees of these cores are CTS-grown, not plan-built)
Residual = predicted - measured. Domain stats = bias / max|res| / rms over domains. Core = sink-weighted mean over all gated sinks.

| corner | core | domains | gated sinks | meas mean | pred mean | core resid | domain in-sample | domain LOO | cross-core fit (other core only) | ICG stage resid | domain max resid |
|---|---|---|---|---|---|---|---|---|---|---|---|
| TT | qxpq_w10 | 1025 | 37,431 | 485.1 | 483.2 | -2.0 | -2.0/20.7/2.8 | - | -3.8/21.5/4.3 (core -3.8) | -1.1/46.0/1.8 | -0.4/45.4/3.0 |
| TT | bf_col | 18 | 52,679 | 565.0 | 550.6 | -14.4 | -3.0/54.0/15.7 | -3.3/66.9/18.5 | -40.3/143.4/51.9 (core -79.3) | -4.1/29.8/8.0 | +1.6/94.7/31.1 |
| FF | qxpq_w10 | 1025 | 37,431 | 383.6 | 382.5 | -1.1 | -1.1/16.6/1.8 | - | -1.7/16.9/2.3 (core -1.7) | -0.8/31.9/1.3 | +0.2/38.3/2.6 |
| FF | bf_col | 18 | 52,679 | 446.5 | 436.3 | -10.2 | -2.5/39.4/11.4 | -2.6/48.9/13.5 | -35.0/116.7/43.7 (core -66.4) | -3.0/20.9/5.7 | +1.3/73.1/24.7 |

## Limits (read before using a number)
- Expected band in the calibrated range (N 20-16k, D up to ~400 um): domain mean +-19 TT / +-14 FF rms (bf_col LOO), worst domain -67 TT. The worst domains are bf_col's two whole-core gates (tile 16k, lane 14k sinks, D ~305-313 um): CTS grew 9-11 levels there vs planned 4, i.e. balancing to the other gated paths, which a per-domain stage model cannot see. 12.8b structures (one gate level, equal-stage regions) avoid that; whole-core gated domains predicted by this model are UNDER-predicted (non-conservative) by up to ~50 TT.
- qxpq alone cannot calibrate the region term (all regions < ~50 um): the cross-core fit from qxpq only misses bf_col by -79 TT. The region coefficient comes from bf_col's 16 lane gates (D 53-305 um).
- These are routed-SPEF numbers of CTS-grown trees from the 10-12/10-20 flows; the region/stage constants carry that flow's CTS settings (fanout, buffer list). A 12.8 plan-built trunk above the gates is timed by the existing NLDM tree model (+ its MODEL-REFIT offset); only the open subtree uses these constants.
- Window: min/max per domain from lo/hi x D; max-resid rms 31 TT on bf_col (the deep balanced domains again).
- Files: icg_measure.tcl (probe), analyse.py (per-domain decomposition), fit.py (fit + validation), fit.json (coefficients + all residuals), fit_excl_wholecore.json (variant without the two whole-core gates: TT 26.01/0.577, bf_col core resid -24.1 -> not chosen), validation_points.json (2,086 domain points + liberty tables, used by test_validation_against_measured_gated_cores).
