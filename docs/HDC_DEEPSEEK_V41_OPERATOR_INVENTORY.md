# DeepSeek-V4.1-Flash on the hardwired decode core: operator inventory

Date: 2026-09-24. Scope: the arithmetic specification and the macro-operation
inventory for a future HDC-based V4.1 ROM package. It follows the reduced Qwen3
decode core described in [TOKEN_PIPELINE_OPTIMIZATION_PLAN.md](TOKEN_PIPELINE_OPTIMIZATION_PLAN.md).

- **Specification:** `tools/hdc_golden_v41.py`. It composes every V4.1 operator
  from `tools/hdc_golden.py`'s binary32 primitives, in a fixed hardware order.
- **Validation:** `tools/hdc_golden_v41_validate.py`, which writes
  `results/rtl/hdc_golden_v41_validation.json`.
- **Test:** `tests/test_hdc_golden_v41.py`.

## 1. What the golden models

The golden models the math of the release's own `inference/model.py`,
`engram.py` and `kernel.py`, on the reduced v2 fixture
(`build/models/deepseek-v4.1-flash-reduced-v2`). It does not use the ABI3
compiler. It keeps the numerics the model declares:

- BF16 storage of every tensor the reference stores in BF16;
- FP8 activation quantisation, per 32-element block, in front of every FP8 or
  FP4 linear;
- FP8 quantise-dequantise of window KV rows;
- FP4 quantise-dequantise of index keys, index queries and compressed KV rows;
- BF16 attention probabilities in the probability-value product.

It chooses the orders the reference leaves to GPU libraries (see the module
docstring). The golden prefills one position at a time, as the HDC would.

### Validation (reduced v2 fixture, oracle prompt of 8 tokens)

- **Engram tables.** The hash tables it derives (compressed token map, primes,
  offsets, multipliers) equal the vendor module's buffers exactly.
- **Teacher forcing.** Each layer runs from the oracle's own input, over the
  prompt and the oracle's decode steps. The golden's BF16 tensors equal the
  oracle's except for isolated one-ulp flips (about one element in a
  thousand). The logits agree to about two binary32 ulps, and the argmax
  agrees at all 16 generated positions. The counts are in the validation
  record.
- **First token.** Free-running, the first token (from the prompt's last
  position) matches the oracle, 3118, with the oracle's own top-1 margin.
- **Later tokens.** These are not a stable target on this fixture, for three
  reasons:
  1. *The oracle disagrees with itself.* Feeding the same prompt one position
     per call, instead of in one prefill call, changes the release's first
     token (see `oracle_self_consistency` in the record). Its decode kernel
     streams KV in blocks of 64 entries, starting from the oldest ring slot, and
     rescales by a running maximum. Prefill of a short prompt sees one block.
     The golden's specified two-pass softmax therefore matches prefill exactly,
     and differs from decode by rounding.
  2. *Emulating the decode kernel is exact locally.* With
     `Model(vendor_decode_from=8)` the golden emulates that block order, and
     teacher-forced decode steps are then as exact as prefill.
  3. *Free-running tokens depend on rounding.* A single one-ulp BF16 flip in
     layer 0's attention output enters the KV cache and grows until the argmax
     moves. This was measured: replacing the Newton reciprocal by IEEE division
     at the attention normalisation removes the first such flip, and then a
     different flip appears later. `results/abi3/deepseek_v41_v2_divergence_settled.json`
     already shows that a perturbation below one percent at layer 0 changes this
     fixture's token. The fixture has random weights, and its top-1 margins are
     a few hundredths.

  The record grades tokens free-running. In the release's decode order the
  golden reproduces the oracle's first seven tokens; in its own two-pass order,
  the first. The test pins the first four in the decode order.

### Reference behaviour that is ambiguous or quirky

- **Index-key alias.** A KV-source indexer publishes
  `shared_attn.index_k` only on steps where its compression group completes.
  On other decode steps it reads whatever the last publisher left there, which
  is layer 20's ratio-1 key cache. The alias is inert here: every ratio-2 layer
  has at most 16 compressed positions below position 32, and `index_topk` is
  16, so everything is selected anyway. The golden implements the intended
  semantics, where each layer reads its own source's keys.
- **Top-k ties.** The reference leaves top-k ties to `torch.topk` on the GPU,
  and index scores are BF16, so ties are possible. The golden ranks ties to
  the lower index.
- **Masked candidates.** Candidate-masked positions carry −inf, but the
  reference still selects them when fewer than `index_topk` finite scores
  exist. It then attends to them, because only positions beyond the causal
  horizon become −1. The golden reproduces this. At the reduced shapes every
  block is a candidate, so the case never arises.
- **Mix coefficients.** Hyper-connection mix coefficients are used one
  sublayer late. Attention consumes the previous layer's FFN `pre` mix, and the
  FFN consumes this layer's attention `pre` mix. The golden follows the
  reference.
