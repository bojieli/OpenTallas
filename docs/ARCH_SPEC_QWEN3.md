# Qwen3-8B decode core: architecture specification (top-down)

Scope: Qwen3-8B (hidden 4,096, 36 layers, 32/8 heads of 128, FFN 12,288,
vocabulary 151,936), greedy and bit-exact against the golden
(`tools/hdc_golden.py`), on two designs. The design point, set by the user,
is **8K context**; 2K is a secondary point.

* **ROM**: the single-reticle Taalas-HC1-class die (N6, 815 mm²) with its
  weights in ROM. By user decision, **users' KV lives in HBM stacks on the ROM
  die**, at every context and batch. The reticle split comes from
  `opentallas.roofline.taalas_hc1_anchor`: ROM 262.0 mm², compute 146.7 mm²,
  and 259.6 mm² of SRAM, now freed and re-budgeted (§4).
* **HBM**: the iso-area comparator, one reticle of logic with 6 HBM3E stacks
  carrying both weights and KV.

6 stacks is the reticle's beachfront. The 60% edge-use rule gives
2 × (26 + 33) mm × 0.6 / 12 mm = 5.9, and the 814 mm² GH100 die carries 6. At
1.0 TB/s a stack and 0.90 sustained, 6 stacks give 5.4 TB/s.

Everything below is computed by `tools/arch_budget_qwen3.py`. It writes
`results/arch/qwen3_budget.json` and is tested by
`tests/test_arch_budget_qwen3.py`. The test includes the **performance gate**:
the RTL-calibrated sequencer model replays the program the core runs, at the
shipped shapes and 8K, against a ratchet that falls as each block lands and
ends at the budget target. The clock is 1.0986 GHz, the slowest routed Qwen3
token-path unit (`ot_hdc_matvec`, ASAP7 TT).

## 1. Requirement and target

Two resources bind on the ROM die:

* **The weight sweep on the MAC lanes.** 7,568,097,280 MACs a token on
  131,072 lanes take 57,740 cycles, a ceiling of 19,027 tok/s. A compute-in-ROM
  weight costs nothing to read, but it still passes through a MAC once per
  token.
* **The KV stream from HBM.** At 8K the cache is 1.21 GB a token in BF16 and
  604 MB in FP8.

The target is the larger of the weight sweep over 55% of the token and the KV
stream over 95% of it:

| context | KV format | KV stream, cycles | target, tok/s | binding |
|---|---|---|---|---|
| **8K** | **FP8 (design point)** | 122,881 | **8,494** <!-- figure: 8,493.7 src="results/arch/qwen3_budget.json#budget.target_tokens_s" name="Qwen3-8B ROM 8K FP8-KV budget target tok/s" --> | KV stream |
| 8K | BF16 | 245,762 | 4,247 | KV stream |
| 8K | 4-bit | 61,440 | 10,465 | weights |
| 2K | any | ≤ 61,440 | 10,465 | weights |

So the design point is **8K with FP8 KV: 129,348 cycles, 8,494 tok/s per
user.** FP8 KV (E4M3, round to nearest even, saturating) is in the golden, the ISA model and the RTL (8a91421a); the scalar core keeps BF16.

On the HBM comparator the bytes over its 6 stacks bind. With the same FP8 KV,
the per-user bound at 8K is 343 tok/s with BF16 weights, 661 with FP8 and
1,379 in the ROM's 3.5-bit format. The target is 95% of each.

## 2. Workload per token (from the graph)

| class | 8K | 2K |
|---|---|---|
| weight MACs (qkv 906 M, o 604 M, gate/up 3,624 M, down 1,812 M, lm_head 622 M) | 7.568 G | 7.568 G |
| attention MACs (Q·K and P·V, each 36 × 32 × 128 × T) | 2,416 M | 604 M |
| KV read, each element once (GQA-shared), BF16 / FP8 | 1,208 / 604 MB | 302 / 151 MB |
| elementwise element-ops (reference graph: three softmax passes) | 29.98 M | 8.75 M |
| dependent stages a layer | 21 (reference graph), 20 (spec, §6) | same |

## 3. Roofline per resource (ROM die, spec widths, FP8 KV)

| resource | 8K cycles | 2K cycles |
|---|---|---|
| weights on 131,072 lanes | 57,740 | 57,740 |
| KV from 6 HBM3E stacks | 122,881 | 30,720 |
| attention on 131,072 lanes | 18,432 | 4,608 |
| elementwise (reference graph) on 1,024 lanes | 29,279 | 8,543 |

## 4. Area: the freed SRAM

KV moved to HBM, so the 259.6 mm² of SRAM is re-budgeted (`area`):

| use | mm² |
|---|---|
| 6 HBM3E PHYs (10 mm² each) | 60.0 |
| KV ring buffer: one layer of 8K FP8 KV plus the refresh cover, 18.7 MB (section 15) | 6.2 |
| the DFlash drafter's ROM (1.05 B parameters at 3.5 bits) | 33.5 |
| the stream unit beyond the compute share (1,024 lanes; estimated) | 12.8 |
| **2 MAC lane copies (the lane multiplier m = 3)** | 138.4 |
| slack | 8.6 |

