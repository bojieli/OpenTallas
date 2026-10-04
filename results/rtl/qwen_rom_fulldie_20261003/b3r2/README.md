# Qwen3-8B ROM full die: b3r2 congestion closure attempt (2026-10-04)

Tool: `tools/qwen_rom_fulldie_b3r2.py` (default off; `tools/qwen_rom_fulldie.py` is unchanged). Tests: `tools/test_qwen_rom_fulldie_b3r2.py`.
Remote cases: `ot-epyc1tb:/srv/opentallas-scratch/claude/qwen-fulldie/cases/b3r2*`. Every case manifest carries `source_commit`.

## Verdict: congestion NOT closed. The 50-iteration final run was not launched.

The b3r2 source builds on the Codex b3 selection (`tools/qwen_rom_fulldie_b3.py`):
- F1 and F2: corridor 637 → 388 bits, tap 511 → 325 bits.
- The spine channel VCH widens from 174.096 to 260.064 µm.
- The south link is split over both channel edges.

It adds the following:
1. **Real signal pins** on the ten abstracts that were signal-empty and refused by `b3_launch_r2`. The interfaces are taken from the RTL port lists:
   - scale ROM, for each result-port group: gre 1 + addr 24 in, q 256 out;
   - constant ROM: re 64 + addr 64×24 in, q 64×64 out;
   - sequencer: ib 379 + 3 to the x root, the non-ME ISA fields + 2 to SU64, a collective descriptor 66, and ME/SU done.
2. **The port-group → slab map.** b2/b3 connected `bword_<blk>` to slab pin `bw{blk%16}`. That puts 48 block words on a pin shared with another word, so b2 under-routed the block-word bus.
3. **Clock regions from decision C**, with the 2.53 mm² of FIFO slots counted in the area.
4. **Optional `--band` re-pack.** The port and scale slabs sit next to the block-row band they serve.

### Global route, k = 16, banded tree top (overflow = GRT "Total Congestion"; use/cap = worst 4 × 4-gcell window)

| case | total | M4 | M5 | M6 | M7 | M8 | M9 | max use/cap M7 / M8 / M9 | M9 windows > 1 | GRT s |
|---|---:|---:|---:|---:|---:|---:|---:|---|---:|---:|
| b2_k16_banded_i5 (before) | 36,383 | 0 | 7 | 0 | 6 | 1,239 | 35,131 | 1.01 / 0.95 / 1.29 | 160 | 2754 |
| b2_k16_banded (50 it) | 37,200 | 0 | 9 | 7 | 13 | 3,883 | 33,288 | 1.01 / 1.17 / 1.28 | 94 | 26005 |
| b3r2_k16_banded_i5: (a)+(b)+(c) as specified, real pins | 1,159,067 | 1,384 | 142,592 | 1,389 | 452,400 | 17,755 | 543,547 | 3.40 / 1.97 / 2.23 | 15,857 | 7803 |
| **b3r2b_k16_banded_i5**: + band-local slabs | **54,584** | 231 | 82 | 116 | 447 | 2,226 | 51,482 | 1.06 / 1.31 / 1.17 | 108 | 1954 |
| b3r2c_k16_banded_i5: + M8 area pins (rejected) | 265,746 | 0 | 17 | 20 | 39 | 15,019 | 250,651 | 1.03 / 1.59 / 1.89 | 4,264 | 2367 |

**Reading.**
- **The b2 baseline is not a like-for-like "before".** It routed neither the scale ROM, constant ROM nor sequencer interfaces (the abstracts had no pins), and it dropped up to 48 block words.
- **The real interfaces cost about 33k bits.** Scale is 96 × 281 = 26,976 bits, crom 5,696 and sequencer about 600. With the b2/b3 slab packing, the scale ROM slabs sit far from their port slabs, which multiplies the overflow 32×.
- **The band re-pack is required, but not sufficient.**
  - It cuts the spine vertical demand at y = 8.8 mm from 35,840 to 8,907 bits (`plan_b3r2b/plan.json` spine_vertical_cut_bits).
  - It drops the worst M9 window from 1.29 to 1.17 and the over-capacity M9 windows from 160 to 108.
  - The GRT gcell overflow still rises to 54.6k. It is spread over slab faces and the hub/tree-top rows (y 12–20 mm), where bands 2–3 are displaced 2–4.7 mm by the central blocks.