- **Divisions.** The reference divides at the attention normalisation, the
  Sinkhorn steps, pooling, routing and in SiLU. The golden divides there too,
  with IEEE division, the qualified `rtl/abi3/ot_a3_fp32_div_rne_pipe.sv`. The
  reference's exp and rsqrt are not correctly rounded: a correctly rounded exp
  disagrees with it more often than `hdc_golden`'s polynomial does, so the
  polynomial stays.

## 2. Macro-operations beyond the Qwen set

Qwen's decode core already has these operations:

- BF16 matvec (sequential FP32 accumulation, K-split tree);
- RMSNorm;
- RoPE (half-split pairs);
- two-pass softmax attention;
- SiLU·up;
- residual add;
- argmax.

The table lists what V4.1 adds. Shapes are given as [rows, columns] for the
reduced model / the shipped model. Costs are per token.

| Macro-op | Math (golden function) | Reduced shapes | Shipped shapes | Existing unit or new | Per-token cost |
|---|---|---|---|---|---|
| FP8 block linear | activation to E4M3 per 32 with a UE8M0 scale; exact 32-term block dot; scale by 2^(ew+ex); sequential FP32 over blocks; BF16 out (`linear_q`) | wq_a [32, 160], wq_b [2048, 32], wkv [32, 160], wo_b [160, 256], indexer wq_b [1024, 32], shared expert, Engram wkv [800, 768] | wq_a [1280, 5120], wq_b [32768, 1280], wkv [512, 5120], wo_b [5120, 8192], indexer wq_b [4096, 1280], Engram wkv [25600, 6144] | **New ME lane type**: E4M3-by-E4M3 multipliers, an exact block accumulator (about 42 bits) and one FP32 scale-add per block. It replaces the BF16 lanes for these weights. | one MAC per weight |
| FP4 expert linear | as above, with E2M1 weights and a UE8M0 scale per row and 32 columns | w1/w3 [64, 160], w2 [160, 64]; 6 of 12 routed | w1/w3 [2304, 5120], w2 [5120, 2304]; 6 of 384 routed | Same new lane, with an E2M1 decode in front | the dominant term at shipped scale |
| Activation quantiser | block absmax; scale exponent = ceil(log2(amax·(1/448))) from the bits; E4M3 RNE with saturation (`quant_fp8`, `qdq_fp8`) | every FP8/FP4 linear input; window KV row [32] | every linear input; window KV row [512] | **New SU stage**: MAX reducer (exists) plus an exponent adder and an E4M3 rounder | one pass per linear input |
| FP4 quantise-dequantise | UE8M0 scale (index q/k, block 32); E4M3 scale with midpoint compares (compressed KV, block 16) (`qdq_fp4_e8m0`, `qdq_fp4_e4m3`) | q [32, 32], key [32], latent [32] | q [32, 128], key [128], latent [512] | New SU stage; the E4M3-scale variant needs seven compares and no divider | small |
| Grouped low-rank output | wo_a is block diagonal: 8 groups, each [o_rank, 8·head_dim]; BF16 | [8, 32, 256] | [8, 1024, 4096] | Existing ME, as 8 matvecs, or one op per group slot | heads·head_dim·o_rank |
| Interleaved-pair RoPE with inverse | pairs are adjacent elements of the last rope_dim; conjugate rotation on the attention output (`rope_tail`); two frequency tables, plain (layers without compression) and YaRN at compress_rope_theta | rope_dim 4 | rope_dim 64 | Existing SU, with a new address pattern and a second table ROM | small |
| Sparse attention with sink | window rows plus selected compressed rows, one shared KV (key equals value); sink joins the denominator only; IEEE divide at the output | 64 heads, head_dim 32, up to 128 + 16 rows | 64 heads, head_dim 512, up to 128 + 512 rows | Existing attention path (scores, softmax, PV) plus a row gather from two caches, the sink add and a **divider** for heads·head_dim quotients | 2·heads·head_dim·rows MACs |
| KV compressor | ratio 2: FP32 kv and gate projections, a 2-slot softmax per channel, pooling, RMSNorm; ratio 1: BF16 projection and RMSNorm (`compressor`) | [32, 160] | [512, 5120] | Existing ME and SU; slot state lives in the KV SRAM | only 4 source layers |
| Indexer | wq_b, then RoPE and FP4 QDQ; weights_proj; BF16 scores against index keys; ReLU, weight, then a sum over index heads (`indexer`) | 32 heads of width 32 over n ≤ 24 keys | 32 heads of width 128 over context/ratio keys (up to the candidate set) | ME for the projections and scores; SU reducer for the head sum | grows with context: the largest context-dependent term at shipped scale |
| Candidate block select | block max over 8 positions; pin the newest block; top-k blocks (`candidate_blocks`) | trivial: every block is kept | 2048 blocks of 8 | **New SELECT unit**: rank by pairwise comparison, ties to the lower index | context/8 comparisons per candidate |
| Index top-k | top-k over index scores, emitted in position order (`topk_lowest_index`) | k = 16 | k = 512 | Same SELECT unit (a streaming top-k with a k-entry sorted buffer is the shipped-scale form) | context comparisons |
| Hyper-connections | mixes = [24, 4·dim] FP32 matvec times the stream rsqrt; sigmoid pre/post; 4-by-4 softmax plus 20 Sinkhorn row/column normalisations; collapse (`hc_pre`) and expand (`hc_post`) | [24, 640] | [24, 20480] | ME for the projection; a **small Sinkhorn unit** (16-entry register file, adder and divider) whose serial chain runs alongside the sublayer | two mixes per layer; the divides do not scale with the model |
| Router | FP32 gate matvec; sqrt(softplus); add the bias; top-6; weights from the unbiased scores divided by (sum + 1e-20), times 1.5 | [12, 160] | [384, 5120] | ME; **softplus** in the SFU (exp, divide, a degree-17 odd series; no log unit); SELECT unit for the top-6 | dim·experts |
| Engram lookup and gate | 24 hash columns: integer multiply by a constant, XOR, modulo a constant prime; FP8 rows times a UE8M0 scale; FP8 wkv to 4 keys plus 1 value; per copy a normalised dot, a signed sqrt, a sigmoid gate and the residual add (`engram_layer`) | tables of about 190K rows of 32 bytes, 2 layers | tables of about 384M rows of 256 bytes, 2 layers | **New hash unit** (64-bit multiply and Barrett modulo), a row-gather port on the table ROM, and IEEE sqrt in the SFU | 24 table reads per Engram layer |
| Clamped SwiGLU | up clamped to ±10, gate to ≤ 10; silu(g) = g / (1 + exp(−g)) | inter 64 | inter 2304 | Existing SU sigmoid class, plus a clamp stage and division form | small |

