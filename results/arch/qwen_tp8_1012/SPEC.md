# Qwen3-8B ROM at TP8: top-down spec (owner decision 2026-10-12)

Stream `qwen-tp8` (log `/home/ubuntu/claude-takeover-20261007/el1011-qwen-tp8.log`). It runs in parallel with the TP4 r22ko4 element and die work, which continues untouched until this plan replaces it.

All numbers come from `gen.py` in this directory, which writes `tp8.json`. Every throughput figure is **modelled**: it takes the TP4 ROM+KV-die token path (`results/arch/token_path_20261009/qwen_rom.json`, 249,431 cycles = 4,810.9 tok/s, grades as recorded there) and applies the TP8 deltas listed in section 6. No TP8 RTL run exists yet.

Two tracks, as the owner directed:

- **Track A (baseline, low risk).** Eight TP8 ROM dies, each paired 1:1 with the existing KV die. The KV die is unchanged; it is the closest block to done (die GRT overflow 0, TT +88.90, FF +17.51).
- **Track B (target if it holds).** A single die type: the TP8 ROM die with the KV die's function merged in, so HBM attaches directly to the ROM die.

## 1. Weight shard, ROM bits, tile count

Model: hidden 4,096, 36 layers, 32 Q / 8 KV heads of 128, FFN 12,288, vocab 151,936. Weights are signed INT8 with one BF16 row scale. The embedding table is in HBM. The LM head is untied and stored in ROM.

- INT8 ROM weights in total: 36 × (2·4096² + 2·4096·1024 + 3·4096·12288) + 151,936·4096 = **7.568 GB**.
  - TP4: 1.892 GB = 15.14 Gbit per die.
  - TP8: 0.946 GB = 7.57 Gbit per die.
- Engine geometry (`tools/hdc_qwen_fullshape_placement_w12.py`, RTL K-split rule):
  - One code word is 8 × 16 lanes × G bits, where G is the number of lane groups per die.
  - Each tile has 4 lane groups. The tile is `ot_qwen_rom_tile_nk`: 2 group-pair columns × `CODE_BANKS` banks, each bank an `ot_rom_4096x266_m8` macro of 4,096 words.

| | G (groups/die) | tiles/die | code words/die | bits/word | code bits/die | banks/column | macros/tile | bank fill |
|---|---|---|---|---|---|---|---|---|
| TP4 (today) | 6,144 | **1,536** | 20,016 | 786,432 | 15.74 Gbit | 5 | 10 | 97.7% |
| TP8, same G | 6,144 | 1,536 | 10,016 | 786,432 | 7.88 Gbit | 3 | 6 | 81.5% |
| **TP8, chosen** | **3,072** | **768** | **20,032** | 393,216 | 7.88 Gbit | **5** | **10** | 97.8% |

**Where 1,536 comes from (TP4).** Words per die = Σ over the 36 layers of the stream words (qkv 64 + o 48 + gate_up 256 + down 144 = 512 per layer), plus the LM head (1,584), giving 20,016. That fits in 5 banks × 4,096 = 20,480 words per column. A G of 6,144 groups at 4 groups per tile is 1,536 tiles.

**TP8 at G = 3,072.** It has the **same 20,032 words** (512 per layer + 1,600 for the LM head), so the tile keeps **the same master, outline, pins and 10 ROM macros** (`CODE_BANKS` 5). Its only change is the synthesis parameter `GT` 6,144 → 3,072: the issue loop's per-round constants derive from the die's group count (`ot_qwen_w12_matvec.sv`). That means one re-synthesis and one re-route of the replicated cluster. The TP4 view stays valid as a die placeholder because its faces are identical. There are **768 tiles per die**: the weight bits halve and so does the tile count, with the stream length per die unchanged.

TP8 at G = 6,144 would halve the stream instead, but it keeps 1,536 shorter tiles (6 macros each), frees no area and needs a new tile. It is rejected.

- **Scales:** 452,144 scale rows per die (TP4: 609,376). The scale ROM lives in the slab port groups and their count halves (section 2).
- **Lane utilisation** stays the same: qkv / gate_up 1.0, o / down 0.889, head 0.989.

## 2. Heads, FFN slice, embedding and LM head per die

