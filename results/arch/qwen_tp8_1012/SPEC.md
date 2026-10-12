# Qwen3-8B ROM at TP8: top-down spec (owner decision 2026-10-12)

Stream `qwen-tp8` (log `/home/ubuntu/claude-takeover-20261007/el1011-qwen-tp8.log`). It runs in parallel with the TP4 r22ko4 element and die work, which continues untouched until this plan replaces it.

All numbers come from `gen.py` in this directory, which writes `tp8.json` and the tables between the `GEN` markers below. The cut inputs come from `cuts.py` (`cuts.json`), which measures the die generators' bus networks. Every throughput figure is **modelled**: it takes the TP4 ROM+KV-die token path (`results/arch/token_path_20261009/qwen_rom.json`, 249,431 cycles = 4,810.9 tok/s, grades as recorded there) and applies the TP8 deltas listed in section 6. No TP8 RTL token run exists yet.

**Die of record (owner, 2026-10-12): track B, a single die type.** It is the TP8 ROM die with the KV die's function merged in, so the HBM stacks attach directly to it. Eight identical dies (eight ROM personalities) in four B200-class packages of 2 dies + 8 stacks. The floorplan is **F2** (section 0).

**Fallback (recorded, not built): track A.** Eight TP8 ROM dies, each paired 1:1 with the existing KV die over the UCIe x64 pair. Every ROM-side change of B (tile, bands, sequencer/VM parameters, the 8-way collective) is also an A change, so A remains reachable by re-adding `qfd_d2d_rom` + the UCIe PHY and keeping the KV die as it is apart from its 1-head program. A costs a second die type and the measured +455-cycle-per-layer attention crossing (section 6). Its ROM die re-fits to about 27.9 x 23.0 mm at the 311-um tile slot.

## 0. CUT ANALYSIS BEFORE RTL

Owner rule (2026-10-12): every new die architecture carries, before RTL, the bits that must cross each major cut line per cycle against the usable tracks there, at a target of 0.55-0.60 of capacity, for each candidate floorplan. This section is that analysis for the merged die.

### 0.1 Method

- **Networks, not estimates.** `cuts.py` takes the relay-staged bus networks of the die generators: the TP8 ROM core as generated today (`tp8a`, 768 tiles, `claude/el1011-qwen-tp8-die` a13e30ceb), the KV die with its closed flags, and r22ko4 for calibration. Each bus segment runs from the pin on one block's face toward its peer to the pin on the peer's face. Clock nets are left out (one CTS tree each, in the spine channel).
- **Capacity.** ASAP7 pitches are M4/M5 48 nm, M6/M7 64 nm and M8/M9 80 nm. A vertical cut is crossed by horizontal layers and a horizontal cut by vertical ones.
  - Over a hard block, only the die layer counts (M8 or M9), at 75% after the die PDN. Blocks own M1-M7 by the layer contract.
  - In a channel, add M6/M7 at 75% and M4/M5 at 50%. That gives 9.4 tracks/um over a block and 31.5 tracks/um in a channel.
  - For an abutted face, the pin rule is 2 tracks a bit on 2 pin layers, that is face length / 0.048 um bits.
- **Two window sizes.**
  - *Coarse:* one tile row pitch, one column pitch, the spine column or the IO band.
  - *Fine:* 260 um, half a row gap. This is the scale at which stacked words overflow GRT.
- **Calibration of the fine scan on measured dies:**
  - r22ko4, with die GRT overflow 155k on M6/M8 H, peaks at **1.05**. The cause is tree-root words stacked in one row, which is the e9 finding.
  - The closed KV die, with GRT overflow 0, peaks at **0.87**, on a single block-local bundle.
  - We design to **0.55**.

### 0.2 Candidate floorplans

The merged die needs 4 HBM3E PHYs. Each is 0.83 x 12.0 mm, so the PHYs need 48 mm of shoreline on two die edges. The coordinator fixed the tile slot at 311.04 x 1,296 um (the lsl6 tile needs at least 288 um; par kit `physical/ref_tile/qfd_tile_nk_tp8.json`). That makes the 64-column core of track A 27.9 mm wide before any HBM strip is added.

