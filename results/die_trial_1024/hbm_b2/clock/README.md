# TRIAL-HBM step 2: die H-tree clock, B2r2 (OpenROAD build + STA)

The die H-tree in `physical/die_plan/hbm_arch/B2r2/clock_htree.json` was built in OpenROAD down to every partition
clock tap of `B2r2/die_plan.json`, globally routed, and timed at SS, TT and FF. There are no relaxed clocks: the period
is 833.333 ps, with 60 ps setup and 25 ps hold uncertainty, and `set_propagated_clock`. The plan was not edited.

- Generator and report: `tools/die_trial/htree_clock.py` (`gen` writes the case, `run.sh` runs it, `report` writes
  the JSON and PNGs).
- Files here:
  - `htree_clock.json`: all numbers.
  - `tap_latency.json`: per-tap insertion for each corner, and the partition means.
  - `htree_built.png`, `tap_latency_heatmap.png`.
- Run: epyc2 (dear-crayfish), `/srv/opentallas-scratch/claude/trial-hbm/clock/full`, launched with
  `ot-run --mem 64 --threads 16 --hosts epyc2`, unit `oth-ubuntu-479453-1792854815`, 2026-10-24 08:13:36-08:14:17 PDT.
  - GRT run: 37 s wall, peak RSS 8.3 GB.
  - STA runs (3 corners in parallel): about 3 s each, 0.3 GB each.
  - The full run took 41 s.
  - Logs, ODB and SPEF stay on the host. A copy is on localhost under the same path.
- Fast test first: the one-rib case `.../clock/rib3` on localhost (W rib of the lowest rib node, 32 leaves, 86 taps).

## What was built

| item | value |
|---|---|
| taps (exactly as g2.py die_probe: tap 0 + R4 grid + declared; 88 partitions) | **2045** (not ~980; 0 taps outside their partition) |
| H-tree | 8 levels, 510 segments; one BUFx24 per child at each branch node (point-to-point nets); repeaters BUFx24 at even cuts of <= 400 um; repeaters per segment by level 1..8 = 11, 5, 15, 7, 3, 2, 1, 1 (identical for every symmetric branch); 1392 tree buffers + 1 root buffer + 256 leaf drivers (BUFx24) |
| NDR | `CK2W2S`: width 0.08 (2W), spacing 0.32 so (w+s)/pitch = 5 tracks (2W2S + VSS shield each side), on all 1393 tree nets, M8/M9 only. The SPEF shows the 2W resistance is honoured (4.2 ohm/um). Shield coupling C is NOT modelled (layer C as is) |
| local nets | each tap is on its nearest leaf. Leaf driver -> 6-stage BUFx12f chain -> tap buffer (BUFx24 at the tap). Every chain is length-matched to the die max leaf->tap distance (1328 um) by a detour. Leaves are padded with dummy chain heads to equal fanout (23). 12270 chain + 3843 dummy + 2045 tap buffers; 19807 cells in all |
| routing | `set_routing_layers M8-M9` for all nets; die PG stripes (M8/M9, 0.48 / 8.64 / 4.32, VDD+VSS) as obstructions (10070). M1-M3 coarse tracks (9.6 um gcells). **No M1-M7 obstructions**: the buffer pins are on M1 and GRT models the via stack. The tree therefore does not use M1-M7, but the partitions' M1-M7 ownership is not checked |
| placement | cells sit at their coordinates (FIRM, no legalization, overlaps allowed: a die-size DPL grid is prohibitive). Node and repeater offsets are snapped to whole 9.6 um gcells (max node move 20 um; root moved 2.9/4.8 um to a gcell centre), and W/S-going cells are mirrored (MY/MX). See "modelling notes" |
| wirelength (GRT) | 3.19 m total: M8 1.05 m, M9 2.14 m. This is the H-tree's 0.49 m (geometric) plus the length-matched local chains' 2.72 m (the unmatched leaf->tap Manhattan sum is 1.39 m) |
| GRT overflow | **0 on M8, 0 on M9** (usage 0.06 % / 0.08 %), no errors. GRT-0037 "blockage outside die area" comes from PG stripes in the last partial gcell column (25194.24 is not a multiple of 9.6) |
| slew / cap | max slew 125.5 ps SS (tree), 93.6 ps (local). Lib limit 320 ps: 0 violations. Max cap: 0 violations. No repair_design / repair_clock_nets was needed or run |

