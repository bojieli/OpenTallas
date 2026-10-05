# SKY130A physical via-ROM slice

**Result:** **PASS**  
**Evidence class:** open-PDK DRC, LVS, and capacitance extraction; not silicon  
**PDK:** `sky130A` / open_pdks `f6eeac7dad085ffcc829ccfd721f7b4ce39edcf7`  
**Magic:** `8.3.674` / `17ac06a24a952380ade3a7d33cd2f0c3943dfc12`  
**Netgen:** `1.5.322`

## Closed gates

- Magic DRC: **0 errors**.
- Netgen LVS: **Circuits match uniquely.**
- Extracted topology: **10 MOS devices, 15 nets, 10 ports**.
- Programming geometry: present column has 6 via1 shapes; absent column has 5; the controlled delta is exactly one.
- PEX: **59 capacitance elements** (53 nonzero), totaling 20.7988 fF across this test slice.

The programmed row device is physically connected to `BL_PRESENT`. The matched
unprogrammed row device terminates at the distinct floating
`ROM_DRAIN_ABSENT` node and is not connected to `BL_ABSENT`. Netgen compares
all declared top-level pins and reports a unique match.

## Geometry and parasitics

The fixed demonstration footprint is 32.500 × 11.500 µm = 373.750 µm².
It is deliberately roomy and **must not be reported as a ROM cell density**.

| Net | Incident extracted capacitance |
|---|---:|
| `BL_PRESENT` | 3.6954 fF |
| `BL_ABSENT` | 3.36481 fF |
| `Q_PRESENT` | 1.63185 fF |
| `Q_ABSENT` | 1.63257 fF |

Detailed distributed wire resistance is not closed by this run; that requires
the separate Magic `extresist` campaign. The PEX netlist here contains the
drawn-device and coupling capacitances supplied by the base extractor.

## Claim boundary

- Establishes: legal geometry under the exact installed public SKY130A Magic deck.
- Establishes: schematic-versus-layout connectivity for the two-column via-programmed ROM slice.
- Establishes: one physical via1 programming difference between otherwise matched present and absent columns.
- Establishes: device and coupling-capacitance extraction from the drawn local geometry.

- Does not establish: N7 or N4 density, bandwidth, delay, energy, leakage, yield, or cost.
- Does not establish: availability or economics of target-foundry late-via ROM personalization.
- Does not establish: full-array decoder, wordline, bitline, sense, repair, simultaneous-read, IR-drop, noise, or thermal behavior.
- Does not establish: whole-wafer inference throughput or GPU speedup.
- Does not establish: silicon correlation or manufacturing sign-off.

There is no SKY130→N7/N4 feature-size scaling rule. Target-node PPA remains
dependent on a characterized target-foundry ROM macro, extracted target
interconnect and sense path, a reticle test vehicle, and silicon correlation.

## Reproduction

```bash
python3 tools/run_sky130_physical.py
```

The machine-readable result is `results/spice/sky130_physical/physical.json`. The exact PDK tree,
tool executables, generator, schematic, decks, and every archived output are
identified by SHA-256 in that file.
