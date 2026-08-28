# Capacitance-extracted SKY130A via-ROM PVT campaign

**Result:** **PASS** (33/33 cases passed)  
**Evidence class:** deterministic open-PDK PVT simulation of the archived capacitance-extracted slice; not silicon  
**Upstream PEX:** `cc4cfae726535e5a5aacda9444862d957b8adb775cde596a0d74b38f1764ff5b`  
**Simulator:** `** ngspice-36 : Circuit level simulation program`

## Results

| Limiting metric | Observed case |
|---|---|
| Minimum dynamic separation / VDD | 1.06375 V/V — case_012 (ff, 1.98 V, 125 C, 20 fF) |
| Maximum VDD/2 discharge delay | 0.0608871 ns — case_032 (ss, 1.62 V, 125 C, 80 fF) |
| Maximum 0–5 ns supply energy | 315.391 fJ — case_031 (ff, 1.98 V, -40 C, 80 fF) |
| Maximum 6–7 ns supply current | 5.28402 uA — case_032 (ss, 1.62 V, 125 C, 80 fF) |

The circuit instantiates two copies of the exact archived two-column PEX
slice. One copy has expert-enable high and validates programmed discharge
plus absent-via retention; the second has expert-enable low and validates
physical masking. The load sweep adds only the declared external output load.

## Governed sweep

- Full 3 × 3 × 3 SS/TT/FF, 1.62/1.80/1.98-V, -40/25/125-C PVT sweep at 20-fF output load.
- 5/20/80-fF output-load sweeps at nominal PVT, slow-low-hot, and fast-high-cold.
- Duplicate points run once, yielding 33 deterministic cases.
- Every case checks bitline state, normalized margin, sense polarity, delay, energy, nonnegative bounded current, and unexpected warnings.

## Claim boundary

- Establishes: electrical read behavior of the exact capacitance-extracted two-column SKY130A demonstration slice.
- Establishes: selected programmed discharge, absent-via retention, expert-enable masking, and static sense polarity over the declared deterministic PVT and output-load campaigns.
- Establishes: delay, supply-energy, and leakage sensitivity for two instantiated copies of this local demonstration slice.

- Does not establish: statistical mismatch yield or sense-amplifier offset.
- Does not establish: distributed wire-resistance, full-row, full-column, decoder, repair, IR-drop, noise, aging, electromigration, or simultaneous-read behavior.
- Does not establish: N7 or N4 density, bandwidth, delay, energy, leakage, yield, or cost.
- Does not establish: whole-wafer inference throughput or GPU speedup.
- Does not establish: silicon correlation or manufacturing sign-off.

This result cannot be scaled from SKY130 into N7/N4 performance or a GPU
speedup. Distributed wire resistance and statistical mismatch remain separate
open gates, followed by target-foundry macro correlation and silicon.

## Reproduction

```bash
python3 tools/run_sky130_extracted_pvt.py
```

Exact inputs, case measures, warnings, thresholds, and SHA-256 identities are
stored in `results/spice/sky130_extracted_pvt.json`.
