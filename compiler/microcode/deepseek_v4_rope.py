"""Typed microcode contract for DeepSeek V4 Flash rotary operators.

Every command binds the frozen v2 arithmetic profile, a concrete phasor
profile, all base/YaRN constants, the complete logical tensor shape, and an
explicit request-to-table position policy.  Compressor prefill and decode are
distinct policies: prefill strides table positions by the compression ratio,
while decode encodes the already adjusted ``start_pos + 1 - ratio`` row.

The fixed-width program and its contracts are semantic compiler evidence for
``ROPE_APPLY`` and ``ROPE_INVERSE`` only.  They contain no activation payload,
cycle, latency, bandwidth, placement, RTL, checkpoint-execution, full-model,
or PPA claim.
"""

from __future__ import annotations

from dataclasses import dataclass, fields, is_dataclass
from enum import IntEnum
import hashlib
import struct
from typing import Any
import zlib

from compiler.ir.model import canonical_json_bytes
from runtime.reference.rope import (
    BASE_ROPE_THETA,
    COMPRESSED_ROPE_THETA,
    MAX_BATCH_SIZE,
    MAX_HEAD_COUNT,
    MAX_POSITION,
    MAX_SEQUENCE_LENGTH,
    OFFICIAL_REPOSITORY,
    OFFICIAL_REVISION,
    ROPE_COMPLEX_PAIRS,
    ROPE_DIMENSION,
    ROPE_NUMERIC_PROFILE,
    YARN_BETA_FAST,
    YARN_BETA_SLOW,
    YARN_CORRECTION_HIGH,
    YARN_CORRECTION_LOW,
    YARN_FACTOR,
    YARN_ORIGINAL_SEQUENCE_LENGTH,
)


MAGIC = b"OTRP"
ABI_MAJOR = 1
ABI_MINOR = 0
HEADER = struct.Struct("<4sBBHII")
RECORD = struct.Struct("<BBH" + "I" * 29)
NO_OPERAND = 0xFFFFFFFF
PROGRAM_INSTRUCTION_COUNT = 2

MODEL_ID = "deepseek-v4-flash-0731"
MODEL_REPOSITORY = OFFICIAL_REPOSITORY
MODEL_REVISION = OFFICIAL_REVISION
NUMERIC_PROFILE = ROPE_NUMERIC_PROFILE
NUMERIC_PROFILE_CODE = int.from_bytes(
    hashlib.sha256(NUMERIC_PROFILE.encode("ascii")).digest()[:4],
    "little",
)
PROGRAM_CONTRACT_SCHEMA = "opentallas.deepseek_v4_rope_program.v1"
SUPPORTED_HEAD_WIDTHS = frozenset({64, 128, 512})
SUPPORTED_RANK4_HEAD_COUNTS = frozenset({8, 16, 32, 64})
SUPPORTED_COMPRESSION_RATIOS = frozenset({0, 4, 128})
PHASOR_TABLE_SHAPE = (MAX_SEQUENCE_LENGTH, ROPE_COMPLEX_PAIRS, 2)
PHASOR_TABLE_BYTES = MAX_SEQUENCE_LENGTH * ROPE_COMPLEX_PAIRS * 2 * 4
CHANNEL_SEMANTICS = "preserve_prefix_rotate_final_64_as_adjacent_complex_pairs"
PRESERVED_PREFIX_POLICY = "copy_channels_before_rotary_suffix_bit_exact"

EXPLICIT_NON_CLAIMS = (
    "checkpoint_execution",
    "cycle_accuracy",
    "cycle_latency",
    "dspark_speculative_multi_token_blocks",
    "full_model_execution",
    "nvidia_comparison",
    "physical_bandwidth",
    "physical_placement",
    "physical_schedule",
    "ppa",
    "rtl_execution",
    "semantic_graph_layer_selection",
    "service_engine_execution",
    "target_kernel_execution",
    "throughput",
)


class DeepSeekV4RopeMicrocodeError(ValueError):
    """Raised when a RoPE descriptor, contract, or wire program is ambiguous."""


class Opcode(IntEnum):
    ROPE_APPLY = 0x60
    ROPE_INVERSE = 0x61
    COMPLETE = 0xFF


class Register(IntEnum):
    INPUT = 0
    OUTPUT = 1


class Resource(IntEnum):
    BASE_PHASOR_TABLE = 0
    COMPRESSED_YARN_PHASOR_TABLE = 1


class TensorRole(IntEnum):
    QUERY = 1
    KV = 2
    INDEX_QUERY = 3
    COMPRESSOR_KV = 4
    ATTENTION_OUTPUT = 5
    ROTARY_SUFFIX = 6
    INDEX_COMPRESSOR_KV = 7


class RopeProfile(IntEnum):
    BASE = 1
    COMPRESSED_YARN = 2


class ScalingMode(IntEnum):
    NONE = 0
    YARN = 1


class Phase(IntEnum):
    PREFILL = 1
    DECODE = 2


class PositionPolicy(IntEnum):
    CONSECUTIVE = 1
    COMPRESSOR_PREFILL_RATIO_STRIDE = 2
    COMPRESSOR_DECODE_ADJUSTED = 3


@dataclass(frozen=True, slots=True)
class RopeDescriptor:
    """Complete semantic command encoded in the first microinstruction."""

    opcode: Opcode
    tensor_role: TensorRole
    tensor_rank: int
    batch_count: int
    sequence_length: int
    head_count: int
    head_width: int
    rope_dimension: int
    numeric_profile: str
    profile: RopeProfile
    scaling_mode: ScalingMode
    theta: int
    original_sequence_length: int
    yarn_factor: int
    beta_fast: int
    beta_slow: int
    correction_low: int
    correction_high: int
    phase: Phase
    position_policy: PositionPolicy
    compression_ratio: int
    request_start_position: int
    table_start_position: int
    last_table_position: int
    position_stride: int
    source_sequence_length: int
    source_cutoff: int

    def __post_init__(self) -> None:
        verify_descriptor(self)


@dataclass(frozen=True, slots=True)
class Instruction:
    """One typed instruction in the standalone two-record RoPE program."""

    opcode: Opcode
    destination: Register | int = NO_OPERAND
    source: Register | int = NO_OPERAND
    resource: Resource | int = NO_OPERAND
    descriptor: RopeDescriptor | None = None
    flags: int = 0

    def __post_init__(self) -> None:
        verify_instruction(self)


@dataclass(frozen=True, slots=True)
class TensorSpec:
    register: Register
    dtype: str
    shape: tuple[int, ...]
    access: str
    live_at_complete: bool
    alias_of: Register | None
    preserved_prefix_width: int
    rotary_suffix_width: int
    channel_semantics: str

    def __post_init__(self) -> None:
        _validate_tensor_spec(self)


@dataclass(frozen=True, slots=True)
class ResourceSpec:
    resource: Resource
    dtype: str
    shape: tuple[int, int, int]
    size_bytes: int
    rope_dimension: int
    complex_pair_count: int
    numeric_profile: str
    profile: RopeProfile
    scaling_mode: ScalingMode
    theta: int
    original_sequence_length: int
    yarn_factor: int
    beta_fast: int
    beta_slow: int
    correction_low: int
    correction_high: int
    semantic_sha256: str
    checkpoint_derived: bool

    def __post_init__(self) -> None:
        _validate_resource_spec(self)


