# ABI 3.0 operator operand conventions

**Contract ID:** TA-ABI3-OPCONV-1

**Status:** frozen at `TA-A3-ARCH-0` plus amendment A6

**Depends on:** `TA-ABI3-WIRE-1` section 12 (OPERATOR payload)

## 1. Why this document exists

The OPERATOR descriptor gives every engine operation four input views, two
output views and four auxiliary IDs. The wire format freezes the *record*; it
does not say which slot means what for a given subopcode. That mapping is the
interface between three independently written components — the backends that
emit descriptors, the engines that execute them, and RTL 3.0 — so leaving it to
each component's local reading is precisely how the four lanes diverged before.

Everything below is normative. An engine must reject an operator whose slots do
not match its row; a backend must not emit one.

`NO_ID` (`0xffffffff`) means "slot unused". Where a row says *symbol*, the slot
holds a value from the runtime-symbol registry (wire format section 12.2), not
an immediate.

## 2. Tensor family

| Subopcode | in0 | in1 | in2 | in3 | out0 | out1 | aux |
|---|---|---|---|---|---|---|---|
| `MATMUL` | activations `[rows, K]` | weights `[N, K]` | — | — | `[rows, N]` | — | — |
| `GROUPED_MATMUL` | activations | weights | group index | — | output | — | `aux0` group count |
| `ROUTED_MATMUL` | activations | routed weights | expert IDs | route weights | output | — | `aux0` expert count |
| `EMBED_LOOKUP` | token IDs (U32) | embedding table | — | — | gathered rows | — | — |

Weights are n-major (`[N, K]`), matching the checkpoint layout, so no relayout
pass is needed; tiling is expressed by view strides.

## 3. Vector family

| Subopcode | in0 | in1 | in2 | in3 | out0 | out1 | aux |
|---|---|---|---|---|---|---|---|
| `RMS_NORM` | input rows | gain vector | — | — | normalised rows | — | — |
| `HEAD_RMS_NORM` | input `[.., heads, dim]` | gain | — | — | output | — | `aux0` head count |
| `ROPE` | input | coefficient rows | — | — | rotated output | — | `aux0` rotary width |
| `ADD` | left | right | — | — | sum | — | — |
| `SILU_MUL` | gate | up | — | — | product | — | — |
| `CONVERT` | source | optional scales | — | — | converted | optional scales | — |
| `SCALE` | input | optional constant | — | — | output | — | — |
| `SOFTMAX` | input | — | — | — | output | — | `aux0` axis |
| `SQRT_SOFTPLUS` | input | — | — | — | output | — | — |
| `HADAMARD` | input | — | — | — | rotated | — | `aux0` block width |
| `COMPRESS` | input | gate/projection | position embedding | — | compressed | state | `aux0` sub-case |
| `MHC` | hidden | `fn` matrix | `base` | `scale` | weights | combination | `aux0` sub-case, `aux1` Sinkhorn iterations, `aux2` `hc_mult` |
| `INDEX_SCORE` | query | key | head weights | — | scores | — | — |

`COMPRESS` and `MHC` sub-cases are named by `aux0` because several neutral
kernel kinds share one subopcode: `COMPRESS` covers `COMPRESS_PROJECT`,
`COMPRESS_POOL` and `COMPRESS_STATE_UPDATE`; `MHC` covers `HYPER_CONNECT_PRE`,
`HYPER_CONNECT_POST` and `HYPER_CONNECT_HEAD`.

## 4. Attention family

| Subopcode | in0 | in1 | in2 | in3 | out0 | aux |
|---|---|---|---|---|---|---|
| `DENSE` | query | key | value | optional mask | context | `aux0` group size, `aux1` mask mode, `aux2` context-length *symbol*, `aux3` position-base *symbol* |
| `GQA` | query | key | value | optional mask | context | as `DENSE` |
| `SPARSE` | query | fused KV | sparse index (U32) | per-head sink logits | context | `aux0` group size, `aux1` block width, `aux2` context-length *symbol*, `aux3` position-base *symbol* |

Mask mode is `0` causal, `1` full. The attention scale is the numeric
descriptor's `scale_bits`, as an fp32 bit pattern.

### 4.1 Amendment A6 — the sparse operand mapping

`SPARSE` deliberately uses a **different** operand mapping from `DENSE`/`GQA`.
The first implementation reused the dense mapping, which left no slot for the
per-head attention-sink logits that DeepSeek-V4-Flash adds to the softmax
denominator after all blocks, and no field for the block width. That looked like
it required an ABI change, but it does not: DeepSeek uses one KV head with a
fused `[.., 512]` KV tensor, so `q, kv, indices, sink` is exactly four operands
and fits the frozen record. Block width goes in `aux1`, which `DENSE`/`GQA` do
not use.

