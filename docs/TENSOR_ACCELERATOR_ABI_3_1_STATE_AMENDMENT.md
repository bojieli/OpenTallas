# Withdrawn ABI 3.1 State and Compressed-Context Proposal

**Withdrawn proposal ID:** `TA-ABI3-STATE-3.1`

**Status:** withdrawn on 2026-09-03; non-normative historical design record

ABI 3.0 remains the sole required program and host ABI under `TA-ADR-003`. No
compiler, simulator, firmware, cycle-model, or RTL implementation may emit or
admit the descriptor minors, feature bits, policies, state classes, durable
roots, journals, or recovery behavior proposed below. The proposal is retained
only to preserve the reasoning that was reviewed before the scope was reduced
to uninterrupted, fail-stop RTL and architecture simulation.

Mutable model state is implemented as ordinary compiler-allocated ABI 3.0
memory objects and tensor views. Existing loops, predicates, DMA/engine
operations, and token-step fences carry the required addresses and ordering.
If a complex state transition cannot fit one existing operator record, the
compiler decomposes it into multiple existing operations and scratch views.
Simulator checkpointing, when useful for a long campaign, is host tooling and
is not an accelerator ABI or RTL persistence contract.

All normative terms in the remainder of this file describe the rejected
proposal and have no authority over ABI 3.0 or project acceptance.

**Proposed dependencies:** `TA-ADR-003`, `TA-ABI3-WIRE-1`, and
`TA-ABI3-OPCONV-1`.

**Proposed amendment:** the program/deployment/descriptor and device-micro-ISA portions of
ABI 3.0. It does not amend the independently versioned host queue ABI 3.0.

**Proposed supersession scope:** for a program header with `abi_major = 3` and
`abi_minor = 1`, and only for the affected descriptor versions and constructs
named here, this contract supersedes conflicting ABI 3.0 rules for feature and
capability registries, A18 tensor-view resolution, A21/A25 state commit and
staging derivation, the `VECTOR.COMPRESS` operand row, counter interpretation,
and post-commit replay. Program ABI 3.0 and descriptor type 1.0 retain their
historical byte and execution semantics. The governing ABI index, ADR, and
operator-conventions document still must cite this contract before a release is
declared frozen.

## 1. Historical proposal language and scope

Within the rejected proposal, the key words **MUST**, **MUST NOT**,
**REQUIRED**, **SHALL**, **SHALL NOT**, **SHOULD**, **SHOULD NOT**, and **MAY**
recorded the rules under review. They are retained verbatim for provenance and
are not normative project requirements.

This amendment defines:

- program ABI version 3.1 (`abi_major = 3`, `abi_minor = 1`) and its
  relationship to program ABI 3.0;
- versioned `STATE`, `PREDICATE`, `TENSOR_VIEW`, and `OPERATOR` descriptors;
- homogeneous, lockstep members within one transactional state resource;
- quotient-addressed compressed-cache publication;
- persistent compressor working windows;
- transaction-private prepared images and atomic generation-root publication;
- capability limits, feature negotiation, traps, counters, checkpointing, and
  recovery; and
- the evidence that must be regenerated before the four production
  deployments can be certified against this amendment.

The four production deployments in scope are Qwen HBM, Qwen ROM, DeepSeek HBM,
and DeepSeek ROM.

### 1.1 Terms

**Program ABI** is the version in the authenticated 256-byte program header.
It is distinct from the host submission/completion record ABI.

**Descriptor type version** is the `type_major` and `type_minor` in an
individual descriptor header.

**Member** is one logical state stream, such as one layer's KV cache, held in a
homogeneous grouped state resource.

**Grouped resource** is one `STATE 1.1` descriptor whose `member_count` is
greater than one. It has one architectural prepare/commit protocol, cursor,
and generation because every member is proven to advance in lockstep.

**Committed image** is the immutable state image selected by the authoritative
committed generation root when a transaction begins.

**Working image** is the transaction-private prepared image cloned or
copy-on-written from the committed image.

**Commit intent** is a validated request to publish a working image at
`CONTROL.COMPLETE`. Recording an intent does not make any byte committed.

**Root flip** is the single durable transition that makes all results of a
transaction authoritative.

**Inactive generation** is implementation-private persistence that can hold the
next complete image of a committed logical state object. It has no
program-visible address or descriptor ID and cannot be named by a tensor view.

**Transaction-generation root** is implementation-private authenticated
persistent metadata selecting one complete transaction outcome and the exact
node-local state generations that belong to it.

**Outcome journal** is implementation-private authenticated persistent metadata
that binds a validated request identity to its terminal completion and root. It
exists to distinguish an all-old abort from an all-new completion after reset
or completion loss; it is not a new program or host wire record.

## 2. Versioning and compatibility

This contract SHALL be an additive ABI 3.1 extension. It SHALL NOT be encoded
as an ABI 3.0 clarification. The new state policies, state classes, predicate
kind, tensor-view address modes, grouped-resource semantics, and stateful
compression transition change execution semantics and add registry values.

Any program using one or more constructs introduced by this document MUST set
the authenticated program header to:

```text
abi_major = 3
abi_minor = 1
```

A program with an ABI 3.0 header MUST NOT contain a descriptor with
`type_minor = 1`, a feature introduced by this amendment, or a nonzero value in
a field reserved by the corresponding 1.0 layout. A 3.1 implementation MUST
reject such a package as a hidden-minor, noncanonical package.

### 2.1 Required compatibility matrix

| Program or host record | ABI 3.0-only implementation | ABI 3.1-capable implementation |
|---|---|---|
| Program header 3.0, descriptors 1.0, only 3.0 constructs | Accept when all existing admission checks and the exact capability binding pass | Accept when all existing admission checks and a matching 3.0 compatibility-capability binding pass |
| Program header 3.1, affected descriptors 1.1, required 3.1 features | Reject at the program header before executing work | Accept only when every required feature, descriptor version, quantitative limit, digest, and semantic check passes |
| Program header 3.0 containing any 1.1 descriptor or 3.1 construct | Reject | Reject; a newer implementation MUST NOT legitimize a hidden minor |
| Program header 3.1 containing unaffected 1.0 descriptors | Reject at the program header | Accept; descriptor versions are selected per descriptor type |
| Host submission/completion ABI 3.0 record | Accept | Accept; this amendment does not alter host record layout or version |

An ABI 3.1-capable hardware and RTL family SHALL support genuine program 3.0
and program 3.1 admission. Support for program 3.0 does not permit
reinterpretation of a historical 1.0 descriptor using 1.1 semantics.

### 2.2 Consequence for the four shipped deployments

All four currently shipped deployments use grouped transactional state and
therefore SHALL be rebuilt as program ABI 3.1 deployments with `STATE 1.1`:

- Qwen HBM: one 36-member grouped KV resource;
- Qwen ROM: one 36-member grouped KV resource;
- DeepSeek HBM: 229 logical state members represented by 11 grouped resources;
- DeepSeek ROM: 229 logical state members represented by 10 grouped resources.

It is not conforming to keep Qwen's program header at 3.0 while adding
`member_count` and `member_stride_bytes`. Unmerging Qwen into 36 `STATE 1.0`
descriptors is also not a production fallback because the shared implementation
admits only 16 state-resource slots.

### 2.3 Host ABI remains 3.0

The submission queue, completion queue, and their record layouts are
independently versioned. They remain host ABI 3.0. A host ABI 3.0 submission
MAY select a program whose authenticated program header is ABI 3.1, subject to
the normal deployment, capability, and digest bindings.

### 2.4 Versioned descriptor dispatch

Descriptor layout and semantic dispatch MUST be keyed by the tuple:

```text
(descriptor_type, type_major, type_minor)
```

An implementation MUST NOT use one global type minor to select one payload
layout for all descriptors. In particular, raising a global supported minor to
one MUST NOT cause former reserved bytes in a 1.0 descriptor to acquire 1.1
meaning.

