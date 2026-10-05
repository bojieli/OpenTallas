"""Exact grouped-output projection microcode for DeepSeek V4 Flash.

This standalone ABI lowers only the official layer-0 operation
``torch.einsum("bsgd,grd->bsgr", o, wo_a)`` and its group-major flattened
view.  One instruction produces both observable views because flattening is
an alias operation, not a second arithmetic operator.  The following
``wo_b`` projection is deliberately outside this fragment.

The resource contract is bound to the official canonical MP4 application.
It describes every legal tensor-parallel mapping at world sizes 1, 2, 4,
and 8 using real BF16 payload hashes and exact byte segments.  No activation,
expected output, callback, timing value, physical placement, or performance
claim is carried in the program.
"""

from __future__ import annotations

from dataclasses import dataclass, fields, is_dataclass
from enum import IntEnum
import hashlib
from types import MappingProxyType
import struct
import zlib

from compiler.ir.model import canonical_json_bytes


MODEL_ID = "deepseek-v4-flash-0731"
MODEL_REPOSITORY = "deepseek-ai/DeepSeek-V4-Flash-0731"
MODEL_REVISION = "7872f01b1d1fe23eabc4c98b48bffcef5a386062"

MODEL_SOURCE_PATH = "inference/model.py"
MODEL_SOURCE_SHA256 = "c0c19e6c9fa439bac7fbb1c5bc1868232dfd5aa2f439a548d0e33dcc2a9edd3f"
CONVERT_SOURCE_PATH = "inference/convert.py"
CONVERT_SOURCE_SHA256 = (
    "6efe65ebc66b18c9f2656816608f941cacfe20da79c2dee19040ecbee8b42bfe"
)
INFERENCE_CONFIG_PATH = "inference/config.json"
INFERENCE_CONFIG_SHA256 = (
    "c90861f3d10a9e4ef5954f8f1a34c529d480da1c5799f84660028f4e38e14e71"
)
CHECKPOINT_INDEX_PATH = "model.safetensors.index.json"
CHECKPOINT_INDEX_SHA256 = (
    "98efab455cf08dfbbbaaba6f570e1bf10bf927d2b4c3c453a59c2f6f0e3be92b"
)
CHECKPOINT_LOCK_ID = "30b3d07304b92cb26440e5ea9e28dcb06c835dbf35652529fa9a856da07ad760"
CHECKPOINT_LOCK_FILE_SHA256 = (
    "3ea51c39bf788d3ec86b628d050b6d0a82539d85c0672634e7381bf287b9424b"
)
CANONICAL_APPLICATION_ID = (
    "0f0f5177460c599059c971cbfd43e4299d6537f0cedb6055a83b77ecb52e16cb"
)
CANONICAL_APPLICATION_FILE_SHA256 = (
    "d5af2cdfb021c8403c85a8726f13777b1320fff983c206e12f1fdac8d843ebf9"
)
CANONICAL_VERIFICATION_ID = (
    "b20ac53d48714c2328470b45f44b06aed11bed4c6dc7ef48f27185c5ba813f28"
)
CANONICAL_VERIFICATION_FILE_SHA256 = (
    "23091100d7f2b6018fbe823a8349ac68a841c94a613da39dad17c4ee117d4d3f"
)
RAW_LAYER0_WO_A_WEIGHT_SHA256 = (
    "4ed730a5e64d2bf11cd13af4800473cf24ac1113744c0d1d5fdb8d438bded258"
)
RAW_LAYER0_WO_A_SCALE_SHA256 = (
    "96416ed079e48da7b60aca5f5c020b4579124d07262bfc50082a414964a3f345"
)

MAGIC = b"OTGO"
ABI_MAJOR = 1
ABI_MINOR = 0
HEADER = struct.Struct("<4sBBHII")
RECORD = struct.Struct("<BBH8I")
NO_OPERAND = 0xFFFFFFFF

MIN_TOKEN_COUNT = 1
MAX_TOKEN_COUNT = 4
GLOBAL_GROUP_COUNT = 8
GLOBAL_HEAD_COUNT = 64
HEADS_PER_GROUP = 8
HEAD_DIM = 512
GROUP_INPUT_FEATURES = HEADS_PER_GROUP * HEAD_DIM
OUTPUT_RANK_PER_GROUP = 1_024
GLOBAL_OUTPUT_FEATURES = GLOBAL_GROUP_COUNT * OUTPUT_RANK_PER_GROUP
GLOBAL_WEIGHT_SHAPE = (GLOBAL_OUTPUT_FEATURES, GROUP_INPUT_FEATURES)
GLOBAL_WEIGHT_BYTES = GLOBAL_OUTPUT_FEATURES * GROUP_INPUT_FEATURES * 2
CANONICAL_ASSIGNMENT_ROWS = 2_048
CANONICAL_ASSIGNMENT_BYTES = CANONICAL_ASSIGNMENT_ROWS * GROUP_INPUT_FEATURES * 2
ROW_BYTES = GROUP_INPUT_FEATURES * 2
TENSOR_PARALLEL_WORLD_SIZES = (1, 2, 4, 8)

