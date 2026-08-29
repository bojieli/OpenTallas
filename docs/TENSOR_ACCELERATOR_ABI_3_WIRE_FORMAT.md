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
`ENTRYPOINT_TABLE=0x000d`, and `SIGNATURE_METADATA=0x000e`.

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
| 104 | 20 | reserved, zero |
| 124 | 4 | record CRC32C |

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