@dataclass(frozen=True, slots=True)
class PositionContract:
    phase: Phase
    policy: PositionPolicy
    compression_ratio: int
    request_start_position: int
    table_start_position: int
    last_table_position: int
    position_stride: int
    output_sequence_length: int
    source_sequence_length: int
    source_cutoff: int
    table_position_formula: str

    def __post_init__(self) -> None:
        _validate_position_contract_record(self)


@dataclass(frozen=True, slots=True)
class StateContract:
    mutable_state_reads: tuple[str, ...]
    mutable_state_writes: tuple[str, ...]
    request_inputs: tuple[str, ...]
    phasor_resource: Resource
    output_commit: str
    alias_policy: str
    preserved_prefix_policy: str
    rotary_suffix_width: int

    def __post_init__(self) -> None:
        _validate_state_contract_record(self)


def _is_sha256(value: str) -> bool:
    return len(value) == 64 and all(
        character in "0123456789abcdef" for character in value
    )


def _integer(
    value: object,
    label: str,
    *,
    minimum: int = 0,
    maximum: int = 0xFFFFFFFF,
) -> int:
    if type(value) is not int or not minimum <= value <= maximum:
        raise DeepSeekV4RopeMicrocodeError(
            f"{label} must be an exact integer in [{minimum}, {maximum}]"
        )
    return value


def _validate_tensor_spec(spec: TensorSpec) -> None:
    if type(spec) is not TensorSpec:
        raise DeepSeekV4RopeMicrocodeError("tensor spec must be exact")
    if type(spec.register) is not Register:
        raise DeepSeekV4RopeMicrocodeError("tensor register must be typed")
    if spec.dtype != "BF16" or type(spec.dtype) is not str:
        raise DeepSeekV4RopeMicrocodeError("RoPE tensors must be exact BF16")
    if (
        type(spec.shape) is not tuple
        or len(spec.shape) not in {3, 4}
        or not all(type(value) is int and value > 0 for value in spec.shape)
    ):
        raise DeepSeekV4RopeMicrocodeError(
            "tensor shape must be an immutable positive rank-3/rank-4 tuple"
        )
    if not 1 <= spec.shape[0] <= MAX_BATCH_SIZE:
        raise DeepSeekV4RopeMicrocodeError("tensor batch dimension is outside bounds")
    if not 1 <= spec.shape[1] <= MAX_SEQUENCE_LENGTH:
        raise DeepSeekV4RopeMicrocodeError(
            "tensor sequence dimension is outside bounds"
        )
    if spec.shape[-1] not in SUPPORTED_HEAD_WIDTHS:
        raise DeepSeekV4RopeMicrocodeError("tensor head width is not official")
    if len(spec.shape) == 4 and spec.shape[2] not in SUPPORTED_RANK4_HEAD_COUNTS:
        raise DeepSeekV4RopeMicrocodeError("tensor local head count is not official")
    expected_access = "read_only" if spec.register is Register.INPUT else "write_only"
    expected_live = spec.register is Register.OUTPUT
    if type(spec.access) is not str or spec.access != expected_access:
        raise DeepSeekV4RopeMicrocodeError("tensor register/access authority differs")
    if (
        type(spec.live_at_complete) is not bool
        or spec.live_at_complete is not expected_live
    ):
        raise DeepSeekV4RopeMicrocodeError("tensor register/liveness authority differs")
    if spec.alias_of is not None:
        raise DeepSeekV4RopeMicrocodeError("RoPE tensor registers must not alias")
    expected_prefix_width = spec.shape[-1] - ROPE_DIMENSION
    if (
        type(spec.preserved_prefix_width) is not int
        or spec.preserved_prefix_width != expected_prefix_width
    ):
        raise DeepSeekV4RopeMicrocodeError(
            "tensor preserved-prefix width must equal head_width - rope_dimension"
        )
    if (
        type(spec.rotary_suffix_width) is not int
        or spec.rotary_suffix_width != ROPE_DIMENSION
    ):
        raise DeepSeekV4RopeMicrocodeError(
            f"tensor rotary suffix width must equal {ROPE_DIMENSION}"
        )
    if (
        type(spec.channel_semantics) is not str
        or spec.channel_semantics != CHANNEL_SEMANTICS
    ):
        raise DeepSeekV4RopeMicrocodeError(
            "tensor channel semantics must preserve the prefix and rotate the final 64"
        )


def _validate_resource_spec(spec: ResourceSpec) -> None:
    if type(spec) is not ResourceSpec:
        raise DeepSeekV4RopeMicrocodeError("resource spec must be exact")
    if type(spec.resource) is not Resource or type(spec.profile) is not RopeProfile:
        raise DeepSeekV4RopeMicrocodeError("phasor resource/profile must be typed")
    if type(spec.scaling_mode) is not ScalingMode:
        raise DeepSeekV4RopeMicrocodeError("phasor scaling mode must be typed")
    if spec.dtype != "COMPLEX_BINARY32_PAIR" or type(spec.dtype) is not str:
        raise DeepSeekV4RopeMicrocodeError("phasor dtype differs")
    if type(spec.shape) is not tuple or spec.shape != PHASOR_TABLE_SHAPE:
        raise DeepSeekV4RopeMicrocodeError("phasor table shape differs")
    if type(spec.size_bytes) is not int or spec.size_bytes != PHASOR_TABLE_BYTES:
        raise DeepSeekV4RopeMicrocodeError("phasor table byte size differs")
    if (
        type(spec.rope_dimension) is not int
        or spec.rope_dimension != ROPE_DIMENSION
    ):
        raise DeepSeekV4RopeMicrocodeError("phasor resource rope dimension differs")
    if (
        type(spec.complex_pair_count) is not int
        or spec.complex_pair_count != ROPE_COMPLEX_PAIRS
    ):
        raise DeepSeekV4RopeMicrocodeError(
            "phasor resource complex-pair count differs"
        )
    if type(spec.numeric_profile) is not str or spec.numeric_profile != NUMERIC_PROFILE:
        raise DeepSeekV4RopeMicrocodeError("phasor numeric profile differs")
    expected_resource = _resource_for_profile(spec.profile)
    expected_constants = _profile_constants(spec.profile)
    observed_constants = (
        spec.scaling_mode,
        _integer(spec.theta, "resource.theta"),
        _integer(
            spec.original_sequence_length,
            "resource.original_sequence_length",
        ),
        _integer(spec.yarn_factor, "resource.yarn_factor"),
        _integer(spec.beta_fast, "resource.beta_fast"),
        _integer(spec.beta_slow, "resource.beta_slow"),
        _integer(spec.correction_low, "resource.correction_low"),
        _integer(spec.correction_high, "resource.correction_high"),
    )
    if (
        spec.resource is not expected_resource
        or observed_constants != expected_constants
    ):
        raise DeepSeekV4RopeMicrocodeError(
            "phasor resource and profile constants disagree"
        )
    semantics = {
        "beta_fast": spec.beta_fast,
        "beta_slow": spec.beta_slow,
        "correction_high": spec.correction_high,
        "correction_low": spec.correction_low,
        "numeric_profile": spec.numeric_profile,
        "original_sequence_length": spec.original_sequence_length,
        "profile": spec.profile.name,
        "rope_dimension": ROPE_DIMENSION,
        "scaling_mode": spec.scaling_mode.name,
        "theta": spec.theta,
        "yarn_factor": spec.yarn_factor,
    }
    expected_digest = hashlib.sha256(canonical_json_bytes(semantics)).hexdigest()
    if (
        type(spec.semantic_sha256) is not str
        or not _is_sha256(spec.semantic_sha256)
        or spec.semantic_sha256 != expected_digest
    ):
        raise DeepSeekV4RopeMicrocodeError("phasor semantic digest differs")
    if type(spec.checkpoint_derived) is not bool or spec.checkpoint_derived:
        raise DeepSeekV4RopeMicrocodeError(
            "phasor table is generated, not checkpoint data"
        )


