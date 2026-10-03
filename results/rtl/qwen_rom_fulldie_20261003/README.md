# Qwen3-8B ROM full die: hierarchical floorplan and die-level feasibility (2026-10-03)

This is a composition of black-box abstracts on the r2 near-HBM frame. It is not a routed die, has no extracted timing, and has no measured power. Replay is in `REPLAY.md`. Records are `floorplan.json`, `feasibility.json` and `clock_trunk.json`. `feasibility_r1_m5open.json` is the superseded first GRT series, kept as evidence.

## 1. Floorplan

| Item | Value |
|---|---|
| Die | 24,156.1 x 32,801.8 µm = **792.36 mm²**. Budget is 815 mm², so 22.6 mm² margin. The die fits 26 x 33. |
| vs r2 | +0.36 mm². The spine needs 1,223.9 µm, not 1,214.8, to pack its 32.32 mm² of slabs in two columns beside the centred link channel with both link channels crossing it. Link channels round up to 97.2 µm (45 rows). |
| Instances | 3,224 in total: 1,536 tiles, 1,536 corridor stations, 64 column heads, 24 row engines, 4 controller bands, 4 E/W PHYs (v2), 4 link FIFOs, 1 hub element, 19 spine slabs, 4 IO blocks, 28 link waypoints |
| Die nets | 3.46 M wires: corridor 0.98 M, tap 0.78 M, ME tree in-block 1.47 M, block words 49 k, head chain 41 k, links 34 k, strip fan 25 k, HBM read 27 k, DFI 37 k |
| Clock domains | stream 1.2 GHz: tiles, corridors, strips, hub element, links. serial 0.9 GHz: SU/SFU, VM side, reducers. HBM 976.6 MHz: controller bands and PHY DFI. See `domains.sdc` and the REGIONS/GROUPS in `floorplan.def`. |
| Crossings | X1-X3: ratio CDC at the hub. **H1-H24 (new)**: async FIFOs, controller (976.6 MHz) to each row engine; this moves r1's P1-P4 assumption. K1-K4: async FIFO for the KV write. M1-M4: mesochronous FIFOs at the strip end. L1-L2: plesiochronous IO links. |

Corridor-gate constraints are adopted (claude/qwen-corridor-gate @ 89e70dd78):

- **Centred pin row.** The station sits at tile mid-height, and the tap rows on both sides are centred on it.
- **Station frame.** 52.704 x 69.12 µm, which is at least the 17.28 µm slab.
- **No long haul on M2-M5.** In the bundled GRT these layers have adjustment 1.0.
- **Link stage pitch ≤ 430.56 µm.** Hub↔stack goes from 46 to **52 stages, +6 each way**. That is **+432 cycles/token (+0.36 µs)** to report to the model. Hub→IO goes from 31 to 37 stages; that path is owned by the all-reduce stream.

## 2. Feasibility

### (a) Floorplan, legality and pin access: PASS

Real ASAP7 technology, every macro placed through `ot_mts::place`:

- 0 overlaps, 0 outside the die.
- `OT_MACRO_TRACK_ASSERT PASS`: 7.17 M pin shapes checked, 0 off-track.
- `pin_access`: 131 unique instances and 1.76 M macro access points, **macroNoAp = 0**.

The pdngen macro-grid script failed (PDN-0217): the element abstracts carry no power pins. The die PDN is therefore defined and analysed through the per-region strap DEF of case (c).

### (c) IR drop, OpenROAD PSM

Setup:

- 2.5 x 2.6 mm windows, at the peak in-phase region densities.
- 45 µm bump array.
- The budget is 35 mV rail to rail (VDD drop + VSS bounce, the r2 basis).
- Interior cells only, at least one bump pitch from the window edge.

| Window | r2 PG (4.4 / 16.7 / 2.5 %), 1/4 VDD bumps | bump-aligned straps | aligned + all-power bumps over the core |
|---|---|---|---|
| tile field | 74-84 mV **FAIL** | 47 mV FAIL | **21 mV PASS** |
| spine/hub | 90-118 mV **FAIL** | 55 mV FAIL | **25 mV PASS** |
| shoreline (PHY bumps = signal) | 74-80 mV **FAIL** | 64 mV FAIL | 35.3 mV (fails by 0.3 mV; a2 pin_access macroNoAp = 0 on the constrained geometry) |

Coverage at 2x the r2 per-net figure passes everywhere: tile field 31-32 mV, shoreline 30-33 mV.

**Finding:** the r2 closed form (35 mV) misses bump-to-stripe crowding. PSM gives 2.1-3.4x that.

**Smallest fix:** align the M8/M9 lattice to the bump columns (+0.4 point of coverage: tile field 4.8 %, hub 2.7 %, strip 17.6 %) and make every bump over the tile field and spine a power bump. The ROM field has no off-die signals. This costs no die area and no routing tracks. At the strip beside the PHY, add 2x strip coverage (17.6 → 33 %), or power bumps over the controller band.

### (b) Global route, bundled k = 32 / 16, every die net

The r1 series left M5 open. The central tree top overflowed 653,621 there, while the banded variant had 0. That series is superseded.

Under the corridor-gate layer rule, at k = 32 with 5 iterations:

- **central tree top: overflow 5,367** (M9 4,216, M8 1,147), around the hub and tree top at the mid-line and in the spine link channel.
- **banded port slices: overflow 2,491**, all in the spine link channel (M9) and around one station.
- Corridors carry 45-47 % of M7 die-wide and fit. Their windows sit at 0.85-1.0 of netted capacity at k = 32 granularity.

The k = 16 runs are in progress (see `feasibility.json`).

### (d) Clock trunk

An H-tree to 1,580 leaves has 11 levels and a 25.6 mm root-to-leaf path. Insertion is 29 ns on the ASAP7 SS routed slope, 15.5 ns on the TT routed slope, and 3.8 ns on thick metal (150 ps/mm). At 5 % OCV:

| Wire model | Root-divergence skew | Synchronous region (≤ 60 ps) |
|---|---|---|
| ASAP7 SS routed slope | 2.9 ns | ≈ 0.3 mm |
| TT routed slope | 1.5 ns | ≈ 2 mm |
| thick metal | 0.38 ns | ≈ 5 mm |

**Verdict:** no single synchronous die tree is possible. Every bus crossing a top-level split needs a FIFO or a clock mesh: the head chain, block words and links at the mid-line and the spine. A tile-local tree plus the corridor-forwarded clock is consistent with the r1 mesochronous plan. The ME tree and block-word edges across rows need retiming at each hop.

## 3. Area and fit

The die is **792.36 mm² against 815 mm²**, a margin of **22.6 mm²**. The fixes above add no die area. The extra link stages cost 6 x 4 x 1,056 flops, about 0.011 mm².

Element P&R still needed (all black boxes here):

1. tile re-frame with the centred tap row and M8 tree pins
2. corridor station / head
3. row engine (claude/qwen-nearhbm-attn in flight)
4. hub element
5. controller band with H-FIFOs
6. link FIFO and waypoints at 430 µm
7. spine slabs: port, scale ROM, VM, SU/SFU, tree top
8. IO band (collective, embedding ROM, UCIe, SerDes)
9. the H-tree / mesh clock spine
