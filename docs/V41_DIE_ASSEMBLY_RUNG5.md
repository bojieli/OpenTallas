# V4.1 die assembly (rung 5): first die-level global route

Workstream W3 of [INTEGRATED_PHYSICAL_PLAN.md](INTEGRATED_PHYSICAL_PLAN.md). This page asks whether the V4.1 ROM layer die and the V4.1 HBM-only comparator die compose on one 815 mm² die. It checks that the clusters fit the root reservation plan, that the channel nets between them route, and what each crossing costs in registered cycles. It is the first die-level result for V4.1. The clusters are **placeholders** sized from source-pinned ledgers. W1's bank map and W2's hardened abstracts will replace them, so no rate or headline changes here.

## Method

- **Hierarchical, never flat.** Each cluster is a black-box abstract, and the top level holds only channel nets. The previous attempt (`ot_chip_v41x_pdie` on ot-pve2, container `85dbe72b1713`) flattened the monolithic K arbiter and KV prefetch into the die top. It then spent 24 h in yosys, the last 3 h inside a single ABC call on a 1.45 M-gate netlist (188 MB BLIF), without finishing. It was stopped on 2026-09-29 and is not resumable.
- **Floorplan.** It follows `results/floorplan/v41_reservation_plan.json`: four compute regions, the two transport channels, HBM/controller strips on the north and south edges, and link strips on the east and west edges. The PHY rects come from the analytical assembly: 4 × HBM3E 12.0 × 0.8335 mm, UCIe-A 1.043 × 6.61 mm and SerDes 1.0 × 18 mm. Each region holds one hub strip facing the vertical channel and 12 ROM/MAC tiles (4 × 3).
- **Cluster sizes.**
  - ROM die: tile content is 10.01 mm². That is the stage-17 ROM reservation (13,296 × `ot_rom_8192x274_m8`, 199.47 mm²) plus the pooled engines (281.18 mm², ledger `placed_mm2`), divided by 48.
  - HBM die: tile content is 6.06 mm². That is the engines divided by 48, plus 0.2 mm² of assumed weight staging.
  - Each hub is 18.8 mm²: the ledger's vector, select, Sinkhorn and VM rows divided by 4.
  - The HBM service strips (12.0 × 0.30 mm), the attention+index cluster (2.4 × 1.7 mm, placed in the gap between the two PHYs) and the collective are explicit placeholders.
- **Edges.** Each connectivity-ledger edge becomes a top-level bus at its ledger width:
  - `vm_me` + `vm_he` = 384 bits to each tile;
  - `hbm_window` 256, `selected_kv` 32, `vm_pv_preload` 128;
  - `vm_collective` 512 and `collective_vm` 2,048 per hub.

  Index keys run at the measured reader rate: 557,056 sectors in 9,278 cycles is 15.01 sectors per cycle per stack, which gives 3,840 bits per stack. Widths the ledger does not give are marked ASSUMED in each record:
  - tile result, 512 bits;
  - hub ring, 512 bits;
  - attention output, 512 bits;
  - link flits, 512 bits.

  On the HBM die, each stack streams weights to the 12 tiles of its adjacent region. That is 3.6 TB/s per die ÷ 4 stacks at 1.087 GHz = 6,624 bits/cycle per stack, or 552 bits per tile.
- **Bundled global route.** OpenROAD GRT fixes its GCell at 15 routing pitches. On ASAP7 that is 0.54 µm, so a full die would need 2.8 × 10⁹ GCells. A 2 × 1.6 mm test already took 11 GB, and a full-die attempt was stopped at 157 GB.
  - The die route therefore scales every routing layer's pitch, width and spacing by k = 32, and routes each bus as ⌈bits/32⌉ bundle nets. Per-layer track capacity through any channel is preserved exactly. The GCell becomes 18.5 µm.
  - Clusters obstruct M1–M7, so only M8/M9 are free over them. M8/M9 keep 30 % in reserve for the die power mesh, and M2–M7 carry the platform's 0.25 derating.
  - A no-net baseline run is subtracted, so the congestion map shows only wire demand.
  - Pins are placed per instance on the edge facing each peer, centred on the peer's projection and then legalised.
  - A k = 16 run checks that bundling does not change the answer (below).
