# FUSED csum tree + fus_hub (LEAD-HBM/LH-P3UNITS/FUSHUB, 2026-10-19)

Next-release HBM die at P = 3, DIE case `f4c_t9p3`. Branch `claude/hbm-next-units-fushub-1019`, based on the FUSED lane branch `claude/hbm-next-units-fusedsram-1019@f2bf7ac6a`. The lane RTL and lane kits are unchanged.

## Decision (LEAD-HBM/LH-P3UNITS, technical call)

The compiler allocator bank-aligns every FUSED.HC_PRE_NORM operand: its bank phase is ph = 0, where ph = VM word address bits [7:3] of A, B and O. With ph = 0, the fixed csum tree is exactly the golden chunk8 reduction order, so no runtime reorder is needed.

- **Why only ph = 0 works.** The golden sums chunk pairs (2c, 2c+1) level by level, with the even chunk on the left. Chunk u of a block is lane (u + ph) mod 32. A fixed physical tree pairs lanes (2c, 2c+1), so it pairs the golden chunks only when ph = 0.
- **The hub refuses ph != 0.** It faults the record before any lane activity.
- **HC_POST is unaffected.** It has no cross-lane reduction, so its ph stays free. The lane-local rule still applies: A, B and O share one phase.
- **Image check.** `tools/hbm_next/fused_phase_check.py` (rules F1-F4, with a selftest) rejects such records.
- **Current P3 images fail the check.** On the `claude/hbm-next-1019@4ce8d6df6` images (ar/mtp/mu L0-L14), every FUSED record fails: the PRE gain B is in HBM (F1), O is off A's phase (F2/F3), and POST C is not 8-aligned (F2). This matches the VEH 07:19 finding.
  - Record: `phase_check_p3_images_4ce8d6df6.json`.
  - The CMTP allocator owns the fix.

## Structure (`rtl/hbm_next/fused/ot_hnx_fused_tree.sv`)

The tree follows the DIE graph (`plan_p4.fused_graph`). Lane lid = 8 q + i, where i is the bank index in its bank pair.

| Level | Node (placed at) | a (lower lanes) | b (upper lanes) |
|---|---|---|---|
| 1 | n1[g], 16x (lane 2g) | lane 2g (abutted) | lane 2g+1 (stacked pair, 668 um) |
| 2 | n2L, 4x (group 0) | n1[0] (local) | n1[1] (g1 -> g0) |
| 2 | n2R, 4x (group 3) | n1[2] (g2 -> g3) | n1[3] (local) |
| 3 | n3 = quadrant node, 4x (group 3) | n2L (g0 -> g3) | n2R (local) |
| 4 | hub t4a / t4b | Q0 / Q2 | Q1 / Q3 |
| 5 | hub t5 | t4a | t4b |

**`ot_hnx_fused_tnode`** is one hardened view, used 28 times on the die and 3 times inside the hub.
- Pin flops on every input; outputs are flop Q.
- **Up path:**
  - It pads the EARLIER child by the difference of the two children's round trips. The pad depth and side are straps tied by the die binder.
  - Pad storage is a 1R1W 128x256 data ring plus a 32x64 control ring (up to 32 edges x 271 b = 8.7 kb), with a post-reset fill mask.
  - The aligned pair is registered.
  - Chunk sums go through one registered FP32 add (`ot_dsrom_qadd` LA 6, a + b).
  - Scalars, fin (AND/OR) and flt pass through one register.
- **Down path:** the parent bus (command 140 b + r 33 b) is re-registered into one KEPT copy per child, 2 edges per node.
- **Faults** (the `fl` bit, OR-ed up the tree to the hub):
  - a chunk sum on one side only;
  - two scalars on one edge;
  - a chunk/scalar output collision;
  - an adder flag.