Reduced-model operator shares, in MACs per token at 24 positions:

- experts about a third;
- q/kv/o projections and attention about a quarter each;
- hyper-connections and the Engram projection a few hundredths each.

At shipped scale the experts are over half. The q/kv/o projections follow at
a bit over a quarter, then attention, and then the indexer, which grows with
context. These shares come from
`tools/hdc_golden_v41.py`'s shapes; they are arithmetic, not measurements.

**New units, summarised:**

1. an MX-format matrix-engine lane (E4M3/E2M1 decode, exact 32-term block
   dot, FP32 scale-accumulate);
2. an activation quantiser stage (absmax, power-of-two scale, E4M3/E2M1
   rounding);
3. a pipelined IEEE divider and square root in the stream unit (both
   qualified elsewhere in the repo);
4. softplus as an SFU class (exp, divide, odd series);
5. a SELECT unit for top-k (index top-k, candidate blocks, router top-6);
6. a Sinkhorn micro-unit;
7. an Engram hash-and-gather unit.

## 3. Package partitioning

### ROM array (layer per package)

The Qwen array cuts at layer boundaries and at the residual after o_proj.
V4.1's cut points are different, because the residual stream is four copies
(4·dim values cross a link instead of dim), and because layers share state.

- **Carry the stream and the pending mix.** Each link carries the four-copy
  residual and the pending `pre` mix (4 values), since the next attention
  consumes the previous FFN's mix.
- **Group layers by KV source.** A package boundary should not separate a KV
  source from its consumers. Layers 2–7 read layer 2's compressed KV and
  selection, 8–13 read 8's, 14–19 read 14's, and 20–39 read 20's compressed KV
  and candidate mask. The group [2–7] fits a package (or a small group of
  packages) that holds the source's compressed cache. Layers 20–39 span many
  packages, so layer 20's compressed KV, index keys and candidate mask must be
  forwarded. This is a per-token broadcast of one compressed row plus the
  selection, which is small next to the stream.
- **Keep Engram on its own ROM.** The Engram tables are the largest ROM items
  at shipped scale, larger than a layer's experts. Layers 1 and 14 need a
  table-ROM package, or a package pair, with a gather port. The table read is
  24 rows per token and needs no compute.
- **Split the attention and MoE halves.** As in Qwen's 10- and 12-package
  arrays, each layer splits into an attention half and a MoE half. The MoE
  half dominates at shipped scale, so routed experts can further split across
  packages by expert id. A token touches 6 of 384 experts plus the shared one.
- **Split lm_head by vocabulary.** The best {row, logit} is carried forward,
  and replaced only when strictly greater (lowest id on ties).

### Wafer

On a wafer, the link cost that pushes the array toward large packages
disappears:

- one tile per attention half-layer;
- expert tiles grouped by expert id;
- the Engram tables in dedicated ROM tiles near layers 1 and 14;
- the four compressed-KV sources as tiles that multicast their per-token rows
  to their consumer layers.

The shipped context lever is the indexer. Its keys grow with context and are
scored every token at eight layers, so index-key SRAM and the SELECT unit
belong in the source-group tiles.