PROGRAM_CONTRACT_SCHEMA = "opentallas.deepseek_v4_grouped_output_program.v1"
PROGRAM_STATUS = "exact_grouped_output_projection_program_contract"
SOURCE_CONTRACT_SCHEMA = "opentallas.deepseek_v4_grouped_output_source.v1"
SOURCE_CONTRACT_STATUS = "official_source_and_canonical_resource_bindings"

SOURCE_OPERATIONS = (
    "attention_group_view",
    "weight_group_view",
    "grouped_einsum_bsgd_grd_to_bsgr",
    "group_major_flatten_alias",
)
EXPLICIT_NONCLAIMS = (
    "bandwidth",
    "checkpoint_execution",
    "cycle_accuracy",
    "cycle_latency",
    "end_to_end_model_execution",
    "full_attention_execution",
    "full_transformer_block_execution",
    "nvidia_comparison",
    "numeric_execution",
    "output_b_projection",
    "physical_schedule",
    "physical_topology",
    "ppa",
    "rtl_execution",
    "tensor_parallel_collective",
)


class Register(IntEnum):
    """Typed state slots in the grouped-output fragment."""

    GROUPED_ATTENTION_INPUT = 0
    GROUPED_OUTPUT = 1
    FLATTENED_OUTPUT = 2


class Resource(IntEnum):
    """Artifact slot resolved to one local canonical layer-0 weight."""

    LAYER0_WO_A_LOCAL_BF16 = 0


class Opcode(IntEnum):
    """The complete v1 operator set for this standalone fragment."""

    GROUPED_OUTPUT_PROJECT = 0x30
    COMPLETE = 0xFF


class DeepSeekV4GroupedOutputMicrocodeError(ValueError):
    """Raised when grouped-output microcode or a typed contract drifts."""


@dataclass(frozen=True)
class Instruction:
    """One fixed-width grouped-output instruction."""

    opcode: Opcode | int
    destination0: Register | int = NO_OPERAND
    destination1: Register | int = NO_OPERAND
    source: Register | int = NO_OPERAND
    resource0: Resource | int = NO_OPERAND
    immediate0: int = 0
    immediate1: int = 0
    immediate2: int = 0
    immediate3: int = 0
    flags: int = 0


@dataclass(frozen=True)
class TensorSpec:
    """Concrete tensor type, shape, liveness, and alias identity."""

    register: Register
    dtype: str
    shape: tuple[int, ...]
    live_at_complete: bool
    evidence_observable: bool
    alias_of: Register | None = None


@dataclass(frozen=True)
class CanonicalAssignment:
    """One official MP4 BF16 assignment and its raw source slices."""

    rank: int
    path: str
    shape: tuple[int, int]
    size_bytes: int
    content_sha256: str
    raw_row_start: int
    raw_row_stop: int
    scale_row_start: int
    scale_row_stop: int


@dataclass(frozen=True)
class ResourceSegment:
    """A byte-exact segment of one canonical MP4 assignment."""

    assignment_rank: int
    path: str
    byte_offset: int
    size_bytes: int
    global_row_start: int
    global_row_stop: int
    content_sha256: str


@dataclass(frozen=True)
class TopologyMapping:
    """One legal local-weight mapping at a tensor-parallel topology."""

    world_size: int
    rank: int
    local_group_count: int
    global_group_start: int
    global_group_stop: int
    global_row_start: int
    global_row_stop: int
    shape: tuple[int, int]
    size_bytes: int
    content_sha256: str
    segments: tuple[ResourceSegment, ...]


@dataclass(frozen=True)
class ResourceSpec:
    """The authenticated local learned resource used by the opcode."""

    resource: Resource
    role: str
    dtype: str
    shape: tuple[int, int]
    size_bytes: int
    checkpoint_derived: bool
    world_size: int
    rank: int
    global_group_start: int
    global_group_stop: int
    global_row_start: int
    global_row_stop: int
    content_sha256: str
    canonical_application_id: str
    segments: tuple[ResourceSegment, ...]


