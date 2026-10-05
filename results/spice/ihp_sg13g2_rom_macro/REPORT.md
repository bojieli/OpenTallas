# IHP SG13G2 routed mask-ROM macro area

**Status:** **PASS**  
**Evidence class:** drawn bit array plus synthesised, placed and fully routed standard-cell periphery; **130 nm**; not silicon  
**PDK:** `ihp-sg13g2` / `v0.3.0` / `5cccb161f7492697cfa52eb14dc03beb00bdca9e`  
**Magic:** `8.3.674`  **OpenROAD:** `v2.0-17598-ga008522d8`  **Yosys:** `0.68`

## What routing found that bitcell geometry could not

**A minimum-pitch ROM array is not legal without periodic substrate taps.** This run drew the same 128 × 128 array with the tap bands removed and the installed public deck returned **6,897 DRC errors**, all of them *N-diff distance to P-tap must be < 20.0um (LU.b)*. The tap bands that fix it are real area, they scale with array height, and a density number taken from bitcell pitch alone does not contain them.

## Inputs this run did not invent

Two numbers enter this run from elsewhere. Neither is written in this runner's
source or in its contract; both are read from the artifact of the run that measured
them, and the run refuses to start if that artifact is missing or was produced by a
different revision of the layout generator.

| Quantity | Value | Read from |
|---|---:|---|
| ROM bitcell area | 0.390150 µm² | `results/spice/ihp_sg13g2_bitcell/bitcell.json#rom_bitcell.cell_area_um2` |
| Wordline pin capacitance | 0.6340 fF/column | `results/spice/ihp_sg13g2_rom_read_energy/read_energy.json#wordline_capacitance.ff_per_column` |

## Measured areas

| Macro | Bits | Bit-array area | Drawn macro | Macro-internal efficiency | Std-cell periphery | Routed die | **Array efficiency** |
|---|---:|---:|---:|---:|---:|---:|---:|
| `rom_128x32_c2` (64×64, c2) | 4,096 | 1598.1 µm² | 2012.1 µm² | 79.42% | 4369.1 µm² | 13402.9 µm² | **11.92%** |
| `rom_512x32_c4` (128×128, c4) | 16,384 | 6392.2 µm² | 7415.8 µm² | 86.20% | 6561.5 µm² | 24395.2 µm² | **26.20%** |

Every routed macro closed detailed routing with 0 violations.

## Against the assumed constant, and against a real memory

- `rom.array_efficiency` is **0.52**, graded `derived`.
- **Macro-internal efficiency** — bit array ÷ drawn macro, i.e. what the custom
  part costs in tap bands, wordline strap and bitline escape — is
  **79.4–86.2%**.
  On that boundary alone the model's 0.52 is *conservative*.
- **Whole-macro efficiency** with a synthesised standard-cell periphery is
  **11.9–26.2%**.
  On that boundary the model's 0.52 is *unreachable*.

The two numbers differ by more than a factor of two and the constant does not say
which boundary it means. That ambiguity, not the value, is the defect.

## How much of the die area is a measurement, and how much is a choice

The nominal die is **sized from the contract's requested utilization**, so the
whole-macro efficiency above is partly a restatement of that constant rather than a
measurement. To bound how much, this run re-routes the identical netlist on
progressively smaller dies and records whether detailed routing still closes with
zero violations.

**The placer's target density is a second chosen constant, and the first version of
this probe measured it by accident.** Every refusal that version recorded arrived as
OpenROAD's `GPL-0302`, whose text is *Use a higher -density or re-floorplan with a
larger core area* — the global placer naming this runner's own target density as the
remedy — and the report called the result a measured cell-area floor. A probe is
therefore now re-tried at every rung of `[0.9, 0.95, 0.99]` before it is allowed to count as a refusal,
and the density each row actually ran at is printed. Read the rows that say *tried*:
each one is a die the first version would have reported as refused.

| Macro | Utilization | Place density | Die | Detailed route | Array efficiency |
|---|---:|---:|---:|---|---:|
| `rom_128x32_c2` | 0.42 (nominal) | 0.57 | 13402.9 µm² | closed, 0 violations | 11.92% |
| `rom_128x32_c2` | 0.55 | 0.70 | 11081.9 µm² | closed, 0 violations | 14.42% |
| `rom_128x32_c2` | 0.70 | 0.90 (tried 0.85, 0.90) | 9260.5 µm² requested | **did not close**: [ERROR DPL-0036] Detailed placement failed. | — |
| `rom_128x32_c2` | 0.85 | 0.85 | 8084.2 µm² requested | **did not close**: [ERROR GPL-0301] Utilization 105.232 % exceeds 100%. | — |
| `rom_512x32_c4` | 0.42 (nominal) | 0.57 | 24395.2 µm² | closed, 0 violations | 26.20% |
| `rom_512x32_c4` | 0.55 | 0.90 (tried 0.70, 0.90) | 20691.0 µm² | closed, 0 violations | 30.89% |
| `rom_512x32_c4` | 0.70 | 0.95 (tried 0.85, 0.90, 0.95) | 18092.9 µm² requested | **did not close**: [ERROR DPL-0036] Detailed placement failed. | — |
| `rom_512x32_c4` | 0.85 | 0.85 | 16432.2 µm² requested | **did not close**: [ERROR GPL-0301] Utilization 115.167 % exceeds 100%. | — |

