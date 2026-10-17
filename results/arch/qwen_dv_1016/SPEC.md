# Q-DV: distributed-vector Qwen3-8B TP8 compute die — spec and priced cost (deliverable 1)

Stream Q-DV. Owner approved it 2026-10-16 ~22:00 (HANDOFF 0cj). Binding principles: memory accelerator-design-principles-1016.

**Status:** evaluation model only. There is no RTL and no GEN yet. Every figure here is a relay-skip planning model built on the q3h final corrected graph and judged with the same metrics as Q-DIEPLAN3 and Q-VMSLICE:
- bit-mm and stages: dieplan2 `metrics.py st()`;
- cut: main `results/arch/qwen_tp8_1012/cuts.py` (CAP_MODE v3, CLUSTER_PLAN M6, `qfd_c_b16` as a cluster);
- price: `tools/throughput/accepted_cost.py compute qwen_rom --node-delta`.

GRT and die STA decide routability and timing; this model does not.

## 1. What changes

The q3h die has one star. 48 cluster words (514 b each) run to 6 port-tile halves in the centre. They pass 3 half-band lane blocks and 6 half result trains, then reach one 15.8-mm² VM. That VM feeds one 11.9-mm² SU64 over an 8,511-b seam, which gives the full-demand cut of 1.435. Around the VM/SU sit seq_su, xs_tap, native59, 16 constant groups and the tree top.

DV removes all of these. In their place it adds:

| new block | n | size (um) | function |
|---|---:|---|---|
| `qfd_dv_redstn` (dvr) | 12 | 345.6 x 864, in the head gap at each column quad | Tree levels 7 (b0+b1, b2+b3: gate/up done), 8 (o/down done) and 9 (with the pair station: qkv / LM head), then the BF16 row scale. |
| `qfd_dv_slice` (dvs) | 12 | 1,944 x 1,944 square, 3 x 4 in the centre straddling the head row | Holds 1/12 of the VM rows (its quad's output rows), an 8-lane SU/SFU slice, its rows' constants (norm gains, RoPE for its heads), and the gather / scalar / AR / D2D ports. |
| `qfd_dv_gather_exit` (dvg) | 2 | 216 x 216, at the centre column's W/E edge on the head row | Replaces xs_tap. Sends the full-x BF16 stream (64 / cycle) onto each side's existing head chain. |

Everything else is unchanged and reused:
- 48 `qfd_c_b16` clusters of closed ROM-leaf tiles at their q3h2 homes;
- 48 column heads, the head chain and the column corridor words;
- IO band, D2D, tt_ctlm, sys_face, embedding provider, clock and reset;
- native59, kept as the D2D-side formatter and moved beside d2d_rom.

**Column-quad ownership** (the matrix map is from the source; agent survey of `ot_qwen_w12_matvec.sv`, `token_source_plan.json`):
- One quad = one column group g of one side = clusters of bands 0-3, so 256 groups.
- The K split S is unchanged per op, so the golden pairwise tree is unchanged:
  - **gate/up, S=128:** the lower and upper cluster pairs each finish one row block at level 7. The compiler places gate block j on one pair and up block j on the other, so SiLU*mul is slice-local.
  - **o/down, S=256:** finishes at level 8 in the quad's station.
  - **qkv / LM head, S=512:** finishes at level 9 between the pair stations (g, g+1).
- 128 rows (one row block) = one head, so QK-norm and RoPE are slice-local. The finishing slices of qkv (even g) sit in the top rows next to native59/D2D; the odd-g slices sit in the bottom rows next to the collective.
- Far bands (0, 3) reach the head gap through a registered 514-b `rs_i -> rs_o` feedthrough in the near cluster: 12 stages, the same mechanism as today's `bc -> bc_o`. This is a **C_B16 port change**: DV owns a variant `qfd_c_b16_dv` and does not edit the CB files.

## 2. Per-layer dataflow (one token, TP8 compute die)

1. **RMSNorm1.** Each slice computes csum8 subtrees of x² over the row blocks it owns. A block is 128 rows = 16 chunks, an aligned subtree of the 512-chunk pairwise tree. The 32 block sums go up a scalar tree on the slice mesh to the root slice. The root does the top 5 pairwise levels in golden order, plus rsqrt. The scalar r comes back down the tree, and each slice applies h = (x * r) * g locally.
2. **Broadcast.** Each slice puts its BF16 h segment into its time slot on the gather merge tree. The tree feeds both exits, then the existing head chains, column corridors and cluster bc. The qkv input is 64 beats, as today.
3. **qkv matvec.** In-cluster levels 1-6, then levels 7-9 in the head-gap stations, then the row scale. The result goes down a 530-b lane to the owning slice.
4. **QK-norm (per head) and RoPE.** Slice-local. q/K/V go up the column mesh to native59 and then to d2d_rom. This is the registered PHY boundary, defined in §5.
5. **Attention.** On the KV die.
6. **Attention return.** Lands from d2d_rom and native59 in a top-row slice, then goes through the gather tree to the exits as the o_proj input (32 beats).
7. **o_proj.** Levels 1-8, then the station, then the lane to the slice.
8. **All-reduce #1.** The o partials go down the column mesh to the collective. The reduced rows come back up the columns, and each slice keeps the rows it owns. The residual add is local.
9. **RMSNorm2 and broadcast.** As in steps 1-2.
10. **gate/up.** Levels 7 in the station, then the lane, then the slice. SiLU*mul is local, using IEEE div/exp as the golden does.
11. **Broadcast act.** 24 beats, then the down matvec, then levels 8, then the slice.
12. **All-reduce #2 and residual.** As in step 8.

**LM head:** final norm as in step 1. Each finishing slice keeps a running (max, lowest index) over its 25 rounds. A 6-input scalar argmax tree runs over the mesh, and the token id goes to sys_face.

**Exactness:**
- Every reduction keeps its golden pairing:
  - matvec: S and the K order are unchanged; only where an adder sits changes;
  - R-ARITH csum8: aligned power-of-two subtrees, with the top levels at the root in pairwise order;
  - all-reduce: rank order, collective unchanged;
  - argmax: lowest index on ties.
- This is class A. It is not a level-6 reorder and not level 7, because no vector work is redistributed spatially beyond where the golden's own split puts it.

**Static schedule:**
- Every link has a fixed, compiler-known latency, which the stage table exports.
- There are no credits and no backpressure.
- The gather tree and mesh carry time-slotted words.

## 3. Bits per cut and bit-mm (relay-skip, same metrics as q3h)

| model | bit-mm | stages @500 | stages @405 | worst cut (full demand) | lines > 0.55 | mm² |
|---|---:|---:|---:|---:|---:|---:|
| q3h (final corrected smoke) | 1,077,241 | 9,565 | 11,948 | **1.435** (x 16,850, VM/SU seam, 8,516 b / 5,935) | 2 | 742.0 |
| **DV dv1** | **893,214 (-17.1 %)** | 4,062 | 5,175 | **0.488** (x 23,750 head gap over a head, 2,677 b / 5,484) | **0** | 742.0 |

DV link families:

| family | bits | bit-mm | max stages / hop |
|---|---:|---:|---:|
| reduce (rs, rs_i, l9) | 40,092 | 10,872 | 4 |
| lanes (12 x 530 b) | 19,080 | 56,682 | 28 (E5 -> centre) |
| gather tree 1,088 b | 19,584 | 2,350 | 0 |
| slice mesh (column 2,312 b, row 180 b) | 22,248 | 2,403 | 0 |
| AR (546 out, 518 back, x 3 columns) | 3,192 | 14,921 | 12 |
| D2D (548 / 520 x 3) | 3,204 | 20,625 | 17 |

- **Lanes.** The lanes run on separate track bands in the 1,179-um head gap. With the head chain, a 260-um window over a head block carries at most 2 x 530 + 1,567 b.
- **Gate/up.** Its two level-7 bursts serialise on the one-word lane at +8 cycles a layer, which halves the head-gap cut: 1,028 b lanes gave 0.67.
- **Centre.** Every slice-to-slice link crosses a 108-um channel between faces of at most 1,944 um, against a 40 k-bit face rule.
- **Largest stage count.** It is the existing control net `ng_io_cmd_free_0` (38 @405), caused by moving sys_face. sys_face goes beside the collective in deliverable 2.

## 4. Slice area (apportioned from the blocks DV replaces)

**Removed: 50.5 mm² in total.**

| removed block | mm² |
|---|---:|
| VM | 15.8 |
| SU64 + SFU | 11.9 |
| constant groups | 1.3 |
| seq_su + xs_tap | 0.3 |
| port halves | 15.3 |
| half-band lanes | 3.4 |
| half trains | 2.4 |
| tree top | 0.14 |

**Slice estimate: about 3.53 mm².**
- (29.3 / 12 = 2.44) for the VM, SU, constants, seq and tap share;
- +0.5 to widen the SU from 5.33 to 8 lanes;
- x 1.2 for ports and region overhead;
- This fits in the 3.78-mm² slot, which is 1.944 mm square.

**Station: 0.30 mm².**
- 3 x 16 FP32 adders, a 16-lane scale multiply and about 43 kbit of per-row BF16 scale ROM;
- the 48 x 514-b pin load becomes 4 x 514 in and 2 x 530 out per station.

**Added: 12 x 3.78 + 12 x 0.30 + 2 x 0.05 = 49.1 mm².**

The die stays 33.0 x 22.47 mm = 742 mm², so the comparison is iso-area. The SU has 96 lanes in total (12 x 8) against 64.

## 5. Slice <-> D2D / KV boundary (registered PHY boundary)

- **Ports.** The 3 top-row slices each own a 548-b D2D-out port and a 520-b return port. They go to native59, which is the only producer and consumer of `lnk_x3`, `lnk_native_tx/rx` and `kv_w*` toward d2d_rom.
- **Registration.** Every bit is registered on both sides of each block face. The link crossing is native59 <-> d2d_rom <-> ucie_kv, the existing registered FDI. The existing UCIe / FDI PHY contract and `qfd_d2d_static` are unchanged. The r7f/r8b D2D successor still gates binding, as before.
- **Elastic and fixed parts.** The KV-die HBM boundary keeps its elastic buffer, which is on the KV die. On the compute die, the slice-to-native59 part is fixed-cycle.
- **Collective.** The bottom-row slices connect to io_collective over the existing `seq_cd` / `io_out` word formats: 546 b out, 518 b back.

## 6. Priced cost (iso-area, Qwen token path)

Per-layer dependent-hop ledger (`cycles_dv.py`). Hop = 405 um. A stage is `ceil(L/405) - 1` plus 1 per block boundary. Each intermediate DV slice that a path crosses is charged 4 stages. The q3h paths are not charged their crossings of the port tiles and VM, which is conservative against DV.

| term | x / layer | q3h | DV | delta |
|---|---:|---:|---:|---:|
| R: result landing, worst cluster to VM / slice (DV includes the 12-stage feedthrough) | 4 | 52 | 57 | +20 |
| P: qkv level 9 between pair stations | 1 | 0 | 4 | +4 |
| X: broadcast source (norm1, norm2, act) | 3 | 8 | 18 | +30 |
| O: attention return to the broadcast | 1 | 39 | 34 | -5 |
| N: global scalar tree, there and back (norm1, norm2) | 2 | 0 | 20 | +40 |
| A: all-reduce out + back (o, down) | 2 | 34 | 54 | +40 |
| K: q/K/V export to d2d | 1 | 28 | 23 | -5 |
| gate/up lane serialisation | | | | +8 |
| QK-norm on 8 lanes (one head = 16 beats, against 10) | | | | +6 |
| **total** | | | | **+138 cycles / layer = 4,968 / token** |

- **Result:** `accepted_cost.py compute qwen_rom --match 'L\d+\.residual$' --node-delta 138` gives **-1.95 % tok/s**. At 132 it is -1.87 %; at 300 it would be -4.15 %.
- **Threshold:** well inside the ~-8 % stop threshold, so implementation may proceed.
- **Gains not claimed:**
  - the SU goes from 64 to 96 lanes: per-slice RMSNorm, residual and SiLU passes are 48 / 16 beats against 64 / 24;
  - the VM/SU seam goes away;
  - the band-lane / half-train serial hops disappear (`R` charges only geometry).

## 7. Principles and pitfalls (accelerator-design-principles-1016)

1. **Vector next to matrix.** Each quad owns y[a:b] in its own slice, with no central VM/SU.
2. **Neighbour-only, pipelined.**
   - Every planned hop is relayed at 405 um, below the measured 425.
   - Mesh and gather links are abutted-channel hops.
   - Lanes and AR / D2D links are relay chains in the head gap and centre channels, with fixed latency in the stage table.
3. **Collectives are trees or chains.**
   - Reduction happens in flight (cluster -> station -> pair).
   - The scalar trees are tiny (32-64 b).
   - Broadcast uses the gather merge tree plus the existing relay head chain.
   - No star: the largest fan-in is 4 x 514 b at a station.
4. **One square slice, hardened once, x12.**
   - The station is one master, x12.
   - The slice has about 1,300 pins against the old VM's 8,511-b seam plus a 1,300-pin clock face.
   - Each slice is its own regional clock and reset region, with neighbour-relative clocks between slices and stations.
5. **Priced and cut-checked before RTL.** This document. Cut 0.488 at <= 0.55, and the PNG was viewed (`dv1.png`).

**Pitfalls avoided:**
- no hub;
- no long unregistered hop: hop-gate 405;
- no long thin block: the slice is 1:1 and the station is 0.4:1 inside the 1.18-mm gap, as small as a relay;
- the die is hierarchical (clusters, stations, slices);
- hold is budgeted on relays, not on tile input padding;
- area is not squeezed: the centre still has white space for channels.

## 7a. Risks / open items

- **Cluster feedthrough.** The `rs_i -> rs_o` feedthrough needs room in the C_B16 corridor: 514 b beside bc_o's 1,567 b. If the T corridor cannot take it, fall back to a 64.8-um relay lane at each quad edge (die width +0.78 mm, which exceeds 33 mm) or move b0/b3 rs onto M8/M9 overflight relays at the band gaps.
- **Slice area.** It is apportioned, not synthesised. The first slice synthesis decides the 1,944 edge, and the head-gap row can grow if needed.
- **Golden match.** The ROM golden must be shown to be the R-ARITH csum8 for the norms on the TP8 compute die (`hdc_golden.reduce_chunked`). The slice bench checks this bit-exact against the existing Qwen golden.

## 8. Next (deliverable 2, then 3)

1. Move sys_face next to the collective.
2. Run a relay-stage plan at hard reach 405, then flow PNG and Explorer export (`dataflow_links.py`, candidate of the current Qwen compute view).
3. Slice RTL from the existing SU/VM sources, specialised to 8 lanes and 1/12 rows, plus the station and gather RTL. Benches bit-exact against the Qwen golden, then `submit_exact`, then the die_cluster hierarchical trial.

Files in this directory:
- `build_dv.py`: the model;
- `cycles_dv.py`: the ledger;
- `metr.py`: metrics;
- `render.py`: PNG;
- `dv1.json`, `dv1.png`, `metrics.txt`, `ledger_dv1.json`, `receipt.json`.

---

# Addendum 2026-10-16 ~23:30: dv2 co-location (coordinator review of dv1)

The coordinator's review of dv1 found a problem. dv1 partitions the centre but does not co-locate. Every 530-b lane still runs up to about 13 mm into the centre, and the broadcast runs back out again. That breaks principle 1. This addendum covers dv2 (`build_dv2.py`), the full-path ledger (`cycles_v2.py`) and the comparison.

## dv2 geometry

- **Slice placement.** Each quad's slice sits in the head gap directly beside its own column group. It is one cluster pitch wide (2,090.9 um). The gap is widened to the slice height plus a 129.6-um relay lane above and below.
- **What the slice absorbs:**
  - the quad's reduction station (levels 7-9 and the row scale);
  - its 4 column x-slice heads;
  - the VM slice, the SU slice and the constants.
- **Reduction.** b1 and b2 rs abut the slice. b0 and b3 still use the near-cluster `rs_i -> rs_o` feedthrough, so the corridor-fit question remains for dv2 too.
- **Next-layer input.** A bidirectional slice-to-slice neighbour stream (1,088 b each way) runs along the gap. It crosses the centre on its own relay lane. tt_ctlm's ib/go enters at g0 on both sides.
- **Global scalars.** A 96-b tree runs along the gap.
- **Edge endpoints.** Each has its own relay lane:
  - AR and D2D chains run slice to slice to g0;
  - g0 connects to io_collective (S) and to native59 -> d2d_rom (N).

## (b) RMSNorm gamma folded into the ROM, 1/rms after the matvec: NOT bit-exact, not adopted

- **Golden order.** `h = (x*r)*g`, then `bf16(h)`, then the INT8 x BF16 csum8 matvec, then the row scale.
- **Why folding breaks it:**
  - folding g into the INT8 codes re-quantises every row, so the codes change;
  - applying r after the matvec moves the BF16 rounding point and the product order.
- **Status.** This is the AGENTS.md level-6 algebraic reorder (excluded). The related norm-after-matvec check (QC-NAM) is closed as REJECTED on a numerical-stability FAIL (docs/INTEGRATED_PHYSICAL_PLAN.md: "do not reopen or credit").
- **Exact alternative adopted instead: norm at the consumer (dv2r).**
  - The residual x is replicated per side. Both sides do the identical residual add, which is exact and deterministic.
  - Each slice streams raw x to the side's slices WHILE the sum-of-squares tree runs.
  - Each slice applies `h = (x*r)*g` (the golden ops, in order, with g from a per-slice BF16 gamma ROM of 4.7 Mbit) and rounds to BF16 where the corridor word is formed.
  - The critical path becomes `max(tree, stream)` instead of `tree + stream`.
  - Only the act broadcast (the down input) still crosses the die.

## (c) Comparison

Full-path stages / layer; tok/s from `accepted_cost.py ... --node-delta`. SU-lane beats and the seam (21 registered VM<->SU crossings / layer) are counted this time, and AR rows are streamed farthest-first.

| design | layer cycles (non-common part) | delta / layer | tok/s | worst cut | bit-mm | stages@405 | die mm² |
|---|---:|---:|---:|---:|---:|---:|---:|
| q3h | 776 | 0 | ref | 1.435 | 1.077 M | 11,948 | 742 |
| dv1 (partitioned centre, L8) | 759 | -17 | +0.25 % | 0.488 | 0.893 M | 5,175 | 742 |
| dv2 single owner (L8) | 887 | +111 | about -1.6 % | (same geometry) | | | |
| **dv2r8 (pick)** | 767 | -9 | +0.13 % | 0.416 | 0.857 M | 4,297 | 797 |
| dv2r16 | 657 | -119 | +1.75 % | 0.439 | 0.924 M | 7,060 | 825 |

Per-term values (R / P / QK / K / O / A / NORM / SILU / BCA / SEAM) are in `led_dv2r8.json` and `led_dv2r16.json`.

**dv2 wins on:**

| term | q3h | dv2 |
|---|---:|---:|
| R: result landing | 52 | 13 |
| NORM | 158 | 177 at L8, 134 at L16 |
| seam | 21 | 0 |

**dv2 loses on:**

| term | q3h | dv2 | why |
|---|---:|---:|---|
| BCA: act all-gather crosses the die | 30 | 81 | |
| K: export from W4 | 28 | 59 | |
| A: g0 <-> collective | 34 | 50 | |

The edge endpoints are now 8-11 mm away.

**PNGs viewed:** `dv1.png`, `dv2r8.png`, `dv2r16.png`.

**Stage counts.** dv2 stages@405 include about 1.4 k from the existing N-edge bump nets (`lnk_fwd_epoch`, `rst_d2d`, max 56-59) that now reach the gap row. Those get their own relay plans in the relay-stage step.

**Centre column.** It is about 150 mm² of white because the die width is fixed by the S-edge IO band (3 SerDes + UCIe = 7.74 mm). Narrowing it to about 4.3 mm, by stacking the PHYs, needs a package/PHY decision and is not assumed.

## Pick (floorplan-objective rule: bit-mm + relay stages + flow PNG, then cut): dv2r8

dv2r8 is preferred because:
- it is the only co-located plan, so it meets principle 1;
- the reduction lands next to the group (R 13 against 52);
- there is no centre star;
- its slice is the squarest (2,091 x 2,581, 1.23:1);
- its die is smaller than dv2r16's (797 against 825 mm²);
- it is tok/s-neutral against q3h at the lowest bit-mm.

dv1 has fewer stages, but it fails co-location. dv2r16's +1.75 % is below the "significant gains" bar and costs +28 mm². SU LANES is a slice-RTL parameter, so 16 lanes can be swapped in later.

## Reach caveat (coordinator / H-REACH, 2026-10-16 ~23:45)

S81 measurements show the following limits:
- unbuffered M4/M5 relay hops are slew-limited to about 175 um;
- timing alone would allow about 400-500 um;
- buffered reach (repeaters on die nets) is still being measured.

Two consequences for this plan:
- **405 um is provisional.** The ledger takes the hop as `QDV_HOP_UM`.
- **Qwen's own reach figures were not measured on wires, buffered or unbuffered:**
  - The KV-die 446 / 460 um (and the compute 425 um) come from `die_reach_1016.json`'s formula: (T - U - skew - launch - capture) / 0.76 ps/um.
  - Launch and capture come from the relay views' ETMs (rlys_296: 219.7 / 124.5 ps; rlys_528: 179.4 / 154.1 ps).
  - 0.76 ps/um is an assumed TT BUFFERED die-wire delay.
  - So these figures already presume repeaters, they ignore slew, and they are not routed-wire measurements.

**200-um sensitivity** (same models, `led_dv2r8_h200.json`):

| design | layer @405 | layer @200 | delta vs q3h @200 | tok/s @200 |
|---|---:|---:|---:|---:|
| q3h | 776 | 1,234 | 0 | ref |
| dv1 | 759 | 1,266 | +32 | -0.46 % |
| dv2 single owner | 887 | 1,464 | +230 | |
| **dv2r8** | 767 | 1,144 | **-90** | **+1.32 %** |
| dv2r16 | 657 | 1,034 | -200 | |

- **dv2r8 is more robust to short reach than q3h and dv1.** Its result landing is local (R 26 against 103), so it has less die wire on the critical path.
- **Its exposed terms** are the act all-gather (BCA 151), the export (K 114) and the AR (A 100). These are the links to give the best repeater plan.
- **Absolute cost.** At 200 um every design gets slower: q3h adds +458 cycles a layer. That is a die-wide issue, not a DV one.

**Plan:**
- Every slice and stream link, the centre crossing lane and the edge-endpoint lanes get die-level repeater buffering. That means buffered relay chains, with stage counts from the measured buffered reach once H-REACH publishes it.
- Slice input pins get a robust first cell: a sized input flop or buffer at the pin, NOT a hold buffer. Hold belongs to the die-level budget on the relay stations (FLOW-HOLD).
- The slice RTL helper has been told this. It applies to the qfd_dv_slice port list.

## Deliverable 2 status (2026-10-17 ~00:20)

- **sys_face moved** beside native59 at the N edge, since it talks to d2d/native59. In dv2r8 this brings:
  - bit-mm 0.889 M -> 0.857 M;
  - stages@405 6,761 -> 4,297, against q3h's 11,948.
  - The cut (0.416) and the ledger (-9 / -90 cycles) are unchanged.
- **Relay plan:** `relay_plan_dv2r8.json` gives every link's length and its stages at 405 and 200 um. Every stage is a repeater-buffered relay station.
  - Remaining long nets are 1-b io_collective <-> sys_face control lines (about 20 mm, S edge to N edge). They get relay chains or move into the sys_face <-> collective calendar.
- **Explorer:** `to_explorer.py` produced the records, and `dataflow_links.py import` put them in the live Dataflow Explorer as candidates of `qwen_r2h5`:
  - `qwen_qdv_dv2r8` (pick);
  - `qwen_qdv_dv1` (comparator).
- **PNG:** `dv2r8.png` was re-rendered and viewed.

## Hold budget (FLOW-HOLD, coordinator-approved, 2026-10-17)

- **Tiles under the rule:** the slice (`qfd_dv_slice2`) and any separate station or relay tiles are recipe-4 leaves with `"hold_budget": "die"`. The rule is `results/arch/boundary_hold_budget_1016/RULE.md`.
  - Pins are flop-first and outputs are flop-driven.
  - There are no inhold/outhold pads.
  - Sign-off: input min = L_min+C+U, output min = U-(L_min+C), with C = 25 and U = 25. Setup is unchanged.
- **Die STA:**
  - It reads `ff_launch_min_ps` from each bound ETM and times every receiver on its hold arc.
  - U = 25 is applied once per link.
  - Neighbour |delta| must be <= 80 ps.
  - It gates on FF hold >= 0.
  - Any shortfall is fixed only in relay stations or die-net hold cells.
- **Opt-outs:** none planned. The slice is single-domain.

## dv2r8e: IO on the die edge (owner question via coordinator, 2026-10-17) -- ADOPTED

`build_dv2e.py` starts from dv2r8 and makes three changes:
- **IO column.** The 3 SerDes PHYs, io_collective and io_ucie are rotated into ONE W-edge column (1,672 um wide), centred on the slice row beside `dvs_W5`. That slice is the end of the stream backbone. Stack order is serdes_2, serdes_1, collective, ucie, serdes, so every FDI goes to a neighbour.
- **D2D side.** ucie_kv / d2d / native59 / sys_face stay on the N edge at the centre axis, where the KV die abuts. That is the shortest, package-legal choice.
- **Centre.** The centre is closed to 994 um: tt_ctlm plus two 108-um channels for the W<->E stream lane.

Variant B was tried and rejected:
- the collective stayed in the centre and the SerDes were split across the W/E edges;
- the FDI links then cross the slice row, giving cut 1.348 and 13 lines > 0.55.

Comparison (same metr.py / cycles_v2.py; @200 = 200-um hop sensitivity):

| | q3h | dv1 | dv2r8 | dv2r16 | **dv2r8e** |
|---|---:|---:|---:|---:|---:|
| worst cut | 1.435 | 0.488 | 0.416 | 0.439 | **0.414** |
| stages @405 | 11,948 | 5,175 | 4,297 | 7,060 | **4,185** |
| stages @200 | 24,543 | 10,575 | 8,988 | 14,517 | **8,641** |
| bit-mm | 1.077 M | 0.893 M | 0.857 M | 0.924 M | **0.807 M** |
| die mm² | 742 | 742 | 797 | 825 | **670 (27.8 x 24.1)** |
| longest single link | 18.9 mm bword_1 | 15.4 | 20.2 | 23.9 | 23.3 mm `sf_io_shared_fault` (1 b) |
| cycles / layer vs q3h @405 | 0 | -17 | -9 | -119 | **-138 (about +2 % tok/s)** |
| cycles / layer vs q3h @200 | 0 | +32 | -90 | -200 | **-351** |

**Decision by routing ease (cut, then stages, then bit-mm): dv2r8e.**
- It is at least as good as dv2r8 on all three.
- It is also smaller by 126 mm² and faster: the AR enters at the backbone end (A 50 -> 4), and the narrower centre shortens the K, O and BCA paths.
- The longest links are 1-b io_collective <-> sys_face/tt control and fault nets that span the W edge to the N centre. They get relay chains.

Outputs:
- `compare_all.png`: q3h | dv1 | dv2r8 | dv2r16 | dv2r8e, same scale and colours, viewed.
- `dv2r8e.png`: viewed.

The plan is now asymmetric: all IO is on the W edge. The E-side AR rows ride the backbone. That traffic is within the collective's own 512 b/cycle, and is ordered farthest-first.

## dv2r8f: no empty regions (owner correction 0cl, 2026-10-17) -- ADOPTED

`build_dv2f.py` starts from dv2r8e and makes three changes.

1. **Centre closed to 0.**
   - The W and E arrays and the slice rows abut. `dvs_W0 | dvs_E0` exchange the stream face to face, like every other slice pair.
   - No die net needs a centre channel any more. The cut model's worst line no longer lies anywhere near the seam.
2. **tt_ctlm / sys_face / native59 / d2d / ucie_kv / embed / clk_rx / rstseq** are packed two abreast at the N end of the W-edge column.
   - The KV die still abuts the N edge, now at the W corner.
   - The KV die cannot sit on the W edge: that edge carries the SerDes beachfront, and the KV die is 24 mm long.
   - ib/go enters the backbone at W5. It is static and pre-issued, so this costs no latency.
3. **Column channel = 216 um.**
   - The 2,516-b D2D + ib lane (native59 -> W5) runs inside it.
   - At 108 um that lane alone would load the channel about 0.74.
   - Routed diagonally over W5's clusters it gave cut 0.517.

| | q3h | dv2r8 | dv2r8e | **dv2r8f** |
|---|---:|---:|---:|---:|
| worst cut | 1.435 | 0.416 | 0.414 | **0.378** |
| stages @405 / @200 | 11,948 / 24,543 | 4,297 / 8,988 | 4,185 / 8,641 | **3,304 / 6,951** |
| bit-mm | 1.077 M | 0.857 M | 0.807 M | **0.792 M** |
| die | 742.0 | 796.8 | 670.4 | **645.6 mm² (26.8 x 24.0)** |
| white space | 18.9 % (140 mm²) | 23.6 % (188) | 9.2 % (61.5) | **5.7 % (37.1)** |
| largest empty rectangle | 30.3 mm² (centre) | 73.9 (centre) | 9.8 (W column) | **10.4 (W column, below the PHYs)** |
| longest link | 18.9 mm | 20.2 | 23.3 | **10.1 mm (1-b ng_io_cmd_free_0)** |
| cycles / layer vs q3h @405 (@200) | 0 | -9 (-90) | -138 (-351) | **-66 (-215)**, +0.96 % tok/s |

**Cycles trade.** The q/K/V export and the attention return now run the whole backbone from the W corner: K 49 -> 87 and O 55 -> 93 against dv2r8e. That is +72 cycles a layer against dv2r8e, but it is still a gain over q3h. The rule applied was routing ease, cut and stages no worse, and dv2r8f is better on both.

**Residual white is structural.** It is 37 mm² in total, of which:
- about 17 mm² are the required band gaps and relay lanes;
- 10.4 mm² lie in the W column below the PHY stack;
- a 2.1-mm gap lies between io_serdes and tt_ctlm.

The arrays fix any edge column at 24 mm tall, which is 37.6 mm² at the 1.56-mm PHY depth. The column content is 21.6 mm²: 3 SerDes, the collective, io_ucie, the D2D group and control. An S-edge row would leave the same residual. The collective stays on the slice row so the AR stays at 4 stages.

**Outputs:**
- `dv2r8f.png` and `compare_all.png` (6 panels, now with white % and the largest empty rectangle) were viewed.
- Explorer record `qwen_qdv_dv2r8f`: `token_designs ['qwen_rom']`, candidate of `qwen_r2h5`.
