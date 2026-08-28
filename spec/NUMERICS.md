# Numerical-format and determinism specification

**Document:** SPEC-NUM 1.0

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

Conversion from an exact finite value to E2M1 uses round-to-nearest,
ties-to-even. At every midpoint, including 0.25 between zero and 0.5, the
endpoint whose retained encoding/significand least-significant bit is zero is
selected. Magnitude above six saturates to signed six and sets finite
saturation. Any result that rounds to zero is canonical positive zero.

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

### NUM-3.4 Indexer FP4 in-place QDQ

`FP4_QDQ` is the distinct activation-simulation path used after the normalized
Hadamard rotations of the index query and compressed index KV. It consumes a
finite-BF16 tensor, makes the last dimension contiguous, flattens all leading
dimensions in row-major order, and partitions each row into independent blocks
of exactly 32 values. A last dimension not divisible by 32 is illegal.

For one block, values first widen exactly from BF16 to binary32 and signed zero
canonicalizes positive. Let `a` be their maximum absolute value and define:

```text
a_floor = max(a, 6 * 2^-126)
r       = binary32_RNE(a_floor * binary32_RNE(1/6))
e       = ceil(log2(r))
s       = 2^e
```

The source kernel implements `e` by inspecting the binary32 exponent and adding
one iff the mantissa is nonzero, then implements `s` by constructing the
binary32 exponent bits. For the complete finite-BF16 domain, the resulting
scale exponent is in `[-126, 126]`, so its diagnostic/stored E8M0 code is
`e + 127` in `0x01..0xfd`. In particular, an all-zero block selects `2^-126`
(`0x01`), not the ordinary activation-microscaling all-zero scale `0x7f`.

For each element, the operation is ordered as follows:

1. divide the widened BF16 value by `s` with binary32 RNE;
2. clamp the binary32 quotient to `[-6, 6]`;
3. convert to E2M1 under the NUM-2.1 RNE rule;
4. widen E2M1 exactly to binary32 and multiply by `s` with binary32 RNE; and
5. convert the result to BF16 under NUM-4.2.

The architectural output is the BF16 tensor with its original shape. E2M1 and
E8M0 codes are exposed by the independent reference for checking even though
the pinned `inplace=True` wrapper returns only the overwritten BF16 tensor.
Nonfinite BF16 input, an unrepresentable scale, or intermediate binary32
overflow poisons. The clamp makes legal E2M1 finite saturation impossible.
This fail-closed overflow behavior and positive-zero canonicalization are
governed target rules; they do not silently commit incidental infinity or
negative-zero behavior from the development CUDA kernel.

### NUM-3.5 KV FP8 in-place QDQ

`FP8_QDQ` is the distinct activation-simulation boundary applied to attention KV
after normalization and RoPE. The pinned Flash and Pro calls pass only
`kv[..., :-64]` to `act_quant(..., 64, "ue8m0", float8_e8m0fnu, True)`.
Consequently, each 512-value KV row has an untouched 64-value BF16 RoPE suffix
and a 448-value non-RoPE prefix divided into seven independent blocks of exactly
64 values. Graph nodes and deployment manifests shall carry all of these widths;
a profile that changes them requires separate qualification.

For one block, values first widen exactly from BF16 to binary32 and signed zero
canonicalizes positive. Let `a` be their maximum absolute value. The official
kernel's `round_scale=True` path is ordered as follows:

```text
a_floor = max(a, binary32(1e-4))
r       = binary32_RNE(a_floor * binary32_RNE(1/448))
e       = ceil(log2(r))
s       = 2^e
```

The exact binary32 floor is `0x38d1b717` and the exact rounded reciprocal is
`0x3b124925`. As in NUM-3.4, the source obtains `e` by inspecting the binary32
exponent and adding one iff the mantissa is nonzero, then constructs `s` directly
from exponent bits. Across the finite-BF16 input domain the selected exponent is
in `[-22, 120]`, represented by E8M0 codes `0x69..0xf7`. An all-zero block
therefore selects `2^-22` (`0x69`), not scale one.