A lane copy costs 69.2 mm² for all 131,072 lanes. That is 528.08 µm² a lane,
measured: `ot_hdc_lane_copy` is 16 lanes of the exact BF16 multiplier and the
circulating FP32 adder with its interleave registers, sharing the group's
weight word, the split tree, result port and argmax. It routed at 8,449 µm²
and **closed at 1.2 GHz**. The whole matrix-engine lane is 1,071.8 µm². The
route of the whole engine at m = 2 against m = 1 is in flight.

Copies serve speculative slots and batched users: one weight word (or, for
slots, one KV word) feeds m positions. They do not speed a single position.

## 5. Budget and per-block requirements (8K, FP8 KV, batch 1)

Budget, as shares of the 129,348-cycle target:

| share | cycles |
|---|---|
| weights (44.6%) | 57,740 |
| attention (15%) | 19,402 |
| elementwise (10%) | 12,935 |
| exposed dependency latency (30%) | 38,804 |
| control (3%) | 3,880 |

Requirements derived from the budget:

| block | requirement |
|---|---|
| MAC array | 131,072 lanes = 8,192 groups (a power of two: every K-split tiles whole rounds, 0.9999 of ideal); lane multiplier m = 3 |
| attention | ≥ 124,520 lanes busy: Q·K and P·V both K-split over the groups |
| KV in HBM | 6 stacks, 604 MB/token FP8 at 5.4 TB/s (122,881 cycles). Layer l+1's KV (positions < t, data-independent of the token) streams while layer l computes, into an 18.7 MB ring (one layer plus the refresh cover, §15). The token's own K/V row stays on die (tail buffer) and is written back behind the stream. Efficiency ≥ 0.90 of raw peak with refresh on. The controller queue is ≥ 512 beats per pseudo-channel, and a refreshing channel must not stall the others. |
| stream unit | **1,024 elements/cycle**, with lane partials and a 10-level cross-lane pairwise reduction tree |
| dependency | ≤ 54 cycles exposed per dependent stage (38,804 over 36 × 20): tile-granular chaining, never a full-unit drain |
| sequencer | ≤ 3,880 exposed control cycles a token |
| vector buffer | ≥ 262,144 FP32 elements (the score rows 32 × 8K) |
| argmax | a streaming compare tree on the result path (as built) |

## 6. Where the cycles go: analytical DAG, spec chain, calibrated model

All figures are cycles per token at 8K, FP8 KV:

| model | cycles | tok/s |
|---|---|---|
| spec dependency chain, reference graph (SU 1,024, K-split attention, as-built unit latencies) | 165,024 | 6,658 |
| **spec dependency chain** (one-pass softmax, prefetched issue): weights 57,744, attention 18,432, elementwise 9,792, latency 63,252 | **149,940** | 7,327 |
| KV stream (FP8, 6 stacks) | 122,881 | 8,941 |
| calibrated model, before this work (SU 1, split ≤ 8, 7,680 groups; KV on core) | 49,888,993 | 22 |
| calibrated model, K-split attention + 4-bit split + prefetched issue (8fb2059d) | 30,090,973 | 36.5 |
| calibrated model, + the 1,024-lane vector stream unit, normalise-after-sum, per-unit waits (0a23b3fe) | 174,856 | 6,283 |
| calibrated model, + 3-cycle FP units, the row max on the engine, P·V chasing the exp pass by rows | 131,185 | 8,375 |
| calibrated model, at HEAD (+ RMSNorm weights folded into the projections with 1/rms after them, one fused SiLU·up op; FP8 KV) | **123,301** <!-- figure: 123,301 src="results/arch/qwen3_budget.json#as_built_calibrated.8192.cycles" name="Qwen3-8B calibrated HEAD cycles 8K" --> | 8,910 |

The HEAD figure is the RTL's parameters set to the spec's: 8,192 groups, SW =
1,024, and LV = 3 time levels. It is not a shipped-scale simulation.

HEAD is **4.7% under the design point's target** of 129,348 and 0.3% above
the KV stream (122,881): **compute has reached the KV floor**, and the ROM
token at 8K is bound by the KV stream, not by the chain. One decoder layer
(the middle one, of 36) at HEAD:

| stage (cut at the matrix engine's weight-op issues) | cycles | engine busy | exposed |
|---|---|---|---|
| QKV projection, then q/k norm, RoPE | 628 | 192 | 436 |
| attention: scores, softmax, P·V, 1/Z | 872 | 512 | 360 |
| O projection, residual, FFN norm | 223 | 128 | 95 |
| gate/up projection, fused SiLU·up | 1,084 | 768 | 316 |
| down projection, residual, next norm | 479 | 384 | 95 |
| **layer** | **3,286** <!-- figure: 3,286 src="results/arch/qwen3_budget.json#as_built_calibrated.8192.layer_chain.cycles" name="Qwen3-8B calibrated layer chain 8K" --> | 1,984 | 1,302 |

The per-layer share of the KV stream is 3,413 cycles, so a layer's chain
(3,286) now fits under it with 127 cycles to spare. The token adds the LM
head and the first layer's norm to the 36 layers. The exposed 1,302 cycles
per layer are the stream-unit passes and result paths between projections;
they matter again only if the KV stream gets faster (4-bit KV, a sensitivity:
61,440 cycles), where the chain would bind.

The analytical spec chain that `rom_token` prices (142,884 at 8K) is now
pessimistic against the calibrated replay; the speculation, batch and power
sections still use it, so their compute-bound figures are conservative.

The chain levers, in the order the user approved, and the token after each
(8K, calibrated):

1. reductions off the critical path -- normalise after P·V, the row max on
   the engine, the RMSNorm fold with 1/rms after the projection, SiLU fused:
   174,856 → 123,301 (with 3);
2. row-granular chaining (P·V chasing the exp pass by rows): included above.
   Tile-granular chaining of the projections gives nothing here: at 8,192
   groups every weight op is a single round, so there is no earlier tile to
   start on;
3. shallower stages (3-cycle FP units; 4-cycle split-tree and reducer
   levels): included above;
4. overlapping the KV prefetch: the KV stream runs beside the chain (the
   streamer's lead covers the fetch), so the token is max(chain, KV stream).

**One lever was tried and rejected: the attention norm applied after the
projection.** The idea is h = x·w, then qkv = W·h·r, so the rsqrt runs beside
the projection. It was bit-exact and on the oracle token, but it saves
nothing. The stream unit drains between SFU classes, so the rsqrt and the
x·w pass still serialise. It was reverted. Folding the norm weight into
the projection's weights (W' = bf16(W·diag(w))) removes the x·w pass instead,
and that is what landed.

The analytical `decode_critical_path.py` prices 2K with KV on chip (8,680
tok/s). Against it, the spec chain at 2K is 129,204 cycles (8,503 tok/s).

## 7. Gap table (requirement vs the RTL)

| block | requirement | RTL | baseline 2K | HEAD 8K |
|---|---|---|---|---|
| stream unit | 1,024 elements/cycle | **landed**: `ot_hdc_vstream`, SW lanes (RTL parameter), R-ARITH reducer | 8,710,761 | 29,817 |
| attention P·V | K-split over positions | **landed**: interleaved K-split | 4,718,592 | 9,216 |
| attention Q·K | K-split over head_dim | **landed**: interleaved K-split | 147,456 | 9,216 |
| matrix engine | 8,192 groups, split field to 2^13 | **landed**: 4-bit split | 892,928 | 57,744 |
| sequencer | ≤ 3,880 control cycles | **landed**: prefetched issue, gap 1 | 22,700 | 4,540 |
| dependency | ≤ 54 exposed per stage | **partly landed**: per-unit waits (`wait_me` / `wait_su`) and row-granular P·V chasing; projections are still whole-op granular | 13.46 M | about 101,000 of waits and chases |
| softmax | one stream pass, 1/Z beside P·V | **landed**: the row max on the engine's result path (`me_rmax`), one exp pass, normalise-after-sum | — | — |
| KV in HBM (ROM die) | 6 stacks, FP8, prefetched | `ot_hdc_kv_stream` exists for the unsplit attention order, BF16 | — | 122,881 |

## 8. Microarchitecture, in implementation order

1. **Attention K-split (landed).**
   * Both attention products cut their K interleaved over the free groups
     (`hdc_golden.attn_splits`, `matvec_il`):
     * Q·K over head_dim, S = min(128, G);
     * P·V over positions, S = G / (head_dim / 16).
   * Chunk c takes k = c, c + S, …. An element past K has both operands zeroed,
     so a ragged last chunk sums exactly. The split tree adds the chunk sums.
   * ISA: `me_split` widened to 4 bits, and a `me_wcs` chunk stride added.
   * RTL: the reduced token is bit-exact and on the oracle. It went from
     32,246 to 31,478 cycles; 8 groups 22,605 → 21,709; position 59
     37,878 → 36,438.
   * The KV-in-HBM streamer keeps the unsplit order for now
     (`HDC_ATTN_SPLIT=0`). Extending it is item 4.
2. **Prefetched sequencer (landed).**
   * A program-word FIFO feeds a decoded NEXT register. `go` is combinational,
     so the unit latches NEXT on the issuing edge. The issue gap falls from 5
     to 1.
   * Reduced token: 31,374 cycles, bit-exact.
   * The timing model was refitted (`seq_gap` 1, `start` 4, `idle_me` 3,
     `idle_su` 0, `red_tail` 31): 31,369 against 31,374 RTL, every issue within
     2 cycles; 8 groups 21,599 against 21,605.
3. **Vector stream unit (landed).** `rtl/hdc/ot_hdc_vstream.sv`.
   * SW lanes, a multiple of 8. Lane l of vector v takes element v·SW + l of
     the current outer iteration (VI mode).
   * Every lane is the scalar datapath, generated from `ot_hdc_stream.sv` by
     `tools/gen_hdc_vstream_lane.py`.
   * The reducer, `ot_hdc_vreduce.sv`, implements R-ARITH, the contract shared
     with the V4.1 core:
     * chunks of 8 contiguous elements, each summed sequentially from +0;
     * a pairwise tree over the chunk sums, padded with +0;
     * in hardware: SW/8 chunk chains a vector, a tree inside the vector, and
       LV time levels pairing the segment's vectors.
   * The order does not depend on SW (`tests/test_hdc_vstream.py` checks the
     hardware structure against `hdc_golden.reduce_chunked` for SW 8–256).
   * `progress` counts vectors, and the program's chase thresholds are in
     vectors.
   * The reduced vehicle ran bit-exact with the oracle's tokens:

     | configuration | before (cycles) | after (cycles) |
     |---|---|---|
     | 4 groups, SW 8 | 31,374 | 27,192 |
     | 8 groups, SW 16 | 21,605 | 16,849 |
     | position 59 | 36,334 | 28,252 |
     | 19-step end to end | 553,052 | 489,328 |

     These figures include items 5 and 6.
   * The timing model was refitted (`red_tail_vec` 43, `idle_su` 1) to within
     6 cycles on all three.
4. **KV streamer for the K-split order and FP8 KV (next).** The KV-in-HBM
   configuration keeps the scalar stream unit and the unsplit attention
   (`HDC_SU_WIDTH=1`, `HDC_ATTN_SPLIT=0`) until then. So do the array, package,
   host and collectives benches (`SU_VEC=0`).
5. **Per-unit waits (landed).**
   * An op that cannot chase waits only for the unit whose in-flight ops it
     conflicts with. Both units is the old barrier.
   * The weighted-sum ops write per-head-batch regions, so they no longer
     serialise.
6. **One-pass softmax (landed).**
   * The golden's `attend`: e = exp(s − max), P·V over bf16(e), then × 1/Z.
     The scale pass over 32 × T is gone, and the reciprocal runs beside P·V.
   * The row max rides the matrix engine's result path. `me_rmax` feeds the
     score op's results through the argmax compare tree and writes the IL
     per-slot maxima as one masked word after the op.
   * The exp pass subtracts M × scale through the Q multiplier. The scale is a
     positive power of two, so max(s)·scale is exactly the scaled max: no
     golden change.
   * P·V chases the exp pass by rows: `chase_rows`, with `progress_rows` in
     the vector unit. It starts once its heads' rows are written.
7. **Latency (landed in part).**
   * The low-latency FP units were brought over from the `a516` branch
     (acc46e61), selectively: `ot_hdc_fastfp.sv`, `ot_hdc_sfu.sv`,
     `ot_hdc_stream.sv`, `ot_hdc_reduce.sv`, their equivalence benches and
     `results/rtl/hdc_sfu_equivalence.json`. Add and multiply take 3 cycles
     (were 5); exp is 49, recip 28, rsqrt 37.
     * The vector reducer and the matrix engine's split tree now use the
       3-cycle adder: 4 cycles a tree level (was 6).
     * The reduced vehicle is bit-exact at 24,992 cycles. The timing model is
       within 6 cycles of it, every issue within 3.
   * Still open: tile-granular chaining on the projections, skipping the
     reducer's time levels for short segments, and waiting for a unit's main
     writes only.

## 9. Speculation (DFlash, τ 4.1)

τ 4.1 is the default: the pooled measured acceptance over 561 blocks. The mean
over prompts, 5.18, is a band only. A verify's slots share the KV stream and
the weight words. On the ROM die their MACs are real work unless lane copies
carry them.

For block B, tokens a step are E[min(L, B)] over the measured block-16
acceptance lengths, assuming a smaller block keeps the first B − 1 drafts:

| ROM die, FP8 KV | best block | tok/s | speedup |
|---|---|---|---|
| 8K, m = 1 | 1 (no speculation) | 7,327 | 1.0 |
| **8K, m = 3** | **B = 3** | **13,090** | **1.79×** |
| 2K, m = 1 | B = 2 | 8,596 | 1.01× |
| 2K, m = 3 | B = 3 | 16,336 | 1.92× |

The rates are against the spec chain's plain token.

On the HBM comparator (8K, FP8 KV, m = 16) the bytes bind. The step reads the
target's and the drafter's weights once for 16 slots: **3.6×** at τ 4.1, taking
BF16 weights from 343 to 1,235 tok/s, FP8 from 661 to 2,380 and 3.5-bit from
1,379 to 4,967.

Requirements this adds:

* the lane multiplier;
* KV-shared verify attention with the causal mask per slot;
* slot-parallel non-weight work;
* 16 DYN banks, the CTL steps and the shared accept unit;
* a KV ring of at least 17 entries.

## 10. Batch (8K, FP8 KV)

Users share the chain's latency and the weight words. Each user has their own
attention and KV stream, so on the ROM die a step is

`max(latency + ⌈B/m⌉ × weights + B × (attention + elementwise), B × KV / bandwidth)`.

Capacity is no longer a limit: 6 × 24 GB of HBM.

| batch | ROM per user | ROM total | HBM (FP8 weights) per user | HBM total |
|---|---|---|---|---|
| 1 | 7,327 | 7,327 | 661 | 661 |
| 2 | 4,470 | 8,941 | 615 | 1,231 |
| 8 | 1,118 | 8,941 | 436 | 3,484 |
| 128 | 70 | 8,941 | 64 | 8,144 |

Rates are tok/s. From batch 2 the ROM die is **KV-stream-bound at 8,941 tok/s
total**, which is 5.4 TB/s over 604 MB a token; more users only divide it.
Lane copies do not help, because each user's KV is its own. At 2K the stream
leaves room: at m = 3 the total reaches 35,763 tok/s at batch ≥ 32.

Energy per token at 8K is about 229 mJ, or 103 mJ at the matrix-engine
figure: logic at the measured reduced step's 16.5 pJ/MAC (3.97 for the matrix
engine alone), and KV at 104.9 pJ/B from HBM. It is an order-of-magnitude
figure, not a sign-off power.

