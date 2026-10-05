# Fixed-seed SKY130A extracted-slice mismatch campaign

**Result:** **PASS** (256/256 modeled samples passed)  
**Evidence class:** public open-PDK mismatch-model simulation of the archived capacitance-extracted local slice; not silicon  
**Operating point:** TT, 1.80 V, 25 C, 20 fF  
**Upstream PEX:** `cc4cfae726535e5a5aacda9444862d957b8adb775cde596a0d74b38f1764ff5b`

## Observed distributions

The table reports linear-interpolated empirical quantiles across the fixed
seed set. It is a circuit-model sensitivity result, not a fitted probability
distribution or a production-yield estimate.

| Metric | Minimum | p01 | p50 | p99 | Maximum |
|---|---:|---:|---:|---:|---:|
| Selected programmed bitline / VDD | 5.27946e-08 | 7.05712e-08 | 2.00893e-07 | 5.1546e-07 | 6.29899e-07 |
| Via-absent bitline / VDD | 1.08933 | 1.08963 | 1.09193 | 1.09389 | 1.09425 |
| Masked programmed bitline / VDD | 0.948154 | 0.948443 | 0.952562 | 0.957757 | 0.959104 |
| Dynamic separation / VDD | 1.08933 | 1.08963 | 1.09193 | 1.09389 | 1.09424 |
| VDD/2 discharge delay (ns) | 0.0338868 | 0.034246 | 0.0354049 | 0.0367635 | 0.0374679 |
| 0-5 ns supply energy (fJ) | 65.8115 | 65.9368 | 66.1615 | 66.4357 | 66.5434 |
| 6-7 ns supply-current RMS (uA) | 0.00622632 | 0.00761175 | 0.111641 | 0.394348 | 0.4347 |

## Reproducibility and activation checks

- The contract deterministically derives 256 unique positive ngspice seeds; the ordered list digest is `4a0443637a8e2918432d05d13323cab3527bf2f74b23171d163fb1cae6448155`.
- A fresh ngspice process reloads the mismatch-enabled primitive models for every seed (`mc_mm_switch=1`, `mc_pr_switch=0`); each generated netlist carries `.option seed=<value>` before model expansion.
- The copied NFET/PFET model files contain 972 `MC_MM_SWITCH*AGAUSS` expressions in total.
- Same-seed replay: **PASS**, maximum absolute parsed-measure delta 0 SI units.
- Cross-seed variation: 256 distinct discharge-delay values and 210 distinct read-margin values.

All passing samples satisfy the same local functional thresholds used by
the deterministic extracted-PVT campaign. Zero failures in this finite
public-model set must not be described as 100% yield: the run omits random
defects, spatial/systematic variation, sense-amplifier offset, compact-array
parasitics, distributed resistance, IR/noise, aging, repair, and silicon
correlation.

## Claim boundary

- Establishes: deterministic fixed-seed sampling of the installed public SKY130A 1V8 per-instance mismatch equations at nominal TT conditions.
- Establishes: electrical sensitivity of the exact capacitance-extracted two-column demonstration slice to the mismatch model over the declared sample set.
- Establishes: same-seed replay reproducibility and observed cross-seed variation for the local extracted testbench.

- Does not establish: silicon yield, defect probability, process capability, confidence level, production failure rate, or sign-off Monte Carlo coverage.
- Does not establish: sense-amplifier offset or yield because the demonstration slice contains only its local static sense inverters.
- Does not establish: distributed wire resistance, compact-array behavior, full-row or full-column behavior, decoder or repair behavior, IR drop, noise, aging, electromigration, or simultaneous full-array activity.
- Does not establish: N7 or N4 density, bandwidth, delay, energy, leakage, yield, or cost.
- Does not establish: whole-wafer inference throughput or GPU speedup.
- Does not establish: target-foundry correlation, manufacturing sign-off, or silicon correlation.

No value in this report may be scaled from SKY130 into N7/N4 or used
to calculate a GPU speedup.

## Reproduction

```bash
python3 tools/run_sky130_extracted_mismatch.py
```

The contract, exact seed per sample, parsed measures, warnings, model-file
hashes, replay deltas, and tool identity are stored in
`results/spice/sky130_extracted_mismatch.json`.