Supported descriptor minors and the compiler's emitted descriptor minors MUST
be separate settings. A 3.1 program MAY contain unaffected descriptor types at
1.0. The affected `STATE`, `PREDICATE`, `TENSOR_VIEW`, and `OPERATOR`
descriptors use 1.1 only when their 1.1 semantics are required.

### 2.5 Capability identity

Program admission continues to bind the exact capability digest. Adding ABI
3.1 features or limits changes that digest. An implementation that must admit
an old, otherwise conforming ABI 3.0 deployment unchanged MUST expose the old
capability profile as a compatibility identity. Otherwise the deployment MUST
be rebuilt against the ABI 3.1 capability, even when its program remains a
genuine 3.0 program.

## 3. ABI 3.1 features and capability limits

The feature registry gains:

| Bit | Name | Required when |
|---:|---|---|
| 13 | `QUOTIENT_STATE_COMMIT` | A `STATE 1.1` descriptor uses `QUOTIENT_APPEND`, or a predicate implements the matching quotient boundary test |
| 14 | `REQUEST_QUOTIENT_VIEWS` | A `TENSOR_VIEW 1.1` uses either quotient request-row mode |
| 15 | `STATEFUL_COMPRESS_TRANSITION` | An `OPERATOR 1.1` uses `VECTOR.COMPRESS` mode 3 |
| 16 | `GROUPED_STATE_MEMBERS` | Any `STATE 1.1` descriptor has `member_count > 1` |

The corrected DeepSeek deployments MUST require bits 13, 14, 15, and 16. The
corrected grouped Qwen deployments MUST require bit 16 and need not require
bits 13 through 15.

Capabilities supporting grouped state MUST declare:

| Limit | Meaning |
|---|---|
| `max_state_resources` | Maximum number of `STATE` descriptors in a deployment |
| `max_state_members_per_resource` | Maximum `member_count` in one `STATE 1.1` descriptor |
| `max_state_members_per_transaction` | Maximum semantic member count summed over every `STATE` descriptor declared by the deployment |

For this accounting, a `STATE 1.0` descriptor has semantic `member_count = 1`
and a `STATE 1.1` descriptor has its authenticated `member_count`. Every
declared state resource participates in the architectural transaction and MUST
be included in the sum. Admission and execution MUST NOT infer or accept a
narrower participant set from an entrypoint, predicate, phase, or observed
control-flow path. This is the ABI 3.1 participant-accounting rule; A22's slot
for every declared resource remains in force.

The shared production implementation profiles SHALL advertise at least:

```text
max_state_resources               = 16
max_state_members_per_resource    = 64
max_state_members_per_transaction = 256
```

Admission MUST reject a deployment exceeding any limit. The sum for
`max_state_members_per_transaction` MUST use checked arithmetic over the
complete declared state set.

## 4. Exact `STATE 1.1` wire layout

`STATE 1.1` retains the 128-byte state payload. Multi-byte integers use the
ABI's little-endian encoding. Offsets below are relative to the start of the
payload, not the descriptor header.

| Offset | Bytes | Type | Field | Normative meaning |
|---:|---:|---|---|---|
| 0 | 1 | U8 | `state_class` | State-class registry value |
| 1 | 1 | U8 | `commit_policy` | Commit-policy registry value |
| 2 | 1 | U8 | `element_dtype` | Element storage dtype |
| 3 | 1 | reserved | `reserved_0` | MUST be zero |
| 4 | 4 | U32 | `session_binding_id` | Session-binding selector; value zero means `CURRENT_SUBMISSION_SESSION` |
| 8 | 4 | U32 | `committed_object_id` | Logical committed memory object |
| 12 | 4 | U32 | `prepared_object_id` | Logical transaction-private prepared object |
| 16 | 8 | U64 | `row_bytes` | Bytes in one row of one member |
| 24 | 8 | U64 | `capacity_rows` | Row capacity of each member |
| 32 | 8 | U64 | `initial_cursor_rows` | Common initial per-member cursor; policy determines whether it is a row, ring slot, quotient row, or absolute token position |
| 40 | 4 | U32 | `generation_bits` | Width, 1 through 64 bits, of the resource generation |
| 44 | 4 | U32 | `counter_class_id` | State counter-class descriptor |
| 48 | 4 | U32 | `view_descriptor_id` | Canonical state view descriptor |
| 52 | 4 | U32 | `node_id` | Bound node identifier |
| 56 | 8 | U64 | `row_position_unit` | Positive quotient divisor for `QUOTIENT_APPEND`; zero otherwise |
| 64 | 32 | bytes | `initial_digest` | Digest of the complete initial grouped committed image |
| 96 | 4 | U32 | `member_count` | Number of homogeneous lockstep members |
| 100 | 4 | reserved | `reserved_1` | MUST be zero |
| 104 | 8 | U64 | `member_stride_bytes` | Byte distance between adjacent member bases |
| 112 | 16 | reserved | `reserved_2` | MUST be zero |

The descriptor header for this payload MUST declare `type_major = 1` and
`type_minor = 1`.

For `STATE 1.1`, `session_binding_id = 0` is the sole assigned value and means
`CURRENT_SUBMISSION_SESSION`. The state resource dynamically binds each
transaction to the `session_id` in that transaction's validated host
submission. The field is not a host session ID, does not name a descriptor, and
is not resolved through the descriptor table. Every nonzero value, including
`NO_ID`, is reserved and MUST fail admission until a later descriptor minor
assigns it. This selector permits one deployment to serve multiple isolated
runtime sessions without rebuilding its descriptor table.

For `generation_bits = G`, the resource generation is an unsigned integer in
`[0, 2^G - 1]`. Values of `G` outside `[1, 64]` fail descriptor admission. A
transaction that would advance a resource at `2^G - 1` MUST fail with
`STATE_TRANSACTION` before root publication; generation never wraps. The host
completion's U64 committed-state-generation field carries the zero-extended
authoritative transaction-generation-root value. All state resources and that
root in a newly created session begin at generation zero and, because every
declared resource participates and advances once per successful publication,
remain at that same numeric value. The root itself is U64 and MUST also refuse,
rather than wrap, when exhausted.

### 4.1 `STATE 1.0` isolation

For `STATE 1.0`, payload bytes 56 through 63 and 96 through 127 remain
reserved-zero. A `STATE 1.0` descriptor represents exactly one state member.
An implementation MUST NOT infer a member count from a memory object's size or
from view offsets.

New commit policies 3 and 4 and new state classes 6 and 7 are not legal in a
1.0 state descriptor. Unknown registry values fail admission.

## 5. Homogeneous member mapping

### 5.1 Canonical physical layout

`STATE 1.1` uses a dense member-major layout. Let:

```text
M = member_count
C = capacity_rows
B = row_bytes
S = member_stride_bytes
```

The following conditions are REQUIRED:

```text
M >= 1
C >= 1
B >= 1
S == C * B
committed_object.size_bytes == M * S
prepared_object.size_bytes  == M * S
```

Those equalities describe the two program-visible logical objects. An
implementation's inactive-generation persistence is separate private backing;
it MUST NOT be exposed by enlarging either object, placing a second generation
after `M * S`, or manufacturing an address that a descriptor can name.

Every multiplication and addition MUST be checked for U64 overflow before an
address or size is accepted.

For member `m`, row `r`, and byte `b`:

```text
0 <= m < M
0 <= r < C
0 <= b < B

address(object, m, r, b) =
    object.base_address + m * S + r * B + b
```

The committed and prepared objects MUST have compatible storage class,
alignment, node, ownership, and access permissions. Their logical writable
address ranges MUST not alias each other or an unrelated mutable object. An
implementation MAY share immutable physical pages internally as a copy-on-write
optimization, because that sharing is not visible through either logical
object. A future padded or row-fused representation requires a later descriptor
minor; it MUST NOT be encoded noncanonically in 1.1.

