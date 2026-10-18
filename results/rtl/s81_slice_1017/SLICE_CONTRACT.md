# S81-SLICE: slice cluster contract (stream 0cm; p4c-lanes base)

Owner: S81-SLICE (slice integration and hardening). Architecture owner: S81-DV (`results/arch/s81_dv_1016/SPEC.md` sections 0a/0b).
Status: RTL in progress. Every latency below is a design value until a bench measures it.

## 1. Physical hierarchy

The slice is 0.95 x 4.6 mm: 5 beat leaves of 0.95 x 0.92 mm, stacked N-S. Leaf k owns elements [64k, 64k + 64) of the slice's 320.
Each leaf is a placement group of hardened sub-leaves. **Every sub-leaf has its own clock root.** Sub-leaves meet only at registered pins: flop-first inputs, flop outputs, recipe 4, `hold_budget: die`.

| Master | Count | Content |
|---|---|---|
| `ot_s81sl_vn` | 5 | h store (4 x 64 BF16), RMSNorm (`ot_hbm_norm_grp` G8 x 8 sub-beats), golden beat tree |
| `ot_s81sl_vq` | 5 | act-quant (`ot_dsrom_aq12`), q / BF16 x families |
| `ot_s81sl_vp` | 5 | leaf store (2 x 512x128), hc_post (16 x closed `ot_dsrom_su_hcpost_lane_pr`), command sequencer |
| `ot_s81sl_xr` (ring/control) | 1 (centre leaf) | ring stop E/W (+ V, + B on C3), ctl decode, command fan-out, partial collector, rstd fan |
| `ot_s81sl_xs` (x streamer) | 1 (centre leaf) | x buffer, slice-local phase / stream / calendar ROMs, static PQ stream path, x-chain words |
| `ot_s81sl_cap` (capture root) | 1 (centre leaf) | 8 return lanes, static return tree + root finish, tag decode, leaf capture writes |
| `ot_s81dv_xfin` | 1 (centre leaf) | S81-DV's exchange + replicated finish |

Slice variants (p4c): **C1** = E/W + V (14 slices); **C3** = C1 + B (s_1S, s_6S). They differ only in the `xr` master.
Cluster glue (soft) holds only registered relay stages between sub-leaves. It has no logic.

## 2. Die ports

Every 1,104-b port is 4 cycle-aligned 276-b lanes. Lane L carries bits [276L + 275 : 276L].
Each lane has its own forwarded-clock pin pair (`clk_in -> clk_out` arc, F1).
Slice ports are plain pin flops. The sink re-time is the die's last station on the slice root (DIE-CLOCK METHOD section 3).

| Port | Bits | Direction | Variant |
|---|---|---|---|
| ring E in / out, ring W in / out | 4 x 276 each | in / out | all |
| V in / out (tier exchange, void units) | 276 | in / out | all |
| B in / out (attention q, P.V) | 4 x 276 each | in / out | C3 |
| x chains (2 up, 2 down) | 4 x 276 each | out | all |
| return lanes (frame cfifo `rd`) | 8 x 70 | in | all |
| straps: slice id | 4 | in (pin flops) | all |

## 3. Ring beat (1,104 b; the V port uses the same 21-b header with a 255-b payload)

| Bits | Field |
|---|---|
| [0] | v |
| [3:1] | kind: 0 CTL, 1 XQ, 2 XB, 3 NX, 4 RD, 5 SC, 6 CL |
| [8:4] | hops remaining. The beat is delivered at every stop it reaches and forwarded while hops > 1. |
| [12:9] | source slice |
| [20:13] | idx (global beat 0..79 for XQ / XB, or a sub-type) |
| [1103:21] | payload |

Payloads:
- **XQ:** `{e1 10, q1 256, e0 10, q0 256}` (532 b, the `dsfd_pq_lx` q-family packing).
- **XB:** 64 x BF16 (1,024 b).
- **NX:** the xfin flit `{v, h4, b8, d 5 x 32}`.
- **CTL:** `[15:0]` slice mask, `[20:16]` target, `[25:21]` leaf mask, `[185:26]` body (160 b). Targets:
  - 0: vp command, to the masked leaves
  - 1: xfin go (`body[31:0]` = eps)
  - 2: streamer issuer / phase start
  - 3: capture phase config
  - 4: ring config (gather mode, inject)
  - 5: leaf-store row write `{a 10, m 4, d 128}`

Static schedule: nothing is arbitrated. A local inject in a slot the ring is forwarding is a sticky fault.

## 4. Sub-leaf interfaces (all single-clock; inputs land in a flop; outputs leave a flop)

### `ot_s81sl_xs` (x streamer)

| Signal | Width | Meaning |
|---|---|---|
| `g_v` | [2:0] | gathered beats this cycle: 0 = own leaf beat, 1 = arrived from W, 2 = arrived from E |
| `g_fam` | [2:0] | family per beat: 0 = q, 1 = BF16 |
| `g_idx` | [20:0] | 3 x 7-b global beat index |
| `g_d` | [3071:0] | 3 x 1,024 b |
| `is_v`, `is_d` | 1, [159:0] | issuer word `{... , slice ring-arrival offset, f_iss 93}` |
| `xw_v`, `xw_d` | 1, [1100:0] | one word stream: `{x2 536, cc 15, x1 266, x0 283, v}` (`dsfd_pq_lx` STATIC_X2); the glue fans it to the 4 chains |
| `fault` | 1 | sticky fault |

ROM images are identical in all 16 slices. The per-slice arrival offset is config, not image.
Bench: lockstep with the production PQ core + `dsfd_pq_lx` on the L0/L2 phases, bit for bit.

### `ot_s81sl_cap` (capture root)

| Signal | Width | Meaning |
|---|---|---|
| `rt` | 8 x [69:0] | frame return lanes (cfifo `rd` after the die re-time) |
| `cfg_v`, `cfg_d` | 1, [159:0] | per-phase return configuration (obase / ops / fmt / np / slice row base) |
| `cw_v[k]`, `cw_a[k]`, `cw_d[k]` | [1:0], [23:0], [63:0] per leaf k = 0..4 | capture word writes to the vp of leaf k: 2 ports, `{row 10, word 2}` addresses, data already rounded per fmt |
| `fault` | 1 | sticky fault |

Row segments of a slice's rows stay inside its 8 frames. The slice finishes partials with golden sibling adds: the static return nodes plus a root finish. A word whose row belongs to another slice is a fault.

### `ot_s81sl_vp` command word `c_d[159:0]`

`[3:0]` op, `[13:4]` a0, `[23:14]` a1, `[31:24]` n, `[159:32]` imm. The ops are listed in the header of `rtl/dsrom_sys/s81_dv/slice/ot_s81sl_vp.sv`.
