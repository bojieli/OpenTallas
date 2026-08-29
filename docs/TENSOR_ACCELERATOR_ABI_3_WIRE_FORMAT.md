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
deployment does not require link instructions.

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

Two of these carry more weight than the rest. **A4** and **A13** together are
what make a loop-compressed program possible at all: A4 lets a descriptor be a
function of an induction variable, and A13 lets a block loop state how many rows
its final iteration actually holds. Without either, a backend that wants to stay
correct must emit one dispatch per element or per token, which is precisely the
ABI 2.5 failure this version exists to remove.

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