- **Channel timing.** Each bus's worst routed length is priced with the routed ASAP7 wire fit. That fit (`floorplans.wire_delay_model()`, from the express-link routes) is 0.5997 ps/µm plus 189.5 ps, at 920 ps with 60 ps uncertainty, giving a reach of **1.118 mm per cycle**. `crossing_cycles` = ⌈L / reach⌉ and `pipeline_registers` = cycles − 1. Both are compared with the analytical `long_wires` budgets in `results/arch/v41_die_assembly.json`. The clock is regional with mesochronous crossings, following that record's clock verdict, so no single tree sits on these paths.
- **Real-technology corridors.** `tools/chip_assembly/v41_corridor.py` builds a channel strip in real ASAP7. It places register stations at three spacings, then runs `repair_design`, GRT, `repair_timing` and STA on global-route parasitics. This checks the reach the die route assumes.

## Results

Records are in `results/physical_abi3/asap7/chip/dies/v41_{rom,hbm}_<variant>_grt.json`, each with an SVG congestion map. Each record pins the sha256 of every input, the tool and the git commit.

| Design / variant | Bundle nets (wires) | GRT overflow | Worst window utilisation (layer) | Windows > 0.8 | Peak RSS |
|---|---|---|---|---|---|
AS_BUILT_ROWS
| ROM, proposal (2 attention, 1 collective at channel crossing) | 2,396 (76,672) | **0** | 1.0 (M4–M8, tile-gap pin windows) | M4 214 · M5 370 · M6 291 · M7 375 · M8 171 | 2.8 GB |
| HBM comparator, proposal | 3,260 (103,168) | **0** | 1.0 (M4–M7) | see record | 2.8 GB |
| ROM, 2 attention + 2 collectives at the link strips | 2,428 (77,696) | **0** | see record | see record | 2.8 GB |

Per-edge crossing cost for the proposal variant, from worst routed length to cycles at 1.118 mm per cycle, against the analytical charged cycles:

| Edge class | Wires | ROM worst mm → cycles | HBM worst mm → cycles | Analytical budget (path, cycles) |
|---|---|---|---|---|
| hub → tile operands (`vm_me`+`vm_he`) | 18,432 | 11.62 → 11 | 11.53 → 11 | pool_operand_in, 20 |
| tile → hub results (ASSUMED 512) | 24,576 | 11.72 → 11 | 11.61 → 11 | pool_result_out, 20 |
| HBM stack → tile weights (HBM only) | 26,496 | – | 10.79 → 10 | none in the analytical ROM model (kv_static_rows 14 used) |
| hub ↔ collective (`vm_collective`, `collective_vm`) | 10,240 | 0.43 → 1 | 0.43 → 1 | collective_edge, 13 |
| collective ↔ UCIe / SerDes (512 each way) | 2,048 | 14.62 → 14 | 14.62 → 14 | collective_edge / stage_hop_edge, 13 |
| HBM → attention (`hbm_window`, index keys, `selected_kv`) | 17,536 | 0.32 → 1 | 0.32 → 1 | kv_static_rows 14 / kv_gather_request 16 |
| hub → attention (`vm_pv_preload`, q) and output | 1,792 | 2.91 → 3 | 2.91 → 3 | pool_operand_in / pool_result_out, 20 |

AS_BUILT_TIMING

CORRIDOR_RESULTS

K16_CHECK

## What composes and what does not

