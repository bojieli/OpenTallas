# Qwen3-8B decode core: architecture specification (top-down)

> **Superseded design point — correction of 2026-10-03.** This specification describes the TP-2 two-reticle package with DFlash. Its 10,874 tok/s autoregressive and 18,720 tok/s DFlash rates are that superseded design. The adopted Qwen3-8B ROM target is option C: TP-4, four dies in two packages, AR only. The corrected per-user figure at 8K is 357.99 µs = 2,793 tok/s. It is a calibrated finite-calendar model with KV delivery; the near-HBM attention entry selected for build is 5,237 tok/s, model only. Sources and caveats: [HEADLINE_BUNDLE_SCOPE.md](HEADLINE_BUNDLE_SCOPE.md), section "Corrected numbers". The text below is retained as history.

Scope: Qwen3-8B (hidden 4,096, 36 layers, 32/8 heads of 128, FFN 12,288,
vocabulary 151,936), greedy and bit-exact against the golden
(`tools/hdc_golden.py`), on two designs. The design point, set by the user,
is **8K context**; 2K is a secondary point. Both designs are the same silicon:
two reticle-class dies in one package with eight HBM3E stacks, the class of a
shipping B200.

* **ROM**: two HC1-class N6 dies of 815 mm² in one CoWoS-L-class package
  (an interposer of about 3.3 reticles). The weights are **8-bit**, INT8
  weight-only with one BF16 scale per output channel, in mask ROM beside the
  lanes. **Every layer is split across both dies** (tensor-parallel 2) and the
  dies exchange FP32 partial sums over UCIe (§1.1). Each die carries **6,144
  weight-lane groups**, the most its half of the 8-bit ROM can feed (§4),
  and a lane multiplier **m = 5**. By user decision, **users' KV lives in HBM
  beside the ROM dies**, at every context and batch: 8 stacks, 4 a die.
* **HBM**: the iso-area comparator, the same package (two reticles of logic,
  the same core and 12,288 groups, the same UCIe split) with the same 8
  stacks carrying both the ROM's INT8 weights and the KV. The matching GPU
  silicon is a B200: two reticle-limited dies and 8 HBM3E stacks.

Why 8-bit weights and why two reticles is the evidence note of §17: a 3.5-bit
format failed the quality bar, and the 8-bit weights do not fit one reticle.

**Stacks per die.** A die in a two-die package gives one edge to its
neighbour (the UCIe link). Its free edge, 2 × (26 + 33) mm less the shared
edge, at the 60% edge use of shipping parts and 12 mm a stack, holds
4 stacks whichever edge is shared (51.0 mm usable in the worse orientation);
B200 also carries 4 a die. At 1.0 TB/s a stack and 0.90 sustained, the 8
stacks give 7.2 TB/s.

Everything below is computed by `tools/arch_budget_qwen3.py`. It writes
`results/arch/qwen3_budget.json` and `results/arch/qwen3_utilization.json`,
and is tested by `tests/test_arch_budget_qwen3.py`. The test includes the
**performance gate**: the RTL-calibrated sequencer model replays the program
the core runs, at the shipped shapes and 8K, against a ratchet that falls as
each block lands and ends at the budget target. The clock is 1.0986 GHz, the
slowest routed Qwen3 token-path unit (`ot_hdc_matvec`, ASAP7 TT).

**Headline, 8K, FP8 KV, one user, batch 1** (power scenario B, the production
lane / A, the lane as built). The package is **liquid-cooled**: the design
cooling class is a GB200 NVL72-class two-die package, 474.6 W a die; the
air-cooled B200 HGX class, 374.6 W a die, is a sensitivity (§11):

| operating point | design rate, tok/s | capped liquid (design), B / A | capped air (sensitivity), B / A | mJ/token, B / A |
|---|---|---|---|---|
| autoregressive (calibrated chain) | **10,874** <!-- figure: 10,873.6 src="results/arch/qwen3_budget.json#power_production.scenarios.B_proposed_production.rom.ar_batch1.tokens_s" name="Qwen3-8B ROM autoregressive design rate 8K" --> | 10,874 / 7,859 | 8,921 / 5,766 | 96.7 / 130.4 |
| DFlash, block 5, m = 5 (specification chain) | **18,720** | 18,720 / 6,680 | 14,176 / 4,804 | 55.4 / 125.9 |
| HBM comparator, same package, INT8 weights | 880.7 (DFlash 2,651) | 881 / 863 | 609 / 580 | 1,284 / 1,318 |

On the production lane each die draws 434.8 W autoregressive and 457.5 W with
DFlash, inside the 474.6 W liquid limit, so both design rates are uncapped.
Both are above the 374.6 W air limit: **O4 needs liquid cooling to reach its
design rates.** The measured lane (A) is capped in either class.

**The 8-bit weights meet the quality threshold in the measured deployment arithmetic.** The exact 6,144-group, two-die K-split has separate BF16 numeric differences and still needs a full-model quality verdict. In the deployment
arithmetic with FP8 E4M3 KV, the tested row-scale weight contract (signed INT8, one
BF16 scale per output row applied after the FP32 sum, plain round-to-nearest
with a per-row clip) changes WikiText-2 perplexity by **−1.59%** <!-- figure: -1.59 src="results/quality/qwen3_8b_weight_format_search.json#modes.e_full_w8_o4_contract_25288d25.wikitext2_2048.rel_delta_ppl" scale="100" name="Qwen3-8B INT8 per-row weights WikiText-2 2K perplexity change %" -->
at 2K, by **−1.03%** <!-- figure: 1.03 src="results/quality/qwen3_8b_weight_format_search.json#modes.e_full_w8_o4_contract_25288d25.wikitext2_8192.rel_delta_ppl" scale="-100" name="Qwen3-8B INT8 per-row weights WikiText-2 8K perplexity decrease %" -->
at 8K; MMLU changes by **−0.5** <!-- figure: 0.5 src="results/quality/qwen3_8b_weight_format_search.json#modes.e_full_w8_o4_contract_25288d25.mmlu.delta_pt" scale="-1" name="Qwen3-8B INT8 per-row weights MMLU loss points" -->
points, against a threshold of +2% and −1 point (§17). Acceptance for DFlash
is measured in BF16.

## 1. Requirement and target

Three resources bind on the ROM package:

* **The weight sweep on the MAC lanes.** 7,568,097,280 MACs a token on
  196,608 lanes (12,288 groups over both dies) take 38,493 cycles ideally
  and 38,880 tiled (0.9901), a ceiling of 28,541 tok/s. A compute-in-ROM
  weight costs nothing to fetch, but it still passes through a MAC once per
  token.
* **The ROM read.** Each lane consumes one 8-bit weight a cycle: 98,304 B a
  cycle a die. The die's swept ROM (its half of the layers' and the
  lm_head's weights, 207.6 mm²) supplies 1.017× that at the repository's
  8-bit read density and 0.75 sustained efficiency. This bound sets the
  groups a die (§4).
* **The KV stream from HBM.** At 8K the cache is 1.21 GB a token in BF16 and
  604 MB in FP8; each die streams its own KV heads from its own 4 stacks.

The target is the larger of the weight sweep over 55% of the token and the KV
stream over 95% of it:

| context | KV format | KV stream, cycles | target, tok/s | binding |
|---|---|---|---|---|
| **8K** | **FP8 (design point)** | 92,161 | **11,325** <!-- figure: 11,324.9 src="results/arch/qwen3_budget.json#budget.target_tokens_s" name="Qwen3-8B ROM 8K FP8-KV budget target tok/s" --> | KV stream |
| 8K | BF16 | 184,321 | 5,662 | KV stream |
| 8K | 4-bit | 46,080 | 15,698 | weights |
| 2K | any | ≤ 46,080 | 15,698 | weights |

