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
