# S81-DV: a distributed-vector S81 layer die (spec, price and cut; deliverable 1)

Stream S81-DV (owner decision 0cj, 2026-10-16 ~22:00). Plan level: nothing in this spec is RTL or a routed die.

**Status: COMPOSED_NOT_NATIVE.** Every rate below is composed from the token-path DAG and plan geometry. It becomes a
measured rate only once the slice benches and the die trial report their latencies.

**Current candidate: p1**, revised after the coordinator review of 10-16:
- reticle margin;
- slice-column white space.

The p0 numbers are kept for history under `p0/`. p1 is in `p1/` and in the Explorer record `s81_dv_p1`.

Reproduce:
- `python3 tools/s81_dv/dv_plan.py --out DIR` writes `plan.json`, `dv_links_record.json` and `dv_flow.png`.
- `python3 tools/s81_dv/dv_price.py --plan DIR/plan.json --out DIR/price.json` writes the price.
- Committed copies of the outputs are in `p1/` (current) and `p0/`.
- Explorer records: `s81_dv_p1` (current) and `s81_dv_p0`, both candidates of `s81_c26b_r`.

## 0. p1 revision (coordinator review, 10-16)

| | p0 | **p1** |
|---|---|---|
| Die | 33.00 × 26.00 mm (full reticle) | **29.37 × 25.00 mm = 734 mm²** |
| Margin per side under the 33 × 26 reticle | 0 | **1.81 mm / 0.50 mm** |
| Slice column | 1.75 mm | **1.30 mm** (the slice width + 50 µm) |
| Slice | 1.70 × 2.60 | **1.25 × 3.50** (2.8:1, 4.375 mm²) |
| Mesh | 8 × 2 mesh | **16-slice bidirectional ring**: E–W along the two tier streets, N–S only at the end columns. Worst latency is the same as the mesh: Δx + Δy. |
| Global/edge units | Below the S slices | **In the inter-tier void of the slice columns**, reusing the white space: G-unit, seq/host, bk ×2, mix4 ×2, coll edge ×4 |
| Frames | 128, 1,220 slots | 128, **1,184 slots (−3%)**: 6 nine-slot + 2 ten-slot per column |
| Stages | 89 | **92** |
| Worst cut / windows > 0.55 | 0.415 / 0 | **0.427 / 0** |
| Over-reach bits | 0 | **0** |
| Relays | 3,048 | **2,018** |
| bit·mm | 0.72 M | **0.47 M** |
| Worst x all-gather + local return | 129 stages | **117 stages** |
| Scalar exchange | 100 stages | **91 stages** |

Why the column can be narrow:
- Every vertical die wire in a slice column starts or ends at that column's slice: x chains, returns, ring ends, unit links.
- So the column needs no through-channel beside the slice.
- Frame lanes run at the column edges (260-µm windows 0 and 4), and the units own the middle.
- The x-tap pins of the frames facing the slice cross a 25-µm gap.

**p1 price** (89 → 92 stages charged by `hop_only`):

| Scenario | AR tok/s | MTP tok/s | vs today (MTP) |
|---|---|---|---|
| DV base | 1,450.0 | 4,248.3 | +28.1% |
| Pin register 16 | 1,444.2 | 4,232.6 | +27.7% |
| SU +10% | 1,431.2 | 4,188.5 | +26.3% |
| SU +25%, pin register 16 | 1,396.5 | 4,087.2 | +23.3% |
| Keep SU/HC rows | 1,319.3 | 3,938.2 | +18.8% |
| Keep SU/HC rows + SU +25% | 1,271.5 | 3,792.8 | +14.4% |

### The three biggest assumptions behind the price