## 11. Power (a first-class requirement)

### 11.1 Production basis (the figures to use)

By user directive, power is priced on the conservative production value
wherever sources disagree. The inputs are in `configs/hardware/technology.json`
(checked against normative and production sources on
worktree-agent-adae6788cbf2f3f86, each entry quoting its source):

* MAC: W4A8 0.09 pJ, FP8 0.13, BF16 0.41, FP32 1.18 (Jouppi ISCA 2021 Table 2
  at 7 nm, × 0.7 to N5);
* logic leakage 0.10 W/mm²; clock 8.5e-11 J/mm²/cycle (ROM and SRAM arrays at
  0.15 of that);
* operand delivery 0.23 pJ/B, SRAM 2.6 pJ/B, ROM read 0.08 pJ/B;
* HBM 13.1 pJ/bit in the stacks (system level), plus 0.8 pJ/bit of active
  interface on the die and 2.8 W a stack idle;
* PSU 0.96, VR 0.87, CDU 0.6%, fans 3%.

Computed by `power_production()` (`results/arch/qwen3_budget.json`
`power_production`). The weights are priced at W4A8 (the lane designed for the
weight format), attention at BF16, and idle lane copies are clock-gated. All
figures are at 8K with FP8 KV:

| design, scenario | tok/s | mJ/token | die W | stacks W | package W | wall W |
|---|---|---|---|---|---|---|
| ROM, batch 1 | 8,910 | **86.2** <!-- figure: 86.246 src="results/arch/qwen3_budget.json#power_production.rom.ar_batch1.energy_per_token_mj" name="Qwen3-8B ROM production-basis mJ/token 8K batch 1" --> | 187.2 | 581.2 | 768.5 | 953.2 |
| ROM, DFlash τ 4.1 (block 3, m = 3) | 13,612 | 49.9 | 213.5 | 465.8 | 679.4 | 842.7 |
| ROM, batch 2 (KV-bound) | 8,941 | 86.4 | 189.5 | 583.2 | 772.6 | 958.4 |
| ROM, batch 128 | 8,941 | 87.0 | 194.4 | 583.2 | 777.6 | 964.5 |
| HBM comparator, batch 1 | 661 | 1,178 | 195.4 | 583.2 | 778.5 | 965.7 |
| HBM comparator, batch 16 | 5,014 | 157.8 | 208.2 | 583.2 | 791.3 | 981.6 |
| HBM comparator, batch 128 | 8,144 | 98.3 | 217.4 | 583.2 | 800.5 | 993.0 |
| B200, batch 1 (measured 689 W decode draw, roofline rate) | 881 | 782 | | | | |

