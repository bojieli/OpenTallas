# ABI 3.0 operator operand conventions

**Contract ID:** TA-ABI3-OPCONV-1

**Status:** frozen at `TA-A3-ARCH-0` plus amendments A6-A11 and A16-A19

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
actually gathered. That clause stands as written; amendment A19 (section 19)
moves the obligation onto the producer, which is `ROUTE.INDEX_TOPK` and has the
window block, the compression ratio and the KV row space it needs to satisfy
it. The released kernel imposes no order and accepts a `-1` at any slot, so this
is OpenTallas's canonical form for the array rather than the model's, chosen so
that a consumer can check what reaches it.

## 5. Route family

| Subopcode | in0 | in1 | in2 | out0 | out1 | aux |
|---|---|---|---|---|---|---|
| `TOPK` | scores | — | — | selected IDs (U32) | weights | `aux0` immediate `k` (`NO_ID` takes `k` from the output extent) |
| `BIASED_TOPK` | scores | selection bias | — | selected IDs | weights | `aux0` `k` |
| `WEIGHT_NORMALIZE` | weights | — | — | normalised | — | — |
| `EXPERT_DISPATCH` | activations | selected IDs | — | dispatched `[groups * k, width]` in `(group, slot)` order | — | `aux0` expert count, **required** |
| `INDEX_TOPK` | scores, or `NO_ID` for the dense form (A20) | window index (A19) | compression ratio (A19) | joined KV rows, compacted and ascending | — | `aux0` `k`, `aux1` mask mode, `aux2` context *symbol*, `aux3` position-base *symbol* |
| `HASH_ROUTE` | token IDs | hash table | — | expert IDs | — | — |
| `WINDOW_INDEX` | positions | — | — | ascending indices | — | `aux0` window, `aux1` mask mode, `aux2` context *symbol* |

`WINDOW_INDEX` writes `arange(first, last + 1)` over the **absolute positions**
of a causal window and nothing else. Amendment A20 (section 20) makes that a
checkable claim rather than a description: a neutral kernel that names an
`index_family` this operator does not produce is refused at admission.

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
| `GROUPED_CONCAT` | up to four inputs concatenated on the join axis | | | output | `aux0` join axis (`NO_ID` and `0` are axis 0; amendment A17) |
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
library, version, device, shape **and thread count** — which every execution
report records. Two runs of the same implementation are bit-identical; the
contract does not claim portability across implementations. That is a weaker
guarantee than the sequential contract and is stated as such wherever it is
used.

Thread count was not in the identity when A7 was first written, and leaving it
out made the amendment's own guarantee false. A threaded library parallelises a
matmul by splitting the reduction across threads, so the association — and
therefore the bits — is a function of how many threads run it. Measured on this
machine at Qwen3-8B shapes, `[97,4096] × [512,4096]ᵀ` with BF16-rounded
operands under `torch.matmul`:

| Threads | SHA-256 of the binary32 result (first 32 hex) |
|---:|---|
| 1 | `be2bc1c7c38a621236a4a5ae95dbdaa4` |
| 4 | `d88caa090e8273ae051771c963d80a3d` |
| 16 | `63799d46b2ec83d22e7a1b7c94077c9f` |

Three thread counts, three different answers, one recorded identity. Two runs
could therefore have declared the same identity and disagreed, which is
precisely what the identity exists to rule out. The torch backends now record
`torch_num_threads` and `torch_num_interop_threads`; NumPy exposes no portable
accessor, so its identity records the thread-count environment variables
instead, and an empty value there means the BLAS chose for itself — such a run
is reproducible only on a machine that would make the same choice.

This does not change which associations are legal, so it is a completion of A7
rather than a new amendment. It does mean that any execution record written
before this change is *incomplete*, not wrong: its tokens are what that machine
produced, but the record does not pin down the configuration well enough to
guarantee a rerun reproduces them.

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

> **Generalised by amendment A15** (wire format, section 12.6). The rule above
> addresses one axis, and the released DeepSeek FP8 weights scale 128 × 128
> *tiles* — 256 codes where this rule demands 32,768. A15 adds
> `scale_block_rows` and makes the statement above its `scale_block_rows = 1`
> case, exactly; no program written against this paragraph changes meaning.


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