1. **The hub's ledger rows do not carry over to the slices.**
   - VM.READ + VM.RELAY + VM.A2 are 15.6% AR / 13.4% MTP. They come from the central VM's floorplan: a leaf-chain read hop of 2 and reach relays.
   - SU.* and HC.* are 8.4% AR / 6.6% MTP. They come from the hierarchical slab's serial chains: NORM 713 cycles hierarchical vs 235 flat, POST 248 vs 22.
   - The assumption is that a 1/16 slice runs at the flat-RTL prices plus pin registers.
   - The "keep SU/HC rows" scenarios bound it. Removing the VM rows is the larger and safer part, because a slice VM is one local bank group at fixed L = 12.
2. **Mesh and ring constants are plan stages, not routed numbers.**
   - Field phase wire: 117 stages vs the DAG basis of 138 (the c26l geometry is actually 75.6 mm, i.e. worse than that basis).
   - Norm exchange: 91 stages per full-h norm, ×2 per layer.
   - Router tree: 50 stages (worst slice → G-unit 20.1 mm); ring h transfer: 2 × 40 stages.
   - Each assumes one relay per 405 µm and no extra pipeline in the ring stops. Each additional ring-stop register adds ≈ 8 cycles per ring traversal to the norm and router paths: about 0.3% per extra register per hop class.
3. **Collectives and the cross-die path are unchanged from the DAG**, conservatively.
   - The cross-die all-gather and all-reduce enter and leave at the end slices instead of a centre collective. The plan distance is similar: slice-to-edge ≤ 16.0 mm vs centre-to-edge ≈ 16 mm.
   - The reduce-scatter that would keep each slice's rows local across dies is not modelled as a gain.
   - The +3% stage count from the shorter frame columns is charged.


## 1. Why

The c26l hub (v3i5) is a star:
- One VM holds the only copy of h.
- The SU, HC and MIX4 slabs read and write it over 8–17 kb buses.
- Every field result returns to one capture point, and every operand leaves from one PQ.

Measured on the same scope (die-level links, frame internals excluded), v3i5 has:
- worst cut 3.22, with 220 windows over 0.60;
- 68,487 over-reach bits;
- 11,182 relays;
- 1.52 M bit·mm.

The largest bus is SU↔VM at 4 × 2,048 b each way.

Five S81 ledger rows exist only because of this hub's geometry and its hierarchical slabs:
- VM.READ 9.09%
- VM.RELAY 5.91%
- SU.HC_PRE_NORM 3.57%
- SU.HC_POST 1.65%
- HC.H_XFER 1.20%

With the other SU/HC/VM/CAPT rows, they cost 24.4% AR and 20.4% MTP of the 25.36% ledger.

## 2. Architecture

### Clusters and slices

There are 16 clusters. Each cluster is 8 existing column frames plus 1 vector slice. They are laid out as 8 cluster columns × 2 tiers.
- A cluster column is [frame column | slice column 1.75 mm | frame column], 4.05 mm pitch.
- The slice is 1.70 × 2.60 mm (1.53:1). It sits in the slice column at its tier's street and is hardened once and replicated 16 times.
- Each slice has one regional clock root and a regional synchronous reset leaf.

### Ownership

Slice g owns the rows [320g, 320g+320) of every 5,120-vector. That covers h (4 HC copies), the attention/FFN outputs, the residual, and all 4 copies.
- Other vectors are dealt to slices in 32-element act-quant blocks, balanced to ±1 block.
- The compiler places each matrix's output rows in the frames of the owning slice, so every finished row returns locally.
- 5,120 / 16 = 320 is 10 quant blocks, so h-sized vectors are block-aligned.
- Every shipped matrix's row count divides by 16: a_proj 448, wq_b 8,192, wo_a 2,048, wo_b 5,120, router 96, experts_gu 6,912, down 8,960, shared_gu 1,152. Field phases therefore stay balanced: each frame holds rows/128.

### What a slice contains

Every unit inside the slice is a 1/16 share of today's hub.