* **The KV stream is the energy.** At batch 1 on the ROM die, 65.2 mJ of the
  86.2 mJ is in the stacks: 63.4 mJ of DRAM energy for the 604 MB of FP8 KV
  and 1.9 mJ of idle floor. The die's 21.0 mJ splits into leakage 5.9, clock 4.3, the HBM interface 3.9, the KV ring's
  SRAM write, read and delivery 3.3, the weights' ROM read and delivery 1.0,
  MACs 1.7 (0.7 weights, 1.0 attention), and the stream unit 1.0. Halving
  the KV bytes (4-bit KV, a sensitivity) is the largest energy lever as well
  as the largest speed lever.
* **Ratios per token at batch 1:** the HBM comparator spends **13.7×** the
  ROM die's energy, and a B200 **9.1×** (at its measured decode draw). The
  comparator's own die is dominated by clock and leakage (238 of 295 mJ) over
  its 1.5 ms token.
* **Worst case.** The hardwired schedule bounds the power. The saturated worst
  case has every lane copy MAC every cycle at BF16, the stream unit and the
  ROM read path busy every cycle, and the 6 stacks at full raw bandwidth. That
  is a die of 407.9 W, stacks of 646.1 W and a package of 1,054.0 W (1,307.4 W
  at the wall). **Provisioned: 1.2 × 1,054.0 / (0.87 × 0.96) = 1,514.3 W.**
  The worst-case die sits at the reticle's cooling limit (0.5 W/mm² × 815
  mm²); every scheduled scenario draws at most 214 W on the die.
