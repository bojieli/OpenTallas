# Tensor-accelerator ABI 3.0 frozen wire format

**Contract ID:** TA-ABI3-WIRE-1

**Status:** frozen by `TA-A3-ARCH-0`

**Version:** 3.0

**Issue date:** 2026-08-29

This document freezes the externally visible binary contract implied by
`TA-ADR-003`. It is normative for ABI 3.0 encoders, decoders, independent
checkers, firmware, functional and timing simulators, and RTL 3.0. Phase B may
express this contract as schemas and code, but may not reinterpret or renumber
it without a new architecture decision and major-version analysis.

## 1. Common encoding rules

- Multi-byte integers are unsigned little-endian unless a typed payload says
  otherwise.
- Records are naturally aligned. Reserved bytes and unassigned flag bits are
  zero and are checked before use.
- `NO_ID` is `0xffffffff`; ID zero is legal unless a typed registry excludes it.
- Byte sizes, offsets, addresses, work bounds, and transaction IDs are 64-bit.
- Deployment-local object, descriptor, event, entrypoint, predicate, schedule,
  counter-snapshot, and source-operation IDs are 32-bit.
- Record CRC is reflected CRC32C/Castagnoli with polynomial `0x82f63b78`,
  initial state `0xffffffff`, and final XOR `0xffffffff`.
- SHA-256 digests are 32 raw bytes in binary records and 64 lowercase
  hexadecimal characters in canonical JSON.
- A CRC field is treated as zero while its record CRC is calculated.
- Unknown major versions, mandatory feature bits, opcodes, descriptor types,
  nonzero reserved values, invalid lengths, or invalid CRCs fail before work is
  issued.

## 2. Device-program header

The program header is exactly 256 bytes and begins on a 256-byte boundary.
Instructions begin immediately after it.

| Offset | Size | Field | Rule |
|---:|---:|---|---|
| 0 | 8 | magic | ASCII `OTTA3PG\0` |
| 8 | 1 | ABI major | `3` |
| 9 | 1 | ABI minor | `0` |
| 10 | 2 | header bytes | `256` |
| 12 | 2 | instruction bytes | `32` |
| 14 | 2 | flags | all version-3.0 bits are currently zero |
| 16 | 4 | instruction count | nonzero and capability bounded |
| 20 | 4 | entrypoint count | nonzero and matches the entrypoint descriptor |
| 24 | 32 | required feature bits | 256-bit little-endian bit vector |
| 56 | 32 | deployment digest | SHA-256 of canonical deployment manifest |
| 88 | 32 | descriptor-table digest | SHA-256 of ordered descriptor records |
| 120 | 32 | topology/health digest | admitted physical topology and epoch |
| 152 | 32 | body digest | SHA-256 of all 32-byte instructions |
| 184 | 8 | maximum retired work | verifier-proved bound |
| 192 | 4 | watchdog class | capability-defined bounded class |
| 196 | 4 | entrypoint-table descriptor ID | typed descriptor reference |
| 200 | 4 | signature-metadata descriptor ID | `NO_ID` only for labeled public builds |
| 204 | 48 | reserved | zero |
| 252 | 4 | header CRC32C | bytes 0 through 251 |

Program-body SHA-256 and every instruction CRC must both pass. A signature
authenticates the release manifest that binds the program; it does not replace
either integrity check.

## 3. Device instruction

Every instruction is exactly 32 bytes.

| Offset | Size | Field | Rule |
|---:|---:|---|---|
| 0 | 1 | major opcode | registry in Section 4 |
| 1 | 1 | subopcode | legal only for its major opcode |
| 2 | 2 | flags | registry below; unassigned bits zero |
| 4 | 4 | predicate ID | `NO_ID` means unconditional |
| 8 | 4 | descriptor ID | typed engine/control descriptor |
| 12 | 4 | wait-set ID | `NO_ID` means no predecessor wait |
| 16 | 4 | signal-event ID | `NO_ID` means no event publication |
| 20 | 4 | control ID or branch target | opcode-defined; target is an instruction index |
| 24 | 4 | source-operation ID | neutral Kernel IR/debug mapping |
| 28 | 4 | instruction CRC32C | bytes 0 through 27 |

Instruction flags are:

| Bit | Name | Meaning |
|---:|---|---|
| 0 | `PREDICATED` | predicate ID is present and evaluated |
| 1 | `PREDICATE_INVERT` | invert the declared predicate result |
| 2 | `WAIT_ACQUIRE` | predecessor completion has acquire semantics |
| 3 | `SIGNAL_RELEASE` | writes publish before event signal |
| 4 | `TRANSACTION_SCOPED` | fault poisons the active transaction |
| 5 | `GLOBAL_SCOPE` | descriptor names a cluster/wafer participant set |
| 6 | `TRACE_BOUNDARY` | emit the versioned trace checkpoint |
| 7 | `OPTIONAL_FEATURE` | admission requires an authenticated alternative path |
| 8–15 | reserved | zero |

`PREDICATE_INVERT` without `PREDICATED`, scope flags inconsistent with the
descriptor, or an instruction-index target outside the authenticated body is
illegal.

## 4. Opcode registry

Engine-specific shapes, numeric contracts, storage, routes, and bounds live in
typed descriptors. The opcode does not name Qwen, DeepSeek, ROM, HBM, a model
layer, or a framework callback.

| Major | Family | Frozen subopcodes |
|---:|---|---|
| `0x00` | control | `NOP=0x00`, `BRANCH=0x01`, `LOOP_SETUP=0x02`, `LOOP_NEXT=0x03`, `WAIT=0x04`, `FENCE=0x05`, `ASSERT=0x06`, `COMPLETE=0x07`, `TRAP=0x08` |
| `0x10` | DMA | `TRANSFER=0x00`, `FILL=0x01`, `GATHER=0x02`, `SCATTER=0x03` |
| `0x20` | tensor | `MATMUL=0x00`, `GROUPED_MATMUL=0x01`, `ROUTED_MATMUL=0x02`, `EMBED_LOOKUP=0x03` |
| `0x30` | vector | `RMS_NORM=0x00`, `HEAD_RMS_NORM=0x01`, `ROPE=0x02`, `ADD=0x03`, `SILU_MUL=0x04`, `CONVERT=0x05`, `SCALE=0x06`, `SOFTMAX=0x07`, `COMPRESS=0x08`, `MHC=0x09`, `HADAMARD=0x0a`, `INDEX_SCORE=0x0b`, `SQRT_SOFTPLUS=0x0c` |
| `0x40` | attention | `DENSE=0x00`, `GQA=0x01`, `SPARSE=0x02` |
| `0x50` | route | `TOPK=0x00`, `BIASED_TOPK=0x01`, `WEIGHT_NORMALIZE=0x02`, `EXPERT_DISPATCH=0x03`, `INDEX_TOPK=0x04`, `HASH_ROUTE=0x05`, `WINDOW_INDEX=0x06` |
| `0x60` | reduction | `ORDERED_SUM=0x00`, `EXPERT_SUM=0x01`, `VOCAB_GATHER=0x02`, `GROUPED_CONCAT=0x03`, `PARTITION_SUM=0x04` |
| `0x70` | selection | `ARGMAX=0x00`, `TOKEN_APPEND=0x01`, `SAMPLE=0x02` |
| `0x80` | state | `READ=0x00`, `PREPARE=0x01`, `COMMIT=0x02`, `DISCARD=0x03`, `GENERATION_ADVANCE=0x04` |
| `0x90` | link | `SEND=0x00`, `RECEIVE=0x01`, `REMOTE_DMA=0x02`, `MULTICAST=0x03`, `GATHER=0x04`, `SCATTER=0x05`, `COLLECTIVE=0x06`, `BARRIER=0x07` |
| `0xa0` | observation | `COUNTER_SNAPSHOT=0x00`, `TRACE_CHECKPOINT=0x01` |
| `0xb0` | recovery | `POISON=0x00`, `ABORT=0x01`, `DRAIN=0x02` |

`SAMPLE` is optional in the initial capability. `ARGMAX`, `TOKEN_APPEND`, and
the control needed for first-EOS termination are mandatory. Link subopcodes
operate only over compiler-admitted topology and object descriptors; they do
not provide arbitrary packet injection.

## 5. Descriptor header and type registry

Every descriptor begins on a 64-byte boundary, has a total size that is a
positive multiple of 64 bytes, and begins with this 64-byte header:

| Offset | Size | Field | Rule |
|---:|---:|---|---|
| 0 | 4 | magic | ASCII `TA3D` |
| 4 | 2 | descriptor type | registry below |
| 6 | 1 | type major | `1` for initial type definitions |
| 7 | 1 | type minor | additive only |
| 8 | 4 | total record bytes | includes header and padding |
| 12 | 4 | flags | type-specific; unknown mandatory bits fail |
| 16 | 4 | primary object ID | type-specific or `NO_ID` |
| 20 | 4 | secondary object ID | type-specific or `NO_ID` |
| 24 | 4 | numeric-profile ID | `NO_ID` when not applicable |
| 28 | 4 | schedule ID | `NO_ID` when not applicable |
| 32 | 4 | access permissions | bit mask below |
| 36 | 4 | owner-scope ID | authenticated scope table |
| 40 | 4 | payload offset | `64` in version 3.0 |
| 44 | 4 | payload bytes | excludes zero padding |
| 48 | 4 | record CRC32C | entire record with this field zero |
| 52 | 12 | reserved | zero |

Descriptor types are `MEMORY_OBJECT=0x0001`, `TENSOR_VIEW=0x0002`,
`NUMERIC=0x0003`, `SCHEDULE=0x0004`, `TOPOLOGY=0x0005`,
`COMMUNICATION=0x0006`, `STATE=0x0007`, `EVENT_WAIT_SET=0x0008`,
`LOOP_CONTROL=0x0009`, `OPERATOR=0x000a`,
`GENERATION_POLICY=0x000b`, `COUNTER_CLASS=0x000c`,
`ENTRYPOINT_TABLE=0x000d`, `SIGNATURE_METADATA=0x000e`, and
`PREDICATE=0x000f`.

Access-permission bits are `READ=bit0`, `WRITE=bit1`, `EXECUTE=bit2`,
`STATE_PREPARE=bit3`, `STATE_COMMIT=bit4`, `REMOTE=bit5`,
`HOST_VISIBLE=bit6`, and `IMMUTABLE=bit7`. Bits 8 through 31 are reserved.
Conflicting permissions, such as writable immutable ROM, fail admission.

## 6. Host submission record

Submission rings contain fixed 128-byte records aligned to 128 bytes.

| Offset | Size | Field |
|---:|---:|---|
| 0 | 4 | magic, ASCII `TA3S` |
| 4 | 1 | ABI major, `3` |
| 5 | 1 | ABI minor, `0` |
| 6 | 1 | host opcode |
| 7 | 1 | flags |
| 8 | 2 | record bytes, `128` |
| 10 | 2 | reserved, zero |
| 12 | 4 | deployment ID |
| 16 | 4 | deployment generation |
| 20 | 4 | session ID or `NO_ID` |
| 24 | 4 | session generation or zero |
| 28 | 4 | request descriptor ID |
| 32 | 8 | transaction ID |
| 40 | 16 | idempotency key |
| 56 | 4 | input memory-window ID |
| 60 | 4 | output memory-window ID |
| 64 | 8 | input offset |
| 72 | 8 | input bytes |
| 80 | 8 | output offset |
| 88 | 8 | output capacity bytes |
| 96 | 4 | entrypoint ID |
| 100 | 4 | generation-policy descriptor ID |
| 104 | 4 | watchdog class |
| 108 | 4 | reserved, zero |
| 112 | 8 | deadline in device cycles; zero means class default |
| 120 | 4 | reserved, zero |
| 124 | 4 | record CRC32C |

Host opcodes are `QUERY_CAPABILITY=0x00`, `LOAD_DEPLOYMENT=0x01`,
`ACTIVATE_DEPLOYMENT=0x02`, `DEACTIVATE_DEPLOYMENT=0x03`,
`UNLOAD_DEPLOYMENT=0x04`, `CREATE_SESSION=0x10`, `GENERATE=0x11`,
`CHECKPOINT_SESSION=0x12`, `RESTORE_SESSION=0x13`,
`DESTROY_SESSION=0x14`, `QUIESCE=0x20`, `RESUME=0x21`,
`RESET=0x22`, and `DIAGNOSTICS=0x23`.

A DeepSeek cluster or wafer request is submitted once to one logical-device
queue. Internal node, reticle, tile, or layer launches are device-program work,
not host submissions.

## 7. Host completion record

Completion rings contain fixed 128-byte records aligned to 128 bytes.

| Offset | Size | Field |
|---:|---:|---|
| 0 | 4 | magic, ASCII `TA3C` |
| 4 | 1 | ABI major, `3` |
| 5 | 1 | ABI minor, `0` |
| 6 | 1 | completion status |
| 7 | 1 | flags |
| 8 | 2 | record bytes, `128` |
| 10 | 2 | trap class |
| 12 | 4 | deployment ID |
| 16 | 4 | deployment generation |
| 20 | 4 | session ID or `NO_ID` |
| 24 | 4 | session generation |
| 28 | 2 | engine-fault class |
| 30 | 2 | reserved, zero |
| 32 | 8 | transaction ID |
| 40 | 4 | committed token position |
| 44 | 4 | produced-token count |
| 48 | 8 | committed state generation |
| 56 | 8 | output bytes written |
| 64 | 4 | first-fault instruction index or `NO_ID` |
| 68 | 4 | fault descriptor ID or `NO_ID` |
| 72 | 4 | counter-snapshot ID or `NO_ID` |
| 76 | 4 | trace ID or `NO_ID` |
| 80 | 8 | completion timestamp in device cycles |
| 88 | 16 | echoed idempotency key |
| 104 | 4 | final selected token ID, `NO_ID` when none was produced |
| 108 | 1 | EOS reason |
| 109 | 3 | reserved, zero |
| 112 | 8 | retired work |
| 120 | 4 | reserved, zero |
| 124 | 4 | record CRC32C |

EOS reason is `NONE=0`, `OFFICIAL_EOS=1`, `MAX_NEW_TOKENS=2`,
`TERMINATED_BY_TRAP=3`, and `HOST_BOUND=4`. Retired work is the count the
microsequencer actually retired and is checked against the program header's
proved maximum.

Completion status is `SUCCESS=0`, `FAILED=1`, `ABORTED=2`, or
`RESET_RECOVERED=3`. `SUCCESS` requires a terminal state commit. A reset may use
`RESET_RECOVERED` only when persistent retirement metadata proves that exact
transaction committed; otherwise it returns `ABORTED`.

## 8. Trap, scope, topology, and ordering registries

Stable trap classes are:

| Value | Class |
|---:|---|
| 0 | none/success |
| 1 | admission or version |
| 2 | authentication or integrity |
| 3 | descriptor or address |
| 4 | capability or resource |
| 5 | illegal instruction or control flow |
| 6 | numeric or exceptional value |
| 7 | DMA, HBM, SRAM, or ROM |
| 8 | tensor, vector, attention, route, reduce, or selection engine |
| 9 | state transaction |
| 10 | timeout or watchdog |
| 11 | link or NoC |
| 12 | power, reset, or thermal |
| 13 | internal invariant |

Topology classes are `SINGLE_CHIP=0`, `CLUSTER_32=1`, and
`WAFER_LOGICAL_DEVICE=2`. Memory/event scopes are `ENGINE=0`, `SRAM_BANK=1`,
`HBM_WINDOW=2`, `STATE_RESOURCE=3`, `NODE=4`, `CLUSTER=5`, `RETICLE=6`,
`WAFER_DEVICE=7`, and `SYSTEM=8`. Ordering values are `NONE=0`, `ACQUIRE=1`,
`RELEASE=2`, `ACQUIRE_RELEASE=3`, and `SEQUENTIAL=4` within the declared scope.
They do not create implicit cache coherence.

## 9. Required feature bits

The program-header feature vector assigns:

| Bit | Feature |
|---:|---|
| 0 | host queue ABI |
| 1 | deployment/descriptor ABI |
| 2 | deterministic microsequencer |
| 3 | BF16 tensor execution |
| 4 | FP8 E4M3FN tensor execution |
| 5 | MXFP4 E2M1 with E8M0 scales |
| 6 | transactional mutable state |
| 7 | on-device argmax, token append, and EOS |
| 8 | inter-chip endpoint and explicit remote movement |
| 9 | wafer endpoint and distributed HBM locality |
| 10 | bounded integrity retry/replay |
| 11 | signed deployment and measured-boot security |
| 12 | data-bearing timing execution |

Unassigned bits are reserved. Qwen HBM still advertises bit 8 because the same
chip/netlist is used in the 32-node DeepSeek system, although a one-node Qwen
deployment does not require link instructions. Program requirements are
operation-derived: declaring a `STATE` descriptor requires bit 6, and declaring
a communication descriptor with nonzero integrity or replay requires bit 10.
A backend capability may advertise either compatibility feature without forcing
an otherwise unrelated program to require it.

## 10. Counter namespaces

Counter IDs are 32-bit. The high byte is a frozen group and the low 24 bits are
an immutable event ID assigned by the Phase-B registry: `0x01` instruction,
`0x02` engine/queue, `0x03` memory, `0x04` tensor, `0x05` vector/reduction,
`0x06` attention, `0x07` route/expert, `0x08` state, `0x09` selection/EOS,
`0x0a` communication/collective, `0x0b` fault/recovery, and `0x0c` latency.
All values are unsigned 64-bit saturating counters with sticky overflow.

Assigning a previously unused low-24-bit event in a minor version is additive.
Changing an assigned event definition or group is incompatible.

## 11. Frozen versus deferred decisions

Record sizes, layouts, enum values, checksum rules, ordering, state atomicity,
failure behavior, topology classes, host/device responsibility, and operation
families are frozen. SRAM size, HBM channel count, engine lane count, queue
depth, link width, physical topology realization, clock, voltage, tile/reticle
count, and performance values remain capability fields selected through
compiler legality and separate SKY130/ASAP7 characterization. A capability may
change those quantitative values without changing ABI semantics, but a program
must bind the exact capability and topology/health digests used to compile it.

## 12. Typed descriptor payloads

Section 5 freezes the descriptor header and the type registry. The typed
payloads are frozen here, under the header's own `type_major` / `type_minor`
fields. Every payload is a whole number of 64-byte units, so the header rule
"total size is a positive multiple of 64 bytes" holds by construction.

| Type | Payload bytes | Total record bytes |
|---|---:|---:|
| `MEMORY_OBJECT` | 64 | 128 |
| `TENSOR_VIEW` | 128 | 192 |
| `NUMERIC` | 64 | 128 |
| `SCHEDULE` | 64 | 128 |
| `TOPOLOGY` | 192 | 256 |
| `COMMUNICATION` | 128 | 192 |
| `STATE` | 128 | 192 |
| `EVENT_WAIT_SET` | 64 | 128 |
| `LOOP_CONTROL` | 64 | 128 |
| `OPERATOR` | 64 | 128 |
| `GENERATION_POLICY` | 64 | 128 |
| `COUNTER_CLASS` | 64 | 128 |
| `PREDICATE` | 64 | 128 |
| `SIGNATURE_METADATA` | 128 | 192 |
| `ENTRYPOINT_TABLE` | 16 + 16 per entry, padded | variable |

The normative field tables for each payload are published as machine-readable
layout records in `spec/abi3/descriptor_payloads.json`, generated from and
checked against the encoder in `runtime/abi3/descriptors.py`. A layout record
names every field's offset, size, kind and reserved status, and the generator
proves the fields are gap-free and naturally aligned.

### 12.1 Tensor-view dynamic index terms

A tensor view carries `dynamic_term_count` (0 through 4) terms. Each term is
`{ uint16 selector_kind, uint16 selector_index, uint32 element_stride }` and
contributes `selector_value * element_stride` elements to the view's element
offset. `selector_kind` is `LOOP_INDUCTION=0`, `RUNTIME_SYMBOL=1`, or
`CONSTANT=2`. For `LOOP_INDUCTION` the index is a loop-control descriptor ID;
for `RUNTIME_SYMBOL` it is a value from the registry in section 12.2.

### 12.2 Runtime-symbol registry

| Value | Symbol |
|---:|---|
| 0 | `SPAN_TOKENS` |
| 1 | `POSITION_START` |
| 2 | `POSITION_END` |
| 3 | `CONTEXT_LENGTH` |
| 4 | `PHASE` |
| 5 | `GENERATION_INDEX` |
| 6 | `MAX_NEW_TOKENS` |
| 7 | `BATCH` |
| 8 | `NODE_ID` |
| 9 | `NODE_COUNT` |
| 10 | `ACTIVE_EXPERT_COUNT` |
| 11 | `SPARSE_INDEX_COUNT` |
| 12 | `LAYER_COUNT` |
| 13 | `VOCABULARY_PARTITIONS` |
| 14 | `SPAN_LAST_INDEX` |

A loop bound and a predicate operand may name any of these. Unassigned values
are reserved.

### 12.6 Amendment A15 — a block scale may tile two axes

A `TENSOR_VIEW` gains `scale_block_rows` at payload offset 104, four bytes; the
reserved span shrinks from 24 bytes at 104 to 20 at 108.

Amendment A8 froze block-scale addressing as one E8M0 byte per
`scale_block_elements`, in the view's logical row-major order, addressed at
`element_offset // scale_block_elements`. That is a one-dimensional rule, and it
cannot describe the released DeepSeek-V4-Flash checkpoint. `layers.0.attn.wq_a`
is a `[1024, 4096]` fp8_e4m3fn weight with a 128-element block, so A8 demands
`1024 × 4096 / 128 = 32,768` scale codes. The checkpoint ships **256**, shaped
`[8, 32]`, which is `1024/128 × 4096/128`: the scales are 128 × 128 *tiles*, not
runs along a row. Block-scaled FP8 is normally laid out this way, and no rule
that addresses a single axis can express it.

So `scale_block_elements` is the block along the **last** axis, and
`scale_block_rows` is the block along the **leading** one. The scale index for
element `(row, col)` of a rank-2 view over `cols` columns is

```
scale_index = (row / scale_block_rows) * (cols / scale_block_elements)
            + (col / scale_block_elements)
```

with integer division, requiring last-axis stride 1,
`cols % scale_block_elements == 0` and `rows % scale_block_rows == 0`; anything
else fails closed, as before.

**A8 is the `scale_block_rows = 1` case of this rule, exactly.** Substituting 1
gives `row * (cols / scale_block_elements) + col / scale_block_elements`, which
is `element_offset // scale_block_elements` whenever the block divides the row —
which A8 already requires. So no existing program changes meaning, and reserved
bytes must be zero, so every view written before this amendment reads
`scale_block_rows = 0`, which is defined to mean 1. MXFP4's 32-element blocks
along the reduction axis stay one-dimensional and untouched.

The alternative was to materialise the 256 codes into 32,768 by repetition. That
would fabricate a layout the checkpoint does not have, and it would break the
zero-copy inverse proof over all 156 GB, which is one of the few things in this
program that is proved rather than argued. Describing the real layout is the
change that was needed.

### 12.7 Amendment A17 — a concatenation states the axis it joins

`REDUCTION.GROUPED_CONCAT` reads a **join axis** from `aux_id_0` of its OPERATOR
descriptor (payload offset 48, already u32, already assigned). `NO_ID` and `0`
both mean **axis 0**, which is the operator this has always been; `1` joins
rank-2 operands on their feature axis. No other value is defined.

With axis 1, *N* inputs of `[R, C_i]` produce `[R, sum(C_i)]`, and input *i*
occupies columns `[sum(C_<i), sum(C_<i) + C_i)`. The operand order is the input
slot order, so the column order is stated by the descriptor and not by a
backend's traversal.

Four things are **refused at admission**, not trapped inside an engine that has
already read operands:

- an `aux_id_0` outside `{0, 1, NO_ID}`;
- a join axis at or beyond an operand's rank;
- a feature join on an operand that is not rank 2; and
- a join whose **non-join extents disagree** — every operand, inputs and output
  alike, must state the same extent on every axis the join does not consume, and
  the output's joined extent must be the sum of the inputs'.

The third of those is a deliberate narrowing rather than an oversight. On a
rank-3 operand a feature join's block is not one contiguous run of the output,
so the destination window becomes a strided rectangle whose correctness depends
on the stride the *producer* chose; nothing in either released model needs it,
and A17 refuses a shape rather than compute one nobody has asked for. Widening
the rank later is additive in exactly the way this amendment is.

**Why the ABI needed this.** DeepSeek-V4-Flash's attention output projection is
`einsum("bsgd,grd->bsgr")`: block diagonal over *features*, eight groups, each
reading its own 4,096-column block of a `[tokens, 32768]` activation and writing
its own 1,024-column block of a `[tokens, 8192]` result. Stated as the graph it
is — eight contractions and a join — the join is on the feature axis, and
before this amendment ABI 3.0 had no operator that could perform one. That was
established by executing the expansion rather than by arguing about it: the
program reached zero arity faults, both backends emitted exactly the right
operand views, and the device then refused the result. An OPERATOR names four
input views, so eight blocks join as a tree — two joins of four and one of two
— and the first of those joins is where it stopped:

```text
GROUPED_CONCAT output view 725 dims (104, 4096) differ from the concatenation (416, 1024)
```

Four `[104, 1024]` blocks joined on axis 0 are `[416, 1024]`, and all eight are
`[832, 1024]`: group-major, where the `[104, 8192]` token-major row belongs.

**No strided output view repairs it.** Group *g* of token *t* begins at
`t * 8192 + g * 1024`, and a rank-2 view has one row stride: a view that walks
groups cannot also walk tokens. The remaining spelling is eight kernels writing
disjoint column ranges of one tensor, which is eight producers of one tensor —
forbidden by single assignment, and rightly.

**The gap was already open elsewhere, and the two lanes already disagreed about
it.** `main.layerNN.index_topk.concat` and `compressed_dense_indices.concat`
join a sliding-window index block to a compressed-index block on axis 1 and
predate the grouped projection entirely. The shared HBM/SRAM planner
re-expressed them as one `DMA.TRANSFER` per column window — and its own
independent checker then objected that the kernel never reached `REDUCTION.3` —
while the ROM backend emitted the frozen operator and the engine refused the
shape. Two lanes disagreeing about one operator is the divergence this ABI
exists to remove, so the amendment closes a defect that predates its motivating
case.

**Nothing on the wire changes.** `aux_id_0` is an assigned u32 field, not a
reserved byte, and `DeploymentBuilder.operator` fills an unnamed auxiliary slot
with `NO_ID`, so every `GROUPED_CONCAT` written before this amendment carries
`NO_ID` there and therefore means axis 0 — the behaviour it already had. A17
fixes the *interpretation* of an existing field for one subopcode, which is why
it is recorded here beside A13 rather than left in one implementation's engine.
It is also invisible to RTL 3.0: the microsequencer's operand walk reads
`input_view_0..3` and `output_view_0..1` at payload bytes 24 through 47
(`rtl/abi3/ot_a3_microsequencer.sv`, the `view_slot_id` multiplexer) and never
indexes past them, so no auxiliary slot has ever reached the sequencer's contact
surface.

The alternative was a new subopcode for a feature join. That would leave two
concatenations in the registry differing only in an axis, and it would not have
closed the two axis-one sites that were already emitting one operator on one
lane and a stream of transfers on the other. Naming the axis is the change that
was actually needed; a second operator is not.

### 12.8 Amendment A18 — an extent may be an affine function of a bound symbol

A `TENSOR_VIEW` gains four fields out of the span A15 left reserved:
`extent_unit` at payload offset 108, `extent_numerator` at 112 and
`extent_bias` at 116, each four bytes, and `extent_axis` at 120, one byte. The
reserved span shrinks from 20 bytes at 108 to 7 at 121.

`extent_axis` is the axis whose extent the request determines, and the other
three give the function that determines it. Writing `a` for the axis, `n` for
the numerator, `u` for the unit, `b` for the bias, and `d` for the
`bound_divisor` of a symbol-bounded loop whose induction value is `i` and whose
bound symbol resolves to `S`:

```
step   = n * d / u                     elements of a per whole iteration
tokens = S - i * d                     the symbol's units this iteration has
extent = n * tokens / u + b            elements of a this iteration has
dim[a] = extent if 0 < extent < dim[a] else dim[a]
```

A term of that loop walks axis `a` in blocks exactly when

```
term_stride == stride[a] * step
```

Both divisions floor, and `u` must divide `n * d`, or one iteration is not a
whole number of that axis's elements and the term walks nothing. The bias is
added **after** the division and is not part of `step`: it is a count the
operand carries whatever the request is, not one an iteration advances by,
which is what lets a selected decode join state
`128 + floor(context / ratio)` while the fixed circular-window base does not
advance with the context-derived suffix.

**A13 is the `axis = 0, n = 1, u = 1, b = 0` case of this rule, exactly.**
Substituting gives `step = d`, the test `term_stride == stride0 * d`,
`extent = tokens`, and `dim0 = tokens if 0 < tokens < dim0` — which is section
12.4 word for word, including its refinement that a term walking some *other*
axis contributes no bound at all. Reserved bytes must be zero, checked on both
encode and decode, so every view written before this amendment reads zero in
all four fields, and a zero numerator and a zero unit are both defined to mean
one. No existing program changes meaning and no byte of any existing program
moves.

