# Numerical-format and determinism specification

**Document:** SPEC-NUM 1.2

The numerical contract is architectural. A different encoding, reduction tree,
rounding point, saturation rule, or exceptional-value policy is an externally
visible behavior change and requires a specification major/minor review plus model
quality requalification.

## NUM-1 Numeric profiles

### NUM-1.1 Profile IDs

| ID | Name | Purpose | Closure status at architecture freeze |
|---:|---|---|---|
| 0 | `INT_DV` | small signed-integer public-tool verification | defined; not target inference |
| 1 | `DSV4_MXFP4` | DeepSeek routed MXFP4 plus dense FP8 | target contract; RTL/DV pending |
| 2 | `FP8_DENSE` | dense/shared FP8 path and vector boundaries | target contract; RTL/DV pending |
| 3 | `BF16_VECTOR` | attention/vector functional-macro boundary | target contract; RTL/DV pending |
| 4 | `QWEN3_BF16_GQA` | Qwen3-8B dense decoder and full GQA control | dense-control contract; RTL/DV pending |
| 5–15 | reserved | no interpretation | reject |

The configured image/session selects one compatible profile set. Commands cannot
change it in flight. Kimi U8-packed weights require a separate compiler-qualified
profile before they can be executed numerically; Kimi remains valid as capacity,
NoC, control, and fault stress without that promotion.

### NUM-1.2 Architectural values

Architectural hidden activations and stage-link hidden vectors are BF16. Routed
weight storage is packed MXFP4 E2M1 with E8M0 microscaling. Dense/shared weight
storage is FP8 E4M3FN with E8M0 scales. Tile and collective partial sums are IEEE
binary32. The compiler manifest records every tensor's source dtype, canonical
internal dtype, block/tile dimensions, scale layout, and conversion hash.

Qwen3-8B selects `QWEN3_BF16_GQA`: decoder and untied LM-head weights remain BF16
in the released image, input embeddings are lookup-resident, and each attention
layer stores/reads BF16 K and V for eight KV heads of 128 elements (4,096 bytes per
token/layer). This profile is deliberately separate from the DeepSeek MXFP4/FP8
profile; no quantization or speculative draft behavior is implied.

## NUM-2 MXFP4 routed weights

### NUM-2.1 E2M1 and E8M0 encoding

One E2M1 value occupies a four-bit nibble. Bit 3 is sign. Positive encodings and
their exact real values are:

| Magnitude bits `[2:0]` | Value |
|---:|---:|
| `000` | 0 |
| `001` | 0.5 |
| `010` | 1 |
| `011` | 1.5 |
| `100` | 2 |
| `101` | 3 |
| `110` | 4 |
| `111` | 6 |

Sign negates a nonzero magnitude. Encoding `1000` is negative zero on input and
is canonicalized to positive zero at the first arithmetic boundary. E2M1 has no
infinity or NaN.

An E8M0 byte `e` in 0..254 represents the exact scale `2^(e-127)`. `0xff` is the
reserved NaN scale and poisons the transaction. E8M0 has no zero; an all-zero data
block uses the canonical scale byte `0x7f` (1.0).

One released DeepSeek routed scale covers 32 logical weights along the reduction
dimension. The real weight is `E2M1(nibble) × E8M0(scale)`. If later tensor metadata
declares another block dimension, it requires a new image/profile version rather
than an implicit reinterpretation.

### NUM-2.2 Canonical packing and layout

The internal byte packing is:

```text
logical weight[2*i]   = packed_byte[i][3:0]
logical weight[2*i+1] = packed_byte[i][7:4]
```

Logical reduction index increases first, then output row, tensor, expert, layer,
and image region as enumerated by the manifest. Scale index is
`floor(reduction_index / 32)` for each output row. The compiler converts any
checkpoint-specific ordering into this layout and emits known-answer blocks and
CRCs. RTL never infers nibble order from a source dtype string.

## NUM-3 Dense FP8 and activation quantization

### NUM-3.1 FP8 E4M3FN weights

FP8 dense/shared weights use the finite-only E4M3 encoding identified by
safetensors `F8_E4M3`: one sign, four exponent, and three fraction bits, exponent
bias 7, subnormals enabled, and no infinity. Only `0x7f` and `0xff` are NaN;
`0x7e` and `0xfe` are the valid finite endpoints +448 and -448. NaN weight
encodings poison the transaction. Negative zero is canonicalized to positive
zero.