`capacity_rows` and `initial_cursor_rows` are declared once but apply equally
to every member. A grouped resource has one common cursor and generation. It
is illegal for member cursors or generations to diverge.

For an implementation that presents the dense object as a flat row array, the
canonical relationship is:

```text
flat_row(member, row) = member * capacity_rows + row
```

A dtype-element tensor-view expression MUST be exactly byte-equivalent to the
address equation above. Where element addressing is used,
`member_stride_bytes` MUST be representable without truncation or fractional
packed-element addressing.

### 5.2 Required admission proof

Admission MUST establish all of the following before work begins:

1. The arithmetic and object-size conditions in Section 5.1 hold for both
   committed and prepared objects.
2. `member_count` does not exceed the per-resource capability limit, and the
   sum of member counts does not exceed the per-transaction limit.
3. Every member-selecting tensor view computes the member base as exactly
   `member_index * member_stride_bytes` in bytes, or the exactly equivalent
   dtype-element expression.
4. Every possible member index is in `[0, member_count)` and every view remains
   within one member window unless it is the canonical whole-resource state
   view.
5. A view cannot cross from one member's rows into another member's rows.
6. Every member follows the same prepare, update, resolution, and publication
   cadence on every admitted control-flow path.
7. Any update predicate is member-independent and identical for all members.
8. No member can be committed, discarded, checkpointed, restored, or made
   authoritative independently of its group.
9. Each prepared grouped descriptor resolves exactly once before successful
   completion.
10. The complete working image exists before partial member writes, so an
    unwritten byte retains the corresponding committed byte.

If the verifier cannot prove the member-index range or lockstep behavior from
the authenticated descriptors and program, it MUST reject the deployment. It
MUST NOT rely on compiler intent that is absent from the authenticated package.

### 5.3 Merge eligibility

Logical states MAY share one `STATE 1.1` descriptor only when they agree on:

- state class;
- element dtype, packing, row width, and capacity;
- commit policy and `row_position_unit`;
- ring modulus, where applicable;
- update predicate and update cadence;
- phase set;
- session, node, and owner binding;
- generation width; and
- initialization, including zero versus negative-infinity padding.

Resources with compression ratios 4 and 128 MUST NOT be merged. Resources with
different reset behavior or different prefill/decode participation MUST NOT be
merged. A compiler unable to form a legal group MAY emit multiple groups, but
the resulting deployment still must fit `max_state_resources`.

## 6. State classes and commit policies

### 6.1 State-class registry

The complete registry through ABI 3.1 is:

| Value | Name | Availability |
|---:|---|---|
| 0 | `KV_CACHE` | 1.0 and 1.1 |
| 1 | `COMPRESSED_KV` | 1.0 and 1.1 |
| 2 | `TOKEN_RING` | 1.0 and 1.1 |
| 3 | `POSITION_CURSOR` | 1.0 and 1.1 |
| 4 | `ROUTE_HISTORY` | 1.0 and 1.1 |
| 5 | `SCRATCH` | 1.0 and 1.1 |
| 6 | `COMPRESSOR_WINDOW` | 1.1 only |
| 7 | `KV_RING` | 1.1 only |

New 1.1 emission MUST use the exact class. A genuine 1.0 compatibility path
MAY continue to recognize its previously admitted aliases, but an alias MUST
NOT be used to evade the program-minor or feature requirements of this
amendment.

### 6.2 Commit-policy registry

| Value | Name | Per-member rows published | Cursor transition |
|---:|---|---|---|
| 0 | `REQUEST_SPAN` | `SPAN_TOKENS` | `cursor += SPAN_TOKENS` |
| 1 | `UNSTAGED` | 0 | unchanged |
| 2 | `SATURATING` | `min(SPAN_TOKENS, capacity_rows)` ring rows | `(cursor + SPAN_TOKENS) mod capacity_rows` |
| 3 | `QUOTIENT_APPEND` | `floor(P1/D) - floor(P0/D)` | `cursor = floor(P1/D)` |
| 4 | `FULL_IMAGE` | `capacity_rows` | `cursor = P1` |

Policies 0, 1, 2, and 4 require `row_position_unit == 0`. Policy 3 requires
`row_position_unit >= 1`. Unknown policies fail admission.

`COMPRESSOR_WINDOW` MUST use `FULL_IMAGE`. `KV_RING` MUST use `SATURATING`.
The corrected DeepSeek compressed caches use `COMPRESSED_KV` with
`QUOTIENT_APPEND`.

Let `S = SPAN_TOKENS` for one coherent request interval `[P0, P1)`. The
following policy checks are REQUIRED:

- `REQUEST_SPAN` requires `S > 0`, `P1 = P0 + S`, common cursor `P0`, and
  `P1 <= capacity_rows`.
- `SATURATING` requires `S > 0`, `P1 = P0 + S`, and common cursor
  `P0 mod capacity_rows`; its new cursor is `P1 mod capacity_rows`.
- `UNSTAGED` permits zero published rows, closes the prepare, and leaves the
  cursor unchanged.
- `QUOTIENT_APPEND` follows the checks in Section 7 and permits zero published
  rows.
- `FULL_IMAGE` requires `0 <= P0 < P1`, `P1 = P0 + S`,
  `P1 = CONTEXT_LENGTH`, and common cursor `P0`; absolute token position is not
  bounded by `capacity_rows`.

A non-positive request span where a policy requires a positive one, or a stale
or gapped cursor, is a state-transaction fault. Exceeding a non-ring row
capacity is a capability/resource fault.

Every successfully published commit policy closes its open prepare and
advances the grouped resource generation exactly once, including `UNSTAGED`
and a zero-row `QUOTIENT_APPEND`. No cursor, generation, or byte transition is
authoritative before the transaction root flips.

### 6.3 Publication over members

For every commit run `(source_row, destination_row, count)` and every member
`m`, the implementation SHALL publish:

```text
source_offset = m * member_stride_bytes
              + source_row * row_bytes

destination_offset = m * member_stride_bytes
                   + destination_row * row_bytes

source = prepared_object.base_address + source_offset
bytes  = count * row_bytes
```

`destination_offset` is an offset in the next logical image of
`committed_object_id`, not a program-visible address. The state controller
copies `bytes` from `source` into implementation-private inactive-generation
backing selected by `(state_descriptor_id, next_resource_generation)` at that
offset, where `next_resource_generation` is the checked current generation plus
one. Using checked arithmetic, it MUST prove `source_offset + bytes` and
`destination_offset + bytes` are at most `M * member_stride_bytes`, and MUST
preserve every destination byte outside the commit runs from the prior committed
generation. The private backing and its metadata are integrity- and
ownership-protected at least as strongly as the logical committed object.

`REQUEST_SPAN` publishes prepared rows starting at zero to committed rows
starting at the common cursor. `SATURATING` publishes the canonical one- or
two-run circular interval from the same prepared and committed ring slots.
`QUOTIENT_APPEND` publishes the same absolute quotient row indices on both
sides. `FULL_IMAGE` publishes rows `[0, capacity_rows)` on both sides.

No member publication is authoritative until the transaction root flips.

## 7. Quotient-addressed state

Let the request cover the half-open absolute token interval `[P0, P1)` and let
`D = row_position_unit`. Define:

```text
q0 = floor(P0 / D)
q1 = floor(P1 / D)
N  = q1 - q0
```

Before accepting a `QUOTIENT_APPEND` intent, the implementation MUST prove:

```text
0 <= P0 < P1
P1 == P0 + SPAN_TOKENS
P1 == CONTEXT_LENGTH
session.position == P0
resource.cursor == q0
q1 <= capacity_rows
```

The commit publishes prepared quotient rows `[q0, q1)` to committed rows
`[q0, q1)` for every member, then sets the common resource cursor to `q1`.

A stale, replayed, or gapped session/resource cursor is a state-transaction
fault. A quotient capacity overflow is a capability/resource fault.

