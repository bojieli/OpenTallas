# IHP SG13G2 extracted mask-ROM array read energy

**Status:** **PASS** (33/33 cases)
**Evidence class:** deterministic simulation of an extracted minimum-pitch ROM bit array; **130 nm**; not silicon
**PDK:** `ihp-sg13g2` / `v0.3.0` / `5cccb161f7492697cfa52eb14dc03beb00bdca9e`
**Simulator:** ngspice 43 with the pinned official PSP103 OSDI modules

## What was measured, and what the constant claims

| Quantity | Value |
|---|---:|
| Array simulated over PVT | 64 rows × 8 columns, minimum legal pitch |
| Extracted bitline capacitance | 0.5032 fF per row + 0.2425 fF (R² = 0.999978) |
| Of that, coupling to the two neighbours | **75.5%** |
| Read energy, nominal case | 135.11 fJ per access of 8 bits |
| Read energy per bit, nominal | **16.889 fJ/bit** |
| Read energy per byte, nominal | **1.351e-13 J/B** |
| Wordline effective input capacitance | **0.6340 fF per column** |
| Of which extracted interconnect | 0.0510 fF per column |
| Assumed `energy.rom_read_j_per_byte` | 8.000e-14 J/B, graded `assumed` |
| Measured ÷ assumed, at 64 rows | 1.69× |

Across the full grid the read energy spans 107.10 fJ (case_016, ss, 1.08 V, 125.0 C) to 188.75 fJ (case_007, ff, 1.32 V, -40.0 C).

## The constant is under-specified, and this is the finding that matters

Read energy per bit is **not** a technology constant. It is affine in column height,
because a read discharges a whole bitline whatever the array stores:

| Column height | Read energy | Per bit | Per byte |
|---:|---:|---:|---:|
| 16 rows | 41.14 fJ | 5.142 fJ/bit | 4.114e-14 J/B |
| 32 rows | 72.78 fJ | 9.098 fJ/bit | 7.278e-14 J/B |
| 64 rows | 135.11 fJ | 16.889 fJ/bit | 1.351e-13 J/B |
| 128 rows | 237.66 fJ | 29.707 fJ/bit | 2.377e-13 J/B |

A straight line through those points has slope **1.7464 fJ per row of column height** and intercept 16.888 fJ, with R² = 0.997203. Per-interval slopes are 1.9778 fJ/row (16→32), 1.9478 fJ/row (32→64), 1.6023 fJ/row (64→128); the per-interval slope falls as the column grows, so the affine fit is slightly conservative at large heights: the precharge device does not fully restore the far end of a long bitline inside a fixed window.
At the measured 3 stored ones in the accessed row of 8 columns, that is 0.5821 fJ per row per discharging bitline.

A single scalar per byte therefore names a column height without saying so. At this
node, and at the 3-of-8 stored-one density of the
accessed row, the assumed 8e-14 J/B corresponds to a column of about
**36 rows**. That is short: the shipped
single-port memories in this same PDK are built at column heights up to 512 rows
(`results/spice/ihp_sg13g2_bitcell/bitcell.json#sram_bitcell.macros[].physical_rows`),
and an unstated column height is the reason
the model needs a column-height term, not a better scalar. The number is quoted here
to size the gap in the model's *shape*, not to restate a 130 nm energy as an N6 one.

## The wordline load the macro flow is entitled to

`physical/ihp_sg13g2_rom_macro/macro_contract.json` needs one number from this run:
the wordline load of the bit array, which sizes the wordline drivers the periphery
synthesises and therefore part of the macro area. It is measured as charge delivered
by the wordline driver divided by the rail — an effective capacitance, which does
not assume the gate is linear — over two windows:

| Window | Effective capacitance |
|---|---:|
| the wordline transition alone | 0.5578 fF/column |
| transition **and** the bitline discharge that follows it | 0.6340 fF/column |
| **given to the macro flow** | **0.6340 fF/column** |

The two windows differ because the falling bitlines pull charge through the row
transistors' gate-drain overlap, and the wordline driver really does supply it on
every access. **The larger of the two is handed to the macro flow.** That sizes the
wordline drivers up, makes the periphery larger and makes the array efficiency this
chain reports lower; the smaller number would have improved it, which is exactly why
it is not the one used.

The extracted interconnect capacitance on the same nets is only
0.0510 fF per column,
because `ext2spice` writes wiring parasitics and the row transistors' gate capacitance
lives inside the device model rather than in a `C` element. **Reading the wordline load
off the parasitic netlist would therefore understate it by design.** That is the reason
this number is measured in simulation and not counted out of the netlist.

## The second finding: minimum pitch buys density and loses margin

At the minimum legal column pitch, **75.5%** of a
bitline's extracted capacitance is coupling to its two neighbours. A stored one on both
neighbours therefore drags an unselected bitline down with them: in the nominal case the
unselected bitline holds only **57.7%**
of the supply at the sample point rather than the full rail. The read still resolves — the
measured margin is 57.5% of the supply — but a
manufacturable array would spend area on shielding, a wider pitch, or twisted bitlines, and
**that area is not in the bitcell pitch**. A density number taken from bitcell geometry alone
does not carry this cost.

## PVT grid

