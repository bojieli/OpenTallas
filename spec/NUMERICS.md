# Numerical-format and determinism specification

**Document:** SPEC-NUM 1.1

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
converted from BF16 to E4M3FN plus one E8M0 scale. The released dense and routed
matrix kernels use 128-value activation blocks. Routed MXFP4 weights retain a
distinct E8M0 scale per 32 reduction values, so one activation scale is reused
across four consecutive routed weight blocks. Another activation or weight block
dimension requires a separately qualified manifest profile.

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

Where an operation explicitly declares direct BF16 arithmetic, its exact finite
result is rounded directly to BF16 under the same rule. It may not first round to
binary32: that double-rounding path can select the wrong BF16 endpoint next to a
BF16 midpoint. The independent reference therefore provides a direct exact-value
BF16 encoder in addition to binary32-to-BF16 conversion.

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

### NUM-4.4 Bias-free BF16 index-head linear

`BF16_LINEAR` is the distinct index-head weight projection at every ratio-four
main-model layer. The qualified Flash graph contains 21 sites, all with logical
shape 4,096 inputs by 64 outputs. The official checkpoint headers contain 21
corresponding `indexer.weights_proj.weight` tensors, each `[64, 4096]` BF16. The
pinned module constructs `ColumnParallelLinear(..., dtype=torch.bfloat16)` and
the generic `linear` dispatcher reaches bias-free `F.linear` because this weight
is neither FP4 nor FP8.

For each logical output and flattened input row, the target:

1. accepts finite BF16 activations and finite BF16 checkpoint weights;
2. decodes each pair at increasing reduction index and forms its exact product;
3. adds that product to a binary32 accumulator initialized to positive zero,
   with one RNE rounding per fused product-add;
4. converts the completed binary32 accumulator once to BF16 under NUM-4.2; and
5. canonicalizes output zero positive and counts finite BF16 saturation.

There is no bias, activation quantization, hidden block scale, or reassociation.
Subnormal BF16 inputs and binary32 accumulators are preserved. Nonfinite input
or intermediate binary32 overflow poisons. The reference accepts general
rectangular matrices so small independent cases remain practical, while the
graph contract qualifies only the source-observed 4,096-to-64 profile.

PyTorch `F.linear` does not make its GEMM reduction tree architectural. A
deterministic development audit used seed `0x424631364c494e45`, PyTorch
2.10.0+cu128, CUDA 12.8, and 16 BF16 input rows by four BF16 weight rows at the
full reduction width 4,096. Native CPU matched all 64 target BF16 outputs.
Native SM120 differed in 27 of 64 outputs under tensor-core tiling; every
difference retained sign and was at most six BF16 encoding steps. These bounded
results motivate an explicit increasing-index target and do not promise native
backend equivalence outside the governed corpus.

### NUM-4.5 Binary32 router-score projection

`ROUTER_SCORE` is the bias-free gate projection at all 43 main blocks and three
DSpark blocks. The qualified graph therefore contains 46 sites, all with 4,096
input columns and 256 expert outputs. Official checkpoint headers independently
contain 46 corresponding `ffn.gate.weight` tensors, each `[256, 4096]` BF16.
The pinned gate calls `linear(x.float(), self.weight.float())`: both architectural
BF16 inputs widen exactly, and `F.linear` returns binary32 scores before the
separate score-function operator.

For each flattened token and logical expert, the target:

1. accepts finite BF16 hidden-state and checkpoint-weight encodings;
2. widens both values exactly and forms an exact product at each increasing K;
3. adds each product to binary32 positive zero with one RNE rounding per fused
   product-add; and
4. returns the completed finite binary32 encoding without a BF16 conversion.

There is no bias, activation quantization, scale, or output saturation. BF16 and
binary32 subnormals are preserved, output zero is canonical positive, and
nonfinite input or intermediate binary32 overflow poisons. The reference accepts
general rectangular matrices for independent testing; the graph qualifies the
source-observed 4,096-to-256 profile.

As with NUM-4.4, native GEMM tiling is not architectural. A deterministic audit
used seed `0x524f555445525343`, PyTorch 2.10.0+cu128, CUDA 12.8, and 16 input
rows by four weight rows at K=4,096. Inputs sampled finite BF16 signs,
significands, and biased exponents 117 through 134. Native CPU differed from the
increasing-K target in 63 of 64 binary32 outputs, by at most 250 encoding steps;
native SM120 differed in 62, by at most 290 steps. No sign changed. These results
are expected reassociation effects after cancellation, not evidence for adopting
either backend tree as the target.

### NUM-4.6 Binary32 DSpark confidence projection

`CONFIDENCE_SCORE` is the single projection after the final five-position
DSpark Markov loop. The official checkpoint header contains exactly one tensor,
`mtp.2.confidence_head.proj.weight`, with shape `[1, 4352]` and BF16 storage.
For each draft position, the pinned source concatenates the 4,096-wide BF16
DSpark hidden row followed by its 256-wide BF16 Markov embedding, converts the
result to binary32, and invokes the bias-free binary32 `Linear` parameter. The
checkpoint loader widens that parameter from its BF16 payload exactly. The one
output remains binary32 after `squeeze(-1)`.

For each batch and draft position, the target therefore:

1. accepts finite BF16 hidden, Markov-embedding, and checkpoint-weight values;
2. orders reduction indices as hidden columns `0..4095`, then Markov columns
   `0..255`;
3. widens each operand exactly, forms its exact product, and adds it to a
   binary32 accumulator initialized to positive zero, with one RNE rounding per
   fused product-add in increasing reduction-index order; and
4. emits the completed finite binary32 encoding without activation, bias,
   scaling, or BF16 output conversion.

BF16 and binary32 subnormals are preserved and output zero canonicalizes
positive. A malformed batch/position/width, any nonfinite input, or intermediate
binary32 overflow poisons. The independent reference accepts smaller nonzero
widths for practical unit cases; only hidden width 4,096, Markov width 256,
block size five, and one output are graph-qualified.

Native `F.linear` is a cross-check rather than the reduction contract. An
official-weight development audit used the tensor payload SHA-256
`15c5d09c7842d0f947ce0afdc154691ead377e6263af71bd2f7cb34bd592f30f`,
seed `0x434f4e464f464649`, PyTorch 2.10.0+cu128, CUDA 12.8, four batches, and all
five draft positions. Inputs sampled finite BF16 signs, significands, and biased
exponents 117 through 134. Native CPU differed from the increasing-K target in
all 20 binary32 outputs by at most 86 same-sign encoding steps; native SM120
differed in 19 of 20 by at most 73 same-sign steps. Hashing each row-major output
as a little-endian binary32 stream gave target, CPU, and SM120 SHA-256 values of
respectively
`cfe942601b45620854e7fadb7c1eb33c171fd0b41484c613265e21b9ef299b67`,
`540eb9d9b0b9e1d2bcce1db72a1feb5ec65b7c782e253f68053c9bf1140cc11c`,
and `5d569fb7829185b013ac13a759beba0ea80a197b5b86d3a44683606f262b53d9`.
These bounded reassociation differences do not make either backend tree
architectural.

### NUM-4.7 Binary32 compressor projections

`COMPRESS_PROJECT` is the paired bias-free projection at every compressed
main-model attention site. The pinned `Compressor.forward` records the input
dtype, widens `x` to binary32, then evaluates `wkv(x)` followed by `wgate(x)`.
Both `Linear` modules have binary32 runtime parameters, but the source states
that their checkpoint tensors are BF16; checkpoint loading therefore widens
every stored weight exactly. Neither output is converted back to BF16 before
the separately specified pooling operation.

The qualified Flash graph and official checkpoint headers contain these exact
profiles. Each site has one `wkv.weight` and one `wgate.weight` tensor.

| Projection scope | Ratio | Sites | Shape of each tensor | Storage |
|---|---:|---:|---:|---:|
| Main overlapping compressor | 4 | 21 | `[1024, 4096]` | BF16 |
| Main non-overlapping compressor | 128 | 20 | `[512, 4096]` | BF16 |
| Indexer overlapping compressor | 4 | 21 | `[256, 4096]` | BF16 |

For every batch, sequence position, and output row, the target:

1. accepts finite BF16 hidden-state and checkpoint-weight encodings;
2. widens each operand exactly and interprets each checkpoint matrix as
   `[output, input]`;
3. forms exact products in increasing input-column order and adds each to a
   binary32 accumulator initialized to positive zero, with one RNE rounding per
   fused product-add;
4. executes the KV and gate projections independently in source order; and
5. emits both completed finite tensors as binary32 without bias, activation
   quantization, scaling, output conversion, or saturation.

BF16 and binary32 subnormals are preserved and output zero canonicalizes
positive. A malformed batch/position/matrix shape, mismatched KV/gate output
count, any nonfinite input, or intermediate binary32 overflow poisons. The
independent reference accepts smaller nonzero rectangular profiles for practical
unit cases; only the three 4,096-column profiles above are graph-qualified.
Pooling, positional weights, overlap transformation, compressor mutation,
normalization, rotation, and cache commit remain separate operators.

An actual-weight development audit byte-range fetched the two projection tensors
for layer 2's main and indexer ratio-four compressors and layer 3's main
ratio-128 compressor. The complete payload SHA-256 values were:

- layer 2 main KV/gate:
  `0247c85dc0f6ccd8356b333c691c518eda037e350cac7cb7a6542463e6e86d76` /
  `b2609470385caf2fe20cda729aa8b37cd3d65cdb877ca220d064c677d11c7d78`;
- layer 3 main KV/gate:
  `79cd97ab7621210200ea2b3161878f7e32633dbc3bdf6d27516e6518220b8637` /
  `282fce242df3dd61eceb2ef751130dee076b83b55955849e1670bb53dc6e8883`;
  and
- layer 2 indexer KV/gate:
  `0b000926c809a0b34ff42cc992ca095c7ae079d1d0a45c6fbba3d87b45be1c26` /
  `6e15bcf0cbcea64e0a6490457b2588b31c5eae668e4aac76912aa7036db38eaa`.

With seed `0x434f4d504f464649`, two batches, four positions, and the first
four output rows of each tensor, the audit emitted 192 binary32 values in
profile order main-ratio-4, main-ratio-128, index-ratio-4, with KV before gate.
PyTorch 2.10.0+cu128 CPU differed from the increasing-K target in 187 values,
by at most 2,936 same-sign encoding steps; CUDA 12.8 SM120 differed in 188, by
at most 1,272 same-sign steps. Hashing the concatenated little-endian binary32
streams gave target, CPU, and SM120 SHA-256 values of respectively
`33a79e6826ab9b34b471a1ff1b0287a45edea04e2ffcfaa6ba1d084b80513999`,
`261432c24e3f753626874f45f8a83191dd05f1575e8aea3074de6005a331f530`,
and `3402752582908f1e68810844636e7d897447af6cb6a05e74101121b33e1ce4a0`.
These expected reassociation differences make neither native backend's reduction
tree architectural.

### NUM-4.8 BF16 learned sparse-index score

`INDEX_SCORE` is the learned score calculation at the 21 ratio-four indexer
sites. The pinned `Indexer.forward` first obtains one BF16 head weight per
logical head from the NUM-4.4 projection, multiplies it by
`head_dim**-0.5 * n_heads**-0.5`, contracts the FP4-QDQ BF16 query and
compressed-KV tensors with `einsum("bshd,btd->bsht")`, applies in-place ReLU,
multiplies by the scaled head weights, and sums the head axis. A
tensor-parallel execution all-reduces this score after the local head sum.
Causal masking and top-k selection are the separate `INDEX_TOPK` operator.

