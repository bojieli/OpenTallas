# SKY130A distributed-RC extraction and local PVT campaign

**Result:** **PASS** (165/165 full-RC electrical cases passed)  
**Evidence class:** public open-PDK distributed-RC extraction and simulation of the archived local demonstration slice; not silicon  
**Physical input:** `511ab051c2be3be23ce8dc183734528a94090218e1db2bd224f179eedd16722a`  
**Magic:** `8.3.674` / `17ac06a24a952380ade3a7d33cd2f0c3943dfc12`

## Extracted styles and electrical effect

Each style has 630 explicit resistor elements, 269 capacitors, and ten
MOS instances. The resistor sum below is only an extraction diagnostic;
it is not an end-to-end or equivalent network resistance.

| PDK RC style | Sum of R elements (ohm, diagnostic) | Total C (fF) | Nominal TT delay (ns) | Nominal delay vs C-only | Worst delay over 33 cases (ns) |
|---|---:|---:|---:|---:|---:|
| `ngspice()` | 403205 | 33.0039 | 0.0412056 | +16.412% | 0.0690256 |
| `ngspice(hrhc)` | 451672 | 40.151 | 0.0490083 | +38.456% | 0.0820173 |
| `ngspice(hrlc)` | 451672 | 29.1065 | 0.0395559 | +11.751% | 0.0653974 |
| `ngspice(lrhc)` | 357693 | 40.106 | 0.0460013 | +29.961% | 0.0784332 |
| `ngspice(lrlc)` | 357693 | 29.0689 | 0.0372312 | +5.184% | 0.06262 |

The comparison is full-RC PEX versus the earlier capacitance-only PEX.
Because network subdivision redistributes capacitance as well as adding
resistors, the delta must not be labeled a pure resistance-only penalty.

## Extraction controls

- Magic's integrated `extract do extresist` path runs exactly once per style.
- Network threshold, delay threshold, and individual-resistor pruning threshold are all zero; simplification is off.
- Every style is extracted twice in a fresh directory. Raw SPICE statement order may differ, but the exact multiset of ports, devices, resistor edges/values, and capacitor edges/values must match.
- All 5 style replays pass semantic equality.
- The nominal top-cell .ext statistics include one 1.11022e-16 gate-to-gate coupling record absent from all four corner-style .ext files; every style still outputs 15 top-cell nets and the same 10-device, 630-resistor, 269-capacitor RC netlist element counts.
- The resistor graph connects the programmed row drain only to `BL_PRESENT`; the absent row drain terminates at `ROM_DRAIN_ABSENT`, remains disconnected from both physical bitlines, and the two programming-state components are disjoint.

## Electrical sweep

For each RC style, the exact archived full-RC netlist is simulated over
the same 33 SS/TT/FF, 1.62/1.80/1.98-V, -40/25/125-C, and
5/20/80-fF points used by the capacitance-only campaign. All local
programmed-discharge, absent-via retention, expert masking, sense polarity,
margin, delay, energy, current, and warning checks pass.

## Claim boundary

- Establishes: Magic full-RC extraction methodology for the exact archived two-column SKY130A demonstration layout under the declared public-PDK interconnect styles.
- Establishes: explicit resistor-network preservation of the programmed-drain and absent-via connectivity distinction.
- Establishes: local full-RC electrical behavior over the same 33 deterministic device-PVT, supply, temperature, and output-load points used by the capacitance-only campaign.
- Establishes: semantic extraction replay despite non-semantic SPICE statement ordering differences.

- Does not establish: compact ROM cell, row, column, decoder, sense-amplifier, repair, clock, or full-array resistance and capacitance.
- Does not establish: full-array simultaneous-current, IR-drop, noise, electromigration, aging, thermal, or power-delivery behavior.
- Does not establish: N7 or N4 density, bandwidth, delay, energy, leakage, yield, or cost.
- Does not establish: whole-wafer timing, inference throughput, or GPU speedup.
- Does not establish: target-foundry late-via availability, sign-off extraction, manufacturing sign-off, or silicon correlation.

This local 32.5 × 11.5-µm demonstration is deliberately roomy. No RC
number here may be feature-size-scaled into N7/N4, a whole array, a wafer,
or a GPU comparison.

## Reproduction

```bash
python3 tools/run_sky130_resistance.py
```

Exact primary/replay artifacts, model identities, per-case measures,
comparisons, thresholds, and SHA-256 values are stored in
`results/spice/sky130_resistance/resistance.json`.