<!-- GEN:FLOORPLANS -->
|  | arrangement | die (mm) | mm² | fits 26 x 33 | slot share |
|---|---|---|---|---|---|
| F1 | 64 cols x 12 rows (tp8a core), KV-die halves rotated into N and S strips under 2 HBM PHYs each, IO on the W/E edges | 29.48 x 28.90 | 851.8 | **no** | 56.5% |
| F2 | 48 cols x 16 rows, KV-die W half on the die W edge and E half on the E edge UNROTATED (2 HBM PHYs per edge), KV centre blocks (seq/host/ahub/embgw) in the ROM spine, all IO (UCIe peer, collective, xfifo, 3 SerDes) in one S band + 400-um IO word channel | 31.17 x 25.78 | 803.7 | yes | 59.9% |
<!-- /GEN:FLOORPLANS -->

- **F1 does not fit the reticle.** Both axes exceed 26 mm. This is the earlier SPEC's B layout re-done at the 311-um slot. Its column cut is also over target at the 52.7-um corridor (0.56, table below).
- **F2 fits** at 31.2 x 25.8 mm, with 1.8 mm and 0.2 mm of margin on the 33-mm and 26-mm axes. Its slot share is 59.9% (≤ 60%).
  - The 83.5-um column channel is chosen to bring the slot share to 60%, and it is also the column-cut fix.
  - The 190-um row gap is what the 26-mm axis leaves after the S IO band (1,564 um) and the 400-um IO word channel.
- **F2 keeps the KV region's internal geometry.** The KV die's W half (x 0-3.7 mm, 2 PHYs on its W edge) becomes the die's W strip. The E half becomes the E strip, unrotated. The cuts the KV die closed at GRT overflow 0 therefore stay as they were. Only the centre column moves: `qkd_seq`, `qkd_host`, `qkd_ahub`, `qkd_embgw` and `qkd_pll` go into the KV-centre sub-column of the ROM spine, while the UCIe pair and the clock/reset bump pair are removed.
  - **Amendment (coord decisions 2026-10-12):**
    - *Clock.* `qkd_pll` stays: it is the die's only clock and reset source. Before the merge, the ROM's `clk_rx` was fed by the KV PLL through `ckb_kv -> ckb_rom`, so removing the PLL would leave the die unclocked. Its `pll_fwd` / `rso_fwd` outputs now drive `clk_rx` directly. `ckb_kv`, `ckb_rom`, `rs_bump` and their `clk_d2d` / `rst_d2d` / `rst_fwd_s` nets are dropped, along with the bump-side reset synchroniser.
    - *Host link.* The 2,085-b `host_fdi` word between `qkd_host` and its SerDes is kept. It ends on a dedicated host SerDes port in the S IO band: one more IO-band port, which the contract gives a slot. Its word counts in the IO-word-channel cut (`cuts.py`, next regeneration).

**Chosen: F2.** Every cut is at or under 0.55 (table below), and F2 is the only candidate that fits the reticle.

### 0.3 Per-cut budgets (bits per cycle vs usable tracks)

