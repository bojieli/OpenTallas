"""Independent verifier for the DeepSeek V4 compressor executable package.

This checker does not import the package builder.  It independently rebuilds
the microcode contract, logical schedule, source binding, interface contracts,
and full-width known answer from the packaged APE bytes.
"""

from __future__ import annotations

from dataclasses import asdict, fields
import hashlib
from pathlib import Path
import struct
from typing import Any

from compiler.microcode.deepseek_v4_compressor import (
    APE_BYTES,
    APE_SHAPE,
    HEAD_DIM,
    MODEL_ID,
    PROGRAM_BYTES,
    PROGRAM_SHA256,
    PROJECTED_WIDTH,
    RATIO,
    decode,
    disassemble,
    encode,
    verify,
    verify_program_contract,
)
from compiler.scheduling.deepseek_v4_compressor import (
    verify_logical_schedule,
    verify_logical_schedule_certificate,
)
from runtime.reference.compressed_kv import (
    CompressedKVValidViewCounters,
    CompressedKVWriteCounters,
    compressed_kv_valid_view_bf16,
    compressed_kv_write_bf16,
    zero_compressed_kv_state_bf16,
)
from runtime.reference.compression_pool import (
    CompressionPoolCounters,
    compress_pool_f32,
)
from runtime.reference.compression_state import (
    CompressionStateCounters,
    compress_state_update_f32,
    zero_compression_state_f32,
)
from runtime.reference.conversion import (
    Binary32ToBF16Counters,
    binary32_tensor_to_bf16_rne,
)
from runtime.reference.formats import encode_binary32_rne
from runtime.service_engine.secure_artifacts import (
    SecureArtifactError,
    SecureDirectory,
    canonical_json_bytes,
    parse_canonical_json,
)


DEPLOYMENT_SCHEMA = "opentallas.deepseek_v4_compressor_executable.v1"
COUNTER_CONTRACT_SCHEMA = "opentallas.deepseek_v4_compressor_counter_contract.v1"
EXECUTION_CONTRACT_SCHEMA = "opentallas.deepseek_v4_compressor_execution_contract.v1"
KNOWN_ANSWER_SCHEMA = "opentallas.deepseek_v4_compressor_known_answer.v1"
COVERAGE_SCHEMA = "opentallas.deepseek_v4_compressor_coverage.v1"
SOURCE_BINDING_SCHEMA = "opentallas.deepseek_v4_compressor_source_binding.v2"
DEPLOYMENT_STATUS = "post_projection_functional_slice_logical_schedule_only"
COMPILER_NAME = "opentallas-deepseek-v4-compressor-executable-packager"
COMPILER_VERSION = "0.1.0"
OFFICIAL_APE_SHA256 = "f93afef4a88371262663f89f026a48b79f7187bd9d6498742c1db2860ae73554"
OFFICIAL_APPLICATION_ID = (
    "0f0f5177460c599059c971cbfd43e4299d6537f0cedb6055a83b77ecb52e16cb"
)
OFFICIAL_VERIFICATION_ID = (
    "b20ac53d48714c2328470b45f44b06aed11bed4c6dc7ef48f27185c5ba813f28"
)
OFFICIAL_TENSOR_NAME = "layers.2.attn.compressor.ape"
OFFICIAL_TENSOR_PATH = "ranks/rank-000/layers.2.attn.compressor.ape.bin"
INITIAL_BATCH_CAPACITY = 4
INITIAL_CACHE_CAPACITY = 8
MAX_REQUEST_SEQUENCE = 8
KNOWN_SESSION_ID = hashlib.sha256(
    b"opentallas:deepseek-v4:compressor-executable:known-answer:lane-0"
).hexdigest()