| Content | Source | Per slice |
|---|---|---|
| VM partition | 1 × `dsfd_vm_bgq28h` bank group (8 of 128 SRAM macros) | 64 KiB; worst layer 71% |
| HC | 4 × `ot_s81_hc_cth` (closed leaf, 64 in the hub today) | h resident, 4 × 320 BF16; POST/NORM lanes NG 16 |
| SU lanes | QN 16, KV 32, QB 2 blocks, SW 64, HCPOST 64 outputs/cycle, RX softplus 2, QR 1 RoPE | `ot_dsrom_su_*` lane RTL, `ot_hbm_norm_grp` (bit-exact to `ot_dsrom_su_norm`) |
| SFU | exp (254-entry n·ln2 table, 16 kb), rsqrt (Newton), fdiv | one copy per lane group |
| Capture | finished rows from 8 frame region roots, 8 × 68 b | bf16/fp32 rounding as `ot_s81ph_capture` |
| x tap | 2 daisy chains up + 2 down (frame cfifo tap and forward), 1,104 b each | |
| Ring stop | E, W and one N/S port, 1,104 b each way, registered; forwards ctl and collective lanes | |
| Golden-subtree combiner | 1 FP32 add pipe, the top of the csum tree, rsqrt | |

Area estimate: about 3.1 mm² of cells against a 4.42 mm² outline.
- 4 cth = 1.71 mm²
- bgq28h = 0.27 mm²
- SU lanes ≈ 0.61 mm², which is the SU slot minus the SM softmax tiles, divided by 16
- control, ring stop, capture and combiner ≈ 0.5 mm²

Pins: about 9.4 k, all pin-registered, on an 8.6 mm perimeter, which is 1.1 pins/µm.

### Units outside the slices

These are the global units, each a small block, and each reached on the mesh or a small tree.

| Unit | Place | Role |
|---|---|---|
| G-unit, 1.10 × 2.20 mm | slice column 3, between tiers | Router top-6 select (`ot_hdc_select_tree`), routing-weight normalisation, HC coefficient finish plus Sinkhorn (`ot_hdc_sinkhorn_mc`, seed ROMs 42 kb, single copy), and the ctl/expert-id/coefficient tree root |
| seq/host/wfc, 1.10 × 1.80 mm | slice column 4, between tiers | |
| Attention | south band | 8 × `ot_s81_su_sm` softmax tiles, abutted 4 + 4 to the two HBM service halves `svc_W` and `svc_E`, which flank the PHY. Scores and P cross an abutted face, not a die wire. Attention is an irregular operator and keeps a dedicated unit (AGENTS method 2). |
| Index select/collect (bk), Engram mix4 | 4 square-ish blocks of 1.25 × 2.1–2.5 mm in the slice columns above the PHY | |
| Collective edge engines | 4 blocks of 1.10 × 1.00 mm beside the end slices | Two 512-b link lanes per tier per edge; links sit at street height on the W/E edges |

## 3. Dataflow per layer type

All die wires are registered relay chains with hops ≤ 405 µm, and every latency is compiler-known. There is no credit or ready signal on chip.

