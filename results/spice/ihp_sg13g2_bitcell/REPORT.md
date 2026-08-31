# IHP SG13G2 measured mask-ROM versus 6T-SRAM bitcell area

**Status:** **PASS**  
**Evidence class:** drawn-geometry measurement in one installed open foundry PDK; **130 nm**; not silicon, not a leading node  
**PDK:** `ihp-sg13g2` / `v0.3.0` / `5cccb161f7492697cfa52eb14dc03beb00bdca9e`  
**Magic:** `8.3.674` / `17ac06a24a952380ade3a7d33cd2f0c3943dfc12`

## The measured ratio

| Quantity | Measured | Source |
|---|---:|---|
| Mask-ROM bitcell pitch | 510 × 765 nm | drawn here; DRC clean under `drc(full)` |
| Mask-ROM bitcell area | **0.390150 µm²** | pitch product |
| Foundry 6T SRAM bitcell pitch | 2.8100 × 1.0700 µm | IHP `sg13g2_sram` macro GDS |
| Foundry 6T SRAM bitcell area | **3.006700 µm²** | pitch product |
| **Measured area ratio** | **0.1298** | ROM ÷ SRAM, same PDK |
| Assumed `rom.cell_to_sram_cell_area_ratio` | 0.2000 | `configs/hardware/technology.json` |
| Measured ÷ assumed | 0.649× | |

At this node the drawn ROM bitcell is **7.71× smaller** than the
foundry 6T cell, against the 5× the assumption implies, so the assumed 0.20 is *conservative* here — and, for the reason given under "rule-set asymmetry" below,
the true same-rule-set ratio is smaller still.

The dual-port 8T bitcell in the same release measures 4.4200 × 1.2300 µm = 5.436600 µm², a ratio of 0.0718.

## Why the ROM pitch is a measurement and not a choice

Every drawn dimension of the ROM bitcell sits on a floor of the installed
public deck. Reducing any one of them by 10 nm produces the named violation below.

| Dimension | Nominal | Probed | DRC errors | Rule that stops the shrink |
|---|---:|---:|---:|---|
| `PX` | 510 nm | 500 nm | 54 | Diffusion spacing < 0.21 (Act.b); Metal1 spacing < 0.18 (M1.b); Metal2 spacing < 0.21 (M2.b) |
| `WD` | 300 nm | 290 nm | 158 | Metal1 spacing < 0.18 (M1.b); Metal2 spacing < 0.21 (M2.b); N-diffusion overlap of N-diffusion contact < 0.07 (Cnt.c) |
| `GS` | 380 nm | 370 nm | 32 | Diffusion contact spacing to poly < 0.11 (Cnt.f) |
| `DA` | 340 nm | 330 nm | 32 | N-diffusion overlap of N-diffusion contact < 0.07 (Cnt.c) |
| `DG` | 210 nm | 200 nm | 16 | Diffusion spacing < 0.21 (Act.b) |
| `PW` | 130 nm | 120 nm | 8 | poly width < 0.13 (Gat.a) |

The probes vary **one dimension at a time**, so what they prove is that each
dimension sits at a floor given the others — local minimality for this topology.
They do not prove a global minimum over all mask-ROM topologies, and a report that
reads them that way is claiming more than was measured.

## Why the SRAM pitch is a measurement and not a choice

The bitcell placement pitch was extracted from every shipped `sg13g2_sram` macro
(28 macros). In every macro carrying a datasheet the number of
bitcell placements equals the datasheet bit count exactly, and the LEF `SIZE`
record equals the datasheet area, so the cell being measured is one stored bit
and not a group. Exactly one pitch is observed per port family.

## The rule-set asymmetry, measured

The two cells are **not** drawn under the same rules, and this run measures the gap
rather than assuming it away. The foundry bitcell carries the PDK's own `SRAM`
recognition layer (GDS 25/0) and is **not legal** under the installed public logic deck:

| Cell | DRC errors under `drc(full)` | Rules violated |
|---|---:|---|
| `RM_IHPSG13_1P_BITKIT_CELL` | 29 | Poly overhang of transistor < 0.18 (Gat.c) (4); N-Diffusion spacing to N-well < 0.31 (NW.d) (27); Can't overlap those layers (3); Metal2 minimum area < 0.144 (M2.d) (8); P-diffusion overlap of P-diffusion contact < 0.07 (Cnt.c) (12); P-diff distance to N-tap must be < 20.0um (LU.a) (8); N-well overlap of P-Diffusion < 0.31 (NW.c) (34); N-diff distance to P-tap must be < 20.0um (LU.b) (6) |
| `RM_IHPSG13_1P_BITKIT_16x2_SRAM` | 389 | Poly overhang of transistor < 0.18 (Gat.c) (128); N-Diffusion spacing to N-well < 0.31 (NW.d) (654); N-diffusion overlap of N-diffusion contact < 0.07 (Cnt.c) (8); Can't overlap those layers (104); Metal2 minimum area < 0.144 (M2.d) (120); P-diffusion overlap of P-diffusion contact < 0.07 (Cnt.c) (324); Extension of tie diffusion beyond tie contact < 6.0um (LU.d, LU.d1) (6); N-well overlap of P-Diffusion < 0.31 (NW.c) (810); Diffusion minimum area < 0.122um^2 (Act.d) (2) |