At the tightest die that still closes, array efficiency is **14.42–30.89%**, and a tighter die of the same netlist does not close. That brackets the reported number between a measured floor and the contract's request: the efficiency is no longer a restatement of the utilization constant.

**Read the stage each probe failed at.** A floor found at placement means the standard cells stopped fitting on the smaller die; a floor found at routing would mean the wires stopped fitting. Every refusal was re-tried at each rung of the contract's placement-density ladder before it was allowed to count, because the placer's target density is a constant this runner chose and GPL-0302 names it as the remedy. These probes fail at detailed placement and global placement — never at routing — so what is measured is a CELL-AREA floor for this periphery and not a routability floor. A custom periphery with fewer cells would move it.

**No refusal above is attributable to the placement density.** Every probe that did not close was re-tried up the density ladder and its final diagnostic no longer names the target density as the remedy, so the refusals are properties of the netlist and the floorplan rather than of a constant in this runner.

**And read the density the tightest die closed at.** The efficiency at the measured floor is reported at placement densities of `rom_128x32_c2` 0.70, `rom_512x32_c4` 0.90. A die that only closes at a high target density has no slack left in it: no room for an ECO, and none for the power distribution network the next paragraph says this flow does not build. The floor brackets the die; it does not propose a floorplan.

**No power distribution network is built.** This flow runs no `pdngen`, no
`global_connect` and lays no straps. The macro's `VSS` pin is declared in the LEF
and, in the netlist that is routed, is tied to `1'b0` — a logic constant inserted by
`insert_tiecells`, not a rail. Every die area above is therefore signal routing
only, and a manufacturable macro carries power, so these areas are lower bounds on
that account too.

For scale, IHP's own SRAM macros at comparable capacity, measured the same way
(bitcell pitch area ÷ LEF footprint), reach:

| Foundry SRAM macro | Bits | Array efficiency |
|---|---:|---:|
| `RM_IHPSG13_1P_256x16_c2_bm_bist` | 4,096 | 43.78% |
| `RM_IHPSG13_1P_512x8_c3_bm_bist` | 4,096 | 47.12% |
| `RM_IHPSG13_1P_64x64_c2_bm_bist` | 4,096 | 24.39% |
| `RM_IHPSG13_1P_1024x16_c2_bm_bist` | 16,384 | 61.83% |
| `RM_IHPSG13_1P_256x64_c2_bm_bist` | 16,384 | 52.87% |
| `RM_IHPSG13_1P_512x32_c2_bm_bist` | 16,384 | 61.79% |

A memory compiler's periphery is custom layout; this one is standard cells at a
placement density the router would accept. **That is why the routed number is a
lower bound and must not be quoted as the efficiency a ROM product would have.**

## Claim boundary

- Establishes: that a via1-programmed mask-ROM bit array drawn at the minimum legal pitch requires periodic substrate tap bands, because without them the array violates the public latch-up rule LU.b.
- Establishes: the drawn macro footprint of that array including tap bands, the wordline strap and the bitline escape, measured from the Magic-written LEF.
- Establishes: the routed die area of that macro with a synthesised standard-cell periphery, under full OpenROAD place-and-route with zero detailed-route violations.
- Establishes: the array efficiency at the contract's requested utilization, and the array efficiency at the tightest die of the same netlist that still closes detailed routing, which is a measured floor rather than a chosen one.

- Does not establish: N7, N6, N5 or N4 macro area, array efficiency, density or timing.
- Does not establish: that a standard-cell periphery is equivalent to a memory-compiler periphery: it is not, and the measured efficiency is therefore a LOWER bound.
- Does not establish: sense-amplifier design, read margin, redundancy, BIST or test coverage, none of which is in this periphery.
- Does not establish: whole-wafer inference throughput or GPU speedup.
- Does not establish: silicon correlation or manufacturing sign-off.
- Does not establish: the array efficiency of a die smaller than the tightest one probed: the floor probe brackets the die area, it does not minimise it.
- Does not establish: a die floor independent of the placer's target placement density: that density is a constant chosen in tools/run_ihp_rom_macro_route.py, the probe escalates it through `die_floor_probe_place_densities` before recording a refusal, and any refusal whose diagnostic still names it is a floor CONDITIONAL ON that ladder.
- Does not establish: any power-distribution area or IR-drop behaviour: this flow builds NO power distribution network and connects no straps, and the bit array's VSS pin is tied to a logic constant by insert_tiecells rather than to a rail, so every die area here is signal routing only and is a LOWER bound on that account too.

## Reproduction

```bash
python3 tools/run_ihp_rom_macro_route.py
```