- **Attention:** 4 Q heads + 1 KV head per die. The GQA group stays whole, and TP8 is the largest split that does not replicate KV heads. The QKV output is (4 + 2) × 128 = 768 rows (TP4: 1,536). `o_proj` uses K = 512 per die and is row-parallel, producing a 4,096-row partial sum.
- **FFN:** gate/up are 3,072 rows per die (1,536 + 1,536). `down` uses K = 1,536 per die, producing a 4,096-row partial sum.
- **LM head:** 151,936 / 8 = 18,992 vocab rows per die (1,600 words). The (max, index) argmax is gathered over 8 dies through the collective, adding about 10 cycles.
- **Embedding:** stays in HBM. The row fetch is 16 KiB per token.
  - Track A: the fetch goes through the KV die over the existing link.
  - Track B: the fetch is on-die.
- **SU work per die halves** where it scales with heads: q/k norm with RoPE, and softmax normalisation. RMSNorm and the residual stay replicated over the full hidden vector.
- **Constant ROM contents** (`qfd_crom_g`: q/k-norm weights, RoPE tables, row scales) are re-imaged per die. The macros stay the same.
- **Tree and bands:** 768 tiles = 3 bands of 256 tiles (TP4: 6 bands).
  - Band, tree-top and slab elements keep their per-band shape, so the band count halves.
  - The tree top (`qfd_tt_up4`) adds 3 band words instead of 6. This is a parameter change on its band count.

**One die type, eight ROM images.** Every TP8 die is the same design. The ROM code layer differs per die rank (8 via-mask personalities, as TP4 has 4). This is the same manufacturing model as today; only the count rises from 4 to 8.

## 3. Collective (both tracks)

**Topology.** 8 dies in 4 B200-class packages (2 dies per package), with a fully connected K4 board between the packages.

- The two dies in a package are the same die type, the second rotated 180°. They abut on the UCIe edge.

**All-reduce algorithm: two-level, rank-ordered, bit-exact.**

1. **In-package exchange over UCIe.** Each die sends its full FP32 partial vector (4,096 words, 16 KiB) to its peer, and both fold `p = d0 + d1` in fixed order. UCIe x64 at about 4.2 TB/s puts 16 KiB on the wire in about 5 cycles, plus a hop of about 14 cycles.
2. **Cross-package one-shot on halves.** Die *i* of each package owns half *i* of the hidden vector (2,048 words, 8 KiB). It sends that half to die *i* of the 3 other packages and folds the 4 package sums in fixed package order: ((p0 + p1) + p2) + p3. This step is the existing 4-input rank-ordered fold, reused at half width.
3. **In-package all-gather over UCIe.** The two dies swap their owned halves.

The fold tree is identical on every die, so the result is bit-exact on all 8 dies. The golden (`compiler`) must use the same order.

**Links per die:**

| Link | Count | Payload per all-reduce |
|---|---|---|
| UCIe x64 (in-package peer) | 1, as TP4 | 16 KiB + 8 KiB |
| 112G SerDes x12 PHY + adapter (one per remote package) | **3** (TP4: 2 off-package destinations through 1 adapter) | 8 KiB each |

- Per link, 8 KiB within the 128-cycle serialisation window is about 77 GB/s. One x12 112G PHY (about 150 GB/s after RS(544,514) FEC) gives about 2× headroom.
- Per package: 6 board links, 2 to each neighbour.

**Latency budget per all-reduce.**

| | Cycles |
|---|---|
| TP4, measured (`qfd_io_collective` path) | 1,121 / 979 |
| TP8, central | TP4 − 128 (serialisation of 8 KiB instead of 16 KiB) + 2 × (14 UCIe + 26 on-die relays) + 5 (one more fold level) ≈ TP4 |
| TP8, conservative | TP4 + 100 |
| Board crossing LAT | 339, unchanged (measured) |

**Without K4.** On a 2×2 board mesh, the diagonal package pair is relayed (about +340 cycles per all-reduce). K4 is therefore a **hard requirement**, as in the 10-09 study.

**Element impact.** `qfd_io_collective` changes:

- an in-package 2-input pre-fold stage and an owner-half select / all-gather stage around the existing 4-rank fold;
- 1 UCIe port and 3 SerDes ports (TP4: UCIe + 1 SerDes adapter carrying 2 destinations);
- `ot_coll_fold_slice` reused at half width.

This counts as a REDESIGN of the cluster with closed children reused. See the element table.

## 4. KV path: track A (paired KV die) vs track B (KV merged)

KV is FP8 E4M3 K and V codes. At P8191 one user needs 36 × (1 KV head) × 128 × 2 × 8,192 = **75.5 MB per die** (TP4: 151 MB). HBM3E is taken as 24 GB and about 1.0 TB/s per stack, as in the KV-die contract.

