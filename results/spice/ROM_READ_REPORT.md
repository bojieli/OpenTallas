# Governed SKY130 via-ROM read-path experiment

**Result:** **PASS** (51/51 cases passed)  
**Evidence class:** simulated open-PDK circuit proxy; not measured silicon  
**PDK pin:** SKY130 primitive library `v0.20.1` / commit `d717cd4d8d93cce6a8d7534f6a40432f0045039f`  
**Simulator:** `******`

## Outcome

The pinned BSIM campaign validates the via-present/via-absent NOR-ROM topology,
the transistor-level expert-wordline mask, and sense polarity over the declared
PVT and synthetic capacitive-load envelope. It does not characterize a ROM macro.
The `array_rows` dimension changes only the explicitly declared lumped bitline
capacitance; it is not extracted array geometry.

| Limiting metric | Observed case |
|---|---|
| Minimum dynamic bitline separation / VDD | 1.00629 V/V — case_043 (ff, 1.98 V, -40 C, 1024 rows, 5 fF port load) |
| Maximum VDD/2 discharge delay | 0.434705 ns — case_044 (ss, 1.62 V, 125 C, 1024 rows, 5 fF port load) |
| Maximum read-window supply energy | 320.689 fJ — case_049 (ff, 1.98 V, -40 C, 1024 rows, 80 fF port load) |
| Maximum inactive local-circuit leakage | 7.83555 uA — case_051 (tt, 1.80 V, 25 C, 1024 rows, 80 fF port load) |

The energy number covers the three matched bitlines, their static sense inverters,
the two wordline-mask paths, and output loads from time zero through the 5-ns
sample. Leakage is the same local circuit after the read pulse; neither quantity
is a per-bit macro number or a whole-wafer power estimate.

## Governed sweep

- Full 3 × 3 × 3 FF/TT/SS, 1.62/1.80/1.98-V, -40/25/125-C PVT sweep at 256 rows and 20-fF output load.
- 64/256/1,024-row × 5/20/80-fF output-load sweeps at nominal PVT, slow-low-hot, and fast-high-cold.
- Duplicate points are executed once, yielding 51 deterministic cases.
- Every case checks programmed discharge, absent-via retention, masked retention, normalized separation, sense polarity, delay, positive bounded energy, nonnegative bounded leakage, and zero warnings.

## What maps—and what does not

- Establishes: via-present versus via-absent NOR-ROM read topology.
- Establishes: transistor-level expert-wordline masking and static sense polarity.
- Establishes: deterministic sensitivity to the declared PVT and synthetic capacitive loads.
- Establishes: a reproducible open-PDK/ngspice circuit-methodology path.

- Does not establish: N7 or N4 ROM density, delay, energy, leakage, bandwidth, yield, or cost.
- Does not establish: full-array simultaneous-read current, IR drop, noise, or thermal feasibility.
- Does not establish: extracted decoder, wordline, bitline, sense-amplifier, repair, or port timing.
- Does not establish: statistical sense offset, mismatch yield, aging, electromigration, or silicon correlation.
- Does not establish: wafer-scale inference throughput or GPU speedup.

There is deliberately **no target-node scaling rule** in the contract. SKY130
cannot be converted to an N7 or N4 density, bandwidth, delay, or energy point
with a feature-size multiplier. Target studies remain blocked on characterized
N7/N4 ROM macros, extracted interconnect/sense paths, PVT/mismatch/aging data,
simultaneous-activity power integrity, test-chip correlation, and silicon.

## Reproduction and machine evidence

```bash
python3 spice/run_sky130_rom_read.py --fetch-pdk
```

The contract SHA-256 is `7600eee004331826a2b47e80bd57a40bc1c7cf32e53b61a5be364391270627f1` and the runner
SHA-256 is `2bda97a2a8ec49f358022353c894b10a616273e3654a0aa2e9c072e67d527e3c`. Exact case inputs, measures,
deck/log hashes, thresholds, PDK file hashes, and tool identity are in
`results/spice/sky130_rom_read.json`. Downloaded PDK files live only in the
ignored `.cache/` directory and are hash-checked before every run.