- **M8 area pins (b3r2c) are 5× worse.** Pin access on M8/M9 over the slabs consumes the layers that the long spine nets need. That variant is rejected.

### Area
- **Die.** 795.977 mm² (24,266.304 × 32,801.76 µm) against the 858 mm² limit, a margin of 62.0 mm².
  - That is +3.61 mm² over b2's 792.364 mm².
  - VCH 260 adds 2.82 mm². The band re-pack widens the spine by 24 µm, adding 0.79 mm².
- **Mesochronous FIFO slots (decision C), 2.53 mm² in total.**
  - Tile-tap FIFOs: 2.374 mm², inside a station frame grown from 69.12 to 103.68 µm (together with the F2 storage, 320 b a station, 0.373 mm²).
  - Block-word FIFOs: 0.149 mm², in the port slab area.
  - Strip-return FIFOs: 0.0066 mm², in the strip FIFO frame.
- **Clock regions.** There are 120: 96 tile blocks of 4 × 4 tiles, 6 spine bands, 12 strip thirds and 6 IO regions.
  - 34 regions are 5.264 mm against the 5.25 mm extent: the tile blocks and spine bands of rows 4–7 and 16–19, which contain a 97.2 µm link channel.
  - This exceedance is reported here, not hidden.

### Latency (`latency_f2.json`, unified-model probe)
- **F2 two-beat instruction.** +1 cycle on each of the 217 ME ops on the token path: **+217 cycles a token, 0.181 µs, −0.121 % rate** (6,674.8 → 6,666.7 tok/s). This is the bound until the RTL prefetch into the 2-deep column FIFO is measured; with prefetch the cost is 0.
- **F1 reset.** 0 cycles a token.
- **Geometry finding: the block-word path is longer than the model.** Worst block-word → tree-top path at a 430.56 µm stage pitch:
  - b2 geometry: 101 stages;
  - b3r2 (no re-pack): 117 stages;
  - b3r2b: 68 stages.
  - The model's `QWEN_WIRE_W12.tws = 30` is therefore optimistic for every built floorplan and must be re-derived.

### Physical checks at the b3r2b floorplan
- **Real technology (`b3r2b_pdn/run.log`).**
  - OT_LEGAL: 3,243 instances, 0 overlaps.
  - OT_MACRO_TRACK_ASSERT PASS: 5,848,824 pins, 0 off-track.
  - pin_access: macroNoAp = 0.
  - Wall 14:31, 11.0 GB RSS.
- **Full-die PDN** (power abstracts with VDD/VSS M7+M8 rails on every element; 3,239 bump-aligned macro grids at a 63.64 µm per-net bump pitch):
  - `run_pdn.log` failed with PDN-0217. pdngen treats `-instances` as a pattern, so t_0_1's grid claimed t_0_10.
  - This was fixed by ordering the grids longest name first, and rerun as `run_pdn_r2.tcl`. That run was still running single-threaded when this record was written; see the remote STATUS.md.
- **IR (PSM)**, with the PASS recipe of b2: aligned straps and every core bump power. Budget 35 mV rail to rail; interior rule = cells at least one bump pitch from the window edge. Record: `ir/ir_record.json`.

| window | b3r2b interior rail to rail | b2 (same recipe) |
|---|---:|---:|
| tile field | 21.03 mV PASS | 21.03 |
| spine/hub | 28.47 mV PASS | 24.63 |
| shoreline W | 20.26 mV PASS | 25.47 |

### What would close it (not attempted; each needs pricing first)
- Give the hub-row bands 2–3 their own slabs: move the central blocks off the W mid column, or widen the spine about 0.5 mm (about 16 mm²).
- Narrow the scale interface by moving the scale ROM into the port slab, which makes it port-local.
- Route the crom bus locally by placing the constant ROM beside SU64.
