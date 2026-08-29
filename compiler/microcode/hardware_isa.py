"""Canonical hardware-facing descriptor ISA for OpenTallas.

This is the stage sequencer ABI, not a GPU-like scalar or SIMT instruction
set.  One record launches a bounded hardware service over manifest-bound
descriptors.  Tensor addresses, loop bounds, numerical constants, mutable
state locations, and schedule slots therefore live in authenticated
descriptor tables rather than as inline instruction immediates.

The small fixture ISA in :mod:`compiler.microcode.isa` and the operator-local
DeepSeek evidence programs remain separate semantic test ABIs.  They must be
lowered to this contract before they can drive the hardware service boundary.
"""

from __future__ import annotations

from dataclasses import dataclass, fields
from enum import IntEnum, IntFlag
import hashlib
import json
from types import MappingProxyType
import struct
from typing import Iterable, Mapping
import zlib


MAGIC = b"OTHWISA1"
ABI_MAJOR = 1
ABI_MINOR = 0
DESCRIPTOR_SCHEMA_VERSION = 1
MAX_RECORDS = 1_000_000
NO_ID = 0xFFFFFFFF

# The header carries both the exact body digest and a caller-supplied SHA-256
# binding for the image/graph/descriptor-table contract.  Reserved bytes are
# zero in ABI 1.0.
HEADER = struct.Struct("<8sBBHHHII32s32s8s")

# The final uint32 is a record-local CRC32.  The preceding reserved uint32 is
# required to be zero.  All other uint32 fields are opaque IDs into
# manifest-bound tables; none is a physical byte address or loop bound.
RECORD = struct.Struct("<BBH15I")


class HardwareISAError(ValueError):
    """Raised when a program or lowering contract is not fail-closed legal."""


class MajorOpcode(IntEnum):
    """The complete stage-level macro-op set for ABI 1."""

    KV_READ = 0x10
    VECTOR = 0x20
    ROUTE = 0x30
    ROM_MATMUL = 0x40
    REDUCE = 0x50
    KV_PREPARE = 0x60
    COMMIT = 0x61
    STAGE_SEND = 0x70
    COMPLETE = 0xFF


class KVReadSubopcode(IntEnum):
    SESSION_STATE = 0x01
    KV_WINDOW = 0x02
    COMPRESSOR_STATE = 0x03
    COMPRESSED_KV = 0x04
    ATTENTION_VIEW = 0x05
    DSPARK_MAIN_KV = 0x06


class VectorSubopcode(IntEnum):
    COPY_EXPAND = 0x01
    RMS_NORM = 0x02
    HEAD_RMS_NORM = 0x03
    ROPE_APPLY = 0x04
    ROPE_INVERSE = 0x05
    FP8_QDQ = 0x06
    FP4_QDQ = 0x07
    HADAMARD_128 = 0x08
    HC_NORMALIZE = 0x09
    HC_SINKHORN = 0x0A
    HC_POST = 0x0B
    HC_HEAD_ACTIVATE = 0x0C
    COMPRESS_POOL = 0x0D
    BINARY32_TO_BF16 = 0x0E
    INDEX_SCORE = 0x0F
    SPARSE_ATTEND = 0x10
    SQRT_SOFTPLUS = 0x11
    SILU_GATE = 0x12
    SAMPLE = 0x13
    TARGET_CAPTURE = 0x14
    BINARY32_ADD = 0x15


class RouteSubopcode(IntEnum):
    WINDOW_INDEX = 0x01
    INDEX_TOPK = 0x02
    COMPRESSED_DENSE_INDEX = 0x03
    SPARSE_GATHER = 0x04
    HASH_LOOKUP = 0x05
    BIASED_TOPK = 0x06
    WEIGHT_NORMALIZE = 0x07
    EXPERT_DISPATCH = 0x08
    DSPARK_WINDOW_INDEX = 0x09


class ROMMatmulSubopcode(IntEnum):
    LOOKUP = 0x01
    DENSE = 0x02
    GROUPED = 0x03
    ROUTED = 0x04
    PAIRED_DENSE = 0x05
    PAIRED_ROUTED = 0x06
    VOCABULARY = 0x07


class ReduceSubopcode(IntEnum):
    PARTITION_SUM = 0x01
    TILE_SUM = 0x02
    GROUPED_CONCAT = 0x03
    EXPERT_SUM = 0x04
    HC_SUM = 0x05
    HC_MEAN = 0x06
    VOCABULARY_GATHER = 0x07


class KVPrepareSubopcode(IntEnum):
    KV_WINDOW = 0x01
    COMPRESSOR_STATE = 0x02
    COMPRESSED_KV = 0x03
    DSPARK_PREFILL_KV = 0x04


class CommitSubopcode(IntEnum):
    KV_WINDOW = 0x01
    COMPRESSOR_STATE = 0x02
    COMPRESSED_KV = 0x03
    DSPARK_PREFILL_KV = 0x04


class StageSendSubopcode(IntEnum):
    ACTIVATION = 0x01


