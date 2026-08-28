# IHP SG13G2 controlled-via ROM physical replication

**Status:** **PASS**  
**Evidence class:** independent public-PDK DRC, LVS, and capacitance extraction; not silicon  
**PDK:** `ihp-sg13g2` / `v0.3.0` / `5cccb161f7492697cfa52eb14dc03beb00bdca9e`  
**Magic:** `8.3.674` / `17ac06a24a952380ade3a7d33cd2f0c3943dfc12`  
**Netgen:** `1.5.322`

## Closed gates

- Magic `drc(full)`: **0 errors**.
- Netgen LVS: **Circuits match uniquely.**
- Extracted topology: **10 MOS devices, 15 nets, 10 ports**.
- Programming geometry: present column has 6 top-level via1 shapes; absent column has 5; delta **1**.
- PEX: **59 capacitance elements** (47 nonzero), totaling 12.9213 fF.

The layout uses IHP's native `sg13_lv_nmos` and `sg13_lv_pmos`
generators. Device-terminal vias are disabled, legal remote landing sites
are routed explicitly, and the lower row-drain via exists only in the
programmed column. The unprogrammed row retains `ROM_DRAIN_ABSENT` as a
distinct extracted node rather than silently joining `BL_ABSENT`.

## Local geometry and parasitics

The fixed demonstration footprint is 32.500 × 11.500 µm = 373.750 µm².
It is deliberately roomy and is **not a ROM-cell density macro**.

| Net | Incident extracted capacitance |
|---|---:|
| `BL_PRESENT` | 3.0459 fF |
| `BL_ABSENT` | 2.76704 fF |
| `Q_PRESENT` | 1.41939 fF |
| `Q_ABSENT` | 1.41951 fF |

Detailed distributed resistance and extracted electrical PVT/load
behavior are separate gates; this run closes base capacitance extraction.

## Scientific interpretation

This is an independent foundry-PDK replication of the controlled-via
method, not a feature-size scaling exercise. Agreement with SKY130 would
reduce the chance that topology legality is a SKY130-deck artifact; it
still would not characterize an N7/N4 product.

- Establishes: legal geometry under the exact installed public IHP SG13G2 Magic deck.
- Establishes: schematic-versus-layout connectivity for an independently implemented two-column via-programmed ROM slice.
- Establishes: one physical via1 programming difference between otherwise matched present and absent columns.
- Establishes: device and coupling-capacitance extraction from the drawn local geometry.

- Does not establish: N7 or N4 density, bandwidth, delay, energy, leakage, yield, or cost.
- Does not establish: availability or economics of target-foundry late-via ROM personalization.
- Does not establish: full-array decoder, wordline, bitline, sense, repair, simultaneous-read, IR-drop, noise, or thermal behavior.
- Does not establish: whole-wafer inference throughput or GPU speedup.
- Does not establish: silicon correlation or manufacturing sign-off.

## Reproduction

```bash
python3 tools/run_ihp_physical.py
```

The machine-readable result records the exact PDK tree, tool binaries,
inputs, decks, and archived output hashes.