| Case | Corner | VDD | T | Row | Energy | Per bit | Margin |
|---|---|---:|---:|---:|---:|---:|---:|
| `case_001` | ff | 1.08 V | -40 C | 32 | 108.80 fJ | 13.600 fJ | 57.4% |
| `case_002` | ff | 1.08 V | 27 C | 32 | 109.01 fJ | 13.626 fJ | 57.4% |
| `case_003` | ff | 1.08 V | 125 C | 32 | 110.05 fJ | 13.757 fJ | 57.2% |
| `case_004` | ff | 1.2 V | -40 C | 32 | 133.69 fJ | 16.712 fJ | 57.2% |
| `case_005` | ff | 1.2 V | 27 C | 32 | 134.00 fJ | 16.750 fJ | 57.2% |
| `case_006` | ff | 1.2 V | 125 C | 32 | 135.43 fJ | 16.929 fJ | 57.2% |
| `case_007` | ff | 1.32 V | -40 C | 1 | 188.75 fJ | 23.594 fJ | 44.9% |
| `case_008` | ff | 1.32 V | -40 C | 32 | 160.94 fJ | 20.117 fJ | 57.0% |
| `case_009` | ff | 1.32 V | -40 C | 62 | 160.90 fJ | 20.113 fJ | 56.9% |
| `case_010` | ff | 1.32 V | 27 C | 32 | 161.32 fJ | 20.165 fJ | 57.0% |
| `case_011` | ff | 1.32 V | 125 C | 32 | 163.09 fJ | 20.386 fJ | 57.0% |
| `case_012` | ss | 1.08 V | -40 C | 32 | 108.22 fJ | 13.527 fJ | 55.6% |
| `case_013` | ss | 1.08 V | 27 C | 32 | 108.17 fJ | 13.521 fJ | 55.3% |
| `case_014` | ss | 1.08 V | 125 C | 1 | 131.39 fJ | 16.424 fJ | 45.5% |
| `case_015` | ss | 1.08 V | 125 C | 32 | 107.12 fJ | 13.390 fJ | 53.8% |
| `case_016` | ss | 1.08 V | 125 C | 62 | 107.10 fJ | 13.387 fJ | 53.8% |
| `case_017` | ss | 1.2 V | -40 C | 32 | 135.67 fJ | 16.959 fJ | 57.6% |
| `case_018` | ss | 1.2 V | 27 C | 32 | 135.85 fJ | 16.981 fJ | 57.6% |
| `case_019` | ss | 1.2 V | 125 C | 32 | 135.79 fJ | 16.974 fJ | 57.0% |
| `case_020` | ss | 1.32 V | -40 C | 32 | 163.73 fJ | 20.466 fJ | 57.6% |
| `case_021` | ss | 1.32 V | 27 C | 32 | 164.15 fJ | 20.519 fJ | 57.6% |
| `case_022` | ss | 1.32 V | 125 C | 32 | 164.82 fJ | 20.602 fJ | 57.6% |
| `case_023` | tt | 1.08 V | -40 C | 32 | 109.35 fJ | 13.669 fJ | 57.4% |
| `case_024` | tt | 1.08 V | 27 C | 32 | 109.52 fJ | 13.690 fJ | 57.4% |
| `case_025` | tt | 1.08 V | 125 C | 32 | 109.67 fJ | 13.709 fJ | 56.9% |
| `case_026` | tt | 1.2 V | -40 C | 32 | 134.80 fJ | 16.850 fJ | 57.5% |
| `case_027` | tt | 1.2 V | 27 C | 1 | 158.98 fJ | 19.872 fJ | 45.5% |
| `case_028` | tt | 1.2 V | 27 C | 32 | 135.11 fJ | 16.889 fJ | 57.5% |
| `case_029` | tt | 1.2 V | 27 C | 62 | 135.08 fJ | 16.885 fJ | 57.5% |
| `case_030` | tt | 1.2 V | 125 C | 32 | 135.79 fJ | 16.974 fJ | 57.5% |
| `case_031` | tt | 1.32 V | -40 C | 32 | 162.38 fJ | 20.297 fJ | 57.3% |
| `case_032` | tt | 1.32 V | 27 C | 32 | 162.79 fJ | 20.349 fJ | 57.4% |
| `case_033` | tt | 1.32 V | 125 C | 32 | 163.82 fJ | 20.477 fJ | 57.4% |

## Claim boundary

- Measured boundary: bit-array only: wordline, cell, bitline and precharge device. It excludes address decode, sense amplification and the macro output latch, all of which rom_read_j_per_byte's own stated boundary includes, so the measured value is a LOWER bound on the quantity that constant names.

- Establishes: extracted bitline capacitance per row of column height for a minimum-pitch via1-programmed NOR mask-ROM array in IHP SG13G2.
- Establishes: the fraction of that capacitance that is coupling to the two neighbouring bitlines at the minimum legal column pitch.
- Establishes: supply energy per read access, and per stored bit, of that exact extracted array over the declared deterministic PVT grid.
- Establishes: that read energy per bit is affine in column height rather than constant, measured over a 16-to-128-row sweep.

- Does not establish: N7, N6, N5 or N4 read energy, delay, leakage, bandwidth or power.
- Does not establish: that a 130 nm energy per byte may be feature-size-scaled into a target-node energy per byte.
- Does not establish: decoder, address, sense-amplifier, output-latch, repair or macro-boundary energy, none of which is in this array.
- Does not establish: statistical mismatch, sense offset, yield, aging or electromigration behaviour.
- Does not establish: whole-wafer inference throughput, device power or GPU speedup.
- Does not establish: silicon correlation or manufacturing sign-off.

## Reproduction

```bash
python3 tools/run_ihp_rom_read_energy.py
```