def _validate_position_contract_record(contract: PositionContract) -> None:
    if type(contract) is not PositionContract:
        raise DeepSeekV4RopeMicrocodeError("position contract must be exact")
    if type(contract.phase) is not Phase or type(contract.policy) is not PositionPolicy:
        raise DeepSeekV4RopeMicrocodeError("position phase/policy must be typed")
    ratio = _integer(contract.compression_ratio, "position.compression_ratio")
    if ratio not in SUPPORTED_COMPRESSION_RATIOS:
        raise DeepSeekV4RopeMicrocodeError("position compression ratio differs")
    request = _integer(
        contract.request_start_position,
        "position.request_start_position",
        maximum=MAX_POSITION,
    )
    table_start = _integer(
        contract.table_start_position,
        "position.table_start_position",
        maximum=MAX_POSITION,
    )
    table_last = _integer(
        contract.last_table_position,
        "position.last_table_position",
        maximum=MAX_POSITION,
    )
    stride = _integer(
        contract.position_stride,
        "position.position_stride",
        minimum=1,
    )
    output_length = _integer(
        contract.output_sequence_length,
        "position.output_sequence_length",
        minimum=1,
        maximum=MAX_SEQUENCE_LENGTH,
    )
    source_length = _integer(
        contract.source_sequence_length,
        "position.source_sequence_length",
        minimum=1,
        maximum=MAX_SEQUENCE_LENGTH,
    )
    cutoff = _integer(
        contract.source_cutoff,
        "position.source_cutoff",
        minimum=1,
        maximum=MAX_SEQUENCE_LENGTH,
    )
    formulas = {
        PositionPolicy.CONSECUTIVE: (
            "table_start=request_start; table[i]=table_start+i"
        ),
        PositionPolicy.COMPRESSOR_PREFILL_RATIO_STRIDE: (
            "table_start=0; table[i]=i*compression_ratio"
        ),
        PositionPolicy.COMPRESSOR_DECODE_ADJUSTED: (
            "table_start=request_start+1-compression_ratio; table[0]=table_start"
        ),
    }
    if (
        type(contract.table_position_formula) is not str
        or contract.table_position_formula != formulas[contract.policy]
    ):
        raise DeepSeekV4RopeMicrocodeError("position formula differs from policy")
    if table_last != table_start + (output_length - 1) * stride:
        raise DeepSeekV4RopeMicrocodeError("position range does not reconcile")
    if contract.policy is PositionPolicy.CONSECUTIVE:
        if stride != 1 or source_length != output_length or cutoff != output_length:
            raise DeepSeekV4RopeMicrocodeError("consecutive position span differs")
        if contract.phase is Phase.PREFILL:
            if request != 0 or table_start != 0:
                raise DeepSeekV4RopeMicrocodeError(
                    "prefill position must start at zero"
                )
        elif output_length != 1 or table_start != request:
            raise DeepSeekV4RopeMicrocodeError("decode consecutive position differs")
    elif contract.policy is PositionPolicy.COMPRESSOR_PREFILL_RATIO_STRIDE:
        expected_cutoff = source_length - source_length % ratio if ratio else 0
        if (
            contract.phase is not Phase.PREFILL
            or ratio not in {4, 128}
            or stride != ratio
            or request != 0
            or table_start != 0
            or cutoff != expected_cutoff
            or output_length != cutoff // ratio
        ):
            raise DeepSeekV4RopeMicrocodeError(
                "compressor prefill position span differs"
            )
    elif (
        contract.phase is not Phase.DECODE
        or ratio not in {4, 128}
        or stride != 1
        or output_length != 1
        or source_length != 1
        or cutoff != 1
        or request + 1 < ratio
        or (request + 1) % ratio != 0
        or table_start != request + 1 - ratio
    ):
        raise DeepSeekV4RopeMicrocodeError(
            "compressor decode adjusted position differs"
        )


def _validate_state_contract_record(contract: StateContract) -> None:
    if type(contract) is not StateContract:
        raise DeepSeekV4RopeMicrocodeError("state contract must be exact")
    if (
        type(contract.mutable_state_reads) is not tuple
        or contract.mutable_state_reads != ()
    ):
        raise DeepSeekV4RopeMicrocodeError("RoPE has no mutable state reads")
    if (
        type(contract.mutable_state_writes) is not tuple
        or contract.mutable_state_writes != ()
    ):
        raise DeepSeekV4RopeMicrocodeError("RoPE has no mutable state writes")
    if type(contract.request_inputs) is not tuple or contract.request_inputs != (
        "request.start_pos",
    ):
        raise DeepSeekV4RopeMicrocodeError("RoPE request input binding differs")
    if type(contract.phasor_resource) is not Resource:
        raise DeepSeekV4RopeMicrocodeError("state phasor resource must be typed")
    if (
        type(contract.output_commit) is not str
        or contract.output_commit != "atomic_after_complete_tensor_rotation"
    ):
        raise DeepSeekV4RopeMicrocodeError("RoPE output commit policy differs")
    if (
        type(contract.alias_policy) is not str
        or contract.alias_policy != "distinct_input_output_registers_no_in_place_alias"
    ):
        raise DeepSeekV4RopeMicrocodeError("RoPE alias policy differs")
    if (
        type(contract.preserved_prefix_policy) is not str
        or contract.preserved_prefix_policy != PRESERVED_PREFIX_POLICY
    ):
        raise DeepSeekV4RopeMicrocodeError("RoPE preserved-prefix policy differs")
    if (
        type(contract.rotary_suffix_width) is not int
        or contract.rotary_suffix_width != ROPE_DIMENSION
    ):
        raise DeepSeekV4RopeMicrocodeError(
            f"RoPE state contract rotary suffix must equal {ROPE_DIMENSION}"
        )


def _strict_equal(value: object, expected: object) -> bool:
    if type(value) is not type(expected):
        return False
    if isinstance(expected, dict):
        return value.keys() == expected.keys() and all(
            type(key) is str and _strict_equal(value[key], expected_item)
            for key, expected_item in expected.items()
        )
    if isinstance(expected, (tuple, list)):
        return len(value) == len(expected) and all(
            _strict_equal(actual, wanted)
            for actual, wanted in zip(value, expected, strict=True)
        )
    if is_dataclass(expected) and not isinstance(expected, type):
        return all(
            _strict_equal(getattr(value, field.name), getattr(expected, field.name))
            for field in fields(expected)
        )
    return value == expected