<!-- GEN:CUTS -->
| cut | plan | bits/cycle (parts) | usable tracks | util | rule that holds it |
|---|---|---|---|---|---|
| tile row H (1 row pitch, vertical cut at the spine face) | F1 | 9,660 (tree_block 2,048, block_roots 1,024, other 444, serdes_words 6,144) | 28,486 | 0.34 | block roots spread over the 4 rows of a block-row (root row = r0 + blockcol mod 4), <= 2 root/band words per row; KV links (F2) <= 2,048 b per row over >= 4 middle rows; any 260-um sub-window over tiles <= 2 words |
| tile column V (1 column pitch, horizontal cut in a row gap) | F1 | 2,557 (station_corridor 509, tree_legs 1,536, band_word 512) | 4,577 | **0.56** | the vertical legs of a 4x4 block spread over its 4 columns (<= 3 words per column pitch), legs in the column channel |
| spine column V (worst y) | F1 | 19,037 (rom_spine 9,109, kv_centre 2,153, kv_strip_to_spine 7,775) | 92,959 | 0.20 | measured tp8a spine + KV-die centre column (F1: + one KV strip running N/S to the spine) |
| KV region <-> core boundary (worst 1,496-um window, channel) | F1 | 4,326 (kv_words 4,326) | 47,140 | 0.09 | KV halves keep their internal geometry (KV die GRT overflow 0); boundary is a 100-um channel |
| tile row H (1 row pitch, vertical cut at the spine face) | F2 | 5,564 (tree_block 2,048, block_roots 1,024, kv_links 2,048, other 444) | 18,137 | 0.31 | block roots spread over the 4 rows of a block-row (root row = r0 + blockcol mod 4), <= 2 root/band words per row; KV links (F2) <= 2,048 b per row over >= 4 middle rows; any 260-um sub-window over tiles <= 2 words |
| tile column V (1 column pitch, horizontal cut in a row gap) | F2 | 2,557 (station_corridor 509, tree_legs 1,536, band_word 512) | 5,547 | 0.46 | the vertical legs of a 4x4 block spread over its 4 columns (<= 3 words per column pitch), legs in the column channel |
| spine column V (worst y) | F2 | 11,262 (rom_spine 9,109, kv_centre 2,153) | 92,959 | 0.12 | measured tp8a spine + KV-die centre column (F1: + one KV strip running N/S to the spine) |
| KV region <-> core boundary (worst 1,496-um window, channel) | F2 | 4,326 (kv_words 4,326) | 47,140 | 0.09 | KV halves keep their internal geometry (KV die GRT overflow 0); boundary is a 100-um channel |
| HBM PHY DFI face (per PHY, abutted) | F1/F2 | 9,207 | 250,000 | 0.04 | face pin rule (face um / 0.048) |
| IO word channel (vertical cut, 400-um channel under the IO band) | F2 | 4,096 (serdes_words 4,096) | 12,604 | 0.33 | xfifo and UCIe abut the collective; SerDes split 1 W / 2 E of the collective so <= 2 SerDes word pairs cross any x |
| crom -> cbuf word row (channel) | F1/F2 | 2,462 (crom 2,462) | 4,727 | 0.52 | >= 150-um channel for the constant-buffer word row |
| stack face: VM S <-> SU N (abutted) | F1/F2 | 8,511 | 16,200 | 0.53 | face pin rule (face um / 0.048) |
| stack face: band_lanes S <-> port_tiles N (abutted) | F1/F2 | 8,192 | 16,200 | 0.51 | face pin rule (face um / 0.048) |
| stack face: tt_up4 W face (NB 3) | F1/F2 | 2,311 | 8,100 | 0.28 | face pin rule (face um / 0.048) |
| stack face: qfd_tile_nk W face (tree words) | F1/F2 | 2,048 | 27,000 | 0.08 | face pin rule (face um / 0.048) |
| stack face: collective E face (2 SerDes x 2,048 b) | F1/F2 | 4,096 | 19,800 | 0.21 | face pin rule (face um / 0.048) |
<!-- /GEN:CUTS -->

**Where the measured inputs come from:**

- **Row cut.** `tree_block` 2,048 b is the largest intra-block leg load of any tp8a row. `other` (sequencer + head chain) is measured the same way.
- **Spine cut.** `rom_spine` 9,109 b is the worst y in the tp8a spine. `kv_centre` 2,153 b is the KV die's centre column.
- **KV boundary.** The KV words crossing the W/E half boundaries total 7,775 b (W) and 6,564 b (E). The worst 1,496-um window carries 4,326 b.

### 0.4 What the as-generated networks show, and the restructures that are now spec

<!-- GEN:HOTSPOTS -->
| network (as generated) | worst 260-um window | bits | usable | util | families |
|---|---|---|---|---|---|
| tp8a_fine_max | y = 21,750 um, 12,480-12,740 | 3,072 | 2,438 | 1.26 | io 3,072 |
| tp8a_fine_tree_max | y = 4,850 um, 18,200-18,460 | 3,004 | 3,605 | 0.833 | tree_block 2,048, tree_spine 512, corridor 444 |
| kv_die_fine_max | y = 19,300 um, 5,460-5,720 | 2,141 | 2,458 | 0.871 | stack_local 2,118, reset 23 |
| r22ko4_fine_max | x = 22,050 um, 22,880-23,140 | 2,560 | 2,438 | 1.05 | tree_spine 1,536, tree_block 1,024 |
<!-- /GEN:HOTSPOTS -->

Every cut above 0.60 is restructured. These rules are binding on the die generator (`tp8b` recipe) and the contract:

1. **IO band (1.26 as generated).** In tp8a, SerDes and xfifo words cross over the collective block on M8 only.
   - Under F2, the xfifo and the UCIe adapter abut the collective's faces.
   - The SerDes sit 1 W / 2 E of the collective, so at most 2 SerDes word pairs (2 x 2,048 b) cross any x.
   - Those words run in a **400-um IO word channel** with no blocks, between the IO band and the core: 0.33.
2. **Tree trunk columns (0.83 as generated).** All 4 vertical legs of a 4x4 block share one column window.
   - The legs of a block spread over its 4 columns, at most 3 words per column pitch.
   - They run in the 83.5-um column channel: 0.46.
3. **Constant-buffer word row (0.93 as generated).** The `qfd_crom_g` -> `qfd_su_cbuf_g` words go in a channel of at least 150 um: 0.52.
4. **Tree roots (r22ko4 1.05; TP4 e9).** The greedy Morton host choice put every 4x4 block root and the 16 band words of a band into ONE tile row.
   - Spread the roots: the root row is r0 + (block column mod 4).
   - Assign corridors explicitly, so no tile row carries more than 2 root/band words (1,024 b) toward the spine.
   - Any 260-um window over tiles carries at most 2 words.
5. **Balanced legs.** Every tree node sees equal relay depth from every leaf, including the band level (near blocks and near bands are padded to the farthest). This is what lets the `array_placed` no-deskew seam bench hold (tp8a: 0/720 misaligned as placed).
   - Pad relays get reserved sites in the row gaps before the bulk relays are placed. This is the open tp8a item: 119 pad-junction hops over 500 um.
6. **KV <-> spine links (F2).**
   - About 8 kb per side crosses the 24-column half array.
   - It is spread over at least 4 middle rows (≤ 2,048 b per row) and routed on M8 over the tiles.
   - Row gaps carry only tree pads and relays (≤ 3.5 kb per gap).

**Bands under F2.** There are 3 bands of 16 blocks (4x4 tiles). The 16 rows form 4 block-rows of 12 blocks, 6 on each side of the spine. Bands are compact:

| Band | Blocks |
|---|---|
| 0 | block-row 0, plus the 4 near-spine blocks of block-row 1 |
| 1 | the other 8 blocks of block-row 1, plus the 8 near-spine blocks of block-row 2 |
| 2 | the other 4 blocks of block-row 2, plus block-row 3 |

Each band's `qfd_sp_band_lanes` / `res_ser` / port group sits in the spine at the band's centroid.

### 0.5 Per-unit throughput budget

Each unit is sized so that it streams without stalling the token path (B4 central basis, section 6). A unit qualifies only with a production-shape throughput bench within 10% of this budget (AGENTS, throughput qualification).

<!-- GEN:UNITS -->
| unit | throughput budget | basis |
|---|---|---|
| qfd_tile_nk (768) | 1 code word (2 x 266-b macro reads) per cycle per tile, stall-free over 512 words/layer + 1,600 head words | stream words/die unchanged at G 3,072 |
| block tree + band tree | 1 reduced 16-lane FP32 word (512 b) per cycle per band, equal relay depth at every node (no deskew) | 3 band words/cycle into tt_up4 |
| qfd_sp_band_lanes / res_ser / port_tiles (x3 / x3 / x6 groups) | 1 band word per cycle per band; 1 scale row per cycle per port group | TP4 per-band shape |
| qfd_tt_up4 / tt_ctlm | 1 combined word per cycle (NB 3: one adder level) |  |
| qfd_sp_vector_memory / su64_sfu | 4,096-wide FP32 vector in 32 cycles at 4,096 b/cycle (VM <-> collective) | RMSNorm/residual over full hidden |
| qfd_io_collective (2-level) | all-reduce <= TP4 measured 1,121 / 979 cycles (central) | section 3 |
| qfd_io_serdes (x3) | 8 KiB per all-reduce per link in <= 128 cycles = 512 b/cycle/direction payload; 1,024-b adapter word (2x) | x12 112G PHY ~150 GB/s |
| qfd_io_ucie (in-package peer) | 16 KiB + 8 KiB per all-reduce at 1,024 b/cycle/direction (16 + 8 cycles payload) |  |
| KV region (128 rheads, 32 ectl, astk, land, ctrl, 4 HBM PHYs) | attention <= 849 cycles/layer at 1 KV head over 128 PCs; HBM 4 x 1.0 TB/s = 3,333 B/cycle | B4 central |
| KV <-> SU/VM on-die links (replace rom_end/kv_end) | q / new K,V / result per layer in <= 100 cycles incl. ~8 relays each way | credit flow, one clock |
| embedding gateway (qkd_embgw, on-die) | 16 KiB row per token in <= 150 cycles = >= 874 b/cycle (a 513-b word takes 256 cycles: widen to 1,024 b or charge +106 cycles/token) | B4 central assumes 150 |
<!-- /GEN:UNITS -->

