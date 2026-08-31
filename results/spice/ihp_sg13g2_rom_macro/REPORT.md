# IHP SG13G2 routed mask-ROM macro area

**Status:** **PASS**  
**Evidence class:** drawn bit array plus synthesised, placed and fully routed standard-cell periphery; **130 nm**; not silicon  
**PDK:** `ihp-sg13g2` / `v0.3.0` / `5cccb161f7492697cfa52eb14dc03beb00bdca9e`  
**Magic:** `8.3.674`  **OpenROAD:** `v2.0-17598-ga008522d8`  **Yosys:** `0.68`

## What routing found that bitcell geometry could not

**A minimum-pitch ROM array is not legal without periodic substrate taps.** This run drew the same 128 × 128 array with the tap bands removed and the installed public deck returned **6,897 DRC errors**, all of them *N-diff distance to P-tap must be < 20.0um (LU.b)*. The tap bands that fix it are real area, they scale with array height, and a density number taken from bitcell pitch alone does not contain them.

## Measured areas

| Macro | Bits | Bit-array area | Drawn macro | Macro-internal efficiency | Std-cell periphery | Routed die | **Array efficiency** |
|---|---:|---:|---:|---:|---:|---:|---:|
| `rom_128x32_c2` (64×64, c2) | 4,096 | 1598.1 µm² | 2012.1 µm² | 79.42% | 4369.1 µm² | 13402.9 µm² | **11.92%** |
| `rom_512x32_c4` (128×128, c4) | 16,384 | 6392.2 µm² | 7415.8 µm² | 86.20% | 6561.5 µm² | 24395.2 µm² | **26.20%** |

Every routed macro closed detailed routing with 0 violations.

## Against the assumed constant, and against a real memory

- `rom.array_efficiency` is **0.70**, graded `assumed`.
- **Macro-internal efficiency** — bit array ÷ drawn macro, i.e. what the custom
  part costs in tap bands, wordline strap and bitline escape — is
  **79.4–86.2%**.
  On that boundary alone the assumed 0.70 is *conservative*.
- **Whole-macro efficiency** with a synthesised standard-cell periphery is
  **11.9–26.2%**.
  On that boundary the assumed 0.70 is *unreachable*.

The two numbers differ by more than a factor of two and the constant does not say
which boundary it means. That ambiguity, not the value, is the defect.

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
- Establishes: the resulting array efficiency, measured rather than assumed.

- Does not establish: N7, N6, N5 or N4 macro area, array efficiency, density or timing.
- Does not establish: that a standard-cell periphery is equivalent to a memory-compiler periphery: it is not, and the measured efficiency is therefore a LOWER bound.
- Does not establish: sense-amplifier design, read margin, redundancy, BIST or test coverage, none of which is in this periphery.
- Does not establish: whole-wafer inference throughput or GPU speedup.
- Does not establish: silicon correlation or manufacturing sign-off.

## Reproduction

```bash
python3 tools/run_ihp_rom_macro_route.py
```