### 7.1 Zero-group commits

`N == 0` is legal and expected for most one-token decodes. A zero-group
`QUOTIENT_APPEND` commit SHALL:

- publish no compressed-cache bytes for any member;
- add zero to committed-row and committed-byte counters;
- leave the quotient cursor unchanged because `q1 == q0`;
- close the open prepare;
- advance the grouped resource generation once when the transaction publishes;
  and
- participate in the same atomic root transition as every other resource.

The generic non-positive-row trap applies only where the request span itself
is required to be a positive row count. It MUST NOT reject a valid
`QUOTIENT_APPEND` with `N == 0`.

Compressed-cache `STATE.PREPARE` and `STATE.COMMIT` instructions MUST be
unconditional. Only instructions that consume or publish a newly completed
group use the quotient predicate. This keeps prepare resolution and resource
generations aligned on zero-group decodes.

### 7.2 Boundary values

The following values are exact:

| End position | `floor(end/4)` | `floor(end/128)` |
|---:|---:|---:|
| 200000 | 50000 | 1562 |
| 200256 | 50064 | 1564 |
| 262144 | 65536 | 2048 |

Following a 200000-token prompt:

- ratio 4 decodes starting at 200000, 200001, and 200002 complete no group;
  the decode starting at 200003 completes one group;
- ratio 128 first completes a group at start 200063 and next at start 200191.

For a one-token decode, a boundary at `P1 = kD` produces exactly group `k-1`
at quotient row `q0`. Every other one-token decode produces zero groups.

## 8. `FULL_IMAGE` compressor state

`FULL_IMAGE` is not a generic state escape hatch. The verifier MUST restrict it
to `COMPRESSOR_WINDOW` resources paired with the stateful `VECTOR.COMPRESS`
transition in Section 11.

The corrected deployments use it only for raw compressor state roles such as:

- `compressor_window_kv.*`;
- `compressor_window_score.*`;
- `index_compressor_window_kv.*`; and
- `index_compressor_window_score.*`.

These windows change on every transaction, including a decode that completes
no compressed group. `REQUEST_SPAN` is incorrect because tokens are not raw
window rows. `UNSTAGED` cannot preserve an update. `SATURATING` describes a
token-indexed modulo ring and does not describe the ratio-4 two-half
overlap/roll transition or its reset and padding rules.

For `FULL_IMAGE`, the working image begins as a complete copy-on-write image of
committed state, the entire logical image of every member is published
same-slot, and the cursor is an absolute next-token position rather than a row
count. The implementation MUST require `cursor == P0`, set the cursor to `P1`,
and MUST NOT compare absolute token position with raw-slot capacity.

### 8.1 Source lock, ratio binding, and logical shapes

The immutable transition profile is
`opentallas.deepseek_v4_compress_state_update.v2`, derived from upstream
revision `7872f01b1d1fe23eabc4c98b48bffcef5a386062`, model-source SHA-256
`c0c19e6c9fa439bac7fbb1c5bc1868232dfd5aa2f439a548d0e33dcc2a9edd3f`, and
inference-configuration SHA-256
`c90861f3d10a9e4ef5954f8f1a34c529d480da1c5799f84660028f4e38e14e71`.
The mathematical definition below is normative and immutable for this profile.
`runtime/reference/compression_state.py` is a conformance oracle for it, not a
mutable source of additional semantics; disagreement with these equations is a
release failure and MUST NOT be resolved by silently following the code.

Let `R` be the paired `OPERATOR 1.1` mode-3 `aux_id_1`. `R` MUST be exactly 4
or 128. A `COMPRESSOR_WINDOW/FULL_IMAGE` resource does not carry `R` in
`row_position_unit`, which remains zero; the resource obtains `R` only through
its authenticated object/view binding to that operator. Define:

```text
c = 2 if R == 4 else 1
P = c * R                         raw state slots: 8 or 128
W = c * H                         projected feature width
```

This profile requires `1 <= B <= B_capacity <= 4`, `1 <= H <= 512`,
`T = P1 - P0`, and `P1 <= 1,048,576`, additionally bounded by the admitted
capability. `input_view_0` MUST be one packed `FP32`
rank-4 logical view with resolved extents `[B,T,2,W]`. Plane 0 is projected KV
and plane 1 is projected score, exactly:

```text
XK[b,t,w] = input_view_0[b,t,0,w]
XS[b,t,w] = input_view_0[b,t,1,w]
```

`input_view_2` MUST be an `FP32` rank-2 APE view `A[p,w]` with extents `[R,W]`.
Both use otherwise ordinary `TENSOR_VIEW` stride and bounds legality; packing
the two input planes does not authorize an implicit relayout. All `XK`, `XS`,
and `A` elements MUST be finite binary32 values.

For each grouped state member, the prepared raw-KV `input_view_1` and raw-score
`input_view_3` expose `FP32` rank-3 logical arrays `K[b,s,w]` and `Z[b,s,w]`
with extents `[B_capacity,P,W]`. Physical state rows are slot-major: row `s` is
the concatenation of `[b,w]` in increasing `b`, then increasing `w`. Therefore
the canonical logical view has element strides `[W, B_capacity*W, 1]`, and each
paired `STATE` descriptor MUST have:

```text
capacity_rows = P
row_bytes     = B_capacity * W * 4
element_dtype = FP32
```

All products and view bounds are checked under the normal `TENSOR_VIEW` and
member-geometry rules.

Write `x (+32) y` for exact real addition of two finite binary32 inputs followed
by one round-to-nearest, ties-to-even binary32 rounding. A non-finite projected
input or APE value, or an addition that cannot produce the required finite
binary32 result, is a numeric fault. Define the APE-biased projected score:

```text
Y[b,t,w] = XS[b,t,w] (+32) A[t mod R,w]
```

All stateful operators, their two raw windows, quotient cache states,
quotient-mode views, boundary predicates, and group consumers in one transition
MUST bind the same `R`. In particular, the corresponding quotient state's
`row_position_unit`, each quotient view's semantic `extent_unit`, and the
predicate divisor MUST equal the operator's `aux_id_1`. A mismatch fails
admission.

The mode-3 outputs defined below are the exact pre-softmax pool operands. The
operator does not itself perform softmax pooling, normalization, RoPE, QDQ, or
compressed-cache publication. `PoolK` is written to `output_view_0` and `PoolZ`
to `output_view_1`; both are `FP32` rank-4 logical arrays whose produced extent
is `[B,N,P,H]`. Their backing descriptors are capacity views large enough for
the admitted maximum, while quotient-mode consumer views expose exactly the
produced `N` groups.

### 8.2 Fresh-session prefill transition

Prefill requires `P0 == 0`, `T = P1 > 0`, and a fresh session binding. Reuse of
the same session identity as an already initialized raw window fails before any
write. Define:

```text
Q = floor(T / R)
E = T mod R
C = Q * R
```

The transition first resets every slot of every active batch lane to binary32
positive zero for `K` and the exact binary32 negative-infinity encoding
`0xFF800000` for `Z`. It then emits exactly `Q` pool groups. For `R == 128`, for
`0 <= g < Q`, `0 <= p < R`, and `0 <= h < H`:

```text
PoolK[b,g,p,h] = XK[b,g*R+p,h]
PoolZ[b,g,p,h] = Y [b,g*R+p,h]
```

For overlapping `R == 4`, every pool group has `2R = 8` phases. For
`0 <= p < R` and `0 <= h < H`:

```text
PoolK[b,0,p,h] = +0.0f
PoolZ[b,0,p,h] = -infinity (0xFF800000)

PoolK[b,g,p,h] = XK[b,(g-1)*R+p,h]       for 1 <= g < Q
PoolZ[b,g,p,h] = Y [b,(g-1)*R+p,h]       for 1 <= g < Q

PoolK[b,g,R+p,h] = XK[b,g*R+p,H+h]       for 0 <= g < Q
PoolZ[b,g,R+p,h] = Y [b,g*R+p,H+h]       for 0 <= g < Q
```