So the design target is **8K with FP8 KV: 97,011 cycles, 11,325 tok/s per
user.** The calibrated chain (101,037 cycles, 10,874 tok/s; §6) is 4% short
of it: the package is bound by its compiled chain, which sits 9% above the KV
stream's floor of 92,161 cycles (11,921 tok/s). FP8 KV (E4M3, round to nearest even,
saturating) is in the golden, the ISA model and the RTL (8a91421a); the scalar
core keeps BF16.

On the HBM comparator the bytes over its 8 stacks bind. With the same FP8 KV,
the per-user bound at 8K is 457 tok/s with BF16 weights and 880.7 at the
ROM's INT8 weights (8.175 GB a token with the KV and the scales). The target
is 95% of each.

### 1.1 The die split and the UCIe hop

All 36 layers run on **both** dies; each die holds half of every layer
(`die_split` in the record):

| | die 0 | die 1 |
|---|---|---|
| query heads | 0–15 | 16–31 |
| KV heads (and their K/V, in the die's own 4 stacks) | 0–3 | 4–7 |
| FFN columns (gate/up rows, down's reduction dimension) | 0–6,143 | 6,144–12,287 |
| lm_head vocabulary rows | 0–75,967 | 75,968–151,935 |
| embedding table | half the rows | half the rows |

The column-parallel matrices (QKV, gate/up, the lm_head) split their output
rows and need no exchange. The row-parallel ones (O and down) split their
reduction dimension, so each die holds a partial sum that the other needs
before the residual add and the next RMSNorm. RMSNorm, the residual, the
sampler and each die's RoPE run on both dies on the full 4,096-element
vector after each exchange. The embedding table is split by rows, so the die
that owns the emitted token's row hands it (INT8, with its scale) to the
other.

**The hop.** A token makes **73 exchanges** (2 a layer, after O and after
down, and 1 for the vocabulary halves' argmax candidates, priced in cycles as
a full exchange, an upper bound). Each all-reduce carries a die's **FP32**
partial of 4,096 elements, **16,384 B each way**: the golden folds the dies' FP32 matrix
outputs in rank order, so the partials cross the link unrounded and both dies
reduce them bit-identically. With the embedding-row handoff a token moves
1,183,754 B each way. The link is `configs/hardware/technology.json`
`links.rom_package_ucie`: a 10 ns hop (range 3–30 ns) at 4.2 TB/s a
direction, 3,823 B a cycle, 0.5 pJ/bit (`configs/hardware/power_scenarios.json`).
An exchange costs 19.27 cycles: 10.99 of hop, 4.29 of transfer and the
4-cycle FP32 add of the received partial, 1,407 cycles for the 73; the
embedding-row handoff adds 12. **The exchanges are on the critical path**:
each sits between a row-parallel matrix and the stage that consumes its
reduced output, so all **1,419 cycles** a token <!-- figure: 1,419 src="results/arch/qwen3_budget.json#ucie.exchange.cycles_per_token" name="Qwen3-8B UCIe exchange cycles per token" --> are exposed, 1.4% of
the autoregressive token (850 to 3,045 cycles over the hop range). Their
energy is 9.5 µJ a token. The link needs one UCIe PHY a die (10 mm²,
assumed) and credit-based flow control so a stalled receiver never drops a
flit.

**The rejected split.** A contiguous layer cut (the embedding and layers 0–19
on one die; layers 20–35, the final norm, the lm_head and the drafter on the
other) needs only a hand-off a token, but at batch 1 the token is on one die
at a time, so every matrix runs on one die's 6,144 groups, and each layer's
KV streams from that die's four stacks alone, which doubles the KV floor.
Priced on the same model it reaches **5,959.6 tok/s autoregressive** <!-- figure: 5,959.6 src="results/arch/qwen3_budget.json#layer_cut_alternative.ar_tokens_s" name="Qwen3-8B contiguous layer cut autoregressive rate" -->
(184,348 cycles, bound by the stack stream) and 12,106.1 with DFlash, 0.54×
and 0.65× the tensor-parallel split's 10,874 and 18,720
(`layer_cut_alternative`, read from `results/arch/qwen3_8bit_design.json`
`o4_contiguous_cut_scenario`; the RTL-gaps record's 12,461.0 omits the
per-row scale stage). The cut is evidence only: tensor-parallel 2 is the only
split that reaches the design rates for the single user.

## 2. Workload per token (from the graph)

| class | 8K | 2K |
|---|---|---|
| weight MACs (qkv 906 M, o 604 M, gate/up 3,624 M, down 1,812 M, lm_head 622 M) | 7.568 G | 7.568 G |
| weight bytes (INT8 + 3.1 MB of per-channel scales) | 7.571 GB | 7.571 GB |
| attention MACs (Q·K and P·V, each 36 × 32 × 128 × T) | 2,416 M | 604 M |
| KV read, each element once (GQA-shared), BF16 / FP8 | 1,208 / 604 MB | 302 / 151 MB |
| elementwise element-ops (reference graph: three softmax passes) | 29.98 M | 8.75 M |
| dependent stages a layer | 21 (reference graph), 20 (spec, §6) | same |
| UCIe exchanges | 73 | 73 |

## 3. Roofline per resource (ROM package, spec widths, FP8 KV)

| resource | 8K cycles | 2K cycles |
|---|---|---|
| weights on 196,608 lanes | 38,493 | 38,493 |
| KV from 8 HBM3E stacks | 92,161 | 23,040 |
| attention on 196,608 lanes | 12,288 | 3,072 |
| elementwise (reference graph) on 1,024 lanes | 29,279 | 8,543 |

## 4. Area of one die

Both dies are alike. The ledger (`area` in the record), per die:

| use | mm² |
|---|---|
| compute share of 6,144 groups (146.7 mm² for 8,192, the HC1-class split) | 110.0 |
| interconnect / overhead (8% / 10% of the reticle) | 65.2 / 81.5 |
| 4 HBM3E PHYs (10 mm² each) | 40.0 |
| UCIe PHY (assumed) | 10.0 |
| KV ring: one layer of 8K FP8 KV plus the package's refresh cover, 19.3 MB (§15) | 6.4 |
| the stream unit beyond the compute share (1,024 lanes; estimated) | 12.8 |
| half of the target's 8-bit ROM (449.3 mm² for the package) | 224.7 |
| half of the 8-bit DFlash drafter's ROM (1.05 B parameters) | 28.8 |
| **4 MAC lane copies (the lane multiplier m = 5)** | 207.6 |
| slack | 28.0 |

**ROM capacity.** The ROM is the repository's HC1-referenced compute-in-ROM
cell (`src/opentallas/roofline.py`: one select cell per ≤ 4-bit nibble, the
cell 1.6× a storage-only mask-ROM bit). An 8-bit weight is two cells, and a
BF16 scale or norm weight four. The target's 8.19 B parameters need 449.3 mm²
(`rom_capacity`), half on each die because every tensor is split.

**Groups a die are ROM-read bound.** The lanes need 98,304 B a cycle a die;
the die's swept ROM supplies it with **headroom 1.017** <!-- figure: 1.017 src="results/arch/qwen3_budget.json#area.rom_read.headroom" name="Qwen3-8B ROM read headroom per die at 6,144 groups" -->.
The next step of the tiling rule, 6,656 groups a die, would need 0.939 of the
read the ROM supplies, so 6,144 is the most the ROM feeds. Area is not the
limit: the lane copies take what the die has left.

A lane copy costs 51.9 mm² for a die's 98,304 lanes. That is 528.08 µm² a
lane, measured: `ot_hdc_lane_copy` is 16 lanes of the exact BF16 multiplier
and the circulating FP32 adder with its interleave registers, sharing the
group's weight word, the split tree, result port and argmax. It routed at
8,449 µm² and **closed at 1.2 GHz**. The whole matrix-engine lane is
1,071.8 µm².

Copies serve speculative slots and batched users: one weight word (or, for
slots, one KV word) feeds m positions. They do not speed a single position.

## 5. Budget and per-block requirements (8K, FP8 KV, batch 1)

Budget, as shares of the 97,011-cycle target:

| share | cycles |
|---|---|
| weights (39.7%, the ideal sweep) | 38,493 |
| attention (15%) | 14,552 |
| elementwise (10%) | 9,701 |
| exposed dependency latency (30%) | 29,103 |
| control (3%), which carries the UCIe exchanges | 2,910 |

Requirements derived from the budget:

| block | requirement |
|---|---|
| MAC array | 196,608 lanes = 12,288 groups, 6,144 a die (the ROM-read bound, §4); lane multiplier m = 5 |
| ROM read | 98,304 B a cycle a die: one 8-bit weight a lane a cycle; lane copies share the word |
| weight lane | an INT8 weight (exact in BF16) × a BF16 activation, exact product, FP32 accumulation in the golden's order; the per-channel BF16 scale applied once per output row after accumulation, a 5-cycle pipelined FP32 multiply after each of the token's 145 weight and 72 exposed attention matvecs (1,085 cycles a token on the chain) |
| UCIe | 73 exchanges a token of one FP32 4,096-element partial each way (16,384 B), plus the embedding-row handoff; hop ≤ 10 ns; credit-controlled |
| attention | ≥ 166,020 lanes busy: Q·K and P·V both K-split over the groups |
| KV in HBM | 8 stacks, 4 a die; 604 MB/token FP8 at 7.2 TB/s (92,161 cycles). Layer l+1's KV (positions < t, data-independent of the token) streams while layer l computes, into each die's 19.3 MB ring (one layer plus the package's refresh cover, §15). The token's own K/V row stays on die (tail buffer) and is written back behind the stream. Efficiency ≥ 0.90 of raw peak with refresh on. The controller queue is ≥ 512 beats per pseudo-channel, and a refreshing channel must not stall the others. |
| stream unit | **2,048 elements/cycle over the package**: one 1,024-lane unit a die, with lane partials and a 10-level pairwise reduction tree each |
| dependency | ≤ 40 cycles exposed per dependent stage (29,103 over 36 × 20): tile-granular chaining, never a full-unit drain |
| sequencer | ≤ 2,910 exposed control cycles a token, the UCIe exchanges included |
| vector buffer | ≥ 262,144 FP32 elements (the score rows 32 × 8K) |
| argmax | a streaming compare tree on the result path (as built), each die over its vocabulary half |

## 6. Where the cycles go: analytical DAG, spec chain, calibrated model

All figures are cycles per token at 8K, FP8 KV, on the package's 12,288
groups (6,144 a die), the 1,419 UCIe cycles included:

| model | cycles | tok/s |
|---|---|---|
| spec dependency chain, reference graph (SU 1,024, K-split attention, as-built unit latencies) | 129,075 | 8,512 |
| **spec dependency chain** (one-pass softmax, prefetched issue): weights 38,880, attention 18,432, elementwise 5,112, latency 57,276, control 720, UCIe 1,419; the post-tree stage priced on weight and KV attention matvecs | **121,839** | 9,017 |
| KV stream (FP8, 8 stacks) | 92,161 | 11,921 |
| **calibrated model at HEAD** (one die's sequencer replay 98,533 + scale multiply 1,085 + UCIe 1,419) | **101,037** <!-- figure: 101,037 src="results/arch/qwen3_budget.json#as_built_calibrated.8192.cycles" name="Qwen3-8B calibrated HEAD cycles 8K" --> | **10,874** |

The calibrated figure is the RTL-calibrated sequencer model replaying the
program one die runs at HEAD: the die's tensor-parallel slice (16 query and
4 KV heads, half the FFN and half the vocabulary; the hidden vector and the
norms whole), 904 instructions, with the RTL's parameters set to the spec's:
6,144 groups, SW = 1,024, and LV = 3 time levels. Both dies run the same
program on their own weights in lockstep, so the die's replay is the
package's chain. Two stages the program does not yet contain are added: the
INT8 contract's per-row scale multiply after each of the token's 145 weight and 72 exposed attention matvecs
(5 cycles each, 1,085 a token) and the 73 UCIe exchanges with the
embedding-row handoff (1,419). It is not a shipped-scale simulation. It is
**4.2% over the design target** of 97,011 and 10% over the KV stream: **the
chain binds the autoregressive token**. The analytical spec chain, which the
speculation and batch sections price, is 21% pessimistic against it. One
decoder layer (the middle one, of 36) at HEAD, on one die's slice:

| stage (cut at the matrix engine's weight-op issues) | cycles | engine busy | exposed |
|---|---|---|---|
| QKV projection, then q/k norm, RoPE | 480 | 128 | 352 |
| attention: scores, softmax, P·V, 1/Z | 852 | 512 | 340 |
| O projection, residual, FFN norm | 183 | 88 | 95 |
| gate/up projection, fused SiLU·up | 768 | 512 | 256 |
| down projection, residual, next norm | 359 | 264 | 95 |
| **layer** | **2,642** <!-- figure: 2,642 src="results/arch/qwen3_budget.json#as_built_calibrated.8192.layer_chain.cycles" name="Qwen3-8B calibrated layer chain 8K" --> | 1,504 | 1,138 |

The per-layer share of the KV stream is 2,560 cycles, so a layer's chain is
82 cycles over it before the layer's scale multiplies and two exchanges. The
exposed 1,138 cycles a layer are the stream-unit passes and result paths
between projections; the die's half-matrices on its 6,144 groups keep the
weight passes short and these do not shrink with them, so they set the
rate. The dependency requirement (≤ 40 exposed cycles a stage) is the lever
that reaches the target: tile-granular chaining of the projections, skipping
the reducer's time levels for short segments, and waiting for a unit's main
writes only.

The chain levers already landed, in the order the user approved:

1. reductions off the critical path: normalise after P·V, the row max on
   the engine, the RMSNorm fold with 1/rms after the projection, SiLU fused;
2. row-granular chaining (P·V chasing the exp pass by rows);
3. shallower stages (3-cycle FP units; 4-cycle split-tree and reducer
   levels);
4. overlapping the KV prefetch: the KV stream runs beside the chain (the
   streamer's lead covers the fetch), so the token is max(chain, KV stream).

**One lever was tried and rejected: the attention norm applied after the
projection.** The idea is h = x·w, then qkv = W·h·r, so the rsqrt runs beside
the projection. It was bit-exact and on the oracle token, but it saves
nothing. The stream unit drains between SFU classes, so the rsqrt and the
x·w pass still serialise. It was reverted. Folding the norm weight into
the projection's weights (W' = bf16(W·diag(w))) removes the x·w pass instead,
and that is what landed. With INT8 weights the fold is an open golden
question: diag(w) scales the input dimension, which a per-output-channel
scale cannot carry, so either the fold is quantised into the INT8 weights (a
different quantisation point; the measured pass of §17 quantises the
norm-folded q/k/v and gate/up matrices, tools/qwen3_deployment_quality.py w8)
or the x·w pass returns on the stream unit.

At 2K the calibrated chain is 84,469 cycles (13,006 tok/s) and the spec chain
104,559 (10,507) against a weight-bound target of 15,698.

## 7. Gap table (requirement vs the RTL)

| block | requirement | RTL | baseline 2K | HEAD 8K |
|---|---|---|---|---|
| stream unit | 2,048 elements/cycle (package) | **landed**: `ot_hdc_vstream`, SW lanes (RTL parameter), R-ARITH reducer; one 1,024-lane unit a die | 8,710,761 | 10,809 (busy, a die) |
| attention P·V | K-split over positions | **landed**: interleaved K-split | 4,718,592 | 9,216 |
| attention Q·K | K-split over head_dim | **landed**: interleaved K-split | 147,456 | 9,216 |
| matrix engine | 12,288 groups, split field to 2^13 | **landed**: 4-bit split | 892,928 | 38,880 |
| sequencer | ≤ 2,910 control cycles | **landed**: prefetched issue, gap 1; 904 instructions a die program | 22,700 | 904 |
| dependency | ≤ 40 exposed per stage | **partly landed**: per-unit waits (`wait_me` / `wait_su`) and row-granular P·V chasing; projections are still whole-op granular | 13.46 M | 82,867 of waits and chases |
| softmax | one stream pass, 1/Z beside P·V | **landed**: the row max on the engine's result path (`me_rmax`), one exp pass, normalise-after-sum | — | — |
| KV in HBM (ROM package) | 8 stacks, FP8, prefetched | `ot_hdc_kv_stream` exists for the unsplit attention order, BF16 | — | 92,161 |
| 8-bit weight path | INT8 ROM word, decode to BF16, per-channel scale after accumulation | **not built**: the reduced vehicle stores BF16 weights (§14); the chain prices the scale multiply | — | 1,085 |
| UCIe split | 73 FP32-partial exchanges a token, credit-controlled | **not built** for this core (the four-die reduced package campaign exercises a fixed-order all-reduce, §14) | — | 1,419 |

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
     * The reduced vehicle is bit-exact (token 1073) at 24,440 cycles in the
       decode campaign re-run on the current RTL
       (`results/rtl/hdc_decode_campaign.json` as regenerated on
       claude/bind-headlines, pending merge; the copy on main predates the
       3-cycle units). The timing model was within 6 cycles of the earlier
       run, every issue within 3.
   * Still open: tile-granular chaining on the projections, skipping the
     reducer's time levels for short segments, and waiting for a unit's main
     writes only. These are the levers that close the 3% to the target (§6).
8. **8-bit weight path (open).** The ROM word holds INT8 weights; a decode
   stage widens each to BF16 (exact) in front of the unchanged lane, and the
   result path multiplies each output row by its BF16 scale after FP32
   accumulation, before the row leaves the engine. The chain prices it as a
   5-cycle pipelined FP32 multiply (`ot_fp32_mul_rne_pipe`'s stages) after
   each of the token's 145 weight and 72 exposed attention matvecs.
9. **UCIe exchange (open).** After O and after down, the engine's FP32 result
   words stream to the link as they emerge; the receiver adds the partner's
   partial in the pipelined FP32 adder in the golden's rank order, so both
   dies hold a bit-identical reduced vector.

## 9. Speculation (DFlash, measured per block, serial step)

Every DFlash figure is read from `results/speculative/dflash_step_timing.json`
(`tools/dflash_step_timing.py`, on the package basis of
`tools/arch_budget_qwen3.timing_basis()`); `tools/arch_budget_qwen3.py` and
`tools/power_scenarios.py` restate none of it. Tokens a step are measured by
running the drafter at each block B on 264 prompt turns
(`results/speculative/dflash_block_acceptance.json`, primary workloads,
cycle-weighted; the equal-weighted mean of workloads is the band), not cut
from a block-16 histogram, in BF16 on a GPU. The step is three serial phases
on the same core: the draft (the drafter's 5 layers over the B slots, its fc
and K/V projections, the shared lm_head over the B − 1 drafts), the verify
(the target over B slots) and the commit. The drafter's layers are split
across the dies like the target's. A phase's exchanges are paid once for all
its slots, each carrying the B slots' FP32 partials (36.42 cycles an
exchange at B = 5): the verify's 73 and its embedding-row handoff cost 2,675
cycles, and the draft's own 12 and its handoff 450. A verify's slots share the KV stream and the weight
words. On the ROM package their MACs are real work unless lane copies carry
them. K-splits are the golden's (`hdc_golden.split_for`, `attn_splits`): at
6,144 groups a die they match the RTL's rule on every target matrix, and
differ only on the drafter's fc slice, which is priced at the golden's
S = 4,096 (640 cycles, where the RTL's rule would give 480); P·V takes the
golden's power-of-two split.

| ROM package, FP8 KV | best block | tokens a step | tok/s | speedup |
|---|---|---|---|---|
| 8K, m = 1 | 1 (no speculation) | 1 | 9,017 | 1.0 |
| **8K, m = 5** | **B = 5** | **2.859** | **18,720** <!-- figure: 18,719.9 src="results/speculative/dflash_step_timing.json#rom['8192/fp8/m5'].best.tokens_s" name="Qwen3-8B ROM DFlash design rate 8K m5" --> (band 20,181) | **2.08×** |
| 2K, m = 1 | 2 | 1.736 | 10,865 | 1.03× |
| 2K, m = 5 | B = 5 | 2.859 | 23,730 | 2.26× |

The rates are against the spec chain's plain token (121,839 cycles,
9,017.1 tok/s). At 8K, m = 5 the step is 167,796 cycles: draft 24,243,
verify 143,543, commit 10. The step's 59.5 G MACs include the drafter's
9.6 G.

On the HBM comparator (8K, FP8 KV) the bytes bind each phase. BF16 weights go
from 457 to 1,373 tok/s, and the ROM's INT8 weights from 880.7 to 2,651
(block 16, 3.66 tokens a step, 3.0×). With DFlash on both, the ROM package is
7.1× the comparator (18,720 against 2,651); without, 12.3× (10,874 against
880.7).

Requirements this adds:

* the lane multiplier;
* KV-shared verify attention with the causal mask per slot;
* slot-parallel non-weight work;
* 16 DYN banks, the CTL steps and the shared accept unit;
* a KV ring of at least 17 entries.

## 10. Batch (8K, FP8 KV)

Users share the chain's latency and the weight words. Each user has their own
attention and KV stream, so on the ROM package a step is

`max(latency + ⌈B/m⌉ × weights + B × (attention + elementwise), B × KV / bandwidth)`.

Capacity is no longer a limit: 8 × 24 GB of HBM.

| batch | ROM per user | ROM total | HBM (INT8 weights) per user | HBM total |
|---|---|---|---|---|
| 1 | 9,017 | 9,017 | 880.7 | 880.7 |
| 2 | 5,961 | 11,921 | 820.1 | 1,640 |
| 8 | 1,490 | 11,921 | 580.5 | 4,644 |
| 128 | 93 | 11,921 | 84.8 | 10,858 |

Rates are tok/s on the spec chain (the calibrated batch-1 rate is 10,874).
From batch 2 the ROM package is **KV-stream-bound at 11,921 tok/s total**,
which is 7.2 TB/s over 604 MB a token; more users only divide it. Lane copies
do not help, because each user's KV is its own. At 2K the stream leaves room:
at m = 5 the total reaches 47,684 tok/s at batch ≥ 16.

A first-order energy per token at 8K ranks these batch rows: about 232 mJ,
or 107 mJ at the matrix-engine figure, from logic at the measured reduced
step's 16.55 pJ/MAC (3.97 for the matrix engine alone; power scenario A) and KV
at the whole 13.64 pJ/bit HBM path (109.1 pJ/B), without clock or stream-unit
energy. It is not the power figure: section 11 prices die, stacks, package and
wall.

## 11. Power (a first-class requirement)

### 11.1 Inputs: the two power scenarios

Every energy, leakage, clock, HBM, MAC-lane, link and cooling figure is read
from `configs/hardware/power_scenarios.json` through
`tools/power_scenarios.py`, where each input carries its evidence class,
boundary and source; `tools/arch_budget_qwen3.py` restates none of them. Two
separate scenarios price the multiply-accumulates, and every other input is
shared:

* **Scenario A (measured implementation):** every MAC, whatever its format,
  at the energy our routed ASAP7 matrix engine reports on the reduced Qwen3
  step, 3.97 pJ/MAC (a BF16 × BF16 lane);
* **Scenario B (proposed production):** a floating-point lane derived from
  published per-operation energies at 7 nm, one multiplier plus one FP32 add
  per product (the golden's accumulation): 0.59 pJ an 8-bit-weight MAC (a
  BF16 multiplier, which an INT8 weight needs no more than), and the same for
  the BF16 attention MACs;
* the HBM path is 13.64 pJ/bit (the least favourable measured path without a
  last-level cache, SC'25 MI250X). 3.45 pJ/bit of it is inside the DRAM stack
  (O'Connor); the other 10.19 pJ/bit (controller, PHY, both ends' I/O and
  control plane) is charged to the logic die. Each stack idles at 2.8 W,
  charged to the dies;
* leakage 0.10 W/mm² on logic (0.0067 and 0.005 W/mm² on the ROM and SRAM
  arrays); clock 8.5e-11 J/mm²/cycle, the arrays at 0.15 of it; operand
  delivery 0.23 pJ/B, SRAM 2.6 pJ/B, ROM read 0.08 pJ/B, a stream-unit FP32
  operation 1.69 pJ; UCIe 0.5 pJ/bit;
* **cooling limit per die of a two-die package**: a shipping package's rating
  less its own 8 stacks at peak bandwidth, halved. The design class is
  **liquid, 474.6 W a die** (GB200 NVL72, 1,200 W; a user decision); **air,
  374.6 W a die** (B200 HGX, 1,000 W), is a sensitivity. The package (both
  dies + our stacks) is checked against the rating too;
* die to wall (from `configs/hardware/technology.json`, which the scenarios
  do not model): VR 0.87, PSU 0.96, CDU 0.6%, fans 3%.

The record is `results/arch/qwen3_budget.json` `power_production` (energy and
power per scenario) and `power` (the requirement). Areas are package totals;
both dies carry half the work, so each die dissipates half the package's
die-side power. Attention is priced at BF16, idle lane copies clock-gated,
and the users' KV is read from HBM on the ROM package and on the comparator
alike. The ROM rows at batch 1 and with DFlash are the design points
`power_scenarios.json` prices; the DFlash point (block, tokens a step, step
cycles with the draft phase, and the MACs of the draft and the verify) is read
by both tools from `results/speculative/dflash_step_timing.json`, and a test
holds the two records equal.

### 11.2 Energy per token and power at 8K, FP8 KV

Scenario B / scenario A. Die W is one die; package W is both dies and the
8 stacks. Liquid is the design class; the air columns are the sensitivity:

| design | tok/s | mJ/token, B / A | die W, B / A | stacks W | package W, B / A | wall W, B / A | capped liquid (design), B / A | capped air (sensitivity), B / A |
|---|---|---|---|---|---|---|---|---|
| ROM, batch 1 | 10,874 | **96.7** <!-- figure: 96.65 src="results/arch/qwen3_budget.json#power_production.scenarios.B_proposed_production.rom.ar_batch1.energy_per_token_mj" name="Qwen3-8B ROM scenario-B mJ/token 8K batch 1" --> / **130.4** <!-- figure: 130.44 src="results/arch/qwen3_budget.json#power_production.scenarios.A_measured_implementation.rom.ar_batch1.energy_per_token_mj" name="Qwen3-8B ROM scenario-A mJ/token 8K batch 1" --> | **434.8** <!-- figure: 434.8 src="results/arch/qwen3_budget.json#power_production.scenarios.B_proposed_production.rom.ar_batch1.die_w" name="Qwen3-8B ROM scenario-B die W autoregressive" --> / 618.6 | 181.3 | 1,050.9 / 1,418.4 | 1,303.6 / 1,759.4 | 10,874 / **7,859** <!-- figure: 7,859.4 src="results/arch/qwen3_budget.json#power_production.scenarios.A_measured_implementation.rom.ar_batch1.cooling.liquid.capped_tokens_s" name="Qwen3-8B ROM autoregressive liquid-capped rate scenario A" --> | 8,921 / 5,766 |
| ROM, DFlash (block 5, m = 5, serial step, 2.859 tokens a step) | 18,720 | 55.4 / 125.9 | 456.6 / 1,116.3 | 124.3 | 1,037.6 / 2,356.9 | 1,287.0 / 2,923.6 | 18,720 / 6,680 | **14,176** <!-- figure: 14,176.2 src="results/arch/qwen3_budget.json#power_production.scenarios.B_proposed_production.rom.dflash_block5.cooling.air.capped_tokens_s" name="Qwen3-8B ROM DFlash air-capped rate scenario B (sensitivity)" --> / 4,804 |
| ROM, batch 2 (KV-bound) | 11,921 | 94.7 / 128.5 | 465.0 / 666.4 | 198.7 | 1,128.8 / 1,531.6 | 1,400.2 / 1,899.8 | 11,921 / 7,854 | 8,934 / 5,735 |
| ROM, batch 128 | 11,921 | 96.4 / 130.2 | 475.4 / 676.8 | 198.7 | 1,149.6 / 1,552.4 | 1,425.9 / 1,925.6 | 11,892 / 7,602 | 8,552 / 5,467 |
| HBM comparator, INT8 weights, batch 1 | 880.7 | **1,284.2** <!-- figure: 1,284.186 src="results/arch/qwen3_budget.json#power_production.scenarios.B_proposed_production.hbm_comparator.batch1.energy_per_token_mj" name="Qwen3-8B HBM comparator INT8 weights scenario-B mJ/token 8K batch 1" --> / 1,318.0 | 466.1 / 481.0 | 198.7 | 1,131.0 / 1,160.8 | 1,402.9 / 1,439.8 | 881 / 863 | 609 / 580 |
| HBM comparator, INT8 weights, batch 16 | 6,684 | 175.2 / 209.0 | 486.1 / 599.0 | 198.7 | 1,171.0 / 1,396.8 | 1,452.5 / 1,732.6 | 6,441 / 4,750 | 4,334 / 3,197 |
| HBM comparator, INT8 weights, batch 128 | 10,858 | 110.5 / 144.3 | 500.5 / 683.9 | 198.7 | 1,199.7 / 1,566.6 | 1,488.1 / 1,943.2 | 10,009 / 6,445 | 6,735 / 4,337 |
| B200, batch 1 (measured 689 W decode draw, roofline rate) | 881 | 782 | | | | | | |

* **Liquid cooling carries the production lane uncapped; air would not.** At
  10,874 tok/s each die draws 434.8 W on the production lane and 618.6 W on
  the measured lane; with DFlash at 18,720 tok/s, 457.5 W and 1,118.8 W. In
  the design class (474.6 W a die) the production lane runs both points
  uncapped; the measured lane caps at 7,859 (autoregressive) and 6,680
  (DFlash). The die check binds, not the package. In air (374.6 W a die, the
  sensitivity) both lanes cap: autoregressive at 8,921 (B) and 5,766 (A)
  tok/s, DFlash at 14,176 and 4,804. **O4 therefore needs liquid cooling to
  reach its design rates.** On the measured lane speculation runs slower than
  plain decoding once capped (6,680 against 7,859 in liquid, 4,804 against
  5,766 in air): its extra MACs cost more power than the KV bytes they save.
* **The HBM path is the dies' energy.** At batch 1 on the ROM package
  (scenario B), 16.7 mJ of the 96.7 mJ is in the stacks and 80.0 mJ on the
  dies:
  * the dies' share of the HBM path 49.2 (604 MB of FP8 KV at 10.19 pJ/bit);
  * leakage 9.9;
  * clock 6.1;
  * MACs 5.9 (4.5 weights, 1.4 attention; 39.7 in scenario A);
  * the KV ring's SRAM write, read and delivery 3.3;
  * the weights' ROM read and delivery 2.3;
  * stack idle 2.0;
  * the stream unit 1.0;
  * the UCIe exchanges 0.009.

  The KV stream costs 65.9 mJ of the 96.7 in all, so halving the KV bytes
  (4-bit KV, a sensitivity) is the largest energy lever.
* **Ratios per token at batch 1**, the HBM comparator being the same package
  with the ROM's INT8 weights and the KV streamed, scenario B / A:
  * **13.29× / 10.10×** <!-- figure: 13.29 src="results/arch/qwen3_budget.json#power_production.scenarios.B_proposed_production.ratios_batch1.hbm_over_rom" name="Qwen3-8B HBM INT8 over ROM energy ratio scenario B" --> against the comparator in the ROM's own weight format: the matched ratio;
  * a B200 at its measured decode draw is 782 mJ, 8.09× / 6.00× the ROM
    package; an illustration only, since its workload and context are not
    matched.

  At batch 128 the gap closes to 96.4 mJ (ROM) against 110.5 mJ (HBM,
  scenario B), at totals of 11,921 and 10,858 tok/s. The comparator's dies
  spend 1,058.6 mJ of its 1,284.2 (B) at batch 1: 666.4 on their share of the
  HBM path (weights and KV), and 383.3 of leakage, clock and stack idle over a
  1.14 ms token. Each of its dies draws 466 W at batch 1, inside the liquid
  limit; in air it would cap at 609 tok/s.
* **Worst case.** The hardwired schedule bounds the power. The saturated worst
  case has every lane copy MAC every cycle at the BF16 lane energy, each die's
  stream unit and ROM read path busy every cycle, and the 8 stacks at full raw
  bandwidth. Scenario B: 855.4 W a die, stacks 220.8 W, package 1,931.6 W
  (2,396.0 W at the wall); **provisioned 1.2 × (die + its stacks) / (0.87 ×
  0.96) = 1,387.6 W a die**, 2,775 W a package. Scenario A: 2,683.0 W a die,
  package 5,586.7 W, provisioned 4,013.5 W a die. Both worst-case dies are
  above the liquid limit, so each die must be power-capped (clock
  throttling) to its cooling class.
* **GPU reference powers:**
  * B200 TDP: 1,000 W (HGX), 1,200 W (NVL72);
  * MLPerf v5.1 measured 1.30 kW a GPU at the wall, saturated: 1,476 mJ/token
    at the roofline rate;
  * measured decode draw: 689 W (arXiv:2609.11133).

### 11.3 The requirement: MAC energy that fits

A die's power other than its MACs does not depend on the lane: static 99.1 W
(leakage 54.4, clock 33.5, stack idle 11.2) plus 27.9 mJ a token of non-MAC
dynamic energy for autoregressive decoding (118.5 W and 11.9 mJ with DFlash).
At the design rate that is, per die:

* **autoregressive, 10,874 tok/s: 402.8 W before any MAC.** In the design
  class (474.6 W liquid) **≤ 1.322 pJ/MAC** fits (≤ 1.046 at the 11,325 tok/s
  target). In air the die is over the 374.6 W limit before any MAC, so no MAC
  energy fits (−0.521 pJ/MAC; −0.723 at the target), and with free MACs it
  would cap at 9,862 tok/s: the die's share of the HBM path binds, not the
  lane;
* **DFlash, 18,720 tok/s (the serial step): 342.2 W before any MAC**,
  leaving **≤ 0.678 pJ/MAC** in liquid (≤ 0.166 in air) at 195 TMAC/s a
  die. The step's 59.5 G MACs include the drafter's 9.6 G, and its draft
  phase's 24,243 cycles are in the step time.

Die energy per token that fits 474.6 W: 43.6 mJ at 10,874 tok/s and 41.9 mJ
at the 11,325 tok/s target (34.5 and 33.1 mJ in air). Capped rates by lane
(liquid, the design / air, the sensitivity):

| lane | pJ/MAC (8-bit weight / BF16) | autoregressive | DFlash |
|---|---|---|---|
| scenario A, routed ASAP7 matrix engine | 3.97 / 3.97 | 7,859 / 5,766 | 6,680 / 4,804 |
| scenario B, derived production lane | 0.59 / 0.59 | 10,874 / 8,921 | 18,720 / 14,176 |
| a lane no better than an A100 tensor core (sensitivity) | 1.40 / 1.40 | 10,752 / 7,888 | 13,438 / 9,664 |

MAC requirements that follow:

* **Design the lane for the ROM's weight format.** An INT8 weight is exact in
  BF16, so the routed exact BF16 × BF16 lane takes it with a weight decode and
  no datapath change; the per-channel scale is applied once per output row
  after FP32 accumulation. This is a golden change: the INT8 per-channel
  checkpoint (and the RMSNorm fold of §6).
* **Operand isolation and clock gating** for idle lanes: groups outside an
  op's tiles, masked elements and idle lane copies.
* **FP32 accumulation** in the golden's order, with exact products.
* **Cool with liquid, or reduce the die's HBM-path energy.** The design
  class is liquid. Even with free MACs the autoregressive die is over the air
  limit, so an air-cooled package at the design rate would need less
  controller, PHY and I/O energy per bit than the measured 10.19 pJ/bit (the
  GH200 path, 8.23 pJ/bit on the die, is the power-scenario sensitivity) or
  fewer KV bytes.

Scenario A is the ASAP7 (7 nm predictive) sign-off applied unscaled to the N6
dies, which are the same node class.

### 11.4 Power levers

The batch-1 power levers (KV SRAM in the area slack or in place of lane
copies, INT4 KV as a sensitivity, an HBM die-share override, DVFS points) are
priced as named scenarios on the same inputs by `tools/qwen_power_levers.py`
(`configs/hardware/qwen_power_levers.json`, record
`results/arch/qwen_power_levers.json`), against this package as its baseline.
None is adopted; the operating point stays DFlash at the serial step, with
the design rate from `results/speculative/dflash_step_timing.json` and the
cooling-capped rates from `results/arch/power_scenarios.json`
(`scenarios.*.qwen3_8b_rom_8k.dflash.capped_rate`, the liquid design class;
the air sensitivity under `cooling_classes.air`).

## 12. HBM comparator requirements

The weight stream never stalls: weights are data-independent, so the stream
runs ahead across every dependency point.

* **Prefetch buffer.** It holds what the stacks deliver during the longest
  weight-free interval of the 8K chain, 1,303 cycles: **8.54 MB** over the
  package.
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
* The same controller rules apply to the ROM package's KV stacks.

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

**What the reduced-vehicle RTL gates do and do not cover.** The reduced Qwen
vehicle stores BF16 weights: the golden rounds inputs to BF16 and forms exact
BF16 × BF16 products accumulated in FP32 (`tools/hdc_golden.py`). An INT8
weight is exactly representable in BF16, so the lane datapath, the split
tree, the stream unit, the sequencer and the KV path those gates verify are
the ones the 8-bit design uses, unchanged. Three parts of the design are not
exercised by any gate: the 8-bit ROM word and its INT8-to-BF16 decode, the
per-channel scale applied after accumulation, and the two-die UCIe split with
its 73 exchanges a token. The reduced gates are single-core evidence; the
four-die reduced package campaign (`results/rtl/hdc_package_tp_campaign.json`)
exercises a fixed-order tensor-parallel all-reduce on a different
configuration, not this split.

## 15. Utilisation of every block (the gate before place and route)

The rule is to improve utilisation without slowing the single user. Every block
of both designs is priced in four scenarios at 8K with FP8 KV:

* batch 1, autoregressive;
* batch 1 with DFlash at the serial step of section 9 (ROM: block 5 at m = 5;
  HBM: block 16);
* the smallest KV-bound batch (ROM 2, HBM 16);
* batch 128.

The record is `results/arch/qwen3_utilization.json`, written by
`tools/arch_budget_qwen3.py utilization()`; a test keeps it current.
Utilisation is demand over peak × step: MFU for compute, MBU for memory and
bandwidth (MBU against raw peak, so 0.90 is the sustained ceiling). The
batch-1 autoregressive row uses the calibrated model's measured unit busy. The
other rows use the budget model's steps, which are conservative; the
KV-bound rows are exact.

**ROM package** (utilisation per scenario: AR 1 / DFlash / batch 2 / batch 128;
areas for both dies):

| block | AR 1 | DFlash | batch 2 | batch 128 | area mm² | verdict |
|---|---|---|---|---|---|---|
| matrix engine, base lanes | 0.51 | 0.36 | 0.28 | 0.11 | 220.0 | right-sized (ROM-read bound) |
| 4 lane copies a die | 0 | 0.36 | 0.07 | 0.11 | 415.3 | justified by DFlash, conditional on power |
| weight ROM read path | 0.39 | 0.26 | 0.21 | 0.08 | 449.3 | right-sized (binding on the lane count) |
| attention (engine share) | 0.12 | 0.07 | 0.07 | 0.03 | (engine) | right-sized with the engine |
| vector stream units, 1,024 lanes a die | 0.29 | 0.87 | 0.32 | 0.32 | 25.6 | right-sized |
| SFUs / reducers (on the stream lanes) | 0.10 / 0.19 | 0.29 / 0.57 | 0.10 / 0.21 | 0.10 / 0.21 | (stream) | with the stream unit |
| KV streamer, controllers, 8 PHYs | 0.83 | 0.56 | 0.90 | 0.90 | 80.0 | right-sized (beachfront-limited) |
| KV ring buffer, capacity (one a die) | 0.50 | 0.50 | 0.50 | 0.50 | 12.8 | the O4 record's sizing; half used |
| KV ring buffer, engine read port | 0.03 | 0.02 | 0.03 | 0.03 | (ring) | justified (latency) |
| UCIe link (latency on the chain) | — | — | — | — | 20.0 | justified (latency) |
| drafter ROM | 0 | 0.03 | 0 | 0 | 57.5 | justified by DFlash |
| sequencer / argmax (busy) | 0.01 / 0 | 0.01 / 0 | 0.01 / 0 | 0.01 / 0 | small | justified (latency) |

The verdicts:

* **Base lanes.** Each die's 6,144 groups are the most its half of the 8-bit
  ROM feeds (read headroom 1.017; 6,656 would be 0.939). The chain binds the
  autoregressive token (101,037 against a 92,161-cycle KV floor), and half the
  groups is 156,217 cycles in the calibrated model, 57% slower a token.
* **Stream unit.** 512 lanes a die is 102,841 cycles (+3.0% a token); 2,048
  is 98,293 (−1.5%), not worth doubling the unit.
* **KV ring buffer.** Each die carries one layer of 8K FP8 KV plus the
  package's refresh cover, 19.3 MB (6.4 mm²), the sizing of the O4 record.
  The stream runs continuously and the engine drains a layer in its attention
  burst, so a layer is the peak occupancy; the die's own four KV heads fill
  half of it, so the ring runs half used at every scenario.
* **Lane copies.** They are idle in autoregressive decode and in every
  KV-bound batch, since each user's KV is its own and from batch 2 the step is
  the KV stream. They carry the DFlash verify, 2.08× single-user tokens/s.
  In the liquid design class the gain holds on the production lane
  (scenario B: 18,720 against 10,874 tok/s, both uncapped) but not on the
  measured 3.97 pJ/MAC lane (scenario A: capped at 6,680 against 7,859), where
  the copies would not pay (section 11); air (the sensitivity) gives the same
  ordering, 14,176 against 8,921 (B) and 4,804 against 5,766 (A). They stay on
  that condition.
* **UCIe.** 73 exchanges a token of 16,384 B of FP32 partials each way, with
  the embedding-row handoff, cost 1,419 cycles on the chain, 1.4% of the
  token; latency, not bandwidth, is what the link costs.
* **Batch.** From batch 2 the base lanes are 72–89% idle and nothing on the
  package can use it: the KV stream is the whole step. Only KV bytes move it.
  The stacks are fixed by the beachfront, so 4-bit KV (a sensitivity, pending
  the accuracy study) is the lever.

Energy per step at batch 1 autoregressive, by the order-of-magnitude basis of
section 10:

| component | share |
|---|---|
| matrix engine (3.97 pJ/MAC) | 17% |
| the rest of the logic (upper bound) | 54% |
| KV reads in the stacks | 28% |
| ROM read and leakage | 0.4% |

Clock gating and operand isolation of the idle lane copies, and of lanes
outside an op's tiles, are therefore requirements, not options.

**HBM comparator** (196,608 lanes, the ROM's INT8 weights and FP8 KV):

| scenario | MFU | MBU (raw) | binding |
|---|---|---|---|
| batch 1 | 0.04 | 0.90 | bytes |
| DFlash, block 16 (serial step) | 0.64 | 0.90 | bytes |
| batch 16 | 0.31 | 0.90 | bytes |
| batch 128 | 0.50 | 0.90 | bytes |
| 2K, batch 128 | 0.99 | 0.69 | MACs |

The comparator's lanes are 4% used at batch 1. The smallest array that keeps
the DFlash step's 128,058-lane need, 8,192 groups (131,072 lanes, tiling
1.000), slows no 8K row but costs the 2K batch rows up to 49% of their
throughput. **The comparator keeps the ROM package's core**, so the ROM ÷ HBM
ratios isolate the weight store. Its stacks and controllers bind every 8K row.

## 16. Prefill and KV ingest (both designs)

**Policy: the GPU does every prefill, cold and incremental, and the package
ingests the KV.** One B200 prefills 8K in 62 ms, about 120,000 prompt tokens
a second (the time to first token on one H200 is 143 ms,
`results/arch/prefill_ingest.json`). On-chip chunked prefill would stall the
batch being decoded.

The source is `docs/ARCH_SPEC_PREFILL.md` (worktree-agent-ab5912eff5bdb5981,
b6d39bd4), which holds the measurements; these rows make them requirements of
this spec:

| id | requirement |
|---|---|
| R-P1 | A PCIe Gen5 x16 endpoint on die 0 of the package, beside its 4 HBM PHYs as on GH100. It sits behind a host PCIe switch shared with a 400G ConnectX-7. Ingest is an RDMA write, peer to peer into the ingest window, with no host bounce. Link goodput is 49.5 GB/s. Die 1's KV heads cross the package's UCIe link (4.2 TB/s, about 80× the endpoint). |
| R-P2 | One KV ingest engine a die (`rtl/hdc/ingest/ot_hdc_kv_ingest.sv`, QKV mode), each writing its own KV heads. It takes vLLM NHD pages (BF16, FP32 or FP8) and writes this core's FP8 layout: K corner-turned into 16-position tiles (`Layout.k_elem`), V position-major, one byte an element. It read-modify-writes the open tile when a turn is appended. It needs 64 KB of block SRAM. Measured: 68 GB/s in (BF16) and one sector a cycle out. It is bit-exact against the golden's own FP8 cache, and the ISA decode from the ingested image is bit-exact. |
| R-P3 | A decode-first HBM arbiter (`ot_hdc_ingest_arb`): a token-bucket share CSR (default 64/256) and 16-sector write bursts; refresh stays with the controller. At the full link rate, ingest takes at most 0.7% of the 7.2 TB/s. The measured share is exact. |
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
(output) token, averaged over a package's users. 4:1 is a chat load; 20:1 is
an agentic load, where tool outputs are appended each turn. The sustained
ingest is R × the decode aggregate × 73,728 B (one position's FP8 K and V over
36 layers), and the B200s needed are R × the decode aggregate / ~120,000
prompt tokens a second per B200. At the KV-bound aggregate (11,921 tok/s), a
4:1 load needs 0.4 B200 per package and 20:1 needs 2.0. The sustained ingest
is 3.5–17.6 GB/s a package, inside R-P1's link. In the HBM capacity model the
8 stacks of 22.5 GB hold 268 users at 8K with FP8 KV after a 0.9 reserve (298
without it). The HBM comparator takes the same endpoint, engines and
arbiter; its ingest share of the stacks is the same 0.7% bound.

## 17. Evidence note: why 8-bit weights, why two reticles

This section records the configurations that were evaluated and rejected. None
of them is the design.

**Why 8-bit.** The earlier design stored HC1-style 3.5-bit weights (INT3 with
one group in eight at INT6). A full-model emulation of the Qwen3 golden on a
GPU (`tools/qwen3_deployment_quality.py`,
`results/quality/qwen3_8b_deployment_arithmetic.json`) measured every
deviation of the deployment arithmetic against the vendor BF16 model on
WikiText-2 at 2K and 8K and 1,000 MMLU questions, against a threshold fixed
before the runs (perplexity +2% at most, MMLU −1 point at most):

| mode | WikiText-2 2K / 8K | MMLU | verdict |
|---|---|---|---|
| arithmetic contract + FP8 KV | −0.16% / −0.09% | −0.3 pt | acceptable |
| + 3.5-bit stand-in, GPTQ | +22.7% / +29.6% | −7.5 pt | not acceptable |
| + 3.5-bit stand-in, rounding | +40.7% / +39.0% | −10.6 pt | not acceptable |
| 4-bit (INT4, rounding) alone | +9.2% / +8.7% | −5.8 pt | not acceptable |

The weight format carries the whole loss; the arithmetic contract and FP8 KV
are quality-neutral. The weight-format search (`tools/qwen3_weight_format_search.py`,
`results/quality/qwen3_8b_weight_format_search.json`) then tried the
sub-8-bit formats with stronger quantisers and rejected all of them on the
same threshold:

* 3.5 bits: the best (Fisher-allocated INT3/INT6 with a Hadamard rotation)
  costs +6.8% perplexity and −4.6 MMLU points;
* ~4.1 bits: a 4-bit Lloyd-Max codebook with rotation passes at 2K (+1.55%)
  but fails at 8K (+2.26%) and on MMLU (−1.3 points);
* 4.5–5.1 bits: codebook and INT8 mixtures pass perplexity but lose 1.2–2.6
  MMLU points; MMLU is the binding criterion from 4 to 5 bits.

**The 8-bit weights pass.** By user decision the weights are 8-bit, exactly
as the RTL contract specifies: signed INT8 without a zero point, one BF16
scale per output row (per vocabulary row for the embedding and the LM head)
applied once after the FP32 K-split sum, quantised by round-to-nearest with a
per-row mean-squared-error clip (no GPTQ). With the arithmetic contract and
FP8 E4M3 KV they change WikiText-2 perplexity by −1.59% at 2K (95% interval
−1.70 to −1.49) and −1.03% at 8K (−1.18 to −0.87), and MMLU by −0.5 points
(−1.4 to +0.4; 74.2% against 74.7%). The perplexity improvement is a real
change of the model, not noise — the per-row clip moves the weights, and
top-1 agreement with BF16 is 95.7% — and MMLU confirms that it costs no
measured accuracy.

**Why two reticles** (`tools/qwen3_8bit_design.py`,
`results/arch/qwen3_8bit_design.json`, which prices every option on the same
timing and power models as this baseline; its O4 row is the adopted design). At 8
bits the target's weights need 449.3 mm² of ROM (262.0 at 3.5 bits: 12/7 as
many select cells, not 8/3.5, because a cell holds a 4-bit nibble) and the
8-bit drafter 57.5 mm². On one 815 mm² reticle with the rest of the floorplan
unchanged, that is **64.2 mm² short with no lane copy** (6.7 mm² short even
without the drafter). The options, each priced for rate, power and cost:

| option | fits | groups a die, m | AR tok/s | DFlash tok/s (block) |
|---|---|---|---|---|
| C0: one reticle, every 8-bit weight in ROM | no (−64.2 mm²) | 8,192, 1 | — | — |
| O1: embedding table in the KV stacks | no (−30.1 mm²) | 8,192, 1 | — | — |
| O2: embedding and lm_head in the KV stacks | yes | 8,192, 1 | 4,402 | 5,412 (3) |
| O3a–c: fewer MAC lanes (4,096–6,144 groups) | yes | 4,096–6,144, 1–2 | 5,498–6,775 | 5,020–7,008 |
| **O4: two reticles in one package, every layer split (adopted)** | **yes** | **6,144, 5** | **10,874** | **18,720 (5)** |
| O5: low-end floorplan assumption (interconnect 5%, overhead 6%) | yes | 8,192, 1 | 8,819 | 7,621 (1) |

A single reticle would fit only by slowing the single user (fewer lanes, or
weights streamed from the KV stacks) or by assuming a smaller floorplan
overhead than the technology file supports; the ROM select cell would have to
shrink from 1.6× to 1.40× a storage-only bit for C0 to fit without lane
copies. Two reticles double the ROM's read bandwidth and the lanes it feeds,
and leave room for four lane copies a die (m = 5). They cost a second die, a second
ROM mask set, two more stacks and a two-reticle interposer of the shipping
B200 class. The iso-area HBM comparator therefore also gets two reticles.

**The adopted option is the record's O4.** The design rates, the cooling-capped
rates, the lane multiplier and the energies above are the record's O4 figures
(`tests/test_qwen3_8bit_design.py` holds the adopted option equal to the
baseline). The record also prices the contiguous layer cut of §1.1
(`o4_contiguous_cut_scenario`) as evidence for the tensor-parallel split.