def _profile_constants(
    profile: RopeProfile,
) -> tuple[ScalingMode, int, int, int, int, int, int, int]:
    if profile is RopeProfile.BASE:
        return (ScalingMode.NONE, BASE_ROPE_THETA, 0, 1, 0, 0, 0, 0)
    if profile is RopeProfile.COMPRESSED_YARN:
        return (
            ScalingMode.YARN,
            COMPRESSED_ROPE_THETA,
            YARN_ORIGINAL_SEQUENCE_LENGTH,
            YARN_FACTOR,
            YARN_BETA_FAST,
            YARN_BETA_SLOW,
            YARN_CORRECTION_LOW,
            YARN_CORRECTION_HIGH,
        )
    raise DeepSeekV4RopeMicrocodeError("profile must be a typed RoPE profile")


def _resource_for_profile(profile: RopeProfile) -> Resource:
    return (
        Resource.BASE_PHASOR_TABLE
        if profile is RopeProfile.BASE
        else Resource.COMPRESSED_YARN_PHASOR_TABLE
    )


def verify_descriptor(value: object) -> None:
    """Fail closed unless every command field forms one official position policy."""

    if type(value) is not RopeDescriptor:
        raise DeepSeekV4RopeMicrocodeError("descriptor must be an exact RopeDescriptor")
    descriptor = value
    if type(descriptor.opcode) is not Opcode or descriptor.opcode not in {
        Opcode.ROPE_APPLY,
        Opcode.ROPE_INVERSE,
    }:
        raise DeepSeekV4RopeMicrocodeError(
            "descriptor opcode must be ROPE_APPLY or ROPE_INVERSE"
        )
    if type(descriptor.tensor_role) is not TensorRole:
        raise DeepSeekV4RopeMicrocodeError("tensor_role must be typed")
    if type(descriptor.profile) is not RopeProfile:
        raise DeepSeekV4RopeMicrocodeError("profile must be typed")
    if type(descriptor.scaling_mode) is not ScalingMode:
        raise DeepSeekV4RopeMicrocodeError("scaling_mode must be typed")
    if type(descriptor.phase) is not Phase:
        raise DeepSeekV4RopeMicrocodeError("phase must be typed")
    if type(descriptor.position_policy) is not PositionPolicy:
        raise DeepSeekV4RopeMicrocodeError("position_policy must be typed")
    if type(descriptor.numeric_profile) is not str or (
        descriptor.numeric_profile != NUMERIC_PROFILE
    ):
        raise DeepSeekV4RopeMicrocodeError(
            "numeric profile must bind the frozen v2 contract"
        )

    rank = _integer(descriptor.tensor_rank, "tensor_rank", minimum=3, maximum=4)
    batch = _integer(
        descriptor.batch_count,
        "batch_count",
        minimum=1,
        maximum=MAX_BATCH_SIZE,
    )
    del batch
    sequence = _integer(
        descriptor.sequence_length,
        "sequence_length",
        minimum=1,
        maximum=MAX_SEQUENCE_LENGTH,
    )
    heads = _integer(
        descriptor.head_count,
        "head_count",
        minimum=1,
        maximum=MAX_HEAD_COUNT,
    )
    width = _integer(descriptor.head_width, "head_width", minimum=1, maximum=512)
    if width not in SUPPORTED_HEAD_WIDTHS:
        raise DeepSeekV4RopeMicrocodeError("head_width must be exactly 64, 128, or 512")
    if rank == 3 and heads != 1:
        raise DeepSeekV4RopeMicrocodeError(
            "rank-3 RoPE tensors must encode head_count=1"
        )
    if rank == 4 and heads not in SUPPORTED_RANK4_HEAD_COUNTS:
        raise DeepSeekV4RopeMicrocodeError(
            "rank-4 head_count must be an official tensor-parallel local count"
        )
    if _integer(descriptor.rope_dimension, "rope_dimension") != ROPE_DIMENSION:
        raise DeepSeekV4RopeMicrocodeError(
            f"rope_dimension must equal {ROPE_DIMENSION}"
        )

    role_rules = {
        TensorRole.QUERY: (Opcode.ROPE_APPLY, 4, 512),
        TensorRole.KV: (Opcode.ROPE_APPLY, 3, 512),
        TensorRole.INDEX_QUERY: (Opcode.ROPE_APPLY, 4, 128),
        TensorRole.COMPRESSOR_KV: (Opcode.ROPE_APPLY, 3, 512),
        TensorRole.ATTENTION_OUTPUT: (Opcode.ROPE_INVERSE, 4, 512),
    }
    if descriptor.tensor_role in role_rules:
        expected_opcode, expected_rank, expected_width = role_rules[
            descriptor.tensor_role
        ]
        if (descriptor.opcode, rank, width) != (
            expected_opcode,
            expected_rank,
            expected_width,
        ):
            raise DeepSeekV4RopeMicrocodeError(
                "tensor role, direction, rank, and complete head width disagree"
            )
    elif descriptor.tensor_role is TensorRole.ROTARY_SUFFIX and width != ROPE_DIMENSION:
        raise DeepSeekV4RopeMicrocodeError("rotary suffix role must have width 64")

    ratio = _integer(descriptor.compression_ratio, "compression_ratio")
    if ratio not in SUPPORTED_COMPRESSION_RATIOS:
        raise DeepSeekV4RopeMicrocodeError(
            "compression_ratio must be exactly 0, 4, or 128"
        )
    expected_profile = RopeProfile.BASE if ratio == 0 else RopeProfile.COMPRESSED_YARN
    if descriptor.profile is not expected_profile:
        raise DeepSeekV4RopeMicrocodeError(
            "profile must be base for ratio 0 and compressed_yarn for ratio 4/128"
        )
    if descriptor.tensor_role is TensorRole.INDEX_QUERY and ratio != 4:
        raise DeepSeekV4RopeMicrocodeError(
            "official index-query RoPE exists only for compression ratio 4"
        )
    expected_constants = _profile_constants(descriptor.profile)
    observed_constants = (
        descriptor.scaling_mode,
        _integer(descriptor.theta, "theta"),
        _integer(descriptor.original_sequence_length, "original_sequence_length"),
        _integer(descriptor.yarn_factor, "yarn_factor"),
        _integer(descriptor.beta_fast, "beta_fast"),
        _integer(descriptor.beta_slow, "beta_slow"),
        _integer(descriptor.correction_low, "correction_low"),
        _integer(descriptor.correction_high, "correction_high"),
    )
    if observed_constants != expected_constants:
        raise DeepSeekV4RopeMicrocodeError(
            "base/YaRN scaling constants do not exactly match the selected profile"
        )

    request_start = _integer(
        descriptor.request_start_position,
        "request_start_position",
        maximum=MAX_POSITION,
    )
    table_start = _integer(
        descriptor.table_start_position,
        "table_start_position",
        maximum=MAX_POSITION,
    )
    table_last = _integer(
        descriptor.last_table_position,
        "last_table_position",
        maximum=MAX_POSITION,
    )
    stride = _integer(descriptor.position_stride, "position_stride", minimum=1)
    source_length = _integer(
        descriptor.source_sequence_length,
        "source_sequence_length",
        minimum=1,
        maximum=MAX_SEQUENCE_LENGTH,
    )
    source_cutoff = _integer(
        descriptor.source_cutoff,
        "source_cutoff",
        minimum=1,
        maximum=MAX_SEQUENCE_LENGTH,
    )

    policy = descriptor.position_policy
    if policy is PositionPolicy.CONSECUTIVE:
        if descriptor.tensor_role is TensorRole.COMPRESSOR_KV:
            raise DeepSeekV4RopeMicrocodeError(
                "compressor KV requires an explicit compressor position policy"
            )
        if stride != 1 or source_length != sequence or source_cutoff != sequence:
            raise DeepSeekV4RopeMicrocodeError(
                "consecutive policy requires unit stride and identical source/output spans"
            )
        if descriptor.phase is Phase.PREFILL:
            if request_start != 0 or table_start != 0:
                raise DeepSeekV4RopeMicrocodeError(
                    "ordinary prefill must explicitly begin at request/table position zero"
                )
        elif sequence != 1 or table_start != request_start:
            raise DeepSeekV4RopeMicrocodeError(
                "ordinary decode must encode one token at its absolute request position"
            )
    elif policy is PositionPolicy.COMPRESSOR_PREFILL_RATIO_STRIDE:
        if (
            descriptor.opcode is not Opcode.ROPE_APPLY
            or descriptor.phase is not Phase.PREFILL
        ):
            raise DeepSeekV4RopeMicrocodeError(
                "compressor-prefill policy is forward prefill only"
            )
        if descriptor.tensor_role not in {
            TensorRole.COMPRESSOR_KV,
            TensorRole.ROTARY_SUFFIX,
        }:
            raise DeepSeekV4RopeMicrocodeError(
                "compressor-prefill policy has wrong tensor role"
            )
        if ratio not in {4, 128} or stride != ratio:
            raise DeepSeekV4RopeMicrocodeError(
                "compressor prefill position_stride must equal ratio 4 or 128"
            )
        expected_cutoff = source_length - source_length % ratio
        if (
            request_start != 0
            or table_start != 0
            or expected_cutoff == 0
            or source_cutoff != expected_cutoff
            or sequence != expected_cutoff // ratio
        ):
            raise DeepSeekV4RopeMicrocodeError(
                "compressor prefill output/stride must derive from the complete ratio cutoff"
            )
    else:
        if (
            descriptor.opcode is not Opcode.ROPE_APPLY
            or descriptor.phase is not Phase.DECODE
        ):
            raise DeepSeekV4RopeMicrocodeError(
                "compressor-decode policy is forward decode only"
            )
        if descriptor.tensor_role not in {
            TensorRole.COMPRESSOR_KV,
            TensorRole.ROTARY_SUFFIX,
        }:
            raise DeepSeekV4RopeMicrocodeError(
                "compressor-decode policy has wrong tensor role"
            )
        if ratio not in {4, 128} or stride != 1:
            raise DeepSeekV4RopeMicrocodeError(
                "compressor decode requires ratio 4/128 and unit output stride"
            )
        if sequence != 1 or source_length != 1 or source_cutoff != 1:
            raise DeepSeekV4RopeMicrocodeError(
                "compressor decode must encode one completed row"
            )
        if request_start + 1 < ratio or (request_start + 1) % ratio != 0:
            raise DeepSeekV4RopeMicrocodeError(
                "compressor decode request position must close a complete ratio group"
            )
        if table_start != request_start + 1 - ratio:
            raise DeepSeekV4RopeMicrocodeError(
                "compressor decode table position must equal start_pos + 1 - ratio"
            )

    if (
        descriptor.opcode is Opcode.ROPE_INVERSE
        and policy is not PositionPolicy.CONSECUTIVE
    ):
        raise DeepSeekV4RopeMicrocodeError(
            "ROPE_INVERSE admits only consecutive positions"
        )
    expected_last = table_start + (sequence - 1) * stride
    if expected_last > MAX_POSITION or table_last != expected_last:
        raise DeepSeekV4RopeMicrocodeError(
            "last_table_position must reconcile without overflowing the pinned table"
        )


