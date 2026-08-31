"""Frozen ABI 3.0 registries.

Every value in this module is normative and is taken from
``docs/TENSOR_ACCELERATOR_ABI_3_WIRE_FORMAT.md`` (contract ``TA-ABI3-WIRE-1``).
Changing an assigned value is a major-version change.  Adding a previously
unassigned value is additive and requires a minor-version bump.
"""

from __future__ import annotations

import enum
from typing import Final

ABI_MAJOR: Final = 3
ABI_MINOR: Final = 0

NO_ID: Final = 0xFFFFFFFF
NO_NODE: Final = 0xFFFF

PROGRAM_MAGIC: Final = b"OTTA3PG\x00"
DESCRIPTOR_MAGIC: Final = b"TA3D"
SUBMISSION_MAGIC: Final = b"TA3S"
COMPLETION_MAGIC: Final = b"TA3C"
CAPABILITY_MAGIC: Final = b"TA3K"

PROGRAM_HEADER_BYTES: Final = 256
INSTRUCTION_BYTES: Final = 32
DESCRIPTOR_HEADER_BYTES: Final = 64
DESCRIPTOR_ALIGNMENT: Final = 64
SUBMISSION_BYTES: Final = 128
COMPLETION_BYTES: Final = 128
CAPABILITY_BYTES: Final = 512

DESCRIPTOR_PAYLOAD_OFFSET: Final = 64
"""Frozen at 64 for version 3.0 (wire format section 5)."""


# --------------------------------------------------------------------------
# Section 3 -- instruction flags
# --------------------------------------------------------------------------
class InstructionFlag(enum.IntFlag):
    """Instruction flag bits.  Bits 8..15 are reserved and must be zero."""

    NONE = 0
    PREDICATED = 1 << 0
    PREDICATE_INVERT = 1 << 1
    WAIT_ACQUIRE = 1 << 2
    SIGNAL_RELEASE = 1 << 3
    TRANSACTION_SCOPED = 1 << 4
    GLOBAL_SCOPE = 1 << 5
    TRACE_BOUNDARY = 1 << 6
    OPTIONAL_FEATURE = 1 << 7


INSTRUCTION_FLAG_MASK: Final = 0x00FF
"""Bits 8..15 are reserved-zero in version 3.0."""


# --------------------------------------------------------------------------
# Section 4 -- opcode registry
# --------------------------------------------------------------------------
class Major(enum.IntEnum):
    """Major opcode families."""

    CONTROL = 0x00
    DMA = 0x10
    TENSOR = 0x20
    VECTOR = 0x30
    ATTENTION = 0x40
    ROUTE = 0x50
    REDUCTION = 0x60
    SELECTION = 0x70
    STATE = 0x80
    LINK = 0x90
    OBSERVATION = 0xA0
    RECOVERY = 0xB0


class Control(enum.IntEnum):
    NOP = 0x00
    BRANCH = 0x01
    LOOP_SETUP = 0x02
    LOOP_NEXT = 0x03
    WAIT = 0x04
    FENCE = 0x05
    ASSERT = 0x06
    COMPLETE = 0x07
    TRAP = 0x08


class Dma(enum.IntEnum):
    TRANSFER = 0x00
    FILL = 0x01
    GATHER = 0x02
    SCATTER = 0x03


class Tensor(enum.IntEnum):
    MATMUL = 0x00
    GROUPED_MATMUL = 0x01
    ROUTED_MATMUL = 0x02
    EMBED_LOOKUP = 0x03


class Vector(enum.IntEnum):
    RMS_NORM = 0x00
    HEAD_RMS_NORM = 0x01
    ROPE = 0x02
    ADD = 0x03
    SILU_MUL = 0x04
    CONVERT = 0x05
    SCALE = 0x06
    SOFTMAX = 0x07
    COMPRESS = 0x08
    MHC = 0x09
    HADAMARD = 0x0A
    INDEX_SCORE = 0x0B
    SQRT_SOFTPLUS = 0x0C


class Attention(enum.IntEnum):
    DENSE = 0x00
    GQA = 0x01
    SPARSE = 0x02


class Route(enum.IntEnum):
    TOPK = 0x00
    BIASED_TOPK = 0x01
    WEIGHT_NORMALIZE = 0x02
    EXPERT_DISPATCH = 0x03
    INDEX_TOPK = 0x04
    HASH_ROUTE = 0x05
    WINDOW_INDEX = 0x06


class Reduction(enum.IntEnum):
    ORDERED_SUM = 0x00
    EXPERT_SUM = 0x01
    VOCAB_GATHER = 0x02
    GROUPED_CONCAT = 0x03
    PARTITION_SUM = 0x04