CLAIM_BOUNDARY = [
    "Executes a generated post-projection ratio-four compressor harness at official 1,024-value projected width using one complete checkpoint-derived layer-2 APE payload.",
    "The request supplies projected FP32 KV and score tensors; learned wkv and wgate projection weights and activations are outside this slice.",
    "The packaged APE-cancellation known answer is a controlled operator-harness stimulus, not a checkpoint-derived activation, and is never model-execution evidence.",
    "The direct post-pool FP32-to-BF16 value is used as this harness's transactional compressed-cache payload; official RMSNorm, RoPE, and activation QDQ between those boundaries are not implemented here.",
    "State versions are immutable, hash-bound artifact packages; failed execution or publication leaves the prior package unchanged, and successful result publication is restart-persistent at the package boundary.",
    "All counters are logical values, bytes, arithmetic operations, metadata fields, and commit events; none are physical memory transactions, cycles, bandwidth, latency, throughput, energy, area, routing, or PPA.",
    "This package establishes no complete attention block, transformer block, full-model result, ROM/GPU comparison, or wafer-scale performance result.",
]

ENTRYPOINT = {
    "ape": "parameters/layers.2.attn.compressor.ape.f32le",
    "counter_contract": "contracts/counter_contract.json",
    "coverage": "evidence/coverage.json",
    "execution_contract": "contracts/execution_contract.json",
    "known_answer": "evidence/known_answer.json",
    "logical_schedule": "schedule/logical_schedule.json",
    "logical_schedule_certificate": "schedule/logical_schedule_certificate.json",
    "program": "program/compressor.bin",
    "program_contract": "program/program_contract.json",
    "program_disassembly": "program/compressor.disassembly.txt",
    "source_binding": "evidence/source_binding.json",
}

ROLE_BY_KEY = {
    "counter_contract": "counter_contract",
    "coverage": "execution_coverage",
    "execution_contract": "execution_contract",
    "known_answer": "known_answer",
    "logical_schedule": "logical_schedule",
    "logical_schedule_certificate": "logical_schedule_certificate",
    "program": "microcode_program",
    "program_contract": "program_contract",
    "program_disassembly": "microcode_disassembly",
    "source_binding": "source_binding",
}


class DeepSeekV4CompressorExecutableCheckError(RuntimeError):
    """Raised when a compressor deployment fails closed verification."""