class CompleteSubopcode(IntEnum):
    TERMINAL = 0x00


class InstructionFlag(IntFlag):
    """Control bits whose corresponding descriptor fields are checked."""

    PREDICATED = 0x0001
    WAIT_DESCRIPTOR = 0x0002
    SIGNAL_TOKEN = 0x0004
    NODE_BEGIN = 0x0008
    NODE_END = 0x0010
    PREFILL_ONLY = 0x0020
    DECODE_ONLY = 0x0040
    BATCH_ATOMIC = 0x0080


VALID_FLAG_MASK = int(
    InstructionFlag.PREDICATED
    | InstructionFlag.WAIT_DESCRIPTOR
    | InstructionFlag.SIGNAL_TOKEN
    | InstructionFlag.NODE_BEGIN
    | InstructionFlag.NODE_END
    | InstructionFlag.PREFILL_ONLY
    | InstructionFlag.DECODE_ONLY
    | InstructionFlag.BATCH_ATOMIC
)


SUBOPCODE_ENUMS: Mapping[MajorOpcode, type[IntEnum]] = MappingProxyType(
    {
        MajorOpcode.KV_READ: KVReadSubopcode,
        MajorOpcode.VECTOR: VectorSubopcode,
        MajorOpcode.ROUTE: RouteSubopcode,
        MajorOpcode.ROM_MATMUL: ROMMatmulSubopcode,
        MajorOpcode.REDUCE: ReduceSubopcode,
        MajorOpcode.KV_PREPARE: KVPrepareSubopcode,
        MajorOpcode.COMMIT: CommitSubopcode,
        MajorOpcode.STAGE_SEND: StageSendSubopcode,
        MajorOpcode.COMPLETE: CompleteSubopcode,
    }
)


@dataclass(frozen=True, slots=True)
class Instruction:
    """One 64-byte stage descriptor instruction.

    Every ``*_descriptor_id`` indexes an authenticated table.  Buffer IDs name
    stage-local logical buffers; they are not SRAM byte addresses.
    """

    major_opcode: MajorOpcode
    subopcode: int
    flags: InstructionFlag = InstructionFlag(0)
    predicate_descriptor_id: int = NO_ID
    destination_buffer_id: int = NO_ID
    source0_buffer_id: int = NO_ID
    source1_buffer_id: int = NO_ID
    auxiliary_buffer_id: int = NO_ID
    tensor_descriptor_id: int = NO_ID
    shape_descriptor_id: int = NO_ID
    numeric_descriptor_id: int = NO_ID
    state_descriptor_id: int = NO_ID
    schedule_descriptor_id: int = NO_ID
    wait_descriptor_id: int = NO_ID
    signal_token_id: int = NO_ID
    operator_descriptor_id: int = NO_ID


@dataclass(frozen=True, slots=True)
class Program:
    """A hardware program and its descriptor/image binding identity."""

    binding_sha256: bytes
    instructions: tuple[Instruction, ...]


@dataclass(frozen=True, slots=True)
class LoweringStep:
    """One symbolic hardware macro-op in a semantic-kind lowering recipe."""

    major_opcode: MajorOpcode
    subopcode: int


_CONTROL_FIELDS = frozenset(
    {
        "predicate_descriptor_id",
        "wait_descriptor_id",
        "signal_token_id",
    }
)

_REQUIRED_FIELDS: Mapping[MajorOpcode, frozenset[str]] = MappingProxyType(
    {
        MajorOpcode.KV_READ: frozenset(
            {
                "destination_buffer_id",
                "shape_descriptor_id",
                "numeric_descriptor_id",
                "state_descriptor_id",
                "schedule_descriptor_id",
                "operator_descriptor_id",
            }
        ),
        MajorOpcode.VECTOR: frozenset(
            {
                "destination_buffer_id",
                "source0_buffer_id",
                "shape_descriptor_id",
                "numeric_descriptor_id",
                "schedule_descriptor_id",
                "operator_descriptor_id",
            }
        ),
        MajorOpcode.ROUTE: frozenset(
            {
                "destination_buffer_id",
                "source0_buffer_id",
                "shape_descriptor_id",
                "schedule_descriptor_id",
                "operator_descriptor_id",
            }
        ),
        MajorOpcode.ROM_MATMUL: frozenset(
            {
                "destination_buffer_id",
                "source0_buffer_id",
                "tensor_descriptor_id",
                "shape_descriptor_id",
                "numeric_descriptor_id",
                "schedule_descriptor_id",
                "operator_descriptor_id",
            }
        ),
        MajorOpcode.REDUCE: frozenset(
            {
                "destination_buffer_id",
                "source0_buffer_id",
                "shape_descriptor_id",
                "numeric_descriptor_id",
                "schedule_descriptor_id",
                "operator_descriptor_id",
            }
        ),
        MajorOpcode.KV_PREPARE: frozenset(
            {
                "source0_buffer_id",
                "shape_descriptor_id",
                "numeric_descriptor_id",
                "state_descriptor_id",
                "schedule_descriptor_id",
                "operator_descriptor_id",
            }
        ),
        MajorOpcode.COMMIT: frozenset(
            {
                "state_descriptor_id",
                "schedule_descriptor_id",
                "operator_descriptor_id",
            }
        ),
        MajorOpcode.STAGE_SEND: frozenset(
            {
                "source0_buffer_id",
                "shape_descriptor_id",
                "numeric_descriptor_id",
                "schedule_descriptor_id",
                "operator_descriptor_id",
            }
        ),
        MajorOpcode.COMPLETE: frozenset(),
    }
)