This is an additive convention on an existing record, not a format change. What
it does mean is that an engine must dispatch its operand reading on the
subopcode and reject a `SPARSE` operator carrying a dense-shaped operand set.

Sparse index arrays are ascending and tail-padded with `0xffffffff`. Padding is
never executed and never counted: `attention.sparse_indices` counts the rows
actually gathered.

## 5. Route family

| Subopcode | in0 | in1 | in2 | out0 | out1 | aux |
|---|---|---|---|---|---|---|
| `TOPK` | scores | — | — | selected IDs (U32) | weights | `aux0` immediate `k` (`NO_ID` takes `k` from the output extent) |
| `BIASED_TOPK` | scores | selection bias | — | selected IDs | weights | `aux0` `k` |
| `WEIGHT_NORMALIZE` | weights | — | — | normalised | — | — |
| `EXPERT_DISPATCH` | activations | selected IDs | — | dispatched `[groups * k, width]` in `(group, slot)` order | — | `aux0` expert count, **required** |
| `INDEX_TOPK` | scores | — | — | ascending indices | — | `aux0` `k`, `aux1` mask mode, `aux2` context *symbol*, `aux3` position-base *symbol* |
| `HASH_ROUTE` | token IDs | hash table | — | expert IDs | — | — |
| `WINDOW_INDEX` | positions | — | — | ascending indices | — | `aux0` window, `aux1` mask mode, `aux2` context *symbol* |

`EXPERT_DISPATCH` requires `aux0`: an engine that cannot state the expert bound
cannot prove a routed ID is inside it, and an unbounded expert ID is a memory
safety problem, not a routing detail.

`BIASED_TOPK` selects on `scores + bias` but returns weights gathered from the
**unbiased** scores. That asymmetry is the DeepSeek `noaux_tc` contract and is
easy to get wrong in both directions.

`HASH_ROUTE` uses a frozen 32-bit avalanche mix. It is part of the contract, not
an implementation choice.

## 6. Reduction family

| Subopcode | in0 | in1 | in2 | out0 | aux |
|---|---|---|---|---|---|
| `ORDERED_SUM` | terms `[terms, ...]` | optional base | — | `[...]` | — |
| `EXPERT_SUM` | contributions `[experts, ...]` | weights `[experts]` | optional base | `[...]` | — |
| `VOCAB_GATHER` | partition logits `[partitions, width]` | optional partition order (U32) | — | `[partitions * width]` | — |
| `GROUPED_CONCAT` | up to four inputs concatenated on axis 0 | | | output | — |
| `PARTITION_SUM` | partials `[partitions, ...]` | optional base | — | `[...]` | `aux0` active-partition *symbol* (`NO_ID` reduces all) |

An optional base enters the ordered sum **first**, as an accumulator's initial
value. `EXPERT_SUM` forms `weight * contribution` in binary32 and reduces in the
declared order, which is what makes a MoE layer independent of expert arrival
order.

## 7. DMA family

| Subopcode | in0 | in1 | out0 | aux |
|---|---|---|---|---|
| `TRANSFER` | source | — | destination | — |
| `FILL` | optional fill-code view | — | destination | `aux0` fill code when in0 is `NO_ID` |
| `GATHER` | index view (U32) | source | destination | — |
| `SCATTER` | index view (U32) | source | destination | — |

Every index is range-checked; an out-of-range index is trap class 3, never a
clamp.

## 8. Selection family

| Subopcode | in0 | out0 | aux |
|---|---|---|---|
| `ARGMAX` | logits (BF16 or FP32) | **one** U32 element | — |
| `TOKEN_APPEND` | **one** U32 element | optional one U32 ring element | — |

`ARGMAX` applies the frozen `greedy_lowest_token_id_argmax` rule and treats a
non-finite logit as a numeric fault, not a value to skip. `TOKEN_APPEND`
validates against the bound GENERATION_POLICY, tests the EOS set, and its ring
output normally carries a dynamic term bound to `GENERATION_INDEX` so one
descriptor serves every decode step.

`SAMPLE` has no governed contract and is deliberately unimplemented; dispatch
fails closed on it.

## 9. Link family

LINK instructions name a COMMUNICATION descriptor rather than an OPERATOR, so
this table does not apply to them. Their fields are frozen in wire format
section 12.

## 10. Compliance

`tests/sim/` asserts each engine rejects an operator whose family, subopcode or
operand shape does not match its row. A backend that emits a non-conforming
operator is rejected at execution, not silently reinterpreted.

