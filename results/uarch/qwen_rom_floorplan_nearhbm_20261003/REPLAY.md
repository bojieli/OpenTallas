Qwen3-8B ROM die floorplan with near-HBM attention (model only)

This record is the floorplan successor for the design selected for build in `results/uarch/qwen_rom_calibrated_calendar_20261003/near-hbm-selected-r1.json`: TP4, G = 6,144, 1,536 tiles and 4 HBM3E stacks per die.

It is a model and a floorplan plan only. There is no RTL, no P&R and no adoption behind it. The tool is `tools/qwen_rom_floorplan_nearhbm.py`, the test is `tests/test_qwen_rom_floorplan_nearhbm.py`, and the outputs are `model-r1.json` and `floorplan-r1.svg`. `inputs/pinaccess/` holds the macro pin-access audit. It is byte-identical to `origin/claude/rom-macro-pin-access-20261003` at 9b7b12038. Every source is sha256-pinned in the record.

## Selected frame: B2-EW

**Die:** 24,452 x 32,800 um = 802.0 mm2. That is inside the 26 x 33 mm field and the 815 mm2 budget.

**Tile field:**
- 64 x 24 tiles of 313.632 x 1,291.68 um, which is 622.3 mm2 (it was 747.7 mm2).
- The tile column corridor narrows from 96.768 um to 52.704 um. The fill lane is gone, so the corridor carries only the 637 non-fill tracks: clock, reset, the 379-bit instruction, the 128-bit x line, go and ready. It provides 740 tracks.
- The slot height is re-derived for the same cell ceiling: 125,000 um2 at 0.5 utilisation, with 10 ROM macros and no KV macros.

**Hub spine:**
- 1,214 um wide and 31.2 mm tall, at the centre of the die.
- It holds the W5 spine blocks carried to TP4 (32.4 mm2), the hub element and a vertical link channel 174 um wide.

**Shoreline:**
- Two HBM PHYs sit on each of the east and west edges.
- The band behind each PHY is 1,562.8 um deep: 833.76 um of PHY, a 400.68 um controller band, and a 328.32 um near-HBM strip.
- The controller bands keep the whole current KV service upper bound (19.22 mm2) as a reservation, with no credit taken.
- Each strip holds six row-engine frames of 328.32 x 1,998 um.

**IO:** the north edge carries UCIe (10 mm2), a board SerDes reservation (4 mm2), the embedding ROM and the collective.

**Refused frames:**
- **A** (the current slot): its outline is 27.2 x 34.5 mm, and its tile cut needs 1,685 tracks against 1,360 available, a deficit of 325.
- **B1** (narrowed corridor, original slot height): 34.5 mm tall.
- **Every N/S-shoreline frame:** taller than 33 mm, and two 12 mm PHYs need 26 mm of edge.

## Links and stages

**Tracks.** Each stack link carries 1,056 tracks (512 b each way plus 32).
- The horizontal channels are 96.768 um, one between tile rows at each stack height. Each takes one link per cut: 756 tracks on M6 and 300 on M8, leaving 304 spare.
- The vertical spine leg carries two links (2,112 tracks): 1,360 on M7 and 752 on M9, leaving 336 spare.
- The 7,973 fill-control tracks are removed.

**Stages at the SS reach of 504 um per stage:**
- Hub to the stack centre is a 17,150 um trunk, which takes 35 stages.
- The in-strip fan to the farthest of the 6 row-engines takes 11 stages, for 46 in total. The model uses 45, so the floorplan adds +2 cycles per layer.
- From the PHY pins to the farthest row-engine is 12 stages. This term is not in the selected 1,700 cycles unless the start of each phase is prefetched.
- The hub is 33 stages from the north IO edge. That distance enters the all-reduce, which the all-reduce stream owns, so it is not priced here.

**Latency relative to the selected token:**
- The terms included here add 216 cycles, giving 191.15 us against 190.97 us.
- The worst case, with every conditional term counted, adds 6,336 cycles and gives 196.2 us.

## Removed area and the KV macro check

The tile KV SRAMs have no other user:
- The read port serves only ME ops with `me_wsrc=1`, which are the scores and P.V (two sites in `tools/hdc_program.py`).
- The write port serves only the new-token K/V write through `DST_KV` (two sites).
- Both move to the near-HBM unit.