---

## 16. Amendment A16 — three conventions the DeepSeek wafer needed

**Frozen.** Nothing here changes a record, a field or a byte of
`runtime/abi3/`; all three are statements about slots and contract names that
the frozen wire format already carries, in the same class as amendment A8. They
are written down because the engines implement them and an undocumented
convention is how two components come apart.

### 16.1 `VECTOR.ROPE` has two contracts, and `aux_id_0` is load-bearing

Section 3's `ROPE` row already reads *`aux0` rotary width*. Until now no
operator used it: Qwen rotates the whole last axis, so its rotary width and its
head width are the same number and leaving the slot at `NO_ID` said nothing
false. DeepSeek-V4-Flash rotates 64 channels of a 512- or 128-wide head, so the
slot has to mean what the row says it means.

An engine therefore dispatches `ROPE` on the numeric descriptor's contract
digest, exactly as amendment A8 has it dispatch `RMS_NORM`:

| contract | channels | pairing | rounding |
|---|---|---|---|
| `qwen3_rope_fp32_bf16_v1` | the whole last axis | `i` with `i + width / 2` | each product to BF16, then the sum |
| `rope_apply_bf16_v1` | the final `aux0` | `2p` with `2p + 1` | binary32 through both products and the sum, one BF16 rounding at the output |
| `rope_inverse_bf16_v1` | as above, conjugate phasor | as above | as above |

Three things separate them and any one of them alone would corrupt a model:
which channels move, which channel each is paired with, and where the
arithmetic rounds. An engine that recognises neither contract must refuse the
operator rather than pick one.

The partial rotation **cannot** be expressed as the whole-axis contract over an
identity-padded table. Under `qwen3_rope_fp32_bf16_v1` channel `i` is paired
with `i + 256`, so rotating channels 448–511 of a 512-wide head necessarily
moves channels 192–255 with them; identity coefficients on the untouched
channels do not prevent that, because those channels are the *partners* of the
rotated ones, not bystanders. Nor is a strided sub-block view over the rotated
channels enough on its own: within any sub-block the frozen kernel still splits
in half, and DeepSeek pairs adjacently. `aux_id_0` plus a contract that names
the pairing is what expresses it; the untouched prefix is carried by the same
operator, which is what the reference's `prefix_bf16_values_preserved` counter
reconciles.

`in1` is `cos[rotary_width] || sin[rotary_width]` — the row spans the *rotated*
channels, and pair `p`'s coefficient is repeated at `2p` and `2p + 1` so the row
reads channel-for-channel against the block it multiplies. That keeps section
3's "cosine then sine" layout and keeps the pair folding in the table rather
than in the engine.

### 16.2 `VECTOR.CONVERT` takes a carried plane for a partial dequantisation

`compiler/ir/v3/lowering.py` already gives `DEQUANTIZE` three inputs and says
why: DeepSeek quantises the 448 non-rotary channels of a 512-wide KV vector to
E4M3FN and keeps the 64 rotary channels in BF16, because those channels carry
position. Reconstructing the vector reads two sources.

| sub-case | in0 | in1 | in2 | out0 |
|---|---|---|---|---|
| whole-row dequantise | codes | block scales | — | converted, same shape as in0 |
| partial dequantise | codes `[.., narrow]` | block scales | carried plane `[.., full]` | `[.., full]` |

The carried channels are **moved, not converted**: their codes reach the output
unchanged and are not counted as conversions. `in2` present is what selects the
sub-case; `in0`'s last axis must be a proper prefix of `out0`'s, and the carried
plane must match the destination exactly. The alternative — a two-operand
dequantise plus a concatenation — is not available, because
`REDUCTION.GROUPED_CONCAT` joins one whole axis of equal-framed operands and
this splits one axis into a converted prefix and a carried suffix — even under
amendment A17, whose feature join still requires every operand to agree on every
axis it does not consume.

The mirror case needs no new slot, only a view: a `QUANTIZE` whose code output
is narrower than its source quantises a prefix of each row, and the backend
presents `in0` with the same row stride and fewer elements of it. The output
shape is the authority; a declared `quantized_width` is checked against it
rather than trusted.

