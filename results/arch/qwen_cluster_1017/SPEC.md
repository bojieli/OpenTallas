# Q-CLUSTER: `qfd_c_b16` / `qfd_c_b16_dv` cluster spec (deliverable 1, 2026-10-17)

Stream Q-CLUSTER (HANDOFF 0cm). It hardens the one cluster that the adopted Qwen compute die dv2r8f (Q-DV, `claude/qdv-1016`) places 48 times. The binding rules are the five die-standard items, neighbour-relative clocking, reach 405 with repeaters, FLOW-HOLD `hold_budget: die`, and the accelerator design principles.

Inputs (as read):
- the CB cluster `claude/q3h-cb-1016` e7e22d5b6: `q3h_cb16_gen.py` (sha256 9102246f…, copied here as `q3h_cb16_gen_cb.py`), `cluster_contract.json` and `cb16_hosts.json`;
- the Codex literal-clock candidate `codex/qwen-regional-2006` 44c0a5398, which has 859 clock ports. It is rejected as a spec (see §2);
- the A0 tile parent `qfd_tile_nk_romleaf_a0`, 457.92 x 1166.4. Q-ROMPARENT-2 owns it; it is not closed (c1r4 is in gates);
- the closed leaves romleaf, operand, rqr_half, node and lsl_fp1;
- `dv2r8f.json`. In it the clusters abut E-W at a pitch of 2,090.88, with 129.6-um band gaps N-S. The die is 26.87 x 23.99 mm, 644.5 mm².

## 0. What the cluster is (unchanged from CB)

The cluster is 4 x 4 A0 tiles, one reduction group:
- **Tree.** The exact morton pair tree (golden pairing; any nk tile may host any node; there is one nl tile).
- **Broadcast.** Four 516-b column words `bc0..3` (2,064 b, not 1,567 b) enter on the master S face. Each runs north through its column's tap corridor, with one `qfd_xcst_n` station per row. Each leaves on the N face as `bco0..3`, a registered feedthrough to the far cluster: 18 edges.
- **Reduction exit.** One 514-b exit `rs` on the S face.