The qualified Flash profile is fixed as follows:

| Quantity | Qualified value |
|---|---:|
| Sites | 21 |
| Compression ratio | 4 |
| Logical heads | 64 |
| Head dimension | 128 |
| Query / compressed-KV input | BF16 after FP4 QDQ |
| Head-weight input | BF16 from NUM-4.4 |
| Scale | binary32 `0x3c3504f3` |
| Score output | BF16 |

For each batch, query position, candidate, and logical head, the target:

1. accepts finite BF16 query, compressed-KV, and head-weight encodings;
2. forms exact query/KV products in increasing head-dimension order, adds each
   to binary32 positive zero with one RNE rounding per fused product-add, and
   converts the completed dot product once to BF16 under NUM-4.2;
3. maps every nonpositive BF16 dot product, including negative zero, to BF16
   positive zero;
4. multiplies the BF16 head weight directly by binary32 `0x3c3504f3` and rounds
   the exact product once to BF16, without first rounding the scale to BF16;
5. multiplies the BF16 ReLU result by that scaled BF16 weight and rounds the
   exact product once to BF16;
6. widens the head contributions exactly to binary32 and reduces logical heads
   in ascending order with the NUM-6.1 balanced tree; valid contiguous
   tensor-parallel partitions must compose into this same global logical tree;
   and
7. converts the completed finite sum once to BF16 under NUM-4.2.

BF16 and binary32 subnormals are preserved. Finite BF16 saturation at the QK,
scaled-weight, weighted-score, or final-output boundary is counted separately;
nonfinite input or binary32 overflow poisons. A zero-length candidate axis is
legal for a short prefill span and produces an empty score row. The independent
reference accepts smaller nonzero head counts and dimensions for practical
unit cases; only the 64-by-128 profile above is graph-qualified.

The binary32 scale boundary is observable: BF16 head weight `0x0246` becomes
`0x0012` when multiplied directly by `0x3c3504f3`, whereas incorrectly
prerounding the scale to BF16 `0x3c35` produces `0x0011`. A governed development
differential used seed `0x494e44584e415449`, PyTorch 2.10.0+cu128, CUDA 12.8,
two batches, two query positions, seven candidates, and the full 64-by-128
profile. After target positive-zero canonicalization, all 28 final BF16 outputs
matched on both CPU and native SM120: each backend had zero differing outputs
and a maximum difference of zero BF16 encoding steps. This bounded synthetic
observation does not establish checkpoint, layer, service-engine, or
end-to-end-model equivalence.

### NUM-4.9 Routed MXFP4 and shared FP8 SwiGLU

`MXFP4_SWIGLU` and `FP8_SWIGLU` are the routed and shared expert paths at all
43 main layers and three DSpark layers. The pinned `Expert.forward` preserves
its BF16 input dtype, executes bias-free `w1` and `w3`, widens both BF16 outputs
exactly to binary32, applies the configured limit, evaluates SiLU and the up
product in binary32, optionally applies one routed binary32 weight, converts
the complete intermediate once to BF16, and executes bias-free `w2`. Routed
experts store all three matrices as packed E2M1 plus per-32 E8M0 scales; the
shared expert stores all three as E4M3FN plus 128-by-128 E8M0 tiles.

Every learned projection first applies NUM-3.3 to nonoverlapping 128-value BF16
activation blocks. For routed projections, one activation scale is reused for
four consecutive 32-value MXFP4 weight blocks. Each block executes the NUM-4.1
increasing-index dot, and its completed binary32 partial is added to a binary32
accumulator in increasing 32-value block order with one RNE addition per block,
matching the released kernel's `C_local_accum +=` source order. The completed
finite accumulator converts once to BF16. Shared projections use the already
qualified `FP8_LINEAR` rule unchanged: ordered 128-value block dots, NUM-6.1
balanced cross-block reduction, and one BF16 conversion. Thus all three learned
projection outputs are architectural BF16 even though the following vector
section operates in binary32.

For every intermediate column, the target executes:

1. widen the BF16 gate and up values exactly to binary32;
2. clamp up to the closed interval `[-10,10]`, but clamp gate only above at
   binary32 `10` (`0x41200000`); a gate below `-10` is deliberately retained;
3. correctly round the mathematical logistic function directly to binary32;
4. multiply gate by that sigmoid with one binary32 RNE rounding (SiLU);
5. multiply SiLU by clamped up with one binary32 RNE rounding;
6. at routed sites only, multiply by the finite nonnegative binary32 route
   weight with one binary32 RNE rounding; and
7. convert that completed finite value once to BF16 under NUM-4.2 before `w2`.

The logistic rule reuses the exact rational-enclosure implementation qualified
for NUM-6.10; it does not expose a separately rounded exponential, add, or
divide. Source and TileLang do not promise a common tensor-core reduction tree
or SiLU approximation across backends, so these are deterministic OpenTallas
target boundaries rather than claims of bit identity with every CUDA launch.
Signed output zero canonicalizes positive. Any malformed shape or scale layout,
nonfinite BF16/binary32 input, E4M3FN NaN, reserved E8M0 scale, or intermediate
binary32 overflow poisons the complete transaction. Finite BF16 saturation is
sticky and counted. All weight, scale, input, and route resources validate before
any result is returned; one immutable result constitutes one logical commit.

The official shape is `4096 -> 2048 -> 4096`, with a limit of 10, six routed
slots per token, and one shared expert. The independent reference also admits
bounded complete matrices and explicit selected-row projection audits so exact
unit and checkpoint-payload evidence remains tractable. A selected-row audit is
not a complete expert invocation. Logical payload/read/work counters do not
specify ROM transactions, cache reuse, cycles, achieved bandwidth, throughput,
energy, area, PPA, or a wafer/GPU advantage.

### NUM-4.10 Shared BF16 vocabulary head

`LM_HEAD` is the one untied vocabulary projection shared by the main model and
DSpark. It is not an MXFP4 routed matrix or an FP8 dense/shared matrix. The
official checkpoint stores `head.weight` as BF16 with shape `[129280,4096]`,
for exactly 1,059,061,760 bytes. The pinned `ParallelHead` creates a binary32
runtime parameter, loads the BF16 payload into it by exact widening, widens its
BF16 hidden input with `x.float()`, and evaluates a bias-free linear projection.
There is no activation microscaling, weight scale, bias, output conversion, or
output saturation at this boundary.

For every selected source row and global vocabulary row, the target:

1. accepts finite BF16 hidden and checkpoint-weight encodings;
2. widens both operands exactly to binary32;
3. starts a binary32 positive-zero accumulator and traverses hidden columns
   `0..4095` in increasing order;
4. forms the exact BF16 product at each column and performs one binary32 RNE
   fused product-add, as in NUM-4.1; and
5. returns the completed finite binary32 logit without BF16 conversion.

BF16 and binary32 subnormals are preserved. Output zero canonicalizes positive.
A malformed batch, sequence, width, vocabulary, or partition shape; a nonfinite
BF16 operand; or binary32 accumulation overflow poisons the complete
transaction. The reference admits smaller nonzero dimensions for exhaustive
unit cases, but only hidden width 4,096 and vocabulary size 129,280 are graph
qualified.

The main-model site calls `ParallelHead` with `full_logits=False`. It validates
the complete finite BF16 input tensor but projects only source position `S-1`,
returning binary32 shape `[B,129280]`. The DSpark site invokes the same head and
same weight with `full_logits=True`; its qualified block size is five and it
projects all five source positions, returning `[B,5,129280]`. Final RMS
normalization and HC-head reduction are upstream operators. Sampling, Markov
bias addition, and the Markov autoregressive loop are downstream operators and
must not be folded into this boundary.

Tensor parallelism partitions only the vocabulary axis. For world size `W` in
`{1,2,4,8}`, rank `r` owns the equal contiguous global rows
`[r*129280/W,(r+1)*129280/W)`. Each rank produces its local binary32 logits;
the source all-gathers those arrays and concatenates them in increasing rank
order. This collective performs no numerical cross-rank reduction. Therefore a
conforming physical collective must reproduce global vocabulary order but may
choose any implementation that leaves every binary32 code unchanged.

For batch `B`, source sequence length `S`, projected-position count `P` (`1`
for main, `S=5` for DSpark), evaluated vocabulary rows `V`, and hidden width
`K`, the semantic counters are:

```text
source hidden BF16 values validated = B * S * K
selected hidden BF16 values read    = B * P * K
selected weight BF16 values read    = V * K
input binary32 widens               = B * P * K
weight binary32 widens              = V * K
exact product-accumulates           = B * P * V * K
binary32 accumulation roundings     = B * P * V * K
binary32 logits produced/gathered   = B * P * V
```

These values describe logical semantic coverage. In particular, the weight
count does not assert that a physical ROM, SRAM, cache, or HBM reads each value
once, and the gathered-logit count is not a link transfer measurement. Physical
placement, reuse, transactions, flits, cycles, latency, bandwidth, inference
bytes/s, throughput, energy, area, PPA, and a GPU comparison require generated
images, schedules, execution counters, and implementation characterization.

The released `F.linear` does not define one CUDA GEMM association order.
OpenTallas therefore freezes increasing hidden-index accumulation as a
deterministic target adaptation; this is not a claim of bit identity with an
arbitrary PyTorch/CUDA kernel. Qualification evidence separately covers a
complete small main/DSpark operator, the complete official BF16 payload and its
four MP=4 partitions, eight full-width official rows crossing every MP=4
boundary under a deterministic synthetic hidden row, and an independently
implemented selected-row arithmetic lane. It does not provide a
checkpoint-derived hidden activation or a complete 129,280-logit official
numeric execution.

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

### NUM-6.8 Weighted RMS normalization

`RMS_NORM` consumes one or more finite-BF16 rows and one finite-BF16 checkpoint
weight for every column. The qualified Flash graph contains 251 weighted sites:
21 at width 128, 90 at width 512, 46 at width 1,024, and 94 at width 4,096.
This weighted contract is distinct from the separately qualified unweighted
`HEAD_RMS_NORM` contract in NUM-6.9 and does not qualify an RMS operation hidden
inside another composite operator.

Checkpoint normalization weights are stored as BF16. The pinned source loads
them into binary32 parameters; the target therefore widens every BF16 weight
exactly rather than inventing additional parameter precision. Each BF16 input is
likewise widened exactly. For one row, operations occur in this order:

1. square every widened input with one binary32 RNE multiplication;
2. reduce those squares in increasing column order with the NUM-6.1 tree;
3. divide once by the exact binary32 encoding of the qualified width;
4. add once the binary32 encoding `0x358637bd` of the source literal `1e-6`;
5. compute a correctly rounded, ties-to-even binary32 reciprocal square root;
6. multiply each original widened input by that reciprocal RMS with one rounding;
7. multiply by its widened checkpoint weight with one further rounding; and
8. convert once to BF16 under NUM-4.2.

No square-add, divide-add, normalization-weight multiply, or output conversion is
fused across these boundaries. BF16 and binary32 subnormal inputs are preserved
at each conversion boundary and arithmetic follows IEEE binary32 RNE, including
correct underflow when a result rounds to zero. Output zero is canonical positive
zero. Nonfinite input or intermediate binary32 overflow poisons; finite BF16
output saturation remains sticky and counted under NUM-5.1.