## Insertion (ps, root clk port -> pin)

| corner | root -> leaf driver in (256): min / max / mean | root -> tap (2045): min / max / mean | leaf -> tap local: min / max |
|---|---|---|---|
| SS | 5317 / 5339 / 5327 | **5757 / 5829 / 5807** | 434 / 495 |
| TT | 4335 / 4355 / 4344 | **4679 / 4740 / 4721** | 339 / 390 |
| FF | 3663 / 3681 / 3671 | **3948 / 4000 / 3983** | 280 / 324 |

**Insertion vs the 250 ps common latency.** Insertion is 4.0-5.8 ns. That is about 16-23x the 250 ps common latency and
5-7 clock periods. A buffered M8/M9 NDR line in ASAP7 costs about 0.27 ps/um at SS, and the root-to-leaf path is 20.4 mm.
- The common part of the insertion cancels on synchronous seams, so it does not matter there.
- It does matter through OCV on the non-common path (next section).
- It also matters for any interface timed against an external or unrelated clock (die IO, PHY_N to the HBM PHY). Those
  see a 1.8 ns SS-FF insertion swing. That is not analysed here.

The die fabric STA should apply `tap_latency.json` as the per-tap source latency, on top of the partitions' 250 ps
internal latency.

## Skew (ps)

| corner | H-tree leaf skew (256 leaves) | global tap skew | local imbalance within one leaf | intra-partition tap spread (max) | seam skew, facing taps, no OCV (max over 225 abutted pairs) | seam with +/-5 % OCV, after CPPR (max) | seam pairs <= 80 ps with OCV + CPPR |
|---|---|---|---|---|---|---|---|
| SS | 22.1 | 72.0 | 56.5 | 63.3 | **54.5** | **594** | 36 / 225 |
| TT | 20.1 | 61.1 | 47.2 | 53.7 | **45.1** | **483** | 80 / 225 |
| FF | 18.1 | 52.8 | 40.5 | 46.5 | **38.5** | **407** | 93 / 225 |

- Seam pairs are partitions that share a face (from the plan rects), 225 in all. "Facing taps" means each tap in the tap
  row or column nearest the shared face is paired with the nearest tap of the neighbour. A hard core's single tap is
  used as is.
- `htree_clock.json` also gives the all-pairs worst (52 ps TT) and the result without CPPR (516 ps TT).
- CPPR credit is the common path up to the divergence pin: the driver of the LCA node's net, or the leaf driver output
  when both taps share a leaf.
- OCV: +5 % late / -5 % early on the non-common path. Skew_ocv = |dA - dB| + 0.05 x (non-common A + non-common B).

**Fraction of the 80 ps seam budget the die tree takes (no OCV): SS 68 %, TT 56 %, FF 48 %.** The partition-internal
face-flop spread comes on top of that. The R4 gate (CPPR skew <= 80 at TT and FF) passes only without OCV.

**With 5 % OCV it FAILS by about 6x.**
- The worst facing pair is NE_b112 | NE_hub. Its LCA is the die root, with 26.9 ps common path removed and 9.38 ns of
  non-common path. That pair tolerates only about a 0.38 % derate.
- By LCA level (TT, worst OCV+CPPR per pair):

| LCA level | pairs | OCV+CPPR range |
|---|---|---|
| 0 (root) | 4 | 475-483 |
| 1 | 42 | 384-406 |
| 2 | 4 | 335-351 |
| 3 | 2 | 202-206 |
| 4 | 42 | 131-155 |
| 5 | 35 | 96-130 |
| 6 | 27 | 73-106 |
| 7 | 51 | 56-87 |
| 8 (same leaf) | 18 | 35-74 |

  Only pairs whose taps hang off the same level-7/8 node pass.