Read the two rows differently. The isolated bitcell is checked without its array
context, so its `LU.a`/`LU.b` counts are an artefact of the missing tap rows and are
not push rules; they disappear in the 16 × 2 array, which carries taps. What survives
**with** array context is the real rule relief: poly endcap (`Gat.c`), well overlap and
spacing (`NW.c`, `NW.d`), contact enclosure (`Cnt.c`) and Metal2 minimum area (`M2.d`).

The ROM cell is logic-rule legal and the SRAM cell is not. A ROM array drawn with
the same relaxations available to the memory cell would be **smaller** than the one
measured here, so **the reported ratio is an upper bound** on the ratio that a single
rule set applied to both cells would give. It is not a floor.

## Foundry SRAM array efficiency, for comparison with `rom.array_efficiency`

Bitcell pitch area divided by the macro's own LEF footprint, for the shipped macros.
This is a real memory's array efficiency at this node, including its decoders, sense
path, control and (where present) BIST.

- single-port lowest: `RM_IHPSG13_1P_64x64_c2_bm_bist` at **24.39%** (4,096 bits)
- single-port highest: `RM_IHPSG13_1P_8192x32_c4` at **83.86%** (262,144 bits)
- assumed `rom.array_efficiency` = 0.70, graded `assumed`

| Fixed-width family | incremental area per bit | implied asymptotic array efficiency |
|---|---:|---:|
| `1P_x16` (mixed column-mux; slope not constant) | 4.0033 µm²/bit | 75.11% |
| `1P_x32` (mixed column-mux; slope not constant) | 3.6224 µm²/bit | 83.00% |
| `1P_x64` | 3.4742 µm²/bit | 86.54% |
| `1P_x8` (mixed column-mux; slope not constant) | 4.6085 µm²/bit | 65.24% |

Efficiency rises steeply with macro size, so a single scalar `array_efficiency` is
only meaningful once the macro geometry it refers to is stated.

## Node honesty

A sibling experiment measures the same ratio in **ASAP7 predictive 7 nm FinFET research PDK** and gets **0.2500** against this run's **0.1298** — the ROM bitcell is 93% larger relative to 6T SRAM at the FinFET node than at 130 nm. **The ratio is therefore node-sensitive and the two numbers must never be averaged, blended or interpolated.** Source: `results/asap7_physical/bitcell_density/bitcell_density.json`.

IHP SG13G2 is a **130 nm** process and the program targets N6/N5. A ratio of two
bitcell areas drawn in one PDK travels further than either absolute area, because
the leading terms — contact size, contact-to-gate clearance, diffusion spacing, gate
length — enter both cells. It still does not travel unchanged: the ROM cell is
contact-and-spacing limited while the 6T cell is additionally limited by well
spacing and by the p/n boundary, and those scale differently. **No number here may
be presented as an N6, N5, N4 or N7 value.**

## Claim boundary

- Establishes: the minimum DRC-legal drawn pitch of an independently implemented via1-programmed NOR mask-ROM bitcell under the exact installed public IHP SG13G2 Magic deck.
- Establishes: that every dimension of that bitcell is at a deck floor, because reducing any one of them by 10 nm produces a named rule violation.
- Establishes: the drawn placement pitch of the IHP SG13G2 foundry single-port and dual-port SRAM bitcells, cross-checked by requiring the bitcell instance count to equal the datasheet bit count in every shipped macro.
- Establishes: the ratio of those two measured pitch areas at 130 nm.
- Establishes: that the foundry SRAM bitcell is not legal under the installed public logic-rule deck, and which rules it violates.

- Does not establish: N7, N6, N5 or N4 bitcell area, density, ratio, delay, energy, leakage, yield, or cost.
- Does not establish: that the measured 130 nm area ratio transfers unchanged to any other node.
- Does not establish: availability or economics of target-foundry late-via ROM personalization.
- Does not establish: full-array decoder, wordline, bitline, sense, repair, simultaneous-read, IR-drop, noise, or thermal behavior.
- Does not establish: whole-wafer inference throughput or GPU speedup.
- Does not establish: silicon correlation or manufacturing sign-off.
- Does not establish: that this is the smallest mask-ROM bitcell drawable under this deck: the floor probes vary one dimension at a time and prove each is at a floor given the others, which is local minimality for this topology, not a global minimum over all ROM topologies.

- Rule-set asymmetry: the ROM bitcell is drawn under the public logic-rule deck and is DRC clean; the foundry SRAM bitcell carries the PDK SRAM recognition layer and violates that same deck, so the measured ratio is an upper bound on the ratio that would be obtained with one rule set applied to both.

## Reproduction

```bash
python3 tools/run_ihp_bitcell_density.py
```
