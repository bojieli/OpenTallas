"""Independent verifier for grouped-output executable deployments.

The checker holds the complete deployment tree, authenticates every file,
reconstructs the topology-specific program, source, schedule, certificate,
resource, execution, interface, and evidence contracts independently, checks
the exact official BF16 resource bytes, and closes the tree before returning
a verification report.  It performs no grouped-output activation execution.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
import struct
from typing import Any, NoReturn

from compiler.checking.deepseek_v4_grouped_output import (
    FROZEN_MAPPING_HASHES,
    verify_deepseek_v4_grouped_output_logical_schedule,
    verify_deepseek_v4_grouped_output_logical_schedule_certificate,
)
from compiler.microcode.deepseek_v4_grouped_output import (
    CANONICAL_APPLICATION_ID,
    CANONICAL_VERIFICATION_ID,
    CHECKPOINT_LOCK_ID,
    MODEL_ID,
    MODEL_REPOSITORY,
    MODEL_REVISION,
    assemble,
    build_program_contract,
    build_source_contract,
    decode,
    disassemble,
    encode,
    resource_contract,
    topology_mapping,
    verify,
    verify_program_contract,
    verify_resource_contract,
    verify_source_contract,
)
from runtime.service_engine.grouped_output_numeric import (
    GROUPED_OUTPUT_SERVICE_NUMERIC_PROFILE,
    grouped_output_functional_counters,
)
from runtime.service_engine.secure_artifacts import (
    SecureArtifactError,
    SecureDirectory,
    canonical_json_bytes,
    parse_canonical_json,
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
OFFICIAL_EVIDENCE_CERTIFICATE_SCHEMA = (
    "opentallas.deepseek_v4_grouped_output_official_evidence_certificate.v1"
)
COMPILER_NAME = "opentallas-deepseek-v4-grouped-output-executable-packager"
COMPILER_VERSION = "0.1.0"
MANIFEST_FILENAME = "deployment_manifest.json"
WEIGHT_PATH = "resources/layer0_wo_a_local.bf16le"
OFFICIAL_EVIDENCE_CERTIFICATE_ID = (
    "57d86552d860aadc779bcfc69a2bffe4fbfdb1908159054661646e1192e02838"
)

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
ROLE_BY_KEY = {
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


class DeepSeekV4GroupedOutputExecutableCheckError(RuntimeError):
    """Raised when a grouped-output deployment fails closed."""


def _poison(message: str, cause: BaseException | None = None) -> NoReturn:
    if cause is None:
        raise DeepSeekV4GroupedOutputExecutableCheckError(message)
    raise DeepSeekV4GroupedOutputExecutableCheckError(message) from cause


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _json(payload: bytes, label: str) -> dict[str, Any]:
    value = parse_canonical_json(payload, label=label, maximum_bytes=2 * 1024 * 1024)
    if type(value) is not dict:
        _poison(f"{label} is not a JSON object")
    return value


def _equal(left: object, right: object) -> bool:
    try:
        return canonical_json_bytes(left) == canonical_json_bytes(right)
    except SecureArtifactError:
        return False


def _exact(value: object, keys: set[str], label: str) -> dict[str, Any]:
    if type(value) is not dict:
        _poison(f"{label} is not an exact object")
    observed = set(value)
    if observed != keys:
        _poison(
            f"{label} fields differ: missing={sorted(keys - observed)}, "
            f"unknown={sorted(observed - keys)}"
        )
    return value


def _digest(value: object, label: str) -> str:
    if (
        type(value) is not str
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        _poison(f"{label} is not a lowercase SHA-256")
    return value


def _artifact_record(path: str, role: str, payload: bytes) -> dict[str, Any]:
    return {
        "path": path,
        "role": role,
        "sha256": _sha256(payload),
        "size_bytes": len(payload),
    }


def _topology(world_size: int, rank: int) -> dict[str, Any]:
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


def _descriptor_schema(*, rank: int, shape_prefix: list[object]) -> dict[str, Any]:
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


def _request_schema(world_size: int, rank: int) -> dict[str, Any]:
    local_groups = 8 // world_size
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
                    {"maximum": 4, "minimum": 1, "type": "integer"},
                    {"maximum": 4, "minimum": 1, "type": "integer"},
                    local_groups * 8,
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
            "numeric_profile": {"const": GROUPED_OUTPUT_SERVICE_NUMERIC_PROFILE},
            "program_sha256": {
                "pattern": "^[0-9a-f]{64}$",
                "type": "string",
            },
            "request_id": {"pattern": "^[0-9a-f]{64}$", "type": "string"},
            "schema": {"const": EXECUTION_REQUEST_SCHEMA},
            "selected_output_ranks": {
                "items": {"maximum": 1023, "minimum": 0, "type": "integer"},
                "maxItems": 1024,
                "minItems": 1,
                "type": "array",
                "uniqueItems": True,
            },
            "status": {"const": "ready"},
            "topology": {"const": _topology(world_size, rank)},
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


def _result_schema(world_size: int, rank: int) -> dict[str, Any]:
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
            "numeric_profile": {"const": GROUPED_OUTPUT_SERVICE_NUMERIC_PROFILE},
            "output_saturation_count": {"minimum": 0, "type": "integer"},
            "outputs": {
                "additionalProperties": False,
                "properties": {
                    "flattened": _descriptor_schema(
                        rank=3,
                        shape_prefix=[
                            {"maximum": 4, "minimum": 1, "type": "integer"},
                            {"maximum": 4, "minimum": 1, "type": "integer"},
                            {"minimum": 1, "type": "integer"},
                        ],
                    ),
                    "grouped": _descriptor_schema(
                        rank=4,
                        shape_prefix=[
                            {"maximum": 4, "minimum": 1, "type": "integer"},
                            {"maximum": 4, "minimum": 1, "type": "integer"},
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
            "token_count": {"maximum": 4, "minimum": 1, "type": "integer"},
            "topology": {"const": _topology(world_size, rank)},
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
    body = {
        "counter_kind": "logical_semantic_accounting_only",
        "counter_names": list(grouped_output_functional_counters(1, world_size, 1)),
        "numeric_profile": GROUPED_OUTPUT_SERVICE_NUMERIC_PROFILE,
        "physical_interpretation": None,
        "schema": COUNTER_CONTRACT_SCHEMA,
    }
    return {**body, "contract_id": _sha256(canonical_json_bytes(body))}


def _execution_contract(world_size: int, rank: int) -> dict[str, Any]:
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
            "local_group_count": 8 // world_size,
            "maximum_token_count": 4,
            "minimum_token_count": 1,
            "output_rank_per_group": 1024,
        },
        "numeric_profile": GROUPED_OUTPUT_SERVICE_NUMERIC_PROFILE,
        "rank_selection": (
            "strictly increasing unique subset of 0..1023; complete only for exact 0..1023"
        ),
        "required_nonclaims": list(REQUIRED_NONCLAIMS),
        "schema": EXECUTION_CONTRACT_SCHEMA,
        "topology": _topology(world_size, rank),
    }
    return {**body, "contract_id": _sha256(canonical_json_bytes(body))}


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
        "topology": _topology(world_size, rank),
    }


def _resource_manifest(
    world_size: int,
    rank: int,
    payload: bytes,
) -> dict[str, Any]:
    spec = resource_contract(world_size, rank)[0]
    body = {
        "application_id": CANONICAL_APPLICATION_ID,
        "checkpoint_lock_id": CHECKPOINT_LOCK_ID,
        "resources": [
            {
                "canonical_application_id": spec.canonical_application_id,
                "dtype": "BF16",
                "encoding": "bfloat16_little_endian",
                "global_group_range": [
                    spec.global_group_start,
                    spec.global_group_stop,
                ],
                "global_row_range": [spec.global_row_start, spec.global_row_stop],
                "path": WEIGHT_PATH,
                "resource_id": 0,
                "resource_name": "LAYER0_WO_A_LOCAL_BF16",
                "role": "layers.0.attn.wo_a.weight.local",
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
                "sha256": _sha256(payload),
                "shape": list(spec.shape),
                "size_bytes": len(payload),
            }
        ],
        "schema": RESOURCE_MANIFEST_SCHEMA,
        "source_contract_id": build_source_contract()["source_contract_id"],
        "status": "complete_official_local_wo_a_resource",
        "topology": _topology(world_size, rank),
        "verification_id": CANONICAL_VERIFICATION_ID,
    }
    return {**body, "resource_manifest_id": _sha256(canonical_json_bytes(body))}


def _verify_official_certificate(value: object) -> None:
    certificate = _exact(
        value,
        {
            "application_id",
            "application_sha256",
            "certificate_id",
            "checkpoint_lock_id",
            "checkpoint_lock_sha256",
            "checks",
            "claim_boundary",
            "mapping_payload_sha256",
            "repository",
            "required_nonclaims",
            "revision",
            "schema",
            "source_contract_id",
            "status",
            "verification_id",
            "verification_sha256",
        },
        "official evidence certificate",
    )
    body = {key: certificate[key] for key in certificate if key != "certificate_id"}
    expected_mappings = {
        f"ws{world_size}-rank{rank}": FROZEN_MAPPING_HASHES[(world_size, rank)]
        for world_size in (1, 2, 4, 8)
        for rank in range(world_size)
    }
    checks = certificate.get("checks")
    if (
        certificate.get("schema") != OFFICIAL_EVIDENCE_CERTIFICATE_SCHEMA
        or certificate.get("status") != "pass"
        or certificate.get("certificate_id") != OFFICIAL_EVIDENCE_CERTIFICATE_ID
        or _sha256(canonical_json_bytes(body)) != OFFICIAL_EVIDENCE_CERTIFICATE_ID
        or certificate.get("application_id") != CANONICAL_APPLICATION_ID
        or certificate.get("checkpoint_lock_id") != CHECKPOINT_LOCK_ID
        or certificate.get("verification_id") != CANONICAL_VERIFICATION_ID
        or certificate.get("repository") != MODEL_REPOSITORY
        or certificate.get("revision") != MODEL_REVISION
        or certificate.get("source_contract_id")
        != build_source_contract()["source_contract_id"]
        or not _equal(certificate.get("mapping_payload_sha256"), expected_mappings)
        or type(checks) is not dict
        or not checks
        or any(value is not True for value in checks.values())
    ):
        _poison("official grouped-output evidence certificate differs")


def verify_deepseek_v4_grouped_output_executable_deployment(
    deployment_dir: Path,
) -> dict[str, Any]:
    """Verify exact package closure and return its immutable identities."""

    try:
        with SecureDirectory(
            Path(deployment_dir),
            label="DeepSeek V4 grouped-output executable deployment",
        ) as root:
            manifest_source = root.open_file(
                MANIFEST_FILENAME,
                label="grouped-output deployment manifest",
                maximum_size=512 * 1024,
            )
            manifest_payload = manifest_source.read_bytes(
                label="grouped-output deployment manifest",
                maximum_bytes=512 * 1024,
            )
            manifest = _json(manifest_payload, "grouped-output deployment manifest")
            _exact(
                manifest,
                {
                    "artifacts",
                    "build_id",
                    "claim_boundary",
                    "compiler",
                    "entrypoint",
                    "evidence",
                    "model_id",
                    "numeric_profile",
                    "repository",
                    "revision",
                    "schema",
                    "status",
                    "topology",
                },
                "grouped-output deployment manifest",
            )
            topology = _exact(
                manifest.get("topology"),
                {
                    "global_group_range",
                    "global_row_range",
                    "local_group_count",
                    "rank",
                    "world_size",
                },
                "deployment topology",
            )
            world_size = topology.get("world_size")
            rank = topology.get("rank")
            if type(world_size) is not int or type(rank) is not int:
                _poison("deployment topology values are not exact integers")
            mapping = topology_mapping(world_size, rank)
            if not _equal(topology, _topology(world_size, rank)):
                _poison("deployment topology differs from exact ownership")
            fixed = {
                "claim_boundary": CLAIM_BOUNDARY,
                "compiler": {"name": COMPILER_NAME, "version": COMPILER_VERSION},
                "entrypoint": ENTRYPOINT,
                "evidence": {
                    "application_id": CANONICAL_APPLICATION_ID,
                    "checkpoint_lock_id": CHECKPOINT_LOCK_ID,
                    "official_evidence_certificate_id": (
                        OFFICIAL_EVIDENCE_CERTIFICATE_ID
                    ),
                    "source_contract_id": build_source_contract()[
                        "source_contract_id"
                    ],
                    "verification_id": CANONICAL_VERIFICATION_ID,
                },
                "model_id": MODEL_ID,
                "numeric_profile": GROUPED_OUTPUT_SERVICE_NUMERIC_PROFILE,
                "repository": MODEL_REPOSITORY,
                "revision": MODEL_REVISION,
                "schema": DEPLOYMENT_SCHEMA,
                "status": DEPLOYMENT_STATUS,
            }
            for key, expected in fixed.items():
                if not _equal(manifest.get(key), expected):
                    _poison(f"deployment {key} differs")

            expected_files = {MANIFEST_FILENAME, *ENTRYPOINT.values()}
            expected_directories = {
                parent.as_posix()
                for path in expected_files
                for parent in Path(path).parents
                if parent != Path(".")
            }
            files, directories = root.enumerate_tree(
                maximum_depth=4,
                maximum_entries=64,
            )
            if files != expected_files or directories != expected_directories:
                _poison("deployment tree closure differs")

            payloads: dict[str, bytes] = {}
            for path in sorted(ENTRYPOINT.values()):
                exact_size = mapping.size_bytes if path == WEIGHT_PATH else None
                maximum = mapping.size_bytes if exact_size is not None else 2 * 1024 * 1024
                source = root.open_file(
                    path,
                    label=f"grouped-output artifact {path!r}",
                    minimum_size=0,
                    maximum_size=maximum,
                    exact_size=exact_size,
                )
                payloads[path] = source.read_bytes(
                    label=f"grouped-output artifact {path!r}",
                    maximum_bytes=max(1, maximum),
                )

            artifacts = manifest.get("artifacts")
            expected_artifacts = [
                _artifact_record(
                    ENTRYPOINT[key],
                    ROLE_BY_KEY[key],
                    payloads[ENTRYPOINT[key]],
                )
                for key in sorted(ENTRYPOINT)
            ]
            if not _equal(artifacts, expected_artifacts):
                _poison("deployment artifact table differs from exact files")
            core = {key: manifest[key] for key in manifest if key != "build_id"}
            build_id = _digest(manifest.get("build_id"), "deployment build_id")
            if _sha256(canonical_json_bytes(core)) != build_id:
                _poison("deployment build_id differs from canonical core")

            weight = payloads[WEIGHT_PATH]
            if _sha256(weight) != FROZEN_MAPPING_HASHES[(world_size, rank)]:
                _poison("packaged local wo_a bytes differ from official mapping")
            for index, (code,) in enumerate(struct.iter_unpack("<H", weight)):
                if code & 0x7F80 == 0x7F80:
                    _poison(f"packaged wo_a has nonfinite BF16 at element {index}")
            specs = resource_contract(world_size, rank)
            verify_resource_contract(specs, world_size, rank)
            expected_resource_manifest = _resource_manifest(
                world_size,
                rank,
                weight,
            )
            resource_manifest = _json(
                payloads[ENTRYPOINT["resource_manifest"]],
                "grouped-output resource manifest",
            )
            if not _equal(resource_manifest, expected_resource_manifest):
                _poison("packaged resource manifest differs")

            program = assemble(world_size, rank)
            verify(program, world_size, rank)
            program_payload = payloads[ENTRYPOINT["program"]]
            if decode(program_payload) != program or encode(
                program,
                world_size,
                rank,
            ) != program_payload:
                _poison("packaged OTGO program differs or fails roundtrip")
            if payloads[ENTRYPOINT["program_disassembly"]] != disassemble(
                program,
                world_size,
                rank,
            ).encode("utf-8"):
                _poison("packaged OTGO disassembly differs")
            program_contract = _json(
                payloads[ENTRYPOINT["program_contract"]],
                "grouped-output program contract",
            )
            verify_program_contract(program_contract, world_size, rank)
            if not _equal(
                program_contract,
                build_program_contract(world_size, rank),
            ):
                _poison("packaged program contract differs")
            source_contract = _json(
                payloads[ENTRYPOINT["source_contract"]],
                "grouped-output source contract",
            )
            verify_source_contract(source_contract)
            if not _equal(source_contract, build_source_contract()):
                _poison("packaged source contract differs")

            schedule = _json(
                payloads[ENTRYPOINT["logical_schedule"]],
                "grouped-output logical schedule",
            )
            certificate = _json(
                payloads[ENTRYPOINT["logical_schedule_certificate"]],
                "grouped-output logical schedule certificate",
            )
            fresh_certificate = verify_deepseek_v4_grouped_output_logical_schedule(
                schedule
            )
            verify_deepseek_v4_grouped_output_logical_schedule_certificate(
                certificate,
                schedule,
            )
            if not _equal(certificate, fresh_certificate):
                _poison("packaged logical schedule certificate differs")
            official_certificate = _json(
                payloads[ENTRYPOINT["official_evidence_certificate"]],
                "grouped-output official evidence certificate",
            )
            _verify_official_certificate(official_certificate)

            expected_json = {
                ENTRYPOINT["counter_contract"]: _counter_contract(world_size),
                ENTRYPOINT["coverage"]: _coverage(world_size, rank),
                ENTRYPOINT["execution_contract"]: _execution_contract(
                    world_size,
                    rank,
                ),
                ENTRYPOINT["execution_request_schema"]: _request_schema(
                    world_size,
                    rank,
                ),
                ENTRYPOINT["execution_result_schema"]: _result_schema(
                    world_size,
                    rank,
                ),
            }
            for path, expected in expected_json.items():
                observed = _json(payloads[path], f"grouped-output artifact {path!r}")
                if not _equal(observed, expected):
                    _poison(f"grouped-output artifact {path!r} differs")
            root.verify()
    except DeepSeekV4GroupedOutputExecutableCheckError:
        raise
    except Exception as exc:
        _poison(f"grouped-output deployment verification failed: {exc}", exc)

    return {
        "build_id": build_id,
        "evidence_eligible": True,
        "official_evidence_certificate_id": OFFICIAL_EVIDENCE_CERTIFICATE_ID,
        "program_sha256": _sha256(program_payload),
        "resource_manifest_id": resource_manifest["resource_manifest_id"],
        "resource_sha256": _sha256(weight),
        "schedule_id": schedule["schedule_id"],
        "status": "verified_official_artifact_only_grouped_output_package",
        "topology": _topology(world_size, rank),
    }


__all__ = [
    "DeepSeekV4GroupedOutputExecutableCheckError",
    "OFFICIAL_EVIDENCE_CERTIFICATE_ID",
    "verify_deepseek_v4_grouped_output_executable_deployment",
]
