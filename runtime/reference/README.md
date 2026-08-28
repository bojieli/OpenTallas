# Independent target-format reference

This directory is outside compiler lowering and RTL. Its implementations may
share versioned interface definitions, but they do not call compiler image,
placement, microcode, schedule, or service-engine algorithms to calculate an
expected result.

`formats.py` is the first DeepSeek V4 target-precision slice. It provides exact
rational scalar semantics for:

- E2M1 values, RNE conversion, saturation, and the official low-nibble-first
  packed layout;
- E8M0 scales, including the reserved `0xff` poison value;
- FP8 E4M3FN classification and round-to-nearest-ties-to-even conversion;
- BF16 classification and binary32-to-BF16 conversion;
- exact IEEE binary32 decode/rounding and ordered fused-product accumulation;
- packed MXFP4 block decoding; and
- NUM-3.3 BF16 activation-block microscaling;
- 32-value MXFP4×FP8 routed block dots; and
- 128-value FP8×FP8 dense block dots.

The tests exhaust every E2M1, E8M0, E4M3FN, and BF16 code, exercise rounding,
saturation, poison, scale-selection, and packing boundaries, and compare every
E4M3FN encoding with the public RTL decoder. A separate development audit also
matched every E4M3FN, BF16, and E8M0 decode against the installed PyTorch dtype
implementation with zero differences. Binary32 tests include deterministic
round trips over 20,000 random finite encodings and cases where ordered
per-product accumulation intentionally differs from one final exact reduction.
A separate SM120 development audit compared E2M1 conversion for all 65,280
finite BF16 encodings with CUDA's native `cvt.rn.satfinite.e2m1x2.f32`. After
the governed positive-zero canonicalization, there were zero differences.

This closes neither `M1` nor numerical qualification. Matrix operators beyond
the qualified dense FP8 linear path, vector operators beyond target-hidden
capture and HC post-mixing, attention/routing operators, real-checkpoint known
answers, layer differentials, end-to-end logits, and task quality remain open.
The earlier exact-integer evaluator remains fixture-only evidence.

`matrix.py` composes the scalar/block rules into complete `FP8_LINEAR`
semantics. It quantizes each BF16 activation block once, applies the released
128-by-128 E8M0 scale orientation, executes ordered 128-value FP8 block dots,
reduces block partials through the canonical balanced tree, and rounds the
binary32 result to BF16. It returns explicit activation-block and output-element
saturation counts. Tests cross the output scale-tile boundary and compare
multi-block randomized matrices with an independently assembled composition.
This does not yet provide a checkpoint-derived known answer or service-engine
opcode.

`quantization.py` implements the complete indexer `FP4_QDQ` boundary. It
flattens leading dimensions into source-order rows, selects an independent
power-of-two E8M0 scale for every 32 BF16 values using the pinned binary32
reciprocal/bit-ceiling sequence, applies E2M1 RNE, and reconstructs BF16 through
the declared binary32 operations. It exposes internal scale and E2M1 codes for
checking even though the official in-place wrapper returns only BF16. Tests
cover every quantization midpoint, the unusual all-zero `0x01` scale, lower and
upper scale transitions, independent blocks, malformed shapes, nonfinite
input, and intermediate overflow. A development differential matched 2,047
successful random/boundary rows on native SM120 in scale, E2M1 code, and BF16
output; the single extreme-overflow row was rejected by the target fail-closed
rule.

`indexing.py` independently implements the three source-constructed integer
index tensors used by `WINDOW_INDEX`, `COMPRESSED_DENSE_INDEX`, and
`DSPARK_WINDOW_INDEX`. It preserves the pinned prefill/decode branch behavior,
circular-window order, compression-completion boundary, offsets, padding, and
DSpark history/draft address split. Inputs and signed-int32 output bounds fail
closed. These structural references do not implement learned index scoring,
top-k tie order, KV mutation, sparse attention, or any service-engine lowering.

`lookup.py` implements the two pinned pure-gather paths. `TOKEN_EMBED` selects
global embedding rows while carrying BF16 as exact 16-bit encodings; this is
equivalent to the source vocabulary-shard masking and all-reduce because one
and only one shard owns a valid token. `HASH_ROUTE` selects the checkpoint's
ordered expert-ID row for each flattened token ID and intentionally preserves
duplicates. It does not implement router scoring, selected-weight gathering, or
expert dispatch.

`structural.py` implements the bit-preserving `HC_EXPAND` copy and the integer
noise-block construction that precedes `DSPARK_NOISE_EMBED`. The HC result
copies every BF16 encoding without arithmetic. The DSpark helper fixes the
current token at column zero and fills later draft columns with the pinned noise
token. The qualified composite then applies the shared global BF16 embedding
lookup and HC expansion without changing any payload bit. Main-hidden projection
remains a separate matrix operator.

`selection.py` resolves the source's intentionally unpinned `torch.topk` tie
behavior. The official release requires `torch>=2.10.0`, while PyTorch 2.10
states that tied indices are not stable. The target rule is therefore score
descending, then logical index ascending. Router scores use raw binary32
encodings; learned index scores use raw BF16 encodings. Both are compared as
exact rationals and NaNs fail closed. `BIASED_TOPK_ROUTE` performs one
binary32-rounded selection-bias add before this ordering; `INDEX_TOPK` applies
the BF16 causal completion mask, deterministic top-k, `-1` padding, and the
compressed-cache offset. Learned index scoring remains a separate pending
operator.

`routing.py` implements `ROUTER_WEIGHT_NORMALIZE` over raw FP32 encodings. It
gathers unbiased scores in selected slot order, retains duplicate selection
slots, reduces the denominator with the NUM-6.1 canonical balanced tree, rounds
each division once, and rounds the subsequent route-scale multiplication once.
Zero denominators, negative scores, nonfinite values, malformed indices, and
overflow fail closed. This fixes a deterministic accelerator tree rather than
claiming that all PyTorch backends use one reduction order.

`dispatch.py` implements `EXPERT_DISPATCH`. It applies the source's row-major
batch/sequence flattening, emits only nonempty expert groups in ascending
logical expert-ID order, and orders each group's assignments by flattened token
then selected slot. BF16 hidden rows and binary32 route weights are copied
bit-for-bit. Duplicate expert IDs for one token remain distinct assignments, so
later expert execution/reduction cannot silently discard a selected slot.
Malformed shapes, out-of-range experts, or nonfinite payloads fail closed. A
known answer reuses all 48 expert IDs from the independently checked official
lookup slice in `docs/DEEPSEEK_V4_LOOKUP_EVIDENCE.md`.

`vector.py` implements `TARGET_HIDDEN_CAPTURE` and `HC_POST` over finite BF16
encodings and binary32 coefficients. Capture widens the four official HC
streams, reduces the source axis with the NUM-6.1 balanced tree, divides once,
and converts once to BF16. HC post-mixing interprets `comb[source][destination]`,
rounds each branch/residual product once, reduces residual sources with the same
tree, adds the branch contribution, and converts once to BF16 while counting
finite output saturation. Shape mismatch, nonfinite input, and intermediate
overflow fail closed. Both trees are deterministic target adaptations rather
than claims about incidental backend reduction order.
