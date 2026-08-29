# DeepSeek V4 DSpark Markov-loop reference evidence

- **Evidence date:** 2026-08-29
- **Qualified boundary:** target-precision `MARKOV_AUTOREGRESSIVE_LOOP` semantics
- **Official model:** `deepseek-ai/DeepSeek-V4-Flash-0731`
- **Official revision:** `7872f01b1d1fe23eabc4c98b48bffcef5a386062`
- **Reference profile:** `opentallas.deepseek_v4_markov_loop_binary32.v1`
- **Graph contract at qualification:** `7c811fc63038c76fd5268facbbb12244fab2e7fbf75bd7cf7598bd20da239122`

## Qualified boundary

The released final DSpark stage first produces five base vocabulary-logit rows.
`DSparkBlock.forward_head` then executes exactly five causally ordered Markov
iterations. At iteration `i`, the token in output column `i` selects one BF16
row from `markov_w1`; that 256-wide row is projected through `markov_w2` into a
binary32 vocabulary bias; the bias is added to base-logit row `i`; and sampling
writes output token column `i+1`. The resulting token is therefore the lookup
index for the next iteration:

```text
input token [B]
  -> repeat i = 0..4 in increasing order:
       BF16 markov_w1 lookup [B,256]
       BF16-storage/binary32-runtime markov_w2 [B,129280]
       binary32 RNE add into base_logits[:,i,:]
       sample adjusted_logits[:,i,:]
  -> output tokens [B,6]
     adjusted logits [B,5,129280]
     Markov embeddings [B,5,256]
```

The initial token is retained at output column zero. All five adjusted logit
rows and all five BF16 embeddings are source-visible: the released method
returns the in-place-adjusted logits and passes the embeddings to the confidence
head. The graph qualification consequently exposes `tokens`,
`adjusted_logits`, and `embeddings`; hiding the adjusted logit tensor would omit
one result returned by `Transformer.forward_spec`.

Both Markov matrices are vocabulary-sharded into equal contiguous intervals.
The embedding path has one owning rank for each lookup; the vocabulary-head
path concatenates local binary32 projections in increasing tensor-parallel rank
order. The reference accepts world sizes 1, 2, 4, and 8 and reconstructs the
logical global tables from rank-ordered shards. It does not claim execution of
a physical all-reduce or all-gather.

Every finite BF16 embedding/head operand widens exactly. Each Markov-head logit
starts at binary32 positive zero, traverses rank columns `0..R-1`, forms an exact
BF16 product, and performs one binary32 RNE fused product-add. Adding that bias
to the base logit is a distinct binary32 RNE operation. No BF16 conversion
occurs on either the bias or adjusted-logit boundary. A cancellation sentinel
distinguishes increasing-rank accumulation from a one-round exact dot, and a
half-ULP sentinel independently fixes the later logit-add rounding point.

## Source and checkpoint authority

The suite re-reads the pinned model, conversion source, configuration, and
checkpoint index, checks their hashes, and inspects the exact
lookup/project/loop/add/sample and equal-contiguous-sharding structures:

| Official artifact | SHA-256 |
|---|---|
| `inference/model.py` | `c0c19e6c9fa439bac7fbb1c5bc1868232dfd5aa2f439a548d0e33dcc2a9edd3f` |
| `inference/convert.py` | `6efe65ebc66b18c9f2656816608f941cacfe20da79c2dee19040ecbee8b42bfe` |
| `inference/config.json` | `c90861f3d10a9e4ef5954f8f1a34c529d480da1c5799f84660028f4e38e14e71` |
| `model.safetensors.index.json` | `98efab455cf08dfbbbaaba6f570e1bf10bf927d2b4c3c453a59c2f6f0e3be92b` |

The governed checkpoint lock is
`30b3d07304b92cb26440e5ea9e28dcb06c835dbf35652529fa9a856da07ad760`.
Both relevant tensors reside in `model-00048-of-00048.safetensors`, have shape
`[129280,256]`, use BF16 storage, and contain 66,191,360 bytes each:

| Tensor | Complete SHA-256 |
|---|---|
| `mtp.2.markov_head.markov_w1.weight` | `966bd0507046347754d0f4bf3addd6df6c179ff16243d63998258b3987e4b2f5` |
| `mtp.2.markov_head.markov_w2.weight` | `40ac7e99651c5c6aab8d2555ff65d247931f318414cf94baedc6da2d3bf7c175` |

The complete-payload test reads every byte, rejects any BF16 NaN or infinity,
and reconstructs these four MP=4 intervals independently:

| Rank | Global rows | W1 SHA-256 | W2 SHA-256 |
|---:|---:|---|---|
| 0 | `0..32319` | `ceea71f22c755c8517e3698004280d64712c93c5a4115c008edb23b2512917f6` | `4e7fb04d60fc0c4fc40020ef9749193607994a35a5c19ab7a6771074a9750f6a` |
| 1 | `32320..64639` | `1ee7e87fb6ef425705393a68c9fc55328e1463e7bc18aad65c343c0177bdc423` | `ea4a7b2122d411f0635ae2e1a21ecfb08687b66721e5442d7ad5e56acaeb46c8` |
| 2 | `64640..96959` | `35170e3fbb7284731f9c83262fd9cd2fdaf24bf8d89956a56b5851de66864ba5` | `c9b30d6e6433fda98a3601b91c7bd3fdc30ffe6208fffc6447aab6de561745ca` |
| 3 | `96960..129279` | `c923b8cd3bcea770a62f5cc655ba9dbe00deed5036493dbbf1642fe471534fef` | `d80ce53194fbed4a6a6f1d34da993cdf7e915d316f94ec331c27be000f0a16dc` |

This establishes complete storage identity and partition extent. It does not
execute all `5*B*129280*256` official products.

## Complete bounded causal evidence

Small complete fixtures exercise behavior that selected official rows cannot:

- a four-token, rank-four identity/permutation corpus produces the exact causal
  cycle `0,1,2,3,0,1` and a phase-shifted second batch;
- every retained embedding, Markov bias, adjusted logit, sampled token, and
  entropy offset is recomputed independently;
- zero-temperature ties choose the first vocabulary index and consume no
  entropy;
- 80 randomized cases vary batch, vocabulary, rank, tensor-parallel world size,
  BF16 weights, binary32 base logits, and causal token histories;
- nonfinite codes, ragged dimensions, unequal shards, out-of-range tokens,
  arithmetic overflow, and entropy exhaustion poison without a result; and
- mutable caller containers cannot alias the deeply immutable result.

The complete reference validates the whole supplied W1 table, W2 table, and
base-logit tensor before exposing a successful result. The returned record
retains the copied base logits, five bias rows, five adjusted rows, five
embeddings, six tokens, all five sampling records, entropy continuation, source
hashes, and exact logical counters.

The record retains weight hashes rather than the complete tables. Public result
construction can detect structural/output mutation and reconstruct every
post-projection add and sampling dependency, but cannot by itself authenticate
checkpoint provenance or recompute the Markov-head dots. Those claims require
entry through the qualified function and the separately locked payload tests.

## Full-rank official selected-row evidence

The selected IDs cross both sides of every MP=4 boundary:

```text
0, 32319, 32320, 64639, 64640, 96959, 96960, 129279
```

Every corresponding W1 and W2 row is independently read at the complete rank
of 256 and checked against a frozen row hash. Projecting official W1 row zero
against the eight official W2 rows using increasing-rank binary32 accumulation
produces:

```text
0xC0581E4C
0xBEA8489F
0xBF051136
0xBF89F37E
0xBF3EFBFF
0xBFA3E9F0
0xC0155C56
0xC09B71D2
```

The eight-logit little-endian stream has SHA-256
`cd2d68aff994647705aee41fd16a5f13f8219fe61ee824eae6f054d43127470d`.
This proves one nonzero official embedding row against eight full-rank official
head rows. It is not a complete vocabulary projection, does not include a real
DSpark base-logit row, and is not a checkpoint-derived end-to-end draft result.

## Sampling and entropy boundary