Columns are L | c0 MY | A | c1 R0 | T | c2 MY | B | c3 R0 | R:
- A and B carry the tree (the tiles' W faces: n_a / n_b / t_out / n_y);
- L, T and R carry the column runs (E faces: tap, rst).

**DV variant `qfd_c_b16_dv`** = the same cluster plus a registered 514-b `rs_i -> rs_o` feedthrough:
- `rs_i` is on the N face; `rs_o` is on the S face, next to `rs`.
- It is used in the near clusters (bands 1 and 2). In the far bands, `rs_i` is tied to the instance's own `tie_lo` and `rs_o` is left open.
- There is one master, so the far bands also instantiate `_dv`. That avoids a second hardened master for 514 b of unused flops.

## 1. Corridor cut estimate (`corridor_cut.py`, results `cut_*.json/.txt`)

**Method.** Every bus is routed with the CB generator's own router and host map, so the legs are exactly the ones the RTL builds:
- tree legs, `rs` exit, the 4 bc->bco runs, reset, and (dv) the feedthrough;
- vertical wires only in corridors, horizontal wires only in row gaps;
- peak bits per 20-um bin.

**Capacity rules.**
- `proj` is the project die rule for channels (`qwen_tp8_1012/cuts.py`): verticals use M5 at 50% plus M7 at 75%. That is 1,434 tracks per 64.8 um.
- `m3` is a sensitivity case that adds M3 at 50%.
- CB's own 0.816 for corridor A counted M3 + M5 at 100%, which is not the project rule.

| case | A | T | B | L / R | worst (proj) | rs lat |
|---|---|---|---|---|---|---|
| CB as is (64.8 corridors), no DV | 2,570 b → **1.79** (m3 1.10) | 1,033 → 0.72 | 2,056 → **1.43** | 517 → 0.72 | **1.79** | 35 |
| DV feedthrough in T (Q-DV first idea) | 1.79 | 1,547 → **1.08** | 1.43 | 0.72 | 1.79 | 35 |
| DV split 2 x 257 into A/B (Q-DV recommendation) | 2,827 → **1.97** | 0.72 | 2,313 → **1.61** | 0.72 | **1.97** | 35 |
| **Adopted: A = T = B = 129.6 um, DV in T** | 2,570 → 0.90 (m3 0.55); trunk outside the pin zones 1,542 → 0.54 | 1,547 → **0.54** | 2,056 → 0.72 (m3 0.44) | 517 → 0.72 | 0.90 at the A pin zone only | 36 |
| same geometry, tree re-hosted for corridor load (annealed) | 0.72 | 0.54 | 0.72 | 0.72 | 0.72 | 45 |

Row-gap channels peak at 514 b (0.18) in every case.

**Findings.**
1. The corridor does **not** fit as drawn, even without DV. A and B are over capacity at 64.8 um under the project rule, and A is over at 1.10 even when M3 is counted. The peak is the tile-face pin zone: the n_a / n_b / t_out / n_y bands are stacked in y on one face, so every L1/L2 connection jogs vertically inside the corridor. Re-hosting the tree cannot get below 4 legs (2,056 b) in that zone (anneal, 6 seeds).
2. Q-DV's split into A/B is the worst option, at 1.97. Q-DV's corridor note also used bc = 1,567 b; the real load is 2 x 516 in T plus 516 each in L and R.
3. **Structural fix (adopted):** widen A, T and B from 64.8 to 129.6 um.
   - The cluster becomes 2,285.28 x 5,184 um (on the 0.432 / 2.16 grid). L and R stay at 32.4 um, so abutting neighbours form a 64.8-um channel (bc0 + bc3, 0.72).
   - The DV feedthrough goes in T. T's two 64.8 halves each carry one bc run, and the feedthrough sits between them.
   - Everything is at or below 0.72 except the A pin zone, at 0.90 proj / 0.55 m3, over about 400 um per row. We keep the CB host map (rs latency 36, versus 45 for the annealed map). If cluster GRT shows overflow there, the fallback is the annealed host map (`cut_dv_w3_annealed_util.json`, 0.72, +9 edges on rs). GRT overflow 0 is the gate; the cut is guidance.
4. **Cost.** The cluster pitch goes from 2,090.88 to 2,285.28 um.
   - The die gets 12 x 194.4 = 2.33 mm wider: 26.87 → 29.20 mm, which is under the 33-mm limit. Area goes from 644.5 to about 700 mm² (+8.7%). Area is cheaper than closure, and the result is still well under the reticle.
   - The slices must take the new pitch (Q-DV). The latency change is negligible (≤1 hop on lateral slice-row links).
5. **Rejected alternatives:**
   - band-gap M8/M9 overflight for b0/b3 rs: relay sites would sit only in row gaps 1,296 um apart, beyond the 600–750 um measured repeated reach;
   - a relay lane per quad edge: same die growth, but the feedthrough stays outside the tree;
   - L/R strips: 1.08 at 32.4 um.

**Feedthrough latency (for Q-DV's ledger).** The `rs_i` pin register is in the N strip, then 12 relays in T at ≤ 405 um (5,120 um between strip registers), then the `rs_o` pin register. That is **14 edges**, not 12. It is fixed and compiler-known: the far band issues 14 cycles earlier. bc->bco stays at 18 edges.

## 2. Clocks: four quadrant roots, registered seams only

- **Regions.** SW = c0-c1 / rows 0-1, SE = c2-c3 / rows 0-1, NW, NE. Each region is 1,142 x 2,592 um.
  - Each has its own clock pin and its own CTS net: `ck_sw` / `ck_se` on the master S face, `ck_nw` / `ck_ne` on the N face, each at the quadrant's centre x.
  - There is no cluster-wide root and no net spans 5.2 mm.
  - The T corridor's left and right halves belong to W and E respectively. The A and B corridors belong to their quadrant.
- **Sinks per quadrant.** About 17.6 k soft flops (70.1 k total: tree 35.5 k, runs 28.9 k, feedthrough 7.2 k, reset) plus 4 tiles x 27 A0 entry pins. That is above 15 k, so the measured form applies: insertion ≤ 300 ps and spread ≤ 80 ps at the gate.
  - If the gate fails, split each quadrant into its two tile rows. Each row then gets its own root, fed by a delay-matched trunk from the same pin.
- **Seams.** Only registered relay hops (≤ 405 um) cross a region seam:
  - the middle row gap (y ≈ 2,592), crossed by the bc runs, the feedthrough, the L4 leg and reset;
  - the T centreline, crossed by L3 legs and reset.
  - Pair check (die_clock_check method) on every seam pair: neighbour skew ≤ 80 ps at TT and FF. Hold on seams is fixed in the seam relay or in a die-net hold cell, never by padding tile pins.
- **Tiles.** Each A0 entry pin (ck, ck_rs, ck_rn, ck_rp*, ck_fa*, ck_lsl*, ck_node, as the closed A0 view declares) is a sink of its quadrant's net, balanced against the ETM pin insertion.
  - The Codex 859-port literal ABI is not used: it exports the cluster's internal clock structure to the die.
- **Die obligations.**
  - Four clock pins per cluster: S-face pins enter from the slice row or band gap, N-face pins from the band gap or the die edge.
  - dv2r8f has no margin above band 3 (cluster top = die top 23,986). The die needs at least 64.8 um there (+0.07 mm height).
  - The four pins of one cluster are a neighbour pair set: the delivered skew must be ≤ 80 ps after cluster insertion.

## 3. Reset

- One `rst_n` pin on the S face (T).
- The tree is pipelined with equal depth to every consumer (tiles' `rst_n` and the stations). There are 18 edges today; the count is re-derived for the widened geometry.
- Every stage is clocked by the quadrant root it sits in, and the hops are ≤ 405 um.
- The tree is synchronous and regional by construction. There is no async or flat reset net.

## 4. Pins: all registered, `hold_budget: die`

| port | bits | face | register |
|---|---|---|---|
| bc0..3 | 4 x 516 | S | entry flop in the S strip (flop-first) |
| bco0..3 | 4 x 516 | N | exit flop in the N strip |
| rs | 514 | S (A) | exit flop |
| rs_o (dv) | 514 | S (T) | exit flop |
| rs_i (dv) | 514 | N (T) | entry flop |
| ck_sw/ck_se, ck_nw/ck_ne | 4 x 1 | S, N | clock |
| rst_n | 1 | S | entry flop |
| cid 12, far 1 | 13 | S | static straps from the instance's own tie_hi/tie_lo: case-analysis constants, not timed |
| tie_hi, tie_lo | 2 | S | tie outputs |

Hold, timing and recipe:
- The spec carries `hold_budget: die`, flop-first entries and flop-last exits, with no inhold, outhold or hold pads, and boundary repair margin 0.
- Pins are on M5, at 0.192 pitch or coarser (≤ 6 pins/um). The S face needs about 3,100 pins (about 600 um at 0.192) on a 2,285-um face.
- The FLOW-HOLD launch/capture rule (input min = L_min + C + U) is checked by the native audit on the cluster view. Native launch ≤ 220, capture ≤ 190 and spread ≤ 80 are required before binding.

## 5. Layers

- The A0 children use M2-M7 (PG M7).
- The cluster owns M2-M7 in its corridors and gaps, plus M8 straps for PG.
- M9 is left to the die PDN and over-flight. dv2r8f puts no die signal bus over the clusters, only the cluster clock/reset pins.

## 6. Plan from here

1. Generate the cluster with the widened geometry and DV ports by extending the CB generator in this branch: a regional clock per quadrant, the feedthrough run, and pin ranges. Then a fabric bench (bit-exact against the reference tree, mutants).
2. Kit: ref_tile cluster spec, die_cluster boundary/snap legaliser, hard A0 children.
3. Gate: `--cts` measuring per-quadrant insertion and spread and seam pairs.
4. Route: `submit_exact`, then native audit.
5. The route waits for a CLOSED, native-PASS A0 view from Q-ROMPARENT-2. Steps 1-3 run against the A0 synth abstract as diagnostic only and are never bound.