| Op | DV dataflow |
|---|---|
| hc_pre + RMSNorm + act-quant (attn.quant, ffn.norm.scale) | Slice-local mix, square and chunk-8 sums. The slice emits the roots of the maximal golden-aligned subtrees of its 40-chunk range, at most 5 roots in a 1,024-leaf tree. These are exchanged on the mesh (worst slice→slice 40.1 mm, 100 stages). Every slice finishes the identical golden tree, rsqrt, scale and FP8 quant: replicated finish, same operands, same order, same bits. |
| a_proj → a_allgather (TP4) → q_norm → q_quant | Rows land in their slices. The cross-die all-gather enters at the W/E end slices and joins the die mesh stream. The q_lora norm spans 4 adjacent slices (tree of 30 stages). |
| wq_b → q_rope | Head h is owned by slice h (512 rows); RoPE is slice-local. q goes on the mesh to slice columns 1 and 6, then down to the PHY-side attention (worst 26.5 mm, 66 stages, vs 50 hub→svc today). |
| Window/index load, scores, softmax, P·V | In the service halves and the abutted SM tiles. P·V rows go back up into the mesh as the wo_a operand. |
| wo_a → z_quant → wo_b → out_allreduce → hc_post | Matvecs read x from the mesh. z_quant is slice-local. The all-reduce goes slice → end slice → edge link, and remote partials come back into the owning slice, which folds them in the fixed order ((p0+p1)+(p2+p3)). hc_post is slice-local (`ot_dsrom_su_hcpost_lane`). |
| Router → softplus·sqrt → router_allgather → bias → top-6 | 96 rows spread over the slices, softplus in the slice. Scores travel on the mesh to the edge for the TP4 gather, then to the G-unit (worst 22.3 mm, 56 stages). Expert ids and routing weights go back on the ctl tree. |
| experts_gu → SwiGLU → route_w → quant2 → down → combine_allreduce → hc_post | gate[j] and up[j] are placed in the same slice. An act-quant block that straddles two slices exchanges one amax with its neighbour. down and combine are as wo_b and out_allreduce above. |
| Shared expert | As the experts; off the critical path today (144–3.7 k slack). |
| HC coefficients / Sinkhorn | Per-slice projection partials (each slice holds 1/16 of the projection ROM) as golden-subtree roots, sent to the G-unit, then Sinkhorn. The 24 coefficients go back on the ctl tree. Off the critical path (6.5–8.6 k slack). |
| Engram (L1, L14) | HBM rows → mix4 → mesh; each slice snoops its 320 elements. The eng.dot reduction uses the same golden-subtree exchange as the norm. |
| Stage hop / MTP hidden rows | h slices stream on the ring to the edge links (≤ 14.3 mm, 36 stages each side). This replaces the H_STORE/H_LOAD (246) of HC.H_XFER. |
| MTP head items (draft ids, accept flags) | Scalars on the ctl tree. |
| LM head / argmax | On the head dies; unchanged by this die. |

The whole on-chip vector path above is real hardware: existing lane RTL plus the new slice control, ring stop and combiner.

## 4. Exactness

Matvec accumulation is unchanged: in-frame, golden sibling tags. Each slice receives finished rows. No K-split is introduced.

Long sums:
- golden `csum`: chunks of 8 summed sequentially from +0, then a pairwise tree padded to a power of two;
- a slice's contiguous range decomposes into maximal aligned subtrees;
- the combiner reproduces the golden tree above them, so the adds and operands are identical to the golden's.

Other orders:
- **All-reduce:** the canonical fold is kept in the owning slice.
- **Act-quant:** blocks are aligned to the 320-element ownership, and for odd-sized vectors at most one amax is exchanged with a neighbour.

## 5. Cut, bit·mm, reach (p0; the p1 figures are in §0)

Scope is the die-level links. Metrics come from `dataflow_links.py` itself (`import` path; 260 µm windows, 5,484 tracks per window).

| | v3i5 hub, same scope | **DV p0** |
|---|---|---|
| Worst cut | 3.22 (220 windows > 0.60) | **0.415** (0 windows > 0.55) |
| Over-reach bits | 68,487 | **0** (every hop ≤ 405 µm) |
| Relays | 11,182 | **3,048** |
| bit·mm | 1.52 M | **0.72 M** |

- The worst window is a slice-column vertical cut of two x chains plus returns.
- The street carries the ring (2 × 1,104 b) plus ctl (16 × 96 b at the centre columns).
- Frames: 128, the same height mix as c26l (60 × 2.70, 40 × 2.99, 28 × 3.00 mm). The die is 33 × 26 mm, frame top 25.68 mm.

## 6. Price (method, and p0 figures; the p1 figures are in §0)

The pricing machinery is the ledger's own: the `accepted_cost.solve` DAG, the MTP wave rule, and `mtp_ledger_1016` hop_only(89) with additive losses.

- **Ledger rows dropped** (they price hub units that DV does not have): all VM.*, SU.*, HC.* and CAPT.CD_PINREG rows. That is 24.4% AR / 20.4% MTP.
- **Ledger rows kept:** field return tree, cfg7, Engram, MIX4, MTP p2. That is 0.77% AR / 0.81% MTP.