Released dense weight scale tensors describe 128×128 logical weight tiles. One
E8M0 scale multiplies each FP8 value in its tile. Scale `0xff` is illegal. Exact
tile orientation and edge padding are compiler-manifest fields and known-answer
tested.

### NUM-3.2 BF16 activation boundary

BF16 uses the upper 16 bits of IEEE binary32: sign bit 15, eight exponent bits,
seven fraction bits, exponent bias 127, subnormals, infinities, and NaNs. Service
inputs must be finite. Signaling/quiet NaN or infinity at a checked architectural
boundary sets numeric-exception poison. Negative zero is accepted and canonicalized
to positive zero before quantization/reduction.

Vector functional macros consume and produce BF16 plus explicit status. They may
use higher internal precision but must return bits matching the qualified reference
model for the frozen operation, rounding, and order.

### NUM-3.3 Activation microscaling

Before an FP8/MXFP4 matrix operation, each manifest-sized activation block is
converted from BF16 to E4M3FN plus one E8M0 scale. Routed blocks contain 32 values;
dense blocks contain 128 unless the manifest selects a separately qualified profile.

For finite block values `x_i`, let `a = max(abs(x_i))` and `M = 448`:

- if `a = 0`, choose scale 1.0 (`0x7f`) and encode positive zeros;
- otherwise choose the smallest power-of-two E8M0 scale `s` for which `a/s <= M`;
- if no legal E8M0 scale represents `s`, poison with numeric range error;
- encode each `x_i/s` to E4M3FN using round-to-nearest ties-to-even;
- a finite rounding overflow saturates to signed 448 and sets the saturation flag.

The saturation flag is counted and returned in tile status. A manifest may promote
any saturation to poison for numerical qualification. No stochastic rounding,
history-dependent scaling, or data-dependent reduction reordering is permitted.

## NUM-4 Arithmetic and rounding

### NUM-4.1 Multiply and accumulate

E2M1/FP8 values and E8M0 scales are decoded exactly as powers-of-two times small
integer significands. Each product is mathematically exact before addition to an
IEEE binary32 accumulator. The accumulator operation has fused-product semantics
with one round-to-nearest-ties-to-even binary32 rounding at each logical add in
increasing reduction-index order.

Weights/activations outside the current block do not influence scale or sum.
Padding lanes are exact positive zero and excluded from saturation/exception
counters. The initial accumulator is positive zero. Subnormal binary32 results are
preserved in the architectural reference; an implementation that flushes them must
define and qualify a different numeric profile.

### NUM-4.2 Conversion to BF16

After the complete specified reduction and vector operation, finite binary32 is
converted to BF16 with round-to-nearest ties-to-even. A finite overflow saturates
to signed BF16 maximum finite (`0x7f7f`/`0xff7f`) and sets saturation status. A NaN
or infinity produced internally is a numeric exception and poisons rather than
being silently emitted. Underflow follows IEEE gradual underflow and may produce
BF16 subnormal or signed zero; output zero is canonicalized positive.

### NUM-4.3 Integer DV mode

`INT_DV` interprets activation and weight fields as two's-complement signed values
of configured widths. Multiplication produces exactly `ACT_W + WEIGHT_W` signed
bits. A widened internal accumulator shall hold the exact sum for the configured
lane/expert/word bound; elaboration rejects an insufficient width. Architectural
`ACC_W` output saturates symmetrically to its signed minimum/maximum and sets
saturation status.

This mode exercises masks, ROM addressing, pipelines, reductions, repair, RAS, and
formal properties cheaply. Its throughput, area, correctness, and coverage do not
close `DSV4_MXFP4`, `FP8_DENSE`, or model quality.

## NUM-5 Exceptional values and errors

### NUM-5.1 Classification

The following poison the whole homogeneous command batch:

- BF16 NaN or infinity at a checked service input;
- FP8 NaN weight/activation;
- E8M0 `0xff` or an unrepresentable activation scale;
- malformed block/tile length, nonzero padding, or inconsistent scale count;
- ROM/scale CRC error or uncorrectable SRAM/HBM data error;
- binary32 NaN/infinity during accumulation/vector service;
- unsupported numeric profile or manifest/profile mismatch.