class Selection(enum.IntEnum):
    ARGMAX = 0x00
    TOKEN_APPEND = 0x01
    SAMPLE = 0x02


class State(enum.IntEnum):
    READ = 0x00
    PREPARE = 0x01
    COMMIT = 0x02
    DISCARD = 0x03
    GENERATION_ADVANCE = 0x04


class Link(enum.IntEnum):
    SEND = 0x00
    RECEIVE = 0x01
    REMOTE_DMA = 0x02
    MULTICAST = 0x03
    GATHER = 0x04
    SCATTER = 0x05
    COLLECTIVE = 0x06
    BARRIER = 0x07


class Observation(enum.IntEnum):
    COUNTER_SNAPSHOT = 0x00
    TRACE_CHECKPOINT = 0x01


class Recovery(enum.IntEnum):
    POISON = 0x00
    ABORT = 0x01
    DRAIN = 0x02


SUBOPCODES: Final[dict[int, type[enum.IntEnum]]] = {
    Major.CONTROL: Control,
    Major.DMA: Dma,
    Major.TENSOR: Tensor,
    Major.VECTOR: Vector,
    Major.ATTENTION: Attention,
    Major.ROUTE: Route,
    Major.REDUCTION: Reduction,
    Major.SELECTION: Selection,
    Major.STATE: State,
    Major.LINK: Link,
    Major.OBSERVATION: Observation,
    Major.RECOVERY: Recovery,
}

ENGINE_FAMILIES: Final[frozenset[int]] = frozenset(
    {
        Major.DMA,
        Major.TENSOR,
        Major.VECTOR,
        Major.ATTENTION,
        Major.ROUTE,
        Major.REDUCTION,
        Major.SELECTION,
        Major.STATE,
        Major.LINK,
    }
)
"""Families whose instructions issue asynchronous engine work."""


def mnemonic(major: int, sub: int) -> str:
    """Return ``FAMILY.SUBOPCODE`` for a legal pair, else raise ``KeyError``."""
    family = Major(major)
    return f"{family.name}.{SUBOPCODES[family](sub).name}"


# --------------------------------------------------------------------------
# Section 5 -- descriptor type registry and permissions
# --------------------------------------------------------------------------
class DescriptorType(enum.IntEnum):
    MEMORY_OBJECT = 0x0001
    TENSOR_VIEW = 0x0002
    NUMERIC = 0x0003
    SCHEDULE = 0x0004
    TOPOLOGY = 0x0005
    COMMUNICATION = 0x0006
    STATE = 0x0007
    EVENT_WAIT_SET = 0x0008
    LOOP_CONTROL = 0x0009
    OPERATOR = 0x000A
    GENERATION_POLICY = 0x000B
    COUNTER_CLASS = 0x000C
    ENTRYPOINT_TABLE = 0x000D
    SIGNATURE_METADATA = 0x000E


class Permission(enum.IntFlag):
    NONE = 0
    READ = 1 << 0
    WRITE = 1 << 1
    EXECUTE = 1 << 2
    STATE_PREPARE = 1 << 3
    STATE_COMMIT = 1 << 4
    REMOTE = 1 << 5
    HOST_VISIBLE = 1 << 6
    IMMUTABLE = 1 << 7


PERMISSION_MASK: Final = 0x000000FF
"""Bits 8..31 are reserved-zero."""


# --------------------------------------------------------------------------
# Section 6/7 -- host queue registries
# --------------------------------------------------------------------------
class HostOpcode(enum.IntEnum):
    QUERY_CAPABILITY = 0x00
    LOAD_DEPLOYMENT = 0x01
    ACTIVATE_DEPLOYMENT = 0x02
    DEACTIVATE_DEPLOYMENT = 0x03
    UNLOAD_DEPLOYMENT = 0x04
    CREATE_SESSION = 0x10
    GENERATE = 0x11
    CHECKPOINT_SESSION = 0x12
    RESTORE_SESSION = 0x13
    DESTROY_SESSION = 0x14
    QUIESCE = 0x20
    RESUME = 0x21
    RESET = 0x22
    DIAGNOSTICS = 0x23


class CompletionStatus(enum.IntEnum):
    SUCCESS = 0
    FAILED = 1
    ABORTED = 2
    RESET_RECOVERED = 3


class SubmissionFlag(enum.IntFlag):
    NONE = 0
    PREFILL_PHASE = 1 << 0
    DECODE_PHASE = 1 << 1
    RETRY = 1 << 2
    TRACE_ENABLE = 1 << 3