The pinned source spells the reduction as `x.square().mean(-1)` and invokes
`torch.rsqrt`; neither expression fixes one cross-backend reduction tree or one
architectural reciprocal-square-root approximation. A deterministic development
audit used seed `0x524d534e41554449`, PyTorch 2.10.0+cu128, CUDA 12.8, and
native SM120 over 16 rows at each qualified width. The explicit target tree
matched all 64 mean-square codes on both CPU and CUDA. The ordinary source
reduction differed in 30/64 CPU and 15/64 CUDA means. Native reciprocal square
root differed from the correctly rounded target in 22/64 CPU and 14/64 CUDA
cases when fed the canonical means, always by one binary32 code in that corpus.
After positive-zero canonicalization, the source expression differed in 22 of
92,160 CPU BF16 outputs and zero CUDA BF16 outputs. These bounded observations
justify keeping the deterministic target rules; they are not a promise of
equivalence for untested inputs, backends, or overflow behavior.

### NUM-6.9 Unweighted query-head RMS normalization

`HEAD_RMS_NORM` consumes one or more finite-BF16 query-head rows of exactly 512
columns and has no checkpoint weight. The qualified Flash graph contains 46
sites: one after query expansion in each of 43 main blocks and three DSpark
blocks. It is not an alias for the binary32 weighted operation in NUM-6.8.

The pinned `fp8_gemm` wrapper returns the process default dtype, which the pinned
model sets to BF16. At this source boundary, native CPU and CUDA checks confirm
that `q.square()`, `.mean()`, addition of the Python literal `1e-6`,
`torch.rsqrt`, and the in-place multiply all return BF16. The source epsilon at
this boundary is therefore BF16 `0x3586`, not binary32 `0x358637bd`.

For one row, the deterministic target executes these boundaries in order:

1. square each original BF16 input and round the exact product directly to BF16;
2. widen each squared BF16 value exactly and reduce the 512 columns with the
   NUM-6.1 balanced binary32 tree;
3. divide once by binary32 512 and convert the binary32 mean once to BF16;
4. add BF16 epsilon `0x3586` and round the exact sum directly to BF16;
5. compute the correctly rounded, ties-to-even BF16 reciprocal square root; and
6. multiply each original BF16 input by that BF16 reciprocal RMS and round the
   exact product directly to BF16.

No square, mean conversion, epsilon add, reciprocal square root, or output
multiply may be fused across these declared BF16 boundaries. Direct BF16
rounding follows NUM-4.2 and must not pass through a binary32 intermediary.
Subnormals are preserved, and output zero is canonical positive zero. Nonfinite
input, binary32 reduction overflow, or finite saturation at a BF16 intermediate
poisons. Finite saturation only at the final BF16 output remains sticky and is
counted under NUM-5.1.

PyTorch does not promise one cross-backend reduction order or correctly rounded
BF16 reciprocal square root. A deterministic development audit used seed
`0x48454144524d534e`, PyTorch 2.10.0+cu128, CUDA 12.8, and native SM120 over 16
width-512 rows. The explicit target tree and the ordinary source mean both
matched all 16 target mean-square codes on CPU and CUDA in this bounded corpus.
Native BF16 reciprocal square root differed from the correctly rounded target
in one CPU row and zero CUDA rows; the CPU result was one BF16 code away. The
complete source expression consequently differed in 427 of 8,192 CPU BF16
outputs and zero CUDA outputs, with every CPU difference an adjacent same-sign
code after positive-zero canonicalization. These observations bound that
development corpus only; the explicit rules above remain the target contract.

### NUM-6.10 Hyper-connection pre-mixing

`HC_PRE` is the composite numeric boundary before each attention and FFN branch.
The source-mapped DeepSeek V4 Flash graph enumerates 92 such sites: two in each
of 43 main blocks and two in each of three DSpark blocks. This section freezes
the deterministic target arithmetic for those sites. It does not qualify
`HC_HEAD`, which has a related but distinct source expression and requires its
own contract.

For positive batch and sequence extents, let `T = batch * sequence`. Every token
is independent; no reduction crosses a batch or sequence axis. The pinned profile
has:

```text
hc_mult = H = 4
width = D = 4096
flattened_width = K = H * D = 16384
mix_fields = M = (2 + H) * H = 24
sinkhorn_iterations = 20
norm_epsilon = binary32 0x358637bd
hc_epsilon = binary32 0x358637bd
```

The two epsilon roles are separately bound manifest and microcode fields even
though this profile gives them the same bits. Silently substituting one field for
the other, or accepting a different encoding, is a profile mismatch.

The inputs are finite BF16 hidden state `x[batch, sequence, H, D]`, finite
binary32 projection `hc_fn[M, K]`, finite binary32 `hc_scale[3]`, and finite
binary32 `hc_base[M]`. The flattening order is exactly
`k = source_stream * D + hidden_column`; projection output row is the outer
dimension of `hc_fn`. The architectural results and retained state are:

```text
branch       BF16 [batch, sequence, D]
post         F32  [batch, sequence, H]
comb         F32  [batch, sequence, H, H]  # [source][destination]
residual     BF16 [batch, sequence, H, D]  # bit-preserving input capture
```

An independent checker shall additionally expose binary32 RMS mean and inverse
in `[batch, sequence]`, the 24 projection accumulators and 24 RMS-scaled mixes in
`[batch, sequence, M]`, and the four `pre` coefficients in
`[batch, sequence, H]`. These are evidence observables, not additional HC_POST
inputs.
`residual` is an architectural pass-through: its BF16 payload is preserved while
signed zero in that payload canonicalizes positive when a later arithmetic
operator consumes it. The arithmetic path below canonicalizes either input-zero
sign positive at its first checked boundary.

In this section, `RN32` means one IEEE binary32 round-to-nearest-ties-to-even
operation with gradual underflow. `CR32(f(...))` means the correctly rounded
binary32 value of the exact real mathematical function, with no visible
intermediate approximation boundary. Ordinary multiply and add expressions are
separate `RN32` operations unless fused-product-add semantics are explicitly
stated.

#### NUM-6.10.1 Internal RMS and projection

For each flattened token row `X[0:K]`, widen finite BF16 exactly to binary32 and
execute:

```text
square[k] = RN32(X[k] * X[k])
square_sum = NUM-6.1-balanced-sum(square[0:K])
mean = RN32(square_sum / binary32(K))
biased_mean = RN32(mean + norm_epsilon)
rms_inverse = CR32(1 / sqrt(biased_mean))
```

The width-16,384 reduction has exactly 14 balanced levels and 16,383 additions.
It is not covered by, or permitted to inherit an implementation from, a weighted
`RMS_NORM` site without separately proving these exact boundaries.

For projection field `q = 0..23`, start with binary32 positive zero and traverse
`k = 0..16383` in increasing order:

```text
acc = +0
acc = RN32(acc + exact(X[k] * hc_fn[q][k]))  # for each increasing k
projection[q] = acc
mix[q] = RN32(projection[q] * rms_inverse)
```

Each projection step has the fused-product semantics of NUM-4.1: the product is
exact and the product-add rounds once. There is no separately rounded product,
TF32 truncation, reassociation, tensor-core-dependent tree, chunk accumulation,
or one-round exact dot product. Multiplication by `rms_inverse` occurs only after
the completed dot product and is a separate binary32 operation.

#### NUM-6.10.2 Field transforms

Fields `0..3` are `pre`, fields `4..7` are `post`, and fields `8..23` are the
row-major combination matrix. For source `i` and destination `j` in `0..3`,
first compute:

```text
pre_z[j] = RN32(RN32(mix[j] * hc_scale[0]) + hc_base[j])
post_z[j] = RN32(RN32(mix[4+j] * hc_scale[1]) + hc_base[4+j])
comb_z[i][j] = RN32(
    RN32(mix[8 + 4*i + j] * hc_scale[2])
    + hc_base[8 + 4*i + j]
)
```

The multiply and add in each affine transform are two rounding boundaries and
must not contract. Define the target logistic primitive as:

```text
SIGMOID32(z) = CR32(1 / (1 + exp(-z)))
pre[j] = RN32(SIGMOID32(pre_z[j]) + hc_epsilon)
post[j] = RN32(binary32(2) * SIGMOID32(post_z[j]))
```

`SIGMOID32` is one correctly rounded mathematical-function boundary. A table,
polynomial, or other implementation is conforming only when its returned code is
identical for every legal binary32 input; an error-bounded but bit-different
approximation requires a separately named numeric profile.

#### NUM-6.10.3 Stable softmax and 20-stage Sinkhorn

The first row-normalization stage is the stabilized softmax. For each source row
`i`, select the maximum finite binary32 value and execute:

```text
delta[i][j] = RN32(comb_z[i][j] - row_max[i])
e[i][j] = CR32(exp(delta[i][j]))
row_sum[i] = NUM-6.1-balanced-sum(e[i][0:4])
comb[i][j] = RN32(RN32(e[i][j] / row_sum[i]) + hc_epsilon)
```

`CR32(exp(...))` is the correctly rounded mathematical exponential. Stabilized
arguments are nonpositive after a successful finite subtraction, so exponential
overflow is impossible. Correct underflow to a binary32 subnormal or positive
zero is legal. At least the maximum element produces exact `exp(0) = 1`, making
the initial row denominator nonzero.

Immediately perform the first column-normalization stage:

```text
col_sum[j] = NUM-6.1-balanced-sum((comb[0][j], ..., comb[3][j]))
col_denom[j] = RN32(col_sum[j] + hc_epsilon)
comb[i][j] = RN32(comb[i][j] / col_denom[j])
```

Then perform exactly 19 serial repetitions of a row stage followed by a column
stage:

```text
row_sum[i] = NUM-6.1-balanced-sum(comb[i][0:4])
row_denom[i] = RN32(row_sum[i] + hc_epsilon)
comb[i][j] = RN32(comb[i][j] / row_denom[i])

col_sum[j] = NUM-6.1-balanced-sum((comb[0][j], ..., comb[3][j]))
col_denom[j] = RN32(col_sum[j] + hc_epsilon)
comb[i][j] = RN32(comb[i][j] / col_denom[j])
```

Consequently, source `sinkhorn_iterations = 20` means exactly 20 row stages and
20 column stages. The stable-softmax division is row stage one; it adds epsilon
after each element division. Row stages 2 through 20 add epsilon once to each
row denominator. All 20 column stages add epsilon once to each column
denominator. An implementation that performs 20 repetitions after the initial
softmax/column pair executes the wrong contract.

Every four-element sum above is the NUM-6.1 specialization
`RN32(RN32(v0+v1) + RN32(v2+v3))`. A left fold, warp-arrival order, or reduction
intrinsic with an unspecified tree is not conforming. Matrix orientation remains
`comb[source][destination]` throughout.

#### NUM-6.10.4 Branch reduction and conversion

For hidden column `d`, multiply the final `pre` coefficient by the corresponding
original widened HC stream and reduce source streams in increasing order:

```text
p0 = RN32(pre[0] * X[0,d])
p1 = RN32(pre[1] * X[1,d])
p2 = RN32(pre[2] * X[2,d])
p3 = RN32(pre[3] * X[3,d])
left = RN32(p0 + p1)
right = RN32(p2 + p3)
y32 = RN32(left + right)
branch[d] = BF16_RNE_SAT(y32)
```

