"""Independent checks for DeepSeek V4 grouped-output compiler evidence.

The logical-schedule checker intentionally does not import the schedule
builder.  It independently decodes the wire program, reconstructs topology,
register, alias, resource, and slot tables, and checks causality before
issuing a hash-bound certificate.

The optional official-evidence checker authenticates the pinned source,
checkpoint lock, canonical application, independent application verification,
four layer-0 ``wo_a`` assignments, and all fifteen legal aggregate local
resources.  Neither certificate is execution, numerical, timing, bandwidth,
physical-schedule, or PPA evidence.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
import hashlib
from pathlib import Path
from typing import Any, BinaryIO
import zlib

from compiler.ir.model import canonical_json_bytes, load_strict_json
from compiler.microcode.deepseek_v4_grouped_output import (
    ABI_MAJOR,
    ABI_MINOR,
    CANONICAL_APPLICATION_FILE_SHA256,
    CANONICAL_APPLICATION_ID,
    CANONICAL_VERIFICATION_FILE_SHA256,
    CANONICAL_VERIFICATION_ID,
    CHECKPOINT_INDEX_PATH,
    CHECKPOINT_INDEX_SHA256,
    CHECKPOINT_LOCK_FILE_SHA256,
    CHECKPOINT_LOCK_ID,
    CONVERT_SOURCE_PATH,
    CONVERT_SOURCE_SHA256,
    GLOBAL_GROUP_COUNT,
    GROUP_INPUT_FEATURES,
    HEAD_DIM,
    HEADER,
    HEADS_PER_GROUP,
    INFERENCE_CONFIG_PATH,
    INFERENCE_CONFIG_SHA256,
    MAGIC,
    MAX_TOKEN_COUNT,
    MIN_TOKEN_COUNT,
    MODEL_ID,
    MODEL_REPOSITORY,
    MODEL_REVISION,
    MODEL_SOURCE_PATH,
    MODEL_SOURCE_SHA256,
    NO_OPERAND,
    OUTPUT_RANK_PER_GROUP,
    RAW_LAYER0_WO_A_SCALE_SHA256,
    RAW_LAYER0_WO_A_WEIGHT_SHA256,
    RECORD,
    ROW_BYTES,
    TENSOR_PARALLEL_WORLD_SIZES,
    assemble,
    build_program_contract,
    build_source_contract,
    encode,
    resource_contract,
    tensor_contract,
    topology_mappings,
    verify,
    verify_program_contract,
    verify_resource_contract,
    verify_source_contract,
    verify_tensor_contract,
)


LOGICAL_SCHEDULE_SCHEMA = "opentallas.deepseek_v4_grouped_output_logical_schedule.v1"
LOGICAL_CERTIFICATE_SCHEMA = (
    "opentallas.deepseek_v4_grouped_output_logical_schedule_certificate.v1"
)
OFFICIAL_EVIDENCE_CERTIFICATE_SCHEMA = (
    "opentallas.deepseek_v4_grouped_output_official_evidence_certificate.v1"
)
LOGICAL_SCHEDULE_STATUS = "logical_schedule_only"
CERTIFICATE_STATUS = "pass"
CLAIM_BOUNDARY = (
    "Deterministic logical instruction, register, alias-view, topology, and "
    "canonical-resource ordering for grouped output only; this is not "
    "execution, numerical agreement, timing, bandwidth, physical scheduling, "
    "or PPA evidence."
)
CERTIFICATE_CLAIM_BOUNDARY = (
    "Independent grouped-output logical-schedule conformance certificate only; "
    "no execution, numerical, cycle, bandwidth, physical-schedule, or PPA claim."
)
OFFICIAL_EVIDENCE_CLAIM_BOUNDARY = (
    "Pinned official source, checkpoint-lock, canonical wo_a assignment, and "
    "aggregate-resource identity certificate only; no activation or output was "
    "executed and no performance property was measured."
)
REQUIRED_NONCLAIMS = [
    "bandwidth",
    "checkpoint_execution",
    "cycle_accuracy",
    "cycle_latency",
    "end_to_end_model_execution",
    "execution_evidence",
    "full_attention_execution",
    "full_transformer_block_execution",
    "nvidia_comparison",
    "numeric_correctness",
    "output_b_projection",
    "physical_schedule",
    "physical_topology",
    "ppa",
    "rtl_execution",
    "tensor_parallel_collective",
]
ORDERING_POLICY = {
    "alias_rule": (
        "FLATTENED_OUTPUT is a view of GROUPED_OUTPUT produced by the same semantic slot"
    ),
    "completion_rule": "terminal COMPLETE depends on every preceding logical slot",
    "dependency_rule": (
        "every consumed register is external or produced by a lower-numbered slot"
    ),
    "resource_rule": (
        "the resource resolves exactly through the topology-specific canonical wo_a contract"
    ),
    "slot_rule": "one microinstruction per monotonically increasing logical slot",
}

FROZEN_SOURCE_CONTRACT_ID = (
    "f0220c70a30456e76276add36821ca7fff12c3944b2d202c2b0118ffdcd29bd9"
)
FROZEN_PROGRAM_BYTES = 88

_ASSIGNMENT_HASHES = (
    "eefc9e67cf4cffd43050c96006bdafd37802cf3059678808f0fae2920bf9cf7b",
    "ab08dafc884593f7b4526c3ad7a74c551ca7eece7414cce2432db782f4c7e016",
    "d9abb5935224997d525ad2889e1082e056515aababfea32492476d7ec26476fc",
    "0bee532ef7196984f664e07e9442adbe073ba34f8fdd5f6afb4b9974503f446b",
)
_HALF_ASSIGNMENT_HASHES = (
    "60ddeeab2ee7f73bf695bea8e4a27bebb89bc5debec2bd6c8031f57b0f95091a",
    "fbd7d95f857d7820675a25fb24280e538d924a8ff2a93d66534b1c4ca78e773d",
    "7f015b095b13a6475d7604f7e0a4f88d6ceae6c6e43719e70a71387139fbb291",
    "864a89722a72a8c5491248540fbb55788cbc21906d83941f346faa2f65ace46f",
    "841368c516a3a4d88fe0a21779f1eafa5a7d525e818f048319fd666cbc343a27",
    "a4e0ccbc47c2ba43939ce139fc0be8ee8a277c0b7f8514707da5108da7ba59f1",
    "81fbf8df07170139e5255dcad1ea95dbde1cfd9dbc0f007eae188362c99a2f67",
    "16f7db1662c18feda343cfabb951807e06b6de746c05f218f8e72befb6831768",
)
FROZEN_MAPPING_HASHES = {
    (1, 0): "8e983ca6e21f951c56e644f036d5ab255e7aa429aac3a510b9773b34c52f48a3",
    (2, 0): "3d6f5ff6b1493268a914a8644e7a4f6a1f9aeb26dda0b5009c2daf473d051a06",
    (2, 1): "e4018706e3435505b5deeb96a123f9defde1dde0b6fa0cfe9b8496dca3905361",
    (4, 0): _ASSIGNMENT_HASHES[0],
    (4, 1): _ASSIGNMENT_HASHES[1],
    (4, 2): _ASSIGNMENT_HASHES[2],
    (4, 3): _ASSIGNMENT_HASHES[3],
    **{(8, rank): digest for rank, digest in enumerate(_HALF_ASSIGNMENT_HASHES)},
}
FROZEN_PROGRAM_SHA256 = {
    (1, 0): "e4722ad4e68661bb2e643cdc526c8e2572f4a319a11e0cdbdad3f3f63a1fcfb6",
    (2, 0): "2686bdf4c61d05f1cb1103bf6d6d0598a5b271c885660c5eb94991f2bbc598af",
    (2, 1): "e3dd05ba5c1f95e001ec4a296b45fbed4b7c425c7a5a083deaf51ed57ec9a2c0",
    (4, 0): "d6ea68b8e9542ac5d3d3991aa62678dd4ec6af854a357d307567b4cecc6dd3d3",
    (4, 1): "e60d60973f8de953455e13063018ee67b90c962629b3947e4785d07da770db52",
    (4, 2): "1a9ec644f1987e04eb6f5d2f5efb34290e082d96ef5080f8303680955ad6cc1d",
    (4, 3): "efecb94bf543b7ac0d6c6754777083814977b36b07980bb931ba4e4f62d35950",
    (8, 0): "e5064a83baa985a846d4a99e866f53ec59f11909dc81664af35ee6b606d33f5f",
    (8, 1): "0be49aaf5b83e2346c3e99e850845bda8ee59dff02eeda93ecbfb81fb08c97d6",
    (8, 2): "e38d32097a66bb23cb6c4215a7bd5fd2e31d301c5db57798b606e42636ca5b08",
    (8, 3): "613c3f2bbecc3988989844da5e5b3a4b5838e3d6b8bd02737c991e5263be9c49",
    (8, 4): "b889d0ae2d1374ac203aaabdb9cab4cde4c22048207c180907a9f44a5179b482",
    (8, 5): "7da745ed158322b0cfdecdf2824b9e05d45a462341675c2296a62623e5dcb7da",
    (8, 6): "69fb674fc5b192e946fcbae945c0bae2aadafb445e9e3ec71b463e43525bda88",
    (8, 7): "e2cb1394d2075866e0327ec43324899ff5ec30f5d35f87f45ddc1472fa7603a2",
}
FROZEN_PROGRAM_CONTRACT_IDS = {
    (1, 0): "843055e993b9bf462b6c09457fcffec16e76a7c6b3d7586c305323e7027315cf",
    (2, 0): "e4c2453a422b8ffcc325ef654a67552ea268673ecbaa89987fc91a8a81f786d8",
    (2, 1): "2a310b41009a1d1305ae32560032d0be8203416322b520b9e84d2db0c23400cc",
    (4, 0): "607548c50a7a44e5e9ceabd8eb19b25b8d76d2e1d2ad941e3665d08422b46f42",
    (4, 1): "4c320c9a9620c20a67eb788d34dffb059a63a6e0053397a7a3cad239174eedce",
    (4, 2): "400866f31848bfff7e320d05a8f6c37131747f7caec7eca085ac77b206c9b243",
    (4, 3): "6eadd4a7cc33573a54ad40793afe18322bfa057bacce4046397dacfcfaabfaab",
    (8, 0): "509fdab1984b9e3ae6f54a648ab1b681415a746c8fb37eaacc8bf17137548f4d",
    (8, 1): "04be6a4a65bd974176d24fbe27d66db1e6adbf8fdde66b975cd4e3eeca779438",
    (8, 2): "9c0cff5088555c79b2e51335ee8fd0a5822165db3e5c3fd898c57b22a9515791",
    (8, 3): "943aad1171f8f37a3fcc5b372d1650f12c90f4334d5e64fb0c0dc8f870655110",
    (8, 4): "0d60073b85591f4a035981e28ebb4ab7b891b5b6841f34984b68c2aafb9c45b5",
    (8, 5): "d4c7c61396fe53ccc2940e5855e8da8b60c1cab8f62c0d492a02e44705701a86",
    (8, 6): "58f4266d81e957698b4865608474b9f2348bb734f78c88d7929ed143bab89777",
    (8, 7): "28d4a26f03d5b42be9a77f842bf63f4e29362c244b4a33efc6f2abd5f6e093a7",
}


class DeepSeekV4GroupedOutputCheckError(ValueError):
    """Raised when logical or cached official evidence fails closed."""


def _sha256(value: object) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def _canonical_equal(left: object, right: object) -> bool:
    return canonical_json_bytes(left) == canonical_json_bytes(right)


def _mapping(value: object, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise DeepSeekV4GroupedOutputCheckError(f"{label} must be an object")
    if any(type(key) is not str for key in value):
        raise DeepSeekV4GroupedOutputCheckError(f"{label} keys must be strings")
    return value


def _exact(value: object, keys: set[str], label: str) -> Mapping[str, Any]:
    record = _mapping(value, label)
    observed = set(record)
    if observed != keys:
        raise DeepSeekV4GroupedOutputCheckError(
            f"{label} fields differ; missing={sorted(keys - observed)}, "
            f"extra={sorted(observed - keys)}"
        )
    return record


def _array(value: object, label: str) -> list[Any]:
    if type(value) is not list:
        raise DeepSeekV4GroupedOutputCheckError(f"{label} must be an array")
    return value


def _integer(value: object, label: str, *, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum:
        raise DeepSeekV4GroupedOutputCheckError(
            f"{label} must be an integer >= {minimum}"
        )
    return value


def _digest(value: object, label: str) -> str:
    if (
        type(value) is not str
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise DeepSeekV4GroupedOutputCheckError(
            f"{label} must be a lowercase SHA-256 digest"
        )
    return value


def _topology(world_size: object, rank: object) -> tuple[int, int, int, int, int]:
    if type(world_size) is not int or world_size not in TENSOR_PARALLEL_WORLD_SIZES:
        raise DeepSeekV4GroupedOutputCheckError(
            "world_size must be exactly 1, 2, 4, or 8"
        )
    if type(rank) is not int or not 0 <= rank < world_size:
        raise DeepSeekV4GroupedOutputCheckError(
            f"rank must be an integer in [0, {world_size - 1}]"
        )
    local_groups = GLOBAL_GROUP_COUNT // world_size
    group_start = rank * local_groups
    row_start = group_start * OUTPUT_RANK_PER_GROUP
    return world_size, rank, local_groups, group_start, row_start


def _assignment_path(rank: int) -> str:
    return f"ranks/rank-{rank:03d}/layers.0.attn.wo_a.weight.bin"


def _segments(world_size: int, rank: int) -> list[dict[str, Any]]:
    _, _, local_groups, group_start, row_start = _topology(world_size, rank)
    del local_groups, group_start
    row_stop = row_start + (GLOBAL_GROUP_COUNT // world_size) * OUTPUT_RANK_PER_GROUP
    result: list[dict[str, Any]] = []
    for assignment_rank in range(4):
        assignment_start = assignment_rank * 2_048
        assignment_stop = assignment_start + 2_048
        start = max(row_start, assignment_start)
        stop = min(row_stop, assignment_stop)
        if start >= stop:
            continue
        half_index = start // 1_024
        digest = (
            _ASSIGNMENT_HASHES[assignment_rank]
            if stop - start == 2_048
            else _HALF_ASSIGNMENT_HASHES[half_index]
        )
        result.append(
            {
                "assignment_rank": assignment_rank,
                "byte_offset": (start - assignment_start) * ROW_BYTES,
                "content_sha256": digest,
                "global_row_range": [start, stop],
                "path": _assignment_path(assignment_rank),
                "size_bytes": (stop - start) * ROW_BYTES,
            }
        )
    return result


def _assert_frozen_compiler_contracts() -> None:
    """Cross-check all fifteen public mappings against independent constants."""

    observed = topology_mappings()
    expected_keys = tuple(
        (world_size, rank)
        for world_size in TENSOR_PARALLEL_WORLD_SIZES
        for rank in range(world_size)
    )
    if tuple((item.world_size, item.rank) for item in observed) != expected_keys:
        raise DeepSeekV4GroupedOutputCheckError(
            "committed topology set differs from the fifteen legal mappings"
        )
    for item in observed:
        key = (item.world_size, item.rank)
        _, _, local_groups, group_start, row_start = _topology(*key)
        expected_segments = _segments(*key)
        actual_segments = [
            {
                "assignment_rank": segment.assignment_rank,
                "byte_offset": segment.byte_offset,
                "content_sha256": segment.content_sha256,
                "global_row_range": [
                    segment.global_row_start,
                    segment.global_row_stop,
                ],
                "path": segment.path,
                "size_bytes": segment.size_bytes,
            }
            for segment in item.segments
        ]
        if (
            item.local_group_count != local_groups
            or item.global_group_start != group_start
            or item.global_group_stop != group_start + local_groups
            or item.global_row_start != row_start
            or item.global_row_stop != row_start + local_groups * OUTPUT_RANK_PER_GROUP
            or item.shape
            != (local_groups * OUTPUT_RANK_PER_GROUP, GROUP_INPUT_FEATURES)
            or item.size_bytes != local_groups * OUTPUT_RANK_PER_GROUP * ROW_BYTES
            or item.content_sha256 != FROZEN_MAPPING_HASHES[key]
            or not _canonical_equal(actual_segments, expected_segments)
        ):
            raise DeepSeekV4GroupedOutputCheckError(
                f"committed topology mapping {key} differs from frozen evidence"
            )

    source = build_source_contract()
    verify_source_contract(source)
    if source.get("source_contract_id") != FROZEN_SOURCE_CONTRACT_ID:
        raise DeepSeekV4GroupedOutputCheckError(
            "committed source contract differs from its frozen identity"
        )


def _decode_frozen_program(
    payload: bytes,
    world_size: int,
    rank: int,
) -> list[dict[str, int]]:
    """Decode the grouped-output wire ABI without calling its decoder."""

    if type(payload) is not bytes or len(payload) != FROZEN_PROGRAM_BYTES:
        raise DeepSeekV4GroupedOutputCheckError(
            "committed grouped-output program has an unexpected byte length"
        )
    magic, major, minor, record_size, count, expected_crc = HEADER.unpack_from(payload)
    if (magic, major, minor, record_size, count) != (
        b"OTGO",
        1,
        0,
        36,
        2,
    ):
        raise DeepSeekV4GroupedOutputCheckError(
            "committed grouped-output wire header differs from the frozen ABI"
        )
    body = payload[HEADER.size :]
    if len(body) != count * record_size:
        raise DeepSeekV4GroupedOutputCheckError(
            "committed grouped-output wire body length differs from its header"
        )
    if zlib.crc32(body) & 0xFFFFFFFF != expected_crc:
        raise DeepSeekV4GroupedOutputCheckError(
            "committed grouped-output wire body fails CRC32"
        )
    _, _, local_groups, _, _ = _topology(world_size, rank)
    expected = [
        {
            "destination0": 1,
            "destination1": 2,
            "flags": 0,
            "immediate0": world_size,
            "immediate1": rank,
            "immediate2": local_groups,
            "immediate3": OUTPUT_RANK_PER_GROUP,
            "opcode": 0x30,
            "resource0": 0,
            "source": 0,
        },
        {
            "destination0": NO_OPERAND,
            "destination1": NO_OPERAND,
            "flags": 0,
            "immediate0": 0,
            "immediate1": 0,
            "immediate2": 0,
            "immediate3": 0,
            "opcode": 0xFF,
            "resource0": NO_OPERAND,
            "source": NO_OPERAND,
        },
    ]
    decoded: list[dict[str, int]] = []
    for index in range(count):
        unpacked = RECORD.unpack_from(body, index * record_size)
        opcode, flags, reserved = unpacked[:3]
        if reserved != 0 or flags != 0:
            raise DeepSeekV4GroupedOutputCheckError(
                f"committed grouped-output instruction {index} has control bits"
            )
        operands = unpacked[3:]
        decoded.append(
            {
                "destination0": operands[0],
                "destination1": operands[1],
                "flags": flags,
                "immediate0": operands[4],
                "immediate1": operands[5],
                "immediate2": operands[6],
                "immediate3": operands[7],
                "opcode": opcode,
                "resource0": operands[3],
                "source": operands[2],
            }
        )
    if not _canonical_equal(decoded, expected):
        raise DeepSeekV4GroupedOutputCheckError(
            "committed grouped-output operands differ from the frozen program"
        )
    return decoded


def _expected_resources(world_size: int, rank: int) -> list[dict[str, Any]]:
    _, _, local_groups, group_start, row_start = _topology(world_size, rank)
    row_count = local_groups * OUTPUT_RANK_PER_GROUP
    expected = [
        {
            "canonical_application_id": CANONICAL_APPLICATION_ID,
            "checkpoint_derived": True,
            "content_sha256": FROZEN_MAPPING_HASHES[(world_size, rank)],
            "dtype": "BF16",
            "global_group_range": [group_start, group_start + local_groups],
            "global_row_range": [row_start, row_start + row_count],
            "rank": rank,
            "resource_id": 0,
            "resource_name": "LAYER0_WO_A_LOCAL_BF16",
            "role": "layers.0.attn.wo_a.weight.local",
            "segments": _segments(world_size, rank),
            "shape": [row_count, GROUP_INPUT_FEATURES],
            "size_bytes": row_count * ROW_BYTES,
            "world_size": world_size,
        }
    ]
    specs = resource_contract(world_size, rank)
    verify_resource_contract(specs, world_size, rank)
    observed = [
        {
            "canonical_application_id": spec.canonical_application_id,
            "checkpoint_derived": spec.checkpoint_derived,
            "content_sha256": spec.content_sha256,
            "dtype": spec.dtype,
            "global_group_range": [
                spec.global_group_start,
                spec.global_group_stop,
            ],
            "global_row_range": [spec.global_row_start, spec.global_row_stop],
            "rank": spec.rank,
            "resource_id": int(spec.resource),
            "resource_name": spec.resource.name,
            "role": spec.role,
            "segments": [
                {
                    "assignment_rank": segment.assignment_rank,
                    "byte_offset": segment.byte_offset,
                    "content_sha256": segment.content_sha256,
                    "global_row_range": [
                        segment.global_row_start,
                        segment.global_row_stop,
                    ],
                    "path": segment.path,
                    "size_bytes": segment.size_bytes,
                }
                for segment in spec.segments
            ],
            "shape": list(spec.shape),
            "size_bytes": spec.size_bytes,
            "world_size": spec.world_size,
        }
        for spec in specs
    ]
    if not _canonical_equal(observed, expected):
        raise DeepSeekV4GroupedOutputCheckError(
            "committed grouped-output resource differs from frozen topology evidence"
        )
    return expected


def _expected_registers(world_size: int, rank: int) -> list[dict[str, Any]]:
    _, _, local_groups, _, _ = _topology(world_size, rank)
    lower = tensor_contract(MIN_TOKEN_COUNT, world_size, rank)
    upper = tensor_contract(MAX_TOKEN_COUNT, world_size, rank)
    verify_tensor_contract(lower, MIN_TOKEN_COUNT, world_size, rank)
    verify_tensor_contract(upper, MAX_TOKEN_COUNT, world_size, rank)
    expected = [
        {
            "alias_of_register_id": None,
            "alias_of_register_name": None,
            "consumer_slots": [0],
            "dtype": "BF16",
            "evidence_observable": True,
            "live_at_complete": False,
            "producer_kind": "external",
            "producer_slot": None,
            "register_id": 0,
            "register_name": "GROUPED_ATTENTION_INPUT",
            "token_major_shape_suffix": [local_groups * HEADS_PER_GROUP, HEAD_DIM],
        },
        {
            "alias_of_register_id": None,
            "alias_of_register_name": None,
            "consumer_slots": [],
            "dtype": "BF16",
            "evidence_observable": True,
            "live_at_complete": True,
            "producer_kind": "slot",
            "producer_slot": 0,
            "register_id": 1,
            "register_name": "GROUPED_OUTPUT",
            "token_major_shape_suffix": [local_groups, OUTPUT_RANK_PER_GROUP],
        },
        {
            "alias_of_register_id": 1,
            "alias_of_register_name": "GROUPED_OUTPUT",
            "consumer_slots": [],
            "dtype": "BF16",
            "evidence_observable": True,
            "live_at_complete": True,
            "producer_kind": "slot",
            "producer_slot": 0,
            "register_id": 2,
            "register_name": "FLATTENED_OUTPUT",
            "token_major_shape_suffix": [local_groups * OUTPUT_RANK_PER_GROUP],
        },
    ]
    observed: list[dict[str, Any]] = []
    for minimum, maximum in zip(lower, upper, strict=True):
        if (
            minimum.register != maximum.register
            or minimum.dtype != maximum.dtype
            or minimum.shape[0] != MIN_TOKEN_COUNT
            or maximum.shape[0] != MAX_TOKEN_COUNT
            or minimum.shape[1:] != maximum.shape[1:]
            or minimum.live_at_complete != maximum.live_at_complete
            or minimum.evidence_observable != maximum.evidence_observable
            or minimum.alias_of != maximum.alias_of
        ):
            raise DeepSeekV4GroupedOutputCheckError(
                "committed grouped-output tensor bounds are inconsistent"
            )
        register_id = int(minimum.register)
        observed.append(
            {
                "alias_of_register_id": (
                    None if minimum.alias_of is None else int(minimum.alias_of)
                ),
                "alias_of_register_name": (
                    None if minimum.alias_of is None else minimum.alias_of.name
                ),
                "consumer_slots": [0] if register_id == 0 else [],
                "dtype": minimum.dtype,
                "evidence_observable": minimum.evidence_observable,
                "live_at_complete": minimum.live_at_complete,
                "producer_kind": "external" if register_id == 0 else "slot",
                "producer_slot": None if register_id == 0 else 0,
                "register_id": register_id,
                "register_name": minimum.register.name,
                "token_major_shape_suffix": list(minimum.shape[1:]),
            }
        )
    if not _canonical_equal(observed, expected):
        raise DeepSeekV4GroupedOutputCheckError(
            "committed grouped-output registers differ from frozen typed bounds"
        )
    return expected


def _expected_slots(instructions: Sequence[Mapping[str, int]]) -> list[dict[str, Any]]:
    project, complete = instructions
    return [
        {
            "dependency_slots": [],
            "destination_register_ids": [
                project["destination0"],
                project["destination1"],
            ],
            "external_input_register_ids": [project["source"]],
            "flags": project["flags"],
            "immediates": [
                project["immediate0"],
                project["immediate1"],
                project["immediate2"],
                project["immediate3"],
            ],
            "instruction_index": 0,
            "instruction_sha256": _sha256(dict(project)),
            "opcode": "GROUPED_OUTPUT_PROJECT",
            "opcode_code": project["opcode"],
            "resource_ids": [project["resource0"]],
            "slot": 0,
            "source_register_ids": [project["source"]],
            "terminal": False,
        },
        {
            "dependency_slots": [0],
            "destination_register_ids": [],
            "external_input_register_ids": [],
            "flags": complete["flags"],
            "immediates": [
                complete["immediate0"],
                complete["immediate1"],
                complete["immediate2"],
                complete["immediate3"],
            ],
            "instruction_index": 1,
            "instruction_sha256": _sha256(dict(complete)),
            "opcode": "COMPLETE",
            "opcode_code": complete["opcode"],
            "resource_ids": [],
            "slot": 1,
            "source_register_ids": [],
            "terminal": True,
        },
    ]


def _expected_counts(world_size: int, rank: int) -> dict[str, int]:
    _, _, local_groups, _, _ = _topology(world_size, rank)
    return {
        "alias_register_count": 1,
        "canonical_resource_bytes": (local_groups * OUTPUT_RANK_PER_GROUP * ROW_BYTES),
        "complete_count": 1,
        "dependency_edge_count": 1,
        "evidence_observable_register_count": 3,
        "external_input_register_count": 1,
        "grouped_output_project_count": 1,
        "instruction_count": 2,
        "live_at_complete_register_count": 2,
        "local_group_count": local_groups,
        "produced_register_count": 2,
        "register_count": 3,
        "resource_count": 1,
        "resource_read_count": 1,
        "slot_count": 2,
    }


def _verify_causality(
    slots: Sequence[Mapping[str, Any]],
    registers: Sequence[Mapping[str, Any]],
    resources: Sequence[Mapping[str, Any]],
) -> None:
    register_by_id = {
        _integer(record.get("register_id"), "register_id"): record
        for record in registers
    }
    resource_ids = {
        _integer(record.get("resource_id"), "resource_id") for record in resources
    }
    if len(register_by_id) != len(registers) or len(resource_ids) != len(resources):
        raise DeepSeekV4GroupedOutputCheckError(
            "register or resource identity is duplicated"
        )
    observed_producers: dict[int, int] = {}
    observed_consumers: dict[int, list[int]] = {
        register_id: [] for register_id in register_by_id
    }
    terminal_count = 0
    for index, slot in enumerate(slots):
        if slot.get("slot") != index or slot.get("instruction_index") != index:
            raise DeepSeekV4GroupedOutputCheckError(
                f"logical slot {index} is not monotonically ordered"
            )
        dependencies = [
            _integer(item, "dependency slot")
            for item in _array(slot.get("dependency_slots"), "dependency slots")
        ]
        if dependencies != sorted(set(dependencies)) or any(
            item >= index for item in dependencies
        ):
            raise DeepSeekV4GroupedOutputCheckError(
                f"logical slot {index} has invalid dependencies"
            )
        required_dependencies: set[int] = set()
        required_external: set[int] = set()
        for raw_id in _array(slot.get("source_register_ids"), "source register IDs"):
            register_id = _integer(raw_id, "source register ID")
            if register_id not in register_by_id:
                raise DeepSeekV4GroupedOutputCheckError(
                    f"logical slot {index} reads unknown register {register_id}"
                )
            record = register_by_id[register_id]
            observed_consumers[register_id].append(index)
            if record.get("producer_kind") == "external":
                if record.get("producer_slot") is not None:
                    raise DeepSeekV4GroupedOutputCheckError(
                        "external register unexpectedly has a producer slot"
                    )
                required_external.add(register_id)
            else:
                producer = record.get("producer_slot")
                if type(producer) is not int or producer >= index:
                    raise DeepSeekV4GroupedOutputCheckError(
                        f"logical slot {index} consumes a non-preceding producer"
                    )
                required_dependencies.add(producer)
        external = {
            _integer(item, "external register ID")
            for item in _array(
                slot.get("external_input_register_ids"), "external register IDs"
            )
        }
        if external != required_external:
            raise DeepSeekV4GroupedOutputCheckError(
                f"logical slot {index} external inputs differ from its sources"
            )
        destinations = [
            _integer(item, "destination register ID")
            for item in _array(
                slot.get("destination_register_ids"), "destination register IDs"
            )
        ]
        if destinations != list(dict.fromkeys(destinations)):
            raise DeepSeekV4GroupedOutputCheckError(
                f"logical slot {index} duplicates a destination"
            )
        for register_id in destinations:
            if (
                register_id not in register_by_id
                or register_by_id[register_id].get("producer_slot") != index
                or register_id in observed_producers
            ):
                raise DeepSeekV4GroupedOutputCheckError(
                    f"logical slot {index} has an incorrect producer"
                )
            observed_producers[register_id] = index
        used_resources = [
            _integer(item, "resource ID")
            for item in _array(slot.get("resource_ids"), "resource IDs")
        ]
        if (
            used_resources != list(dict.fromkeys(used_resources))
            or not set(used_resources) <= resource_ids
        ):
            raise DeepSeekV4GroupedOutputCheckError(
                f"logical slot {index} uses duplicated or unknown resources"
            )
        if slot.get("terminal") is True:
            terminal_count += 1
            if (
                index != len(slots) - 1
                or dependencies != list(range(index))
                or destinations
                or slot.get("source_register_ids") != []
                or used_resources
            ):
                raise DeepSeekV4GroupedOutputCheckError(
                    "terminal COMPLETE is not the final all-predecessor barrier"
                )
        elif set(dependencies) != required_dependencies:
            raise DeepSeekV4GroupedOutputCheckError(
                f"logical slot {index} dependencies differ from causality"
            )
    if terminal_count != 1 or not slots or slots[-1].get("opcode") != "COMPLETE":
        raise DeepSeekV4GroupedOutputCheckError(
            "logical schedule lacks one exact terminal COMPLETE"
        )
    for register_id, record in register_by_id.items():
        if not _canonical_equal(
            record.get("consumer_slots"), observed_consumers[register_id]
        ):
            raise DeepSeekV4GroupedOutputCheckError(
                f"register {register_id} consumer table differs from slot reads"
            )
        if record.get("producer_kind") == "external":
            if register_id in observed_producers:
                raise DeepSeekV4GroupedOutputCheckError(
                    f"external register {register_id} is also produced"
                )
        elif observed_producers.get(register_id) != record.get("producer_slot"):
            raise DeepSeekV4GroupedOutputCheckError(
                f"register {register_id} producer table differs from slot writes"
            )


def verify_deepseek_v4_grouped_output_logical_schedule(
    value: object,
) -> dict[str, Any]:
    """Verify one local-rank schedule and return a logical certificate."""

    schedule = _exact(
        value,
        {
            "claim_boundary",
            "identity",
            "ordering_policy",
            "registers",
            "required_nonclaims",
            "resources",
            "schedule_id",
            "schema",
            "slots",
            "status",
            "summary",
            "topology",
        },
        "grouped-output logical schedule",
    )
    if schedule["schema"] != LOGICAL_SCHEDULE_SCHEMA:
        raise DeepSeekV4GroupedOutputCheckError(
            "unsupported grouped-output logical schedule schema"
        )
    if schedule["status"] != LOGICAL_SCHEDULE_STATUS:
        raise DeepSeekV4GroupedOutputCheckError("logical schedule status differs")
    body = {key: schedule[key] for key in schedule if key != "schedule_id"}
    if _digest(schedule["schedule_id"], "schedule_id") != _sha256(body):
        raise DeepSeekV4GroupedOutputCheckError(
            "schedule_id does not bind canonical schedule serialization"
        )
    if schedule["claim_boundary"] != CLAIM_BOUNDARY:
        raise DeepSeekV4GroupedOutputCheckError("schedule claim boundary differs")
    if not _canonical_equal(schedule["ordering_policy"], ORDERING_POLICY):
        raise DeepSeekV4GroupedOutputCheckError("schedule ordering policy differs")
    if not _canonical_equal(schedule["required_nonclaims"], REQUIRED_NONCLAIMS):
        raise DeepSeekV4GroupedOutputCheckError("schedule nonclaims differ")

    topology = _exact(
        schedule["topology"],
        {
            "global_group_range",
            "global_row_range",
            "local_group_count",
            "rank",
            "world_size",
        },
        "schedule topology",
    )
    world_size = topology.get("world_size")
    rank = topology.get("rank")
    world_size, rank, local_groups, group_start, row_start = _topology(
        world_size,
        rank,
    )
    expected_topology = {
        "global_group_range": [group_start, group_start + local_groups],
        "global_row_range": [
            row_start,
            row_start + local_groups * OUTPUT_RANK_PER_GROUP,
        ],
        "local_group_count": local_groups,
        "rank": rank,
        "world_size": world_size,
    }
    if not _canonical_equal(topology, expected_topology):
        raise DeepSeekV4GroupedOutputCheckError(
            "schedule topology does not exactly partition global groups and rows"
        )

    _assert_frozen_compiler_contracts()
    program = assemble(world_size, rank)
    verify(program, world_size, rank)
    program_payload = encode(program, world_size, rank)
    key = (world_size, rank)
    if (
        len(program_payload) != FROZEN_PROGRAM_BYTES
        or hashlib.sha256(program_payload).hexdigest() != FROZEN_PROGRAM_SHA256[key]
    ):
        raise DeepSeekV4GroupedOutputCheckError(
            "committed grouped-output program differs from its frozen identity"
        )
    instructions = _decode_frozen_program(program_payload, world_size, rank)
    program_contract = build_program_contract(world_size, rank)
    verify_program_contract(program_contract, world_size, rank)
    if program_contract.get("contract_id") != FROZEN_PROGRAM_CONTRACT_IDS[key]:
        raise DeepSeekV4GroupedOutputCheckError(
            "committed grouped-output program contract identity differs"
        )

    expected_resources = _expected_resources(world_size, rank)
    expected_registers = _expected_registers(world_size, rank)
    expected_slots = _expected_slots(instructions)
    expected_identity = {
        "abi_magic_ascii": MAGIC.decode("ascii"),
        "abi_major": ABI_MAJOR,
        "abi_minor": ABI_MINOR,
        "canonical_application_id": CANONICAL_APPLICATION_ID,
        "canonical_verification_id": CANONICAL_VERIFICATION_ID,
        "instruction_record_bytes": RECORD.size,
        "model_id": MODEL_ID,
        "program_bytes": FROZEN_PROGRAM_BYTES,
        "program_contract_id": FROZEN_PROGRAM_CONTRACT_IDS[key],
        "program_sha256": FROZEN_PROGRAM_SHA256[key],
        "register_table_sha256": _sha256(expected_registers),
        "repository": MODEL_REPOSITORY,
        "resource_table_sha256": _sha256(expected_resources),
        "revision": MODEL_REVISION,
        "source_contract_id": FROZEN_SOURCE_CONTRACT_ID,
        "token_count_maximum": MAX_TOKEN_COUNT,
        "token_count_minimum": MIN_TOKEN_COUNT,
    }
    if not _canonical_equal(schedule["identity"], expected_identity):
        raise DeepSeekV4GroupedOutputCheckError(
            "schedule program, source, or table identity differs"
        )
    resources = _array(schedule["resources"], "schedule resources")
    registers = _array(schedule["registers"], "schedule registers")
    slots = _array(schedule["slots"], "schedule slots")
    if not _canonical_equal(resources, expected_resources):
        raise DeepSeekV4GroupedOutputCheckError(
            "schedule resource identity or topology bounds differ"
        )
    if not _canonical_equal(registers, expected_registers):
        raise DeepSeekV4GroupedOutputCheckError(
            "schedule register identity, aliasing, or causality differs"
        )
    if not _canonical_equal(slots, expected_slots):
        raise DeepSeekV4GroupedOutputCheckError(
            "schedule instruction identity or ordering differs"
        )
    _verify_causality(slots, registers, resources)
    counts = _expected_counts(world_size, rank)
    if not _canonical_equal(schedule["summary"], counts):
        raise DeepSeekV4GroupedOutputCheckError(
            "schedule exact count reconciliation differs"
        )

    certificate_body = {
        "checks": {
            "all_fifteen_topology_mappings": True,
            "alias_view_identity": True,
            "canonical_resource_identity": True,
            "canonical_serialization_hash": True,
            "exact_count_reconciliation": True,
            "instruction_identity": True,
            "producer_before_consumer": True,
            "source_contract_identity": True,
            "terminal_complete": True,
            "wire_program_decode": True,
        },
        "claim_boundary": CERTIFICATE_CLAIM_BOUNDARY,
        "counts": counts,
        "program_contract_id": FROZEN_PROGRAM_CONTRACT_IDS[key],
        "program_sha256": FROZEN_PROGRAM_SHA256[key],
        "register_table_sha256": expected_identity["register_table_sha256"],
        "required_nonclaims": list(REQUIRED_NONCLAIMS),
        "resource_table_sha256": expected_identity["resource_table_sha256"],
        "schedule_id": schedule["schedule_id"],
        "schema": LOGICAL_CERTIFICATE_SCHEMA,
        "source_contract_id": FROZEN_SOURCE_CONTRACT_ID,
        "status": CERTIFICATE_STATUS,
        "topology": dict(expected_topology),
    }
    return {
        **certificate_body,
        "certificate_id": _sha256(certificate_body),
    }


def verify_deepseek_v4_grouped_output_logical_schedule_certificate(
    value: object,
    schedule: object,
) -> None:
    """Require a logical certificate to equal a fresh independent check."""

    expected = verify_deepseek_v4_grouped_output_logical_schedule(schedule)
    certificate = _exact(
        value,
        set(expected),
        "grouped-output logical schedule certificate",
    )
    if not _canonical_equal(dict(certificate), expected):
        raise DeepSeekV4GroupedOutputCheckError(
            "logical schedule certificate differs from independent verification"
        )


def _file_sha256(path: Path, label: str) -> str:
    if not path.is_file():
        raise DeepSeekV4GroupedOutputCheckError(f"{label} is not a file: {path}")
    digest = hashlib.sha256()
    try:
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1 << 20), b""):
                digest.update(chunk)
    except OSError as exc:
        raise DeepSeekV4GroupedOutputCheckError(f"cannot hash {label}: {exc}") from exc
    return digest.hexdigest()


def _require_file_hash(path: Path, expected: str, label: str) -> None:
    observed = _file_sha256(path, label)
    if observed != expected:
        raise DeepSeekV4GroupedOutputCheckError(
            f"{label} SHA-256 differs; observed {observed}"
        )


def _relevant_application_records(
    application: Mapping[str, Any],
) -> tuple[Mapping[str, Any], Mapping[str, Any], list[Mapping[str, Any]]]:
    inputs = application.get("inputs")
    assignments = application.get("assignments")
    if type(inputs) is not list or type(assignments) is not list:
        raise DeepSeekV4GroupedOutputCheckError(
            "canonical application lacks input or assignment arrays"
        )
    weight_inputs = [
        _mapping(record, "wo_a weight input")
        for record in inputs
        if isinstance(record, Mapping)
        and record.get("name") == "layers.0.attn.wo_a.weight"
    ]
    scale_inputs = [
        _mapping(record, "wo_a scale input")
        for record in inputs
        if isinstance(record, Mapping)
        and record.get("name") == "layers.0.attn.wo_a.scale"
    ]
    wo_a_assignments = [
        _mapping(record, "wo_a assignment")
        for record in assignments
        if isinstance(record, Mapping)
        and record.get("name") == "layers.0.attn.wo_a.weight"
    ]
    if len(weight_inputs) != 1 or len(scale_inputs) != 1 or len(wo_a_assignments) != 4:
        raise DeepSeekV4GroupedOutputCheckError(
            "canonical application does not contain one wo_a weight input, one "
            "scale input, and four BF16 assignments"
        )
    return weight_inputs[0], scale_inputs[0], wo_a_assignments


def _expected_application_assignments() -> list[dict[str, Any]]:
    return [
        {
            "logical_dtype": "BF16",
            "name": "layers.0.attn.wo_a.weight",
            "path": _assignment_path(rank),
            "payload_bytes": 16_777_216,
            "rank": rank,
            "scale_source": {
                "name": "layers.0.attn.wo_a.scale",
                "payload_sha256": RAW_LAYER0_WO_A_SCALE_SHA256,
                "shape": [64, 32],
                "slice": {
                    "axis": 0,
                    "start": rank * 16,
                    "stop": (rank + 1) * 16,
                },
                "storage_dtype": "F8_E8M0",
            },
            "sha256": _ASSIGNMENT_HASHES[rank],
            "shape": [2_048, 4_096],
            "source": {
                "name": "layers.0.attn.wo_a.weight",
                "payload_sha256": RAW_LAYER0_WO_A_WEIGHT_SHA256,
                "shape": [8_192, 4_096],
                "slice": {
                    "axis": 0,
                    "start": rank * 2_048,
                    "stop": (rank + 1) * 2_048,
                },
                "storage_dtype": "F8_E4M3",
            },
            "storage_dtype": "BF16",
            "transform": "dequantize_fp8_e8m0_to_bf16_rne",
        }
        for rank in range(4)
    ]


def _expected_verification_checks() -> list[dict[str, Any]]:
    check_ids = (
        "262e31d8aee1df5f19ee5d21a1537750024424fb835fd974f905c9eaab4f99bf",
        "cda77b23fa9a73bd28be62b1ee20b4e06cd13ccc1c344acfcb428ef21d187089",
        "bde22aa0c6b9bfabcc591c7f25b8733dda0bc64a39f113a959df732a066ac3ca",
        "f50d63d0360345597c57dabee2ffb43d86cd721ec63b077c32a7174fb372ef5b",
    )
    detail_ids = (
        "3b49bfde73ca7d8501eed1ae99bffbc273bbdddc4a7ed252d3537486537bde27",
        "ae25b90dce5b330f93401cf81bb8f914872e6e05c498a84ee6d78dfa0f40738d",
        "0cfd4538a113e8b2a862a8a3bc3c0946baf6cf0d387ffb5d44a4d1a995019dbc",
        "c5fa7dcce51b2309993515b5a45725897f4a1df2e3847265c008eb950d2e4777",
    )
    return [
        {
            "assignment_path": _assignment_path(rank),
            "check_id": check_ids[rank],
            "checked_output_bytes": 16_777_216,
            "detail_check_id": detail_ids[rank],
            "method": "independent_fp8_e8m0_bf16",
            "output_sha256": _ASSIGNMENT_HASHES[rank],
            "rank": rank,
            "source_name": "layers.0.attn.wo_a.weight",
            "status": "full_payload_match",
            "transform": "dequantize_fp8_e8m0_to_bf16_rne",
        }
        for rank in range(4)
    ]


def _hash_segments(
    root: Path,
    segments: Sequence[Mapping[str, Any]],
) -> str:
    digest = hashlib.sha256()
    streams: dict[str, BinaryIO] = {}
    try:
        for segment in segments:
            relative = segment["path"]
            if type(relative) is not str:
                raise DeepSeekV4GroupedOutputCheckError(
                    "resource segment path must be a string"
                )
            path = root / relative
            try:
                resolved = path.resolve(strict=True)
                resolved.relative_to(root.resolve(strict=True))
            except (OSError, ValueError) as exc:
                raise DeepSeekV4GroupedOutputCheckError(
                    f"resource segment path is unavailable or escapes root: {relative}"
                ) from exc
            if path.is_symlink() or not path.is_file():
                raise DeepSeekV4GroupedOutputCheckError(
                    f"resource segment is not a regular non-symlink file: {relative}"
                )
            stream = streams.get(relative)
            if stream is None:
                stream = path.open("rb")
                streams[relative] = stream
            offset = _integer(segment["byte_offset"], "segment byte offset")
            remaining = _integer(
                segment["size_bytes"],
                "segment size bytes",
                minimum=1,
            )
            stream.seek(offset)
            while remaining:
                chunk = stream.read(min(remaining, 1 << 20))
                if not chunk:
                    raise DeepSeekV4GroupedOutputCheckError(
                        f"resource segment is truncated: {relative}"
                    )
                digest.update(chunk)
                remaining -= len(chunk)
    except OSError as exc:
        raise DeepSeekV4GroupedOutputCheckError(
            f"cannot read canonical wo_a resource: {exc}"
        ) from exc
    finally:
        for stream in streams.values():
            stream.close()
    return digest.hexdigest()


def verify_deepseek_v4_grouped_output_official_evidence(
    snapshot_root: Path,
    checkpoint_lock_path: Path,
    application_root: Path,
) -> dict[str, Any]:
    """Authenticate cached official source and all local ``wo_a`` mappings."""

    snapshot_root = Path(snapshot_root)
    checkpoint_lock_path = Path(checkpoint_lock_path)
    application_root = Path(application_root)
    application_path = application_root / "canonical_application.json"
    verification_path = application_root / "canonical_verification.json"
    _require_file_hash(
        checkpoint_lock_path,
        CHECKPOINT_LOCK_FILE_SHA256,
        "checkpoint lock",
    )
    _require_file_hash(
        application_path,
        CANONICAL_APPLICATION_FILE_SHA256,
        "canonical application",
    )
    _require_file_hash(
        verification_path,
        CANONICAL_VERIFICATION_FILE_SHA256,
        "canonical verification",
    )
    for relative, expected in (
        (MODEL_SOURCE_PATH, MODEL_SOURCE_SHA256),
        (CONVERT_SOURCE_PATH, CONVERT_SOURCE_SHA256),
        (INFERENCE_CONFIG_PATH, INFERENCE_CONFIG_SHA256),
        (CHECKPOINT_INDEX_PATH, CHECKPOINT_INDEX_SHA256),
    ):
        _require_file_hash(snapshot_root / relative, expected, relative)

    try:
        lock = load_strict_json(checkpoint_lock_path)
        application = load_strict_json(application_path)
        verification = load_strict_json(verification_path)
    except (OSError, ValueError) as exc:
        raise DeepSeekV4GroupedOutputCheckError(
            f"cannot load official grouped-output evidence: {exc}"
        ) from exc
    source = _mapping(lock.get("source"), "checkpoint source")
    if (
        lock.get("schema") != "opentallas.checkpoint_lock.v1"
        or lock.get("lock_id") != CHECKPOINT_LOCK_ID
        or source.get("repository") != MODEL_REPOSITORY
        or source.get("revision") != MODEL_REVISION
        or source.get("remote_code_policy") != "disabled"
        or source.get("checkpoint_index") != CHECKPOINT_INDEX_PATH
    ):
        raise DeepSeekV4GroupedOutputCheckError(
            "checkpoint lock source identity or remote-code policy differs"
        )
    expected_file_hashes = {
        MODEL_SOURCE_PATH: MODEL_SOURCE_SHA256,
        CONVERT_SOURCE_PATH: CONVERT_SOURCE_SHA256,
        INFERENCE_CONFIG_PATH: INFERENCE_CONFIG_SHA256,
        CHECKPOINT_INDEX_PATH: CHECKPOINT_INDEX_SHA256,
    }
    file_records = lock.get("files")
    if type(file_records) is not list:
        raise DeepSeekV4GroupedOutputCheckError(
            "checkpoint lock files must be an array"
        )
    selected_files = {
        record.get("path"): record.get("sha256")
        for record in file_records
        if isinstance(record, Mapping) and record.get("path") in expected_file_hashes
    }
    if not _canonical_equal(selected_files, expected_file_hashes):
        raise DeepSeekV4GroupedOutputCheckError(
            "checkpoint lock does not bind all required source files"
        )

    application_source = _mapping(application.get("source"), "application source")
    if (
        application.get("application_id") != CANONICAL_APPLICATION_ID
        or application.get("schema") != "opentallas.canonical_application.v1"
        or application.get("status") != "complete_official_transform_application"
        or application.get("evidence_scope") != "official_checkpoint"
        or application_source.get("checkpoint_lock_id") != CHECKPOINT_LOCK_ID
        or application_source.get("repository") != MODEL_REPOSITORY
        or application_source.get("revision") != MODEL_REVISION
    ):
        raise DeepSeekV4GroupedOutputCheckError(
            "canonical application source identity or completion status differs"
        )
    weight_input, scale_input, assignments = _relevant_application_records(application)
    expected_weight_input = {
        "action": "slice_then_dequantize_wo_a_to_bf16",
        "logical_dtype": "FP8_E4M3FN",
        "name": "layers.0.attn.wo_a.weight",
        "payload_sha256": RAW_LAYER0_WO_A_WEIGHT_SHA256,
        "shape": [8_192, 4_096],
        "size_bytes": 33_554_432,
        "storage_dtype": "F8_E4M3",
    }
    expected_scale_input = {
        "action": "consume_wo_a_scale",
        "logical_dtype": "UE8M0_SCALE",
        "name": "layers.0.attn.wo_a.scale",
        "payload_sha256": RAW_LAYER0_WO_A_SCALE_SHA256,
        "shape": [64, 32],
        "size_bytes": 2_048,
        "storage_dtype": "F8_E8M0",
    }
    if (
        not _canonical_equal(weight_input, expected_weight_input)
        or not _canonical_equal(scale_input, expected_scale_input)
        or not _canonical_equal(assignments, _expected_application_assignments())
    ):
        raise DeepSeekV4GroupedOutputCheckError(
            "canonical wo_a input or assignment descriptors differ"
        )

    if (
        verification.get("schema") != "opentallas.canonical_application_check.v1"
        or verification.get("status") != "full_assignment_match"
        or verification.get("verification_id") != CANONICAL_VERIFICATION_ID
        or verification.get("application_id") != CANONICAL_APPLICATION_ID
        or verification.get("checkpoint_lock_id") != CHECKPOINT_LOCK_ID
    ):
        raise DeepSeekV4GroupedOutputCheckError(
            "canonical application verification identity or status differs"
        )
    checks = verification.get("checks")
    if type(checks) is not list:
        raise DeepSeekV4GroupedOutputCheckError(
            "canonical verification checks must be an array"
        )
    wo_a_checks = [
        _mapping(record, "wo_a verification check")
        for record in checks
        if isinstance(record, Mapping)
        and record.get("source_name") == "layers.0.attn.wo_a.weight"
    ]
    if not _canonical_equal(wo_a_checks, _expected_verification_checks()):
        raise DeepSeekV4GroupedOutputCheckError(
            "independent wo_a application checks differ from frozen evidence"
        )

    _assert_frozen_compiler_contracts()
    observed_hashes: dict[str, str] = {}
    for world_size in TENSOR_PARALLEL_WORLD_SIZES:
        for rank in range(world_size):
            key = (world_size, rank)
            segments = _segments(*key)
            observed = _hash_segments(application_root, segments)
            if observed != FROZEN_MAPPING_HASHES[key]:
                raise DeepSeekV4GroupedOutputCheckError(
                    f"canonical BF16 bytes differ for topology {key}: {observed}"
                )
            observed_hashes[f"ws{world_size}-rank{rank}"] = observed

    model_source = (snapshot_root / MODEL_SOURCE_PATH).read_text(encoding="utf-8")
    frozen_source_fragment = (
        "        o = o.view(bsz, seqlen, self.n_local_groups, -1)\n"
        "        wo_a = self.wo_a.weight.view(self.n_local_groups, self.o_lora_rank, -1)\n"
        "        # NOTE: wo_a is FP8 in checkpoint; could do FP8 einsum here for better perf,\n"
        "        # but using BF16 for simplicity.\n"
        '        o = torch.einsum("bsgd,grd->bsgr", o, wo_a)\n'
        "        x = self.wo_b(o.flatten(2))\n"
    )
    if model_source.count(frozen_source_fragment) != 1:
        raise DeepSeekV4GroupedOutputCheckError(
            "official source no longer contains the frozen grouped-output sequence"
        )

    certificate_body = {
        "application_id": CANONICAL_APPLICATION_ID,
        "application_sha256": CANONICAL_APPLICATION_FILE_SHA256,
        "checks": {
            "all_fifteen_aggregate_payload_hashes": True,
            "canonical_application_identity": True,
            "canonical_verification_identity": True,
            "checkpoint_lock_identity": True,
            "exact_four_wo_a_assignments": True,
            "official_source_file_hashes": True,
            "official_source_operator_sequence": True,
            "raw_weight_and_scale_identity": True,
        },
        "checkpoint_lock_id": CHECKPOINT_LOCK_ID,
        "checkpoint_lock_sha256": CHECKPOINT_LOCK_FILE_SHA256,
        "claim_boundary": OFFICIAL_EVIDENCE_CLAIM_BOUNDARY,
        "mapping_payload_sha256": observed_hashes,
        "repository": MODEL_REPOSITORY,
        "required_nonclaims": list(REQUIRED_NONCLAIMS),
        "revision": MODEL_REVISION,
        "schema": OFFICIAL_EVIDENCE_CERTIFICATE_SCHEMA,
        "source_contract_id": FROZEN_SOURCE_CONTRACT_ID,
        "status": CERTIFICATE_STATUS,
        "verification_id": CANONICAL_VERIFICATION_ID,
        "verification_sha256": CANONICAL_VERIFICATION_FILE_SHA256,
    }
    return {
        **certificate_body,
        "certificate_id": _sha256(certificate_body),
    }


__all__ = [
    "CERTIFICATE_CLAIM_BOUNDARY",
    "CERTIFICATE_STATUS",
    "FROZEN_MAPPING_HASHES",
    "FROZEN_PROGRAM_BYTES",
    "FROZEN_PROGRAM_CONTRACT_IDS",
    "FROZEN_PROGRAM_SHA256",
    "FROZEN_SOURCE_CONTRACT_ID",
    "LOGICAL_CERTIFICATE_SCHEMA",
    "LOGICAL_SCHEDULE_SCHEMA",
    "OFFICIAL_EVIDENCE_CERTIFICATE_SCHEMA",
    "OFFICIAL_EVIDENCE_CLAIM_BOUNDARY",
    "DeepSeekV4GroupedOutputCheckError",
    "verify_deepseek_v4_grouped_output_logical_schedule",
    "verify_deepseek_v4_grouped_output_logical_schedule_certificate",
    "verify_deepseek_v4_grouped_output_official_evidence",
]