The credit is **3,072 macros = 11.96 mm2**, not the pricing's 23.91 mm2. The W12 tile holds two macros per tile, not one per group.

## Power

These figures are at 5,237 tok/s, in scenario A, using the measured TT MAC.

**Strip:**
- 0.92 W/mm2 averaged over time.
- 3.92 W/mm2 peak during a phase.

**PHY.** All of the unqualified 10.19 pJ/b HBM-path share is placed on the PHY:
- 1.61 W/mm2 on average.
- 7.34 W/mm2 at the 0.9 TB/s peak.

**Band:** 1.42 W/mm2 on average.

**Limits:**
- No hot-spot limit is sourced (`power_scenarios.json` hot_spot reads "none found"), so this is **FLAGGED**.
- The only reference is H200's die average of 0.675 W/mm2.
- The die is about 173 W against the 474.6 W liquid limit (scenario A).

**IR drop.** On the repository die grid (2.5% M8/M9 per net, closed form), the peak strip drop is 229 mV against a 35 mV budget in A, and needs 16.4% coverage. In B it is 44 mV and needs 3.2%. This is an ASAP7 statement.

## Hardened elements to qualify, in order

1. **Near-HBM row-engine.**
   - 24 per die, in a 328.32 x 1,998 um frame.
   - Contents: 512 MAC lanes, 4 exp pipes and one `ot_sram_1r1w_1024x256_m2_r2c2`. Using 6 score SRAMs per stack instead of 4 costs +0.098 mm2 per die.
   - The SRAM is placed R0/MY only, at origin 0 mod 48 nm.
   - Cell utilisation must stay at or below 0.70.
   - Timing binds: MAC 1,040 MHz, exp 1,196 MHz and fp32_mul are not closed at SS 1.2 GHz.
2. **Hub element.**
   - One per die, in a 412.56 x 412.56 um frame, at 0.70.
   - Timing binds: recip and fp32_mul. The fallback moves 1/Z to the SFU and costs +576 cycles per token.
3. **Link endpoint.**
   - 184 stations, each 96.768 x 8.64 um at 0.53, plus 4 strip-side mesochronous FIFOs of 96.768 x 136.08 um.
   - The test is a 504 um span on a 1,056-bit bus at SS/FF.
4. **Tile re-frame.** The W12 tile without its KV slice, in a 313.632 x 1,291.68 um frame at 0.5.

**Prerequisite:** an east/west-shoreline HBM PHY abstract variant. The catalog PHY has M5 pins on its top edge and no legal R90 orientation.

## Replay

Run from the repository root:

```bash
(cd tests && python3 -m unittest test_qwen_rom_floorplan_nearhbm -v)
(cd tools && python3 qwen_rom_floorplan_nearhbm.py --verify)
```

`--verify` regenerates both outputs in a temporary directory and requires them to be byte-identical. It runs in seconds.

---

# r2: margins netted for place and route (model only)

r2 answers whether the r1 margins let place and route complete. It does not change anything in r1: `model-r1.json` and `floorplan-r1.svg` are byte-identical, and the r1 tool is unchanged.

- **Tool:** `tools/qwen_rom_floorplan_nearhbm_r2.py`. It imports r1.
- **Test:** `tests/test_qwen_rom_floorplan_nearhbm_r2.py`.
- **Outputs:** `model-r2.json` and `floorplan-r2.svg`.
- **KV service decomposition:** `inputs/kvservice/kv_service_families.py`.

## Die and margins

**Die:** 24,147 x 32,800 um = **792.0 mm2**. That is 23.0 mm2 under 815; r1 was 802.0.
- Unallocated area is 29.4 mm2: 20.3 mm2 of free shoreline plus 9.1 mm2 of IO spare.
- The change against r1 is funded by trimming the KV service reservation. The controller band narrows from 400.5 to 247.5 um.
- Keeping the whole 19.22 mm2 reservation still fits, at 802.0 mm2.

## Corridors per layer

