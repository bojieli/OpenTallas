# Capacitance-extracted IHP SG13G2 controlled-via ROM PVT campaign

**Status:** **PASS** (33/33 cases passed)  
**Evidence class:** deterministic simulation of archived IHP PEX with official PSP103 models; not silicon  
**Upstream PEX:** `9f5d3569091d8acfc0ee8429bebaffddd73b12d66ed3243e944344af08c0688f`  
**Simulator:** ngspice 43 with pinned OSDI modules

## Results

| Limiting metric | Observed case |
|---|---|
| Minimum dynamic separation / VDD | 1.06978 V/V — case_012 (ff, 1.32 V, 125 C, 20 fF) |
| Maximum VDD/2 discharge delay | 0.0652107 ns — case_032 (ss, 1.08 V, 125 C, 80 fF) |
| Maximum 0–5 ns supply energy | 142.238 fJ — case_031 (ff, 1.32 V, -40 C, 80 fF) |
| Maximum 6–7 ns RMS supply current | 0.0787293 µA — case_001 (ff, 1.32 V, -40 C, 5 fF) |

The testbench instantiates two copies of the exact archived PEX slice.
The selected copy checks programmed discharge and absent-via retention;
the second holds expert-enable low and checks masking. Output load is the
only synthetic capacitance added to the extracted circuit.

## Governed sweep

- Full 3 × 3 × 3 SS/TT/FF, 1.08/1.20/1.32-V, -40/27/125-C sweep at 20 fF.
- 5/20/80-fF load sweeps at nominal, slow-low-hot, and fast-high-cold conditions.
- Duplicate points run once, yielding 33 deterministic cases.
- Supply points remain below the public low-voltage model's 1.5-V VDS maximum.

## Claim boundary

- Establishes: electrical read behavior of the exact capacitance-extracted IHP SG13G2 two-column demonstration slice.
- Establishes: selected programmed discharge, absent-via retention, expert-enable masking, and static sense polarity over the declared deterministic PVT and output-load cases.
- Establishes: delay, supply-energy, and leakage sensitivity using official public IHP PSP103 low-voltage MOS models.

- Does not establish: statistical mismatch yield or sense-amplifier offset.
- Does not establish: distributed wire-resistance, full-row, full-column, decoder, repair, IR-drop, noise, aging, electromigration, or simultaneous-read behavior.
- Does not establish: N7 or N4 density, bandwidth, delay, energy, leakage, yield, or cost.
- Does not establish: whole-wafer inference throughput or GPU speedup.
- Does not establish: silicon correlation or manufacturing sign-off.

No IHP or SKY130 electrical value is feature-size-scaled into N7/N4
performance or a GPU speedup.

## Reproduction

```bash
python3 tools/run_ihp_extracted_pvt.py
```