---

## 11. Amendment A7 — numeric contracts and the execution backend

Measured on this machine at Qwen3-8B shapes (`[8,4096] x [4096,4096]^T`):

| Path | Rate | One 8,000-token Qwen prefill (6.06e13 MAC) |
|---|---:|---:|
| exact scalar sequential-K kernel | 0.15 GMAC/s | ~112 hours |
| NumPy binary32 matmul | 1.1 GMAC/s | ~15 hours |
| Torch CPU binary32 matmul | 5.0 GMAC/s | ~3.4 hours |
| Torch CUDA binary32 matmul | 970 GMAC/s (30 TMAC/s at prefill shapes) | ~2 seconds of contraction |

The exact sequential kernel cannot execute the mandatory workloads. That is not
a tooling inconvenience; it decides whether this program can produce real tokens
at all. Two things follow.

**`SEQUENTIAL_ASCENDING` was never the hardware contract.** It is an artifact of
a scalar simulator. The accelerator being designed contracts a 4,096-element
reduction on a lane array; it forms a tree across the lane width and accumulates
partial sums across passes. A strictly sequential 4,096-step dependency chain is
the one thing such hardware provably does *not* do. Declaring a blocked
reduction is therefore more faithful to the design, not a concession to
simulation speed.

**Two contracts are declared, and both are exact.**

`bf16_bf16_fp32_sequential_rne_v1`
    BF16 operands widened exactly to binary32, exact products, strictly
    ascending-K binary32 accumulation, one RNE output rounding. Reproducible on
    any machine. Used for **numeric qualification** at small shapes and as the
    scalar oracle.

`bf16_bf16_fp32_blocked_rne_v1`
    BF16 operands widened exactly to binary32, exact products, binary32
    accumulation in the executing implementation's declared deterministic
    blocked association, one RNE output rounding. Used for **execution**.

The blocked contract's association is fixed by an *implementation identity* —
library, version, device and shape — which every execution report records. Two
runs of the same implementation are bit-identical; this was verified, and the
contract does not claim portability across implementations. That is a weaker
guarantee than the sequential contract and is stated as such wherever it is
used.

Three consequences make it sound for this program's purposes:

1. **ROM versus HBM stays bit-exact.** Both targets execute on the same
   implementation with the same descriptors, so a token difference between them
   is a real difference, never an artifact of association.
2. **Correctness is still checked against something we did not compute.** The
   acceptance gate is token-level agreement with the external reference oracle,
   which runs the vendor modelling code.
3. **The gap between the two contracts is measured, not assumed.** A
   qualification report records the observed difference at representative
   shapes; it is not asserted to be zero.

Anything that claims bit-exactness must name which of the two contracts it
means. A report that says only "exact" is incomplete.

## 12. Amendment A8 — resolved operand ambiguities

The engine workers found five places where the frozen tables under-specified an
operation. Each is resolved here rather than left to local reading.

**`VECTOR.SCALE` sub-case moves to `aux_id_0`.** The first implementation
inferred the sub-case from `scale_bits != 0`, which makes a legitimate scale of
zero unrepresentable. `aux_id_0` now names it: `0` multiply by the profile's
`scale_bits`, `1` elementwise multiply by `input_view_1`, `2` logistic sigmoid.
This matches the `COMPRESS`/`MHC` pattern already in section 3.

**Two RMSNorm contracts coexist and are both correct.** The Qwen contract
materialises the normalised value in BF16 before the gain multiply; the DeepSeek
contract stays in binary32. Measured, they disagree by exactly one BF16 ulp on 24.81 % of elements at
width 4096 and 25.78 % at width 128, so they are genuinely different
operations and get different names:
`qwen3_rmsnorm_fp32_bf16_v1` and `deepseek_rmsnorm_binary32_v1`. The engine
dispatches on the numeric descriptor's contract digest. Silently picking one
would corrupt whichever model did not get it.

**RMSNorm declares `PAIRWISE_TREE`.** The frozen kernel's row sum is a balanced
tree, so `SEQUENTIAL_ASCENDING` — the builder's default — contradicted it. The
enum already had the right value; the builder was wrong to default it.

**`SWIGLU` takes two operands, not three.** `lowering.py` gave it three inputs,
but no three-operand contract exists and the engine correctly refuses it. The
neutral kind lowers to `VECTOR.SILU_MUL` with `(gate, up)`; a separate limit, if
a model needs one, belongs in the numeric descriptor.

