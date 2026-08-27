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
bias 7, subnormals enabled, no infinity, and the standard E4M3FN NaN encodings.
Finite maximum magnitude is 448. NaN weight encodings poison the transaction.
Negative zero is canonicalized to positive zero.

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

Duplicate routed expert IDs are removed before arithmetic, so an expert contributes
once. Selected distinct experts contribute in ascending logical expert ID, not
router arrival order. The compiler maps physical repaired sources back to logical
source IDs before the canonical tree.

### NUM-6.2 Timing independence

Stalls, HBM response interleaving across tags, static-route physical arrival time,
tile quarantine/remap, packet retry, and legal clock throttle may change completion
time only. Reduction endpoints hold early partials until their canonical partner
and never substitute physical arrival order. Identical legal input and configuration
therefore produce identical bits.

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
