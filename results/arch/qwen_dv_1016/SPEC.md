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