- **Intra-partition:** every multi-tap partition (79) is fed by more than one leaf. Hub, b112, io and b013 straddle the
  root split (y = 9158), so their own taps diverge at the root: 522 ps TT with OCV.

Per the spec, hard cores (SM, PHY) take leaf delay = 250 - core lib insertion. **NOT APPLIED**: the plan declares no
core lib insertion (`q_sm*` / `PHY_N` clock: `insertion_ps` 250, one tap each). Their taps are timed like any other tap.

## Findings on the plan (numbers, not fixed)

1. **Leaf -> tap distance is up to 1328 um** (mean 679, p90 1051), against the spec's "<= 400 um local trees". The 16x16
   leaf grid (cells of 1575 x 1145 um) is too coarse for that claim. Each leaf drives 1-23 taps.
   - Balancing these local nets costs 2.72 m of M8/M9 wire.
   - Even balanced, they leave 40-57 ps of local imbalance. That comes from the detour approximation and the pin stubs.
2. **67 of 256 leaves drive no tap.** Most sit over the eight SM hard cores, each of which has a single central tap.
3. **The H-tree bands and tile halves do not follow partition faces.**
   - The trunk splits at y = 9158 (inside the hub / b1xx / io / b01x row), 4579 (inside the su2x / spu1 row) and 13738
     (inside the sm / spt row). Abutted partitions and even taps of one partition therefore diverge high in the tree.
   - The spec's "seam neighbours share the trunk, CPPR removes it" holds only for the NW_x | seam | NE_x pairs. It does
     not hold for the 225 in-tile faces: 46 pairs diverge at level 0-1.
4. **The rib and the level-4 inner child overlap.** The level-4 child next to the seam runs back along its own rib on M8
   (3149 um x 8 rib sides = 25 mm of doubled wire, and 2 x the reserved tracks there).
5. **2045 taps**, not the ~980 the brief expected: the R4 400 um grids of hub (143 per tile), mc (66), io (33), su/spu
   (24-28), and so on.

## What looks wrong (visual review of the PNGs)

- `htree_built.png`:
  - The tree itself is symmetric.
  - The orange local nets are long. They fan from leaves sitting in SM cores (grey) into the spb/spt and su columns, and
    from the leaves just outside the seam column into `root` / `vsN*`. A few span the full 1.3 mm cell diagonal.
  - About a quarter of the leaves sit idle over hard cores.
  - The level-3 ribs at y = 6878 / 11448 run through the hub and su rows, not along faces.
- `tap_latency_heatmap.png`:
  - The colour range is narrow: 72 ps at SS, 53 ps at FF.
  - Early (dark) taps are speckled through every partition. These are the taps closest to their leaf, where the
    length-match detour is imperfect.
  - No coherent W/E or N/S gradient is visible; the residual tree skew is about 20 ps.
  - The worst seam pairs (red) are all in the middle row (b112 / b113 / hub / io), where the root split runs. Their
    deterministic skew is small (35-55 ps), but with OCV it is 400-600 ps.

## Modelling notes and limits

- **Parasitics.** GRT estimate parasitics (`estimate_parasitics -global_routing`, setRC.tcl). There is no detailed route
  and no extraction, and the same RC is used at every corner.
  - The estimate adds a pin-to-gcell-centre stub per pin.
  - With the plan's raw coordinates these stubs drift by up to 0.1 kohm per stage. That alone faked 35 ps of H-tree skew
    in the rib test.
  - Snapping offsets to gcells and mirroring cells cut it to 6.5 ps on one rib and 18-22 ps on the full die. That
    residual is still estimate quantization (mirror nets differ by about 0.4 % in R), not topology.
- **Clock gating.** None. Every buffer is non-inverting, and only rising-edge arrivals are reported.
- **OCV.** The OCV numbers are computed analytically from the STA arrivals, not with `set_timing_derate` / CPPR in STA.

## NOT RUN

- Detailed routing / extraction.
- Hard-core leaf compensation (no core insertion in the plan).
- M1-M7 partition obstructions (dropped; see above).
- repair_clock_nets (not needed).
- Die fabric STA using `tap_latency.json` (lane owner).