| | Track A: TP8 ROM + KV die (1:1) | Track B4: merged, 4 stacks/die | Track B2: merged, 2 stacks/die |
|---|---|---|---|
| Dies per instance | 8 ROM + 8 KV (2 types) | **8 (1 type)** | 8 (1 type) |
| HBM stacks / instance | 32 | 32 | 16 |
| KV capacity per die | 96 GB → 1,271 users | 96 GB → 1,271 users | 48 GB → 635 users |
| Users before KV-bandwidth bound (prefetch over the layer) | 9.2 | 8.8 | 4.8 |
| Deployment batch need | ~5 (tile-window saturation, 10-09 study) | ~5 | ~5 (marginal) |
| HBM PHYs per die, shoreline | (KV die: 4 × 12.0 mm on its E/W edges) | 4 PHYs (10 mm² each), 2 on N + 2 on S edge (24 mm of 25 mm each) | 2 PHYs, 1 on N + 1 on S |
| ROM↔KV crossing | UCIe x64 pair (rom_end / kv_end), measured +455 cycles/layer in attention | on-die registered link (~100 cycles) | on-die |
| Package | 2 ROM + 2 KV dies + 8 stacks (~2.4k mm² interposer) | **2 dies + 8 stacks: exactly B200-class** | 2 dies + 4 stacks |

**Capacity is never the limit.** Even one stack per die holds about 300 users. HBM bandwidth decides the stack count:

- At 1 KV head over 128 pseudo-channels (4 stacks), the attention window halves relative to TP4.
- With 2 stacks, it stays at the TP4 per-user time.

**KV hub elements under B.** Each element's die-to-die interface becomes on-die:

- `ot_qkvd_rom_end` + `ot_qkvd_kv_end` + 2 × `ot_qkvd_ucie_x64_phy` + `qfd_d2d_rom` / `qkd_d2d`: dropped from the die. The two ends' word streams (q, new K/V, result, embedding request/data) become **direct registered relay links** between the SU / vector-memory / sequencer faces and the KV region's hub ports. Credit flow is kept and runs on one clock. The CDC stays at the HBM controller boundary (`qkd_cdc_wleaf`), as on the KV die today.
  - Lowest-risk first step: keep `rom_end` / `kv_end` back-to-back without the PHY (REUSE), then remove them.
- Unchanged in function and interface, re-placed as region slots of the merged die: `ot_nhb_*` (pbst / pvlg / zh), `ot_qwen_nearhbm_attn_hub_t/p`, `ot_qkh_ktree` / `ot_qkh_lane8`, `qkd_rhead`, ectl, kvwq, land, astk, ctrl.
  - Their head count per die is 1 instead of 2. The KV-die head configuration (row-engine head assignment and the sequencer program) is the only change.
  - Under track A this is the same change to the KV die's program, made without touching its physical work.

**Area and slot share** (contract v5 slot areas, scaled per cell):

| | Die | Slots | Slot share | Channels |
|---|---|---|---|---|
| TP4 r22ko4 | 25.04 × 32.80 = 821 mm² | 592.4 mm² | 72.1% | 27.9% |
| Track A ROM die | 25.0 × 23.0 = 575 mm² | 320.8 mm² | **55.8%** | 44.2% |
| Track A KV die (unchanged) | 8.37 × 24.59 = 205.8 mm² | 121.5 mm² | 59.0% | |
| Track B merged die | 25.0 × 31.0 = 775 mm² (90% of reticle) | 436.5 mm² (ROM 319.8 + KV 116.7) | **56.3%** | 43.7% |

**Throughput (P8191, AR; section 6):**

| Case | tok/s | vs TP4 (4,810.9) |
|---|---|---|
| A, central | 5,605.5 | +16.5% |
| A, conservative | 4,675.5 | −2.8% |
| B4, central | 5,839.5 | **+21.4%, +4.2% over A** |
| B4, conservative | 4,920.5 | +2.3% |
| B2, central | 5,358.9 | +11.4% |

**Recommendation.**

- **Build track A now.** Every A change (tile reuse, 768-tile floorplan, bands, sequencer/VM head parameters, the 8-way collective) is shared with B. The KV die stays as it is apart from its head-count program.
- **Adopt track B (merged die, 4 stacks per die) as the TP8 target, gated on one milestone:** the A ROM-die iteration reaching GRT overflow 0 with real tile views.
- **Why B:** its numbers close. It gives:
  - 56.3% slots on a 775 mm² die with 83 mm² of reticle margin;
  - a B200-class package;
  - 32 stacks covering a batch of about 9;
  - +4.2% per user over A by removing the UCIe attention crossing;
  - **one die type, one package type**.