Netted capacity is raw tracks, less the power grid at the region's IR coverage, less a 5% via/obstruction allowance (assumed), less the clock spine. The target is <= 70% of netted tracks: min(1 - ORFS layer adjustment 0.25, 1 - the die model's M8/M9 reserve 0.30).

| Corridor | Width (um) | Demand | 70% of netted | Demand / raw |
|---|---|---|---|---|
| Tile column (M7/M9) | 52.704 | 637 | 938 | 0.43 |
| Horizontal link (M6/M8) | 96.768 | 1,056 | 1,655 | 0.39 |
| Vertical spine (M7/M9) | 174.096 | 2,112 | 3,164 | 0.43 |
| In-strip fan (M7/M9, over the engine frames) | 328.32 | 1,056 | 5,172 | 0.11 |

- Every corridor fits the target at its r1 width.
- No width is narrowed below r1; r2 never relaxes a width.

## PG coverage (M8/M9 per net, 35 mV)

| Region | Peak density | Coverage per net |
|---|---|---|
| Tile field | 1.05 W/mm2 | 4.4% |
| Hub | 0.39 W/mm2 | 2.5% (the base grid) |
| Strip (scenario A) | 3.92 W/mm2 | 16.4% |

## Routed evidence: the gate

The only routed reference is a buffered straight-bus corridor:
- `v41_corridor_136um_1500w_M4up` routes at **0.225** of raw same-direction tracks, with GRT at 30.06% and 0 overflow.
- The 3,000-wire run is **unresolved at 0.451**: it stopped while still in congestion reduction.
- The r1/r2 corridors sit at 0.39-0.43, inside that unmeasured band.

What this means for the die:
- 815 mm2 holds the corridors down to a density of **0.362**.
- At 0.225 the die would be 902.5 mm2.
- Narrower 128-bit links (+10.1 us) do not help, because the tile column corridor carries the area.

**Gate:** route a 504 um link span and a tile-column corridor strip at the r2 widths before die assembly.

## Long wires and CTS

**Stations and repeaters at 504 um/stage:**
- Stations: 1.16 mm2 of FFs.
- Repeaters: 1.09 mm2. That is 7.71 buffers per wire-mm, as in the routed corridor.
- Both sit in corridor whitespace.

**CTS:**
- CTS is 5.3% of cell area (p90 over 139 routed blocks), 13.5 mm2 in all. Repair buffers add 6.7%.
- After both, tile utilisation is 0.56 (cap 0.70).
- Hub element utilisation would be 0.78, so its frame grows by 5.8% per side.
- Clock power is 52 W with ICG gating (assumed constant) and 280 W ungated (measured).

## Hot spot

**Limit:** 2.0 W/mm2 nominal, 1.0 conservative, 4.0 aggressive. Source: IEEE EPS HIR Thermal chapter v0.9, s2 and Table 4 (https://eps.ieee.org/wp-content/uploads/2026/05/HIR_20-Thermal_0.9.docx.pdf).

Thermal time constant: the strip's is 1.2 ms, much longer than the 0.58 us phase. The time-averaged flux is therefore the thermal load.

**Strip:**
- Passes in single-user decode: 0.92 W/mm2.
- Sustained 100% duty in scenario A would reach 3.92 W/mm2. That case needs a duty governor <= 0.48, or a measured MAC <= 1.92 pJ.
- A 0.9 GHz strip costs +14.0 us and still leaves 2.99 W/mm2. A deeper strip costs +20.7 mm2.

**PHY:**
- r1's 7.34 W/mm2 is **implausible**. Published host PHY energy is 0.29-0.8 pJ/b, which gives 0.21-0.58 W/mm2.
- The rest of the 10.19 pJ/b would be 22.8 W/mm2 in the controller band. That is 5.8x the densest logic, so it has no physical home there.
- Bounded by logic density, the band is <= 1.62 pJ/b and 0.86 W/mm2.

**Row-engine element P&R:** no change.

## Replay

```bash
(cd tests && python3 -m unittest test_qwen_rom_floorplan_nearhbm_r2 test_qwen_rom_floorplan_nearhbm -v)
(cd tools && python3 qwen_rom_floorplan_nearhbm_r2.py --verify && python3 qwen_rom_floorplan_nearhbm.py --verify)
```