The final conversion follows NUM-4.2. It preserves gradual underflow,
canonicalizes output zero positive, and makes finite BF16 saturation sticky and
countable. The reduction must not become a left fold or `X * sum(pre)`, even at
layer 0 where `HC_EXPAND` initially makes the four streams bit-identical.

#### NUM-6.10.5 Poison and atomic commit

Malformed shapes; nonfinite BF16 `x`; nonfinite binary32 projection, scale, or
base; a profile/epsilon mismatch; binary32 overflow or nonfinite output at an
ordinary arithmetic boundary; or a zero/nonfinite division denominator poisons
the complete homogeneous command under NUM-5. Subnormal BF16 and binary32 values
are preserved; FTZ and DAZ are not allowed. A correctly rounded exponential or
sigmoid result that underflows to positive zero is not poison. Sigmoid rounding
to `1.0` is not saturation. Finite saturation exists only at the final BF16
branch conversion.

Poison is atomic across all `T` rows. No branch, post, combination, residual-state
advance, diagnostic intermediate, downstream RMS/query result, or success counter
may commit from a poisoned command. An implementation may continue protocol
drain behavior as allowed by NUM-5.2, but a valid-looking partial result must not
escape.

#### NUM-6.10.6 Logical counters

For each successfully committed token, the semantic schedule counters are exact:

| Counter identifier | Per-token value |
|---|---:|
| `hc_pre_input_bf16_values` | 16,384 |
| `hc_pre_rms_square_multiplies` | 16,384 |
| `hc_pre_rms_reduction_adds` | 16,383 |
| `hc_pre_rms_divides` | 1 |
| `hc_pre_rms_epsilon_adds` | 1 |
| `hc_pre_rsqrt_evaluations` | 1 |
| `hc_pre_projection_product_accumulates` | 393,216 |
| `hc_pre_projection_rms_multiplies` | 24 |
| `hc_pre_field_affine_multiplies` | 24 |
| `hc_pre_field_affine_adds` | 24 |
| `hc_pre_sigmoid_evaluations` | 8 |
| `hc_pre_coefficient_epsilon_adds` | 4 |
| `hc_pre_post_factor_multiplies` | 4 |
| `hc_pre_softmax_max_comparisons` | 12 |
| `hc_pre_softmax_subtracts` | 16 |
| `hc_pre_exp_evaluations` | 16 |
| `hc_pre_sinkhorn_row_stages` | 20 |
| `hc_pre_sinkhorn_column_stages` | 20 |
| `hc_pre_sinkhorn_row_reduction_adds` | 240 |
| `hc_pre_sinkhorn_column_reduction_adds` | 240 |
| `hc_pre_sinkhorn_divides` | 640 |
| `hc_pre_sinkhorn_epsilon_adds` | 172 |
| `hc_pre_branch_coefficient_multiplies` | 16,384 |
| `hc_pre_branch_reduction_adds` | 12,288 |
| `hc_pre_branch_bf16_conversions` | 4,096 |
| `hc_pre_residual_bf16_values_preserved` | 16,384 |

The command values are these coefficients multiplied by `T`. The
`hc_pre_branch_bf16_saturations` counter is data-dependent in `0..4096*T` and
shall equal the exact number of finite binary32 results clamped by NUM-4.2. One
correctly rounded sigmoid or exponential counts as one logical evaluation
regardless of its physical implementation. These are semantic reconciliation
counters, not physical tensor-core operations, instruction counts, ROM/HBM
traffic, cycles, area, energy, throughput, or PPA evidence.

#### NUM-6.10.7 Conformance anchors and source boundary

The following all-zero anchor has independently reproducible exact results. Set
all BF16 `x` encodings and all `hc_fn`, `hc_scale`, and `hc_base` values to
positive zero. Required binary32 codes are:

```text
RMS mean                         0x00000000
RMS inverse                      0x447a0000
all projection and mix fields    0x00000000
each pre coefficient             0x3f000011
each post coefficient            0x3f800000
each stable-softmax-plus-epsilon  0x3e800022
each final combination element   0x3e7ffff0
```

The branch and residual are all BF16 `0x0000`, and branch saturation count is
zero.

The increasing-index projection rule has a second algebraic anchor. In one
projection row set the first three `(X, hc_fn)` pairs to
`(1,1)`, `(2^-12,2^-12)`, and `(-1,1)`, with every later pair zero. The target
accumulator is binary32 `0x00000000`: adding `2^-24` to `1` is an exact midpoint
that ties to the even encoding `1`, after which adding `-1` gives zero. A dot
product rounded only once at its end would instead retain `2^-24`, code
`0x33800000`. The checker shall expose the projection accumulator so downstream
rounding cannot conceal this distinction.

The pinned source fixes tensor shapes, field splitting, expression order, and the
20-stage loop structure. It does not make bit-exact the `F.linear` reduction,
FMA contraction, RMS reduction, `torch.rsqrt`, TileLang reductions,
`T.sigmoid`/`T.exp`, compiler math mode, or device FTZ behavior. Therefore the
rules in NUM-6.10 are deterministic OpenTallas target adaptations, not a claim of
universal bit identity with PyTorch, TileLang, CUDA, or any particular NVIDIA
GPU. No official-CUDA bit corpus is promoted into this contract. A separately
pinned backend audit may report differences, but those observations neither
change the target nor constitute accelerator conformance.

The reference qualification evidence in
`docs/DEEPSEEK_V4_HC_PRE_EVIDENCE.md` now supplies an independently regenerated
correctly-rounded sigmoid/exponential corpus, a separate Decimal-based service
oracle, asymmetric matrices distinguishing pass 19 from pass 20 and proving
source/destination orientation, balanced-versus-left-fold RMS/softmax/branch
sentinels, poison and atomic-commit mutations, and exact reference/service
comparisons for `T = 1..4` using hash-locked layer-0 attention HC parameters.
The extent corpus deliberately repeats one independently verified official
tokenizer/lookup-derived token so that transaction extent is isolated from value
variation; heterogeneous sparse-value differential corpora are qualified
separately. These results qualify the target reference boundary only. They do
not select backend-dependent bits or establish compiler, service integration,
RTL, timing, PPA, or full-model execution.

### NUM-6.11 Routed-expert and shared-expert reduction

`EXPERT_REDUCE` is the final arithmetic boundary in every MoE block. The
source-mapped Flash graph contains 46 sites: one in each of 43 main blocks and
one in each of three DSpark blocks. The qualified Flash profile has hidden width
4,096, 256 routed experts, top-k six, and one shared expert. Inputs are the
qualified NUM-6.6 dispatch, one finite-BF16 output row for every dispatched
selected slot, and one finite-BF16 shared-expert tensor in
`[batch, sequence, 4096]` order. Routed rows align one-for-one with the dispatch
groups and assignments. The route weight has already been consumed inside the
routed expert before its down projection; this boundary must not multiply it a
second time.

For each flattened token and hidden column, execute the following logical
operation independent of physical rank ownership or arrival time:

1. For each selected logical expert, collect all of that token's routed BF16
   outputs in ascending selected-slot order. Duplicate expert IDs remain
   separate contributions. Widen each BF16 encoding exactly to binary32 and
   reduce the slots with the NUM-6.1 tree.
2. Order the resulting distinct-expert partials by ascending logical expert ID
   and reduce them with a second NUM-6.1 tree. A repaired or tensor-parallel
   implementation must map physical sources back to this global logical order;
   an incidental collective tree is not architectural.
3. Widen the corresponding shared-expert BF16 value exactly and add it to the
   completed routed sum with one binary32 RNE addition. The shared contribution
   is always last and is not a leaf of either routed tree.
4. Convert the result once to BF16 under NUM-4.2.

There is no BF16 rounding between either routed tree and the shared add. BF16
and binary32 subnormals are preserved, and output zero canonicalizes positive.
Malformed dispatch invariants or shapes, missing or repeated token/slot records,
misaligned expert groups, nonfinite input, or intermediate binary32 overflow
poisons. Finite saturation is permitted only at the final BF16 conversion and
is sticky and counted.

The pinned source initializes binary32 `y`, executes
`y[idx] += expert(...)` for experts in ascending ID, performs a distributed sum
when tensor parallelism is active, adds the shared BF16 expert, and finally
converts to the input BF16 dtype. This fixes the shared-add-last boundary but
does not define duplicate-index collision or cross-backend reduction order.
PyTorch 2.10 documents that indexed mutation is equivalent to `index_put_` and
that, with accumulation disabled, behavior is undefined when indices contain
duplicates. On PyTorch 2.10.0+cu128, a bounded witness with token indices
`[0, 0, 1]` and BF16 contributions `[1, 2, 3]` retained `[2, 3]` on CPU and
`[1, 3]` on native SM120; both discarded one legal routed slot instead of the
required `[3, 3]`.

A separate deterministic development audit used seed `0x4558505245445543`, 16
tokens, width 128, eight experts, and six unique selected experts per token. The
target matched both CPU and native SM120 after BF16 conversion in all 2,048
outputs. This no-collision agreement is a bounded observation, not a relaxation
of the explicit target tree. Preserving every selected slot is the governed
architectural rule because inheriting the released advanced-index collision
would make valid model behavior backend-dependent.

### NUM-6.12 Sparse attention with learned sink

`SPARSE_ATTENTION` is the selected-KV attention boundary in every main and
DSpark block. The Flash graph contains 46 sites: one in each of 43 main blocks
and one in each of three DSpark blocks. The global logical profile is:

```text
heads = H = 64
head dimension = D = 512
source block = G = 64 selected slots
score scale = binary32 0x3d3504f3
padding index = signed INT32 -1
query, KV, probability, output = BF16
score, denominator, output accumulator, attention sink = binary32
```

The score-scale code is the correctly rounded binary32 representation of
`512^-1/2`, exact rational `11863283 / 268435456`. The 64 global heads may be
partitioned across execution ranks, but the graph and counters use global
logical order. A physical partition shall reconstruct the same head-indexed
results and aggregate counts.

For positive batch and query extents, inputs are finite BF16
`q[batch, query, H, D]`, finite BF16 `kv[batch, rows, D]`, finite binary32
`sink[H]`, and signed INT32 `index[batch, query, P]` for positive selected-axis
extent `P`. A valid index lies in `0..rows-1`; only `-1` denotes padding.
Duplicate valid indices are legal and remain distinct source slots. Padding may
occur between valid entries and before valid entries in later blocks. The first
64-slot source block of every query row must nevertheless contain at least one
valid entry: the released window construction guarantees this, while an
all-padding first block would expose the source expression `-inf - -inf` and is
not a finite target transaction.

The selected axis is extended implicitly with `-1` to
`T = ceil(P / G) * G`. This tail extension changes block work but performs no
index-buffer read and no mutable-KV read. Explicit `-1` entries are read from the
index tensor but likewise perform no mutable-KV read.

In this section, `RN32` means one binary32 round-to-nearest-ties-to-even
operation with gradual underflow. `FPA32(acc, a, b)` means the exact product of
the finite BF16 operands `a` and `b` is added to the finite binary32 accumulator
and rounded once to binary32, as in NUM-4.1. `CR32(exp(x))` means the correctly
rounded binary32 encoding of the mathematical exponential with no visible
intermediate approximation. `BF16_RNE_SAT` is NUM-4.2.

#### NUM-6.12.1 Block score and online-softmax state

For each query row and head, initialize:

```text
scores_max = -infinity                 # source-control sentinel only
sum_exp = binary32 +0
acc_o[d] = binary32 +0 for d = 0..D-1
```

Traverse the 64-slot blocks in increasing source order. For every valid slot
`j`, gather the complete BF16 KV row once and form:

```text
qk = binary32 +0
for d = 0..D-1:
    qk = FPA32(qk, q[head,d], gathered_kv[j,d])
score[j] = RN32(qk * score_scale)
```

An invalid slot has conceptual score `-infinity` and a zero gathered row. It
does not enter the finite ordered dot. Determine `new_max` by finite numeric
binary32 value across the previous maximum and all valid scores in the block.
For the first block, define the exact source result of
`exp(-infinity - finite_new_max)` as positive binary32 zero. For every later
block:

```text
scores_scale = CR32(exp(RN32(scores_max - new_max)))
```

If a later block is entirely padding, `new_max == scores_max` and
`scores_scale == 1.0`; that block is legal and numerically neutral. For each of
the 64 lanes:

```text
p32[j] = 0                                           if padding
p32[j] = CR32(exp(RN32(score[j] - new_max)))         otherwise
```

Reduce all 64 `p32` codes, including zeros for padding, with the exact NUM-6.1
balanced binary32 tree. There are six levels and 63 additions:

```text
block_sum = NUM-6.1-balanced-sum(p32[0:64])
sum_scaled = RN32(sum_exp * scores_scale)
sum_exp = RN32(sum_scaled + block_sum)
```

The multiply and add are distinct target boundaries. Contraction into one FMA
or reassociation with the score tree is not conforming. Assign
`scores_max = new_max` only with the completed block state.

#### NUM-6.12.2 Probability conversion and AV accumulation

Each of the 64 binary32 `p32` values converts exactly once with
`BF16_RNE_SAT`; this is the released kernel's shared-memory `FP32 -> BF16` copy
before AV. Because `0 <= p32 <= 1`, ordinary finite inputs cannot saturate at
this boundary. For every output dimension, first rescale the prior accumulator
with one separate binary32 multiplication, then traverse all 64 source slots in
increasing order:

```text
p16[j] = BF16_RNE_SAT(p32[j])
acc = RN32(acc_o[d] * scores_scale)
for j = 0..63:
    acc = FPA32(acc, p16[j], gathered_kv[j,d])
acc_o[d] = acc
```

Padding supplies BF16 positive zero for both operands. Duplicate valid indices
execute separate product-adds at their separate source slots. Implementations
may reuse a physical row value only if every duplicate probability contribution
and every logical traffic/event count is retained.

#### NUM-6.12.3 Learned sink and final conversion

After all selected blocks, the learned sink contributes only to the denominator;
it has no AV value. Preserve the source order rather than inserting the sink into
the running maximum:

```text
sink_delta = RN32(sink[head] - scores_max)
sink_exp = CR32(exp(sink_delta))
denominator = RN32(sum_exp + sink_exp)
o32[d] = RN32(acc_o[d] / denominator)
output[d] = BF16_RNE_SAT(o32[d])
```

Unlike score and rescale exponentials, `sink_delta` can be positive. The target
general exponential is proved with exact rational intervals: nonpositive
arguments use an alternating-Taylor enclosure after power-of-two argument
reduction, while positive arguments use the reciprocal enclosure of
`exp(-x)`. Precision doubles until both interval endpoints select the same RNE
code. Correct underflow to a binary32 subnormal or positive zero is legal;
finite exponential overflow poisons. Host `libm`, a GPU approximate intrinsic,
or an error bound that returns a different code is not this numeric profile.

The denominator must be positive finite. A maximum selected score always yields
one exact `p32 = 1`, so a successful finite transaction cannot have a zero
denominator. The final divide rounds once to binary32, then the output converts
once to BF16. No earlier output BF16 boundary exists.

#### NUM-6.12.4 Poison, subnormals, and atomicity

Malformed or nonrectangular shapes; an empty batch, query, head, dimension, KV,
or selected axis; nonfinite BF16 query/KV; nonfinite sink or scale; nonpositive
scale; an index other than `-1` or a legal KV row; an all-padding first block;
binary32 overflow at a dot, scale, rescale, denominator, AV, sink exponential,
or divide boundary; or a zero/nonfinite denominator poisons the complete
homogeneous command under NUM-5. BF16 and binary32 subnormals are preserved;
FTZ and DAZ are not permitted. Arithmetic zero canonicalizes positive. Finite
BF16 saturation is sticky and countable at the final output conversion.

All validation and arithmetic complete before any result, final maximum,
denominator, sink diagnostic, counter, or downstream state can commit. KV is
read-only at this operator; prepare/commit semantics for window and compressed
KV remain separate state operators.

#### NUM-6.12.5 Logical bytes and operation counters

For one global logical query row, let:

```text
P = selected-axis entries stored in the index tensor
T = ceil(P / 64) * 64 source compute lanes
V = number of valid selected occurrences, duplicates included
U = number of unique valid KV row indices
E = P - V explicit -1 entries
L = T - P implicit tail lanes
```

The storage-tier-neutral logical traffic is:

| Traffic | Bytes per query row |
|---|---:|
| query read | `H * D * 2 = 65,536` |
| attention-sink read | `H * 4 = 256` |
| selected-index read | `P * 4` |
| **mutable selected-KV read** | **`V * D * 2 = 1,024 * V`** |
| BF16 output write | `H * D * 2 = 65,536` |

The mutable-KV term counts valid occurrences, not `T`, and is therefore zero for
all `E + L` padding lanes. It deliberately does not collapse duplicates from
`V` to `U`. These are semantic bytes at the operator boundary. A later physical
schedule must separately report HBM transactions, SRAM hits, multicast,
coalescing, compression, retries, and inter-wafer flits; none may silently
replace this logical counter.

Exact source-work counters per query row are:

| Counter identifier | Value |
|---|---:|
| `sparse_source_blocks` | `T / 64` |
| `sparse_valid_selected_rows` | `V` |
| `sparse_unique_selected_rows` | `U` |
| `sparse_duplicate_selected_rows` | `V - U` |
| `sparse_explicit_padding_slots` | `E` |
| `sparse_implicit_tail_padding_lanes` | `L` |
| `sparse_qk_valid_product_accumulates` | `H * D * V` |
| `sparse_qk_padding_product_lanes` | `H * D * (E + L)` |
| `sparse_score_scale_multiplies` | `H * T` |
| `sparse_online_rescale_exp_evaluations` | `H * T / 64` |
| `sparse_score_exp_evaluations` | `H * T` |
| `sparse_score_reduction_adds` | `H * (T / 64) * 63` |
| `sparse_online_denominator_multiplies` | `H * T / 64` |
| `sparse_online_denominator_adds` | `H * T / 64` |
| `sparse_probability_bf16_conversions` | `H * T` |
| `sparse_output_rescale_multiplies` | `H * D * T / 64` |
| `sparse_av_product_accumulates` | `H * D * T` |
| `sparse_sink_exp_evaluations` | `H` |
| `sparse_sink_denominator_adds` | `H` |
| `sparse_final_binary32_divides` | `H * D` |
| `sparse_output_bf16_conversions` | `H * D` |

The padded QK and AV entries describe source block lanes; they are not mutable
KV bytes. A physical implementation may gate zero work, but its schedule and
counter reconciliation must show the transformation explicitly. These counts
are not cycles, Tensor Core instructions, bandwidth utilization, energy, or PPA.

#### NUM-6.12.6 Conformance evidence and source boundary

The one-row anchor with `q=(1,0)`, selected `kv=(2,4)`, sink zero, and scale one
has maximum `0x40000000`, sink exponential `0x3e0a9555`, denominator
`0x3f9152ab`, and BF16 output `(0x3fe1, 0x4061)`. The first probability-rounding
sentinel produces BF16 output `0xbea9`; retaining its probability in binary32
through AV produces adjacent code `0xbea8`. A 65-slot two-block sentinel fixes
online rescaling, duplicate preservation, and final denominator `0x41c56fdd`.

The general exponential has fixed underflow, ordinary, positive, and overflow
answers and matches an independent 220-decimal-digit corpus. With seed
`0x5350415253454456`, the complete target matched a separately expressed
PyTorch source-structure calculation in all 96 BF16 outputs on both CPU and
CUDA 12.8/SM120 under PyTorch 2.10.0+cu128. The bounded corpus includes two
source blocks, holes, duplicates, positive/negative sinks, and tail padding.

The unmodified pinned kernel was additionally executed through TileLang 0.1.8
on CUDA 12.8/SM120. A full-dimension exact-eighths corpus matched all 8,192 BF16
outputs. A broad finite-BF16 corpus differed in three of 8,192 outputs at flat
indices 5,066, 5,651, and 6,124; each difference was one same-sign BF16 code.
The deterministic report SHA-256 is
`57834785ff91628950e59f90222548f7088d13984366c1ee12f86f1a8edcbc4d`.
This bounded difference is retained rather than used to change the target tree.

The canonical MP=4 checkpoint audit concatenates `layers.0..42`, then
`mtp.0..2`, each in rank `0..3` order. Its 184 sink shards contain 2,944 finite
binary32 values and 11,776 bytes with SHA-256
`2f93e2a35c5ad1dbd4aaff353a46082d6811e7b896bf388583bd05e023c2844f`.
The minimum is `-2.4585509300231934` (`0xc01d58e6`), the maximum is
`2.4927473068237305` (`0x401f892c`), and the sign counts are 2,680 positive,
264 negative, and zero exact zeros.

The pinned source fixes block size, data types, gather/padding behavior,
online-update expression order, the BF16 probability copy, learned sink
position, and final output type. It does not fix TileLang GEMM/reduction trees,
FMA contraction, exponential approximation, or device FTZ. The explicit target
rules are therefore deterministic adaptations, not a claim that every
PyTorch/TileLang/CUDA backend emits identical intermediate bits. The checkpoint
audit qualifies the sink payload only. Real checkpoint-derived query/KV known
answers, service-engine execution, transactional KV state, certified schedules,
RTL, cycles, and PPA remain open.

### NUM-6.13 DeepSeek V4 compressor pooling and state

The compressor contract is pinned to `deepseek-ai/DeepSeek-V4-Flash-0731`
revision `7872f01b1d1fe23eabc4c98b48bffcef5a386062`, whose
`inference/model.py` SHA-256 is
`c0c19e6c9fa439bac7fbb1c5bc1868232dfd5aa2f439a548d0e33dcc2a9edd3f`.
The graph contains the following released profiles:

| Scope | Ratio | Raw projected width | Pooled width | Sites |
|---|---:|---:|---:|---:|
| main overlapping compressor | 4 | 1,024 binary32 values | 512 | 21 |
| indexer overlapping compressor | 4 | 256 binary32 values | 128 | 21 |
| main non-overlapping compressor | 128 | 512 binary32 values | 512 | 20 |

Each of the 62 sites is represented by five separate graph operations:
`COMPRESS_PROJECT`, `COMPRESS_STATE_UPDATE`, `COMPRESS_POOL`,
`BINARY32_TO_BF16`, and `COMPRESS_KV_WRITE`. Weighted RMS normalization,
position transformation, and FP8 or FP4 QDQ remain separate operations between
conversion and cache commit. This separation is architectural: projection and
raw compressor state are binary32, while only the post-pool converted and
subsequently transformed row is committed as BF16 mutable KV.