### 16.3 `REDUCTION.EXPERT_SUM`'s base may join after the terms

Section 6 reads (contributions, weights, optional base) and places the base
*first*, which is the residual convention: the base is one more term and it
associates with the rest. `runtime.reference.dispatch.reduce_expert_outputs_bf16`
does something different — it reduces the routed contributions with the NUM-6.1
balanced tree and *then* adds the shared expert with one further binary32
addition.

With six routed terms and a balanced tree these are different numbers, not two
spellings of one: a base folded in as a seventh leaf meets the routed sum at the
second level of the tree, and a base added afterwards meets the completed sum.
The contract name selects the placement — `dispatch_reduce_expert_outputs_bf16_v1`
adds the base after the terms — and every other contract keeps section 6's
first-term placement.

The association itself is a separate statement and travels in the numeric
descriptor's `reduction_order`, which the neutral kernel declares. A reduction
that states no order is encoded as sequential, which for this operation is also
a different number; the exporter says `pairwise_tree` because the reference's
tree is what the model is.

## 17. Amendment A17 — `REDUCTION.GROUPED_CONCAT` names its join axis

Wire format section 12.7 is normative; this section states what it means for an
operand row and what it obliges a backend to do.

| Subopcode | in0 | in1 | in2 | in3 | out0 | aux |
|---|---|---|---|---|---|---|
| `GROUPED_CONCAT`, axis 0 | `[L_0, ...]` | `[L_1, ...]` | `[L_2, ...]` | `[L_3, ...]` | `[sum(L_i), ...]` | `aux0` = `0` or `NO_ID` |
| `GROUPED_CONCAT`, axis 1 | `[R, C_0]` | `[R, C_1]` | `[R, C_2]` | `[R, C_3]` | `[R, sum(C_i)]` | `aux0` = `1` |

Unused input slots are `NO_ID` and contribute nothing, as before. Input *i*
occupies `[sum(C_<i), sum(C_<i) + C_i)` of the output's feature axis, in slot
order: the descriptor states the column order, so no backend has to choose one.

`aux0` here is an **immediate**, not a runtime symbol. That is the same reading
`VECTOR.ROPE`'s rotary width and `ROUTE.TOPK`'s `k` already have, and it is the
opposite of `REDUCTION.PARTITION_SUM`'s `aux0`, which is a symbol; the row above
is the authority for which, exactly as section 1 requires.

**What an engine must do.** Dispatch the operand reading on the axis, refuse an
axis the amendment does not define, refuse a feature join on an operand that is
not rank 2, and refuse a set of operands that disagree on any extent the join
does not consume. All four are also admission refusals, so an engine that sees
one is seeing a program that reached it without being verified.

**What a backend must do.** Emit the axis. A neutral `CONCAT` kernel carries its
join axis as an attribute — the DeepSeek export states one on every
concatenation it emits, and Qwen3-8B emits none at all — and that attribute is
what `aux0` must carry; a backend that drops it silently re-labels a feature
join as a row join. A backend that previously *re-expressed* an axis-one
concatenation as one movement per column window must stop: the operator exists
now, the movement form costs one event per input where the operator costs one
per kernel, and a lane that emits transfers where the other lane emits
`REDUCTION.3` is the divergence this contract exists to prevent.

**What it does not change.** Axis 0 behaves exactly as it did, including the
trailing-shape agreement rule, which is the `axis = 0` case of the non-join
extent rule stated in general. No existing program's bytes move, because an
unnamed `aux0` is `NO_ID` and `NO_ID` is axis 0.

## 18. Amendment A18 — an operand states which extent the request decides

Wire format section 12.8 is normative; this section states what it means for an
operand row and what it obliges a backend to do.

Every row in this document states extents in symbols — `[B, S, H, D]`,
`[rows, K]` — and until now exactly one of those symbols could actually follow
the request: the leading one, through amendment A13, and only by shortening.
That was enough while the leading axis carried the request's own unit and no
operand held anything the request did not put there. It stops being enough in
three places, and they are three different failures rather than one:

| Subopcode | operand | shape | request-dependent extent |
|---|---|---|---|
| `VECTOR.COMPRESS`, `aux0 = 2` | `in0` | `[B, S, 2, W]` | `S` at axis 1, `1 * S / 1` |
| `VECTOR.COMPRESS`, `aux0 = 2` | `out0`, `out1` | `[B, G, P, D]` | `G` at axis 1, `1 * S / ratio` |
| `VECTOR.INDEX_SCORE` | `in1` | `[B, C, D]` | `C` at axis 1, `1 * S / 128` |
| `VECTOR.INDEX_SCORE` | `out0` | `[B, S, C]` | `C` at axis 2, `1 * S / 128` |
| `REDUCTION.GROUPED_CONCAT`, axis 0 | `out0` | `[R, D]` | `R` at axis 0, `1 * S / 1 + 128` |

`COMPRESS_STATE_UPDATE` groups along `S` and its overlap transform reaches
across `G`, so neither axis can be the batch and neither can be moved to the
front. `INDEX_SCORE` requires `kv_batch == batch`, so under every assignment of
`B` at least one of `S` and `C` is a non-leading axis. And the attention KV
join carries a 128-row sliding window that the request does not supply, so its
output extent is *longer* than the rows the request has — which a clamp cannot
state at all, because a clamp only shortens. None of the three is a shape a
backend chose; all three are what the released model computes.

**What a backend must do.** State the axis, the numerator, the unit and the
bias on the view. A neutral tensor whose extent is a *derived* symbol lowers to
the base symbol as the loop's `bound_symbol` and to the affine coefficients on
the view: `span_groups_ratio4` is `SPAN_TOKENS / 4`, `attention_rows_window` is
`CONTEXT_LENGTH + 128`, `attention_rows_ratio4` is
`5 * CONTEXT_LENGTH / 4 + 128`. A backend that states none of them leaves the
operand at its declared maximum, and the verifier now refuses a view that
declares one and cannot resolve it, so the failure is an admission refusal
rather than a wrong answer.

A backend must **not** re-express a join whose output extent it cannot state as
a stream of movements with a symbol-offset destination window. That is
mechanically available — the all-gather already offsets a destination by
`NODE_ID` — and it is exactly the hand-expansion amendment A17 abolished for
axis 1: one operator with two spellings across two backends. The extent has a
spelling now; use it.

**What an engine must do.** Nothing new. An engine reads resolved extents and
they arrive at the request's size, exactly as A13's already did. The DeepSeek
operators keep their existing shape checks, and those checks are what turn a
backend that dropped the declaration into a refusal at the operand rather than
a wrong tensor: `COMPRESS_STATE_UPDATE` refuses a span with no complete group,
`INDEX_SCORE` refuses a key whose batch is not the query's, and
`GROUPED_CONCAT` refuses an output that is not the sum of its inputs.

That last one is worth stating plainly, because A17 and A18 meet there and do
different jobs. **A17 names the axis a join consumes; A18 states the extent the
join produces.** A17's rule — the output's joined extent is the sum of the
inputs' — remains a *check*, evaluated against the extents the operands resolve
to. It is not a derivation: a view's extent is the view's own statement, and no
operator rewrites one. So a join whose output extent follows the request must
say so under A18, and A17 then confirms that what it said is the sum.

**What it does not change.** An operand that declares none of the four fields
behaves exactly as it did. All four are zero on every view written before this
amendment, and that is axis 0, the bound symbol's own value, and no bias —
which is amendment A13, unchanged.

## 19. Amendment A19 — `ROUTE.INDEX_TOPK` selects, rebases and joins

Wire format section 12.9 is normative; this section states what it means for an
operand row and what it obliges a backend to do.

| Subopcode | in0 | in1 | in2 | in3 | out0 | aux |
|---|---|---|---|---|---|---|
| `INDEX_TOPK`, unjoined | scores `[span, C]` | `NO_ID` | `NO_ID` | — | ascending indices `[span, k]` | `aux0` `k`, `aux1` mask mode, `aux2` context *symbol*, `aux3` position-base *symbol* |
| `INDEX_TOPK`, joined | scores `[span, C]` | window index `[span, W]` U32 | compression ratio `[1]` U32 | — | joined KV rows `[span, W + k]` U32, compacted, ascending, `0xffffffff`-padded | as above |