**`ot_hnx_fused_hub`** is the logic of `ot_hnx_fused_top`, without the lanes:
- job decode, with the PRE ph = 0 check added;
- the scalar prologue, with **scb in a 1R1W 128x256 SRAM**. Before, it was a 48 x 256 b runtime-indexed flop array (SAFE-DESIGN item 5). The command bus gets one pipeline edge, so a WGT beat takes the macro's registered read issued on its own edge;
- the row-pipelined padded heap, unchanged;
- / D, + eps, rsqrt, and the r broadcast;
- t4a / t4b / t5 and the 4 quadrant down buses.

**Static schedule.** There are no credits, ready, FIFOs or arbitration.
- Lanes are not padded to lockstep. Lane L runs its whole calendar D(L) edges after the hub command. D(L) is a fixed per-bank offset handed to CMTP (below).
- The pads make every lane's round trip equal: scalar 113 edges, chunk 138 edges at E = 2. The bench top `$fatal`s if they are not.

## Hops per level (DIE f4c_t9p3, 405-um hops, centre-to-centre via the plan channel)

| Level / link | SW (q0) | NW (q1) | SE (q2) | NE (q3) | Landed |
|---|---|---|---|---|---|
| L1 lane pair (668 um) | 2 hops = 1 cyc | 2 = 1 | 2 = 1 | 2 = 1 | no |
| L2 g1 -> g0 | 8 = 4 + 3 | 11 = 6 + 3 | 8 = 4 + 3 | 8 = 4 + 3 | yes |
| L2 g2 -> g3 | 11 = 6 + 3 | 8 = 4 + 3 | 11 = 6 + 3 | 11 = 6 + 3 | yes |
| L3 g0 -> g3 | 17 = 9 + 3 | 17 = 9 + 3 | 17 = 9 + 3 | 15 = 8 + 3 | yes |
| quadrant -> hub | 17 = 9 + 3 | 17 = 9 + 3 | 19 = 10 + 3 | 18 = 9 + 3 | yes |

- A link costs ceil(hops / 2) cycles at forwarded half-cycle hops.
- A landed link adds 1 (ring) + E (handoff), with E = 2 assumed. The die STA sets the real E per link (LANDING-CONTRACT L5).
- There are 16 landed crossings.
- **Pads (edges):**
  - n1: 2 on a.
  - n2L: 14 / 18 / 14 / 14 on a.
  - n2R: 18 / 14 / 18 / 18 on b.
  - n3: 20 / 28 / 20 / 18 on b.
  - hub: t4a 4, t4b 4, t5 2.
- **Down offset D(L)** (hub command edge -> lane input), banks i0..7:
  - SW: 35 36 42 43 32 33 23 24
  - NW: 35 36 44 45 30 31 23 24
  - SE: 36 37 43 44 33 34 24 25
  - NE: 34 35 41 42 32 33 23 24

## Cost for CMTP

The changes against `ot_hnx_fused_top`'s RL = 4 star (WSC 26) are:
- **Scalar prologue:** WSC = 115 edges (+89).
- **r return:** the chunk path to the hub adds about +5 levels x (LA + 3) + 2 x links, offset by the old 5-level tree.

The row II is unchanged, because the tree is pipelined at one block every 4 (PRE) cycles. The measured c1 comes from bench t0 (pending).

## SAFE-DESIGN checklist (owner 10-19). Reviewed BEFORE the first gate.

### `hnx_fused_tnode_1019` (172.8 x 172.8)