Finite quantization/output saturation is not automatically poison but is sticky,
counted, and visible; numerical qualification may set a manifest `saturation_fatal`
policy. Corrected ECC does not change numeric bits after correction and follows the
command's `ALLOW_CORRECTED` policy.

### NUM-5.2 Poisoned calculation

After poison, an implementation may gate arithmetic and output positive zero data,
but valid/tag/sequence/credit/drain behavior continues. Poison can only transition
from zero to one within a transaction. No poisoned partial may be committed or
mixed into an unpoisoned transaction.

## NUM-6 Reduction and determinism

### NUM-6.1 Canonical tree

Lane, expert, tile, reticle, and stage partials use the same canonical balanced
binary tree. At level zero, ordered source IDs `(0,1)`, `(2,3)`, and so forth are
added left operand first. At each next level, adjacent prior results are paired in
ascending range order. A missing source in a non-power-of-two final group is exact
positive zero. Each binary32 addition rounds once under NUM-4.1.

For routed expert-output reduction, duplicate routed expert IDs are coalesced so
an expert executes once without discarding any repeated slot contribution.
Selected distinct experts contribute in ascending logical expert ID, not router
arrival order. The compiler maps physical repaired sources back to logical source
IDs before the canonical tree. The earlier router-weight denominator is the
source-slot-axis reduction defined separately by NUM-6.4.

### NUM-6.2 Timing independence

Stalls, HBM response interleaving across tags, static-route physical arrival time,
tile quarantine/remap, packet retry, and legal clock throttle may change completion
time only. Reduction endpoints hold early partials until their canonical partner
and never substitute physical arrival order. Identical legal input and configuration
therefore produce identical bits.

### NUM-6.3 Deterministic selection

Router top-k comparisons consume IEEE binary32 scores. Learned-index top-k
comparisons consume BF16 scores, matching the pinned BF16 Q/K einsum, head
weighting, head reduction, and causal-mask path. Larger values sort first. Exact
score ties sort by ascending logical candidate index; physical lane, arrival
order, and backend-specific sort behavior cannot break a tie. NaN scores poison.
Router and learned-index source scores must be finite; BF16 negative infinity is
introduced only as the causal invalid-position sentinel.

For biased expert routing, each finite original score and its FP32 selection bias
are added with one round-to-nearest-ties-to-even binary32 rounding before top-k.
The selected routing weight is still gathered from the original unbiased score.
For compressed-index prefill, incomplete groups are replaced by negative infinity
before top-k and any selected invalid slot becomes `-1`; valid compressed indices
then receive the manifest window offset. Decode selects from all complete cached
groups.

This explicit tie rule is a target adaptation, not a claim about incidental CUDA
ordering. The pinned release requires `torch>=2.10.0`, and the official PyTorch
2.10 `torch.topk` contract states that indices of tied elements are not guaranteed
stable. A deterministic accelerator therefore cannot inherit that unspecified
behavior.

### NUM-6.4 Routed-weight normalization

`ROUTER_WEIGHT_NORMALIZE` gathers original unbiased IEEE binary32 scores in the
selected slot order. Duplicate expert IDs remain duplicate source slots at this
boundary, matching `Gate.forward`; later execution may coalesce an expert only if
it preserves the combined contribution of every slot. All source scores are
finite and nonnegative. The manifest route scale is finite and greater than zero.

The denominator reduces the selected slot axis with the NUM-6.1 canonical
balanced tree, preserving slot order. A zero or nonfinite denominator poisons.
Each gathered score is divided by that binary32 denominator with one
round-to-nearest-ties-to-even binary32 rounding, then multiplied by the binary32
route scale with one further rounding. There is no fused divide-scale operation
and no final renormalization.

The pinned source spells this as `weights.sum(dim=-1)`, in-place division, and
in-place multiplication, but does not specify one cross-backend reduction tree.
The canonical tree is therefore an explicit deterministic target adaptation; it
does not claim bit identity with every incidental PyTorch CPU or CUDA reduction.

### NUM-6.5 Target-hidden capture

`TARGET_HIDDEN_CAPTURE` consumes a rectangular finite-BF16 tensor in
`[batch, sequence, hc_mult, width]` order and emits
`[batch, sequence, width]`. The source HC dimension must equal the manifest
`hc_mult`; the pinned Flash and Pro value is four. Each BF16 source encoding is
widened exactly to binary32 by appending sixteen zero low bits. NaN or infinity
input poisons.