_ALLOWED_DATA_FIELDS: Mapping[MajorOpcode, frozenset[str]] = MappingProxyType(
    {
        MajorOpcode.KV_READ: _REQUIRED_FIELDS[MajorOpcode.KV_READ],
        MajorOpcode.VECTOR: _REQUIRED_FIELDS[MajorOpcode.VECTOR]
        | frozenset(
            {
                "source1_buffer_id",
                "auxiliary_buffer_id",
                "tensor_descriptor_id",
            }
        ),
        MajorOpcode.ROUTE: _REQUIRED_FIELDS[MajorOpcode.ROUTE]
        | frozenset(
            {
                "source1_buffer_id",
                "auxiliary_buffer_id",
                "tensor_descriptor_id",
                "numeric_descriptor_id",
            }
        ),
        MajorOpcode.ROM_MATMUL: _REQUIRED_FIELDS[MajorOpcode.ROM_MATMUL]
        | frozenset({"source1_buffer_id", "auxiliary_buffer_id"}),
        MajorOpcode.REDUCE: _REQUIRED_FIELDS[MajorOpcode.REDUCE]
        | frozenset({"source1_buffer_id", "auxiliary_buffer_id"}),
        MajorOpcode.KV_PREPARE: _REQUIRED_FIELDS[MajorOpcode.KV_PREPARE]
        | frozenset({"source1_buffer_id", "auxiliary_buffer_id"}),
        MajorOpcode.COMMIT: _REQUIRED_FIELDS[MajorOpcode.COMMIT],
        MajorOpcode.STAGE_SEND: _REQUIRED_FIELDS[MajorOpcode.STAGE_SEND]
        | frozenset({"auxiliary_buffer_id"}),
        MajorOpcode.COMPLETE: frozenset({"destination_buffer_id"}),
    }
)

_ID_FIELD_NAMES = tuple(
    field.name
    for field in fields(Instruction)
    if field.name not in {"major_opcode", "subopcode", "flags"}
)


def _step(major: MajorOpcode, subopcode: IntEnum) -> LoweringStep:
    return LoweringStep(major, int(subopcode))