For each element, the operation is ordered as follows:

1. divide the widened BF16 value by `s` with binary32 RNE;
2. clamp the binary32 quotient to `[-448, 448]`;
3. convert to finite-only E4M3FN under NUM-3.1 RNE;
4. widen E4M3FN exactly to binary32 and multiply by `s` with binary32 RNE; and
5. convert the result to BF16 under NUM-4.2.

The architectural result replaces only the 448-value prefix; the RoPE suffix is
bit-preserving. The independent reference additionally exposes the seven E8M0
scale bytes and internal E4M3FN codes for checking even though the pinned
`inplace=True` wrapper returns only the overwritten BF16 tensor. Nonfinite BF16
input, an unrepresentable scale, E4M3FN NaN, or intermediate binary32 overflow
poisons. The clamp makes legal E4M3FN finite saturation impossible. Positive-zero
canonicalization and fail-closed overflow are governed target adaptations rather
than claims that incidental CUDA infinity or signed-zero behavior may commit.

### NUM-3.6 Indexer Hadamard rotation

`HADAMARD_ROTATE` is the width-128 normalized Sylvester Hadamard transform
applied to index queries and compressed index KV immediately before NUM-3.4.
The pinned model requires BF16 input and calls the unversioned
`fast_hadamard_transform` dependency with `scale=128**-0.5`. Because the release
does not pin one dependency version or backend, OpenTallas freezes the
documented matrix and the public CUDA kernel's operation order as a governed
target rule.

Each BF16 input widens exactly to binary32 and signed zero canonicalizes
positive. Seven butterfly stages execute in ascending strides
`1, 2, 4, 8, 16, 32, 64`. For every pair `(a, b)` in a stage, the lower output
is `binary32_RNE(a+b)` and the upper output is `binary32_RNE(a-b)`. Both use the
pre-stage values; no in-place dependency is permitted within a pair. After all
stages, each element is multiplied once by binary32 `0x3db504f3`, the
binary32-rounded value of the source's Python `128**-0.5`, and converted once
to BF16 under NUM-4.2.

The target preserves binary32 subnormals. This intentionally differs from the
observed FTZ edge behavior of a public v1.1.0 development build compiled with
`--use_fast_math`; the tested ordinary finite vectors match that implementation
bit for bit.
Nonfinite BF16 input, intermediate binary32 overflow, or output-conversion
exception poisons. Widths other than 128 require a separate profile rather than
implicit padding or a different butterfly schedule.

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

### NUM-6.7 HC post-mixing

`HC_POST` consumes a finite-BF16 branch tensor in
`[batch, sequence, width]`, a finite-BF16 residual tensor in
`[batch, sequence, source_hc, width]`, finite binary32 post coefficients in
`[batch, sequence, destination_hc]`, and finite binary32 combination
coefficients in `[batch, sequence, source_hc, destination_hc]`. Both HC axes
must equal manifest `hc_mult`; the pinned Flash and Pro value is four.

For destination stream `j` and hidden column `d`, the branch contribution is
`post[j] * branch[d]`. Residual source `i` contributes
`comb[i][j] * residual[i][d]`. BF16 operands widen exactly and each product
rounds once to binary32. Residual products reduce by increasing source HC index
with the NUM-6.1 canonical balanced tree. The branch product is then added to
the residual sum with one binary32 rounding, followed by one NUM-4.2 BF16
conversion. Intermediate binary32 overflow or nonfinite input poisons. Finite
BF16 saturation is sticky and counted; output zero is canonical positive zero.

The pinned source expresses the residual term as `torch.sum(..., dim=2)`. A
bounded development audit found the installed PyTorch CPU and CUDA paths agreed
with each other but used a left-associated four-term source reduction, which can
differ from the NUM-6.1 tree after BF16 conversion. The target tree is therefore
an explicit deterministic adaptation. The reference tests retain a concrete
case producing target `0xbbd2` versus sequential-source `0xbbd3`.

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