**Block-scale addressing is frozen.** `scale_object_id` names an object, which
carries no shape, so the rule is: one E8M0 byte per `scale_block_elements`, laid
out in the view's logical row-major order, addressed at
`element_offset // scale_block_elements`. It requires last-axis stride 1 and
`K % scale_block_elements == 0`; anything else fails closed.

---

## 13. Amendment A9 — neutral IR gaps found by lowering a second model

Exporting DeepSeek-V4-Flash against the same schema Qwen uses found four
things the neutral IR could not express. That is exactly what a second model is
for: a schema validated against one model is a schema with unexamined
assumptions. Three are resolved in the schema; one is deferred with a stated
reason rather than half-built.

**Predicated kernels (resolved).** `Kernel` gains `predicate`, naming an
earlier kernel's boolean output. DeepSeek's compressor runs its
pool/norm/rope/quantise/commit chain only at ratio boundaries, and the source
graph carries that as a first-class guard. With no predicate field the guard
could only travel as an attribute, leaving a backend to choose between always
running the chain — wrong — and honouring an unenforced hint. ABI 3.0 already
carries predicates on instructions and loop descriptors; the neutral IR was the
only layer missing one. `check_neutral` now requires the named tensor to be a
`bool` produced earlier.

**Banked weights (resolved).** `CheckpointBinding` gains an ordered `segments`
list. A layer's 256 routed experts are one operand to the model but are
interleaved and lexicographically ordered across the shards, so no single byte
range covers a bank. Without segments the operand had to travel as an attribute
holding a list of tensor names, which is not an operand at all. Each segment
carries its own digest, so verification stays incremental instead of requiring
the assembled image — which matters when the bank is part of 156 GB. This is
the same mechanism the backends already use to give a per-layer weight group a
uniform stride.

**Derived constants (resolved).** `Tensor` gains `generator`, and a `constant`
may now carry a generator instead of a checkpoint binding. A rotary coefficient
table, a causal window index table and a compressed-group enumeration are
constants no checkpoint contains — they are computed from declared parameters.
Requiring a binding for every constant made them undeclarable, which in turn
left `VECTOR.ROPE`'s `in1` "coefficient rows" slot unfillable by either
exporter.

**Stochastic selection (deferred, with reason).** No neutral kind produces or
consumes randomness, so only the greedy branch of the released `sample()` is
expressible. This is deliberately left open: ADR-003 section 7 makes sampling an
optional capability with an explicitly versioned RNG and probability contract,
and says it is not required for initial greedy acceptance. `SELECTION.SAMPLE` is
correspondingly unimplemented and fails closed. The gap is real and is recorded
as **OI-4**: neither lane can honour a `do_sample: true` request until a
governed sampling contract exists, and inventing an RNG to close it would make
every future result irreproducible.

## 14. Amendment A10 — two operand corrections from the DeepSeek lowering

**`REDUCTION.EXPERT_SUM` weights are optional.** Section 6 reads
(contributions, weights, optional base), but the released DeepSeek expert
applies its routing weight *before* the down projection — `mxfp4_swiglu_bf16`
takes `route_weight_binary32_codes` and `reduce_expert_outputs_bf16` takes
none. A backend that re-applied weights at the reduction would square them.
`input_view_1` is therefore optional, and an operator that omits it is
declaring that the weight was already applied. The kernel's
`routing_weight_application` attribute records which convention is in force.

**`ROUTE.BIASED_TOPK`'s second output may be unused.** The `noaux_tc` gate
selects on biased scores and re-gathers weights from the unbiased scores, so
the biased scores themselves are dead in this model. The slot stays in the row
because a model that selects and weights on the same scores needs it; an
exporter that does not use it says so rather than silently dropping it.

---

## 15. Amendment A11 — the KV append operand row

`KV_APPEND` lowered to `VECTOR.CONVERT`, which the vector engine correctly read
as a dequantize and rejected on a shape mismatch. An append is a *movement*: one
source plane written at the positions the request names. It lowers to
`DMA.SCATTER`.

| Neutral kind | in0 | in1 | out0 |
|---|---|---|---|
| `KV_APPEND` | source plane | destination positions (U32) | appended extent |

That is the reverse of `DMA.SCATTER`'s own row in section 7, where `in0` is the
index. The backend permutes the two when it binds the operator. Both exporters
already emit `(source, index)` in that order, and rewriting either to match the
engine's slot order would push a backend concern into the neutral IR, which
ADR-003 section 15 forbids.

Qwen appends the key plane and the value plane as two independent movements
rather than one fused operation, which is what the hardware does — two DMA
descriptors into two extents of the prepared state. Its per-layer kernel count
is therefore twenty rather than nineteen.