DV deltas on the DAG, AR / MTP cycles:

| Rule | AR | MTP |
|---|---|---|
| Hub in/out stages removed (−56 + pin reg 8) | −11.5 k | −9.6 k |
| Hub-wired BCAST/RET (−37 + 8) | −19.4 k | −8.0 k |
| Hub-slab stations | −3.2 k | −1.2 k |
| Field phase wire ×129/138 | −6.8 k | −6.4 k |
| Full-h norm mesh exchange (+100 − 18) | +13.3 k | +7.2 k |
| q-norm tree | +0.5 k | +0.5 k |
| q to attention | +0.6 k | +0.6 k |
| Router tree | +2.2 k | +2.4 k |
| Ring h-transfer | +4.1 k | +4.2 k |

The DAG net is −1.1% AR / −1.0% MTP. Collectives are left unchanged, which is conservative.

| Scenario (89 stages) | AR tok/s | MTP tok/s | MTP vs today |
|---|---|---|---|
| Today (ledger as is) | 1,072.5 | 3,315.4 | — |
| **DV base** | **1,438.5** | **4,218.9** | **+27.3%** |
| Pin register 16 | 1,432.9 | 4,203.4 | +26.8% |
| SU at +10% | 1,420.1 | 4,160.0 | +25.5% |
| SU at +25%, pin register 16 | 1,386.0 | 4,060.3 | +22.5% |
| 120 frames (stage remap) | 1,428.2 | 4,197.5 | +26.6% |
| **Pessimistic:** keep every SU.*/HC.* row, pin register 16 | 1,307.5 | 3,908.3 | +17.9% |

- No scenario is a loss.
- The MTP floor (~3,000) is not at risk.
- The DV ledger would hold only the kept rows (≤ 1%), so the 15% design limit is met without an owner exception.

What is not yet measured:
- The slice's SU/HC latencies are the flat-RTL prices plus pin registers. The contingency rows bound the risk.
- The mesh exchange and ring constants are plan stages, not routed numbers.
- Everything stays COMPOSED_NOT_NATIVE until the slice bench and the die trial exist.

## 7. Principles and pitfalls

| Principle / pitfall | How DV meets or avoids it |
|---|---|
| P1 co-locate | VM/SU/HC per slice beside the frames that produce its rows |
| P2 neighbour-only | E/W/N/S mesh links, ≤ 405 µm hops, fixed time of flight |
| P3 trees not stars | Norm, router, coefficients and MTP items are tiny mesh/ctl payloads; the cross-die collective joins the ring at the edges |
| P4 one square slice ×16 | 1.70 × 2.60 mm; regional roots |
| P5 priced before RTL | This document |
| Long thin blocks | None: the largest aspect is 2.1:1 except the PHY-shaped service halves, which are unchanged from today |
| Hold padding | Hold goes to relay stations and the die budget (FLOW-HOLD) |
| Flat 10 M-net GRT | The die is hierarchical: 16 slice clusters + frames + relay chains (die_cluster flow) |

## 8. Reuse and new work

**Closed or bindable views reused:**
- Frames as they are: Q elements, ROM, cfg7, return nodes, qbank, BF front roots, relays/stations, and the cfifo_crs r5f view (native PASS, c2e5317db).
- HC cth.
- VM bgq28h.
- SU lane leaves (sml_u65, smd_u65, swe, qne, kve, kvq, qbt*).
- SM softmax tiles.
- 536/566 relay classes.

**New:**
- Slice top (control, descriptors, ring stop, capture, x-chain head, combiner).
- G-unit wrapper.
- Collective edge engine (fold engine reused from `ot_w15_rom_oneshot`).
- Service halves.
- Compiler: row placement by ownership, mesh time slots.

**Deliverable 3 order:**
1. Slice RTL bit-exact against `hdc_golden_v41` (chunk8) on the S81 SU/HC cases, with a 16-slice exchange bench for the norm.
2. Slice closure via submit_exact.
3. Hierarchical die trial (die_cluster).