#### NUM-6.13.1 Raw state, APE, and overlap assembly

`COMPRESS_STATE_UPDATE` accepts finite binary32 KV and gate-score projection
outputs. It adds the finite binary32 APE checkpoint row with one binary32 RNE
addition per score feature. Ratio four owns eight raw rows of width `2D`: four
previous rows and four current rows. A completed pool group has eight rows of
width `D`, formed from the previous group's first feature half followed by the
current group's second feature half. The first completed group substitutes four
positive-zero KV rows and four negative-infinity score rows for the absent
previous group. Ratio 128 owns 128 ordinary non-overlapping rows of width `D`.

For prefill at `start_pos == 0`, only the complete prefix
`floor(sequence_length / ratio) * ratio` is exposed to pooling. The incomplete
suffix remains in raw state. For ratio four, the last complete raw group is also
retained as the next group's previous half. The source can evaluate score-plus-
APE separately for complete-prefix pooling and for rows retained in state; the
target counters preserve both source computations instead of assuming a reused
temporary. For decode, exactly one raw row is accepted, written at the phase
`start_pos mod ratio`, and a pool group is emitted only when
`(start_pos + 1) mod ratio == 0`. A completed ratio-four current group then
becomes the previous group.

All caller tensors and the complete prior state validate before address
derivation and immutable result construction. Inactive batches remain
bit-preserved. `Compressor.forward` itself overwrites only addressed rows, so a
new-session raw-state reset is an explicit session-controller responsibility;
it is not silently attributed to the source method.

#### NUM-6.13.2 Deterministic binary32 pooling

For every batch, complete group, and output dimension, `COMPRESS_POOL` executes
the following target rule over eight ratio-four candidates or 128 ratio-128
candidates:

1. select the finite numeric maximum, retaining the first source lane on a tie;
2. subtract that maximum from every finite score with binary32 RNE;
3. evaluate mathematical exponential once with correctly rounded binary32
   output; a negative-infinity sentinel contributes positive zero;
4. reduce exponentials in source-position order with the NUM-6.1 balanced
   binary32 tree;
5. divide every exponential by the denominator once with binary32 RNE;
6. multiply every binary32 KV value by its probability once with binary32 RNE;
7. reduce products in source-position order with the same NUM-6.1 tree; and
8. canonicalize a zero result to positive zero.

Input NaNs, positive infinity, an unexpected negative infinity, a nonpositive
denominator, or intermediate binary32 overflow poisons the whole transaction.
Binary32 subnormals are preserved. This arithmetic freezes a reproducible
accelerator target; it does not assert that PyTorch CPU and CUDA softmax use the
same reduction tree or exponential approximation.

#### NUM-6.13.3 Explicit binary32-to-BF16 boundary

Immediately after pooling, the official method executes `kv.to(dtype)` before
RMS normalization. `BINARY32_TO_BF16` therefore validates a nonempty finite
rank-three binary32 tensor and converts each value exactly once under NUM-4.2
round-to-nearest, ties-to-even. Gradual BF16 underflow is preserved, output zero
is canonical positive zero, finite BF16 saturation is counted, and the result
commits only after the complete input validates. Its logical traffic is exactly
four input bytes and two output bytes per value. It does not include RMSNorm,
RoPE, activation QDQ, or a compressed-cache write.

#### NUM-6.13.4 Compressed-KV commit and validity

`COMPRESS_KV_WRITE` accepts only finite BF16 rows after normalization, position
transformation, and FP8/FP4 QDQ reconstruction. A prefill commits the complete
prefix `floor(sequence_length / ratio)` at slots starting from zero. A one-token
decode commits slot `floor(start_pos / ratio)` only on a ratio boundary; an
incomplete decode window commits no payload row.

The released PyTorch cache object has no validity bitmap. The accelerator target
adds committed-prefix validity so stale payload cannot become visible across
sessions. New-session prefill invalidates the active batches before committing
their new complete prefixes. Decode requires the old valid-prefix length to
equal `floor(start_pos / ratio)` and rejects a gap, forged prefix, or generation
mismatch. Inactive batches and payload outside the newly written rows remain
bit-preserved. Validation, prefix checking, result preparation, and commit are
atomic. Validity-bit writes are counted separately from BF16 payload bytes.

`INDEX_SCORE` reads the committed index-compressed cache; `SPARSE_ATTENTION`
reads the committed main-compressed cache. Neither may consume the uncommitted
pool result or the wrong cache namespace.

#### NUM-6.13.5 Logical counters and storage-tier boundary

The raw-state reference separately reports source KV/score reads, APE reads and
adds, raw-state reads and writes, preserved values, overlap fill, state rolls,
pool operands, modulo evaluations, and transaction commits. The pool reference
separately reports source/APE traffic, comparisons, subtractions, exponentials,
tree additions, probability divisions, weighted multiplications, output writes,
and commits. Conversion reports binary32 reads, BF16 writes, saturation, and
commit. The compressed-cache reference separately reports BF16 source/state
payload traffic, preserved rows, validity invalidation/writes, and commit.

These are logical operator bytes and operations. They do not identify SRAM or
HBM placement, cache hits, banks, bursts, coalescing, NoC traffic, cycles,
achieved bandwidth, latency, energy, area, PPA, or ROM/GPU advantage. Immutable
model weights may be candidates for ROM; raw compressor state and compressed KV
are mutable and must remain in a writable tier. Any M9 storage or throughput
claim must map these exact logical streams through an executable placement and
schedule rather than treating them as a measured physical byte rate.

#### NUM-6.13.6 Checkpoint and source conformance evidence

The governed checkpoint audit found all 62 finite FP32 APE tensors: 21 of shape
`[4,256]`, 21 of `[4,1024]`, and 20 of `[128,512]`. Together they contain
1,418,240 values and 5,672,960 bytes with aggregate SHA-256
`ad6333d91c83b72c3fc426ea712b91446ef4020eac1dc39a299d9e56ab288ea4`.
The range is `-3.3454201221466064` (`0xc0561b5d`) through
`1.1580443382263184` (`0x3f943acc`), with 799,732 negative, 618,508 positive,
and no zero values.

The audit executes the unmodified official `Compressor.forward` and
`overlap_transform`; projection, normalization, RoPE, and QDQ are isolated by
test doubles. On CPU and CUDA 12.8/SM120, the APE-cancelled corpus matched all
1,024 target BF16 outputs. On a broad exact-eighth corpus, both devices differed
from the deterministic target at one of 1,024 outputs: official `0x3d08` versus
target `0x3d09` at flat index 672. The one-code difference is retained as
evidence of the declared backend/target boundary, not hidden by changing the
target arithmetic. The deterministic report SHA-256 is
`d14c2b33d9cfc105af9ba3dc18c4ac3b749a203bd0a6b0d3f1d8592315651324`.

This qualifies the pooling target, all released APE payloads, raw-state
semantics, conversion, and compressed-cache transaction references. It does not
qualify checkpoint-derived projection activations, an executable service-engine
transaction, RTL, a schedule, cycles, physical bandwidth, PPA, complete-model
decode, or any GPU comparison.

### NUM-6.14 Grouped attention-output projection

The grouped-output contract is pinned to `Attention.forward` in
`deepseek-ai/DeepSeek-V4-Flash-0731` revision
`7872f01b1d1fe23eabc4c98b48bffcef5a386062`. After sparse attention and inverse
RoPE, the official source executes:

```text
o = o.view(batch, sequence, local_groups, -1)
wo_a = wo_a.weight.view(local_groups, output_rank, -1)
o = einsum("bsgd,grd->bsgr", o, wo_a)
x = wo_b(o.flatten(2))
```

`GROUPED_OUTPUT_PROJECT` covers the first view, the `einsum`, and the group-major
flattened alias. The downstream FP8 `wo_b` projection is a separate
`FP8_LINEAR` node. The released global profile has 64 attention heads, eight
groups, eight contiguous heads per group, head dimension 512, group-input width
4,096, output rank 1,024 per group, and global canonical weight shape
`[8192,4096]`. Tensor-parallel world sizes 1, 2, 4, and 8 assign each rank one
contiguous interval of respectively 8, 4, 2, or 1 groups.

The raw checkpoint `wo_a` tensor is FP8 E4M3FN with E8M0 scales. The governed
canonical transform slices output rows and dequantizes each exact FP8/scale
value once to BF16 RNE. Grouped-output arithmetic consumes that canonical BF16
payload; raw checkpoint conversion is not repeated inside this operator.

#### NUM-6.14.1 Group orientation and dot arithmetic

For each batch `b`, position `s`, local group `g`, and output-rank row `r`, form
the input vector by concatenating that group's eight heads in increasing
logical-head order, with each head's 512 dimensions in increasing order. Let
`K = 8 * head_dim`. The target then executes:

```text
acc = binary32(+0)
for k = 0 .. K-1:
    acc = RN32_FMA(BF16(input[b,s,g,k]), BF16(weight[g,r,k]), acc)
output[b,s,g,r] = BF16_RNE(acc)
```

Each BF16 product is exact before one binary32 RNE fused-product-add boundary.
The loop is left-associated in increasing `k`; a balanced tree, tensor-core
tile tree, end-of-dot exact sum, or reassociation is not conforming. A completed
finite accumulator converts once under NUM-4.2. There is no bias, activation
quantization, scale lookup, or additional rounding inside this operator.
Output zero is canonical positive zero, gradual subnormal behavior is retained,
and finite BF16 saturation is sticky and counted.

The grouped result has shape `[B,S,G_local,R]`. Its flattened result is the
exact group-major alias `[B,S,G_local*R]`; it performs no second arithmetic or
copy in the semantic contract. A selected-row audit entry point may evaluate
explicit increasing output-rank rows while retaining the declared rank of
1,024. Such a result is evidence for those rows only and reports incomplete
coverage unless every row is supplied.

#### NUM-6.14.2 Poison, immutability, and logical counters

All attention and canonical-weight elements must be finite exact BF16 codes.
Shapes, tensor-parallel ownership, selected ranks, and every caller payload
validate and freeze before arithmetic begins. Any malformed axis, nonfinite
input, binary32 accumulation overflow, or inconsistent public result record
poisons the complete transaction. No partial output commits. Public records use
deep exact tuples, bind the numeric profile, reject subclass authority, and
reconcile grouped/flattened aliases, topology, dimensions, and all derivable
counters.

For `T = B*S`, `G` local groups, `R` evaluated rows per group, and reduction
width `K`, the operator reports:

```text
attention_values       = T * G * K
canonical_weight_values = G * R * K
product_accumulates    = T * G * R * K
binary32_roundings     = product_accumulates
output_conversions     = T * G * R
declared_full_outputs  = T * G * 1024
transaction_commits    = 1
```

These are semantic operations and logical payload values. They are not physical
ROM/SRAM/HBM transactions, bursts, cache behavior, NoC flits, cycles, latency,
bandwidth, energy, area, PPA, or a GPU comparison.

#### NUM-6.14.3 Conformance evidence and source boundary

The independent official-evidence checker re-hashes `inference/model.py`,
`inference/convert.py`, `inference/config.json`, the checkpoint index and lock,
the canonical application, and its independent verification. It verifies all
four 16,777,216-byte MP=4 BF16 `layers.0.attn.wo_a.weight` assignments and all
15 legal aggregate tensor-parallel resource mappings. The resulting certificate
identity is
`57d86552d860aadc779bcfc69a2bffe4fbfdb1908159054661646e1192e02838`.