def build_descriptor(
    *,
    opcode: Opcode,
    tensor_role: TensorRole,
    tensor_rank: int,
    batch_count: int,
    sequence_length: int,
    head_count: int,
    head_width: int,
    profile: RopeProfile,
    phase: Phase,
    position_policy: PositionPolicy,
    compression_ratio: int,
    request_start_position: int,
    source_sequence_length: int | None = None,
) -> RopeDescriptor:
    """Construct one canonical descriptor while retaining every derived field."""

    if type(opcode) is not Opcode:
        raise DeepSeekV4RopeMicrocodeError("opcode must be typed")
    if type(tensor_role) is not TensorRole:
        raise DeepSeekV4RopeMicrocodeError("tensor_role must be typed")
    if type(profile) is not RopeProfile:
        raise DeepSeekV4RopeMicrocodeError("profile must be a typed RoPE profile")
    constants = _profile_constants(profile)
    source_length = (
        sequence_length if source_sequence_length is None else source_sequence_length
    )
    if type(position_policy) is not PositionPolicy:
        raise DeepSeekV4RopeMicrocodeError("position_policy must be typed")
    sequence_length = _integer(
        sequence_length,
        "sequence_length",
        minimum=1,
        maximum=MAX_SEQUENCE_LENGTH,
    )
    source_length = _integer(
        source_length,
        "source_sequence_length",
        minimum=1,
        maximum=MAX_SEQUENCE_LENGTH,
    )
    compression_ratio = _integer(compression_ratio, "compression_ratio")
    if compression_ratio not in SUPPORTED_COMPRESSION_RATIOS:
        raise DeepSeekV4RopeMicrocodeError(
            "compression_ratio must be exactly 0, 4, or 128"
        )
    request_start_position = _integer(
        request_start_position,
        "request_start_position",
        maximum=MAX_POSITION,
    )
    if position_policy is PositionPolicy.CONSECUTIVE:
        table_start = request_start_position
        stride = 1
        cutoff = source_length
    elif position_policy is PositionPolicy.COMPRESSOR_PREFILL_RATIO_STRIDE:
        if compression_ratio not in {4, 128}:
            raise DeepSeekV4RopeMicrocodeError(
                "compressor prefill requires compression_ratio 4 or 128"
            )
        table_start = 0
        stride = compression_ratio
        cutoff = source_length - source_length % compression_ratio
    else:
        if compression_ratio not in {4, 128}:
            raise DeepSeekV4RopeMicrocodeError(
                "compressor decode requires compression_ratio 4 or 128"
            )
        table_start = request_start_position + 1 - compression_ratio
        stride = 1
        cutoff = 1
    last = table_start + (sequence_length - 1) * stride
    return RopeDescriptor(
        opcode=opcode,
        tensor_role=tensor_role,
        tensor_rank=tensor_rank,
        batch_count=batch_count,
        sequence_length=sequence_length,
        head_count=head_count,
        head_width=head_width,
        rope_dimension=ROPE_DIMENSION,
        numeric_profile=NUMERIC_PROFILE,
        profile=profile,
        scaling_mode=constants[0],
        theta=constants[1],
        original_sequence_length=constants[2],
        yarn_factor=constants[3],
        beta_fast=constants[4],
        beta_slow=constants[5],
        correction_low=constants[6],
        correction_high=constants[7],
        phase=phase,
        position_policy=position_policy,
        compression_ratio=compression_ratio,
        request_start_position=request_start_position,
        table_start_position=table_start,
        last_table_position=last,
        position_stride=stride,
        source_sequence_length=source_length,
        source_cutoff=cutoff,
    )