- **Trade-off:** schedule risk moves into one die-level integration. The KV side is already closed as its own die, so under B its regions transplant as two strips (W and E halves of the KV die become the N and S strips under the HBM PHYs). B is not adopted before the A ROM die converges.
- **B2 is rejected:** it saves 16 stacks but sits at the batch margin (4.8 vs about 5) and loses 8% per user.

## 5. Die floorplan targets

**Track A ROM die: 25.0 × 23.0 mm.**

- **Tile array:** 64 tile columns × 12 rows of `qfd_tile_nk` (267 × 1,291.7 µm, pitch about 320 µm including the `qfd_cst` channel). That is 20.5 × 15.5 mm, with the TP4 spine column (VM, seq, SU, ctlm) in the middle as today.
- **Bands:** 3 bands of 4 rows × 64 columns.
- **IO band** along N (1.56 mm): UCIe 6.4 mm, collective 2.3 mm, 3 × SerDes 2.56 mm, xfifo.
- **To the KV die:** UCIe x64 PHY + `qfd_d2d_rom` on S, as TP4.

**Track B die: 25.0 × 31.0 mm.**

- Same tile, spine and IO arrangement, with the IO on the W/E edges.
- N and S strips, about 3.4 mm deep each: 2 HBM3E PHYs on the edge, then ctrl / land / astk / rhead / ectl / kvwq / cdc rows facing the array.
- The UCIe peer edge is E. The second die in the package is rotated 180°.

**Rules (both tracks):**

| Rule | Target |
|---|---|
| Slot share | ≤ 60% (A 55.8%, B 56.3%) |
| Channels | ≥ 35% (A 44%, B 44%) |
| Relay pitch | ≤ 500 µm of wire per stage (504 µm SS reach); last segment ≤ ~100 µm into an unregistered input |
| Seam relays | die_top_logic, regenerated by the generator |
| Layers | die top M8/M9 only; slots pg M6, strap M7 (die strap M8); `qfd_tile_nk` signal_max M7 (contract D6); other elements signal_max M6, clock entry M6 (D1) |
| Seam check | as contract v5 `seam_check` (die_audit hops_over 0, clock plan 0 violations, GRT overflow 0, TT ≥ 0 / FF ≥ 0 after pads) |

**Congestion lesson from r22ko4.** GRT overflow was 155k on M6/M8 H, with a 72% slot share and a 2D residual at the option-4 constant-buffer word row. At about 56% slots with 44% channels, the M6/M8 H supply per tile row roughly doubles. The generator must still route the cbuf word row in a channel and not across tile rows.

## 6. Throughput composition (P8191, AR, 1.2 GHz)

Basis: the TP4 L1 layer row is 6,835 cycles. Its contents:

| Item | Cycles | Grade |
|---|---|---|
| qkv | 259 | |
| qknorm_rope | 101 | |
| attn_kv | 1,816 | measured through the link |
| o | 382 | |
| AR1 | 1,121 | measured |
| rmsnorm | 15 + 91 | |
| gate_up | 632 | |
| down | 370 | |
| AR2 | 979 | measured |
| residual | 1,067 | includes 821 of split-station / issue relays |

Head: 3,101 (measured). Embedding fetch: 272.

TP8 deltas per die:

| Item | Delta | Reason |
|---|---|---|
| Matvec stream (qkv / o / gate_up / down) | 0 | words per die unchanged at G = 3,072 |
| Die relays (95/op priced) and split relays (821) | × 0.65 (A) / × 0.75 (B) central; × 1 conservative | the A die is 23 mm tall, not 32.8 |
| qknorm_rope | × 0.5 | 4 + 1 heads instead of 8 + 2 |
| attn_kv, A | 849 + 455 | measured link crossing kept; 849 = engine at 1 KV head over 128 PCs |
| attn_kv, B4 | 849 + 100 | on-die |
| attn_kv, B2 | 1,361 + 100 | |
| Conservative attention | TP4 window kept | |
| All-reduce | 0 central / +100 conservative, each | section 3 |
| Head | +16 words + 10 argmax gather | |
| Embedding | 150 on-die (B) | |

The results are in the table in section 4.

**What is not charged:**

- DSpark MTP (AR only, as the basis).
- The SerDes always-on lane power of 3 × x12 PHYs per die.
- The batch aggregate, which stays a modelled ceiling.

## 7. Element impact

See `ELEMENT_IMPACT.md` (same directory) for the classified table: REUSE / PARAMETER CHANGE / REDESIGN, with reason and RTL file for each element. The contract is `results/arch/hier_contract_1012/qwen_rom_tp8.json`.