class CompletionFlag(enum.IntFlag):
    NONE = 0
    EOS_STOP = 1 << 0
    LENGTH_STOP = 1 << 1
    POISONED = 1 << 2
    COUNTER_OVERFLOW = 1 << 3
    TRACE_LOSS = 1 << 4
    STATE_COMMITTED = 1 << 5


# --------------------------------------------------------------------------
# Section 8 -- trap, scope, topology and ordering registries
# --------------------------------------------------------------------------
class TrapClass(enum.IntEnum):
    NONE = 0
    ADMISSION_OR_VERSION = 1
    AUTHENTICATION_OR_INTEGRITY = 2
    DESCRIPTOR_OR_ADDRESS = 3
    CAPABILITY_OR_RESOURCE = 4
    ILLEGAL_INSTRUCTION_OR_CONTROL_FLOW = 5
    NUMERIC_OR_EXCEPTIONAL_VALUE = 6
    MEMORY_SUBSYSTEM = 7
    ENGINE = 8
    STATE_TRANSACTION = 9
    TIMEOUT_OR_WATCHDOG = 10
    LINK_OR_NOC = 11
    POWER_RESET_OR_THERMAL = 12
    INTERNAL_INVARIANT = 13


class TopologyClass(enum.IntEnum):
    SINGLE_CHIP = 0
    CLUSTER_32 = 1
    WAFER_LOGICAL_DEVICE = 2


class Scope(enum.IntEnum):
    ENGINE = 0
    SRAM_BANK = 1
    HBM_WINDOW = 2
    STATE_RESOURCE = 3
    NODE = 4
    CLUSTER = 5
    RETICLE = 6
    WAFER_DEVICE = 7
    SYSTEM = 8


class ParticipantScope(enum.IntEnum):
    """Amendment A14: what a collective's participants *are*.

    Wire format section 12.5.  ``COMMUNICATION.participant_scope`` selects the
    quantity of the admitted TOPOLOGY descriptor that counts the members of a
    collective:

    ==============  ==========================================
    ``NODE``        ``node_count``
    ``RETICLE``     ``reticle_count``
    ``TILE``        ``reticle_count * tiles_per_reticle``
    ==============  ==========================================

    Zero is ``NODE``, which is the derivation every pre-A14 program already
    had, so a program written before the amendment carries the amendment's
    default in its reserved zero and means exactly what it meant before.  This
    registry is distinct from :class:`Scope`, which names a *memory and event*
    scope; a participant scope names the fabric a collective spans.
    """

    NODE = 0
    RETICLE = 1
    TILE = 2


class Ordering(enum.IntEnum):
    NONE = 0
    ACQUIRE = 1
    RELEASE = 2
    ACQUIRE_RELEASE = 3
    SEQUENTIAL = 4


# --------------------------------------------------------------------------
# Section 9 -- required feature bits
# --------------------------------------------------------------------------
class Feature(enum.IntEnum):
    HOST_QUEUE_ABI = 0
    DEPLOYMENT_DESCRIPTOR_ABI = 1
    DETERMINISTIC_MICROSEQUENCER = 2
    BF16_TENSOR = 3
    FP8_E4M3FN_TENSOR = 4
    MXFP4_E2M1_E8M0 = 5
    TRANSACTIONAL_STATE = 6
    ON_DEVICE_SELECTION = 7
    INTER_CHIP_ENDPOINT = 8
    WAFER_ENDPOINT = 9
    INTEGRITY_RETRY = 10
    SIGNED_DEPLOYMENT = 11
    DATA_BEARING_TIMING = 12


FEATURE_VECTOR_BYTES: Final = 32
"""256-bit little-endian bit vector in the program header."""


def feature_vector(bits: object) -> bytes:
    """Encode an iterable of feature bit indices as the 32-byte header vector."""
    value = 0
    for bit in bits:  # type: ignore[union-attr]
        index = int(bit)
        if not 0 <= index < FEATURE_VECTOR_BYTES * 8:
            raise ValueError(f"feature bit {index} out of range")
        value |= 1 << index
    return value.to_bytes(FEATURE_VECTOR_BYTES, "little")


def feature_bits(vector: bytes) -> frozenset[int]:
    """Decode the 32-byte header vector into a set of bit indices."""
    if len(vector) != FEATURE_VECTOR_BYTES:
        raise ValueError("feature vector must be exactly 32 bytes")
    value = int.from_bytes(vector, "little")
    return frozenset(i for i in range(FEATURE_VECTOR_BYTES * 8) if value >> i & 1)