* The GPU reference powers: B200 TDP 1,000 W (HGX) and 1,200 W (NVL72);
  MLPerf v5.1 measured 1.30 kW a GPU at the wall, saturated (1,476 mJ/token
  at the roofline rate); measured decode draw 689 W (arXiv:2609.11133).

### 11.2 ASAP7-measured basis (the sign-off cross-check)

The reticle's cooling limit is 408 W (the iso-area study, `a57e0d89` at
09b4b1b1). At the design point's 8,494 tok/s that is a die energy budget of
**48.0 mJ per token**. With 75% of it for the MAC lanes, less 6 × 2.8 W of HBM
interface idle, the matrix engine must reach:

* **≤ 3.41 pJ/MAC** for autoregressive decoding at the target: 9.98 G MACs a
  token at 84.8 TMAC/s;
* **≤ 1.41 pJ/MAC** for the best speculative configuration uncapped
  (m = 3, B = 3: 206 TMAC/s).

As built, the ASAP7 sign-off of the reduced step's BF16 × BF16 lane is 3.97
pJ/MAC:

* Autoregressive decoding draws 449 W, capped to 7,720 tok/s. That is still
  above the spec chain's 7,327, so it does not bind yet.
* DFlash draws 1,088 W and is capped to 4,909 tok/s, below autoregressive
  decoding.
* At the GPU's 1.4 pJ/MAC (SC'25) neither is capped.

The HBM DRAM energy of the KV stream, 604 MB × 104.9 pJ/B, is the stacks'
own: 538 W at the target. It is not charged to the die.

MAC requirements that follow:

* **Design the lane for the ROM's weight format.** That means 4-bit weights
  (3.5 bits a weight with group scales) × FP8/BF16 activations with FP32
  accumulation, not a BF16 × BF16 lane. This is a golden change: the quantised
  checkpoint.
* **Operand isolation and clock gating** for idle lanes: groups outside an
  op's tiles, masked elements and idle lane copies.
* **FP32 accumulation** in the golden's order, with exact products.

Energy is the ASAP7 (7 nm predictive) sign-off applied unscaled to the N6
reticle, which is the same node class.

**Reconciliation with the iso-area study's 8K headline.** Its ROM figures are
≤ 2,570 tok/s autoregressive (BF16 KV), 4,617 with FP8 KV, and 4,767 with
DFlash. They imply about 3.1 TB/s of KV bandwidth over 6 stacks. This budget
uses 6 × 1.0 TB/s × 0.90 = 5.4 TB/s, which gives 4,470 (BF16 KV, KV-bound) and
7,327 (FP8 KV, compute-bound). The stack bandwidth is the difference to
settle.

## 12. HBM comparator requirements

The weight stream never stalls: weights are data-independent, so the stream
runs ahead across every dependency point.

* **Prefetch buffer.** It holds what the stacks deliver during the longest
  weight-free interval of the 8K chain, 1,505 cycles: **7.40 MB**.
