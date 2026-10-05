# IHP SG13G2 distributed-RC extraction and local PVT campaign

**Result:** **PASS** (165/165 full-RC electrical cases passed)  
**Evidence class:** independent public open-PDK distributed-RC extraction and simulation of the archived local demonstration slice; not silicon  
**Physical input:** `bb6b6b8bbaef9e7143c812d79650e8555de86de5ca59a05e763687c4bdf610b5`  
**Magic:** `8.3.674` / `17ac06a24a952380ade3a7d33cd2f0c3943dfc12`  
**Simulator:** pinned ngspice 43 with four hash-verified IHP OSDI modules

## Extracted styles and electrical effect

Every style has 10 MOS instances, 41 explicit resistor elements, and 68
capacitors. The resistor sum is only an extraction diagnostic; it is not
an end-to-end or equivalent network resistance.

| IHP public RC style | Sum of R elements (ohm, diagnostic) | Total C (fF) | Nominal TT delay (ns) | Nominal delay vs C-only | Worst delay over 33 cases (ns) |
|---|---:|---:|---:|---:|---:|
| `ngspice()` | 26581.1 | 17.9765 | 0.0448135 | +3.766% | 0.0678111 |
| `ngspice(hrhc)` | 26765.7 | 19.8829 | 0.0461815 | +6.933% | 0.0700528 |
| `ngspice(hrlc)` | 26765.7 | 16.2224 | 0.0434555 | +0.621% | 0.065579 |
| `ngspice(lrhc)` | 26478.6 | 19.7985 | 0.0461815 | +6.933% | 0.0700528 |
| `ngspice(lrlc)` | 26478.6 | 16.1556 | 0.0434555 | +0.621% | 0.0655791 |

This is a full-RC-versus-capacitance-only comparison. Network
subdivision redistributes capacitance as well as adding resistors, so the
difference is not reported as a pure resistance penalty.

## Extraction controls

- Magic's integrated `extract do extresist` path runs exactly once per style and pass.
- Network threshold, delay threshold, and individual-resistor pruning threshold are zero; simplification is off.
- Each style is extracted twice in a fresh directory. The exact multisets of ports, MOS terminals/parameters, resistor edges/values, and capacitor edges/values must match.
- All 5 style replays pass semantic equality.
- All five styles emit the same 10-device, 41-resistor, 68-capacitor RC netlist element counts. The two high-R styles extract and output 15 of 41 top-cell networks; nominal and both low-R styles extract and output 14 of 41. Both primitive subcells extract and output one substrate/well network.
- Every extraction reports zero geometry/tool feedback errors.
- The programmed row terminal belongs only to the `BL_PRESENT` resistor component. The absent row terminal belongs to `ROM_DRAIN_ABSENT`, not either physical bitline, and the two program-state components are disjoint.
- All six extracted non-ground NMOS body nodes retain positive-resistance paths to `VGND`; substrate/body resistance is not discarded.

## Electrical sweep

Each primary full-RC netlist is simulated over the same 33 SS/TT/FF,
1.08/1.20/1.32-V, -40/27/125-C, and 5/20/80-fF points used by
the capacitance-only IHP campaign. The official PSP103 models and exact
pinned OSDI modules are used in every case.

## Claim boundary

- Establishes: Magic full-RC extraction methodology for the exact archived two-column IHP SG13G2 demonstration layout under all five public interconnect styles.
- Establishes: explicit resistor-network preservation of the programmed-drain and absent-via connectivity distinction, including extracted nonzero NMOS substrate/body paths.
- Establishes: local full-RC electrical behavior over the same 33 deterministic device-PVT, supply, temperature, and output-load points used by the capacitance-only IHP campaign.
- Establishes: semantic extraction replay despite any non-semantic SPICE statement ordering differences.

- Does not establish: compact ROM cell, row, column, decoder, sense-amplifier, repair, clock, or full-array resistance and capacitance.
- Does not establish: full-array simultaneous-current, IR-drop, noise, electromigration, aging, thermal, or power-delivery behavior.
- Does not establish: N7 or N4 density, bandwidth, delay, energy, leakage, yield, or cost.
- Does not establish: whole-wafer timing, inference throughput, or GPU speedup.
- Does not establish: target-foundry late-via availability, sign-off extraction, manufacturing sign-off, or silicon correlation.

The 32.5 × 11.5-µm layout is a deliberately roomy demonstration slice.
No IHP or SKY130 RC value may be feature-size-scaled into N7/N4, a
whole array, a wafer, or a GPU speedup.

## Reproduction

```bash
python3 tools/run_ihp_resistance.py
```

The JSON result records exact primary/replay artifacts, PDK and tool
identities, per-case measures, baseline deltas, and SHA-256 values.