That is verified rather than asserted, three times. All 53 pre-A18 RTL vector
cases resolve their 401 operand views to the same extents under the new rule as
under the old one, the mHC non-leading-axis case among them. The two
formulations were compared exhaustively over the parameter space section 12.4
already cites — divisors 1–8, extents 1–11, bounds 0–19 and iterations 0–5,
10,560 combinations, no disagreement. And on the released model the check is
stronger than either: the DeepSeek-V4-Flash ROM wafer deployment, lowered by a
backend that declares none of the four fields, produces byte-identical
descriptors and instructions with this amendment implemented and without it —
3,333 descriptors, 1,051 instructions, work bound 4,417,598 — and stops in the
same place, at the same 685 retired instructions.

#### What could not be expressed

Three released operands need this, and none of them is a special case of the
other two. Each was established by executing the lowering and reading the
engine's refusal, not by inspecting a shape.

**A request-dependent extent behind the batch.**
`VECTOR.COMPRESS` sub-case 2 forms its groups along `S` —
`groups = span // ratio` — and its overlap transform reaches across `G`
(`pool[:, 1:, :ratio] = groups[:, :-1, :, :head_dim]`), so the operand's
request-dependent extent must sit at **axis 1**. A13 clamps `dim0` only, and
the engine refused correctly:

```text
prefill failed: COMPRESS_STATE_UPDATE span 1 contains no complete group of 4;
the should-compress predicate is false and the operation must not be issued
```

Every alternative was tried and each failed on execution. `[T, 1, 2, W]` puts
the tokens in the batch and gives span 1. `[1, T_max, 2, W]` is not clamped at
all and reads 262,144 rows of zeros. Per-group dispatch loses the cross-group
overlap the transform *is*. A two-group sliding window needs a descending loop
and a negative offset at `g = 0`. `VECTOR.INDEX_SCORE` makes the same point
independently, which is what says this is a rule and not one operator: its row
is `in0 [B,S,Hd,D]`, `in1 [B,C,D]`, `in2 [B,S,Hd]`, `out0 [B,S,C]`, and the
engine requires `kv_batch == batch`, so under every assignment of `B` at least
one of `S` and `C` lands at a non-leading axis.

**An extent counted in groups rather than in the symbol's own units.** A13's
clamp is in the bound symbol's units, so a loop blocking 512 tokens over a
group axis of ratio 4 produced an extent four times too long. The *count* was
already expressible — a block loop's trip is `ceil(symbol / bound_divisor)` —
and only the *extent* was not.

**A phase selects one of two extents.**
`main.layerNN.attention_kv_view` does not join current KV to a duplicate
128-row window. The pinned source selects current rows in prefill and the
physical window in decode, then appends a valid compressed prefix when the
layer has one:

```text
prefill = S + floor(S / ratio)
decode  = 128 + floor(C / ratio)
```

At ratio zero those are `S` and fixed 128. A clamp can only shorten one
declared extent; it cannot choose two different input subsets or affine
functions. Before the phase rule was expressed, one false three-way join could
still pass an operand-sum check at its maximum and fail only at execution:

```text
prefill failed: GROUPED_CONCAT output view 678 dims (104, 512) differ from
the axis-0 concatenation (262272, 512)
```

This is an **axis-0** join, so it is not what A17 fixed; A17 names the axis a
join consumes, A18 states the extent one selected descriptor presents, and the
neutral `phase_inputs` rule selects which descriptor exists on the request's
ABI 3.0 control-flow path. The decode bias of 128 remains a genuine affine
term: `b` is not a refinement of `n` and `u`.

There is a mechanically available workaround — expressing the join as one
movement per row block with a symbol-offset destination window, exactly as the
all-gather already does for `NODE_ID`. It is refused here for the same reason
A17 refused it on axis 1: it is one operator with two spellings across two
backends, and a lane that emits transfers where the other emits `REDUCTION.3`
is the divergence this ABI exists to remove.

#### Why an affine function, and not eight more symbols

The DeepSeek exporter declares eight derived runtime symbols the frozen A5
registry cannot name: `span_groups_ratio4`, `span_groups_ratio128`,
`context_groups_ratio4`, `context_groups_ratio128`, `attention_rows_window`,
`attention_rows_ratio4`, `attention_rows_ratio128` and
`selected_rows_ratio128`. 704 released tensors lead with one of them, and every
one is presently presented at its declared maximum: `COMPRESS_POOL` at 65,536
groups, `INDEX_SCORE`'s key at 65,536 candidates, the attention `CONCAT`
summing 262,272 rows.

Assigning eight more registry values would have been additive, in the strict
sense A12 used. It is refused here for two reasons, and the first is the
document's own rule.

*The names are model-specific and section 4 forbids that.* `ratio4` and
`ratio128` are DeepSeek-V4-Flash's two compression ratios. Section 4 says the
frozen registries do not name Qwen, DeepSeek, ROM, HBM, a model layer or a
framework callback. A symbol called `span_groups_ratio128` breaks that where
the document is most explicit about it, and the next model's ratio would need a
ninth.

*The names were never the gap; the arithmetic was.* Every one of the eight is
`n * S / u + b` over a symbol the registry already has:

| declared symbol | as an affine function |
|---|---|
| `span_groups_ratio4` | `SPAN_TOKENS / 4` |
| `span_groups_ratio128` | `SPAN_TOKENS / 128` |
| `context_groups_ratio4` | `CONTEXT_LENGTH / 4` |
| `context_groups_ratio128` | `CONTEXT_LENGTH / 128` |
| `attention_rows_window` | `SPAN_TOKENS` (declared prefill form) |
| `attention_rows_ratio4` | `5 * SPAN_TOKENS / 4` (declared prefill form) |
| `attention_rows_ratio128` | `129 * SPAN_TOKENS / 128` (declared prefill form) |
| `selected_rows_ratio128` | `CONTEXT_LENGTH / 128 + 128` (retired by A20) |

Amendment A20 has since retired the eighth. `selected_rows_ratio128` sized the
feature axis of a join that no longer exists — the dense compressed index is one
`ROUTE.INDEX_TOPK` whose output is `[span, 128 + k]` for a constant `k` — so the
exporter declares seven derived symbols and the graph nine in all. The row is
kept above because A18's argument is about the *form*, and the form is what
carries the other seven.

The two with a numerator are exact rather than approximate:
`floor(5s/4) = s + floor(s/4)` because `5s/4 = s + s/4` and `s` is an integer,
and likewise for 129/128. That is what the numerator is for — it lets one
symbol state both a count of rows and a count of groups derived from those same
rows in prefill. Decode uses a separate context-derived descriptor with bias
128 on the selected ABI 3.0 branch.

**The boundary, stated rather than left to be discovered.** The form is exact
for an extent affine in **one** bound symbol. A compressed layer's selected KV
join in decode is `128 + CONTEXT_LENGTH / ratio`, still one symbol and therefore
expressible; but it needs different operands and coefficients from the same
join in prefill. Existing `PHASE_IS` predicates and forward `CONTROL.BRANCH`
instructions select those descriptors. No record or field changes, and no ABI
3.1 state machinery, are involved. A program whose prefill and decode share one
view descriptor still cannot state both layouts. The neutral graph therefore
names an ordered input subset per phase, and each backend derives that subset's
one-symbol extent before emitting the existing branches. If `phase_inputs` and
its binding are removed, the candidate union again becomes
`SPAN_TOKENS + 128 + CONTEXT_LENGTH / ratio`; both backends refuse that mixed
two-symbol join rather than approximate it. The compiler differential checks
the ratio-0, ratio-4 and ratio-128 descriptors in both phases, including
absolute decode position 200,000.

**An extent that floors to zero is not a clamp.** Three tokens contain no whole
group of four, so `extent` is zero at `b = 0` and `dim[a]` keeps its block.
That is deliberate: ABI 3.0 has no zero-extent view — the verifier refuses one
— so "the request has none of this axis" is a *predicate* question, and the
operator must omit that optional compressed operand rather than issue an empty
view. It is the same question the compressor's own should-compress predicate
asks. The base selected layout remains nonempty: current rows in prefill or the
fixed 128 physical rows in decode.

**One axis per view, deliberately.** A view names one request-dependent extent.
`INDEX_SCORE`'s output is `[B,S,C]` with two of them, and it is expressible
because placing the tokens in the batch — the placement the token-as-batch rule
already makes for this family — leaves `C` as the only axis the request moves.
Nothing in either released model needs two, and a second declaration is
additive in exactly the way this amendment is. This is the same deliberate
narrowing A17 made when it defined a feature join for rank-2 operands only.

#### Admission

Three rules keep the fields honest, all refusals rather than engine faults,
because a deployment whose operand can never be resolved should be refused
before it is activated:

- an `extent_axis` at or beyond the view's rank;
- an `extent_unit` or `extent_numerator` of exactly 1, which is a value the
  encoding does not assign — one is written as zero, so that a view not using
  the amendment is byte-identical to the same view written before it; and
- a view that declares any of the four fields and carries **no term that walks
  it**. Without that rule the operand silently keeps its declared maximum,
  which is the 65,536-candidate failure this amendment exists to remove, and a
  silent wrong extent is worse than a refusal.

The admission rule A13 already had generalises with the rest: `dim[a]` may not
exceed `step + b`, because iteration *i* covers exactly that many elements of
that axis and a view claiming more is claiming elements belonging to the next
iteration. With `a = 0, n = 1, u = 1, b = 0` that is section 12.4's `dim0 ≤ d`
unchanged, and its exhaustive result — 1,027 disagreements between the two
formulations, every one with `dim0 > bound_divisor` — carries over because the
substitution is an identity.

#### RTL 3.0

This is the first amendment since A13 that reaches the microsequencer. A14, A15
and A17 all touched bytes it never reads; this one does not.
`ot_a3_view_resolver.sv` read `dim0` at payload bits 223:192 and `stride0` at
415:384 and published one extent, `out_dim0` — dims and strides 1 through 5 were
dark, and so was everything above bit 831. A18 needs `dim[a]` and `stride[a]`
for a declared *a*, so the resolver gains a six-way mux over those two fields,
reads the four new fields at bits 895:864, 927:896, 959:928 and 967:960, and
publishes the axis beside the extent. The two divisions by `u` use one restoring
divider over a 64-bit numerator, the same structure `ot_a3_loop_stack.sv`
already runs for `bound_divisor`; a numerator and unit of one bypass it, so the
A13 path costs exactly the cycles it always did.

### 12.9 Amendment A19 — a sparse index is produced joined, rebased and compacted

`ROUTE.INDEX_TOPK` gains two operands out of the three input slots it left
empty. `input_view_1` is the **sliding-window index block** `[span, window]`
its result is joined to, and `input_view_2` is a one-element U32 view naming
the **compression ratio** of its candidate axis. `output_view_0` becomes the
joined array `[span, window + k]`, **compacted and ascending**, tail-padded
with `0xffffffff`. `NO_ID` in either slot is the operator this has always
been: no window segment, ratio one, no rebase.

With a compression ratio `r`, the candidate axis holds `context / r` groups,
group `g` completes at absolute position `r * (g + 1) - 1`, and a causal query
at absolute position `p` therefore sees

```
visible = (p + 1) / r        candidates, floored
row(g)  = phase_base + g     phase_base is S in prefill, window in decode
```

and the operator writes `sort(compact(window_row, rebased_selection))`.

**Why the ABI needed this.** This was three defects at one boundary, and every
one of them was read off the device rather than argued about. The ROM
deployment's `ROUTE.INDEX_TOPK` operator carried
`in = [scores, NO_ID, NO_ID, NO_ID]` and `aux = [512, 0, CONTEXT_LENGTH,
POSITION_START]`, its result was joined to a window block by a separate
`REDUCTION.GROUPED_CONCAT` on axis 1, and `ATTENTION.SPARSE` refused what
arrived:

```text
prefill failed: sparse index view 1425: query 0 interleaves padding with
selected rows; amendment A6 fixes padding as a trailing run
```

*The padding was interior.* A sliding window shorter than its 128 slots is
tail-padded inside its own block, so joining a second block behind it puts
padding in the middle of the row. That is the refusal above.

*The selection was not rebased.* The operator emitted columns of the score
view. Column 0 is compression group 0, which lives after the selected base
layout: at KV row `S` in prefill and row 128 in decode. Unrebased it named a
real but unrelated base row, so a bounds check alone could not refuse the wrong
answer.

*The causal horizon was counted in the wrong unit.* `aux_id_1 = 0` is
`MASK_CAUSAL`, and the engine's causal rule was `limit = base + row + 1`: one
new candidate per token. On a compressed axis a candidate is a group of `r`
tokens and one completes every `r` tokens. For the 104-token prompt that is 26
candidates where the operator offered up to 104, so the selection ranged over
78 groups the request does not have. This is the operative error in the failing
tile; the missing rebase is the one that would have been operative next.

**The contract was already written; only the engine had it wrong.** The
qualified reference this operator implements,
`runtime/reference/selection.py::index_topk_indices`, already takes
`compression_ratio`, `start_position` and `offset`, and already applies exactly
the mask above. The qualified consumer,
`runtime/reference/sparse_attention.py`, already accepts `-1` at **any** slot
with no ordering requirement, and counts `explicit_padding_slots` separately
from `implicit_tail_padding_lanes` — it *expects* padding that is not a
suffix. Both mirror the released model:
`inference/model.py::Attention.forward` concatenates the window and compressed
indices into one `sparse_attn` call, `inference/kernel.py::sparse_attn` reads
each slot as `idxs[i] != -1` with no order imposed, and `Indexer.forward`
returns `topk_idxs + offset` for `offset = kv.size(1) if start_pos == 0 else
win`. The rebase is in the producer in the released model too.

**One rule replaces the released model's two branches.** `Indexer.forward`
masks with `(s + 1) // ratio` when `start_pos == 0` and exposes its whole cache
otherwise. Substituting the absolute position `p = base + row` into A19's rule
gives `(row + 1) / r` at `base = 0`, which is the first branch, and
`(p + 1) / r = context / r`, every cached group, at a span of one — which is
the second. A tiled prefill, which the released implementation never performs
and neither branch describes, is the general case in between, and it is the
case OpenTallas actually runs.

**Nothing on the wire changes.** `input_view_1` and `input_view_2` are assigned
u32 fields at payload bytes 28 and 32, not reserved bytes, and
`DeploymentBuilder.operator` fills an unnamed operand slot with `NO_ID`, so
every `INDEX_TOPK` written before this amendment carries `NO_ID` in both and
therefore means the un-joined, ratio-one operator it already was. This is the
same class of change as A6, which gave `ATTENTION.SPARSE` a fourth operand
without moving a byte, and as A17, which fixed the interpretation of an
assigned field for one subopcode.

