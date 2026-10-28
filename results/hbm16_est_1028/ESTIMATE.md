# HBM16-EST-1: 16-SM HBM die, one-page estimate (12.14b, analytic, 2026-10-28)

This is an estimate for a later owner decision. It is not a build and not a change to the release plan: the release keeps 8 SMs (OWNER 07:2x).
Base: today's 8-SM die plan C18 (`intel2:/srv/opentallas-scratch2/claude/hbm-streets2-1027/c18/die_plan.json`, B2o lineage, 88 partitions, 28.40 x 18.54 mm = 526.6 mm2).
Labels: CHECKED = read or recomputed from a plan or tool output. UNCHECKED = analytic or scaled.

## Verdict: NOT FEASIBLE on today's cores in one reticle; MARGINAL only after 3-4 structural shrinks

The binding problem is height: four of today's quad tiles in a 2x2 come to 28.4 x 38.1 mm = 1082 mm2, against a 26 x 33 reticle (858 mm2).
Removing the SM column channels fixes the width (25.5 mm) but not the height (38.1 mm).
See `hbm16_sketch.png`; the render was viewed.

## 1. Floorplan sketch and area (form A16 = 4 quad tiles in a 2x2)

Layout:
- N tiles mirror S tiles. There is one HBM3E PHY row per tile pair on the N edge and one on the S edge: 2 stacks per die, the same 1 stack per 8 SMs as today.
- The root/seam forms a centre cross.
- Each tile is [SM|spine|SM] / SU / band (hub, HC ring, IDX) / SU / [SM|spine|SM]. This is today's NW tile, identical masters, with orientations R0/MY/MX/R180.

Area budget at today's sizes (per-type outlines CHECKED from C18; sums UNCHECKED):

| item | mm2 |
|---|---|
| SM, 16 x 26.03 | 416.5 |
| tile services (hub 35.5 + HC 19.4 + IDX 11.2 + SU 25.7 + io 2.8), x 4 | 378 |
| tile spines, 21.3 x 4 | 85 |
| PHY rows, 2 x 58.9 (incl. 2 x 40.6 empty corners) | 118 |
| root + seam cross | ~80 |
| **total** | **~1078**, i.e. 126 % of the reticle |

What the reticle allows:
- Width: tile width must be <= (26 - 1.685)/2 = 12.16 mm. Today it is 13.36, so -9 %.
- Height: tile height must be <= (33 - 2 x 2.074 - 1.0)/2 = 13.85 mm. Today it is 16.47, so -16 %.
- SM rows take 9.02 mm of the tile height, so the SU + band stack must go from 7.45 mm to 4.83 mm (-35 %).

Shrink levers (all UNCHECKED):

| lever | saving (mm2) | notes |
|---|---|---|
| (L1) remove the SM column-broadcast channels or move them to over-SM M6/M7 | -52 | SM 5.77 -> 5.05 mm wide. Needs an SM-type re-sign: 512 half cores. |
| (L2) use the PHY-row corners | -40 to -80 | Corners are empty (fill 0.00). Move controllers/io/SerDes into them and lower the row. |
| (L3) repack services to ~0.65-0.70 hard fill | -40 to -60 | HC ring today 0.15-0.33 and track-bound; the W128 ring re-floorplan is owed anyway. SU rows are 0.36-0.44. |
| (L4) narrow the empty spines | -20 to -40 | 13.1 mm2 per tile of 0-cell corridors; needs over-SM feedthrough with bays in the SM channels. |

All four together give 850-930 mm2. The tile-height cut (-35 % on the SU + band stack) remains the open item.

## 2. Demand vs supply

- **Inside a tile: unchanged** (same masters).
  - B2 max face 0.69 and ft 0.79 including the die H-tree reservation, which locality-first removes.
  - C18 worst face is NW_hub|root at 0.97 (CHECKED from plan notes).
  - The hub is already hard at 8 SMs: straight hub cuts measured 1.7-3.3x over face capacity (DIE-HBM-6, 06:38).
- **Die-level traffic: CHECKED** from the C18 ports. Each tile exchanges 20.1k bits with the seam/root (NW: 10.5k out + 9.6k in; NE: 13.9k).
  - Today the hub abuts the root.
  - In a 2x2 the hubs sit about 8 mm from a central root.
  - One central root would therefore need a ~20k-bit vertical corridor per tile: at 3.6 b/um (6 pins/um x 0.6) that is 2.8-5.6 mm of corridor width. This is the mechanism that killed candidate A (spb/spu V 1.76, hub|su 1.9).