`aux2` and `aux3` are read **in the symbol's own units**. For DeepSeek that is
tokens, and the candidate axis is counted in compression groups, so `in2` is
what converts between the two. Before A19 they were silently the same number
and a compressed axis had no way to say otherwise; that is the whole of defect
three.

`in2` is a **one-element U32 view**, not an immediate: `aux0..aux3` are spent
on this operator and an operator has four. It reads a mask-programmed constant
because a compression ratio is a property of the layer, not of the request.

**What an engine must do.** Dispatch on the presence of the two slots. With
`in1` absent there is no window segment and `W` is zero; with `in2` absent the
ratio is one and a candidate is already a KV row, which is the operator as it
stood. With both present:

* the visible candidate count for the query at absolute position `p` is
  `(p + 1) / r`, floored, clamped to `context / r`;
* a selected candidate `g` names KV row `span + W + g`;
* the emitted row is the window block and the rebased selection, with every
  `0xffffffff` removed, sorted ascending and tail-padded back to `W + k`.

Refuse a window block whose leading extent is not the span, an `in2` that is not
one U32 element, and an output narrower than `W + k`. `aux0` is the selection
width and not the operand width: the output is the join, so `W + k` is its last
extent and `k` alone is what the operator selects.

`context / r == 0` is **not** a fault. Below one whole compression group the
released model runs that layer as pure sliding-window attention, so the
operator selects nothing and emits the window block alone. Refuse it only when
there is no window block either, because then there is nothing to emit.

**What `ATTENTION.SPARSE` must do with the result.** Bound the index by the
fused KV operand's own resolved leading extent, and read `aux_id_2` as a bound
on *positions* only. A19 makes the index name rows of a join — the request's
rows, the window, then the compressed rows — and a context length in tokens
counts none of those. `DENSE` and `GQA` keep `aux_id_2` as a row bound because
their KV view is indexed by position; for them the two numbers are the same
one. A fused KV buffer presented at capacity still says how much of itself the
request filled, through its view's extent, which is amendment A13.

**What a backend must do.** Fill both slots and stop emitting the axis-1
`REDUCTION.GROUPED_CONCAT` that used to follow. The neutral kernel states the
ratio as an operand rather than as an attribute, so a backend that drops it
loses an operand rather than silently defaulting to one.

**What it does not change.** Amendment A6's ordering clause stands exactly as
written: a sparse index array is ascending and tail-padded, padding is never
executed and never counted. A19 does not relax it — it moves the obligation to
the producer that can actually satisfy it. `ATTENTION.SPARSE` still refuses an
index that interleaves padding or descends, and it should: after A19 such an
array can only come from a producer that failed to compact, and a malformed
index that names real KV rows is exactly the failure a consumer must not
absorb.

**Where the ordering comes from.** The released kernel is indifferent to it —
`kernel.sparse_attn` reads `topk_idxs` as a set of `-1`-or-row lanes — so
ascending order is OpenTallas's choice, not the model's, and it is made once,
here, by the operator that has all the pieces. The reference this operator
implements, `runtime/reference/selection.py::index_topk_indices`, already takes
`compression_ratio`, `start_position` and `offset`; the operator is a strict
subset of its own contract, and the join is the only thing it adds.

## 20. Amendment A20 — `ROUTE.INDEX_TOPK` without a score operand, and a frozen index-family registry

Wire format section 12.10 is normative; this section states what it means for an
operand row and what it obliges a backend to do.

| Subopcode | in0 | in1 | in2 | out0 | aux |
|---|---|---|---|---|---|
| `INDEX_TOPK`, ranked | scores `[span, C]` | window index `[span, W]` U32 | compression ratio `[1]` U32 | joined KV rows `[span, W + k]` U32 | `aux0` `k` selected, `aux1` mask mode, `aux2` context *symbol*, `aux3` position-base *symbol* |
| `INDEX_TOPK`, **dense** | `NO_ID` | window index `[span, W]` U32 | compression ratio `[1]` U32 | joined KV rows `[span, W + k]` U32 | `aux0` `k` **capacity**, `aux1..3` as above |