**Why an input slot and not an auxiliary one.** `aux_id_0` through `aux_id_3`
are all spent on this operator — `k`, the mask mode, the context symbol and the
position-base symbol — and an operator has exactly four. The compression ratio
is a scalar, so the temptation is to assign it an undefined *value* of
`aux_id_1` the way A12 assigned an unused symbol number. That is refused here:
`aux_id_1` means "mask mode" for four subopcodes across two engine families,
and a field that means one thing for `WINDOW_INDEX` and two things for
`INDEX_TOPK` is the divergence this document exists to remove. An input view is
the channel an operator has for a value it did not compute, and the ratio is
pinned per layer, so it reads a one-element mask-programmed constant declared
by the `constant_u32_v1` generator.

**Why A6 keeps tail compaction but not numerical sorting.** A19 removes padding
holes before publishing its joined result. The consumer checks that padding is
a suffix and still checks every selected value against the resolved KV rows.
It does not require numerical monotonicity: a direct decode `WINDOW_INDEX`
consumer must preserve chronological physical ring order such as `1..127, 0`,
and selected-slot order reaches the block-64 numeric contract. A19 continues to
choose a sorted canonical order for its own joined output.

**What a backend must do.** Emit the window block into `input_view_1` and the
ratio constant into `input_view_2`, and stop emitting the axis-1
`GROUPED_CONCAT` behind them. A join that A19 folds into its producer is one
operator with two spellings the moment one backend folds it and the other does
not, which is what A17 abolished for the axis and A18 for the extent.

**And the consumer bounds the row space, not the token count.** A19 defines
what a sparse index names, so it has to say what checks it. `ATTENTION.SPARSE`
read `aux_id_2` as a count of KV rows, truncated its fused KV operand to that
many, and refused every index beyond it. On a joined operand that is wrong in
both directions: the operand had 258 rows for a 104-token request and lost 154
of them, and the first correctly rebased index was refused —

```text
prefill failed: sparse index view 1419: query 3 selects KV row 232, outside
the 104 valid rows
```

That capture used the obsolete duplicate-window layout and is retained only as
the discovery trace. The corrected fused KV operand is a **phase-selected row
space**: current then compressed in prefill, physical window then compressed in
decode. No token count is its physical row count. Its own resolved extent does
bound rows, while `aux_id_2` bounds the absolute *positions* used by the causal
base check. `DENSE` and `GQA` are untouched: their KV view is indexed by
position, so for them the two are the same number.

**Zero candidates is not a fault.** A context shorter than one compression
group has completed none, and the released model runs that layer as pure
sliding-window attention: `get_compress_topk_idxs` returns a `[seqlen, 0]`
block and the concatenation behind it is a no-op. So `context / r == 0` selects
nothing and the operator emits the window block alone. That is what keeps A19's
operator *unconditional* where the two kernels it replaces were not: the
selection used to be predicated off and the join used to name an absent
operand, and now the only thing that vanishes is a score operand the operator
already knows how to have none of. It is refused only when there is also no
window block, because then the operator has nothing to emit and an empty
softmax has no value.

**Refusals.** Three, before the operator reads a score:

- an `input_view_1` whose leading extent is not the score view's span;
- an `input_view_2` that is not a single U32 element; and
- an `output_view_0` narrower than `window + k`.

`aux_id_0` is the **selection** width, not the operand width. The output is the
join, so its last extent is `window + k` and a backend that reads `k` off the
output declares `640` where `512` belongs — measured, on the first run of this
amendment:

```text
prefill failed: ROUTE.INDEX_TOPK selects 640 positions and joins a 128-slot
window into 640 slots
```

**How far it gets.** With A19 the DeepSeek-V4-Flash ROM wafer deployment
executes the whole ratio-4 sparse path of `TA-DS-CHAT-1` — the indexer's
selection, the rebase, the join and the sparse attention behind it — and runs
514 seconds against the 343 the A6 refusal used to reach. It stops in a
different layer, on a different question:

```text
prefill failed: COMPRESS_STATE_UPDATE span 104 contains no complete group of
128; the should-compress predicate is false and the operation must not be
issued
```

That is section 12.8's own trap, at ratio 128 instead of ratio 4: a 104-token
request completes no whole group of 128, so the compressed half of that layer
does not exist for this request and the released model runs it as pure
sliding-window attention. The neutral graph states the predicate; nothing on
either lane yet acts on one. That is the next amendment's subject, not this
one's.

**RTL 3.0.** Not involved, for the same reason A17 was not, and the proof is
the same line. `ot_a3_microsequencer.sv`'s operand walk is a six-way multiplexer
over `op_payload[223:192]` through `op_payload[383:352]` — `input_view_0..3` and
`output_view_0..1`, payload bytes 24 through 47 — selected by a slot counter and
not by the subopcode, and every value above bit 383 is dark to it. A19 puts a
real descriptor ID where an operator previously carried `NO_ID` in a slot the
sequencer already walks, and changes nothing about how it walks it. The
microsequencer has never read `aux_id_0..3` at bits 511:384 either, which is
why the alternative above would also have been invisible to it — invisibility to
the sequencer is not the argument for a change, only a bound on its cost.

### 12.10 Amendment A20 — a dense index is a selection with the selection removed

`ROUTE.INDEX_TOPK`'s `input_view_0` becomes **optional**. Present, it is the
index scores and the operator takes the top `aux_id_0` of the candidates the
causal rule admits, which is the operator A19 defines. `NO_ID`, and the operator
takes **every** candidate that rule admits, in ascending group order. Nothing
else moves.

| slot | ranked (A19) | dense (A20) |
|---|---|---|
| `in0` | index scores `[span, C]` | **`NO_ID`** |
| `in1` | window block `[span, W]` U32, tail-padded | unchanged |
| `in2` | compression ratio, one U32 element | unchanged |
| `out0` | `[span, W + k]` U32, compacted, ascending, `0xffffffff`-padded | unchanged |
| `aux0` | `k`, the selection width | `k`, the **capacity** of the compressed segment |
| `aux1..3` | mask mode, context symbol, position-base symbol | unchanged |

For the query at absolute position `p = base + row`, with ratio `r`:

```
sort((window_row minus padding) ++
     (arange(0, min((p + 1) / r, candidates)) + phase_base))
phase_base = S in prefill, W in decode
```

**No opcode is added.** The dense family was being lowered to
`ROUTE.WINDOW_INDEX`, which emits the causal window in source order: absolute
current-request rows in prefill and physical circular slots in decode. Neither
representation enumerates completed compression groups, and the ROM backend
refused to build the graph rather than emit it:

```text
kernel 'main.layer03.compressed_dense_indices.enumerate' declares index family
'causal_compressed_dense', which this backend does not implement.
```

That refusal was right and the repair is not a seventh route subopcode, because
the operator that *does* produce the family is already next door and already
does every hard part of it.

**The released implementation says they are one function.** In the pinned
snapshot `inference/model.py`, SHA-256
`c0c19e6c9fa439bac7fbb1c5bc1868232dfd5aa2f439a548d0e33dcc2a9edd3f`,
`Attention.forward` chooses between exactly two producers for the compressed
half of its index and concatenates either one to the same window block:

```python
compress_topk_idxs = self.indexer(x, qr, start_pos, offset).int()   # ratio 4
...
compress_topk_idxs = get_compress_topk_idxs(ratio, bsz, seqlen, start_pos, offset)
topk_idxs = torch.cat([topk_idxs, compress_topk_idxs], dim=-1)
```

and the two differ by a ranking and nothing else:

```python
# Indexer.forward, decode
topk_idxs = index_score.topk(min(self.index_topk, end_pos // ratio), -1)[1] + offset
# get_compress_topk_idxs, decode
matrix = torch.arange(0, (start_pos + 1) // ratio) + offset
```

`end_pos // ratio` at a span of one is `(start_pos + 1) // ratio`: the same
horizon, on the same axis, in the same units, rebased by the same `offset`, and
joined at the same concatenation. One takes the best `k` of them and the other
takes all of them. A19 put the horizon, the rebase, the compaction, the
ascending order and the zero-candidate case into `ROUTE.INDEX_TOPK`; A20 is the
observation that the score operand is the *only* thing the second producer does
not have.

**What the engine does differently.** Three statements, and each is the one it
already made read through the operand that is left. The span comes off `out0`
instead of the score view — the operator writes one row per query either way, so
the dense form loses an operand and not a dimension. The candidate axis is
bounded by `aux_id_0` instead of by the scored columns — the same statement,
that no more groups may be named than the compressed segment can hold. And the
per-row selection is `arange(0, take)` instead of a rank, where `take` is the
limit the causal rule already computed. Everything after the selection —
rebase, join, compact, sort, pad — is untouched.

**Why this removes a wall rather than adding machinery.** The pair A20 retires
declared a `[span, selected_rows_ratio128]` array: **two** request-determined
axes, where A18 gives a view one, so a backend had to resolve a symbol on the
row axis and a second on the feature axis of the same operand. The dense
operator's output is `[span, 128 + k]` with `k = CONTEXT_LENGTH_max / 128` a
constant the operator pads out — `[span, 2176]` for the 262,144-token
deployment, exactly as the ratio-4 array is `[span, 640]`. Measured on the
published graph, the count of tensors declaring two symbolic extents falls from
**61 to 21**, and the 21 that remain are `INDEX_SCORE`'s
`[span_tokens, context_groups_ratio4]` output, which is a different operand with
a different reason. `selected_rows_ratio128` — the eighth of the derived
runtime symbols section 12.8 lists — is retired with the join that needed it,
leaving seven derived and nine runtime symbols in all.

It also deletes an intermediate tensor and an `operand_present_predicate` per
compressed-dense layer. The score operand does not become conditionally absent,
it becomes *statically* absent, which is one fewer alternative operand path for
a backend to get wrong. The published graph loses 20 `WINDOW_INDEX` kernels and
20 axis-1 `CONCAT`s and gains 20 `INDEX_TOPK`s: 3,976 kernels to 3,956, 7,066
tensors to 7,047.

**How a neutral graph says a slot is empty.** `absent_operands` names the ABI
input slots a kernel leaves `NO_ID`, and it is the static counterpart of
`operand_present_predicate`: the operands are placed either side of the hole
rather than packed down, so the window block stays in `in1` and the ratio in
`in2`. Which slots may be named is frozen in
`compiler/ir/v3/lowering.py::OPTIONAL_INPUT_SLOTS` and checked at neutral
admission — a kind that is not in that table may not declare the attribute at
all. This replaces two private per-kind hole tables, one in each backend, with
one per-kernel statement both of them read.

**Refusals.** A19's three stand, and `aux_id_0` behaves exactly as it did:
`NO_ID` derives it as `slots - W`, which for a joined output is the compressed
segment's own width, so a dense operator may state its capacity or let the
output state it. What changes is what the number is *used* for. With a score
view it bounds a selection; with none it bounds the candidate axis, so a context
that completes more groups than the segment holds is refused rather than
truncated:

```text
ROUTE.INDEX_TOPK: a context of 64 at compression ratio 4 is 16 candidates,
outside the 3 slots aux_id_0 gives the compressed segment of output view 5
```

**`index_family` becomes a gate or ceases to exist; it becomes a gate.** The
attribute named which released helper a kernel reproduces and no engine,
verifier or backend read it. That shape is what produced this defect: twenty
layers declared `causal_compressed_dense` while lowering to an operator that
emits a sliding-window position list, and every index the substitution named was
a legal KV row, so the operand checks passed, the bound checks passed and the
numeric checks passed. A comment that reads like a contract is worse than no
comment, because a reader believes it.

So the families each frozen operator produces are now a registry —
`compiler/ir/v3/lowering.py::INDEX_FAMILIES` — and an unknown one is refused at
**neutral admission**, which both backends already call before they lower
anything. One rule, not two backends each remembering. `ROUTE.WINDOW_INDEX`
produces `causal_circular_window` and that is the whole list.

The first thing the rule caught was not the defect it was written for. DSpark's
draft window declares `causal_window_then_current_draft`, and the released
`get_dspark_topk_idxs` gives every draft query the same row —
`arange(0, min(window, p + 1))` followed by the draft block at
`window + arange(block)`. At window 128, block 5 and position 200 that is KV
rows 0 through 132, all 133 of them; `ROUTE.WINDOW_INDEX` emits 73 through 200
and five pads. Sixty rows in common, and **not one of the five draft rows** —
which are the entire point of a draft block's index. It is the same
substitution a second time, latent behind a profile the first release does not
build, and it is now a refusal at export instead of a silently wrong token in
whatever build turns the profile on.

**What a backend must do.** Read `absent_operands` and leave the named slot
`NO_ID`, placing the remaining operands either side of it —
`compiler/ir/v3/lowering.py::abi_input_slots` does the placement, so adopting
this is one call rather than a per-kind hole table, and the same call also
expresses `VECTOR.COMPRESS` sub-case 2's empty `in1`, which both backends
presently keep privately. Stop treating
`ROUTE.INDEX_TOPK`'s `in0` as mandatory: A19's note that "every other frozen
operand row is mandatory — `ROUTE.INDEX_TOPK` reads its score view's *shape*
even where the request completes no candidate" is no longer true of `in0`, and
a backend that keeps a private per-kind hole table has to learn this one from
the shared table instead. The compressed-dense numeric contract loses its two
step qualifiers and becomes `indexing_compressed_dense_indices_v1`, so
`spec/abi3/numeric_contract_union.json` and
`configs/hardware/abi3_capability/*.json` are republished with this amendment:
the union drops `indexing_compressed_dense_indices_causal_compressed_enumeration_v1`,
`indexing_compressed_dense_indices_window_then_compressed_indices_v1` and A19's
`selection_index_topk_indices_window_then_compressed_indices_v1`, and gains the
one contract that replaces all three. Republishing the capability moves the
digest of every deployment admitted against it, which is why it is done here,
once, with the amendment that causes it rather than as quiet drift: the shared
single-chip capability moves from `e50fd317…` to `afdb2245…` and Qwen's HBM
deployment with it, from `d7ef6810…` to `05bf410b…`. Nothing else about Qwen
moves — 75 instructions, 218 descriptors, 22,715 retired work, the same eight
tokens, and the ROM lane untouched at `a60d8500…`, because the ROM capability
does not read this union.

**How far it gets.** At this amendment checkpoint the ROM backend's refusal
stops firing on its own: with
nothing emitting `causal_compressed_dense`, `IMPLEMENTED_INDEX_FAMILIES` has
nothing to reject, the DeepSeek-V4-Flash graph builds on both storage classes at
1,156 instructions and 3,389 descriptors, and the ROM-versus-HBM storage-class
equivalence proof — skipped since the refusal landed — holds again for DeepSeek:
318 descriptors differ, all `MEMORY_OBJECT`, all ROM to HBM, with nothing
beyond the fields normalized by that then-current proof.

Those 1,156/3,389 figures are historical amendment-state evidence, not the
current certificate. The source-current proof is schema
`opentallas.abi3.storage_and_placement_equivalence.v2`: it emits 1,171
instructions and 3,403 descriptors on each generated DeepSeek side, and its
same 318 ROM→HBM objects divide into 312 ROM-local-placement→HBM-unplaced and
6 already-unplaced→HBM-unplaced transitions, with no residual violation. It
still compares two builds through the ROM backend rather than the shipped ROM
and HBM product backends.