For each output element, source HC slots reduce in increasing stream order with
the NUM-6.1 canonical balanced binary32 tree. The resulting binary32 sum is
divided by the binary32 encoding of `hc_mult` with one round-to-nearest
ties-to-even operation, then converted once to BF16 under NUM-4.2. Intermediate
binary32 overflow poisons and output zero is canonical positive zero.

The pinned source spells this as `h.mean(dim=2)` and returns BF16 on the audited
CPU/CUDA paths, but does not specify one cross-backend reduction tree. This
canonical source-axis tree is an explicit deterministic target adaptation. It
does not claim that every PyTorch backend or input class implements the same
intermediate overflow behavior.

### NUM-6.6 Routed-expert dispatch

`EXPERT_DISPATCH` flattens the BF16 hidden tensor's batch and sequence axes in
row-major order, matching the pinned `x.view(-1, dim)`. Its route-index and
binary32 route-weight matrices have one row per flattened token and exactly the
manifest `top_k` columns. Expert indices must lie in the manifest expert range;
hidden payloads and route weights must be finite, and route weights must be
nonnegative.

Nonempty dispatch groups appear in ascending logical expert ID. Within one
expert, assignments appear in ascending flattened token index and then
ascending selected-slot index, matching the logical result of the source's
expert loop and `torch.where(indices == i)`. Each assignment carries the
unchanged BF16 hidden row and binary32 route-weight encoding. Duplicate expert
IDs within one token remain separate selected-slot assignments. A later
implementation may execute their identical expert input once only if it retains
and applies every route-weight contribution under the NUM-6.1 reduction rule.

Dispatch performs no arithmetic. Physical rank ownership, repaired placement,
arrival order, and queue timing may filter or delay groups but must not alter
this global logical order or payload mapping.

### NUM-6.7 Qwen causal GQA and softmax

`qwen3_gqa_fp32_softmax_bf16_v1` consumes BF16 Q in
`[sequence,32,128]` order and transaction-private BF16 K/V in
`[sequence,8,128]` order. Query heads `4*h` through `4*h+3` select KV head
`h`, matching the source `repeat_kv` mapping. The committed prefix is followed
by the active request's prepared append. Query position `i` may observe the
complete committed prefix and prepared positions through `i`; later prepared
positions are causal-mask targets.

For every query/key pair, BF16 factors widen exactly to binary32. Products and
accumulator additions execute in increasing head-dimension order under
NUM-4.1. The completed dot converts to BF16 under NUM-4.2. It is then multiplied
by BF16 `0x3db5`, the Qwen `128**-0.5` scalar after source-dtype promotion, and
converted again to BF16. An allowed mask element is positive zero. A disallowed
element is finite BF16 minimum `0xff7f`; mask addition widens both operands,
performs one binary32 addition, and converts once to BF16.

Softmax widens the masked BF16 scores to binary32. It selects the finite maximum,
subtracts that maximum from each element with one binary32 rounding, and applies
the correctly rounded mathematical exponential to binary32. A shifted input at
or below -104 produces positive zero, which is its correctly rounded binary32
result. Exponentials reduce as follows:

- rows shorter than eight reduce sequentially in increasing key index;
- other rows accumulate increasing key indices into eight lanes;
- tail indices update the corresponding low lanes; and
- lanes combine as `(0+4, 1+5, 2+6, 3+7)`, then adjacent pairs, with one
  binary32 rounding at every addition.

One binary32 division computes the reciprocal denominator. Each exponential is
multiplied by that reciprocal with one binary32 rounding and converted to BF16.
The probability-by-V dot then executes in increasing key index under NUM-4.1
and converts once to BF16. The output layout is `[sequence,32,128]`; flattening
the final two dimensions to 4,096 elements is a separate layout operation.

NaN or infinity input, intermediate binary32 overflow, a nonpositive softmax
denominator, or any illegal shape poisons the transaction. The maximum element
guarantees an exact exponential of one, so a zero denominator cannot occur for
a legal nonempty row. Saturating BF16 conversions set their operation-specific
sticky count. Output zero is canonical positive zero.