def verify_instruction(value: object) -> None:
    if type(value) is not Instruction:
        raise DeepSeekV4RopeMicrocodeError("instruction must be exact and typed")
    instruction = value
    if type(instruction.opcode) is not Opcode:
        raise DeepSeekV4RopeMicrocodeError("instruction opcode must be typed")
    if type(instruction.flags) is not int or instruction.flags != 0:
        raise DeepSeekV4RopeMicrocodeError("instruction flags must be exact zero")
    if instruction.opcode is Opcode.COMPLETE:
        if (
            instruction.destination != NO_OPERAND
            or instruction.source != NO_OPERAND
            or instruction.resource != NO_OPERAND
            or instruction.descriptor is not None
        ):
            raise DeepSeekV4RopeMicrocodeError("COMPLETE must have no operands")
        return
    if type(instruction.destination) is not Register or (
        instruction.destination is not Register.OUTPUT
    ):
        raise DeepSeekV4RopeMicrocodeError("RoPE destination must be typed OUTPUT")
    if (
        type(instruction.source) is not Register
        or instruction.source is not Register.INPUT
    ):
        raise DeepSeekV4RopeMicrocodeError("RoPE source must be typed INPUT")
    if instruction.destination is instruction.source:
        raise DeepSeekV4RopeMicrocodeError(
            "RoPE input and output registers must not alias"
        )
    if type(instruction.descriptor) is not RopeDescriptor:
        raise DeepSeekV4RopeMicrocodeError(
            "RoPE instruction requires an exact descriptor"
        )
    verify_descriptor(instruction.descriptor)
    if instruction.opcode is not instruction.descriptor.opcode:
        raise DeepSeekV4RopeMicrocodeError(
            "instruction and descriptor directions differ"
        )
    expected_resource = _resource_for_profile(instruction.descriptor.profile)
    if (
        type(instruction.resource) is not Resource
        or instruction.resource is not expected_resource
    ):
        raise DeepSeekV4RopeMicrocodeError(
            "phasor resource does not match the explicit profile"
        )


def assemble(descriptor: RopeDescriptor) -> tuple[Instruction, ...]:
    """Assemble the sole legal transaction program for a validated descriptor."""

    verify_descriptor(descriptor)
    program = (
        Instruction(
            descriptor.opcode,
            destination=Register.OUTPUT,
            source=Register.INPUT,
            resource=_resource_for_profile(descriptor.profile),
            descriptor=descriptor,
        ),
        Instruction(Opcode.COMPLETE),
    )
    verify(program, descriptor)
    return program


def verify(
    instructions: object,
    expected_descriptor: RopeDescriptor | None = None,
) -> None:
    """Require one semantic instruction followed by one operand-free COMPLETE."""

    if (
        type(instructions) is not tuple
        or len(instructions) != PROGRAM_INSTRUCTION_COUNT
    ):
        raise DeepSeekV4RopeMicrocodeError(
            "program must be an exact two-instruction tuple"
        )
    first, complete = instructions
    verify_instruction(first)
    verify_instruction(complete)
    if first.opcode not in {Opcode.ROPE_APPLY, Opcode.ROPE_INVERSE}:
        raise DeepSeekV4RopeMicrocodeError("program must begin with a RoPE operator")
    if complete != Instruction(Opcode.COMPLETE):
        raise DeepSeekV4RopeMicrocodeError("program must end in one exact COMPLETE")
    if expected_descriptor is not None:
        verify_descriptor(expected_descriptor)
        if not _strict_equal(first.descriptor, expected_descriptor):
            raise DeepSeekV4RopeMicrocodeError(
                "program descriptor differs from expectation"
            )


def _descriptor_uints(descriptor: RopeDescriptor) -> tuple[int, ...]:
    return (
        int(descriptor.tensor_role),
        descriptor.tensor_rank,
        descriptor.batch_count,
        descriptor.sequence_length,
        descriptor.head_count,
        descriptor.head_width,
        descriptor.rope_dimension,
        NUMERIC_PROFILE_CODE,
        int(descriptor.profile),
        int(descriptor.scaling_mode),
        descriptor.theta,
        descriptor.original_sequence_length,
        descriptor.yarn_factor,
        descriptor.beta_fast,
        descriptor.beta_slow,
        descriptor.correction_low,
        descriptor.correction_high,
        int(descriptor.phase),
        int(descriptor.position_policy),
        descriptor.compression_ratio,
        descriptor.request_start_position,
        descriptor.table_start_position,
        descriptor.last_table_position,
        descriptor.position_stride,
        descriptor.source_sequence_length,
        descriptor.source_cutoff,
    )


def encode(instructions: object) -> bytes:
    verify(instructions)
    records: list[bytes] = []
    for instruction in instructions:
        if instruction.opcode is Opcode.COMPLETE:
            operands = (NO_OPERAND, NO_OPERAND, NO_OPERAND, *(0,) * 26)
        else:
            if instruction.descriptor is None:  # pragma: no cover - verify guards
                raise DeepSeekV4RopeMicrocodeError(
                    "RoPE instruction lost its validated descriptor"
                )
            operands = (
                int(instruction.destination),
                int(instruction.source),
                int(instruction.resource),
                *_descriptor_uints(instruction.descriptor),
            )
        records.append(RECORD.pack(int(instruction.opcode), 0, 0, *operands))
    body = b"".join(records)
    return (
        HEADER.pack(
            MAGIC,
            ABI_MAJOR,
            ABI_MINOR,
            RECORD.size,
            PROGRAM_INSTRUCTION_COUNT,
            zlib.crc32(body) & 0xFFFFFFFF,
        )
        + body
    )


def _enum(enum_type: type[IntEnum], raw: int, label: str) -> IntEnum:
    try:
        return enum_type(raw)
    except ValueError as exc:
        raise DeepSeekV4RopeMicrocodeError(f"unknown {label} code {raw}") from exc


