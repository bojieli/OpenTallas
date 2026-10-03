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