def _poison(message: str, cause: BaseException | None = None) -> None:
    if cause is None:
        raise DeepSeekV4CompressorExecutableCheckError(message)
    raise DeepSeekV4CompressorExecutableCheckError(message) from cause


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _digest(value: object, label: str) -> str:
    if (
        type(value) is not str
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        _poison(f"{label} is not a canonical lowercase SHA-256")
    return value


def _exact_dict(value: object, keys: set[str], label: str) -> dict[str, Any]:
    if type(value) is not dict:
        _poison(f"{label} must be an exact object")
    if set(value) != keys:
        _poison(
            f"{label} fields differ: missing={sorted(keys - set(value))}, "
            f"unknown={sorted(set(value) - keys)}"
        )
    return value


def _json(source: bytes, label: str) -> dict[str, Any]:
    try:
        value = parse_canonical_json(source, label=label, maximum_bytes=2 * 1024 * 1024)
    except SecureArtifactError as exc:
        _poison(str(exc), exc)
    if type(value) is not dict:
        _poison(f"{label} must contain an object")
    return value


def _f32_payload(value: object) -> bytes:
    output = bytearray()

    def visit(item: object) -> None:
        if type(item) is int:
            output.extend(struct.pack("<I", item))
        elif type(item) in {list, tuple}:
            for child in item:
                visit(child)
        else:
            _poison("known-answer F32 result is not an integer tensor")

    visit(value)
    return bytes(output)


def _bf16_payload(value: object) -> bytes:
    output = bytearray()

    def visit(item: object) -> None:
        if type(item) is int:
            output.extend(struct.pack("<H", item))
        elif type(item) in {list, tuple}:
            for child in item:
                visit(child)
        else:
            _poison("known-answer BF16 result is not an integer tensor")

    visit(value)
    return bytes(output)


def _ape_codes(payload: bytes, *, source_kind: str) -> tuple[tuple[int, ...], ...]:
    if len(payload) != APE_BYTES:
        _poison(f"APE payload has {len(payload)} bytes, expected {APE_BYTES}")
    digest = _sha256(payload)
    if source_kind == "official" and digest != OFFICIAL_APE_SHA256:
        _poison("official APE identity differs from the canonical tensor")
    flat = tuple(code for (code,) in struct.iter_unpack("<I", payload))
    for index, code in enumerate(flat):
        if code & 0x7F800000 == 0x7F800000:
            _poison(f"APE contains nonfinite binary32 at element {index}")
    return tuple(
        tuple(flat[row * PROJECTED_WIDTH : (row + 1) * PROJECTED_WIDTH])
        for row in range(RATIO)
    )


def _known_inputs(ape: tuple[tuple[int, ...], ...]) -> tuple[tuple, tuple]:
    zero = encode_binary32_rne(0)
    kv_rows: list[tuple[int, ...]] = []
    score_rows: list[tuple[int, ...]] = []
    for phase in range(RATIO):
        value = encode_binary32_rne(phase + 1)
        kv_rows.append((zero,) * HEAD_DIM + (value,) * HEAD_DIM)
        score_rows.append(tuple(code ^ 0x80000000 for code in ape[phase]))
    return (tuple(kv_rows),), (tuple(score_rows),)


def _expected_known_answer(ape: tuple[tuple[int, ...], ...]) -> dict[str, Any]:
    projected_kv, projected_scores = _known_inputs(ape)
    raw = zero_compression_state_f32(
        ratio=RATIO,
        batch_capacity=INITIAL_BATCH_CAPACITY,
        head_dim=HEAD_DIM,
    )
    compressed = zero_compressed_kv_state_bf16(
        ratio=RATIO,
        cache_capacity=INITIAL_CACHE_CAPACITY,
        kv_head_count=1,
        kv_value_width=HEAD_DIM,
        batch_capacity=INITIAL_BATCH_CAPACITY,
    )
    state_result = compress_state_update_f32(
        raw,
        projected_kv,
        projected_scores,
        ape,
        session_ids=(KNOWN_SESSION_ID,),
        start_pos=0,
    )
    if state_result.pool_inputs is None:
        _poison("independent known answer did not form a pool group")
    pool = compress_pool_f32(
        state_result.pool_inputs.kv_f32_codes,
        state_result.pool_inputs.score_f32_codes,
        ratio=RATIO,
    )
    conversion = binary32_tensor_to_bf16_rne(pool.pooled_f32_codes)
    cache_rows = tuple(
        tuple((row,) for row in sequence) for sequence in conversion.bf16_codes
    )
    write = compressed_kv_write_bf16(
        compressed,
        cache_rows,
        active_session_ids=(KNOWN_SESSION_ID,),
        start_pos=0,
        sequence_length=RATIO,
    )
    view = compressed_kv_valid_view_bf16(
        write.state,
        active_session_ids=(KNOWN_SESSION_ID,),
    )
    if any(
        code != 0x40200000
        for sequence in pool.pooled_f32_codes
        for row in sequence
        for code in row
    ):
        _poison("independent known-answer pool differs from exact 2.5")
    if any(
        code != 0x4020
        for sequence in conversion.bf16_codes
        for row in sequence
        for code in row
    ):
        _poison("independent known-answer conversion differs from exact BF16 2.5")
    return {
        "counters": {
            "compressed_kv_commit": asdict(write.counters),
            "conversion": asdict(conversion.counters),
            "pool": asdict(pool.counters),
            "raw_state_prepare": asdict(state_result.counters),
            "valid_prefix_view": asdict(view.counters),
        },
        "expected": {
            "completed_rows_per_batch": 1,
            "converted_bf16_code": "0x4020",
            "converted_bf16_sha256": _sha256(_bf16_payload(conversion.bf16_codes)),
            "pooled_binary32_code": "0x40200000",
            "pooled_f32_sha256": _sha256(_f32_payload(pool.pooled_f32_codes)),
            "valid_prefix_lengths": [1],
            "valid_view_bf16_sha256": _sha256(_bf16_payload(view.bf16_codes)),
        },
        "input_generator": {
            "batch_size": 1,
            "kv_current_half_binary32_values": [1, 2, 3, 4],
            "kv_previous_half_binary32_value": 0,
            "score_rule": "bitwise sign-negation of the packaged APE",
            "sequence_length": 4,
            "session_ids": [KNOWN_SESSION_ID],
            "start_pos": 0,
        },
        "model_id": MODEL_ID,
        "schema": KNOWN_ANSWER_SCHEMA,
    }


def _expected_counter_contract() -> dict[str, Any]:
    return {
        "counter_kind": "logical_semantic_accounting_only",
        "physical_interpretation": None,
        "schema": COUNTER_CONTRACT_SCHEMA,
        "stages": {
            "compressed_kv_commit": [
                field.name for field in fields(CompressedKVWriteCounters)
            ],
            "conversion": [field.name for field in fields(Binary32ToBF16Counters)],
            "pool": [field.name for field in fields(CompressionPoolCounters)],
            "raw_state_prepare": [
                field.name for field in fields(CompressionStateCounters)
            ],
            "valid_prefix_view": [
                field.name for field in fields(CompressedKVValidViewCounters)
            ],
        },
    }


def _expected_execution_contract() -> dict[str, Any]:
    return {
        "atomicity": {
            "abort": "discard all immutable candidates and publish no result",
            "commit": "atomically create one complete result/state package",
            "prior_state_mutation": "forbidden",
            "restart_persistence": "published immutable package; no hidden process state",
        },
        "dimensions": {
            "batch_capacity": INITIAL_BATCH_CAPACITY,
            "cache_capacity": INITIAL_CACHE_CAPACITY,
            "head_dim": HEAD_DIM,
            "maximum_active_batch": INITIAL_BATCH_CAPACITY,
            "maximum_request_sequence": MAX_REQUEST_SEQUENCE,
            "projected_width": PROJECTED_WIDTH,
            "ratio": RATIO,
        },
        "optional_payload_rule": (
            "pool and conversion payloads are present iff at least one ratio-four "
            "group completes; compressed commit otherwise receives zero rows"
        ),
        "program_sha256": PROGRAM_SHA256,
        "schema": EXECUTION_CONTRACT_SCHEMA,
        "state_identity": (
            "SHA-256 over canonical state metadata and exact raw/compressed payload descriptors"
        ),
    }


def _expected_coverage(source_kind: str) -> dict[str, Any]:
    return {
        "covered": [
            "official_full_size_ape_load"
            if source_kind == "official"
            else "synthetic_full_size_ape_load",
            "causal_raw_state_prepare_update",
            "deterministic_ratio4_pool",
            "finite_binary32_to_bf16_conversion",
            "causal_compressed_kv_commit",
            "valid_prefix_view",
            "immutable_state_artifact_publication",
        ],
        "model_id": MODEL_ID,
        "not_covered": [
            "learned_wkv_or_wgate_projection",
            "compressor_rms_normalization",
            "compressor_rotary_embedding",
            "compressor_activation_qdq",
            "full_attention_or_transformer_block",
            "physical_schedule_or_transactions",
            "cycles_latency_bandwidth_throughput_energy_ppa",
            "rom_or_gpu_comparison",
        ],
        "schema": COVERAGE_SCHEMA,
        "source_kind": source_kind,
    }


def _expected_source_binding(source_kind: str, ape_sha256: str) -> dict[str, Any]:
    official = source_kind == "official"
    return {
        "application_id": OFFICIAL_APPLICATION_ID if official else None,
        "ape_sha256": ape_sha256,
        "canonical_relative_path": OFFICIAL_TENSOR_PATH if official else None,
        "checkpoint_payload_evidence_eligible": official,
        "execution_input_provenance": (
            "controlled_known_answer_not_checkpoint_activation"
        ),
        "model_id": MODEL_ID,
        "model_execution_evidence_eligible": False,
        "schema": SOURCE_BINDING_SCHEMA,
        "shape": list(APE_SHAPE),
        "source_kind": source_kind,
        "tensor_name": OFFICIAL_TENSOR_NAME,
        "verification_id": OFFICIAL_VERIFICATION_ID if official else None,
    }


def _artifact_record(path: str, role: str, payload: bytes) -> dict[str, Any]:
    return {
        "path": path,
        "role": role,
        "sha256": _sha256(payload),
        "size_bytes": len(payload),
    }


def verify_deepseek_v4_compressor_executable_deployment(
    deployment_dir: Path,
) -> dict[str, Any]:
    """Verify exact tree closure, identities, semantics, and known answer."""

    try:
        with SecureDirectory(
            Path(deployment_dir),
            label="DeepSeek V4 compressor executable deployment",
        ) as root:
            manifest_file = root.open_file(
                "deployment_manifest.json",
                label="compressor deployment manifest",
                maximum_size=512 * 1024,
            )
            manifest_payload = manifest_file.read_bytes(
                label="compressor deployment manifest",
                maximum_bytes=512 * 1024,
            )
            manifest = _json(manifest_payload, "compressor deployment manifest")
            _exact_dict(
                manifest,
                {
                    "artifacts",
                    "build_id",
                    "claim_boundary",
                    "compiler",
                    "entrypoint",
                    "model_id",
                    "schema",
                    "source_kind",
                    "status",
                },
                "compressor deployment manifest",
            )
            source_kind = manifest["source_kind"]
            if source_kind not in {"official", "synthetic"}:
                _poison("deployment source_kind differs")
            expected_fixed = {
                "claim_boundary": CLAIM_BOUNDARY,
                "compiler": {"name": COMPILER_NAME, "version": COMPILER_VERSION},
                "entrypoint": ENTRYPOINT,
                "model_id": MODEL_ID,
                "schema": DEPLOYMENT_SCHEMA,
                "source_kind": source_kind,
                "status": DEPLOYMENT_STATUS,
            }
            for key, expected in expected_fixed.items():
                if canonical_json_bytes(manifest[key]) != canonical_json_bytes(
                    expected
                ):
                    _poison(f"deployment {key} differs")

            expected_files = {"deployment_manifest.json", *ENTRYPOINT.values()}
            expected_directories = {
                parent.as_posix()
                for path in expected_files
                for parent in Path(path).parents
                if parent != Path(".")
            }
            files, directories = root.enumerate_tree(
                maximum_depth=4, maximum_entries=64
            )
            if files != expected_files or directories != expected_directories:
                _poison("deployment tree closure differs")

            payloads: dict[str, bytes] = {}
            for path in sorted(ENTRYPOINT.values()):
                exact_size = APE_BYTES if path == ENTRYPOINT["ape"] else None
                maximum = APE_BYTES if exact_size else 2 * 1024 * 1024
                source = root.open_file(
                    path,
                    label=f"compressor artifact {path!r}",
                    exact_size=exact_size,
                    maximum_size=maximum,
                    minimum_size=0,
                )
                payloads[path] = source.read_bytes(
                    label=f"compressor artifact {path!r}",
                    maximum_bytes=max(1, maximum),
                )

            raw_artifacts = manifest["artifacts"]
            if type(raw_artifacts) is not list or len(raw_artifacts) != len(ENTRYPOINT):
                _poison("deployment artifact records differ")
            expected_records = []
            for key in sorted(ENTRYPOINT):
                role = (
                    "checkpoint_ape_f32"
                    if key == "ape" and source_kind == "official"
                    else "synthetic_ape_f32"
                    if key == "ape"
                    else ROLE_BY_KEY[key]
                )
                expected_records.append(
                    _artifact_record(
                        ENTRYPOINT[key],
                        role,
                        payloads[ENTRYPOINT[key]],
                    )
                )
            if canonical_json_bytes(raw_artifacts) != canonical_json_bytes(
                expected_records
            ):
                _poison("deployment artifact manifest differs from exact files")

            core = {key: manifest[key] for key in manifest if key != "build_id"}
            build_id = _digest(manifest["build_id"], "deployment build_id")
            if _sha256(canonical_json_bytes(core)) != build_id:
                _poison("deployment build_id differs from its canonical core")

            ape_payload = payloads[ENTRYPOINT["ape"]]
            ape = _ape_codes(ape_payload, source_kind=source_kind)
            ape_sha256 = _sha256(ape_payload)

            program_payload = payloads[ENTRYPOINT["program"]]
            if (
                len(program_payload) != PROGRAM_BYTES
                or _sha256(program_payload) != PROGRAM_SHA256
            ):
                _poison("packaged compressor program identity differs")
            program = decode(program_payload)
            verify(program)
            if encode(program) != program_payload:
                _poison("packaged compressor program does not round-trip")
            if payloads[ENTRYPOINT["program_disassembly"]] != disassemble(
                program
            ).encode("utf-8"):
                _poison("packaged compressor disassembly differs")
            program_contract = _json(
                payloads[ENTRYPOINT["program_contract"]],
                "compressor program contract",
            )
            verify_program_contract(
                program_contract,
                program_sha256=PROGRAM_SHA256,
                ape_sha256=ape_sha256,
            )

            schedule = _json(
                payloads[ENTRYPOINT["logical_schedule"]],
                "compressor logical schedule",
            )
            certificate = _json(
                payloads[ENTRYPOINT["logical_schedule_certificate"]],
                "compressor logical schedule certificate",
            )
            verify_logical_schedule(schedule, ape_sha256=ape_sha256)
            verify_logical_schedule_certificate(
                certificate,
                schedule,
                ape_sha256=ape_sha256,
            )

            expected_json = {
                ENTRYPOINT["counter_contract"]: _expected_counter_contract(),
                ENTRYPOINT["coverage"]: _expected_coverage(source_kind),
                ENTRYPOINT["execution_contract"]: _expected_execution_contract(),
                ENTRYPOINT["known_answer"]: _expected_known_answer(ape),
                ENTRYPOINT["source_binding"]: _expected_source_binding(
                    source_kind,
                    ape_sha256,
                ),
            }
            for path, expected in expected_json.items():
                observed = _json(payloads[path], f"compressor artifact {path!r}")
                if canonical_json_bytes(observed) != canonical_json_bytes(expected):
                    _poison(f"compressor artifact {path!r} differs")
            root.verify()
    except DeepSeekV4CompressorExecutableCheckError:
        raise
    except Exception as exc:
        _poison(f"compressor deployment verification failed: {exc}", exc)

    return {
        "ape_sha256": ape_sha256,
        "build_id": build_id,
        "checkpoint_payload_evidence_eligible": source_kind == "official",
        "controlled_known_answer_verified": True,
        "known_answer_sha256": _sha256(payloads[ENTRYPOINT["known_answer"]]),
        "model_execution_evidence_eligible": False,
        "program_sha256": PROGRAM_SHA256,
        "schedule_sha256": _sha256(payloads[ENTRYPOINT["logical_schedule"]]),
        "source_kind": source_kind,
        "status": ("verified_logical_schedule_and_controlled_full_width_known_answer"),
    }


__all__ = [
    "DeepSeekV4CompressorExecutableCheckError",
    "verify_deepseek_v4_compressor_executable_deployment",
]