### 0.6 Early die prototyping with placeholder views

Before the tiles close, the die is prototyped on placeholder views:

- **Tiles:**
  - `qfd_tile_nk`: an exact-shape 311.04 x 1,296 abstract with the TP4 pin plan (identical faces), until `qfd_tile_nk_tp8` routes.
  - `qfd_port_tiles` / `qfd_tt_up4`: the TP8 kits (`*_tp8*`).
  - The collective: the 1166.4 x 950.4 cluster outline.
- **KV strips:** the KV die's closed element views at their KV-die coordinates.
- **Flow:** the `tp8b` generator recipe (F2) runs the same seam benches (array_placed no-deskew, p2p, credit) and the die chain (die_audit hops_over 0, clock plan 0 violations, GRT overflow 0, TT >= 0 / FF >= 0 after pads) as tp8a it1.
- **Re-budget:** the cut table above is re-derived from each iteration's GRT layer usage.

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

## 3. Collective

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

## 4. KV path (track B, merged): stacks, capacity, area

KV is FP8 E4M3 K and V codes. At P8191 one user needs 36 x (1 KV head) x 128 x 2 x 8,192 = **75.5 MB per die** (TP4: 151 MB). HBM3E is taken as 24 GB and about 1.0 TB/s per stack, as in the KV-die contract.

| | **B4: merged, 4 stacks/die (of record)** | B2: merged, 2 stacks/die | A (fallback): TP8 ROM + KV die |
|---|---|---|---|
| Dies per instance | **8 (1 type)** | 8 (1 type) | 8 ROM + 8 KV (2 types) |
| HBM stacks / instance | 32 | 16 | 32 |
| KV capacity per die | 96 GB -> 1,271 users | 48 GB -> 635 users | 96 GB -> 1,271 users |
| Users before KV-bandwidth bound | 8.8 | 4.8 | 9.2 |
| HBM PHYs per die | 4, 2 on the W and 2 on the E edge (F2) | 2 | on the KV die |
| ROM<->KV crossing | on-die registered links (~100 cycles) | on-die | UCIe x64 pair, measured +455 cycles/layer |
| Package | **2 dies + 8 stacks: B200-class** | 2 dies + 4 stacks | 2 ROM + 2 KV dies + 8 stacks |

- **Capacity is never the limit.** Even one stack per die holds about 300 users. HBM bandwidth decides the stack count:
  - with 1 KV head over 128 pseudo-channels (4 stacks), the attention window halves relative to TP4;
  - with 2 stacks, it stays at the TP4 per-user time.
- **B2 is rejected.** It sits at the batch margin (4.8 users vs about 5 needed) and loses 8% per user.

**KV elements under B.** The die-to-die interface becomes on-die:

- `ot_qkvd_rom_end` + `ot_qkvd_kv_end` + 2 x `ot_qkvd_ucie_x64_phy` + `qfd_d2d_rom` / `qkd_d2d` leave the die. The two ends' word streams (q, new K/V, result, embedding request/data) become **direct registered relay links** between the SU / VM / sequencer faces and the KV region's hub ports.
  - Credit flow is kept, on one clock.
  - The CDC stays at the HBM controller boundary (`qkd_cdc_wleaf`), as on the KV die today.
  - Lowest-risk first step: keep `rom_end` / `kv_end` back-to-back without the PHY (REUSE), then remove them.