# This table is deliberately explicit.  It is a structural lowering recipe,
# not evidence that operand descriptors, schedules, service engines, or RTL
# implementations exist.  Loop counts (including the five Markov steps) are
# carried by shape/operator descriptors, never by repeating element-level
# instructions.
DEEPSEEK_V4_OPERATOR_LOWERING: Mapping[str, tuple[LoweringStep, ...]] = (
    MappingProxyType(
        {
            "ATTENTION_KV_VIEW": (
                _step(MajorOpcode.KV_READ, KVReadSubopcode.ATTENTION_VIEW),
            ),
            "BIASED_TOPK_ROUTE": (
                _step(MajorOpcode.ROUTE, RouteSubopcode.BIASED_TOPK),
            ),
            "BF16_LINEAR": (
                _step(MajorOpcode.ROM_MATMUL, ROMMatmulSubopcode.DENSE),
            ),
            "BINARY32_TO_BF16": (
                _step(MajorOpcode.VECTOR, VectorSubopcode.BINARY32_TO_BF16),
            ),
            "COMPRESS_KV_WRITE": (
                _step(MajorOpcode.KV_READ, KVReadSubopcode.COMPRESSED_KV),
                _step(
                    MajorOpcode.KV_PREPARE,
                    KVPrepareSubopcode.COMPRESSED_KV,
                ),
                _step(MajorOpcode.COMMIT, CommitSubopcode.COMPRESSED_KV),
            ),
            "COMPRESS_POOL": (
                _step(MajorOpcode.VECTOR, VectorSubopcode.COMPRESS_POOL),
            ),
            "COMPRESS_PROJECT": (
                _step(MajorOpcode.ROM_MATMUL, ROMMatmulSubopcode.PAIRED_DENSE),
            ),
            "COMPRESS_STATE_UPDATE": (
                _step(MajorOpcode.KV_READ, KVReadSubopcode.COMPRESSOR_STATE),
                _step(
                    MajorOpcode.KV_PREPARE,
                    KVPrepareSubopcode.COMPRESSOR_STATE,
                ),
                _step(MajorOpcode.COMMIT, CommitSubopcode.COMPRESSOR_STATE),
            ),
            "COMPRESSED_DENSE_INDEX": (
                _step(MajorOpcode.ROUTE, RouteSubopcode.COMPRESSED_DENSE_INDEX),
            ),
            "COMPRESSED_KV_VALID_VIEW": (
                _step(MajorOpcode.KV_READ, KVReadSubopcode.COMPRESSED_KV),
            ),
            "CONFIDENCE_SCORE": (
                _step(MajorOpcode.ROM_MATMUL, ROMMatmulSubopcode.DENSE),
            ),
            "DSPARK_MAIN_PROJECT": (
                _step(MajorOpcode.ROM_MATMUL, ROMMatmulSubopcode.DENSE),
                _step(MajorOpcode.VECTOR, VectorSubopcode.RMS_NORM),
            ),
            "DSPARK_NOISE_EMBED": (
                _step(MajorOpcode.ROM_MATMUL, ROMMatmulSubopcode.LOOKUP),
                _step(MajorOpcode.VECTOR, VectorSubopcode.COPY_EXPAND),
            ),
            "DSPARK_PREFILL_KV": (
                _step(MajorOpcode.KV_READ, KVReadSubopcode.DSPARK_MAIN_KV),
                _step(
                    MajorOpcode.KV_PREPARE,
                    KVPrepareSubopcode.DSPARK_PREFILL_KV,
                ),
                _step(MajorOpcode.COMMIT, CommitSubopcode.DSPARK_PREFILL_KV),
            ),
            "DSPARK_WINDOW_INDEX": (
                _step(MajorOpcode.ROUTE, RouteSubopcode.DSPARK_WINDOW_INDEX),
            ),
            "EXPERT_DISPATCH": (
                _step(MajorOpcode.ROUTE, RouteSubopcode.EXPERT_DISPATCH),
            ),
            "EXPERT_REDUCE": (
                _step(MajorOpcode.REDUCE, ReduceSubopcode.EXPERT_SUM),
            ),
            "FP4_QDQ": (
                _step(MajorOpcode.VECTOR, VectorSubopcode.FP4_QDQ),
            ),
            "FP8_LINEAR": (
                _step(MajorOpcode.ROM_MATMUL, ROMMatmulSubopcode.DENSE),
            ),
            "FP8_QDQ": (
                _step(MajorOpcode.VECTOR, VectorSubopcode.FP8_QDQ),
            ),
            "FP8_SWIGLU": (
                _step(MajorOpcode.ROM_MATMUL, ROMMatmulSubopcode.PAIRED_DENSE),
                _step(MajorOpcode.VECTOR, VectorSubopcode.SILU_GATE),
                _step(MajorOpcode.ROM_MATMUL, ROMMatmulSubopcode.DENSE),
            ),
            "GROUPED_OUTPUT_PROJECT": (
                _step(MajorOpcode.ROM_MATMUL, ROMMatmulSubopcode.GROUPED),
            ),
            "HADAMARD_ROTATE": (
                _step(MajorOpcode.VECTOR, VectorSubopcode.HADAMARD_128),
            ),
            "HASH_ROUTE": (
                _step(MajorOpcode.ROUTE, RouteSubopcode.HASH_LOOKUP),
            ),
            "HC_EXPAND": (
                _step(MajorOpcode.VECTOR, VectorSubopcode.COPY_EXPAND),
            ),
            "HC_HEAD": (
                _step(MajorOpcode.ROM_MATMUL, ROMMatmulSubopcode.DENSE),
                _step(MajorOpcode.VECTOR, VectorSubopcode.HC_HEAD_ACTIVATE),
                _step(MajorOpcode.REDUCE, ReduceSubopcode.HC_SUM),
            ),
            "HC_POST": (
                _step(MajorOpcode.VECTOR, VectorSubopcode.HC_POST),
                _step(MajorOpcode.REDUCE, ReduceSubopcode.HC_SUM),
            ),
            "HC_PRE": (
                _step(MajorOpcode.VECTOR, VectorSubopcode.HC_NORMALIZE),
                _step(MajorOpcode.ROM_MATMUL, ROMMatmulSubopcode.DENSE),
                _step(MajorOpcode.VECTOR, VectorSubopcode.HC_SINKHORN),
                _step(MajorOpcode.REDUCE, ReduceSubopcode.HC_SUM),
            ),
            "HEAD_RMS_NORM": (
                _step(MajorOpcode.VECTOR, VectorSubopcode.HEAD_RMS_NORM),
            ),
            "INDEX_SCORE": (
                _step(MajorOpcode.VECTOR, VectorSubopcode.INDEX_SCORE),
            ),
            "INDEX_TOPK": (
                _step(MajorOpcode.ROUTE, RouteSubopcode.INDEX_TOPK),
            ),
            "KV_WINDOW_WRITE": (
                _step(MajorOpcode.KV_READ, KVReadSubopcode.KV_WINDOW),
                _step(MajorOpcode.KV_PREPARE, KVPrepareSubopcode.KV_WINDOW),
                _step(MajorOpcode.COMMIT, CommitSubopcode.KV_WINDOW),
            ),
            "LM_HEAD": (
                _step(MajorOpcode.ROM_MATMUL, ROMMatmulSubopcode.VOCABULARY),
                _step(MajorOpcode.REDUCE, ReduceSubopcode.VOCABULARY_GATHER),
            ),
            "MARKOV_AUTOREGRESSIVE_LOOP": (
                _step(MajorOpcode.ROM_MATMUL, ROMMatmulSubopcode.LOOKUP),
                _step(MajorOpcode.ROM_MATMUL, ROMMatmulSubopcode.VOCABULARY),
                _step(MajorOpcode.VECTOR, VectorSubopcode.BINARY32_ADD),
                _step(MajorOpcode.VECTOR, VectorSubopcode.SAMPLE),
            ),
            "MXFP4_SWIGLU": (
                _step(MajorOpcode.ROM_MATMUL, ROMMatmulSubopcode.PAIRED_ROUTED),
                _step(MajorOpcode.VECTOR, VectorSubopcode.SILU_GATE),
                _step(MajorOpcode.ROM_MATMUL, ROMMatmulSubopcode.ROUTED),
            ),
            "RMS_NORM": (
                _step(MajorOpcode.VECTOR, VectorSubopcode.RMS_NORM),
            ),
            "ROPE_APPLY": (
                _step(MajorOpcode.VECTOR, VectorSubopcode.ROPE_APPLY),
            ),
            "ROPE_INVERSE": (
                _step(MajorOpcode.VECTOR, VectorSubopcode.ROPE_INVERSE),
            ),
            "ROUTER_SCORE": (
                _step(MajorOpcode.ROM_MATMUL, ROMMatmulSubopcode.DENSE),
            ),
            "ROUTER_WEIGHT_NORMALIZE": (
                _step(MajorOpcode.ROUTE, RouteSubopcode.WEIGHT_NORMALIZE),
            ),
            "SAMPLE": (
                _step(MajorOpcode.VECTOR, VectorSubopcode.SAMPLE),
            ),
            "SPARSE_ATTENTION": (
                _step(MajorOpcode.ROUTE, RouteSubopcode.SPARSE_GATHER),
                _step(MajorOpcode.VECTOR, VectorSubopcode.SPARSE_ATTEND),
            ),
            "SQRT_SOFTPLUS": (
                _step(MajorOpcode.VECTOR, VectorSubopcode.SQRT_SOFTPLUS),
            ),
            "TARGET_HIDDEN_CAPTURE": (
                _step(MajorOpcode.REDUCE, ReduceSubopcode.HC_MEAN),
                _step(MajorOpcode.VECTOR, VectorSubopcode.TARGET_CAPTURE),
            ),
            "TOKEN_EMBED": (
                _step(MajorOpcode.ROM_MATMUL, ROMMatmulSubopcode.LOOKUP),
                _step(MajorOpcode.REDUCE, ReduceSubopcode.PARTITION_SUM),
            ),
            "WINDOW_INDEX": (
                _step(MajorOpcode.ROUTE, RouteSubopcode.WINDOW_INDEX),
            ),
        }
    )
)