def decode(payload: object) -> tuple[Instruction, ...]:
    """Decode and semantically validate one complete fixed-width program."""

    if type(payload) is not bytes:
        raise DeepSeekV4RopeMicrocodeError("microcode payload must be exact bytes")
    if len(payload) < HEADER.size:
        raise DeepSeekV4RopeMicrocodeError("microcode is shorter than its header")
    magic, major, minor, record_size, count, expected_crc = HEADER.unpack_from(payload)
    if magic != MAGIC:
        raise DeepSeekV4RopeMicrocodeError("microcode magic mismatch")
    if (major, minor) != (ABI_MAJOR, ABI_MINOR):
        raise DeepSeekV4RopeMicrocodeError("unsupported RoPE microcode ABI")
    if record_size != RECORD.size or count != PROGRAM_INSTRUCTION_COUNT:
        raise DeepSeekV4RopeMicrocodeError(
            "microcode shape differs from the two-record ABI"
        )
    body = payload[HEADER.size :]
    if len(body) != count * RECORD.size:
        raise DeepSeekV4RopeMicrocodeError(
            "microcode body length differs from its header"
        )
    if zlib.crc32(body) & 0xFFFFFFFF != expected_crc:
        raise DeepSeekV4RopeMicrocodeError("microcode CRC32 mismatch")

    decoded: list[Instruction] = []
    for index in range(count):
        unpacked = RECORD.unpack_from(body, index * RECORD.size)
        opcode_raw, flags, reserved = unpacked[:3]
        values = unpacked[3:]
        if flags != 0 or reserved != 0:
            raise DeepSeekV4RopeMicrocodeError(
                f"instruction {index} has unsupported flags or reserved bits"
            )
        opcode = _enum(Opcode, opcode_raw, "opcode")
        if opcode is Opcode.COMPLETE:
            if values != (NO_OPERAND, NO_OPERAND, NO_OPERAND, *(0,) * 26):
                raise DeepSeekV4RopeMicrocodeError(
                    "COMPLETE wire operands must be canonical"
                )
            decoded.append(Instruction(Opcode.COMPLETE))
            continue
        destination_raw, source_raw, resource_raw, *raw = values
        if raw[7] != NUMERIC_PROFILE_CODE:
            raise DeepSeekV4RopeMicrocodeError(
                "wire numeric profile does not bind frozen v2"
            )
        descriptor = RopeDescriptor(
            opcode=opcode,
            tensor_role=_enum(TensorRole, raw[0], "tensor role"),
            tensor_rank=raw[1],
            batch_count=raw[2],
            sequence_length=raw[3],
            head_count=raw[4],
            head_width=raw[5],
            rope_dimension=raw[6],
            numeric_profile=NUMERIC_PROFILE,
            profile=_enum(RopeProfile, raw[8], "profile"),
            scaling_mode=_enum(ScalingMode, raw[9], "scaling mode"),
            theta=raw[10],
            original_sequence_length=raw[11],
            yarn_factor=raw[12],
            beta_fast=raw[13],
            beta_slow=raw[14],
            correction_low=raw[15],
            correction_high=raw[16],
            phase=_enum(Phase, raw[17], "phase"),
            position_policy=_enum(PositionPolicy, raw[18], "position policy"),
            compression_ratio=raw[19],
            request_start_position=raw[20],
            table_start_position=raw[21],
            last_table_position=raw[22],
            position_stride=raw[23],
            source_sequence_length=raw[24],
            source_cutoff=raw[25],
        )
        decoded.append(
            Instruction(
                opcode,
                destination=_enum(Register, destination_raw, "destination register"),
                source=_enum(Register, source_raw, "source register"),
                resource=_enum(Resource, resource_raw, "phasor resource"),
                descriptor=descriptor,
            )
        )
    program = tuple(decoded)
    verify(program)
    return program


def tensor_contract(descriptor: RopeDescriptor) -> tuple[TensorSpec, ...]:
    verify_descriptor(descriptor)
    shape = (
        (descriptor.batch_count, descriptor.sequence_length, descriptor.head_width)
        if descriptor.tensor_rank == 3
        else (
            descriptor.batch_count,
            descriptor.sequence_length,
            descriptor.head_count,
            descriptor.head_width,
        )
    )
    preserved_prefix_width = descriptor.head_width - ROPE_DIMENSION
    common = {
        "preserved_prefix_width": preserved_prefix_width,
        "rotary_suffix_width": ROPE_DIMENSION,
        "channel_semantics": CHANNEL_SEMANTICS,
    }
    return (
        TensorSpec(
            Register.INPUT,
            "BF16",
            shape,
            "read_only",
            False,
            None,
            **common,
        ),
        TensorSpec(
            Register.OUTPUT,
            "BF16",
            shape,
            "write_only",
            True,
            None,
            **common,
        ),
    )


def verify_tensor_contract(value: object, descriptor: RopeDescriptor) -> None:
    expected = tensor_contract(descriptor)
    if not _strict_equal(value, expected):
        raise DeepSeekV4RopeMicrocodeError(
            "tensor contract must preserve the complete shape without aliasing"
        )


def _profile_semantics(descriptor: RopeDescriptor) -> dict[str, Any]:
    return {
        "beta_fast": descriptor.beta_fast,
        "beta_slow": descriptor.beta_slow,
        "correction_high": descriptor.correction_high,
        "correction_low": descriptor.correction_low,
        "numeric_profile": descriptor.numeric_profile,
        "original_sequence_length": descriptor.original_sequence_length,
        "profile": descriptor.profile.name,
        "rope_dimension": descriptor.rope_dimension,
        "scaling_mode": descriptor.scaling_mode.name,
        "theta": descriptor.theta,
        "yarn_factor": descriptor.yarn_factor,
    }


def resource_contract(descriptor: RopeDescriptor) -> tuple[ResourceSpec, ...]:
    verify_descriptor(descriptor)
    semantics = _profile_semantics(descriptor)
    return (
        ResourceSpec(
            resource=_resource_for_profile(descriptor.profile),
            dtype="COMPLEX_BINARY32_PAIR",
            shape=PHASOR_TABLE_SHAPE,
            size_bytes=PHASOR_TABLE_BYTES,
            rope_dimension=ROPE_DIMENSION,
            complex_pair_count=ROPE_COMPLEX_PAIRS,
            numeric_profile=descriptor.numeric_profile,
            profile=descriptor.profile,
            scaling_mode=descriptor.scaling_mode,
            theta=descriptor.theta,
            original_sequence_length=descriptor.original_sequence_length,
            yarn_factor=descriptor.yarn_factor,
            beta_fast=descriptor.beta_fast,
            beta_slow=descriptor.beta_slow,
            correction_low=descriptor.correction_low,
            correction_high=descriptor.correction_high,
            semantic_sha256=hashlib.sha256(canonical_json_bytes(semantics)).hexdigest(),
            checkpoint_derived=False,
        ),
    )


def verify_resource_contract(value: object, descriptor: RopeDescriptor) -> None:
    expected = resource_contract(descriptor)
    if not _strict_equal(value, expected):
        raise DeepSeekV4RopeMicrocodeError(
            "resource contract does not exactly bind the selected phasor profile"
        )


def position_contract(descriptor: RopeDescriptor) -> PositionContract:
    verify_descriptor(descriptor)
    formulas = {
        PositionPolicy.CONSECUTIVE: "table_start=request_start; table[i]=table_start+i",
        PositionPolicy.COMPRESSOR_PREFILL_RATIO_STRIDE: (
            "table_start=0; table[i]=i*compression_ratio"
        ),
        PositionPolicy.COMPRESSOR_DECODE_ADJUSTED: (
            "table_start=request_start+1-compression_ratio; table[0]=table_start"
        ),
    }
    return PositionContract(
        phase=descriptor.phase,
        policy=descriptor.position_policy,
        compression_ratio=descriptor.compression_ratio,
        request_start_position=descriptor.request_start_position,
        table_start_position=descriptor.table_start_position,
        last_table_position=descriptor.last_table_position,
        position_stride=descriptor.position_stride,
        output_sequence_length=descriptor.sequence_length,
        source_sequence_length=descriptor.source_sequence_length,
        source_cutoff=descriptor.source_cutoff,
        table_position_formula=formulas[descriptor.position_policy],
    )