The pinned source fixes GQA grouping, score scaling, causal masking, FP32
softmax, BF16 probability conversion, and BF16 value aggregation, but `matmul`
and reduction primitives do not promise one bit pattern across every PyTorch
backend and input. Increasing-index dots and the eight-lane sum are deterministic
target adaptations. Authentic-checkpoint known answers and decoding gates, not
incidental synthetic backend differences, qualify the profile.

### NUM-6.8 Transactional KV publication

`bf16_byte_preserving_state_v1` stores K and V without arithmetic conversion.
One resource snapshot has a 64-bit generation, a committed contiguous length,
and a fixed capacity. Prepare requires an exact expected-generation match and a
nonempty append beginning at the committed length; overwrite, holes, and
capacity overflow poison. Prepared bytes remain private to the request
transaction. Its attention operations read the committed prefix plus only that
transaction's append.

Commit first validates every resource in the request group. All entries must
have distinct resource IDs, the same nonzero transaction ID, matching base
generations, and legal appends. It then atomically publishes every append and
increments each generation by exactly one. No resource may become visible when
any validation, arithmetic, memory, or completion dependency fails. Abort and
malformed or incomplete execution discard all prepared records and preserve the
prior committed payload, length, and generation bit-for-bit. Reusing a prepared
record after commit is stale and fails closed.

### NUM-6.9 Qwen BF16 residual and SiLU-gating boundaries

`bf16_add_rne_v1` consumes two equal-shape finite-BF16 tensors. Each operand
widens exactly to binary32, one binary32 addition rounds to nearest ties to even,
and the result converts once to BF16 under NUM-4.2. There is no fused residual
operation, hidden FP32 residual state, or reassociation across elements. The two
Qwen decoder residual sites use this same contract.

`qwen3_silu_mul_bf16_v1` consumes equal-shape finite-BF16 gate and up tensors.
For gate value `x`, sigmoid is defined with a stable sign-selected binary32
subgraph:

```text
x >= 0: e = exp(-x); sigmoid = 1 / (1 + e)
x <  0: e = exp( x); sigmoid = e / (1 + e)
```

The nonpositive exponential is correctly rounded to binary32 as in NUM-6.7.
The denominator addition and division each round once to binary32. The
binary32 product `x * sigmoid` rounds once and then converts to BF16 under
NUM-4.2. This materialized BF16 SiLU activation is multiplied by the BF16 up
value with one binary32 rounding and converted once more to BF16. Thus each
element accounts for one exponential, one sigmoid-denominator addition, one
division, two multiplications, and two BF16 conversions. An optimized engine may
replace the internal sigmoid computation only when exhaustive finite-BF16
differential evidence proves the same materialized activation and final output.

Nonfinite input or binary32 overflow poisons. Each finite BF16 conversion has
its own sticky saturation count. Input negative zero is accepted; every output
zero is canonical positive zero. The intermediate BF16 boundary follows the
pinned source's BF16 `SiLU` tensor followed by its separate BF16 multiplication,
rather than treating the whole expression as one unrounded host operation.

## NUM-7 Speculative decoding

### NUM-7.1 Candidate dimension

Candidate positions are ordered from zero. Target verification computes each
candidate with the same formats and per-position state snapshot. Shared weight
traversal must not change per-candidate dot-product order. Acceptance returns the
longest valid prefix defined by the external algorithm plus fallback semantics;
hardware does not inject a statistical acceptance model.

Prepared KV/state for candidates is committed only for the accepted architectural
positions and only after the whole command passes integrity. Rejected/uncommitted
candidate state is discarded by generation. Draft arithmetic, if implemented,
uses separately manifest-declared numeric tensors and status.

## NUM-8 Qualification boundary

### NUM-8.1 Required evidence

Target numerical closure requires:

- exhaustive decode tests for every E2M1 and E8M0 encoding and every FP8 class;
- boundary/known-answer tests for BF16 conversion and scale selection;
- differential random matrix blocks against an independently implemented reference;
- exact tensor-layout and scale-orientation tests from pinned checkpoint metadata;
- layer/operator comparisons against the public model implementation;
- end-to-end logits, acceptance, and task-quality qualification on representative
  workloads, including saturation and long-context cases.

The first five are possible in public infrastructure once payload subsets are
obtained. Full model quality and production kernel equivalence may require external
compute/traces. Until target-format RTL and these tests pass, analytical operation
counts and `INT_DV` behavior are not numerical implementation evidence.