What it then stops on is the backend obligation above, and it stops loudly,
which is the property the amendment is for. Neither backend yet reads
`absent_operands`, so the ROM lane packs the two operands down into `in0` and
`in1` and the engine refuses at issue —

```text
prefill failed: ROUTE.INDEX_TOPK window view 2084 covers 1 query rows,
expected 104
```

— where view 2084 is the one-element compression-ratio constant being read as
the window block, and the HBM lane refuses at plan time, "binds 2 input views
where ROUTE.4 requires 3". Both are the same one-call adoption, and neither can
produce a wrong index while it is outstanding.

**RTL 3.0.** Not involved, and this time the proof is a line written for it.
`ot_a3_microsequencer.sv`'s operand walk is the six-way multiplexer over
`op_payload[223:192]` through `op_payload[383:352]` that A17 and A19 were also
invisible to, driven by a slot counter and never by the subopcode — and its scan
state already has the branch A20 needs:

```systemverilog
S_VIEW_SCAN: begin
    if (view_next_slot >= 3'd6) begin
        state <= S_ISSUE;
    end else if (view_slot_id == A3_NO_ID) begin
        view_next_slot <= view_next_slot + 3'd1;
    end else begin ...
```

The module header states the same thing in prose — views are published "in
operand order (inputs 0..3 then outputs 0..1, **skipping NO_ID**)". A20 puts
`NO_ID` in slot 0, which is the one position the walk has never treated
specially, and the skip is unconditional on which slot it is. A19 put a real
descriptor ID where an operator carried `NO_ID`; A20 does the reverse, on the
same walk, through the same branch.

### 12.11 Amendment A21 — a commit's row count is the resource's, not the request's

A `STATE` descriptor's `commit_policy`, one byte at payload offset 1, is
defined. It says where a `STATE.COMMIT`'s row count comes from:

| Value | Policy | The commit covers |
|---:|---|---|
| 0 | `REQUEST_SPAN` | `SPAN_TOKENS` rows at the cursor, which then advances by them. A non-positive count is trap class 9 and `cursor + rows > capacity_rows` is trap class 4. |
| 1 | `UNSTAGED` | nothing. No descriptor of the deployment names the resource's prepared image as a destination, so no transaction can put a row there. The cursor does not move and the capacity bound is satisfied by construction. |

Both policies still close the resource's prepare and advance its generation
when the transaction reaches `CONTROL.COMPLETE`: ADR-003 8.6 makes the whole
declared state set one architectural transition, and a resource this
transaction did not change still took part in the step that happened.

`REQUEST_SPAN` is the rule ABI 3.0 has always executed and zero is the value
the byte has always carried, so no pre-A21 deployment changes and no decoder
written against the pre-A21 layout misreads one. The field was named in the
frozen payload from the freeze; what it did not have was a registry, and
nothing read it.

#### What was wrong

`runtime/sim/device.py` took `rows = SPAN_TOKENS` for every `STATE.COMMIT`, and
`rtl/abi3/ot_a3_microsequencer.sv` bound the same symbol for every `STATE`
instruction:

```systemverilog
end else if (ins_major == A3_MAJOR_STATE) begin
    state_payload <= desc_payload;
    sym_index_q <= A3_SYMBOL_SPAN_TOKENS;
```

`SPAN_TOKENS` is a **request** symbol. It is a row count only where the
resource's row axis is the token axis — true of a KV cache, which is indexed by
position, and false of a fixed recurrent window. A state whose `capacity_rows`
is below the span therefore could not be committed by any backend, however it
lowered, and both DeepSeek lanes stopped on the same resource at a 104-token
prefill:

```text
ROM:  prefill failed: state 329: committing 104 rows at cursor 0 with 0 already staged exceeds capacity 8
HBM:  prefill failed: state 340: committing 104 rows at cursor 0 with 0 already staged exceeds capacity 8
```

#### The released source decides that the window is eight rows

The resource is the ratio-4 layer-2 compressor staging window,
`capacity_rows: 8`, `row_bytes: 4096` — eight rows of 1,024 binary32. In the
pinned snapshot `inference/model.py`, SHA-256
`c0c19e6c9fa439bac7fbb1c5bc1868232dfd5aa2f439a548d0e33dcc2a9edd3f`, that is
exactly what `Compressor.__init__` allocates, at construction and once:

```python
coff = 1 + self.overlap                                     # line 298
...
# State buffers for decode-phase incremental compression.    # line 307
self.register_buffer("kv_state", torch.zeros(args.max_batch_size, coff * compress_ratio, coff * self.head_dim, dtype=torch.float32), persistent=False)   # line 309
```

With `compress_ratio = 4`, `overlap = True` (line 296) and `head_dim = 512`,
`kv_state` is `[max_batch_size, 8, 1024]` binary32. Its row count is
`coff * compress_ratio` — a constant of the architecture. It is not a function
of the request, and no request makes it larger.

How much of it a prefill writes is decided in `forward`'s `start_pos == 0` branch:

```python
if overlap and cutoff >= ratio:
    self.kv_state[:bsz, :ratio] = kv[:, cutoff-ratio : cutoff]                      # line 337
...
if remainder > 0:
    kv, self.kv_state[:bsz, offset : offset+remainder] = kv.split([cutoff, remainder], dim=1)   # line 340
```

A prefill writes `ratio` rows and then `seqlen % ratio` more — at most
`2 * ratio - 1 = 7` rows for any sequence length whatever. At `seqlen = 104`
the remainder is zero and it writes exactly **four**. The prefill's *results*
go somewhere else entirely, to the compressed cache at line 380:
`self.kv_cache[:bsz, :seqlen // ratio] = kv`, which is this ABI's separate
`compressed_kv` resource with its own capacity of one row per group.

So the exporter is right and the third possibility is closed: the released
compressor really does keep an eight-row raw window, and a deployment that
declared 104 rows for it would be describing a different machine.

#### Why the count is declared and cannot be observed

The number a commit needs is how many rows the transaction staged. A device
cannot read it anywhere:

- A `STATE.COMMIT` instruction carries a descriptor ID, a predicate, a wait
  set, a signal event and a source-operation ID (section 3). It has no
  immediate and no operand. There is no room in the instruction for a count.
- The state engine never sees the staging. A program stages a resource through
  ordinary operator output views bound to the prepared image; at the state
  engine those writes are indistinguishable from any other tensor write, and
  RTL 3.0's control plane does not see device memory at all.

What *is* observable, and is a property of the deployment rather than of any
backend's opinion, is whether the deployment can stage the resource **at all**:
whether any descriptor names its prepared image as a destination. Only two can
— an `OPERATOR`'s `output_view_0`/`output_view_1`, and a `COMMUNICATION`'s
local or remote endpoint. A prepared image named by neither is one no
transaction of that deployment can put a byte into.

That derivation is therefore made once, in the shared builder every backend
emits through (`DeploymentBuilder._declare_commit_policies`), from the finished
descriptor table, and re-derived and checked by the verifier
(`_verify_commit_policies`, check `commit_policy_declared`). A backend does not
choose the value and cannot get it wrong, and two backends cannot disagree
about a fact neither of them states.

#### What it says about the two lanes

Every ratio-4 and ratio-128 compressor window in both DeepSeek deployments is
`UNSTAGED`, and the derivation is not a formality — it found that no operator
in either program names those images in **either** direction:

| lane | state | `capacity_rows` | prepared image named as input | as output |
|---|---|---:|---:|---:|
| ROM | 329, 333 — main ratio-4 KV/score | 8 | 0 | 0 |
| ROM | 337, 341 — indexer ratio-4 | 8 | 0 | 0 |
| ROM | 345, 349 — main ratio-128 | 128 | 0 | 0 |
| ROM | 353 — sliding-window KV ring | 128 | 7 | 4 |
| ROM | 317, 321, 325 — compressed caches | 65,536 / 2,048 | 1–2 | 1–2 |
| HBM | 340, 344, 388, 392 — main ratio-4 | 8, 160 | 0 | 0 |
| HBM | 352, 356, 400, 404 — indexer ratio-4 | 8, 160 | 0 | 0 |
| HBM | 368, 376 — main ratio-128 | 2,560 | 0 | 0 |

The two lanes merge these resources differently — ROM declares a per-slot
capacity over a twenty-one-slot object, HBM splits the same twenty-one windows
into one descriptor and a twenty-slot one — and the derivation reaches the same
answer on both, because it asks about the object rather than about the merge.

`VECTOR.COMPRESS`'s state-update sub-case produces the two pool operands
`COMPRESS_POOL` reads next and writes no raw row, because this ABI's
compressor is a prefill operator and the released raw window is a decode
structure — line 307 says so on itself. The window is declared, prepared and
committed because the graph declares it, and A21 is what lets a commit of it
say the true thing rather than a span-shaped one.

Qwen-3 8B is unaffected in every respect: its thirty-six merged KV resources
are staged by `DMA.SCATTER`, they declare `REQUEST_SPAN`, the byte they carry
is the byte they carried, and their descriptors, digests, counters and tokens
are unchanged.

#### RTL 3.0

Involved, and this is the first amendment since A18 that is. A14, A15, A17,
A19 and A20 all touched bytes the microsequencer never reads; this one changes
a rule it executes. `ot_a3_state_controller.sv` already latched `row_bytes`,
`capacity_rows` and `initial_cursor_rows` out of `op_payload` at bits 128, 192
and 256, so the field A21 needs is one more slice of a payload the block
already holds — `op_payload[8 +: 8]`, latched into `slot_policy` beside the
capacity when the slot is claimed. Two rules move with it: `commit_rows` is
zero under `UNSTAGED` regardless of what the sequencer bound, and the
zero-count trap becomes conditional, because zero rows is a malformed request
only where the request is what supplies them. The capacity comparison is
untouched: `commit_end` is `cursor + 0` under `UNSTAGED` and a cursor never
exceeds its own capacity.

The vector set gains `a21_unstaged_commit`, one program committing a staged
resource and an unstaged one whose eight-row capacity is below the
sixty-four-token span — the shape of the wall, in a vector that would have
trapped class 4 before the amendment and retires clean after it. Its
`state_rows_committed` is 64: the span from the staged resource, nothing from
the unstaged one.

It also repaired the set. Every pre-A21 vector prepared and committed a
resource whose prepared image no descriptor could write — the workspace
operator's destination view named a second window of the *activation* object —
so every commit row count in the set was rows nothing had staged, and under
A21 all sixty-three would have become `UNSTAGED` and asserted zero. The
workspace operator now writes the KV resource's prepared image, which is what
a real lane emits and what makes those commits mean what they claim.

### 12.12 Amendment A22 — a deployment's state resources are counted, and the capability bounds them

A capability gains one limit:

| Limit | Bounds |
|---|---|
| `max_state_resources` | the number of `STATE` descriptors a deployment may declare |

One `STATE` descriptor is one state resource. A transactional-state
implementation holds a slot per declared resource for the life of a
transaction — its committed cursor, its capacity, its row stride, its
generation, its commit policy (A21), and whether a prepare is open — because
ADR-003 8.6 makes the whole declared state set one architectural transition and
an abort has to release all of it, not only what this transaction touched. That
slot file is storage, it is finite, and until this amendment no capability field
said how deep it was.

A deployment declaring more state resources than the admitting capability holds
slots for is **refused at admission**, by `runtime.abi3.verifier` check
`state_resource_bound` and independently by `tools/check_abi3_deployment.py`
under the same name.

#### What was wrong

`rtl/abi3/ot_a3_pkg.sv` declared

```systemverilog
localparam integer A3_LOOP_DEPTH   = 4;    // capability max_loop_depth
localparam integer A3_STATE_SLOTS  = 8;
localparam integer A3_EVENT_COUNT  = 256;  // capability max_events
```

Two of those lines name the capability field that expresses them. The middle
one names nothing, because nothing expressed it: `Capability.REQUIRED_LIMITS`
had thirteen entries and none of them was a state-slot count, and
`grep -rn "max_state\|state_slots" runtime/abi3/ configs/` found nothing at
all. So a deployment with more state resources than the sequencer has slots
carried only legal values, was admitted by both admission paths, and was
discovered at run time by the slot file running out:

```systemverilog
if (!hit_found && !free_found) begin
    op_ok <= 1'b0;
    op_trap_class <= A3_TRAP_CAPABILITY;
```

The DeepSeek-V4-Flash ROM wafer deployment declares **ten** `STATE` descriptors
— 317, 321, 325, 329, 333, 337, 341, 345, 349 and 353, the compressed caches,
the ratio-4 and ratio-128 compressor windows and the sliding-window KV ring
A21 enumerates — and its first ten instructions are ten `STATE.PREPARE`. The
eighth `STATE.PREPARE` claimed the eighth and last slot; the ninth — the
instruction at index 8 — found neither a hit nor a free slot and trapped class
4, eight instructions into the 29,333 the golden model retires. The two Qwen lanes
declare one state resource each and never came near it, which is why four
correlating cases said nothing about the bound.

#### What the number is, and why the four profiles agree on it

Sixteen, in every shipped profile. The largest real demand is DeepSeek's ten;
sixteen is the next power of two and leaves six spare, and the slot file is
addressed by `$clog2(SLOTS)`, so sixteen is one address bit rather than a
ragged decoder.

They agree because this is storage in the shared microsequencer, exactly as
`max_loop_depth` is — four in all four profiles since the freeze, for the same
reason. A profile is free to differ in what the sequencer *streams* past
itself, and the four do: `max_instructions` ranges over 4,096, 8,192 and
65,536, and `max_descriptors` over 16,384 and 65,536, because an instruction
and a descriptor are read from memory and not held. What the sequencer *holds*
is one design. A profile that claimed more state slots than the sequencer
implements would be a claim no implementation of it could honour, which is the
defect this amendment closes rather than a freedom it should preserve.

#### RTL 3.0

Involved. `A3_STATE_SLOTS` becomes 16, `SLOT_W` becomes 4, and
`ot_a3_state_controller.sv`'s slot file grows from 1,647 to 3,305 flip-flops
— +1,658, and the hit/free scan becomes a sixteen-way priority search instead
of an eight-way one. Nothing else in the block changes: every width in it was
already derived from `SLOTS` or `SLOT_W`.

Every width except one. The reset loop wrote

```systemverilog
pending_slot[i] <= 4'd0;
```

into a `[SLOT_W-1:0]` register — a literal that happened to be right at
`SLOT_W = 3` by truncation and at `SLOT_W = 4` by luck, and would have been a
silent width mismatch at any larger slot count. It is now `{SLOT_W{1'b0}}`,
which is what every other reset in the block already was.

### 12.13 Amendment A23 — an event ID is bounded by the capability's ID space, not by a count of events

A capability gains one limit, and one consistency rule:

| Limit | Bounds |
|---|---|
| `max_event_id` | the largest event ID an instruction's signal-event field, or a wait set's producer slot, may name |

and `max_events <= max_event_id + 1`, checked in `Capability.validate`.

`max_events` is unchanged in meaning: it bounds how many *distinct* events a
program signals. `max_event_id` bounds the *identifiers*. Neither implies the
other in the direction that matters, and an implementation whose event
scoreboard is a bit per ID is bounded by the second. Both checks stand —
`event_count_bound` and `event_id_bound` — in `runtime.abi3.verifier` and
independently in `tools/check_abi3_deployment.py`.

#### What was wrong

```systemverilog
localparam integer A3_EVENT_COUNT  = 256;  // capability max_events
```

The comment was true of exactly one of the four shipped profiles. `rom_qwen3`
admitted 256, `rom_deepseek_v4` 512, and both HBM/SRAM profiles 4,096. A
parameter documented as a capability field, disagreeing numerically with three
of the four capabilities it claims to transcribe, is not a bound anything
enforces.

And the check it named was the wrong check. `runtime/abi3/verifier.py` proved

```python
len(events) <= limits["max_events"]
```

— the *count* of distinct IDs. The scoreboard is addressed by ID:

```systemverilog
wire signal_in_range = (signal_event_id < EVENTS);
wire [EVENT_INDEX_W-1:0] signal_index = signal_event_id[EVENT_INDEX_W-1:0];
```

so what bounds it is the largest ID plus one. The two coincide only when IDs
are dense from zero. A program signalling three events numbered 4000, 4001 and
4002 passes the count check against any of the four profiles and then indexes
past the end of a scoreboard that has no such entries.

The DeepSeek-V4-Flash wafer program is the dense case and still overran it: 396
distinct IDs, numbered 0 through 395, against `A3_EVENT_COUNT = 256`. IDs 256
to 395 would have aliased onto 0 to 139 — a wait on one of them would have been
satisfied by an unrelated producer, or trapped class 13 against one that had
not run. It never got that far, because A22's slot file stopped the program at
instruction 8; the aliasing was latent behind it and would have been the next
divergence.

#### The consistency rule found a third thing

A scoreboard addressed by ID holds `max_event_id + 1` entries and therefore
cannot carry more than that many distinct signalled events. `max_events` of
4,096 over an ID space of 512 describes a machine nobody can build. Both
HBM/SRAM profiles said exactly that, and nothing checked it, because until
`max_event_id` existed there was nothing to check it against. Their `max_events`
comes down from 4,096 to 512 with this amendment. That narrows what those
profiles admit and widens nothing: no program that was refused becomes
admitted.

#### What the number is

At A23's original closure, `max_event_id = 511` in every shipped profile, an ID
space of 512. The then-largest real demand was DeepSeek ROM's 396 IDs. The
explicit ABI-3.0 rolling-compressor lowering subsequently made the full
DeepSeek HBM program require 596 distinct completion levels. The current RTL
3.0 implementation therefore has `max_event_id = 1023`, an ID space of 1,024,
in every shipped profile. A profile may advertise a smaller `max_events` count
when its own program family needs less (`256` for Qwen ROM and `512` for
DeepSeek ROM); both fields remain checked and `max_events <= max_event_id + 1`.

This is a capability increase, not an ABI change: neither field layout nor any
opcode, descriptor, predicate, or execution rule changed. The HBM profiles
advertise `max_events = 1024`, leaving 428 IDs above the measured 596-event
program.

#### RTL 3.0

Involved. `A3_EVENT_COUNT` is 1,024 and `EVENT_INDEX_W` follows it at 10 bits —
the scoreboard already derives its index width from its `EVENTS` parameter.
Relative to the 512-entry implementation, the `signalled` and `published`
vectors each gain 512 bits, for 1,024 additional scoreboard flip-flops total.

A23 also narrows what `signal_error` reports; A24 has the rest of that.

### 12.14 Amendment A24 — an event is a level, and every retiring instruction that names one raises it

Two rules, both about when an event becomes signalled.

**Single assignment is a property of the program text.** ADR-003 section 9 says
"events are single-assignment within one transaction". That is a rule on the
program: at most one instruction may name a given event ID in its signal-event
field, which `runtime.abi3.verifier._verify_instructions` proves at admission.
It is not a rule on the execution. An event is a **level**: its one producer
raises it when it retires, nothing lowers it before the transaction ends, and
raising a level that is already raised is idempotent. The publication bit is a
level for the same reason: once a `SIGNAL_RELEASE` has ordered the producer's
writes ahead of the signal, a later signal without one does not un-order them.

**No instruction family is exempt from publishing.** Section 3 gives every
instruction a signal-event ID and says only that `NO_ID` means no publication.
Section 4 exempts no family. A `CONTROL` instruction that names an event
publishes it on retirement exactly as an engine instruction does, and a
`CONTROL.NOP` that names one is a real and useful shape: it publishes "every
producer named above this point has retired" without dispatching any work.

#### Why the level reading is the only one available

The dynamic reading — an event may be *written* at most once during the
execution — is not a stricter version of the same rule. It is a different rule,
and it is unimplementable here:

- It makes every loop-compressed program illegal, and loop-compressed programs
  are the only kind ABI 3.0 admits. Amendments A4 and A13 exist precisely so a
  descriptor can be a function of an induction variable and a block loop can
  state its final iteration; a producer inside a loop body signals once per
  trip by construction.
- Satisfying it would need one event ID per loop trip. One DeepSeek prefill
  retires 29,333 instructions against capability event spaces of hundreds. The
  ID space would have to scale with retired work, which is the ABI 2.5 failure
  this version exists to remove.
- There is no re-arm. No operator in section 4 clears an event and no
  descriptor field says an event is auto-clearing, so a pulse could never be
  re-observed and the ABI gives a program no way to ask for one.
- `_verify_events`' proof that no wait deadlocks is about *program order* — a
  wait's producers must precede it, and control flow is forward-only apart from
  `LOOP_NEXT` back edges. That argument is preserved trip to trip by a level
  and destroyed by a pulse.

`runtime.sim.device.Device` has executed the level reading since the beginning:
`signalled` is a `set`, `signalled.add` is idempotent, and a re-signal is
reported nowhere. The reference model is right and this amendment writes down
what it does.

#### What was wrong

`rtl/abi3/ot_a3_event_scoreboard.sv` implemented the dynamic reading:

```systemverilog
if (signalled[signal_index])
    signal_error <= 1'b1;
signalled[signal_index] <= 1'b1;
```

Every engine instruction in the Qwen-3 8B program sits inside a loop, so on one
prefill the sequencer raised **691 signals against 26 distinct event IDs** and
the sticky error bit was set on all four Qwen cases — 100% of the shipped
programs the RTL could run at the time. Nothing trapped on it, `Device`
published no counterpart, and no campaign compared it, so a bit that fired on
every program the project ships had never been read as a defect.

The second rule was wrong in the other direction. `ot_a3_microsequencer.sv`
raised `evt_signal_valid` in exactly one place:

```systemverilog
S_ISSUE: begin
    ...
    if (issue_valid && issue_ready) begin
        issue_valid <= 1'b0;
        evt_signal_valid <= (ins_signal_event_id != A3_NO_ID);
```

No `CONTROL` instruction reaches `S_ISSUE`, so a `CONTROL` instruction naming
an event never published it. `runtime/sim/device.py` had already been repaired
here — "Nothing in the wire format exempts CONTROL from publishing an event;
the asymmetry was accidental" — and the RTL had not, with nothing correlating
the two because no program had exercised it. Qwen has none: all 26 of its
signalling instructions are `DMA`, `TENSOR`, `VECTOR`, `ATTENTION` or
`SELECTION`. DeepSeek has five, all `CONTROL.NOP`, at instructions 392, 398,
661, 964 and 970, signalling events 132, 135, 227, 329 and 332. Wait set 1433
at instruction 402 declares `ACQUIRE` ordering over producers 95, 132 and 135,
and two of those three are published by a `CONTROL.NOP`. With A22's and A23's
bounds raised the RTL reached instruction 402 and trapped class 13 there,
having retired 1,464 of the 29,333 the golden model retires — a defect that
only became visible once the two ahead of it were closed.

#### RTL 3.0

Involved, on both rules.

The scoreboard drops the repeat-assignment error. `signal_error` now reports
exactly one condition, an event ID outside the implemented space, which A23
makes a refusal at admission — so on any admitted program the bit is zero, and
that is the ABI's answer rather than a hand-written expectation. Both checkers
of the deployment co-simulation therefore *assert* it, at divergence site 47,
instead of counting it.

The microsequencer gains a `publish_signal` task called from every `CONTROL`
retirement — `NOP`/`WAIT`/`FENCE`/`ASSERT`, `BRANCH`, `COMPLETE`, and the
shared `S_LOOP_DONE` that retires `LOOP_SETUP` and `LOOP_NEXT`. `CONTROL.TRAP`
does not retire and does not publish, and neither does a predicated-off
instruction of any family, which is what `Device` does on both paths.

### 12.15 What A22, A23 and A24 moved, and what they cost

Adding a limit to a capability changes its canonical JSON, which changes its
digest, which changes the digest of every deployment admitted against it. That
is done here, once, with the amendments that cause it, in the way A20 did it:

| capability | before | after |
|---|---|---|
| `rom_qwen3` | `717de6c9…` | `38234d6c…` |
| `rom_deepseek_v4` | `46ba2338…` | `91f7e6cc…` |
| `hbm_sram_single_chip` | `afdb2245…` | `dd650068…` |
| `hbm_sram_cluster_32` | `c638808c…` | `61d90451…` |

| deployment | before | after |
|---|---|---|
| Qwen3-8B ROM single chip | `a60d8500…` | `c71ee77e…` |
| Qwen3-8B HBM single chip | `05bf410b…` | `fb5c66df…` |
| DeepSeek-V4-Flash ROM wafer | `507e0b57…` | `f5f21bb2…` |

Nothing else about any of the three programs moves: 75 instructions and 239
descriptors on the Qwen ROM lane, 75 and 218 on the Qwen HBM lane, 1,156 and
3,387 on the DeepSeek wafer lane, the same retired work, the same tokens.

The RTL grows by **2,170 flip-flops** — 1,658 in the state slot file (1,647 to
3,305) and 512 in the event scoreboard (512 to 1,024) — plus the combinational
widening that goes with them: a sixteen-way slot search instead of an eight-way
one, and one more bit of event index. That is the whole cost of the three
amendments and is what the physical lane must re-synthesise against. Nothing
else in the sequencer changes size: an instruction and a descriptor are
streamed past it, not held.

`configs/hardware/abi3_capability/*.json` are published from the profiles that
define them by `tools/publish_abi3_capabilities.py`, which grew two entries
with this amendment: the two ROM profiles had the same two sources of truth
that tool exists to remove, and were simply not listed in it. They agreed with
the code by coincidence, with nothing checking that they did.

#### How far it got at the A24 milestone

With A22, A23 and A24 the then-current shipped-deployment co-simulation
(`tools/rtl_abi3_deployment_campaign.py`) correlated **all three deployments
that existed at that milestone** against `runtime.sim.device.Device` at full
depth, on both entrypoints, under Icarus 11.0 and Verilator 5.050. Both
simulators printed this historical marker:

```text
PASS: ABI3 RTL deployment co-simulation deployments=3 cases=6 completions=6 issues=19029 views=58849 signal_flag_cases=0 apply_overflow_cases=0 checks=410331
```

The retained campaign has since moved with A25--A28 and the fourth shipped
image. Its current authoritative marker is:

```text
PASS: ABI3 RTL deployment co-simulation deployments=4 cases=8 completions=8 issues=25054 views=72331
```

The current DeepSeek wafer image is `fa907792…`, with 1,171 instructions and 3,403
descriptors. Its wafer prefill retires 18,491 instructions with 6,852 engine
issues and 20,499 resolved operand views, and its decode 11,714 with 3,600 and
10,428 — up from 8 retired instructions and 8 engine issues before these
amendments. The current campaign also includes the DeepSeek HBM cluster; the
artifact's deployment inventory and `correlated_cases` remain authoritative.
What the campaign still does not establish is unchanged and is listed in the
artifact: the engines are recording no-ops on both sides, so this is the
control plane and not the arithmetic.

### 12.16 Amendment A25 — a commit whose row axis is a ring saturates onto it

This amendment remains the ABI 3.0 rule for a deployment that represents a
sliding window as a transactional `STATE` resource. It is not a mechanism for
compact compressed-KV publication. In the required uninterrupted, fail-stop
simulation profile, TA-ADR-003 lowers compact compressed KV and compressor
working history as ordinary writable HBM tensors, ordered by the token-step
event frontier and fence. They issue no `STATE.COMMIT`, so their completed-group
row axis requires no wire-format divisor or additional commit policy.

`commit_policy` gains a third value. A21 gave the byte a registry of two, and
both of those answers are about a resource whose row axis is *one* thing: the
token axis (`REQUEST_SPAN`), or nothing a transaction can write (`UNSTAGED`).
A sliding window is both at once — it is a KV cache, indexed by position, and
its row axis is a fixed ring of `capacity_rows` slots — and neither answer
describes it.

| Value | Policy | The commit covers |
|---:|---|---|
| 2 | `SATURATING` | `min(SPAN_TOKENS, capacity_rows)` rows: the **last** rows of the span, at the slots `position mod capacity_rows` gives them. The published slots are the circular run of that many slots ending, exclusive, at `(cursor + SPAN_TOKENS) mod capacity_rows`, and the cursor advances to that same value. A non-positive `SPAN_TOKENS` is trap class 9, as under `REQUEST_SPAN`; `cursor + rows > capacity_rows` is unreachable, because a ring cannot be overflowed by a span — the span wraps onto it — so trap class 4 cannot arise from a saturating commit. |

Both of A21's rules are unchanged, byte for byte and rule for rule: zero is
still `REQUEST_SPAN`, one is still `UNSTAGED`, and no deployment that carries
either changes.

#### What the amendment says exactly, and why the reference decides it

Three questions have to be answered to make "saturating" mean something, and
`runtime/reference/kv_window.py` answers all three. It is the frozen reading of
the pinned `inference/model.py`, SHA-256
`c0c19e6c9fa439bac7fbb1c5bc1868232dfd5aa2f439a548d0e33dcc2a9edd3f`, and the ABI
describes what it already does rather than inventing a rule beside it.

**Which rows survive.** A fresh prefill of `S` tokens into a window of `W`
"retains only the final `W` input rows in circular slot order" — the module's
own first paragraph. So a commit publishes `min(span, capacity_rows)` rows and
they are the *last* ones of the span. Rows the ring has already replaced are
not published, because they are not in the resource any more.

**In what slot order.** The reference's `_write_plan` splits the fresh prefill
with `S > W` into two assignments — one, where `S` is a whole number of windows
and the second is empty — and they are the released model's own:

```python
cutoff = sequence_length % window_size            # runtime/reference/kv_window.py
# source [S-W, S-W + (W-cutoff))  ->  slots [cutoff, W)
# source [S-cutoff, S)            ->  slots [0, cutoff)
```

and the decode branch writes the single slot `start_pos % window_size`. Both
are one map: **absolute row `r` lives at slot `r mod capacity_rows`**, in the
prefill direction and in the decode direction. The commit therefore publishes a
circular run of slots, and the two-run case is the same split for the same
reason — the ring's tail, then its head.

**How the cursor advances.** To `(cursor + SPAN_TOKENS) mod capacity_rows`,
which is the slot the next absolute position writes: after a 129-token prefill
into a 128-row ring the cursor is 1, and the decode step at position 129 writes
slot `129 mod 128 = 1`, which is the oldest slot and the one the released model
replaces. The cursor advances by the *span*, not by the rows published, because
what it tracks is the position, and 129 positions passed. That single rule
reproduces all three of the reference's cases — `S <= W`, `S > W`, and decode —
without a case analysis of its own.

One consequence is worth stating because it is what makes the amendment safe to
apply to a resource that never clips: at `cursor == 0` with a span shorter than
the ring, the run is `(0, span)` and the cursor becomes `span`. That is
byte-for-byte the commit `REQUEST_SPAN` performed. Every DeepSeek prefill ever
run before `TA-DS-CTX-129-1` was in exactly that case.

The agreement with the reference is **checked and not asserted**:
`tests/abi3/test_commit_policy.py` calls the reference's own `_write_plan` and
requires the device's published slot runs to equal its destination segments, in
the same order, for every sequence length from 1 to `3W + 1` and for a decode
step at every slot, at three window sizes. A rule that agreed with the released
model only below the window, or only in the count and not in the order, would
fail there.

#### What was wrong

`TA-DS-CTX-129-1` is 129 prompt tokens, one more than `window_tokens`. On the
ROM wafer it ran 9,076 seconds of prefill and then refused:

```text
prefill failed: state 353: committing 129 rows at cursor 0 with 0 already
staged exceeds capacity 128            (trap CAPABILITY_OR_RESOURCE)
```

The sparse attention above it was exact — 403,560 context positions, 403,560
sparse indices, 413,245,440 KV bytes and 355,008 attention heads, every one the
closed-form model for a 129-token prefill. Only the commit refused, and it
refused because `STATE.COMMIT` had no way to say `min(span, capacity)`. A21's
own docstring states the principle it was enforcing: `SPAN_TOKENS` "is a row
count only where the resource's row axis is the token axis, which is true of a
KV cache and false of a fixed recurrent window". The DeepSeek sliding window is
both, and A21's registry had no row for both.

It failed **closed** — it refused rather than wrapping silently or truncating,
so no wrong token was produced — and A25 keeps that property everywhere it did
not remove the condition itself. What it removes is a refusal that was wrong:
the resource was never going to overflow, because a ring cannot.

**Why nothing caught it.** Every DeepSeek prefill ever run was shorter than the
128-row window, so `span` never exceeded `capacity` and `REQUEST_SPAN` was
indistinguishable from a saturating policy — the byte-identical case above.
`TA-DS-CHAT-1` is 104 tokens and its prefix is 32. A prompt that does not exceed
the window cannot exercise sparsity at all, which is exactly why the reporting
ladder starts above it, so the first prompt that could ever have found this is
the first prompt built to test sparse attention.

#### Why the policy is derived, and from what

A21 made `commit_policy` a fact about the finished deployment rather than a
backend's opinion, "so a backend cannot get it wrong and two backends cannot
disagree about a fact neither of them states". A25 keeps that and extends the
derivation with one more observable:

- the prepared image is no descriptor's destination → `UNSTAGED` (A21);
- it is a destination, **and a `DMA.SCATTER` addresses it through a ring index
  table whose modulus is a whole divisor of `capacity_rows`** → `SATURATING`;
- otherwise → `REQUEST_SPAN`.

`DMA.SCATTER` is the one movement whose index operand names its *destination*
rows — a gather's index names its source (section 3) — so a scatter whose index
is a ring writes a ring. The ring is not inferred from a name or a shape: it is
`runtime.sim.generators.ring_indices_v1`, `position mod modulus`, a **generated**
object whose generator and `modulus` the deployment manifest declares and whose
result digest the manifest binds, so a generator that drifts is caught before
the derivation reads it. The whole rule is one shared function,
`runtime.abi3.deployment.derive_commit_policies`, called by the builder every
backend emits through and re-derived by the verifier
(`_verify_commit_policies`, check `commit_policy_declared`).

**Refusals.** Four, all fail-closed, all naming the resource:

- a declared policy outside the registry is refused at admission;
- a declared policy that disagrees with the derived one is refused at
  admission, with the reason the derivation reached — no descriptor stages the
  image, some descriptor does and no ring addresses it, or a ring of *n* rows
  does;
- a ring whose modulus is **not** a whole divisor of `capacity_rows` is refused
  at build and at admission. The row axis is then neither the ring nor the
  capacity, and the amendment refuses to choose one of two numbers rather than
  saturating at a length it cannot justify;
- a saturating resource whose `initial_cursor_rows` is not a slot of its own
  ring — that is, not less than `capacity_rows` — is refused. A cursor outside
  the ring has no slot to name.

#### What it says about the two lanes

Every ring-staged resource in both DeepSeek deployments becomes `SATURATING`,
and nothing else in either lane moves:

| lane | state | class | `capacity_rows` | ring | policy |
|---|---|---|---:|---:|---|
| ROM | 353 — sliding-window KV ring | `KV_CACHE` | 128 | 128 | `SATURATING` |
| ROM | 317, 321, 325 — compressed caches | `COMPRESSED_KV` | 65,536 / 2,048 / 65,536 | — | `REQUEST_SPAN` |
| ROM | 329, 333, 337, 341, 345, 349 — compressor windows | `COMPRESSED_KV` | 8 / 128 | — | `UNSTAGED` |
| HBM | 344, 372 — sliding-window KV rings | `KV_CACHE` | 2,560 / 2,944 | 128 | `SATURATING` |
| HBM | 340, 348, 352 — compressed caches | `COMPRESSED_KV` | 40,960 / 1,376,256 | — | `REQUEST_SPAN` |
| HBM | 332, 336, 356, 360, 364, 368 — compressor windows | `COMPRESSED_KV` | 168 / 2,560 | — | `UNSTAGED` |

Qwen-3 8B is unaffected in every respect, and this is checked rather than
asserted: its KV cache is staged by a `DMA.SCATTER` whose index is
`arange_u32_v1` — absolute positions, not a ring — so it keeps `REQUEST_SPAN`,
and both Qwen deployments are **byte-identical** with the amendment and without
it. A KV cache whose row axis genuinely is the token axis is exactly the case
A25 must not touch, and the discriminator is the ring, not the capacity and not
the class.

#### What A25 does not decide: the row count is merge-relative

The two lanes merge this resource differently, and A21 recorded that they do:
ROM declares one 128-row window over a forty-three-window object, HBM splits the
same forty-three windows into a twenty-window descriptor and a
twenty-three-window one and declares 2,560 and 2,944. A21's question survived
the merge because its answer is a *policy*; A25's answer is also a policy, but
the rows it publishes are counted in the resource's own declared
`capacity_rows`, and a row count does not survive a merge. So ROM clips at 128
rows and HBM at 2,560 and 2,944, and above the window the two lanes'
`state.rows_committed` are not comparable.

That is a property of the merge and not of this amendment, and it is stated
here rather than hidden: **on neither lane does a merged resource's commit row
count equal the rows the transaction actually staged.** ROM stages forty-three
windows and commits one window's worth; HBM stages twenty and commits the span.
That was already true under `REQUEST_SPAN` below the window — a 32-token
prefill on ROM staged forty-three windows and committed thirty-two rows — and it
is visible now only because A25 is the first rule that has to name a number
above the window. Repairing it means either declaring the ring in the descriptor
or refusing the merge, and both are a further amendment rather than a repair
here.

No token depends on it today, and that is a fact about the deployments rather
than a hope: on both lanes **every** state resource's committed image is named
by no operator view in either direction — ten of ten on ROM, eleven of eleven on
HBM — so the committed image is a durability record the forward pass never
reads. The prepared image is what the attention gathers from, and the
ring-indexed scatter places it correctly whatever the commit says.

#### What is behind it

A25 opens the ladder's first three rungs and no further. The next wall is the
same defect one resource over: a **compressed** KV cache's row axis is groups,
not tokens — a commit of a `compress_ratio` cache publishes `span / ratio` rows
— and `REQUEST_SPAN` gives it the span. Neither `REQUEST_SPAN` nor `SATURATING`
expresses that, and the capacity check refuses it, closed, exactly as the
window refused:

| lane | first span that traps | resource |
|---|---:|---|
| ROM | 2,049 | state 321, `COMPRESSED_KV`, `capacity_rows` 2,048 |
| HBM | 40,961 | state 340, `COMPRESSED_KV`, `capacity_rows` 40,960 |

So `TA-DS-CTX-129-1`, `-160-1` and `-256-1` are reachable on both lanes with
this amendment and `TA-DS-CTX-2052-1` is not, and the 200,000- and
1,048,576-token regimes the published ratios are quoted in remain unreachable —
now for a compressed cache's row axis rather than a window's.

#### RTL 3.0

Involved, for the same reason A21 was: this changes a rule the sequencer
executes. `ot_a3_state_controller.sv` already latches `commit_policy` into
`slot_policy` beside the capacity, so A25 adds no field. Three rules move with
the new value: `commit_rows` is `min(span, capacity)` under `SATURATING`; the
capacity comparison is skipped, because a ring satisfies it by construction and
comparing `cursor + rows` against a capacity a saturating commit has already
been clamped to would refuse a legal commit; and the applied cursor is
`(cursor + span) mod capacity` rather than `cursor + rows`, which is the one
piece of arithmetic the block did not already have. The modular reduction is
the block's only divide and is bounded by the same 32-bit row space every other
cursor uses. The staged record grows by one 32-bit field per slot, the span,
because the cursor must advance by the positions the request presented and the
counters by the rows the ring published, and above the ring those are different
numbers.

The change is **behaviour-preserving on every vector that exists**, and this is
executed rather than argued: the microsequencer co-simulation
(`tools/rtl_abi3_campaign.py`) reproduces its marker unchanged under Icarus
11.0 and Verilator 5.050 —

```text
PASS: ABI3 RTL microsequencer cases=65 headers=65 programs=53 issues=185 views=460 traps=11
```

— with a correlation set that names "state prepare, commit, discard, read and
advance counts", "state commit applied or discarded, and rows committed" and
"trap class and first faulting instruction" among the quantities compared. All
sixty-five vectors carry `REQUEST_SPAN` or `UNSTAGED`, and on both the block
computes exactly what it computed before.

**The rule is not yet exercised above the ring, and that is owed.** Amendment
A26 enlarged the microsequencer campaign's header and symbol memories and added
its sixty-fifth case, but that case exercises a fixed-address view edge rather
than a saturating state commit. The shipped-deployment co-simulation does run the DeepSeek wafer
program, whose sliding window now declares `SATURATING`, but it runs it at a
sixteen-token prompt — below the ring, where a saturating commit is
byte-identical to the one before it. So the RTL executes the new value and
agrees with the golden model on every case either side runs, and **no vector
yet drives a span past the ring**. That is the same shape of gap this amendment
exists to close one level up, it is stated here rather than left to be
rediscovered, and the golden model's own conformance suite
(`tests/abi3/test_commit_policy.py`) does cover the clip, the wrap and the
slot order.

#### What it costs

One byte per saturating state resource, and the digests that cover it. The
DeepSeek ROM lane's descriptor table changes in **five** bytes — one
`commit_policy` and the four-byte record CRC32C that seals it — and the HBM
lane's in **ten**, for its two rings. Both lanes' descriptor-table and
deployment digests therefore change, and the pinned DeepSeek digest in
`tools/build_abi3_deployment_rtl_vectors.py` and the shipped deployment RTL
vector set must be republished against them, exactly as A20 and A22–A24 were.
That republication is **not done in this amendment** and is owed: at the time
of writing those files carry uncommitted changes from the A22–A24
republication, and re-deriving them here would mix two amendments' digests into
one set with no way to attribute a later mismatch to either. Until it is done,
three checks fail, and they fail by design rather than by accident — a stale
bundle carrying the pre-A25 policy byte is *refused at admission*, which is the
amendment working:

| check | what it is asking for |
|---|---|
| `tests/compiler/test_rtl_abi3.py::test_deployment_vector_set_is_reproducible` | rebuild the four deployment bundles under `build/abi3/`, then regenerate `testdata/compiler/abi3_deployment/` |
| `tests/compiler/test_rtl_abi3.py::test_a_lowered_work_bound_bounds_both_sides` | the same bundles |
| `tests/compiler/test_rtl_abi3.py::test_retained_deployment_campaign_is_bound_to_these_sources` | re-run `tools/rtl_abi3_deployment_campaign.py` against them |

The two campaigns that do **not** read a deployment bundle — the microsequencer
co-simulation and the engine-datapath co-simulation — are re-recorded here, and
both reproduce their markers unchanged. Both Qwen deployments are
byte-identical, so neither Qwen digest moves and neither Qwen pin needs
touching. No capability field is added, no payload field is assigned,
and
`spec/abi3/descriptor_payloads.json` is unchanged: A25 assigns a value in a
registry the frozen layout already carries, which is additive in exactly the way
A21 was.

### 12.17 Amendment A26 — an edge mask clamps without advancing an address

`TENSOR_VIEW.edge_mask_id`, at payload offset 12, names a `LOOP_CONTROL`
descriptor. The field was present in the frozen 128-byte layout but had no
resolution or admission semantics; `NO_ID` continues to mean no edge mask.

An edge-masked view uses A18's declared axis and affine extent exactly as a
dynamic `LOOP_INDUCTION` term does, with one deliberate difference: the loop
contributes **no element-offset term**. Writing `i` for the named loop's active
induction value, `d` for its bound divisor and `S` for its bound symbol, the
resolver computes

```
step   = extent_numerator * d / extent_unit
remain = extent_numerator * (S - i*d) / extent_unit + extent_bias
dim[extent_axis] = remain if 0 < remain < dim[extent_axis]
                   else dim[extent_axis]
element_offset   = element_offset       # unchanged by the edge mask
```

The division, bias and zero-extent rules are A18's. The named loop must be
active at resolution, verified at admission, runtime-symbol bounded, and form a
whole axis step; the declared extent may not exceed `step + extent_bias`.
Unlike an A4 term, no stride test is needed because an edge mask states that it
bounds the axis rather than that it walks the axis.