_CANONICAL_ASSIGNMENT_HASHES = (
    "eefc9e67cf4cffd43050c96006bdafd37802cf3059678808f0fae2920bf9cf7b",
    "ab08dafc884593f7b4526c3ad7a74c551ca7eece7414cce2432db782f4c7e016",
    "d9abb5935224997d525ad2889e1082e056515aababfea32492476d7ec26476fc",
    "0bee532ef7196984f664e07e9442adbe073ba34f8fdd5f6afb4b9974503f446b",
)

CANONICAL_ASSIGNMENTS = tuple(
    CanonicalAssignment(
        rank=rank,
        path=f"ranks/rank-{rank:03d}/layers.0.attn.wo_a.weight.bin",
        shape=(CANONICAL_ASSIGNMENT_ROWS, GROUP_INPUT_FEATURES),
        size_bytes=CANONICAL_ASSIGNMENT_BYTES,
        content_sha256=content_sha256,
        raw_row_start=rank * CANONICAL_ASSIGNMENT_ROWS,
        raw_row_stop=(rank + 1) * CANONICAL_ASSIGNMENT_ROWS,
        scale_row_start=rank * 16,
        scale_row_stop=(rank + 1) * 16,
    )
    for rank, content_sha256 in enumerate(_CANONICAL_ASSIGNMENT_HASHES)
)

_MAPPING_CONTENT_SHA256 = {
    (1, 0): "8e983ca6e21f951c56e644f036d5ab255e7aa429aac3a510b9773b34c52f48a3",
    (2, 0): "3d6f5ff6b1493268a914a8644e7a4f6a1f9aeb26dda0b5009c2daf473d051a06",
    (2, 1): "e4018706e3435505b5deeb96a123f9defde1dde0b6fa0cfe9b8496dca3905361",
    (4, 0): _CANONICAL_ASSIGNMENT_HASHES[0],
    (4, 1): _CANONICAL_ASSIGNMENT_HASHES[1],
    (4, 2): _CANONICAL_ASSIGNMENT_HASHES[2],
    (4, 3): _CANONICAL_ASSIGNMENT_HASHES[3],
    (8, 0): "60ddeeab2ee7f73bf695bea8e4a27bebb89bc5debec2bd6c8031f57b0f95091a",
    (8, 1): "fbd7d95f857d7820675a25fb24280e538d924a8ff2a93d66534b1c4ca78e773d",
    (8, 2): "7f015b095b13a6475d7604f7e0a4f88d6ceae6c6e43719e70a71387139fbb291",
    (8, 3): "864a89722a72a8c5491248540fbb55788cbc21906d83941f346faa2f65ace46f",
    (8, 4): "841368c516a3a4d88fe0a21779f1eafa5a7d525e818f048319fd666cbc343a27",
    (8, 5): "a4e0ccbc47c2ba43939ce139fc0be8ee8a277c0b7f8514707da5108da7ba59f1",
    (8, 6): "81fbf8df07170139e5255dcad1ea95dbde1cfd9dbc0f007eae188362c99a2f67",
    (8, 7): "16f7db1662c18feda343cfabb951807e06b6de746c05f218f8e72befb6831768",
}
MAPPING_CONTENT_SHA256 = MappingProxyType(_MAPPING_CONTENT_SHA256)


def _strict_contract_equal(value: object, expected: object) -> bool:
    """Compare contracts without bool/int, enum/int, or container aliases."""

    if type(value) is not type(expected):
        return False
    if isinstance(expected, dict):
        if (
            value.keys() != expected.keys()
            or any(type(key) is not str for key in value)
            or any(type(key) is not str for key in expected)
        ):
            return False
        return all(
            _strict_contract_equal(value[key], expected_item)
            for key, expected_item in expected.items()
        )
    if isinstance(expected, (list, tuple)):
        return len(value) == len(expected) and all(
            _strict_contract_equal(actual_item, expected_item)
            for actual_item, expected_item in zip(value, expected, strict=True)
        )
    if is_dataclass(expected) and not isinstance(expected, type):
        return all(
            _strict_contract_equal(
                getattr(value, field.name),
                getattr(expected, field.name),
            )
            for field in fields(expected)
        )
    return value == expected


def validate_topology(world_size: int, rank: int) -> None:
    """Require one of the fifteen legal tensor-parallel mappings."""

    if type(world_size) is not int or world_size not in TENSOR_PARALLEL_WORLD_SIZES:
        raise DeepSeekV4GroupedOutputMicrocodeError(
            "world_size must be exactly 1, 2, 4, or 8"
        )
    if type(rank) is not int or not 0 <= rank < world_size:
        raise DeepSeekV4GroupedOutputMicrocodeError(
            f"rank must be an integer in [0, {world_size - 1}]"
        )


