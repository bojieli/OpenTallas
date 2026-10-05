# Qwen ROM near-HBM corridor routability gate (r2 floorplan)

Question: do the r2 corridors (results/uarch/qwen_rom_floorplan_nearhbm_20261003/model-r2.json) route at
0.39-0.43 of the raw same-direction tracks on their assigned layers? The only earlier routed bus passed at 0.225.

Method (tools/qwen_corridor_gate.py; RTL rtl/chip/physical/qcg/, hooks physical/qwen_corridor_gate/):
- Flow: ORFS through tools/run_abi3_physical_persistent.py. SS (WC) primary corner at 0.833 ns with 60 ps setup
  uncertainty. Repair at WC and BC with 25 ps hold uncertainty. Route M2-M9 with the platform's 0.25 layer adjustment.
- A, link span: 504 um and 1,056 signals. Station flop banks (8.64 um slabs) sit at both ends, with 4 BUFx4 repeater
  slabs between them (7.71 per wire-mm). Long haul runs on M6/M8. `A_tile` uses the r2 tile-field PG (4.4% per
  net on M8/M9); `A_strip` uses the strip PG (16.4%).
- B/C/D, tile column: one tile pitch (1,291.68 um) and 637 signals. Stations sit every 430.56 um with 3 repeaters per
  segment, and the entry station taps a 637-pin tile-edge row on M4/M6. Long haul runs on M7/M9 with tile-field PG.
  - B: the pin row is one-sided, above the station.
  - C: the pin row is centred on the station.
  - D: like C, with a 17.28 um station slab, needed below the r2 width.
- PG: the repo die grid (pdn_die.tcl) carries the r2 M8/M9 coverage, built from 0.444/0.476 um stripes (MAXWIDTH
  2 um). The M6-M9 stack connect replaces the parallel M6-M8 connect.
- Layer assignment: global-route capacity on the non-assigned same-direction layers is zero between slabs. A per-layer
  audit of the routed DEF requires 1% or less of the between-slab wire on those layers.
- Timing: OpenSTA on the RCX SPEF at SS and at FF, separately.

Routability (GRT overflow 0 and DRT 0 violations; `verdict.json`):

| Series | Densest clean ratio | First failing ratio | r2 ratio |
|---|---|---|---|
| A_tile, horizontal link | 0.547 | 0.600 (GRT 3,984) | 0.388 |
| A_strip, link under strip PG | 0.448 | 0.500 (GRT 14) | 0.388 |
| D/C, tile column, centred pins | 0.546 | 0.596 (GRT 10) | 0.430 |
| B, tile column, one-sided pins | 0.300 | 0.430 (GRT 24, tap fan-out zone only) | 0.430 |

Every clean run converged to 0 DRT violations, and every one held the layer assignment except C_tile_r0362. That run
routed clean but put 2.0% of its between-slab wire on M3/M5, a wide-corridor artifact. Two other wide reruns
(B_tile_r0362 and D_tile_r0362) behaved anomalously and are not used in the bracket.

Die: with the routable ratio of about 0.546, every r2 width routes. Widths are never narrowed, so the die stays at
792.0 mm2 and 815 holds. If the tile pin row stays one-sided (B), the tile corridor needs 0.30, which gives
840.1 mm2 and does NOT fit 815.

Timing (not part of the routability gate):
- FF hold is met everywhere.
- SS setup on the 504 um link span misses by 29-79 ps on 1-4% of endpoints. Each BUFx4 stage on M6 costs about
  135 ps per 100 um, so the measured reach is shorter than the r2 504 um.
- The 430 um tile segment at r2 width (D_tile_r2) closes, at +11.9 ps.

Attempts that failed because of the harness or the host are kept as `*_attempt*.json`: hard blockages, RSZ-3006 on
dont_touch repeaters, OOM kills, and station slabs too small for the cells. `*_frozenrep` runs kept the repeaters at
BUFx4 for the whole flow; `*_released` runs handed them to the resizer at PRE_RESIZE.

Replay: `python3 tools/qwen_corridor_gate.py argv --variant D_tile_r2 --jobroot <dir>` gives the launch line;
`record` and `summary` rebuild the records and `verdict.json`.