This is the rolling-buffer form. A producer and its consumers may execute
inside one block loop while reusing element zero of one block-sized activation
object on every iteration. The final iteration still presents only the rows the
request owns, but no later iteration can address beyond the physical block.
Using an ordinary dynamic term cannot state that: a zero stride preserves the
address but does not walk and therefore cannot clamp, while a block stride
clamps but requires a full-context object.

The change is additive. Every released view already carries `NO_ID` in the
field and keeps its old meaning and bytes. The functional resolver, independent
verifier and RTL view resolver all implement the same rule; an inactive edge
loop is a memory trap rather than a silent full-extent fallback.

### 12.18 Amendment A27 — a zero-base joined prefill carries its logical row

No field is assigned by this amendment. It fixes how `ROUTE.INDEX_TOPK` reads
the fields A19 already assigned when A26 makes the score and selection views a
fixed-address one-row stream.

`aux_id_3` remains the **request** position-base symbol. A prefill request binds
it to zero once; a physical row-loop iteration does not rewrite a runtime
symbol. For a causal `INDEX_TOPK` with a joined window and a zero base, the last
non-pad entry of `input_view_1` is therefore the absolute position `p` used for
the compressed-candidate horizon. The row must be non-empty, strictly ascending
and inside the context or the engine traps. Its selected compressed group `g`
also names KV row `context + g`, because the phase-selected prefill KV layout is
the request's complete current rows followed immediately by compressed rows;
the physical one-row score slice is not that request span. Decode instead uses
its explicit nonzero position base, physical circular-window indices, and a
compressed base equal to the fixed window capacity.

This composes the existing records rather than extending them: A19's window
operand already carries the prefill absolute interval, A26 already carries the
fixed-address loop slice, and `aux_id_2`/`aux_id_3` remain the context and
request-base symbol IDs at payload bytes 56 and 60. Descriptor payloads,
capabilities, decoders and pre-A27 nonzero-base deployments are byte-identical.
Operator conventions section 23 defines the resulting causal rule and its
fail-closed checks.

#### Phase-selected sparse KV layout (existing ABI 3.0 control flow)

The neutral `phase_inputs` attribute does not assign wire-format state. It
requires both backends to emit two already-legal descriptor blocks and select
them with the existing `PHASE_IS` predicate and forward `CONTROL.BRANCH`:

```text
prefill: current[0:S] || compressed[0:floor(S / ratio)]
decode:  physical_window[0:128] || compressed[0:floor(C / ratio)]
```

At ratio zero the suffix is absent; below the first completed group the
optional compressed path is predicated off. Each block consumes its live event
with `CONTROL.WAIT` (or the existing ROM `CONTROL.FENCE` for the uncompressed
path) before convergence, and its phase-specific extent is propagated to the
sparse consumer. `ATTENTION.SPARSE` checks selected values against that
physical row extent while reading `aux_id_2` only as the absolute
position-space bound. This composition adds no field, opcode, feature,
transaction policy, or ABI 3.1 requirement.

### 12.19 Amendment A28 — node-indexed authenticated object sources

No wire field is assigned by this amendment. It defines the deployment-v1
manifest extension used when one symmetric `MEMORY_OBJECT` descriptor names a
different authenticated local image on each cluster node.

An object source of kind `node_segments` carries consecutive node IDs starting
at zero and one non-empty ordered segment list per admitted topology node. Every
list must cover exactly the descriptor's `size_bytes`; the object must be
immutable. The generic verifier rejects a missing topology, a map-count
mismatch, a writable object, a missing object binding, or asymmetric coverage.
There is no fallback to node zero or to a shared source.

The existing 32-byte `MEMORY_OBJECT.content_digest` binds the complete node map.
For one node, the local image digest is
`SHA256(concat(segment_sha256[0], ..., segment_sha256[n-1]))`, where every
segment digest is a required decoded 32-byte SHA-256 value in manifest order.
The descriptor root is the SHA-256 of canonical JSON containing:

```text
schema = "opentallas.abi3.node-segments-content.v1"
size_bytes = the symmetric local object extent
node_count = the number of ordered node maps
nodes = [{node_id, content_sha256}, ...]
```

The deployment-manifest digest separately authenticates segment paths, byte
offsets and lengths; the content root binds ordered bytes and node ownership.
Publication and disk loading both recompute the root and reject a stale
descriptor. Shared `segments` sources retain their existing digest bytes, so
old deployment-v1 manifests remain readable and byte-identical. A reader that
does not implement the new tagged source kind fails closed rather than treating
it as a shared image.

## 13. Amendments made at the architecture freeze

The draft of this document disagreed with `TA-ADR-003` in five places. All five
were repaired before release rather than carried as debt; each is recorded here
because a decoder written against the pre-freeze draft would be wrong.

| ID | Change | Reason |
|---|---|---|
| `TA-A3-ARCH-0-A1` | completion bytes 104-108 carry the final selected token ID and the EOS reason | ADR-003 6.3 requires both and the draft had no field for either |
| `TA-A3-ARCH-0-A2` | completion bytes 112-119 carry retired work | the header proves a maximum retired-work bound, which was otherwise unobservable |
| `TA-A3-ARCH-0-A3` | descriptor type `PREDICATE = 0x000f` is assigned | every instruction has a predicate ID and ADR-003 5.2 mandates predicates, but no descriptor defined one |
| `TA-A3-ARCH-0-A4` | tensor views carry up to four dynamic index terms | ADR-003 5.1 requires loop-compressed programs; a loop over tiles cannot move its window unless a descriptor can be a function of the induction variable. Without this, ABI 3.0 would reproduce the ABI 2.5 failure of 924,386 flat records per forward step |
| `TA-A3-ARCH-0-A5` | the runtime-symbol registry in section 12.2 is frozen | ADR-003 5.2 names these scalars in prose only; loop bounds, predicates and A4 terms need one shared numbering |

Assigning a previously unused descriptor type, reserved byte range, or symbol
value is additive. None of these amendments changes an already-assigned value.

## 14. Complete amendment index

Amendments after A5 were made during implementation, each because a real model
or a real backend could not express something the architecture requires. They
are listed here so a reader has one place to find them; the numbered sections
remain normative.

| ID | Subject | Defined in |
|---|---|---|
| A1 | completion carries the final token and EOS reason | this document, section 7 |
| A2 | completion carries retired work | this document, section 7 |
| A3 | descriptor type `PREDICATE = 0x000f` | this document, section 5 |
| A4 | tensor views carry dynamic index terms | this document, section 12.1 |
| A5 | the runtime-symbol registry | this document, section 12.2 |
| A6 | the sparse-attention operand mapping | operator conventions, section 4.1 |
| A7 | two numeric contracts and the execution backend | operator conventions, section 11 |
| A8 | five resolved operand ambiguities | operator conventions, section 12 |
| A9 | predicated kernels, banked weights, derived constants | operator conventions, section 13 |
| A10 | optional expert-sum weights; unused biased-topk output | operator conventions, section 14 |
| A11 | the KV append operand row | operator conventions, section 15 |
| A12 | `SPAN_LAST_INDEX` | this document, section 12.3 |
| A13 | the partial final iteration of a block loop | this document, section 12.4 |
| A14 | the scope of a collective's participants | this document, section 12.5 |
| A15 | a block scale may tile two axes | this document, section 12.6 |
| A16 | two rotary contracts; the carried plane of a partial dequantisation; the expert sum's trailing base | operator conventions, section 16 |
| A17 | a concatenation states the axis it joins | this document, section 12.7; operator conventions, section 17 |
| A18 | an extent may be an affine function of a bound symbol, at a named axis | this document, section 12.8; operator conventions, section 18 |
| A19 | a sparse index is produced joined, rebased and compacted | this document, section 12.9; operator conventions, section 19 |
| A20 | a dense index is a selection with the selection removed; an index family is refused where it is not implemented | this document, section 12.10; operator conventions, section 20 |
| A21 | a state commit's row count is declared by the resource, not taken from the request span | this document, section 12.11; operator conventions, section 21 |
| A22 | a deployment's state resources are counted, and the capability bounds them | this document, section 12.12 |
| A23 | an event ID is bounded by the capability's ID space, not by a count of events | this document, section 12.13 |
| A24 | an event is a level, and every retiring instruction that names one raises it | this document, section 12.14 |
| A25 | a commit whose row axis is a ring saturates onto it: the rows published are `min(span, capacity_rows)`, in circular slot order | this document, section 12.16; operator conventions, section 22 |
| A26 | an edge mask clamps a rolling tensor view at the final partial loop iteration without advancing its element offset | this document, section 12.17 |
| A27 | a joined zero-base prefill row carries the logical query position across a fixed-address stream | this document, section 12.18; operator conventions, section 23 |
| A28 | a symmetric cluster object may bind one ordered authenticated local image per node through a domain-separated manifest content root | this document, section 12.19; `runtime/abi3/deployment.py` |

Two of these carry more weight than the rest. **A4** and **A13** together are
what make a loop-compressed program possible at all: A4 lets a descriptor be a
function of an induction variable, and A13 lets a block loop state how many rows
its final iteration actually holds. Without either, a backend that wants to stay
correct must emit one dispatch per element or per token, which is precisely the
ABI 2.5 failure this version exists to remove. **A18** is the same statement
made general: the axis a block loop resolves, and the affine function of the
bound symbol that resolves it, are the view's to declare rather than the rule's
to assume, and A13 is its identity case.

### 12.3 Amendment A12 — `SPAN_LAST_INDEX`

Runtime symbol `14` is `SPAN_LAST_INDEX`, defined as `span_tokens - 1`.

Selecting the final row of the current span is an ordinary operation — it is how
a prefill hands one hidden state to the vocabulary projection — but it was not
expressible. A tensor view offsets by `selector_value * element_stride`, and the
registry had no symbol meaning "one before the end", so the index view resolved
to the whole span. The alternative was arithmetic inside a descriptor, which
ABI 3.0 deliberately does not have: a descriptor states a binding, it does not
compute one.

Assigning a previously unassigned symbol value is additive.

### 12.4 Amendment A13 — the partial final iteration of a block loop

A tensor view states static extents. When a loop blocks a symbolic extent — a
512-token block over a 93-token span — the final iteration holds fewer rows than
the block, and a view whose `dim0` is the block size would present rows the
request does not have.

The loop descriptor already carries everything needed to know this:
`bound_symbol_id` is the extent and `bound_divisor` is the block. So when a
view's leading axis is indexed by a `LOOP_INDUCTION` term over a
symbol-bounded loop — meaning the term advances by one whole block of leading
rows, `term_stride = stride0 × bound_divisor` — its resolved leading extent is

```
remaining = symbol_value - iteration * bound_divisor
dim0      = remaining if 0 < remaining < dim0 else dim0
```

This is normative for every ABI 3.0 implementation, including RTL 3.0. Without
it a backend must emit one dispatch per token to stay correct, which is exactly
the retired-work failure ABI 3.0 exists to remove: with the rule, a 93-token
Qwen prefill issues about 700 engine dispatches; without it, about 63,600.

**`dim0` may not exceed `bound_divisor`, and that is what makes the rule
unambiguous.** The functional reference applies the clamp only while
`remaining < bound_divisor`; the formula above does not mention the divisor.
Writing an RTL implementation against both surfaced the difference. They are the
same function on every program where `dim0 ≤ bound_divisor`, and they differ on
every program where it does not — checked exhaustively over divisors 1–8,
extents 1–11, bounds 0–19 and iterations 0–5: 1,027 disagreements, every one of
them with `dim0 > bound_divisor`, and none without.

So the resolution is not to pick a formulation. Iteration *i* of a block loop
covers rows `[i·bound_divisor, (i+1)·bound_divisor)`; a view indexed by that
loop and claiming more than `bound_divisor` leading rows is claiming rows that
belong to the next iteration, which is malformed however the clamp is written.
A deployment containing one is **refused at admission**, and on every admissible
program the two statements of the rule are provably the same rule.

**Which loops index the leading axis is derived, not assumed.** A term is
walking the leading axis exactly when one iteration advances by one whole block
of it, `term_stride = stride0 × bound_divisor`; the clamp and the admission
rule above both apply only to such terms. A view may perfectly well be indexed
by a loop along some *other* axis. The DeepSeek mHC branch reduction is one: its
leading axis is the four hyper-connection streams while its loop steps over
tokens, so its term stride is one token's row rather than four streams' worth of
the leading one. Clamping that view would present four streams as one, which is
not a partial final iteration of anything.

Both the reference resolver and the admission rule originally applied to any
loop-induction term in slot zero. That is the same statement with the stride
condition assumed rather than checked, and it held for every view either model
had emitted until one of them needed a loop over a non-leading axis.

Nothing about the descriptor changes. A13 fixes the *interpretation* of an
existing field combination that was previously unstated, which is why it is
recorded here rather than left in one implementation's resolver.

### 12.5 Amendment A14 — the scope of a collective's participants

A `COMMUNICATION` descriptor gains a `participant_scope` at payload offset 80,
one byte, taking `NODE = 0`, `RETICLE = 1`, `TILE = 2`. The reserved span
shrinks from 48 bytes at offset 80 to 47 at offset 81.

`_participants` derives a collective's member set from the admitted topology.
Until now it derived that set from `node_count` alone, so participants were
always nodes. That is right for a cluster and unusable for a wafer. A
`WAFER_LOGICAL_DEVICE` is presented to the host as one device — that is what the
topology class *means* — so it declares one node, and every collective on it is
therefore a collective over a single participant, which the engine correctly
refuses as degenerate. The DeepSeek wafer deployment builds, verifies and proves
its inverse over all 156 GB, and cannot execute a single one of its five
collective services.

The descriptor already knew better than the engine did. `TOPOLOGY` carries
`reticle_count` and `tiles_per_reticle` beside `node_count`, and
`local_reticle_id` and `local_tile_id` beside `local_node_id`: the wafer's
structure was modelled from the start. Only the participant derivation was
node-only. So the member count is now

```
NODE     -> node_count
RETICLE  -> reticle_count
TILE     -> reticle_count * tiles_per_reticle
```

with `group_id` partitioning that set exactly as before, and the degenerate-set
refusal unchanged: a collective over one participant is still an error at any
scope, because a one-endpoint transfer is `LINK.SEND`.

Two admission rules keep the field honest. A scope the topology cannot support
is refused — `RETICLE` against a zero `reticle_count`, `TILE` against a zero
`tiles_per_reticle`. And a `SINGLE_CHIP` topology admits only `NODE`, because a
chip has no reticle or tile fabric to address.

This is additive in the strict sense. Reserved bytes must be zero, checked on
both encode and decode, so every program written before this amendment carries
zero at offset 80 and therefore means `NODE` — the behaviour it already had. No
existing deployment changes, and no byte of any existing program moves.

The alternative was to declare the wafer's `node_count` to be its reticle count.
That would make the collectives run and would delete the distinction the
topology class exists to draw, leaving nothing in the deployment to say the
thing is one logical device. Making the fabric addressable is the change that
was actually needed; renaming its nodes is not.