After forming the pool operands, the active raw state is the reset image plus
only these assignments:

```text
R == 4 and C >= R:
    K[b,p,:] = XK[b,C-R+p,:]              for 0 <= p < R
    Z[b,p,:] = Y [b,C-R+p,:]

R == 4:
    K[b,R+p,:] = XK[b,C+p,:]              for 0 <= p < E
    Z[b,R+p,:] = Y [b,C+p,:]

R == 128:
    K[b,p,:] = XK[b,C+p,:]                for 0 <= p < E
    Z[b,p,:] = Y [b,C+p,:]
```

Thus a ratio-4 state retains the last complete projected group in its previous
half and the incomplete suffix in its current half; a ratio-128 state retains
only its incomplete suffix. Slots not assigned above remain at their exact
reset values. Inactive batch lanes remain bit-for-bit unchanged. A grouped
member not targeted by the current operator invocation retains its working
baseline until its ordered member invocation; before commit, every member of
the group MUST have undergone the same transition for the same request.

### 8.3 Decode transition and overlap roll

Decode requires `P0 > 0`, `T = P1 - P0 == 1`, an exact session-binding match,
and `cursor == P0`. Define:

```text
p = P0 mod R
d = R + p if R == 4 else p
complete = (P1 mod R) == 0
N = 1 if complete else 0
```

For every active batch lane, first perform:

```text
K[b,d,:] = XK[b,0,:]
Z[b,d,:] = XS[b,0,:] (+32) A[p,:]
```

If `complete` is false, the operator emits no pool group and makes no other raw
state change. If `complete` is true and `R == 128`, it emits the single group:

```text
PoolK[b,0,p,h] = K[b,p,h]
PoolZ[b,0,p,h] = Z[b,p,h]                 for 0 <= p < R, 0 <= h < H
```

If `complete` is true and `R == 4`, it first emits:

```text
PoolK[b,0,p,h]   = K[b,p,h]
PoolZ[b,0,p,h]   = Z[b,p,h]
PoolK[b,0,R+p,h] = K[b,R+p,H+h]
PoolZ[b,0,R+p,h] = Z[b,R+p,H+h]           for 0 <= p < R, 0 <= h < H
```

and only after capturing that pool group rolls the complete current half into
the previous half:

```text
K[b,p,:] = K[b,R+p,:]
Z[b,p,:] = Z[b,R+p,:]                     for 0 <= p < R
```

The current half is not cleared by the roll. Inactive batch lanes and bytes not
assigned by these equations remain bit-for-bit equal to the working image's
committed baseline. Every successful prefill or decode transition sets the
absolute cursor to `P1`; its raw-window state and any emitted pool operands
become authoritative only through the common transaction root.

## 9. `PREDICATE 1.1`

The predicate-kind registry gains:

```text
10 COMPARE_SYMBOL_QUOTIENT
```

This kind is legal only in a descriptor whose header declares
`type_major = 1`, `type_minor = 1`, beneath a program ABI 3.1 header.

It reuses the existing 64-byte predicate payload. The relevant encoding is:

| Payload offset | Field | Required value |
|---:|---|---|
| 0 | `predicate_kind` | 10 |
| 1 | `comparison` | Existing comparison registry value |
| 2 | `selector_kind` | `RUNTIME_SYMBOL` = 1 |
| 3 | reserved | 0 |
| 4 | `selector_index` | Left runtime-symbol ID |
| 8 | `immediate` | Positive U64 divisor `D` |
| 16 | `object_id` | `NO_ID` = `0xFFFFFFFF` |
| 20 | `element_index` | Right runtime-symbol ID |
| 24 | reserved through byte 63 | All zero |

Evaluation is:

```text
left  = floor(symbol[selector_index] / D)
right = floor(symbol[element_index] / D)
result = compare(left, right, comparison)
```

The compression-boundary predicate is encoded as:

```text
selector_index = POSITION_START = 1
element_index  = POSITION_END   = 2
comparison     = LT             = 2
immediate      = 4 or 128
```

No new runtime symbol is introduced. `immediate == 0`, a non-runtime selector,
a non-`NO_ID` object, or an unknown comparison is noncanonical and fails
admission.

## 10. `TENSOR_VIEW 1.1`

Payload byte 121, formerly reserved, becomes `request_row_mode`:

| Value | Name | Meaning |
|---:|---|---|
| 0 | `LEGACY_A18` | Existing ABI 3.0/A18 extent behavior |
| 1 | `QUOTIENT_DELTA_LOCAL` | Quotient delta determines extent; base remains local |
| 2 | `QUOTIENT_DELTA_ABSOLUTE` | Quotient delta determines extent; base advances to absolute quotient row `q0` |

Payload bytes 122 through 127 remain reserved-zero.
Modes 1 and 2 are legal only with descriptor `type_major = 1`,
`type_minor = 1`, beneath a program ABI 3.1 header. In `TENSOR_VIEW 1.0`, byte
121 remains reserved-zero and has no selectable mode semantics.

### 10.1 Version-scoped replacement of A18

For `request_row_mode = 0`, A18 remains unchanged, including its positive-only
clamp and term-that-walks-the-axis admission rule. For modes 1 and 2, the
resolution equations in this section replace A18's extent formula,
positive-only clamp, and requirement that a dynamic term walk `extent_axis`.
The verifier MUST require that no dynamic term walks the quotient axis and MUST
assign `q1 - q0` even when that value is zero. Dynamic terms on other axes
continue to use their existing rules. This override is selected only by a
`TENSOR_VIEW 1.1` descriptor beneath a program 3.1 header and MUST NOT alter the
resolution of any 1.0 view.

For modes 1 and 2, the canonical existing extent fields are:

| Payload offset | Field | Required value |
|---:|---|---|
| 108 | `extent_unit` | Positive divisor `D` |
| 112 | `extent_numerator` | Raw wire value 0 |
| 116 | `extent_bias` | 0 |
| 120 | `extent_axis` | Valid axis of the view |
| 121 | `request_row_mode` | 1 or 2 |

Raw `extent_numerator = 0` is REQUIRED because A18 defines raw zero as semantic
one and rejects literal wire one as noncanonical. Thus the semantic numerator
is one even though the wire field is zero.

Resolution is:

```text
D  = semantic extent_unit
q0 = floor(POSITION_START / D)
q1 = floor(POSITION_END / D)
resolved_dim[extent_axis] = q1 - q0
```

For `QUOTIENT_DELTA_LOCAL`, `element_offset` is unchanged. For
`QUOTIENT_DELTA_ABSOLUTE`:

```text
element_offset += q0 * stride[extent_axis]
```

Local pool, intermediate, and scatter-index views use mode 1. Prepared
compressed-cache destination views use mode 2. Existing committed-context
views MAY continue to use `CONTEXT_LENGTH / D` under their existing contract.

No edge mask, dynamic term, or other extent rule may independently clamp or
advance the same quotient axis. A zero resolved extent is valid, but every
instruction consuming a quotient-mode view MUST be guarded by the exact
matching `COMPARE_SYMBOL_QUOTIENT` predicate. `DMA.SCATTER` indices remain
local `0..N-1`; absolute destination positioning comes from mode 2.

## 11. `OPERATOR 1.1` stateful compression

The opcode remains `VECTOR.COMPRESS`, major/subopcode `0x30/0x08`.
`OPERATOR 1.1` defines the following mode:

```text
aux_id_0 = 3  # STATEFUL_COMPRESS_TRANSITION
aux_id_1 = ratio, 4 or 128
aux_id_2 = POSITION_START symbol ID, 1
aux_id_3 = POSITION_END symbol ID, 2
```

Mode 3 is legal only with descriptor `type_major = 1`, `type_minor = 1`,
beneath a program ABI 3.1 header.