The reference and separately implemented service arithmetic match exactly on
official-width grouped and flattened output, saturation, ownership, and all
corresponding logical counters. The locked differential covers all 15 legal
topology/rank mappings at one token and `T=1..4` for MP=4 rank zero, using real
canonical layer-0 weights and selected output rows 0 and 1,023. Its aggregate
identity is
`7966492eeeed82bfd9b8cc7555bef3c31f3c4ec65079e235379ddc957906aaed`.
The activation corpus is deterministic synthetic data; it is not a
checkpoint-derived sparse-attention output, and selected rows are not complete
1,024-row execution.

PyTorch `einsum` fixes orientation and dtype but not one portable reduction
tree. Native CPU/CUDA comparisons are therefore bounded development
observations, not the architectural oracle. The target rule above is a
deterministic adaptation and does not claim official-backend bit equivalence.
The logical microprogram and independently checked two-slot schedule establish
operator/resource ordering only. They do not establish artifact-driven
execution, `wo_b`, a tensor-parallel collective, a complete attention or block,
RTL, a physical schedule, timing, bandwidth, PPA, model decode, or performance.

### NUM-6.15 Session-bound circular KV window

`KV_WINDOW_WRITE` is pinned to the circular assignments in
`Attention.forward` and `DSparkAttention.forward` from
`deepseek-ai/DeepSeek-V4-Flash-0731` revision
`7872f01b1d1fe23eabc4c98b48bffcef5a386062`. The official cache has shape
`[B,128,512]`: it is one latent KV row shared by 64 query heads, not a 64-head
KV cache. The target reference represents the row as `[H,V]` with official
`H=1,V=512`; smaller factorizations with `H*V <= 512` are structural test
profiles only.

The architectural position ceiling is the hash-pinned top-level
`config.json:max_position_embeddings = 1,048,576`. This is an address bound,
not evidence that the standalone inference driver runs that length: its source
default is 4,096 and its interactive override is 65,536.

#### NUM-6.15.1 Payload transition

For fresh prefill at `start_pos == 0`, input sequence length `S`, and window
size `W=128`:

- if `S <= W`, write every input row to slots `[0,S)`;
- if `S > W`, retain only the final `W` rows and place absolute position `p`
  at slot `p mod W`, preserving the exact two-slice assignment order; and
- expose the committed absolute range `[max(0,S-W),S)`.

Decode requires `S == 1`, exact `start_pos == next_position` for every active
lane, and writes the row to slot `start_pos mod W`. Its successor cursor is
`start_pos + 1`. All BF16 payload values must be finite. Complete input, prior
state, metadata authority, bounds, and address segments validate before the
new immutable state is assembled; no failed transition exposes a partial
write.

#### NUM-6.15.2 Session, retirement, and version authority

Each fixed-capacity batch lane carries:

```text
{session_id, lane_active, next_position, uint64 version}
```

Session IDs are exactly 64 lowercase hexadecimal digits. Active lanes form a
contiguous prefix and share one cursor. A never-initialized lane has no session,
zero cursor, zero version, and positive-zero payload. A retired lane retains
its session identity and payload as a tombstone, resets its cursor to zero, and
advances its version. Every write, retirement, and view requires equality with
the complete current capacity-wide version vector. Decode additionally
requires exact active-session identity. Removed lanes are retired only as a
trailing active suffix; each affected lane advances its version once.

A session ID may be reused after its current tombstone is deliberately replaced
under current version authority. Stale authority, skipped/replayed position,
duplicate identity, non-prefix activity, version overflow, or cross-session
decode poisons before transition. This pure reference defines deterministic
compare-and-version semantics but does not claim atomic compare-and-swap across
independent service requests.

#### NUM-6.15.3 Chronological valid view and counters

For an active lane with next position `N`, the valid view returns precisely
`[max(0,N-W),N)` in increasing absolute-position order, mapping each position
through `position mod W`. It returns the absolute start, exclusive next
position, session, and exact version. Unused active capacity, all inactive
capacity, and preserved tombstone payload are counted as excluded and cannot
enter a later `ATTENTION_KV_VIEW`.

The write/retire/view records reconcile logical BF16 source and state rows,
bytes, preserved capacity, modulo evaluations, valid rows before/invalidated/
after, session IDs, active flags, cursors, versions, and immutable commit count.
These are semantic counts only. They do not identify SRAM or HBM traffic,
bursts, banking, caches, NoC flits, cycles, latency, bandwidth, energy, area,
routing, PPA, or model throughput. Window KV is mutable and may never be
assigned to mask ROM.

The conformance suite covers both official default axes and bounded exhaustive
profiles; wraparound prefill/decode, `S<W`, `S=W`, and `S>W`; lane shrink,
retirement, tombstone replacement, session reuse, version overflow, stale
authority, maximum position, deep immutability, constructor forgery, malformed
and nonfinite data, counter reconciliation, and randomized physical/causal
oracles. This qualifies `KV_WINDOW_WRITE` target semantics. It does not qualify
projection, RMSNorm, RoPE, QDQ, combined `ATTENTION_KV_VIEW`, compiler/service
lowering, RTL, checkpoint-derived values, long-context quality, or performance.

### NUM-6.16 DSpark main-conditioning projection

`DSPARK_MAIN_PROJECT` is pinned to `Transformer.forward` and
`DSparkBlock.forward_embed` in `deepseek-ai/DeepSeek-V4-Flash-0731` revision
`7872f01b1d1fe23eabc4c98b48bffcef5a386062`. The source captures BF16 hidden
rows after main layers 40, 41, and 42, concatenates those three width-4,096
rows in exactly that order, applies `mtp.0.main_proj`, and then applies
`mtp.0.main_norm`. This boundary consumes the already-captured tensors;
`TARGET_HIDDEN_CAPTURE` remains a separate qualified graph operation.

The released projection has E4M3FN weight shape `[4096,12288]`, E8M0 scale
shape `[32,96]`, no bias, and the ordinary dense-FP8 numeric contract. For
each token:

1. concatenate source 40, then 41, then 42 without conversion or arithmetic;
2. quantize the BF16 activation in 96 increasing 128-value blocks under
   NUM-3.3;
3. evaluate all 4,096 projection rows with output scale tile
   `floor(output_row/128)`, increasing-K block dots, and the NUM-6.1 padded
   reduction of 96 binary32 partials;
4. convert each finite projection accumulator once to BF16; and
5. execute NUM-6.8 weighted RMS normalization at width 4,096 with BF16
   `mtp.0.main_norm.weight` and epsilon binary32 `0x358637bd`.

The canonical padded tree performs 96 cross-block additions per projection
output. This differs from an unpadded algebraic 95-add tree because the
three-element intermediate level is padded with positive zero before its two
final levels. That operation count and reduction order are part of the target
profile.

All 50,331,648 projection-weight bytes, 3,072 scale bytes, finite norm weights,
capture axes, and `B*S` bound `1..4` validate before arithmetic or exact-zero
acceleration. E4M3FN NaN, reserved E8M0 `0xff`, nonfinite BF16, binary32
overflow, malformed shape, or inconsistent public record poisons the complete
transaction. Exact zero activation and byte-exact zero weight rows may skip
mathematically redundant host work, but every complete semantic counter remains
at the declared shape. Public records are deeply immutable and reconstruct the
retained projection-to-RMS relationship; because they omit projection resources
and captures, their constructors do not authenticate projection provenance.

For `T=B*S`, the principal logical counts are:

```text
capture_values             = T * 12,288
activation_blocks          = T * 96
projection_block_dots      = T * 4,096 * 96
projection_products        = T * 4,096 * 12,288
projection_tree_adds       = T * 4,096 * 96
projection_conversions     = T * 4,096
rms_squares                = T * 4,096
rms_tree_adds              = T * 4,095
rms_pointwise_multiplies   = T * 8,192
transaction_commits        = 1
```

The independent reference/service differential covers a nonzero full-shape
synthetic composition, complete official resources at zero input for
`T=1..4`, and real official projection rows 0, 127, 128, and 4,095 at full
reduction width. The governed identities and precise claim separation are in
`docs/DEEPSEEK_V4_DSPARK_MAIN_PROJECT_EVIDENCE.md`. This qualifies target
reference semantics only. Logical values and operations are not physical
ROM/SRAM/HBM bytes, cycles, bandwidth, latency, throughput, energy, area, PPA,
or GPU-comparison evidence.

### NUM-6.17 Attention KV row-space composition

`ATTENTION_KV_VIEW` is pinned to `Attention.forward`,
`DSparkAttention.forward`, and their index helpers in
`deepseek-ai/DeepSeek-V4-Flash-0731` revision
`7872f01b1d1fe23eabc4c98b48bffcef5a386062`. The pinned
`inference/model.py` has SHA-256
`c0c19e6c9fa439bac7fbb1c5bc1868232dfd5aa2f439a548d0e33dcc2a9edd3f`.
This operation composes already-projected, normalized, position-transformed,
and QDQ-processed BF16 KV with already-committed session-bound state. It does
not repeat any of those producer operations or execute sparse attention.

Let `B` be the active batch count, `W=128`, `D=512`, `S` the current sequence
extent, `N` the committed exclusive next position, and `R` a compression ratio
in `{4,128}`. The three legal layouts are:

```text
main prefill: current_kv[0:S] || compressed_prefix[0:floor(S/R)]
main decode:  physical_window[0:W] || compressed_prefix[0:floor(N/R)]
DSpark decode: physical_main_window[0:W] || current_draft_kv[0:5]
```

The compressed suffix is absent when the main layer has ratio zero. Main
prefill requires `start_pos=0` and `N=S`; it retains the complete current
sequence even when `S>W`. Main decode requires `S=1` and
`N=start_pos+1`. DSpark is decode-only, forbids compressed KV, and requires
exactly five current draft rows. Its separately produced `main_kv` row is
committed to slot `start_pos mod W`; the suffix is the distinct draft `kv`
block. The compiler graph must therefore route draft `kv`, not `main_kv`, into
the DSpark `ATTENTION_KV_VIEW` input.

For any decode view define the valid physical-slot set:

```text
P = {p mod W | max(0,N-W) <= p < N}
```

The main-decode selectable set is `P` plus compressed rows
`W..W+floor(N/R)-1` when compression exists. The DSpark selectable set is `P`
plus draft rows `W..W+4`. Unused or preserved stale window slots remain in the
fixed physical output but are never selectable. The set is retained as
increasing physical indices; chronological or query-specific ordering belongs
to `WINDOW_INDEX`, `COMPRESSED_DENSE_INDEX`, `INDEX_TOPK`, or
`DSPARK_WINDOW_INDEX`, not this operation. Every emitted prefill row is valid;
causal per-query masking likewise remains in the separate index tensor.

All active window lanes must form a contiguous prefix, match one to four unique
lowercase 64-hex-digit sessions, share one cursor, and carry the exact complete
capacity-wide version vector. Main prefill rechecks every retained circular
row against the corresponding current KV write. Main decode rechecks the one
new physical slot against its current row. DSpark deliberately omits that
comparison against the five draft rows because its committed main row has a
different source. A compressed input must be an exact independently
revalidated `COMPRESSED_KV_VALID_VIEW` record with the same sessions, cursor,
ratio, row width, prefix length, versions, finite payload, and complete logical
counters. Any mismatch poisons the whole view.

For `C=floor(N/R)` when compression is present and zero otherwise, principal
logical counts are:

```text
current_source_rows_read = B * S
window_state_rows_read   = 0 for main prefill, otherwise B * W
compressed_rows_read     = B * C
output_rows_written      = B * (S + C) for main prefill
                           B * (W + C) for main decode
                           B * (W + 5) for DSpark decode
valid_output_rows        = output_rows_written for main prefill
                           B * (min(N,W) + C) for main decode
                           B * (min(N,W) + 5) for DSpark decode
transaction_commits      = 0
```

BF16 values and bytes, current/window reconciliation, invalid exposed capacity,
modulo evaluations, and session/active/cursor/prefix/version metadata are also
reconciled. These are logical counters only, not HBM/SRAM traffic, bursts,
banks, cache behavior, cycles, latency, bandwidth, throughput, energy, area,
routing, or PPA. Returned payloads, retained sources, compressed snapshots,
regions, validity sets, and counters are deeply immutable and reconstructible.

The conformance suite covers both compression ratios, prefill beyond the
window, decode before and after fill, circular wraparound, official
`[1,128,512]` decode shape, the DSpark main/draft distinction, stale authority,
wrong current rows, forged compressed views and counters, malformed/nonfinite
payloads, alias resistance, forged public results, exact counters, and a
bounded randomized physical-slot oracle. The governed source and claim boundary
are recorded in `docs/DEEPSEEK_V4_ATTENTION_KV_VIEW_EVIDENCE.md`. This qualifies
target reference semantics only; it does not qualify compiler/service/RTL
execution, producer authentication, atomic inter-request compare-and-swap,
checkpoint-derived attention, or physical performance.

### NUM-6.18 DSpark prefill-only main-KV transaction

`DSPARK_PREFILL_KV` is pinned to `Transformer.forward_spec` and the
`start_pos == 0` branch of `DSparkBlock.forward` and
`DSparkAttention.forward` in
`deepseek-ai/DeepSeek-V4-Flash-0731` revision
`7872f01b1d1fe23eabc4c98b48bffcef5a386062`. Each of the three DSpark stages
skips its ordinary block during prefill. From an already-produced BF16
conditioning tensor `[B,S,4096]`, the stage instead performs:

```text
FP8 wkv [512,4096]
  -> weighted BF16 RMSNorm [512]
  -> base RoPE on channels [448,512)
  -> block-64 FP8 QDQ on channels [0,448)
  -> session/version-authorized circular-window commit [B,128,1,512]
```

The released resource set for each stage is an E4M3FN projection weight of
2,097,152 bytes, an E8M0 scale tensor `[4,32]` of 128 bytes, and 512 finite
BF16 normalization weights. Projection uses the ordinary dense-FP8 rule:
32 increasing 128-value activation blocks, output scale tile
`floor(output_row/128)`, NUM-6.1 reduction of 32 binary32 block partials, and
one BF16 conversion. Weighted RMS normalization is NUM-6.8 at width 512.

Base RoPE begins at absolute position zero and changes only the final 64
channels. The first 448 channels are then independently quantized and
dequantized in seven increasing 64-value blocks under the qualified FP8-QDQ
contract. The committed row concatenates those 448 reconstructed BF16 values
with the 64 rotated BF16 values. RoPE is deliberately before QDQ, and the RoPE
channels are never included in the QDQ blocks.

`start_pos` must equal zero. The window must have the official fixed
`[capacity,128,1,512]` shape, active batch capacity must cover `B`, and the
write obeys the complete NUM-6.15 session, freshness, retirement, and
capacity-wide version authority. For `S>128`, all `S` arithmetic rows are
retained in the operator result while only the final 128 rows per active lane
are read and committed by the circular-window transaction. Projection,
normalization, RoPE, QDQ, state authority, and every complete resource validate
before the immutable successor is exposed. A failure poisons the whole
composition without a partial state transition.

For `T=B*S`, capacity `C`, and `W=128`, principal logical counts are:

```text
conditioning_values              = T * 4,096
activation_blocks                = T * 32
projection_block_dots            = T * 512 * 32
projection_products              = T * 512 * 4,096
projection_tree_adds             = T * 512 * 31
projection_conversions           = T * 512
rms_squares                      = T * 512
rms_tree_adds                    = T * 511
rms_pointwise_multiplies         = T * 1,024
rope_rotated_values              = T * 64
rope_binary32_multiplies         = T * 128
rope_binary32_adds               = T * 64
qdq_blocks                       = T * 7
qdq_values                       = T * 448
window_source_rows_read          = B * min(S,W)
window_state_rows_written        = B * min(S,W)
window_state_rows_preserved      = C * W - B * min(S,W)
transaction_commits              = 1
```

The resource-value counters additionally cover all 2,097,152 E4M3FN weights,
128 E8M0 scales, and 512 BF16 norm weights once per stage transaction. Exact
zero activation and byte-exact zero weight rows may skip redundant host work
only after complete input/resource validation; counters still retain the
declared semantic extent. Window rows and bytes are logical state values, not
physical SRAM/HBM transactions. Projection resource values are likewise not a
claim that every byte is physically fetched per token.

Public results retain projection, normalization weights and diagnostics,
rotated values, QDQ codes/scales, committed KV, the complete window-write
record, and counters. They reconstruct every boundary after projection. They
omit conditioning and projection resources, so public construction does not
authenticate projection arithmetic or provenance.

The locked evidence separates three claims: a nonzero complete-shape synthetic
composition; all three official stage resources at zero input for `T=1..4`;
and four nonzero official projection rows checked through an independent FP8
service lane. No checkpoint-derived nonzero conditioning is available, and
those corpora may not be combined into such a claim. The identities and
resource hashes are governed by
`docs/DEEPSEEK_V4_DSPARK_PREFILL_KV_EVIDENCE.md`. This qualifies reference
semantics only, not a complete DSpark block, autoregressive acceptance,
artifact-driven service execution, RTL, physical ROM/SRAM/HBM traffic, cycles,
latency, inference bytes/s, throughput, energy, area, PPA, or GPU advantage.

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

### NUM-7.2 DSpark five-step Markov autoregressive loop

`MARKOV_AUTOREGRESSIVE_LOOP` begins after the DSpark `LM_HEAD` has produced
five binary32 base-logit rows and after the main `SAMPLE` has produced one
initial token plus an explicit entropy continuation. For the graph-qualified
profile, vocabulary size `V` is 129,280, Markov rank `R` is 256, and block size
is exactly five. Inputs are finite binary32 base logits `[B,5,V]`, initial token
IDs `[B]`, BF16 `markov_w1` and `markov_w2` tables `[V,R]`, one finite binary32
temperature, and an immutable entropy value. The official tensors are
`mtp.2.markov_head.markov_w1.weight` and
`mtp.2.markov_head.markov_w2.weight`.

The transaction retains the initial token in output column zero and executes
steps `i=0..4` strictly in increasing order:

1. token `tokens[:,i]` selects one complete BF16 row of `markov_w1` per batch;
2. every selected embedding widens exactly and projects through every global
   `markov_w2` vocabulary row, starting from binary32 positive zero and
   traversing Markov columns `0..R-1` in increasing order;
3. each exact BF16 product enters one binary32 RNE fused product-add;
4. the completed finite Markov bias is added to `base_logits[:,i,:]` with one
   **separate** binary32 RNE addition, with no intervening BF16 conversion; and
5. `SAMPLE` consumes that adjusted row and writes `tokens[:,i+1]`, which is the
   lookup index for the next step.

This dependency forbids reordering, parallel token decisions, or using the
initial token for more than step zero. The immutable successful result exposes
tokens `[B,6]`, adjusted logits `[B,5,V]`, BF16 Markov embeddings `[B,5,R]`,
and the entropy continuation after step four. It also retains the copied base
logits, five projected bias rows, per-step sampling records, source identities,
and exact logical counters for reconciliation. Every input, both complete
weight tables, and all arithmetic results validate before the result commits;
malformed shape/partition, out-of-range token, nonfinite operand, overflow,
entropy exhaustion, or a later-step error poisons the whole transaction without
mutating caller data or exposing a partial token sequence.

Tensor parallelism admits world sizes 1, 2, 4, and 8. Both vocabulary axes use
equal contiguous intervals. A W1 lookup reads the one rank that owns the token;
W2 produces local vocabulary intervals that concatenate in increasing rank
order without a numerical cross-rank reduction. This is a logical topology
contract, not an implementation of the physical lookup routing or gather.

Binary32 positive or negative zero temperature applies finite-binary32
first-index argmax at every step and consumes no entropy. At nonzero
temperature, exact source equivalence fails closed by default: the pinned
release specifies only `torch>=2.10.0` and does not fix the PyTorch/CUDA
generator state, seed-to-word mapping, `exponential_(1)` mapping, exponential,
or reduction implementation. A separately selected target adaptation accepts
immutable positive-finite binary32 values representing post-`exponential_(1)`
draws. It consumes them in step-major, then batch-major, then vocabulary-major
order; each step receives the prior step's continuation, and success consumes
exactly `5*B*V` draws. This adaptation freezes deterministic target arithmetic
without claiming stochastic source bit identity or RNG quality.

Principal successful semantic counts are:

```text
initial token reads/writes          = B
causal token reads                  = 5 * B
base binary32 logits read           = 5 * B * V
W1 / W2 BF16 values validated       = V * R each
embedding row lookups               = 5 * B
embedding BF16 values read/written  = 5 * B * R
exact product-accumulates           = 5 * B * V * R
binary32 accumulation roundings     = 5 * B * V * R
separate binary32 bias additions    = 5 * B * V
adjusted binary32 logits produced   = 5 * B * V
sampling calls                      = 5
sampling logits read                = 5 * B * V
argmax comparisons                  = 5 * B * (V - 1)
entropy draws                       = 0 or 5 * B * V
sampled / complete tokens written   = 5 * B / 6 * B
transaction commits                 = 1
```

These are logical coverage counters. Complete official payload hashes, MP=4
interval hashes, bounded complete causal corpora, rounding sentinels, and eight
full-rank official selected-row projections qualify the reference boundary.
They do not establish checkpoint-derived DSpark hidden state or base logits, a
complete official vocabulary projection, exact nonzero-temperature CUDA replay,
target verification or speculative acceptance, full generation, graph-to-
microcode lowering, artifact-driven service execution, a physical collective,
ROM/SRAM/HBM placement or traffic, schedules, RTL, cycles, latency, bandwidth,
throughput, power, energy, area, PPA, manufacturability, task quality, or GPU
advantage.

## NUM-8 Qualification boundary

### NUM-8.1 Required evidence

Target numerical closure requires:

- exhaustive decode tests for every E2M1 and E8M0 encoding and every FP8 class;
- boundary/known-answer tests for BF16 conversion and scale selection;
- differential random matrix blocks against an independently implemented reference;
- exact tensor-layout and scale-orientation tests from pinned checkpoint metadata;
- layer/operator comparisons against the public model implementation;
- HC_PRE transcendental, pass-count, orientation, poison, and atomic-commit
  evidence required by NUM-6.10.7;
- end-to-end logits, acceptance, and task-quality qualification on representative
  workloads, including saturation and long-context cases.

The first six are possible in public infrastructure once payload subsets are
obtained. Full model quality and production kernel equivalence may require external
compute/traces. Until target-format RTL and these tests pass, analytical operation
counts and `INT_DV` behavior are not numerical implementation evidence.