The two rows are one operator. The released model's two producers for the
compressed half of a sparse index — `Indexer.forward` and
`get_compress_topk_idxs` — count the same causal horizon on the same axis in
the same units, add the same `offset`, and meet at the same concatenation in
`Attention.forward`. One ranks the candidates that horizon admits and the other
takes all of them, so the dense family is the ranked one with `in0` removed.

**What an engine must do.** With `in0` absent:

* read the span from `out0` — the operator writes one row per query either way,
  so the dense form loses an operand and not a dimension;
* bound the candidate count by `aux0` rather than by the scored columns. It is
  the same statement in both forms: no more groups may be named than the
  compressed segment can hold. A context that completes more is a refusal, not
  a truncation;
* emit, for the query at absolute position `p`,
  `arange(0, min((p + 1) / r, candidates))` rebased by `span + W`, in ascending
  group order.

Everything after the selection is A19 unchanged: rebase, join to the window
block, compact away the padding, sort ascending, tail-pad to `W + k`.

**`aux0` is read the same way in both rows.** `NO_ID` derives it as the output's
last extent minus `W`, which is the compressed segment's own width, so a dense
operator may state its capacity or leave the output to state it. A19's caution
still applies in both rows and is the one that bites: `aux0` is the segment,
never the operand, so a backend that copies the output's last extent into it
declares `W + k` where `k` belongs and is refused.

**How a neutral kernel says a slot is empty.** The `absent_operands` attribute
names the ABI input slots the kernel leaves `NO_ID`. It is the static
counterpart of `operand_present_predicate`: one says an operand is present under
a condition, the other says it is not there at all. Operands are placed **either
side** of the hole and never packed down, so the window block stays in `in1` and
the ratio in `in2` — the same rule `VECTOR.COMPRESS` sub-case 2 already needed
for its empty `in1`, now stated per kernel in the shared contract instead of per
kind in each backend. Which slots a kind may leave empty is frozen in
`compiler/ir/v3/lowering.py::OPTIONAL_INPUT_SLOTS`; a kind absent from that
table may not declare the attribute at all.

**An index family is refused where it is not implemented.** `index_family` named
which released helper a kernel reproduces and nothing read it, which is exactly
how twenty layers came to declare `causal_compressed_dense` while lowering to an
operator that emits a sliding-window position list. Every index that
substitution named was a legal KV row, so nothing downstream could refuse it.
The families each operator produces are therefore a frozen registry,
`compiler/ir/v3/lowering.py::INDEX_FAMILIES`, and an unknown one is refused at
neutral admission — one rule both backends inherit, rather than a rule each
backend has to remember. `ROUTE.WINDOW_INDEX` produces `causal_circular_window`;
that is the list.

The rule's first catch was not the case it was written for.
`causal_window_then_current_draft`, DSpark's draft window, is the released
`get_dspark_topk_idxs`: every draft query gets the same row,
`arange(0, min(window, p + 1))` then the draft block at `window + arange(block)`.
At window 128, block 5, position 200 that is KV rows 0..132; `WINDOW_INDEX`
emits 73..200 and five pads — 60 rows in common and none of the five draft
rows, which are the whole reason a draft block has an index of its own.

**What a backend must do.** Place operands with
`compiler/ir/v3/lowering.py::abi_input_slots`, which returns the IR input for
each ABI slot and `None` for a declared hole, and bind `NO_ID` where it returns
`None`. Stop treating `ROUTE.INDEX_TOPK`'s `in0` as mandatory — A19's rule that
every frozen operand row but `GROUPED_CONCAT`'s is mandatory no longer holds for
this slot. Drop any private per-kind table of empty operand slots for this kind
in favour of the kernel's own declaration, because a hole one backend places and
the other packs down is one operator with two spellings, which is what A17
abolished for the axis, A18 for the extent and A19 for the join.

**What it does not change.** A6's ordering clause, A19's three refusals, the
zero-candidate case, and the meaning of every other slot. A ranked
`INDEX_TOPK` written before this amendment carries a real descriptor ID in
`in0` and is the operator it always was.