For that exact version-and-mode tuple, the operand row below supersedes the
ABI 3.0 `VECTOR.COMPRESS` row in `TA-ABI3-OPCONV-1`. Modes 0 through 2 retain
their historical mappings and behavior; in particular, this amendment does not
reinterpret legacy mode 2's prefill-only transition.

The exact relevant payload slots are:

| Offset | Field | Binding |
|---:|---|---|
| 0 | `engine_family` | `VECTOR` = `0x30` |
| 1 | `engine_sub` | `COMPRESS` = `0x08` |
| 24 | `input_view_0` | Projected packed KV/score input |
| 28 | `input_view_1` | Prepared raw-KV window, `READ\|WRITE` |
| 32 | `input_view_2` | APE input |
| 36 | `input_view_3` | Prepared raw-score window, `READ\|WRITE` |
| 40 | `output_view_0` | Pool-KV backing |
| 44 | `output_view_1` | Pool-score backing |
| 48 | `aux_id_0` | 3 |
| 52 | `aux_id_1` | 4 or 128 |
| 56 | `aux_id_2` | 1 |
| 60 | `aux_id_3` | 2 |

This operator MUST execute unpredicated on every prefill and decode
transaction. It MUST update the prepared raw-KV and raw-score windows on every
execution. It emits pool output rows only for the `N` complete groups in the
request. `N == 0` is successful and still updates raw state.

Pool output descriptors are capacity views. Quotient-mode consumer views
expose only the active `N` rows. Pooling, normalization, RoPE, QDQ, compressed
cache scatter/append, and other group consumers MUST carry the exact quotient
predicate.

For this mode only, this is a version-scoped replacement of A21's exhaustive
staging-source list: deployment staging analysis MUST count `input_view_1` and
`input_view_3` as both sources and destinations in addition to ordinary
operator outputs and communication endpoints. Both view descriptors MUST grant
`READ` and `WRITE`, must resolve to transaction-private prepared
`COMPRESSOR_WINDOW` resources using `FULL_IMAGE`, and must be included in
producer/fence analysis. No other input slot becomes a destination. Builder and
verifier MUST derive and check this fact from the completed authenticated
descriptor table. Every paired window and consumer MUST declare the same ratio
under Section 8.1.

Legacy `aux_id_0 = 2` behavior remains a legacy prefill-only transition. It is
not legal for the corrected DeepSeek decode path.

## 12. Transactional working images and visibility

### 12.1 Resource state machine

Each participating state resource follows:

```text
IDLE -> PREPARED -> COMMIT_INTENT -> COMPLETE / root publication
                  \-> DISCARDED   -> COMPLETE retaining old root
```

`STATE.PREPARE` MUST create a transaction-private working image initialized
bit-for-bit from the authoritative committed generation. A physical full copy
is not required, but the observable result must be identical to one.

Views explicitly naming the prepared object access the calling transaction's
working image. They have read-your-writes behavior: a consumer ordered after a
producer can read rows newly staged in the same transaction. Views naming the
committed object continue to observe the old committed generation until the
root flips. No other session or transaction may observe the working image.

`STATE.COMMIT` validates and records a commit intent. It MUST NOT expose bytes,
advance the authoritative cursor or generation, or rebind committed views. It
freezes further writes to that resource, but its working image remains readable
by correctly ordered same-transaction consumers until completion.

`STATE.DISCARD` destroys the transaction's right to access the working image.
It leaves committed bytes, cursor, and generation unchanged.

A successful `CONTROL.COMPLETE` requires a commit intent for every declared
state resource. `STATE.DISCARD` is an abort/failure-path resolution: if any
resource is discarded, the transaction follows the all-old rule, publishes no
new transaction root, and cannot return `SUCCESS`. This is what preserves one
session-wide numeric generation across resources of different classes.

An implementation that reuses prepared backing storage MUST use a fresh clone,
copy-on-write map, or generation/epoch tags. Merely clearing an `open_prepare`
flag is not conforming because dirty bytes from an aborted transaction could
contaminate a retry.

### 12.2 Protocol errors

The following are state-transaction errors:

- preparing an already prepared resource;
- committing a resource with no open prepare;
- committing or discarding the same prepare more than once;
- writing a resource after commit intent or discard;
- completing while any prepare is unresolved;
- reading a discarded working image;
- using stale, replayed, or gapped state/session position; and
- causing members of one group to resolve differently.

Each prepared descriptor MUST resolve exactly once on every successful path.

## 13. Atomic validation and root publication

At `CONTROL.COMPLETE`, the implementation MUST perform the following logical
sequence before reporting success:

1. wait for and fence every producer of transaction-scoped data;
2. validate every state intent, member range, cursor transition, capacity
   bound, and generation transition;
3. verify that every prepare resolved exactly once;
4. make every node-local inactive state image and its metadata durable;
5. make the token result, session position, session generation, per-resource
   cursor/generation, counters, and transaction outcome durable; and
6. publish all of them through one authoritative transaction-generation root.

No node-local state image, member subset, cursor, token, or session position may
become authoritative before the transaction root. A sequential series of
visible per-resource commits is not conforming.

For a 32-node transaction, one node's failure before publication aborts the
entire transaction. The durable global root MUST identify a complete set of
node-local generations. Checkpoint and restore MUST follow that root rather
than select independently advanced node roots.

The inactive-generation map, node-local roots, global transaction-generation
root, and outcome journal are implementation-private persistence. They are not
ABI descriptors, memory objects, tensor-view addresses, or additions to the
host record layout. Their physical encoding MAY vary, but firmware MUST
authenticate their integrity and freshness and MUST reject a torn, replayed,
cross-session, cross-deployment, or mixed-node record. The durable metadata for
one outcome MUST bind at least:

- deployment ID and generation, capability digest, program digest, and
  descriptor-table digest;
- session ID, submitted and resulting session generations, transaction ID, and
  idempotency key;
- every participating state descriptor ID, its old and new generation and
  cursor, and the integrity identity of its complete inactive image;
- the complete ordered node-generation set for a global transaction;
- selected token, committed position, counters including sticky overflow, and
  the terminal completion fields; and
- a monotonically protected persistence epoch or equivalent anti-rollback
  value.

Firmware MUST validate the complete bound set before selecting a root. The
single durable selection of that authenticated root is the architectural root
flip; writing an image or journal body alone is not publication. A private
encoding change that can alter checkpoint/recovery interoperability requires a
firmware persistence-format version, but does not create a program-visible
address.

### 13.1 Failure boundary and retry

A failure before the durable root flip leaves all authoritative state old:

- all committed member bytes remain old;
- all resource cursors and generations remain old;
- session position and generation remain old; and
- no newly selected output token is authoritative.

Inactive bytes written before that failure may remain physically present but
MUST be unreachable and ignored by checkpoint, restore, and subsequent
transactions.

A failure after the durable root flip is a committed all-new transaction with
a lost or delayed completion. It MUST NOT be reported or recovered as an
aborted all-old transaction. Recovery and a retry using the same transaction
identity MUST return or replay the recorded committed outcome and MUST NOT
execute the model transition again.

For this replay, “the same transaction identity” means an exact match of the
original validated request's ABI version, host opcode, all semantic flags,
deployment ID and generation, session ID and submitted session generation,
request-descriptor ID, transaction ID, idempotency key, input and output window
identities and ranges, entrypoint, generation-policy ID, watchdog class,
deadline, and every other field that can affect execution or returned bytes.
Only the `RETRY` flag and consequently the record CRC may differ. Reserved and
constant framing fields remain canonical. A mismatch is not a replay and MUST
fail closed before work.