# --------------------------------------------------------------------------
# Section 10 -- counter namespaces
# --------------------------------------------------------------------------
class CounterGroup(enum.IntEnum):
    INSTRUCTION = 0x01
    ENGINE_QUEUE = 0x02
    MEMORY = 0x03
    TENSOR = 0x04
    VECTOR_REDUCTION = 0x05
    ATTENTION = 0x06
    ROUTE_EXPERT = 0x07
    STATE = 0x08
    SELECTION_EOS = 0x09
    COMMUNICATION = 0x0A
    FAULT_RECOVERY = 0x0B
    LATENCY = 0x0C


def counter_id(group: CounterGroup, event: int) -> int:
    """Compose a 32-bit counter ID from its frozen group and event."""
    if not 0 <= event < (1 << 24):
        raise ValueError("counter event must fit in 24 bits")
    return (int(group) << 24) | event


# --------------------------------------------------------------------------
# Numeric formats (payload-level; see the numeric descriptor)
# --------------------------------------------------------------------------
class DType(enum.IntEnum):
    """Storage element types addressable by a tensor view."""

    U8 = 0x00
    I8 = 0x01
    U16 = 0x02
    I16 = 0x03
    U32 = 0x04
    I32 = 0x05
    U64 = 0x06
    I64 = 0x07
    BF16 = 0x10
    FP16 = 0x11
    FP32 = 0x12
    FP64 = 0x13
    FP8_E4M3FN = 0x20
    FP8_E5M2 = 0x21
    MXFP4_E2M1 = 0x30
    E8M0_SCALE = 0x31


DTYPE_BITS: Final[dict[int, int]] = {
    DType.U8: 8,
    DType.I8: 8,
    DType.U16: 16,
    DType.I16: 16,
    DType.U32: 32,
    DType.I32: 32,
    DType.U64: 64,
    DType.I64: 64,
    DType.BF16: 16,
    DType.FP16: 16,
    DType.FP32: 32,
    DType.FP64: 64,
    DType.FP8_E4M3FN: 8,
    DType.FP8_E5M2: 8,
    DType.MXFP4_E2M1: 4,
    DType.E8M0_SCALE: 8,
}


class StorageClass(enum.IntEnum):
    HOST = 0
    HBM = 1
    SRAM = 2
    ROM = 3
    STATE = 4


class IntegrityMode(enum.IntEnum):
    NONE = 0
    CRC32C = 1
    ECC = 2
    CRC_AND_ECC = 3


class RoundingMode(enum.IntEnum):
    NEAREST_EVEN = 0
    TOWARD_ZERO = 1
    STOCHASTIC = 2


class ReductionOrder(enum.IntEnum):
    SEQUENTIAL_ASCENDING = 0
    PAIRWISE_TREE = 1
    BLOCKED_ASCENDING = 2


class StateClass(enum.IntEnum):
    KV_CACHE = 0
    COMPRESSED_KV = 1
    TOKEN_RING = 2
    POSITION_CURSOR = 3
    ROUTE_HISTORY = 4
    SCRATCH = 5


class CommitPolicy(enum.IntEnum):
    """Where a ``STATE.COMMIT``'s row count comes from (amendment A21).

    ``SPAN_TOKENS`` is a *request* symbol.  It is a row count only where the
    resource's row axis is the token axis, which is true of a KV cache and
    false of a fixed recurrent window.  The number of rows a commit publishes
    is therefore a property of the resource, declared here, at STATE payload
    offset 1 -- a byte the frozen layout has always carried and no reader has
    ever consulted.

    ``REQUEST_SPAN`` is the rule ABI 3.0 has always executed and the value the
    byte has always held, so no pre-A21 deployment changes.  ``UNSTAGED`` says
    the deployment names the resource's prepared image as no descriptor's
    destination, so no transaction can stage a row into it and its commit
    publishes none.

    ``SATURATING`` (amendment A25, wire format section 12.16) is the third
    answer, and it is the one a sliding window needs: the resource *is* staged,
    and its row axis is a ring of ``capacity_rows`` slots that the token axis
    is mapped onto by ``position mod capacity_rows``.  A commit publishes
    ``min(SPAN_TOKENS, capacity_rows)`` rows -- the last ones of the span, in
    circular slot order -- and the cursor advances to
    ``(cursor + SPAN_TOKENS) mod capacity_rows``.  A KV cache and a fixed
    recurrent window are both, and the DeepSeek sliding window is both at once.
    """

    REQUEST_SPAN = 0
    UNSTAGED = 1
    SATURATING = 2