def validate_token_count(token_count: int) -> None:
    """Require the bounded flattened token count supported by this ABI."""

    if (
        type(token_count) is not int
        or not MIN_TOKEN_COUNT <= token_count <= MAX_TOKEN_COUNT
    ):
        raise DeepSeekV4GroupedOutputMicrocodeError(
            f"token_count must be an integer in [{MIN_TOKEN_COUNT}, {MAX_TOKEN_COUNT}]"
        )


def canonical_assignment_contract() -> tuple[CanonicalAssignment, ...]:
    """Return all four official layer-0 MP4 BF16 assignments."""

    return CANONICAL_ASSIGNMENTS


def verify_canonical_assignment_contract(value: object) -> None:
    if not _strict_contract_equal(value, canonical_assignment_contract()):
        raise DeepSeekV4GroupedOutputMicrocodeError(
            "canonical wo_a assignments differ from the official frozen contract"
        )


def _segment_content_sha256(
    assignment: CanonicalAssignment,
    global_row_start: int,
    global_row_stop: int,
) -> str:
    if (
        global_row_start == assignment.raw_row_start
        and global_row_stop == assignment.raw_row_stop
    ):
        return assignment.content_sha256
    if global_row_stop - global_row_start == CANONICAL_ASSIGNMENT_ROWS // 2:
        return _MAPPING_CONTENT_SHA256[(8, global_row_start // 1_024)]
    raise RuntimeError("unsupported canonical assignment segment")


def _mapping_segments(
    global_row_start: int,
    global_row_stop: int,
) -> tuple[ResourceSegment, ...]:
    segments: list[ResourceSegment] = []
    for assignment in CANONICAL_ASSIGNMENTS:
        segment_start = max(global_row_start, assignment.raw_row_start)
        segment_stop = min(global_row_stop, assignment.raw_row_stop)
        if segment_start >= segment_stop:
            continue
        byte_offset = (segment_start - assignment.raw_row_start) * ROW_BYTES
        size_bytes = (segment_stop - segment_start) * ROW_BYTES
        segments.append(
            ResourceSegment(
                assignment_rank=assignment.rank,
                path=assignment.path,
                byte_offset=byte_offset,
                size_bytes=size_bytes,
                global_row_start=segment_start,
                global_row_stop=segment_stop,
                content_sha256=_segment_content_sha256(
                    assignment,
                    segment_start,
                    segment_stop,
                ),
            )
        )
    if (
        not segments
        or segments[0].global_row_start != global_row_start
        or segments[-1].global_row_stop != global_row_stop
        or any(
            left.global_row_stop != right.global_row_start
            for left, right in zip(segments, segments[1:])
        )
        or sum(segment.size_bytes for segment in segments)
        != (global_row_stop - global_row_start) * ROW_BYTES
    ):
        raise RuntimeError("canonical segments do not exactly cover local wo_a")
    return tuple(segments)


def topology_mapping(world_size: int, rank: int) -> TopologyMapping:
    """Return the exact group, row, byte, and digest ownership mapping."""

    validate_topology(world_size, rank)
    local_group_count = GLOBAL_GROUP_COUNT // world_size
    group_start = rank * local_group_count
    group_stop = group_start + local_group_count
    row_start = group_start * OUTPUT_RANK_PER_GROUP
    row_stop = group_stop * OUTPUT_RANK_PER_GROUP
    size_bytes = (row_stop - row_start) * ROW_BYTES
    return TopologyMapping(
        world_size=world_size,
        rank=rank,
        local_group_count=local_group_count,
        global_group_start=group_start,
        global_group_stop=group_stop,
        global_row_start=row_start,
        global_row_stop=row_stop,
        shape=(row_stop - row_start, GROUP_INPUT_FEATURES),
        size_bytes=size_bytes,
        content_sha256=_MAPPING_CONTENT_SHA256[(world_size, rank)],
        segments=_mapping_segments(row_start, row_stop),
    )


def topology_mappings() -> tuple[TopologyMapping, ...]:
    """Return all fifteen legal mappings in world-size/rank order."""

    return tuple(
        topology_mapping(world_size, rank)
        for world_size in TENSOR_PARALLEL_WORLD_SIZES
        for rank in range(world_size)
    )


def verify_topology_mappings(value: object) -> None:
    if not _strict_contract_equal(value, topology_mappings()):
        raise DeepSeekV4GroupedOutputMicrocodeError(
            "tensor-parallel mappings differ from the fifteen frozen mappings"
        )


def tensor_contract(
    token_count: int,
    world_size: int,
    rank: int,
) -> tuple[TensorSpec, ...]:
    """Return the complete typed state for one bounded local-rank command."""

    validate_token_count(token_count)
    mapping = topology_mapping(world_size, rank)
    return (
        TensorSpec(
            Register.GROUPED_ATTENTION_INPUT,
            "BF16",
            (
                token_count,
                mapping.local_group_count * HEADS_PER_GROUP,
                HEAD_DIM,
            ),
            False,
            True,
        ),
        TensorSpec(
            Register.GROUPED_OUTPUT,
            "BF16",
            (token_count, mapping.local_group_count, OUTPUT_RANK_PER_GROUP),
            True,
            True,
        ),
        TensorSpec(
            Register.FLATTENED_OUTPUT,
            "BF16",
            (token_count, mapping.local_group_count * OUTPUT_RANK_PER_GROUP),
            True,
            True,
            alias_of=Register.GROUPED_OUTPUT,
        ),
    )


def verify_tensor_contract(
    value: object,
    token_count: int,
    world_size: int,
    rank: int,
) -> None:
    if not _strict_contract_equal(
        value,
        tensor_contract(token_count, world_size, rank),
    ):
        raise DeepSeekV4GroupedOutputMicrocodeError(
            "grouped-output tensors differ from the exact typed contract"
        )


def resource_contract(world_size: int, rank: int) -> tuple[ResourceSpec, ...]:
    """Return the one authenticated local layer-0 canonical BF16 resource."""

    mapping = topology_mapping(world_size, rank)
    return (
        ResourceSpec(
            resource=Resource.LAYER0_WO_A_LOCAL_BF16,
            role="layers.0.attn.wo_a.weight.local",
            dtype="BF16",
            shape=mapping.shape,
            size_bytes=mapping.size_bytes,
            checkpoint_derived=True,
            world_size=world_size,
            rank=rank,
            global_group_start=mapping.global_group_start,
            global_group_stop=mapping.global_group_stop,
            global_row_start=mapping.global_row_start,
            global_row_stop=mapping.global_row_stop,
            content_sha256=mapping.content_sha256,
            canonical_application_id=CANONICAL_APPLICATION_ID,
            segments=mapping.segments,
        ),
    )


def verify_resource_contract(value: object, world_size: int, rank: int) -> None:
    if not _strict_contract_equal(value, resource_contract(world_size, rank)):
        raise DeepSeekV4GroupedOutputMicrocodeError(
            "local wo_a resource differs from the exact topology binding"
        )


def _expected_program(world_size: int, rank: int) -> tuple[Instruction, ...]:
    mapping = topology_mapping(world_size, rank)
    return (
        Instruction(
            Opcode.GROUPED_OUTPUT_PROJECT,
            destination0=Register.GROUPED_OUTPUT,
            destination1=Register.FLATTENED_OUTPUT,
            source=Register.GROUPED_ATTENTION_INPUT,
            resource0=Resource.LAYER0_WO_A_LOCAL_BF16,
            immediate0=world_size,
            immediate1=rank,
            immediate2=mapping.local_group_count,
            immediate3=OUTPUT_RANK_PER_GROUP,
        ),
        Instruction(Opcode.COMPLETE),
    )


def assemble(world_size: int, rank: int) -> tuple[Instruction, ...]:
    """Assemble the sole legal grouped projection and completion sequence."""

    program = _expected_program(world_size, rank)
    verify(program, world_size, rank)
    return program


def verify(
    instructions: tuple[Instruction, ...],
    world_size: int,
    rank: int,
) -> None:
    """Require exact opcodes, operands, topology immediates, and completion."""

    if not _strict_contract_equal(instructions, _expected_program(world_size, rank)):
        raise DeepSeekV4GroupedOutputMicrocodeError(
            "program does not exactly lower GROUPED_OUTPUT_PROJECT and COMPLETE"
        )


def _operands(instruction: Instruction) -> tuple[int, ...]:
    return (
        int(instruction.destination0),
        int(instruction.destination1),
        int(instruction.source),
        int(instruction.resource0),
        instruction.immediate0,
        instruction.immediate1,
        instruction.immediate2,
        instruction.immediate3,
    )


def encode(
    instructions: tuple[Instruction, ...],
    world_size: int,
    rank: int,
) -> bytes:
    """Encode an exact program with fixed width and a body CRC32."""

    verify(instructions, world_size, rank)
    records: list[bytes] = []
    for index, instruction in enumerate(instructions):
        operands = _operands(instruction)
        if type(instruction.flags) is not int or instruction.flags != 0:
            raise DeepSeekV4GroupedOutputMicrocodeError(
                f"instruction {index} has unsupported flags"
            )
        if any(
            type(value) is not int or not 0 <= value <= 0xFFFFFFFF for value in operands
        ):
            raise DeepSeekV4GroupedOutputMicrocodeError(
                f"instruction {index} has an operand outside uint32"
            )
        records.append(
            RECORD.pack(int(instruction.opcode), instruction.flags, 0, *operands)
        )
    body = b"".join(records)
    return (
        HEADER.pack(
            MAGIC,
            ABI_MAJOR,
            ABI_MINOR,
            RECORD.size,
            len(instructions),
            zlib.crc32(body) & 0xFFFFFFFF,
        )
        + body
    )


def _register(value: int) -> Register | int:
    if value == NO_OPERAND:
        return value
    try:
        return Register(value)
    except ValueError:
        return value


def _resource(value: int) -> Resource | int:
    if value == NO_OPERAND:
        return value
    try:
        return Resource(value)
    except ValueError:
        return value


def decode(payload: bytes) -> tuple[Instruction, ...]:
    """Decode structurally valid v1 bytes; call :func:`verify` for semantics."""

    if type(payload) is not bytes:
        raise DeepSeekV4GroupedOutputMicrocodeError("microcode must be exact bytes")
    if len(payload) < HEADER.size:
        raise DeepSeekV4GroupedOutputMicrocodeError(
            "microcode is shorter than its header"
        )
    magic, major, minor, record_size, count, expected_crc = HEADER.unpack_from(payload)
    if magic != MAGIC:
        raise DeepSeekV4GroupedOutputMicrocodeError("microcode magic mismatch")
    if (major, minor) != (ABI_MAJOR, ABI_MINOR):
        raise DeepSeekV4GroupedOutputMicrocodeError(
            f"unsupported grouped-output ABI {major}.{minor}; expected "
            f"{ABI_MAJOR}.{ABI_MINOR}"
        )
    if record_size != RECORD.size:
        raise DeepSeekV4GroupedOutputMicrocodeError(
            f"unsupported instruction size {record_size}"
        )
    if count == 0 or count > 8:
        raise DeepSeekV4GroupedOutputMicrocodeError(
            "microcode instruction count is outside the ABI bound"
        )
    body = payload[HEADER.size :]
    if len(body) != count * RECORD.size:
        raise DeepSeekV4GroupedOutputMicrocodeError(
            "microcode body length differs from its header"
        )
    if zlib.crc32(body) & 0xFFFFFFFF != expected_crc:
        raise DeepSeekV4GroupedOutputMicrocodeError("microcode CRC32 mismatch")

    result: list[Instruction] = []
    for index in range(count):
        unpacked = RECORD.unpack_from(body, index * RECORD.size)
        opcode_raw, flags, reserved = unpacked[:3]
        if reserved != 0:
            raise DeepSeekV4GroupedOutputMicrocodeError(
                f"instruction {index} has nonzero reserved bits"
            )
        if flags != 0:
            raise DeepSeekV4GroupedOutputMicrocodeError(
                f"instruction {index} has unsupported flags"
            )
        try:
            opcode = Opcode(opcode_raw)
        except ValueError as exc:
            raise DeepSeekV4GroupedOutputMicrocodeError(
                f"instruction {index} has unknown opcode 0x{opcode_raw:02x}"
            ) from exc
        result.append(
            Instruction(
                opcode=opcode,
                destination0=_register(unpacked[3]),
                destination1=_register(unpacked[4]),
                source=_register(unpacked[5]),
                resource0=_resource(unpacked[6]),
                immediate0=unpacked[7],
                immediate1=unpacked[8],
                immediate2=unpacked[9],
                immediate3=unpacked[10],
                flags=flags,
            )
        )
    return tuple(result)


def _assignment_json(assignment: CanonicalAssignment) -> dict[str, object]:
    return {
        "content_sha256": assignment.content_sha256,
        "path": assignment.path,
        "rank": assignment.rank,
        "raw_row_range": [assignment.raw_row_start, assignment.raw_row_stop],
        "scale_row_range": [assignment.scale_row_start, assignment.scale_row_stop],
        "shape": list(assignment.shape),
        "size_bytes": assignment.size_bytes,
    }


def _segment_json(segment: ResourceSegment) -> dict[str, object]:
    return {
        "assignment_rank": segment.assignment_rank,
        "byte_offset": segment.byte_offset,
        "content_sha256": segment.content_sha256,
        "global_row_range": [segment.global_row_start, segment.global_row_stop],
        "path": segment.path,
        "size_bytes": segment.size_bytes,
    }


def build_source_contract() -> dict[str, object]:
    """Build the hash-bound official source and transformation identity."""

    body: dict[str, object] = {
        "canonical_application": {
            "application_id": CANONICAL_APPLICATION_ID,
            "file_sha256": CANONICAL_APPLICATION_FILE_SHA256,
            "status": "complete_official_transform_application",
            "verification_file_sha256": CANONICAL_VERIFICATION_FILE_SHA256,
            "verification_id": CANONICAL_VERIFICATION_ID,
            "verification_status": "full_assignment_match",
        },
        "canonical_assignments": [
            _assignment_json(assignment) for assignment in CANONICAL_ASSIGNMENTS
        ],
        "checkpoint": {
            "index_path": CHECKPOINT_INDEX_PATH,
            "index_sha256": CHECKPOINT_INDEX_SHA256,
            "lock_file_sha256": CHECKPOINT_LOCK_FILE_SHA256,
            "lock_id": CHECKPOINT_LOCK_ID,
            "raw_scale_sha256": RAW_LAYER0_WO_A_SCALE_SHA256,
            "raw_weight_sha256": RAW_LAYER0_WO_A_WEIGHT_SHA256,
        },
        "claim_boundary": (
            "Official source identities, source operator sequence, raw tensor "
            "identities, and canonical BF16 assignment identities only; this "
            "does not claim execution or numerical output agreement."
        ),
        "model_id": MODEL_ID,
        "repository": MODEL_REPOSITORY,
        "revision": MODEL_REVISION,
        "schema": SOURCE_CONTRACT_SCHEMA,
        "source_files": [
            {"path": MODEL_SOURCE_PATH, "sha256": MODEL_SOURCE_SHA256},
            {"path": CONVERT_SOURCE_PATH, "sha256": CONVERT_SOURCE_SHA256},
            {"path": INFERENCE_CONFIG_PATH, "sha256": INFERENCE_CONFIG_SHA256},
        ],
        "source_operations": list(SOURCE_OPERATIONS),
        "status": SOURCE_CONTRACT_STATUS,
        "transform": "dequantize_fp8_e8m0_to_bf16_rne",
    }
    return {
        **body,
        "source_contract_id": hashlib.sha256(canonical_json_bytes(body)).hexdigest(),
    }


def verify_source_contract(value: object) -> None:
    if not _strict_contract_equal(value, build_source_contract()):
        raise DeepSeekV4GroupedOutputMicrocodeError(
            "official grouped-output source contract differs from its frozen identity"
        )


def build_program_contract(world_size: int, rank: int) -> dict[str, object]:
    """Build the hash-bound program, topology, tensor, and resource contract."""

    mapping = topology_mapping(world_size, rank)
    program_bytes = encode(assemble(world_size, rank), world_size, rank)
    source = build_source_contract()
    body: dict[str, object] = {
        "abi": {
            "magic_ascii": MAGIC.decode("ascii"),
            "major": ABI_MAJOR,
            "minor": ABI_MINOR,
            "record_bytes": RECORD.size,
        },
        "claim_boundary": (
            "Exact GROUPED_OUTPUT_PROJECT to grouped and flattened alias views, "
            "then terminal COMPLETE, with typed topology and canonical layer-0 "
            "wo_a binding only; no execution, wo_b, collective, timing, or PPA claim."
        ),
        "dimensions": {
            "global_group_count": GLOBAL_GROUP_COUNT,
            "global_head_count": GLOBAL_HEAD_COUNT,
            "group_input_features": GROUP_INPUT_FEATURES,
            "head_dim": HEAD_DIM,
            "heads_per_group": HEADS_PER_GROUP,
            "maximum_token_count": MAX_TOKEN_COUNT,
            "minimum_token_count": MIN_TOKEN_COUNT,
            "output_rank_per_group": OUTPUT_RANK_PER_GROUP,
        },
        "model_id": MODEL_ID,
        "operator_sequence": [
            Opcode.GROUPED_OUTPUT_PROJECT.name,
            Opcode.COMPLETE.name,
        ],
        "program_bytes": len(program_bytes),
        "program_sha256": hashlib.sha256(program_bytes).hexdigest(),
        "required_nonclaims": list(EXPLICIT_NONCLAIMS),
        "resource": {
            "content_sha256": mapping.content_sha256,
            "segments": [_segment_json(segment) for segment in mapping.segments],
            "shape": list(mapping.shape),
            "size_bytes": mapping.size_bytes,
        },
        "schema": PROGRAM_CONTRACT_SCHEMA,
        "source_contract_id": source["source_contract_id"],
        "status": PROGRAM_STATUS,
        "tensor_views": {
            "flattened_output_alias_of": Register.GROUPED_OUTPUT.name,
            "flattened_output_register": Register.FLATTENED_OUTPUT.name,
            "grouped_output_register": Register.GROUPED_OUTPUT.name,
            "input_register": Register.GROUPED_ATTENTION_INPUT.name,
        },
        "topology": {
            "global_group_range": [
                mapping.global_group_start,
                mapping.global_group_stop,
            ],
            "global_row_range": [mapping.global_row_start, mapping.global_row_stop],
            "local_group_count": mapping.local_group_count,
            "rank": rank,
            "world_size": world_size,
        },
    }
    return {
        **body,
        "contract_id": hashlib.sha256(canonical_json_bytes(body)).hexdigest(),
    }


def verify_program_contract(value: object, world_size: int, rank: int) -> None:
    if not _strict_contract_equal(value, build_program_contract(world_size, rank)):
        raise DeepSeekV4GroupedOutputMicrocodeError(
            "grouped-output program contract differs from its hash-bound definition"
        )


def disassemble(
    instructions: tuple[Instruction, ...],
    world_size: int,
    rank: int,
) -> str:
    """Return the exact human-readable program after semantic verification."""

    verify(instructions, world_size, rank)
    lines = [f"# OpenTallas DeepSeek V4 grouped-output ABI {ABI_MAJOR}.{ABI_MINOR}"]
    for pc, instruction in enumerate(instructions):
        lines.append(
            f"{pc:04d} {Opcode(instruction.opcode).name:<22} "
            f"dst=[{int(instruction.destination0):#010x},"
            f"{int(instruction.destination1):#010x}] "
            f"src={int(instruction.source):#010x} "
            f"resource={int(instruction.resource0):#010x} "
            f"imm=[{instruction.immediate0},{instruction.immediate1},"
            f"{instruction.immediate2},{instruction.immediate3}]"
        )
    return "\n".join(lines) + "\n"


__all__ = [
    "ABI_MAJOR",
    "ABI_MINOR",
    "CANONICAL_APPLICATION_FILE_SHA256",
    "CANONICAL_APPLICATION_ID",
    "CANONICAL_ASSIGNMENTS",
    "CANONICAL_VERIFICATION_FILE_SHA256",
    "CANONICAL_VERIFICATION_ID",
    "CHECKPOINT_INDEX_PATH",
    "CHECKPOINT_INDEX_SHA256",
    "CHECKPOINT_LOCK_FILE_SHA256",
    "CHECKPOINT_LOCK_ID",
    "CONVERT_SOURCE_PATH",
    "CONVERT_SOURCE_SHA256",
    "CanonicalAssignment",
    "DeepSeekV4GroupedOutputMicrocodeError",
    "EXPLICIT_NONCLAIMS",
    "GLOBAL_GROUP_COUNT",
    "GLOBAL_HEAD_COUNT",
    "GLOBAL_OUTPUT_FEATURES",
    "GLOBAL_WEIGHT_BYTES",
    "GLOBAL_WEIGHT_SHAPE",
    "GROUP_INPUT_FEATURES",
    "HEAD_DIM",
    "HEADER",
    "HEADS_PER_GROUP",
    "INFERENCE_CONFIG_PATH",
    "INFERENCE_CONFIG_SHA256",
    "Instruction",
    "MAGIC",
    "MAPPING_CONTENT_SHA256",
    "MAX_TOKEN_COUNT",
    "MIN_TOKEN_COUNT",
    "MODEL_ID",
    "MODEL_REPOSITORY",
    "MODEL_REVISION",
    "MODEL_SOURCE_PATH",
    "MODEL_SOURCE_SHA256",
    "NO_OPERAND",
    "OUTPUT_RANK_PER_GROUP",
    "Opcode",
    "PROGRAM_CONTRACT_SCHEMA",
    "PROGRAM_STATUS",
    "RAW_LAYER0_WO_A_SCALE_SHA256",
    "RAW_LAYER0_WO_A_WEIGHT_SHA256",
    "RECORD",
    "ROW_BYTES",
    "Register",
    "Resource",
    "ResourceSegment",
    "ResourceSpec",
    "SOURCE_CONTRACT_SCHEMA",
    "SOURCE_CONTRACT_STATUS",
    "SOURCE_OPERATIONS",
    "TENSOR_PARALLEL_WORLD_SIZES",
    "TensorSpec",
    "TopologyMapping",
    "assemble",
    "build_program_contract",
    "build_source_contract",
    "canonical_assignment_contract",
    "decode",
    "disassemble",
    "encode",
    "resource_contract",
    "tensor_contract",
    "topology_mapping",
    "topology_mappings",
    "validate_token_count",
    "validate_topology",
    "verify",
    "verify_canonical_assignment_contract",
    "verify_program_contract",
    "verify_resource_contract",
    "verify_source_contract",
    "verify_tensor_contract",
    "verify_topology_mappings",
]
