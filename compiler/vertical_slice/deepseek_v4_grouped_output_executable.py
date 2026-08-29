"""Build an authenticated DeepSeek V4 grouped-output executable package.

The package is topology-specific and contains the complete local layer-0
canonical ``wo_a`` BF16 resource, exact OTGO microcode, typed program/source
contracts, deterministic logical schedule and independent certificate,
runtime interfaces, and the official-evidence certificate.  Source bytes are
read only from the pinned canonical MP4 application after its source, lock,
application, transform-verification, assignment, and aggregate identities
have passed the independent grouped-output evidence checker.

No activation, expected output, callback, execution result, checkpoint shard,
or reference implementation enters the package.  This slice ends at the
grouped and flattened local ``wo_a`` output views, before ``wo_b``, any tensor
parallel collective, complete attention, a transformer block, the full model,
RTL, timing, or PPA.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
import struct
from typing import Any

from compiler.checking.deepseek_v4_grouped_output import (
    verify_deepseek_v4_grouped_output_logical_schedule,
    verify_deepseek_v4_grouped_output_logical_schedule_certificate,
    verify_deepseek_v4_grouped_output_official_evidence,
)
from compiler.checking.deepseek_v4_grouped_output_executable import (
    verify_deepseek_v4_grouped_output_executable_deployment,
)
from compiler.microcode.deepseek_v4_grouped_output import (
    CANONICAL_APPLICATION_ID,
    CANONICAL_ASSIGNMENTS,
    CANONICAL_VERIFICATION_ID,
    CHECKPOINT_LOCK_ID,
    MAX_TOKEN_COUNT,
    MIN_TOKEN_COUNT,
    MODEL_ID,
    MODEL_REPOSITORY,
    MODEL_REVISION,
    OUTPUT_RANK_PER_GROUP,
    TENSOR_PARALLEL_WORLD_SIZES,
    assemble,
    build_program_contract,
    build_source_contract,
    disassemble,
    encode,
    resource_contract,
    topology_mapping,
    verify,
    verify_program_contract,
    verify_resource_contract,
    verify_source_contract,
)
from compiler.scheduling.deepseek_v4_grouped_output import (
    build_deepseek_v4_grouped_output_logical_schedule,
)
from runtime.service_engine.grouped_output_numeric import (
    GROUPED_OUTPUT_SERVICE_NUMERIC_PROFILE,
    grouped_output_functional_counters,
)
from runtime.service_engine.secure_artifacts import (
    SecureArtifactError,
    SecureDirectory,
    canonical_json_bytes,
    publish_payload_tree,
)


DEPLOYMENT_SCHEMA = "opentallas.deepseek_v4_grouped_output_executable.v1"
DEPLOYMENT_STATUS = "official_artifact_program_packaged_execution_not_evidenced"
RESOURCE_MANIFEST_SCHEMA = "opentallas.deepseek_v4_grouped_output_resources.v1"
EXECUTION_CONTRACT_SCHEMA = (
    "opentallas.deepseek_v4_grouped_output_execution_contract.v1"
)
COUNTER_CONTRACT_SCHEMA = (
    "opentallas.deepseek_v4_grouped_output_functional_counter_contract.v1"
)
COVERAGE_SCHEMA = "opentallas.deepseek_v4_grouped_output_executable_coverage.v1"
EXECUTION_REQUEST_SCHEMA = (
    "opentallas.deepseek_v4_grouped_output_execution_request.v1"
)
EXECUTION_RESULT_SCHEMA = (
    "opentallas.deepseek_v4_grouped_output_execution_result.v1"
)
COMPILER_NAME = "opentallas-deepseek-v4-grouped-output-executable-packager"
COMPILER_VERSION = "0.1.0"
MANIFEST_FILENAME = "deployment_manifest.json"
WEIGHT_PATH = "resources/layer0_wo_a_local.bf16le"

CLAIM_BOUNDARY = [
    (
        "Packages and permits artifact-only execution of the exact local "
        "GROUPED_OUTPUT_PROJECT followed by terminal COMPLETE."
    ),
    (
        "The package contains complete official layer-0 wo_a BF16 row coverage "
        "for exactly one tensor-parallel world-size/rank mapping."
    ),
    (
        "The grouped output and flattened output are two views of the same "
        "group-major values; flattening is not a second arithmetic operator."
    ),
    (
        "Requests supply external already-computed grouped attention activations; "
        "the package does not claim their producer or complete sparse attention."
    ),
    (
        "Logical counters are semantic arithmetic and shape reconciliation, not "
        "cycles, latency, bandwidth, traffic, throughput, energy, area, density, "
        "routing, or PPA."
    ),
    (
        "This slice ends before wo_b, tensor-parallel collectives, complete "
        "attention, a transformer block, the full model, RTL, or any NVIDIA comparison."
    ),
]

REQUIRED_NONCLAIMS = [
    "bandwidth",
    "checkpoint_execution",
    "complete_attention",
    "cycle_accuracy",
    "cycle_latency",
    "end_to_end_model_execution",
    "full_transformer_block_execution",
    "nvidia_comparison",
    "output_b_projection",
    "physical_schedule",
    "physical_topology",
    "ppa",
    "rtl_execution",
    "tensor_parallel_collective",
]

ENTRYPOINT = {
    "counter_contract": "interfaces/functional_counter_contract.json",
    "coverage": "evidence/execution_coverage.json",
    "execution_contract": "interfaces/execution_contract.json",
    "execution_request_schema": "interfaces/execution_request_v1.schema.json",
    "execution_result_schema": "interfaces/execution_result_v1.schema.json",
    "logical_schedule": "schedule/logical_schedule.json",
    "logical_schedule_certificate": "schedule/logical_schedule_certificate.json",
    "official_evidence_certificate": "evidence/official_evidence_certificate.json",
    "program": "program/grouped_output.bin",
    "program_contract": "program/program_contract.json",
    "program_disassembly": "program/grouped_output.disassembly.txt",
    "resource_manifest": "resources/resource_manifest.json",
    "source_contract": "program/source_contract.json",
    "weight": WEIGHT_PATH,
}

_ROLE_BY_KEY = {
    "counter_contract": "functional_counter_contract",
    "coverage": "execution_coverage",
    "execution_contract": "execution_contract",
    "execution_request_schema": "execution_request_schema",
    "execution_result_schema": "execution_result_schema",
    "logical_schedule": "logical_schedule",
    "logical_schedule_certificate": "logical_schedule_certificate",
    "official_evidence_certificate": "official_evidence_certificate",
    "program": "otgo_microcode_program",
    "program_contract": "program_contract",
    "program_disassembly": "microcode_disassembly",
    "resource_manifest": "resource_manifest",
    "source_contract": "source_contract",
    "weight": "official_layer0_wo_a_local_bf16",
}


class DeepSeekV4GroupedOutputExecutableBuildError(RuntimeError):
    """Raised when an official grouped-output package cannot be published."""


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _json(value: object) -> bytes:
    return canonical_json_bytes(value)


def _artifact_record(path: str, role: str, payload: bytes) -> dict[str, Any]:
    return {
        "path": path,
        "role": role,
        "sha256": _sha256(payload),
        "size_bytes": len(payload),
    }


def _topology_contract(world_size: int, rank: int) -> dict[str, Any]:
    mapping = topology_mapping(world_size, rank)
    return {
        "global_group_range": [
            mapping.global_group_start,
            mapping.global_group_stop,
        ],
        "global_row_range": [mapping.global_row_start, mapping.global_row_stop],
        "local_group_count": mapping.local_group_count,
        "rank": rank,
        "world_size": world_size,
    }


def _descriptor_schema(
    *,
    rank: int,
    shape_prefix: list[object],
) -> dict[str, Any]:
    return {
        "additionalProperties": False,
        "properties": {
            "dtype": {"const": "BF16"},
            "encoding": {"const": "bfloat16_little_endian"},
            "path": {"type": "string"},
            "rank": {"const": rank},
            "sha256": {"pattern": "^[0-9a-f]{64}$", "type": "string"},
            "shape": {
                "prefixItems": [
                    {"const": value} if type(value) is int else value
                    for value in shape_prefix
                ],
                "items": False,
                "maxItems": rank,
                "minItems": rank,
                "type": "array",
            },
            "size_bytes": {"minimum": 0, "type": "integer"},
        },
        "required": [
            "dtype",
            "encoding",
            "path",
            "rank",
            "sha256",
            "shape",
            "size_bytes",
        ],
        "type": "object",
    }


def _execution_request_schema(world_size: int, rank: int) -> dict[str, Any]:
    mapping = topology_mapping(world_size, rank)
    topology = _topology_contract(world_size, rank)
    return {
        "$id": (
            "https://opentallas.org/schemas/compiler/"
            f"deepseek_v4_grouped_output_execution_request_ws{world_size}_r{rank}.json"
        ),
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "additionalProperties": False,
        "properties": {
            "build_id": {"pattern": "^[0-9a-f]{64}$", "type": "string"},
            "input": _descriptor_schema(
                rank=4,
                shape_prefix=[
                    {"maximum": MAX_TOKEN_COUNT, "minimum": 1, "type": "integer"},
                    {"maximum": MAX_TOKEN_COUNT, "minimum": 1, "type": "integer"},
                    mapping.local_group_count * 8,
                    512,
                ],
            ),
            "input_binding": {
                "additionalProperties": False,
                "properties": {
                    "kind": {"const": "external_content_hash_binding_only"},
                    "producer_id": {
                        "pattern": "^[0-9a-f]{64}$",
                        "type": "string",
                    },
                    "producer_schema": {"type": "string"},
                    "source_byte_offset": {"minimum": 0, "type": "integer"},
                    "source_content_sha256": {
                        "pattern": "^[0-9a-f]{64}$",
                        "type": "string",
                    },
                },
                "required": [
                    "kind",
                    "producer_id",
                    "producer_schema",
                    "source_byte_offset",
                    "source_content_sha256",
                ],
                "type": "object",
            },
            "numeric_profile": {
                "const": GROUPED_OUTPUT_SERVICE_NUMERIC_PROFILE,
            },
            "program_sha256": {
                "pattern": "^[0-9a-f]{64}$",
                "type": "string",
            },
            "request_id": {"pattern": "^[0-9a-f]{64}$", "type": "string"},
            "schema": {"const": EXECUTION_REQUEST_SCHEMA},
            "selected_output_ranks": {
                "items": {
                    "maximum": OUTPUT_RANK_PER_GROUP - 1,
                    "minimum": 0,
                    "type": "integer",
                },
                "maxItems": OUTPUT_RANK_PER_GROUP,
                "minItems": 1,
                "type": "array",
                "uniqueItems": True,
            },
            "status": {"const": "ready"},
            "topology": {"const": topology},
        },
        "required": [
            "build_id",
            "input",
            "input_binding",
            "numeric_profile",
            "program_sha256",
            "request_id",
            "schema",
            "selected_output_ranks",
            "status",
            "topology",
        ],
        "title": "OpenTallas DeepSeek V4 grouped-output execution request",
        "type": "object",
    }


def _execution_result_schema(world_size: int, rank: int) -> dict[str, Any]:
    topology = _topology_contract(world_size, rank)
    return {
        "$id": (
            "https://opentallas.org/schemas/compiler/"
            f"deepseek_v4_grouped_output_execution_result_ws{world_size}_r{rank}.json"
        ),
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "additionalProperties": False,
        "properties": {
            "build_id": {"pattern": "^[0-9a-f]{64}$", "type": "string"},
            "complete_output": {"type": "boolean"},
            "counter_reconciliation": {"const": "exact"},
            "execution_scope": {
                "enum": [
                    "complete_grouped_output_projection",
                    "selected_output_rank_audit",
                ]
            },
            "logical_counters": {"type": "object"},
            "model_id": {"const": MODEL_ID},
            "numeric_profile": {
                "const": GROUPED_OUTPUT_SERVICE_NUMERIC_PROFILE,
            },
            "output_saturation_count": {"minimum": 0, "type": "integer"},
            "outputs": {
                "additionalProperties": False,
                "properties": {
                    "flattened": _descriptor_schema(
                        rank=3,
                        shape_prefix=[
                            {"maximum": MAX_TOKEN_COUNT, "minimum": 1, "type": "integer"},
                            {"maximum": MAX_TOKEN_COUNT, "minimum": 1, "type": "integer"},
                            {"minimum": 1, "type": "integer"},
                        ],
                    ),
                    "grouped": _descriptor_schema(
                        rank=4,
                        shape_prefix=[
                            {"maximum": MAX_TOKEN_COUNT, "minimum": 1, "type": "integer"},
                            {"maximum": MAX_TOKEN_COUNT, "minimum": 1, "type": "integer"},
                            {"minimum": 1, "type": "integer"},
                            {"minimum": 1, "type": "integer"},
                        ],
                    ),
                },
                "required": ["flattened", "grouped"],
                "type": "object",
            },
            "program_sha256": {
                "pattern": "^[0-9a-f]{64}$",
                "type": "string",
            },
            "request_id": {"pattern": "^[0-9a-f]{64}$", "type": "string"},
            "request_sha256": {
                "pattern": "^[0-9a-f]{64}$",
                "type": "string",
            },
            "resource_sha256": {
                "pattern": "^[0-9a-f]{64}$",
                "type": "string",
            },
            "result_id": {"pattern": "^[0-9a-f]{64}$", "type": "string"},
            "schema": {"const": EXECUTION_RESULT_SCHEMA},
            "selected_output_ranks": {
                "items": {"type": "integer"},
                "minItems": 1,
                "type": "array",
            },
            "status": {"const": "pass"},
            "token_count": {
                "maximum": MAX_TOKEN_COUNT,
                "minimum": MIN_TOKEN_COUNT,
                "type": "integer",
            },
            "topology": {"const": topology},
        },
        "required": [
            "build_id",
            "complete_output",
            "counter_reconciliation",
            "execution_scope",
            "logical_counters",
            "model_id",
            "numeric_profile",
            "output_saturation_count",
            "outputs",
            "program_sha256",
            "request_id",
            "request_sha256",
            "resource_sha256",
            "result_id",
            "schema",
            "selected_output_ranks",
            "status",
            "token_count",
            "topology",
        ],
        "title": "OpenTallas DeepSeek V4 grouped-output execution result",
        "type": "object",
    }


def _counter_contract(world_size: int) -> dict[str, Any]:
    counter_names = list(grouped_output_functional_counters(1, world_size, 1))
    body = {
        "counter_kind": "logical_semantic_accounting_only",
        "counter_names": counter_names,
        "numeric_profile": GROUPED_OUTPUT_SERVICE_NUMERIC_PROFILE,
        "physical_interpretation": None,
        "schema": COUNTER_CONTRACT_SCHEMA,
    }
    return {
        **body,
        "contract_id": _sha256(_json(body)),
    }


def _execution_contract(world_size: int, rank: int) -> dict[str, Any]:
    mapping = topology_mapping(world_size, rank)
    body = {
        "atomicity": {
            "abort": "publish no result directory",
            "commit": "atomically create one complete immutable result directory",
            "deployment_mutation": "forbidden",
            "request_mutation": "forbidden",
            "restart_replay": "verify the complete persisted result artifact closure",
        },
        "claim_boundary": list(CLAIM_BOUNDARY),
        "dimensions": {
            "head_dim": 512,
            "heads_per_group": 8,
            "local_group_count": mapping.local_group_count,
            "maximum_token_count": MAX_TOKEN_COUNT,
            "minimum_token_count": MIN_TOKEN_COUNT,
            "output_rank_per_group": OUTPUT_RANK_PER_GROUP,
        },
        "numeric_profile": GROUPED_OUTPUT_SERVICE_NUMERIC_PROFILE,
        "rank_selection": (
            "strictly increasing unique subset of 0..1023; complete only for exact 0..1023"
        ),
        "required_nonclaims": list(REQUIRED_NONCLAIMS),
        "schema": EXECUTION_CONTRACT_SCHEMA,
        "topology": _topology_contract(world_size, rank),
    }
    return {
        **body,
        "contract_id": _sha256(_json(body)),
    }


def _coverage(world_size: int, rank: int) -> dict[str, Any]:
    return {
        "covered": [
            "pinned_official_source_and_checkpoint_lock_identity",
            "independently_verified_canonical_wo_a_transform_application",
            "complete_local_wo_a_bf16_resource",
            "exact_otgo_microcode_decode",
            "deterministic_logical_schedule_and_certificate",
            "artifact_only_grouped_output_numeric_execution",
            "grouped_and_flattened_output_views",
            "atomic_immutable_result_publication_and_replay",
        ],
        "model_id": MODEL_ID,
        "not_covered": list(REQUIRED_NONCLAIMS),
        "numeric_profile": GROUPED_OUTPUT_SERVICE_NUMERIC_PROFILE,
        "schema": COVERAGE_SCHEMA,
        "topology": _topology_contract(world_size, rank),
    }


def _resource_manifest(
    world_size: int,
    rank: int,
    weight_payload: bytes,
) -> dict[str, Any]:
    spec = resource_contract(world_size, rank)[0]
    body = {
        "application_id": CANONICAL_APPLICATION_ID,
        "checkpoint_lock_id": CHECKPOINT_LOCK_ID,
        "resources": [
            {
                "canonical_application_id": spec.canonical_application_id,
                "dtype": spec.dtype,
                "encoding": "bfloat16_little_endian",
                "global_group_range": [
                    spec.global_group_start,
                    spec.global_group_stop,
                ],
                "global_row_range": [spec.global_row_start, spec.global_row_stop],
                "path": WEIGHT_PATH,
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
                "sha256": _sha256(weight_payload),
                "shape": list(spec.shape),
                "size_bytes": len(weight_payload),
            }
        ],
        "schema": RESOURCE_MANIFEST_SCHEMA,
        "source_contract_id": build_source_contract()["source_contract_id"],
        "status": "complete_official_local_wo_a_resource",
        "topology": _topology_contract(world_size, rank),
        "verification_id": CANONICAL_VERIFICATION_ID,
    }
    return {
        **body,
        "resource_manifest_id": _sha256(_json(body)),
    }


def _read_official_local_weight(
    application_root: Path,
    world_size: int,
    rank: int,
) -> bytes:
    specs = resource_contract(world_size, rank)
    verify_resource_contract(specs, world_size, rank)
    spec = specs[0]
    chunks: list[bytes] = []
    try:
        with SecureDirectory(
            Path(application_root),
            label="DeepSeek V4 canonical MP4 application",
        ) as root:
            held: dict[str, bytes] = {}
            assignment_hashes = {
                segment.path: next(
                    assignment.content_sha256
                    for assignment in CANONICAL_ASSIGNMENTS
                    if assignment.path == segment.path
                )
                for segment in spec.segments
            }
            for segment in spec.segments:
                payload = held.get(segment.path)
                if payload is None:
                    source = root.open_file(
                        segment.path,
                        label=f"canonical assignment {segment.path!r}",
                        exact_size=16_777_216,
                        maximum_size=16_777_216,
                    )
                    payload = source.read_bytes(
                        label=f"canonical assignment {segment.path!r}",
                        maximum_bytes=16_777_216,
                    )
                    if _sha256(payload) != assignment_hashes[segment.path]:
                        raise DeepSeekV4GroupedOutputExecutableBuildError(
                            f"canonical assignment {segment.path!r} hash differs"
                        )
                    held[segment.path] = payload
                stop = segment.byte_offset + segment.size_bytes
                chunk = payload[segment.byte_offset:stop]
                if len(chunk) != segment.size_bytes or _sha256(chunk) != (
                    segment.content_sha256
                ):
                    raise DeepSeekV4GroupedOutputExecutableBuildError(
                        f"canonical segment {segment.path!r} differs"
                    )
                chunks.append(chunk)
            root.verify()
    except SecureArtifactError as exc:
        raise DeepSeekV4GroupedOutputExecutableBuildError(
            f"cannot hold canonical wo_a assignments securely: {exc}"
        ) from exc
    payload = b"".join(chunks)
    if len(payload) != spec.size_bytes or _sha256(payload) != spec.content_sha256:
        raise DeepSeekV4GroupedOutputExecutableBuildError(
            "recomposed local wo_a resource differs from its topology identity"
        )
    for index, (code,) in enumerate(struct.iter_unpack("<H", payload)):
        if code & 0x7F80 == 0x7F80:
            raise DeepSeekV4GroupedOutputExecutableBuildError(
                f"canonical local wo_a contains nonfinite BF16 at element {index}"
            )
    return payload


def build_deepseek_v4_grouped_output_executable_deployment(
    snapshot_root: Path,
    checkpoint_lock_path: Path,
    application_root: Path,
    output_dir: Path,
    *,
    world_size: int,
    rank: int,
) -> dict[str, Any]:
    """Build, create-once publish, and independently verify one package."""

    mapping = topology_mapping(world_size, rank)
    if world_size not in TENSOR_PARALLEL_WORLD_SIZES:  # pragma: no cover
        raise DeepSeekV4GroupedOutputExecutableBuildError("unsupported topology")
    try:
        official_evidence = verify_deepseek_v4_grouped_output_official_evidence(
            Path(snapshot_root),
            Path(checkpoint_lock_path),
            Path(application_root),
        )
    except (OSError, ValueError) as exc:
        raise DeepSeekV4GroupedOutputExecutableBuildError(
            f"official grouped-output evidence failed: {exc}"
        ) from exc

    weight_payload = _read_official_local_weight(
        Path(application_root),
        world_size,
        rank,
    )
    program = assemble(world_size, rank)
    verify(program, world_size, rank)
    program_payload = encode(program, world_size, rank)
    program_contract = build_program_contract(world_size, rank)
    verify_program_contract(program_contract, world_size, rank)
    source_contract = build_source_contract()
    verify_source_contract(source_contract)
    schedule = build_deepseek_v4_grouped_output_logical_schedule(world_size, rank)
    schedule_certificate = verify_deepseek_v4_grouped_output_logical_schedule(schedule)
    verify_deepseek_v4_grouped_output_logical_schedule_certificate(
        schedule_certificate,
        schedule,
    )

    payloads: dict[str, bytes] = {
        ENTRYPOINT["counter_contract"]: _json(_counter_contract(world_size)),
        ENTRYPOINT["coverage"]: _json(_coverage(world_size, rank)),
        ENTRYPOINT["execution_contract"]: _json(
            _execution_contract(world_size, rank)
        ),
        ENTRYPOINT["execution_request_schema"]: _json(
            _execution_request_schema(world_size, rank)
        ),
        ENTRYPOINT["execution_result_schema"]: _json(
            _execution_result_schema(world_size, rank)
        ),
        ENTRYPOINT["logical_schedule"]: _json(schedule),
        ENTRYPOINT["logical_schedule_certificate"]: _json(schedule_certificate),
        ENTRYPOINT["official_evidence_certificate"]: _json(official_evidence),
        ENTRYPOINT["program"]: program_payload,
        ENTRYPOINT["program_contract"]: _json(program_contract),
        ENTRYPOINT["program_disassembly"]: disassemble(
            program,
            world_size,
            rank,
        ).encode("utf-8"),
        ENTRYPOINT["resource_manifest"]: _json(
            _resource_manifest(world_size, rank, weight_payload)
        ),
        ENTRYPOINT["source_contract"]: _json(source_contract),
        ENTRYPOINT["weight"]: weight_payload,
    }
    artifacts = [
        _artifact_record(ENTRYPOINT[key], _ROLE_BY_KEY[key], payloads[ENTRYPOINT[key]])
        for key in sorted(ENTRYPOINT)
    ]
    core = {
        "artifacts": artifacts,
        "claim_boundary": list(CLAIM_BOUNDARY),
        "compiler": {"name": COMPILER_NAME, "version": COMPILER_VERSION},
        "entrypoint": dict(ENTRYPOINT),
        "evidence": {
            "application_id": CANONICAL_APPLICATION_ID,
            "checkpoint_lock_id": CHECKPOINT_LOCK_ID,
            "official_evidence_certificate_id": official_evidence["certificate_id"],
            "source_contract_id": source_contract["source_contract_id"],
            "verification_id": CANONICAL_VERIFICATION_ID,
        },
        "model_id": MODEL_ID,
        "numeric_profile": GROUPED_OUTPUT_SERVICE_NUMERIC_PROFILE,
        "repository": MODEL_REPOSITORY,
        "revision": MODEL_REVISION,
        "schema": DEPLOYMENT_SCHEMA,
        "status": DEPLOYMENT_STATUS,
        "topology": _topology_contract(world_size, rank),
    }
    manifest = {
        **core,
        "build_id": _sha256(_json(core)),
    }
    payloads[MANIFEST_FILENAME] = _json(manifest)
    directories = sorted(
        {
            parent.as_posix()
            for path in payloads
            for parent in Path(path).parents
            if parent != Path(".")
        }
    )
    try:
        publish_payload_tree(
            Path(output_dir),
            payloads=payloads,
            directories=directories,
            label=(
                "DeepSeek V4 grouped-output executable deployment "
                f"ws{mapping.world_size}-rank{mapping.rank}"
            ),
            maximum_depth=4,
            maximum_entries=64,
        )
        return verify_deepseek_v4_grouped_output_executable_deployment(
            Path(output_dir)
        )
    except (SecureArtifactError, OSError, ValueError) as exc:
        raise DeepSeekV4GroupedOutputExecutableBuildError(
            f"cannot publish verified grouped-output deployment: {exc}"
        ) from exc


__all__ = [
    "CLAIM_BOUNDARY",
    "COMPILER_NAME",
    "COMPILER_VERSION",
    "COUNTER_CONTRACT_SCHEMA",
    "COVERAGE_SCHEMA",
    "DEPLOYMENT_SCHEMA",
    "DEPLOYMENT_STATUS",
    "ENTRYPOINT",
    "EXECUTION_CONTRACT_SCHEMA",
    "EXECUTION_REQUEST_SCHEMA",
    "EXECUTION_RESULT_SCHEMA",
    "MANIFEST_FILENAME",
    "RESOURCE_MANIFEST_SCHEMA",
    "REQUIRED_NONCLAIMS",
    "WEIGHT_PATH",
    "DeepSeekV4GroupedOutputExecutableBuildError",
    "build_deepseek_v4_grouped_output_executable_deployment",
]