def verify_position_contract(value: object, descriptor: RopeDescriptor) -> None:
    if not _strict_equal(value, position_contract(descriptor)):
        raise DeepSeekV4RopeMicrocodeError("position contract differs from the command")


def state_contract(descriptor: RopeDescriptor) -> StateContract:
    verify_descriptor(descriptor)
    return StateContract(
        mutable_state_reads=(),
        mutable_state_writes=(),
        request_inputs=("request.start_pos",),
        phasor_resource=_resource_for_profile(descriptor.profile),
        output_commit="atomic_after_complete_tensor_rotation",
        alias_policy="distinct_input_output_registers_no_in_place_alias",
        preserved_prefix_policy=PRESERVED_PREFIX_POLICY,
        rotary_suffix_width=ROPE_DIMENSION,
    )


def verify_state_contract(value: object, descriptor: RopeDescriptor) -> None:
    if not _strict_equal(value, state_contract(descriptor)):
        raise DeepSeekV4RopeMicrocodeError(
            "state/commit contract differs from the command"
        )


def descriptor_record(descriptor: RopeDescriptor) -> dict[str, Any]:
    verify_descriptor(descriptor)
    return {
        "batch_count": descriptor.batch_count,
        "beta_fast": descriptor.beta_fast,
        "beta_slow": descriptor.beta_slow,
        "compression_ratio": descriptor.compression_ratio,
        "correction_high": descriptor.correction_high,
        "correction_low": descriptor.correction_low,
        "head_count": descriptor.head_count,
        "head_width": descriptor.head_width,
        "last_table_position": descriptor.last_table_position,
        "numeric_profile": descriptor.numeric_profile,
        "opcode": descriptor.opcode.name,
        "original_sequence_length": descriptor.original_sequence_length,
        "phase": descriptor.phase.name,
        "position_policy": descriptor.position_policy.name,
        "position_stride": descriptor.position_stride,
        "profile": descriptor.profile.name,
        "request_start_position": descriptor.request_start_position,
        "rope_dimension": descriptor.rope_dimension,
        "scaling_mode": descriptor.scaling_mode.name,
        "sequence_length": descriptor.sequence_length,
        "source_cutoff": descriptor.source_cutoff,
        "source_sequence_length": descriptor.source_sequence_length,
        "table_start_position": descriptor.table_start_position,
        "tensor_rank": descriptor.tensor_rank,
        "tensor_role": descriptor.tensor_role.name,
        "theta": descriptor.theta,
        "yarn_factor": descriptor.yarn_factor,
    }


def descriptor_id(descriptor: RopeDescriptor) -> str:
    return hashlib.sha256(
        canonical_json_bytes(descriptor_record(descriptor))
    ).hexdigest()


def build_program_contract(descriptor: RopeDescriptor) -> dict[str, Any]:
    verify_descriptor(descriptor)
    program = assemble(descriptor)
    payload = encode(program)
    body = {
        "abi": {
            "instruction_count": PROGRAM_INSTRUCTION_COUNT,
            "major": ABI_MAJOR,
            "magic_ascii": MAGIC.decode("ascii"),
            "minor": ABI_MINOR,
            "record_bytes": RECORD.size,
        },
        "descriptor": descriptor_record(descriptor),
        "descriptor_id": descriptor_id(descriptor),
        "model_id": MODEL_ID,
        "model_repository": MODEL_REPOSITORY,
        "model_revision": MODEL_REVISION,
        "operator_sequence": [descriptor.opcode.name, Opcode.COMPLETE.name],
        "program_bytes": len(payload),
        "program_sha256": hashlib.sha256(payload).hexdigest(),
        "required_nonclaims": list(EXPLICIT_NON_CLAIMS),
        "schema": PROGRAM_CONTRACT_SCHEMA,
        "status": "typed_logical_microcode_only",
    }
    return {
        **body,
        "contract_id": hashlib.sha256(canonical_json_bytes(body)).hexdigest(),
    }


def verify_program_contract(value: object, descriptor: RopeDescriptor) -> None:
    expected = build_program_contract(descriptor)
    if not _strict_equal(value, expected):
        raise DeepSeekV4RopeMicrocodeError(
            "program contract differs from canonical authority"
        )


def disassemble(instructions: object) -> str:
    verify(instructions)
    first, _ = instructions
    descriptor = first.descriptor
    if descriptor is None:  # pragma: no cover - verify guards
        raise DeepSeekV4RopeMicrocodeError(
            "RoPE instruction lost its validated descriptor"
        )
    lines = [f"# OpenTallas DeepSeek V4 RoPE ABI {ABI_MAJOR}.{ABI_MINOR}"]
    lines.append(
        f"0000 {first.opcode.name} dst=OUTPUT src=INPUT "
        f"resource={first.resource.name} profile={descriptor.profile.name} "
        f"phase={descriptor.phase.name} policy={descriptor.position_policy.name} "
        f"shape={tensor_contract(descriptor)[0].shape} "
        f"request_start={descriptor.request_start_position} "
        f"table_start={descriptor.table_start_position} "
        f"stride={descriptor.position_stride}"
    )
    lines.append("0001 COMPLETE")
    return "\n".join(lines) + "\n"


__all__ = [
    "ABI_MAJOR",
    "ABI_MINOR",
    "CHANNEL_SEMANTICS",
    "EXPLICIT_NON_CLAIMS",
    "HEADER",
    "Instruction",
    "MAGIC",
    "MAX_BATCH_SIZE",
    "MAX_POSITION",
    "MAX_SEQUENCE_LENGTH",
    "MODEL_ID",
    "MODEL_REPOSITORY",
    "MODEL_REVISION",
    "NO_OPERAND",
    "NUMERIC_PROFILE",
    "NUMERIC_PROFILE_CODE",
    "Opcode",
    "PHASOR_TABLE_BYTES",
    "PHASOR_TABLE_SHAPE",
    "PRESERVED_PREFIX_POLICY",
    "PROGRAM_INSTRUCTION_COUNT",
    "Phase",
    "PositionContract",
    "PositionPolicy",
    "RECORD",
    "ROPE_COMPLEX_PAIRS",
    "ROPE_DIMENSION",
    "Register",
    "Resource",
    "ResourceSpec",
    "RopeDescriptor",
    "RopeProfile",
    "ScalingMode",
    "StateContract",
    "SUPPORTED_COMPRESSION_RATIOS",
    "SUPPORTED_HEAD_WIDTHS",
    "SUPPORTED_RANK4_HEAD_COUNTS",
    "TensorRole",
    "TensorSpec",
    "DeepSeekV4RopeMicrocodeError",
    "assemble",
    "build_descriptor",
    "build_program_contract",
    "decode",
    "descriptor_id",
    "descriptor_record",
    "disassemble",
    "encode",
    "position_contract",
    "resource_contract",
    "state_contract",
    "tensor_contract",
    "verify",
    "verify_descriptor",
    "verify_instruction",
    "verify_position_contract",
    "verify_program_contract",
    "verify_resource_contract",
    "verify_state_contract",
    "verify_tensor_contract",
]