- **Locality-first fix (12.13): a distributed root.**
  - Each tile keeps a root slice beside its hub, as today: +13 to +26 mm2.
  - Tiles connect only by the VM/COLL ring (2.8k b/dir) plus control. A 1 mm seam then carries it at <= 0.6 (UNCHECKED).
- **Hops: UNCHECKED.**
  - Ring hops between tiles: N<->S ~14-16 mm = 35-40 hops; W<->E ~12-13 mm = 30-33 hops (405 um each).
  - Max die path is 59 mm Manhattan, against 47 mm today.

## 3. Cells vs the 400k cap

- Tile partitions are the same masters with the same core pieces, so every kit stays <= 400k cells (CHECKED: the C18 types are already built from hard cores; for example the hub is 157 cores, root 46 cores, 8.75M cells).
- Instances roughly double (UNCHECKED):
  - about 2,100 hard-core placements, against 1,063 today;
  - 512 SM halves.
- The distributed root needs about 4 root slices plus a small top tree (root/hc_eng/tkm are already split into <= 350k pieces).
- New work is the MX/R180 mirror pin tables.

## 4. Clock and crossings (UNCHECKED, scaled from LOCALITY-SCORE-2/3 HBM: 63 regions, 519 crossings, fish feed, count-aligned at D8, 0 failing)

- About 126 regions and about 1,040 crossings.
- Max hop chain about 15-16 instead of 12 (scaled by span).
- Per-crossing count-aligned margin is local, so it is unchanged (104-121 ps at D8, pending the MESO-COUNT-2 K fix).
- New risk: the 4-tile ring is a cycle through the centre cross. At least one inter-tile ring edge is off-feed (loop closing), so it needs a hop chain or a counted loop.

## 5. Token rate (pricer tools/hgi_sim/plan_study_price_1017.py, X 377.6 ns, run in docker on intel2)

Setup:
- Same per-class B2 stages for both dies; 16-SM = variant a/b (s 2, G1 192, 4 lanes); 8-SM = c_L4 (s 4, G1 384).
- Check: c_L4 reproduces the committed price_B2.json 1670.8 / 2840.0 (CHECKED).

| 16-SM case | AR tok/s | MTP tok/s | Qwen tok/s |
|---|---|---|---|
| 8-SM c_L4 (reference) | 1670.8 | 2840.0 | 908.3 |
| same stages | 1985.2 (+18.8 %) | 3362.3 (+18.4 %) | 956.1 |
| die classes x1.6 | 1948.7 (+16.6 %) | 3315.9 | 954.0 |
| die classes +24 cyc (VM_RING/COLL_RING/COLL_EP/HC_ENG; 2x2 root distance) | 1848.0 (+10.6 %) | 3163.3 (+11.4 %) | 948.2 |

- Applied to the release's safe-locality ~1700-1770 AR, a 16-SM die gives about **1880-2100 AR** (UNCHECKED ratio scaling).
- Dies: 192 instead of 384 (same 384 HBM stacks). Logic silicon is about 192 x ~860 = 165k mm2, against 384 x 527 = 202k mm2 (UNCHECKED).
- One-tier array fabric becomes easy at 192 dies. Today 384 dies need the TU single-lane port mode (HBM-NET).

## 6. Biggest risks and cost

Risks:
1. Tile height (-16 %, i.e. -35 % on the SU + band stack) does not fit without re-floorplanning the hub, HC ring and SU rows. The hub is already the hardest partition at 8 SMs.
2. Die-level traffic needs a distributed root (RTL delta: root split plus top tree, with LEC). A central root re-creates candidate A's 1.76 ft overload.
3. Yield and cost at full reticle (858 mm2) with 2 HBM stacks. The 4-tile ring creates an off-feed loop, and the die is 2x the cells for die GRT/STA, at the limits of what we have closed so far.

Cost after the release (UNCHECKED): about 300-450 lane-hours, roughly 2-3 weeks wall time with 5 lanes:
- plan/region map: 40 h;
- SM channel re-sign: 60 h;
- hub/HC/SU re-floorplan and kits: 120 h;
- root split RTL + LEC: 60 h;
- die GRT/STA/token: 80 h.

The estimate gate (12.14b) does NOT pass today. The next cheap step is a gen_arch `A16` variant at reticle with L1-L4, to measure G0C face/ft on paper (about 4 h).

Files:
- `st16_{same,pess,pess2}.json` (stage inputs);
- `price16_*.json` (pricer outputs);
- `hbm16_sketch.png`, `sketch.py`;
- `fill.py`, `traf.py` (plan readers).