This lookup occurs before ordinary stale-session-generation rejection. It is
the sole exception to the ABI 3.0 rule that a retry requires a session
generation that has not advanced: a matching post-root request may carry the
original submitted generation because it performs no work and returns the
journaled terminal outcome. A pre-root retry still requires the session
generation to be unchanged. A post-root request not found in authenticated
retained outcome metadata MUST NOT be guessed committed or re-executed.
The authenticated outcome record MUST remain available for the lifetime of the
session and travel in its checkpoint; authenticated session destruction may
retire it.

This post-root rule is required to prevent duplicated compressed groups,
duplicated output tokens, and divergent session position.

## 14. Traps, counters, checkpoint, and recovery

### 14.1 Trap classification

The following classifications are REQUIRED:

| Condition | Trap class |
|---|---:|
| Unsupported program/descriptor version, hidden 1.1 construct under a 3.0 header | 1, `ADMISSION_OR_VERSION` |
| Malformed descriptor field, address overflow, illegal view/member range | 3, `DESCRIPTOR_OR_ADDRESS` |
| Capability-limit violation or quotient capacity overflow | 4, `CAPABILITY_OR_RESOURCE` |
| Duplicate prepare/resolution, missing prepare, unresolved prepare, stale/gapped/replayed cursor, generation overflow, write after resolution | 9, `STATE_TRANSACTION` |

Memory, engine, link, timeout, integrity, and internal faults retain their
existing trap classes. Any pre-root fault, regardless of its class, aborts the
complete transaction and invokes the all-old rule. A post-root completion loss
is recovered as a committed transaction, not converted into a state trap that
rolls back the root.

### 14.2 Counter semantics

The existing counter IDs and event names are retained. Their ABI 3.1 meaning is
a backward-compatible generalization: one counter row is one row of one
semantic state member. For a `STATE 1.0` descriptor, define semantic `M = 1`
regardless of how application data happens to be packed inside its logical
row; therefore every genuine 1.0 program produces exactly its historical
counter values. For a `STATE 1.1` descriptor, `M = member_count`. This rule does
not renumber an event or reinterpret a 1.0 descriptor. A mixed-version program
sums each descriptor's contribution using its own semantic `M`.

Let `R` be rows published per member and `B = row_bytes`. On successful root
publication, per-node data-volume counters SHALL add:

```text
state.rows_committed += M * R
state.bytes_written  += M * R * B
```

For the policies in this amendment:

```text
REQUEST_SPAN:    R = SPAN_TOKENS
UNSTAGED:        R = 0
SATURATING:      R = min(SPAN_TOKENS, capacity_rows)
QUOTIENT_APPEND: R = q1 - q0
FULL_IMAGE:      R = capacity_rows
```

Rows and bytes multiply again by node count when an aggregate cluster counter
represents physical work on all nodes. Arithmetic MUST be checked at the
counter width and preserve the existing sticky-overflow behavior.

Instruction/resource counters such as prepares, commit instructions, discards,
and applied commit intents count one grouped descriptor operation and MUST NOT
multiply by `member_count`. The grouped resource generation advances once on a
published commit, including an unstaged or zero-group commit. An implementation
that exposes a generation-transition counter counts that grouped transition
once.

`state.unstaged_commits` and `state.saturated_commits` count one grouped
descriptor commit. `state.rows_clipped` counts unpublished physical member
rows and adds:

```text
M * (SPAN_TOKENS - min(SPAN_TOKENS, capacity_rows))
```

`FULL_IMAGE` counters describe the logical image published even when an
implementation realizes publication as a pointer/root change. A pre-root abort
MUST NOT increment committed-row or committed-byte counters in the authoritative
transaction outcome.

### 14.3 Checkpoint and restore

A checkpoint MUST capture, through one authoritative root:

- the full committed image of every member of every grouped resource;
- each group's common cursor and generation;
- session position and generation;
- the committed output/result record needed for idempotent retry;
- counter state, including sticky overflow; and
- the transaction-outcome journal or equivalent idempotency metadata.

A checkpoint MUST NOT read an arbitrary prepared object or inactive generation.
Restore MUST select one complete committed root and restore all members and
metadata from that root. It MUST NOT combine state from different generations
or nodes.

Checkpoint firmware MUST first authenticate the selected root and every bound
image and outcome record. The checkpoint serializes the logical committed
member bytes and the architectural metadata listed above; it MUST NOT serialize
or expose an inactive-generation physical address, private root pointer, or
implementation-local journal address as an ABI identity. Restore may allocate
different private backing, but it MUST reconstruct and authenticate one
equivalent complete root before admitting a new transaction. Authentication,
anti-rollback, or version failure makes restore fail closed rather than select a
best-effort subset.

After restore, the quotient cursor and session position originate from the
same committed transaction. Therefore the next boundary group cannot be
omitted or duplicated. A durability test that checks only regenerated token
equality is insufficient; it MUST also inspect every member's committed image.

## 15. Non-normative implementation guidance and cost rationale

This section proposes mechanics. An implementation may use different mechanics
if it satisfies Sections 1 through 14 exactly.

### 15.1 Recommended grouped implementation

Retain the 16-entry state-resource CAM/slot file. Add per-slot member count and
stride metadata and a nested commit walker:

```text
for each commit intent:
    for member in 0 .. member_count-1:
        for each canonical policy run:
            copy or materialize that member's run in the inactive generation
```

A six-bit member index covers the proposed 64-member limit. Implementations may
publish a full-image COW root rather than physically recopy unchanged bytes, as
long as visibility and counters remain architectural.

### 15.2 Why unmerging is rejected

The current production geometry is:

| Deployment | Logical members | Grouped descriptors | Maximum members in one descriptor |
|---|---:|---:|---:|
| DeepSeek HBM | 229 | 11 | 23 |
| DeepSeek ROM | 229 | 10 | 43 |
| Qwen HBM | 36 | 1 | 36 |
| Qwen ROM | 36 | 1 | 36 |

Unmerging DeepSeek needs at least 229 state slots, or a practical power-of-two
depth of 256, versus 16 today. That is 14.31 times the exact slot count or 16
times at 256.

The current RTL slot arrays represent approximately 170 persistent bits plus a
pending record per slot. Including the pending record, the structural storage
estimate is approximately:

| Slot depth | Approximate register bits | Approximate bytes |
|---:|---:|---:|
| 16 | 3,808 | 476 |
| 229 | 55,418 | 6.77 KiB |
| 256 | 61,952 | 7.56 KiB |

This lower bound excludes the much larger CAM comparison, priority selection,
mux, fanout, timing, and working-image costs. By comparison, a U32 member count
plus U64 stride adds 96 bits per existing slot, or 1,536 bits/192 bytes over 16
slots, plus one six-bit walker index.

At the package level, unmerging would add 218 state records to DeepSeek HBM and
219 to DeepSeek ROM. With a 64-byte descriptor header and 128-byte state
payload, that is 41,856 and 42,048 bytes respectively. It also adds at least
436 or 438 prepare/commit instructions. Qwen would add 35 descriptors and at
least 70 prepare/commit instructions.

The larger problem is control flow: current layer loops select members through
dynamic affine offsets while instruction and view object IDs are static.
Unmerging would require broad loop unrolling or a new dynamic descriptor/object
selection ISA. Explicit member geometry fixes committed publication without
that sequencer expansion and does not increase the bytes a correct transaction
must make durable.

The existing Qwen finding is specifically a committed-image durability and
restart defect: only the leading member was being published. It does not, by
itself, prove that current in-process token numerics are wrong, because active
execution can read and write the prepared member windows. This is why closure
must inspect every committed member rather than rely on token equality alone.

## 16. Proposed implementation work packages

This section is non-normative as to code organization and mechanics. The order
is recommended because each package gives the next one a stable contract to
target.

1. **Freeze registries and codecs.** Add program minor 1, per-type descriptor
   layout dispatch, features 13 through 16, capability limits, all new enum
   values, and exact encode/decode/CRC/digest tests. Keep 1.0 codecs unchanged.