The pinned source configuration defaults temperature to `1.0`, encoded as
binary32 `0x3f800000`. The release requires only `torch>=2.10.0`; it does not pin
a Torch/CUDA build, generator state representation, exponential word-to-value
mapping, softmax exponential, or reduction order. Exact nonzero-temperature
source replay therefore fails closed by default, including at causal step zero.
No implicit host entropy, process-global RNG, or wall clock can enter the
reference.

Two qualified modes remain explicit:

1. Binary32 positive or negative zero selects source-exact finite-binary32
   first-index argmax for each of the five rows and leaves any supplied entropy
   object unchanged.
2. A caller may set `require_pytorch_cuda_equivalence=False` and provide an
   immutable positive-finite binary32 stream of post-`exponential_(1)` draws.
   This separately named target adaptation uses the qualified correctly rounded
   exponential and balanced-softmax profile. Draw order is step-major, then
   batch-major, then vocabulary-major. Exactly `5*B*V` draws are consumed, and
   every step's immutable continuation becomes the next step's input.

Supplying too few draws may fail at a later causal step, but the caller's
original entropy value remains unchanged and no partial result commits. This
deterministic adaptation preserves the released algebra without claiming
PyTorch/CUDA stochastic bit identity or a seed-to-draw mapping.

## Logical accounting boundary

For batch `B`, vocabulary `V`, Markov rank `R`, and fixed block size five, a
successful transaction reports:

```text
initial token reads/writes             = B
causal token reads                     = 5 * B
base binary32 logits validated/read    = 5 * B * V
W1 BF16 values validated               = V * R
W2 BF16 values validated               = V * R
embedding row lookups                  = 5 * B
embedding BF16 values read/written     = 5 * B * R
embedding binary32 widens              = 5 * B * R
logical unique W2 binary32 widens      = V * R
exact product-accumulates              = 5 * B * V * R
binary32 accumulation roundings        = 5 * B * V * R
Markov bias values produced            = 5 * B * V
separate binary32 bias additions       = 5 * B * V
adjusted binary32 logits produced      = 5 * B * V
sampling calls                         = 5
sampling logits read                   = 5 * B * V
argmax comparisons                     = 5 * B * (V - 1)
entropy draws                          = 0 or 5 * B * V
sampled tokens written                 = 5 * B
complete output tokens written         = 6 * B
transaction commits                    = 1
```

These are semantic counts. The unique W2 widen count does not assert one
physical read or cache fill, and product counts do not imply hardware issue
rate. Nothing here selects ROM, SRAM, HBM, cache, bank, NoC, or collective
placement or measures transactions, bursts, flits, instructions, cycles,
latency, bandwidth, inference bytes/s, throughput, power, energy, area,
routing, PPA, manufacturability, or GPU advantage.

## Reproduction

```bash
pytest -q \
  tests/runtime/test_deepseek_v4_sampling.py \
  tests/runtime/test_deepseek_v4_markov_loop.py \
  tests/compiler/test_deepseek_v4_graph.py

ruff check \
  runtime/reference/markov_loop.py \
  tests/runtime/test_deepseek_v4_markov_loop.py \
  compiler/frontend/deepseek_v4_graph.py \
  tests/compiler/test_deepseek_v4_graph.py
```

The complete official payload and selected-row cases require the pinned local
checkpoint. Without it, those cases skip; complete small fixtures, randomized
causal arithmetic, sampling boundaries, poison, immutability, and counters
remain runnable.

## Explicit nonclaims

This qualification does not establish checkpoint-derived DSpark hidden state
or base logits, a complete official vocabulary projection, exact
nonzero-temperature PyTorch/CUDA replay, RNG quality, confidence projection,
target verification, speculative acceptance, complete generation, generated
deployment artifacts, artifact-driven service execution, a physical
tensor-parallel collective, compiler image or placement, schedule, RTL,
physical ROM/SRAM/HBM traffic, cycles, latency, bandwidth, inference bytes/s,
throughput, power, energy, area, routing, PPA, manufacturability, task quality,
or GPU advantage.