- These keep their function and interface and are re-placed in the W/E strips with their KV-die geometry: `ot_nhb_*`, `ot_qwen_nearhbm_attn_hub_t/p`, `ot_qkh_*`, `qkd_rhead`, ectl, kvwq, land, astk, ctrl.
  - The head count per die is 1 instead of 2. The row-engine head assignment and the sequencer program are the only change, plus the `ectl_h` NG=1 parameter.

**Area** (contract v5 slot areas scaled per cell; tile slot 311.04 x 1,296):

| | Die | Slots | Slot share |
|---|---|---|---|
| TP4 r22ko4 | 25.04 x 32.80 = 821 mm² | 592.4 mm² | 72.1% |
| **B, F2 (of record)** | **31.17 x 25.78 = 803.7 mm²** (94% of the 858 mm² reticle) | 481.3 mm² (ROM 364.6 + KV 116.7) | **59.9%** |
| B, F1 (rejected) | 29.48 x 28.90 = 851.8 mm²: does not fit 26 x 33 | 481.3 mm² | 56.5% |

**Throughput (P8191, AR; section 6):**

| Case | tok/s | vs TP4 (4,810.9) |
|---|---|---|
| **B4, central** | **5,839.5** | **+21.4%** |
| B4, conservative | 4,920.5 | +2.3% |
| B2, central | 5,358.9 | +11.4% |
| A (fallback), central / conservative | 5,605.5 / 4,675.5 | +16.5% / -2.8% |

## 5. Die floorplan (F2)

**Die: 31.17 x 25.78 mm.** The 33-mm reticle axis runs W-E.

- **W and E strips:** the KV die's halves, each 3.70 mm wide with a 100-um channel to the core. Each has 2 HBM3E PHYs on the die edge (24 of 25.8 mm), then ctrl / cdc / kvwq / land / rhead / ectl / astk facing the core, as on the KV die.
- **Core:** 48 columns x 16 rows of `qfd_tile_nk`.
  - Column pitch 394.54 um: the 311.04 slot plus an 83.5-um column channel that holds the `qfd_cst` station and the vertical tree legs.
  - Row pitch 1,486 um: the 1,296 tile plus a 190-um row gap that holds tree pads and relays.
  - 24 columns on each side of the spine column.
- **Spine column (4.59 mm, mid-die):**
  - from tp8a: VM, SU, tt_ctlm, tt_up4, seq_su, 3 band_lanes, 3 res_ser, 6 port groups, crom/cbuf, clkrx;
  - from the KV-die centre column: qkd_seq / host / ahub / embgw / pll (the die's clock source, wired to clkrx).
- **S band (1,564 um):** UCIe peer PHY + adapter (in-package peer edge; the second die of the package is rotated 180°), the collective with xfifo, 3 collective SerDes, and the host SerDes port (`host_fdi`, 2,085 b, to `qkd_host`). Above it sits the 400-um IO word channel.

**Rules:**

| Rule | Target |
|---|---|
| Slot share | ≤ 60% (59.9%) |
| Cuts | ≤ 0.55 of usable tracks (section 0) |
| Relay pitch | ≤ 500 um of wire per stage; last segment ≤ ~100 um into an unregistered input |
| Seam relays | die_top_logic, regenerated |
| Layers | die top M8/M9 only; slots pg M6, strap M7 (die strap M8); `qfd_tile_nk` signal_max M7 (D6); others signal_max M6, clock entry M6 (D1) |
| Seam check | contract v5 `seam_check` (die_audit hops_over 0, clock plan 0 violations, GRT overflow 0, TT >= 0 / FF >= 0 after pads) |

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

The results are in the table in section 4. The relay scale for B (0.75) predates F2 (25.8 mm tall, 31.2 mm wide); it is kept until the tp8b die iteration measures the relays.

**What is not charged:**

- DSpark MTP (AR only, as the basis).
- The SerDes always-on lane power of 3 × x12 PHYs per die.
- The batch aggregate, which stays a modelled ceiling.

## 7. Element impact

`ELEMENT_IMPACT.md` (same directory, generated from `element_impact.json`) classifies every element of the merged die (ROM side + KV region) as REUSE / PARAMETER CHANGE / REDESIGN / REMOVED. For each element it gives the region on F2, what the element needs, the RTL file and the current TP8 status. The contract is `results/arch/hier_contract_1012/qwen_rom_tp8.json` ([qwen-tp8/die]; v2/v3 move it from tp8a to F2).