2. **Implement admission before execution.** Add header/descriptor downgrade
   checks, member/object arithmetic, merge homogeneity and lockstep proof,
   quotient/view/operator cross-binding, and the two member limits.
3. **Normalize compiler physical state.** Make HBM and ROM both emit per-member
   capacity, explicit member count and stride, exact state classes/policies,
   and program 3.1 headers. Preserve member-major affine loop offsets.
4. **Build transaction-private working images.** Introduce clone/COW and epoch
   isolation, explicit intent records, read-your-writes visibility, exact
   discard, and no public mutation before completion.
5. **Implement quotient and compressor semantics.** Add predicate evaluation,
   tensor-view modes, stateful `VECTOR.COMPRESS`, input-view staging discovery,
   zero-group handling, and differential reference checks.
6. **Implement atomic publication and recovery.** Materialize inactive grouped
   generations, add the durable global root and outcome journal, coordinate all
   32 nodes, and implement pre-/post-root recovery behavior.
7. **Update RTL and formal models.** Add version admission, member metadata and
   walker, policies 3/4, quotient datapaths, full-image intent handling,
   counter multiplication, and atomic-root interface properties.
8. **Close verification before refreshing claims.** Run the focused matrix in
   Section 17, then rebuild all four deployments and regenerate the stale
   evidence in Section 18.

An implementation branch may overlap work packages, but no new production
artifact should be promoted until packages 1 through 7 agree on the same wire
and transaction semantics.

## 17. Focused conformance and closure matrix

The required outcome in this matrix is normative. Test filenames, harness
structure, and whether a proof is dynamic or formal are implementation choices.

| Area | Required positive closure | Required negative/fault closure |
|---|---|---|
| Versioning | Genuine header 3.0/type 1.0 package runs on the dual-admission implementation; header 3.1 selectively uses affected 1.1 layouts | 3.0 header plus any 1.1 descriptor/new construct fails; 1.0 former-reserved fields remain rejected; unsupported minor fails before work |
| Wire identity | New fields round-trip with exact little-endian bytes, record CRC, descriptor-table digest, deployment digest, and program-header binding; session selector zero resolves independently for two runtime sessions | One-bit mutations in each new field, feature vector, or bound fail the appropriate integrity/admission check; reject nonzero `session_binding_id` and generation widths 0 and 65 |
| Member geometry | Unique sentinels survive prepare, update, commit, checkpoint, and restore for member counts 1, 20, 21, 23, 36, and 43 | Reject counts 0 and 65, total 257, stride mismatch, multiplication overflow, undersized/oversized objects, aliasing, out-of-range member selection, and a view crossing members |
| Lockstep proof | Every member follows the same update cadence and one grouped generation transition | Reject mismatched class, dtype, capacity, policy, divisor, ring modulus, phase set, predicate, initialization, session/node binding, or partial group resolution |
| Quotient arithmetic | Properties around `D-1`, `D`, `D+1`, 127/128/129, 2047/2048/2049/2051/2052, 200000, 200256, and 262144; a 256-decode horizon ends at cursors 50064 and 1564 | Reject zero divisor, stale/gapped/replayed cursor, inconsistent request symbols, and quotient capacity overflow |
| Zero-group decode | Raw compressor windows change; compressed-cache commit closes and advances generation with zero rows/bytes; no group consumer executes | Reject a missing/unresolved compressed-cache commit and any unpredicated quotient-view consumer |
| Boundary decode | Exactly one group is produced, written at row `q0`, committed for every member, and visible to ordered same-transaction consumers | Discard/retry and injected faults prove no duplicate or omitted group |
| Full image | Ratio-4 and ratio-128 state and pool operands match Sections 8.1 through 8.3 and the independent oracle across reset, prefill, nonboundary decode, boundary roll, one-round-RNE APE phase, and exact padding | Reject `FULL_IMAGE` on another state class, wrong raw capacity, mixed ratios, malformed packed input planes, wrong APE shape, or an operator not bound to both prepared read/write windows |
| Counters | Rows and bytes equal semantic `M * per_member_rows` and `* row_bytes`, then node multiplication where applicable; 1.0 uses `M = 1`; descriptor-operation counters remain one | Overflow is sticky; aborted work does not appear as committed rows/bytes; zero-group adds zero data volume; generation overflow is refused rather than wrapped |
| Working visibility | Prepared views see committed baseline plus ordered same-transaction writes; committed views remain old before root | Reused prepared storage after abort cannot reveal dirty bytes; read-after-discard and write-after-resolution trap |
| Atomic publication | Successful completion exposes all members, resources, token, position, counters, and all 32 nodes at one generation | Faults after prepare, state write, intent, each inactive member copy, and immediately before root flip are all-old; one-node failure aborts all nodes |
| Post-root recovery | Fault immediately after durable root flip recovers the all-new recorded result; an exactly matching original request is idempotent despite its submitted generation now being stale | Recovery must never rerun a post-root committed transition or classify it as aborted; changed transaction ID, idempotency key, session/deployment identity, entrypoint, policy, or window range fails closed |
| Qwen durability | All 36 layer-member images survive committed-image restart and subsequent execution | A member-erased or member-swapped checkpoint control is detected even if a short token sequence happens to match |
| Differential compression | Raw state and pool outputs match `runtime/reference/compression_state.py` for both ratios | Perturbed overlap, roll, padding, APE phase, or score initialization is detected |
| RTL/formal | Properties cover descriptor-minor gating, nested member walker, quotient calculation, zero-row commit, full-image publication, counters, and root atomicity | Prove no partial member/node publication and no transition from aborted inactive data to an authoritative root |

## 18. Stale evidence and required refresh

The ABI 3.1 descriptors, object geometry, capability digests, descriptor-table
digests, deployment bindings, and transaction semantics invalidate accelerator
evidence produced from the grouped ABI 3.0 packages. The following MUST be
regenerated after implementation stabilization:

- W6.3 DeepSeek HBM token capture;
- W6.4 DeepSeek ROM token capture;
- their derived ROM-versus-HBM comparison and context-gate records;
- all four W6.6 restart artifacts: Qwen HBM, Qwen ROM, DeepSeek HBM, and
  DeepSeek ROM;
- the Qwen W10 natural A and B captures and their natural-acceptance record;
- the live/in-progress HBM W10 stress capture and the pending ROM stress/check;
- P10.7 Qwen standard deployments, certificates, and preflight records; and
- every source-current deployment or RTL correlation artifact whose bound
  program, descriptor table, capability, or state-publication semantics
  changed.

The existing W10 natural captures may remain labelled as prior-head evidence;
they pass their original natural gate but do not prove this amendment. Qwen
W6.1/W6.2 records likewise remain historical rather than source-current.

W10.5's DeepSeek reference-oracle context ladder and W10.6's reference scenario
remain valid reference evidence because their mathematical oracle is not
changed. They do not prove the corrected accelerator path and MUST NOT be used
as substitutes for regenerated ABI 3.1 execution and restart evidence.

## 19. Architectural invariants

A conforming implementation and evidence set SHALL establish all of these
invariants:

1. No ABI 3.1 construct is accepted beneath an ABI 3.0 program header.
2. Every grouped resource has explicit, authenticated, per-member geometry.
3. A group has one lockstep cursor and generation, while all member bytes are
   actually published.
4. A zero-group decode updates raw compressor state without fabricating a
   compressed row or leaving a prepare unresolved.
5. Same-transaction prepared reads observe ordered staged writes, while public
   committed reads cannot observe them before the root.
6. Abort cannot contaminate retry through reused prepared backing storage.
7. Every failure before the root is all-old across every member and node.
8. Every failure after the root is recovered as all-new and idempotently
   completed.
9. Checkpoint and restore select one authoritative generation and preserve all
   members, cursors, generations, counters, and transaction outcome metadata.
10. All four production deployments and their claims are rebuilt from the
    finalized ABI 3.1 implementation rather than promoted from ABI 3.0
    evidence.