def subopcode_name(major_opcode: MajorOpcode, subopcode: int) -> str:
    """Return the qualified subopcode name or fail on an illegal pair."""

    try:
        enum_type = SUBOPCODE_ENUMS[major_opcode]
        return enum_type(subopcode).name
    except (KeyError, ValueError) as exc:
        raise HardwareISAError(
            f"illegal subopcode 0x{subopcode:02x} for {major_opcode.name}"
        ) from exc


def validate_operator_mapping(operator_kinds: Iterable[str]) -> None:
    """Require exact one-to-one coverage of a semantic operator catalog."""

    kinds = tuple(operator_kinds)
    if any(type(kind) is not str or not kind for kind in kinds):
        raise HardwareISAError("operator kinds must be non-empty strings")
    if len(kinds) != len(set(kinds)):
        raise HardwareISAError("operator kind catalog contains duplicates")
    expected = set(kinds)
    mapped = set(DEEPSEEK_V4_OPERATOR_LOWERING)
    if expected != mapped:
        missing = sorted(expected - mapped)
        extra = sorted(mapped - expected)
        raise HardwareISAError(
            f"hardware lowering coverage differs: missing={missing}, extra={extra}"
        )
    for kind, steps in DEEPSEEK_V4_OPERATOR_LOWERING.items():
        if not steps:
            raise HardwareISAError(f"operator {kind} has an empty lowering")
        for step in steps:
            if type(step) is not LoweringStep:
                raise HardwareISAError(f"operator {kind} has an untyped lowering step")
            subopcode_name(step.major_opcode, step.subopcode)
            if step.major_opcode in {
                MajorOpcode.STAGE_SEND,
                MajorOpcode.COMPLETE,
            }:
                raise HardwareISAError(
                    f"operator {kind} illegally owns program termination"
                )