- **Routability is not the constraint.** Neither design overflows. Die-level wire demand is 1–3 % of the free resource. The only saturated windows sit at tile-gap pin-access points (136–149 µm gaps between tiles), which the corridor runs check in real technology. The 75–105 k inter-cluster wires fit in the reservation plan's channels and over-the-cluster M8/M9.
- **Tiles fit, with thin gaps.** The tiles fit the reservation regions at 91.6–91.9 % slot fill. That leaves 131–149 µm gaps between tiles, and those gaps carry the operand and result buses. The UCIe-A published depth (1.043 mm) overruns the 1.0 mm east link strip by 43 µm, so the strip must widen.
- **Latency is placement-bound, not wire-bound.**
  - With the RTL's counts placed as-built (one attention path, one collective at the east link strip), the north stacks' KV and index traffic crosses the die, and every collective and link path detours to the east edge. The as-built rows above give the cycle costs.
  - Moving the collective to the transport-channel crossing and giving each HBM edge its own attention+index cluster brings every KV edge to 1 cycle and every hub↔collective edge to 1 cycle. The remaining long paths are the link flits (14 cycles, 1 over the analytical 13) and the hub→far-tile operand and result paths (11 cycles, under the analytical 20).
- **The collective is pin-limited when it sits at an edge.** Four hubs × 2,560 wires enter one 0.44 mm-tall cluster. It must grow to 0.547 mm, and its approach through the 100 µm gap to the region-3 tiles is the as-built congestion site. At the channel crossing the same wires arrive on four sides, at 0.43 mm.
- **Not yet shown:**
  - detailed route;
  - extracted timing of real cluster boundaries;
  - IR/EM (the PDN here is a capacity reservation);
  - pin access below bundle granularity;
  - the attention/HBM-service/collective contents (placeholders);
  - the HBM comparator's weight-staging area, which is assumed.

## Proposal for root: collective, controller and router counts (discrepancy D1 / plan finding #2)

The analytical ledger has 8 one-shot engines of 128 lanes, 2 package controllers and 4 fabric routers per die. The die RTL has 1 engine of 16 lanes × GW4 (64 FP32 lanes), 1 controller and 1 three-port router. The die route shows that **count does not set the on-die collective latency; placement does.** The VM-to-link path is bounded below by the hub-to-link-PHY Manhattan distance wherever the engines sit. Engines at the edge turn that distance into wide 2,560-wire-per-hub buses. Engines at the channel crossing turn it into 512-bit link flits. Proposed:

1. **Collective engines: one logical collective at the transport-channel crossing, adjacent to all four hubs.** Size its lane count from the executed collective schedule, not from the ledger's 8 × 128. The RTL parameter is `CL_LANES`, and the C7 exposure result (`results/arch/v41_collective_exposure.json`) is the input. The physical cost of more lanes at the crossing is small: 4 × `CL_LANES`/16 × 2,560 wires over less than 0.5 mm. At an edge the same lanes would cost 20–28 mm each, so the ledger's edge placement should not be adopted.
2. **Fabric routers: one per link-PHY strip the die terminates.** That is 2 routers: east UCIe-A (package peer) and west SerDes (stage hop and switch). Each sits at its strip and connects to the collective over the 14-cycle link-flit channel. The ledger's 4 has no port that justifies it in this floorplan.
3. **Package controller: 1 per die, as in the RTL.** The ledger's second controller has no separate endpoint in the reservation plan.
4. **Attention/index: 2 clusters, one per HBM edge.** This removes the 25–32-cycle cross-die KV and index-key haul. It needs a KV layout decision: stripe CKV and index keys across the two stacks of an edge instead of all four, and split the context between the two clusters with a softmax-partial merge. The merge is one small exchange of (m, l, acc) per head over the hub path. It must be proved numerically before adoption.

Root decides. W3 will re-run these cases with W1's inventory and W2's abstracts as they land.

## Reproduce

```
python3 tools/chip_assembly/v41_die.py write --arch v41_rom --n-attn 2 --coll-place center --work W
# or: v41_die.py run ... (runs W/run.tcl and the no-net baseline W/run_base.tcl in the ORFS image)
python3 tools/chip_assembly/v41_die.py record --arch v41_rom --n-attn 2 --coll-place center --work W --tag a2cc
python3 tools/chip_assembly/v41_corridor.py write --work C --length-mm 3.4 --width-um 140 --wires 300 --min-layer M4 --rc-layer M5
```