| # | Item | Result |
|---|---|---|
| 1 | Pins registered, 2-stage reset landing | PASS. Every input lands in a pin flop: iac/iad/ibc/ibd, idv/idd, and the straps in pk_q/pb_q. Every output is a flop Q. `reset_landing` uses 2 stages plus `ot_rst_relay` REGIONS 4. |
| 2 | Reach <= 405 um a cycle | PASS. The tile is 172.8 sq, so every path is < 250 um. Die links are relay stations at 405 um, with landings between regions. |
| 3 | Fanout <= ~32 / kept copies | PASS. The down bus has one kept copy per child (`keep`). The strap selects are registered once, and the gate measures their fanout. Reset uses 4 relay regions. |
| 4 | Depth <= 600 ps | PASS-pending gate. SRAM rd -> select ends at the aligned-pair register. The add is the closed f12 l6 core. |
| 5 | Storage > 2 kb in SRAM | PASS. The 8.7 kb pad is in 128x256 + 32x64 1R1W macros. There are no flop delay lines >= 3 deep: the pad is the ring, and the add valid is a 6-bit vline. |
| 6 | Floorplan | Macros on the 43.2 lattice, >= 25.9 um from the pin faces, 45 um channel, one std band. Aspect 1. Utilisation is WAIVED: the tile is pin-limited, with 1,350 pins at 2.6/um per face, so the outline is set by the faces. |
| 7 | Clock | One small centre-fed root (~3k flops). io_hold_margin 0.03. The gate measures spread <= 80. |
| 8 | Static schedule | PASS. Pads and WSC are derived statically. Every added edge is listed above for CMTP. |

### `hnx_fused_hub_1019` (345.6 x 345.6, inside the 432 x 432 fus_hub reserve)

| # | Item | Result |
|---|---|---|
| 1 | Pins | PASS. Quadrant buses land in the hub nodes' pin flops, the job word in jq, wsc in wt. Outputs are flop Q: tnode kept da/db, done/fault/busy_q. busy is now registered (+1 edge). `reset_landing` 2 stages plus relay REGIONS 4. |
| 2 | Reach | PASS-pending gate. Logic sits between the W/E faces (345.6 um). The face -> node pin flops are at the face; the gate measures > 405-um stages. |
| 3 | Fanout | PASS. Reset uses 4 relay regions and each node has its own relay. The heap leaf hit decode drives 20 leaves (32 b each). |
| 4 | Depth | PASS-pending gate. The heap and tail are `ot_hnx_fused_top`'s closed-form cores. scb rd goes to one 2:1 half-select into a pipe register. |
| 5 | Storage | **FIXED**: scb (12.3 kb flop array) moved to a 1R1W 128x256 SRAM. The 3 node pads are SRAM rings. |
| 6 | Floorplan | 4 x 128x256 + 3 x 32x64 on the 43.2 lattice, with channels >= 34.8 um, >= 43.2 um from the W pin face and 69 um from N. Aspect 1, one std band. The outline is estimated (~35k std + 17.2k macros, util ~0.45); the gate's synthesis area re-sizes it. |
| 7 | Clock | One centre-fed root (~8k flops). io_hold_margin 0.03. The gate measures spread <= 80. |
| 8 | Static schedule | PASS. No credits or backpressure. The +1 command pipe, WSC 115 and the busy edge are handed to CMTP. |

## Benches (Verilator 5.050, fleet; `tools/hbm_next/hnx_fushub_bench.sh`, bench top `rtl/hbm_next/fused/tb/ot_hnx_fused_tree_top.sv`)

| Stage | What | Expect |
|---|---|---|
| t0 | PRE / POST, N = 1, 2, 3, 4, 6 at ph 0 (golden chunk8) | PASS 10/10 |
| phr | PRE N 4 at ph 3 must be refused (fault, 0 writes); POST N 2 at ph 5 is accepted | refuse 1, post PASS 1 |
| ref | `ot_hnx_fused_top` (rotating star) on the ph 3 / ph 5 vectors (shows the vectors are valid) | PASS |
| m4 | heap not cleared on consume | FAIL |
| m7 | hub accepts PRE ph != 0 | FAIL (mismatch: the fixed tree is not the golden order) |
| m8 | lanes 2 and 4 of q0 swap tree positions | FAIL (mismatch) |
| m9 | q0 n2L pad one edge short | FAIL (misaligned chunk sums) |

Status: see `lanes/LH-P3UNITS.md` and `pending_results.txt`. Witnesses go to `witness/` when the runs finish.