def lowering_manifest(
    *, semantic_graph_contract_id: str, operator_kinds: Iterable[str]
) -> dict[str, object]:
    """Build the deterministic semantic-IR to hardware-ISA bridge contract."""

    if (
        type(semantic_graph_contract_id) is not str
        or len(semantic_graph_contract_id) != 64
    ):
        raise HardwareISAError("semantic graph contract ID must be 64 hex characters")
    try:
        bytes.fromhex(semantic_graph_contract_id)
    except ValueError as exc:
        raise HardwareISAError("semantic graph contract ID is not hexadecimal") from exc
    kinds = tuple(operator_kinds)
    validate_operator_mapping(kinds)
    mappings = []
    for kind in sorted(DEEPSEEK_V4_OPERATOR_LOWERING):
        steps = DEEPSEEK_V4_OPERATOR_LOWERING[kind]
        mappings.append(
            {
                "kind": kind,
                "sequence": [
                    {
                        "major_opcode": step.major_opcode.name,
                        "subopcode": subopcode_name(
                            step.major_opcode, step.subopcode
                        ),
                    }
                    for step in steps
                ],
            }
        )
    result: dict[str, object] = {
        "abi": {"major": ABI_MAJOR, "minor": ABI_MINOR},
        "descriptor_schema_version": DESCRIPTOR_SCHEMA_VERSION,
        "execution_status": "structural_lowering_only_pending_bound_descriptors",
        "mapped_kind_count": len(mappings),
        "mappings": mappings,
        "semantic_graph_contract_id": semantic_graph_contract_id,
        "status_nonclaims": [
            "artifact_driven_service_execution",
            "certified_schedule",
            "cycle_latency_or_throughput",
            "physical_address_or_capacity_legality",
            "rtl_microprogram_execution",
        ],
    }
    canonical = json.dumps(
        result, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    result["lowering_sha256"] = hashlib.sha256(canonical).hexdigest()
    return result


def _uint32(value: object, label: str) -> int:
    if type(value) is not int or not 0 <= value <= 0xFFFFFFFF:
        raise HardwareISAError(f"{label} must be an exact uint32")
    return value


def _validate_instruction(instruction: object, index: int) -> Instruction:
    if type(instruction) is not Instruction:
        raise HardwareISAError(f"instruction {index} must be an exact Instruction")
    if type(instruction.major_opcode) is not MajorOpcode:
        raise HardwareISAError(f"instruction {index} has an untyped major opcode")
    if type(instruction.subopcode) is not int or not 0 <= instruction.subopcode <= 0xFF:
        raise HardwareISAError(f"instruction {index} subopcode is outside uint8")
    subopcode_name(instruction.major_opcode, instruction.subopcode)
    if type(instruction.flags) is not InstructionFlag:
        raise HardwareISAError(f"instruction {index} flags must be InstructionFlag")
    raw_flags = int(instruction.flags)
    if raw_flags & ~VALID_FLAG_MASK:
        raise HardwareISAError(f"instruction {index} has reserved flag bits")
    for name in _ID_FIELD_NAMES:
        _uint32(getattr(instruction, name), f"instruction {index} {name}")

    flag_pairs = (
        (
            InstructionFlag.PREDICATED,
            instruction.predicate_descriptor_id,
            "predicate descriptor",
        ),
        (
            InstructionFlag.WAIT_DESCRIPTOR,
            instruction.wait_descriptor_id,
            "wait descriptor",
        ),
        (
            InstructionFlag.SIGNAL_TOKEN,
            instruction.signal_token_id,
            "signal token",
        ),
    )
    for flag, value, label in flag_pairs:
        if bool(instruction.flags & flag) != (value != NO_ID):
            raise HardwareISAError(
                f"instruction {index} {label} field/flag validity differs"
            )
    if (
        instruction.flags & InstructionFlag.PREFILL_ONLY
        and instruction.flags & InstructionFlag.DECODE_ONLY
    ):
        raise HardwareISAError(
            f"instruction {index} cannot be both prefill-only and decode-only"
        )

    allowed = _ALLOWED_DATA_FIELDS[instruction.major_opcode]
    if instruction.major_opcode != MajorOpcode.COMPLETE:
        allowed = allowed | _CONTROL_FIELDS
    required = _REQUIRED_FIELDS[instruction.major_opcode]
    for name in _ID_FIELD_NAMES:
        populated = getattr(instruction, name) != NO_ID
        if name in required and not populated:
            raise HardwareISAError(
                f"instruction {index} {instruction.major_opcode.name} requires {name}"
            )
        if populated and name not in allowed:
            raise HardwareISAError(
                f"instruction {index} {instruction.major_opcode.name} forbids {name}"
            )

    state_opcode = instruction.major_opcode in {
        MajorOpcode.KV_PREPARE,
        MajorOpcode.COMMIT,
    }
    if bool(instruction.flags & InstructionFlag.BATCH_ATOMIC) != state_opcode:
        raise HardwareISAError(
            f"instruction {index} batch-atomic flag differs from state-write class"
        )
    if instruction.major_opcode == MajorOpcode.COMPLETE and instruction.flags:
        raise HardwareISAError(f"instruction {index} COMPLETE must have zero flags")
    return instruction


def verify(program: object) -> None:
    """Verify opcode, descriptor, state-commit, and terminal invariants."""

    if type(program) is not Program:
        raise HardwareISAError("program must be an exact Program")
    if type(program.binding_sha256) is not bytes or len(program.binding_sha256) != 32:
        raise HardwareISAError("program binding must be exactly 32 bytes")
    if program.binding_sha256 == bytes(32):
        raise HardwareISAError("program binding must not be the all-zero digest")
    if type(program.instructions) is not tuple:
        raise HardwareISAError("program instructions must be an exact tuple")
    if not 1 <= len(program.instructions) <= MAX_RECORDS:
        raise HardwareISAError("program instruction count is outside the ABI bound")

    outstanding: dict[int, tuple[int, int]] = {}
    signal_tokens: set[int] = set()
    for index, raw_instruction in enumerate(program.instructions):
        instruction = _validate_instruction(raw_instruction, index)
        if instruction.major_opcode == MajorOpcode.COMPLETE and index != len(
            program.instructions
        ) - 1:
            raise HardwareISAError("COMPLETE may appear only in the terminal slot")
        if instruction.signal_token_id != NO_ID:
            if instruction.signal_token_id in signal_tokens:
                raise HardwareISAError(
                    f"instruction {index} reuses signal token {instruction.signal_token_id}"
                )
            signal_tokens.add(instruction.signal_token_id)
        if instruction.major_opcode == MajorOpcode.KV_PREPARE:
            state_id = instruction.state_descriptor_id
            if state_id in outstanding:
                raise HardwareISAError(
                    f"instruction {index} prepares already-pending state {state_id}"
                )
            outstanding[state_id] = (
                instruction.subopcode,
                instruction.predicate_descriptor_id,
            )
        elif instruction.major_opcode == MajorOpcode.COMMIT:
            state_id = instruction.state_descriptor_id
            expected = outstanding.get(state_id)
            actual = (instruction.subopcode, instruction.predicate_descriptor_id)
            if expected is None:
                raise HardwareISAError(
                    f"instruction {index} commits state {state_id} without prepare"
                )
            if expected != actual:
                raise HardwareISAError(
                    f"instruction {index} commit class or predicate differs from prepare"
                )
            del outstanding[state_id]

    if program.instructions[-1].major_opcode != MajorOpcode.COMPLETE:
        raise HardwareISAError("program lacks one terminal COMPLETE")
    if outstanding:
        raise HardwareISAError(
            f"program completes with uncommitted state descriptors {sorted(outstanding)}"
        )
    stage_send_positions = [
        index
        for index, instruction in enumerate(program.instructions)
        if instruction.major_opcode == MajorOpcode.STAGE_SEND
    ]
    if len(stage_send_positions) > 1:
        raise HardwareISAError("program contains more than one STAGE_SEND")
    if stage_send_positions and stage_send_positions[0] != len(program.instructions) - 2:
        raise HardwareISAError("STAGE_SEND must immediately precede COMPLETE")


def _record_prefix(instruction: Instruction) -> bytes:
    return struct.pack(
        "<BBH14I",
        int(instruction.major_opcode),
        instruction.subopcode,
        int(instruction.flags),
        instruction.predicate_descriptor_id,
        instruction.destination_buffer_id,
        instruction.source0_buffer_id,
        instruction.source1_buffer_id,
        instruction.auxiliary_buffer_id,
        instruction.tensor_descriptor_id,
        instruction.shape_descriptor_id,
        instruction.numeric_descriptor_id,
        instruction.state_descriptor_id,
        instruction.schedule_descriptor_id,
        instruction.wait_descriptor_id,
        instruction.signal_token_id,
        instruction.operator_descriptor_id,
        0,
    )


def encode(program: Program) -> bytes:
    """Encode a verified program into the canonical little-endian wire ABI."""

    verify(program)
    records: list[bytes] = []
    for instruction in program.instructions:
        prefix = _record_prefix(instruction)
        records.append(prefix + struct.pack("<I", zlib.crc32(prefix) & 0xFFFFFFFF))
    body = b"".join(records)
    return HEADER.pack(
        MAGIC,
        ABI_MAJOR,
        ABI_MINOR,
        HEADER.size,
        RECORD.size,
        0,
        len(program.instructions),
        DESCRIPTOR_SCHEMA_VERSION,
        hashlib.sha256(body).digest(),
        program.binding_sha256,
        bytes(8),
    ) + body


def decode(payload: bytes) -> Program:
    """Decode, integrity-check, and semantically verify a hardware program."""

    if type(payload) is not bytes or len(payload) < HEADER.size:
        raise HardwareISAError("hardware program is truncated or not exact bytes")
    (
        magic,
        major,
        minor,
        header_size,
        record_size,
        header_flags,
        count,
        descriptor_schema,
        expected_body_sha256,
        binding_sha256,
        header_reserved,
    ) = HEADER.unpack_from(payload)
    if magic != MAGIC:
        raise HardwareISAError("hardware program magic differs")
    if (major, minor) != (ABI_MAJOR, ABI_MINOR):
        raise HardwareISAError(
            f"unsupported hardware ISA {major}.{minor}; expected {ABI_MAJOR}.{ABI_MINOR}"
        )
    if header_size != HEADER.size or record_size != RECORD.size:
        raise HardwareISAError("hardware program record geometry differs")
    if header_flags != 0 or header_reserved != bytes(8):
        raise HardwareISAError("hardware program header has nonzero reserved fields")
    if descriptor_schema != DESCRIPTOR_SCHEMA_VERSION:
        raise HardwareISAError("hardware program descriptor schema differs")
    if not 1 <= count <= MAX_RECORDS:
        raise HardwareISAError("hardware program instruction count is outside the ABI bound")
    body = payload[HEADER.size :]
    if len(body) != count * RECORD.size:
        raise HardwareISAError("hardware program body length differs from its header")
    if hashlib.sha256(body).digest() != expected_body_sha256:
        raise HardwareISAError("hardware program body SHA-256 differs")

    decoded: list[Instruction] = []
    for index in range(count):
        record = body[index * RECORD.size : (index + 1) * RECORD.size]
        prefix = record[:-4]
        expected_crc = int.from_bytes(record[-4:], "little")
        if zlib.crc32(prefix) & 0xFFFFFFFF != expected_crc:
            raise HardwareISAError(f"instruction {index} CRC32 differs")
        values = RECORD.unpack(record)
        major_raw, subopcode, raw_flags = values[:3]
        ids = values[3:16]
        reserved = values[16]
        if reserved != 0:
            raise HardwareISAError(f"instruction {index} reserved word is nonzero")
        try:
            major_opcode = MajorOpcode(major_raw)
        except ValueError as exc:
            raise HardwareISAError(
                f"instruction {index} has unknown major opcode 0x{major_raw:02x}"
            ) from exc
        if raw_flags & ~VALID_FLAG_MASK:
            raise HardwareISAError(f"instruction {index} has reserved flag bits")
        decoded.append(
            Instruction(
                major_opcode,
                subopcode,
                InstructionFlag(raw_flags),
                *ids,
            )
        )
    program = Program(binding_sha256, tuple(decoded))
    verify(program)
    return program


def disassemble(program: Program) -> str:
    """Render descriptor IDs without pretending they are physical addresses."""

    verify(program)

    def shown(value: int) -> str:
        return "-" if value == NO_ID else str(value)

    lines = [
        f"# OpenTallas hardware descriptor ISA {ABI_MAJOR}.{ABI_MINOR}",
        f"# binding_sha256={program.binding_sha256.hex()}",
    ]
    for pc, instruction in enumerate(program.instructions):
        lines.append(
            f"{pc:06d} {instruction.major_opcode.name}."
            f"{subopcode_name(instruction.major_opcode, instruction.subopcode):<24} "
            f"flags=0x{int(instruction.flags):04x} "
            f"dst={shown(instruction.destination_buffer_id)} "
            f"src0={shown(instruction.source0_buffer_id)} "
            f"src1={shown(instruction.source1_buffer_id)} "
            f"aux={shown(instruction.auxiliary_buffer_id)} "
            f"tensor_desc={shown(instruction.tensor_descriptor_id)} "
            f"shape_desc={shown(instruction.shape_descriptor_id)} "
            f"numeric_desc={shown(instruction.numeric_descriptor_id)} "
            f"state_desc={shown(instruction.state_descriptor_id)} "
            f"schedule_desc={shown(instruction.schedule_descriptor_id)} "
            f"operator_desc={shown(instruction.operator_descriptor_id)}"
        )
    return "\n".join(lines) + "\n"


__all__ = [
    "ABI_MAJOR",
    "ABI_MINOR",
    "CommitSubopcode",
    "CompleteSubopcode",
    "DEEPSEEK_V4_OPERATOR_LOWERING",
    "DESCRIPTOR_SCHEMA_VERSION",
    "HEADER",
    "HardwareISAError",
    "Instruction",
    "InstructionFlag",
    "KVPrepareSubopcode",
    "KVReadSubopcode",
    "LoweringStep",
    "MAGIC",
    "MAX_RECORDS",
    "MajorOpcode",
    "NO_ID",
    "Program",
    "RECORD",
    "ROMMatmulSubopcode",
    "ReduceSubopcode",
    "RouteSubopcode",
    "SUBOPCODE_ENUMS",
    "StageSendSubopcode",
    "VALID_FLAG_MASK",
    "VectorSubopcode",
    "decode",
    "disassemble",
    "encode",
    "lowering_manifest",
    "subopcode_name",
    "validate_operator_mapping",
    "verify",
]