* **Sustained efficiency.** At least 0.90 of raw peak, measured with refresh
  on (`technology.json`'s 0.90 is a GPU STREAM-class figure, with refresh).
  * All-bank refresh (tRFC 350 ns every 3.9 µs) meets it on the Qwen3 reduced
    vehicle: 0.904 at 1 pseudo-channel and 0.910 at 2. Its floor is 9.0%.
  * Per-bank refresh (200 ns) is allowed only with a record showing ≥ 0.90.
    Refresh-aware scheduling measured 0.914 and 0.889; at a 1 ns tRFCpb it
    reached 0.998.
  * Record: `results/rtl/hdc_hbm_campaign.json` `refresh_study` (be30614a on
    the HBM comparator branch). Qwen3 keeps REFab, at 0.9037 and 0.9095.
* **Controller queue.** At least 512 beats per pseudo-channel (bandwidth ×
  tRFC ≈ 350 beats). On the V4.1 vehicle a 64-beat queue cost up to 15% of a
  token; for Qwen3 the deeper queue is neutral. A refreshing channel must not
  stall the others.
* **MAC rate.** Above the stream, so the buffer drains.
* The same controller rules apply to the ROM die's KV stacks.

## 13. Physical rules for every block

These come from the full-chip effort at a 1.0 ns ASAP7 target:

* Every block boundary is registered, inputs and outputs. A registered
  512-bit output needs about 300 ps inside the block (router clock-to-pin
  about 270 ps), and feed-through paths get their own budget.
* Clock insertion on the matrix engine took about 540 ps.
* Repair needs a 40% slew margin and a 15 ps setup margin, for estimated
  against extracted wire delay.
* Routes must carry a real hold margin (the fix at 48fc68e6).

## 14. Implementation and evidence

Each block goes through the same steps:

1. golden;
2. ISA and program, with the ISA model bit-exact;
3. RTL on the reduced vehicle (Verilator, `tools/rtl_hdc_decode_campaign.py`),
   bit-exact and on the oracle token;
4. a per-block performance testbench asserting the block's spec;
5. recalibration of `tools/hdc_timing.py`, and a lower `RATCHET_8K` in
   `tests/test_arch_budget_qwen3.py`.

Place and route of the whole core, and the integrated token simulation, follow
the blocks.

## 15. Utilisation of every block (the gate before place and route)

The rule is to improve utilisation without slowing the single user. Every block
of both designs is priced in four scenarios at 8K with FP8 KV:

* batch 1, autoregressive;
* batch 1 with DFlash at τ 4.1 (ROM: block 3 at m = 3; HBM: block 16);
* the smallest KV-bound batch (ROM 2, HBM 16);
* batch 128.

The record is `results/arch/qwen3_utilization.json`, written by
`tools/arch_budget_qwen3.py utilization()`; a test keeps it current.
Utilisation is demand over peak × step: MFU for compute, MBU for memory and
bandwidth (MBU against raw peak, so 0.90 is the sustained ceiling). The
batch-1 autoregressive row uses the calibrated model's measured unit busy. The
other rows use the budget model's steps, which are conservative; the
KV-bound rows are exact.

**ROM reticle** (utilisation per scenario: AR 1 / DFlash / batch 2 / batch 128):

| block | AR 1 | DFlash | batch 2 | batch 128 | area mm² | verdict |
|---|---|---|---|---|---|---|
| matrix engine, base lanes | 0.62 | 0.49 | 0.31 | 0.21 | 146.7 | right-sized |
| 2 lane copies | 0 | 0.49 | 0.15 | 0.21 | 138.4 | justified by DFlash, conditional on power |
| weight ROM read path | 0.47 | 0.37 | 0.23 | 0.16 | 262.0 | right-sized |
| attention (engine share) | 0.15 | 0.10 | 0.08 | 0.05 | (engine) | right-sized with the engine |
| vector stream unit, 1,024 lanes | 0.24 | 0.50 | 0.24 | 0.24 | 12.8 | right-sized |
| SFUs / reducers (on the stream lanes) | 0.08 / 0.15 | 0.16 / 0.32 | 0.08 / 0.16 | 0.08 / 0.16 | (stream) | with the stream unit |
| KV streamer, controllers, 6 PHYs | 0.90 | 0.71 | 0.90 | 0.90 | 60.0 | binding |
| KV ring buffer, capacity | 1.00 | 1.00 | 1.00 | 1.00 | 6.2 | **right-sized (was 0.56)** |
| KV ring buffer, engine read port | 0.04 | 0.03 | 0.04 | 0.04 | (ring) | justified (latency) |
| drafter ROM | 0 | 0.05 | 0 | 0 | 33.5 | justified by DFlash |
| sequencer / argmax (busy) | 0.01 / 0.04 | 0.01 / 0.03 | 0.01 / 0.02 | 0.01 / 0.01 | small | justified (latency) |

The verdicts:

* **Base lanes.** Compute sits at the KV floor (123,301 against 122,881
  cycles). Half the groups is 198,565 cycles in the calibrated model, 61%
  slower a token.
* **Stream unit.** It is the smallest width that holds the floor. 512 lanes is
  133,569 cycles (+8.3% a token); 2,048 lanes is 121,569, under the floor, so
  it buys nothing.
* **KV ring buffer: over-provisioned, right-sized (applied).** Two layers
  (33.6 MB) were 56% used. The stream runs continuously, because it binds the
  token, and the engine drains a layer in its attention burst. So the peak
  occupancy is one layer (16.8 MB) plus what lands during a refresh
  (5.4 TB/s × 350 ns). That is 18.7 MB, and 5.0 mm² go to slack (section 4).
* **Lane copies.** They are idle in autoregressive decode and in every
  KV-bound batch, since each user's KV is its own and from batch 2 the step is
  the KV stream. They carry the DFlash verify, 1.77× single-user tokens/s. That
  gain holds under the cooling limit only at ≤ 1.35 pJ/MAC. At the measured
  3.97 pJ/MAC the capped DFlash rate falls below autoregressive, and the copies
  would not pay (section 11). They stay on that condition.
* **Batch.** From batch 2 the base lanes are 69–79% idle and nothing on the die can
  use it: the KV stream is the whole step. Only KV bytes move it. The stacks
  are fixed by the beachfront, so 4-bit KV (a sensitivity, pending the
  accuracy study) is the lever.

Energy per step at batch 1 autoregressive, by the order-of-magnitude basis of
section 10:

| component | share |
|---|---|
| matrix engine (3.97 pJ/MAC) | 17% |
| the rest of the logic (upper bound) | 55% |
| KV reads in the stacks | 28% |
| ROM read and leakage | 0.2% |

Clock gating and operand isolation of the idle lane copies, and of lanes
outside an op's tiles, are therefore requirements, not options.

**HBM comparator** (131,072 lanes, FP8 weights and KV):

| scenario | MFU | MBU (raw) | binding |
|---|---|---|---|
| batch 1 | 0.05 | 0.90 | bytes |
| DFlash τ 4.1, block 16 | 0.74 | 0.90 | bytes |
| batch 16 | 0.35 | 0.90 | bytes |
| batch 128 | 0.56 | 0.90 | bytes |
| 2K, batch 128 | 1.00 | 0.62 | MACs |

The comparator's lanes are 5% used at batch 1, and a smaller array was tried.
6,656 groups (106,496 lanes, tiling 0.947) still cover the DFlash step's
97,471-lane need and slow no 8K row. At 2K, however, the batches from 32 users
are MAC-bound, and it would cost them 23% of their throughput (13,564 against
17,621 tok/s). **The comparator keeps its 131,072 lanes rather than be
handicapped.** Its stacks and controllers bind every 8K row.

## 16. Prefill and KV ingest (both designs)

**Policy: the GPU does every prefill, cold and incremental, and the chip
ingests the KV.** One B200 prefills 8K in 62 ms, about 120,000 prompt tokens
a second. On-chip chunked prefill on the ROM die (m = 3) would manage 31,800
positions a second, and it would stall the batch being decoded.

The source is `docs/ARCH_SPEC_PREFILL.md` (worktree-agent-ab5912eff5bdb5981,
b6d39bd4), which holds the measurements; these rows make them requirements of
this spec:

| id | requirement |
|---|---|
| R-P1 | A PCIe Gen5 x16 endpoint on the reticle, beside the 6 HBM PHYs as on GH100. It sits behind a host PCIe switch shared with a 400G ConnectX-7. Ingest is an RDMA write, peer to peer into the ingest window, with no host bounce. Link goodput is 49.5 GB/s. |
| R-P2 | One KV ingest engine (`rtl/hdc/ingest/ot_hdc_kv_ingest.sv`, QKV mode). It takes vLLM NHD pages (BF16, FP32 or FP8) and writes this core's FP8 layout: K corner-turned into 16-position tiles (`Layout.k_elem`), V position-major, one byte an element. It read-modify-writes the open tile when a turn is appended. It needs 64 KB of block SRAM. Measured: 68 GB/s in (BF16) and one sector a cycle out. It is bit-exact against the golden's own FP8 cache, and the ISA decode from the ingested image is bit-exact. |
| R-P3 | A decode-first HBM arbiter (`ot_hdc_ingest_arb`): a token-bucket share CSR (default 64/256) and 16-sector write bursts; refresh stays with the controller. At the full link rate, ingest takes at most 0.9% of the 5.4 TB/s. The measured share is exact. |
| R-P4 | The KV streamer's tail SRAM, which holds the open tile and the one before it, must be loadable from the ingested image at decode start. The alternative is for the streamer to read the open tile from HBM on its first token. Either way this is a small tail-preload step in `ot_hdc_kv_stream`. |
| R-P5 | Numerics. Decode is bit-exact given the ingested KV. For bit-identity with this core's own rounding, the GPU sends FP32, or FP8 cast from FP32 with round-to-nearest-even and saturation (`hdc_golden.to_fp8`). BF16 on the wire double-rounds 3.1% of values. |

**Numerics contract.** The chip's decode is bit-exact to the golden *given
the KV it holds*. The KV itself is not bit-identical across prefill paths.
The golden's prefill attends to FP8 KV, while a GPU prefill attends to wide
KV. On the reduced vehicle 34% of the resulting elements differ
(`results/arch/prefill_numerics.json` on the prefill branch). An ingested
cache is therefore a different, equally valid starting state, not the
golden's. Token-level agreement with a GPU-prefilled reference is a quality
metric, not a bit-exactness claim.

**Sizing.** A load of R:1 prefills R new prompt (input) tokens per generated
(output) token, averaged over a chip's users. 4:1 is a chat load; 20:1 is an
agentic load, where tool outputs are appended each turn. The sustained ingest
is R × the decode aggregate × 73,728 B (one position's FP8 K and V over 36
layers), and the B200s needed are R × the decode aggregate / ~120,000 prompt
tokens a second per B200. At the KV-bound aggregate (8,941 tok/s), a 4:1 load
needs 0.3 B200 per chip and 20:1 needs 1.5. The sustained ingest is 2.6–13.2
GB/s a chip, well inside R-P1's link. The HBM comparator takes
the same endpoint, engine and arbiter; its ingest share of the stacks is the
same 0.9% bound.
