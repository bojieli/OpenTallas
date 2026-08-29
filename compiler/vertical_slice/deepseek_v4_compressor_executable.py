"""Build a generated executable package for one DeepSeek V4 compressor slice.

The package contains the full layer-2 main-compressor APE tensor, exact fixed
microcode, a logical (non-cycle) schedule and certificate, interface contracts,
and a full-width deterministic known-answer record.  It begins after learned
projection and intentionally does not claim that the direct BF16 harness payload
is the official post-RMSNorm/RoPE/QDQ attention-cache value.
"""

from __future__ import annotations

from dataclasses import asdict, fields
import hashlib
from pathlib import Path
import struct
from typing import Any, Literal

from compiler.checking.deepseek_v4_compressor_executable import (
    verify_deepseek_v4_compressor_executable_deployment,
)
from compiler.microcode.deepseek_v4_compressor import (
    APE_BYTES,
    APE_SHAPE,
    HEAD_DIM,
    MODEL_ID,
    PROGRAM_BYTES,
    PROGRAM_SHA256,
    PROJECTED_WIDTH,
    RATIO,
    assemble,
    build_program_contract,
    disassemble,
    encode,
)
from compiler.scheduling.deepseek_v4_compressor import (
    build_logical_schedule,
    build_logical_schedule_certificate,
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
    canonical_json_bytes,
    publish_payload_tree,
)


DEPLOYMENT_SCHEMA = "opentallas.deepseek_v4_compressor_executable.v1"
COUNTER_CONTRACT_SCHEMA = "opentallas.deepseek_v4_compressor_counter_contract.v1"
EXECUTION_CONTRACT_SCHEMA = (
    "opentallas.deepseek_v4_compressor_execution_contract.v1"
)
KNOWN_ANSWER_SCHEMA = "opentallas.deepseek_v4_compressor_known_answer.v1"
COVERAGE_SCHEMA = "opentallas.deepseek_v4_compressor_coverage.v1"
SOURCE_BINDING_SCHEMA = "opentallas.deepseek_v4_compressor_source_binding.v1"
DEPLOYMENT_STATUS = "post_projection_functional_slice_logical_schedule_only"
COMPILER_NAME = "opentallas-deepseek-v4-compressor-executable-packager"
COMPILER_VERSION = "0.1.0"
OFFICIAL_APE_SHA256 = (
    "f93afef4a88371262663f89f026a48b79f7187bd9d6498742c1db2860ae73554"
)
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


class DeepSeekV4CompressorExecutableBuildError(RuntimeError):
    """Raised when the compressor artifact package cannot be built exactly."""


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _json(value: object) -> bytes:
    return canonical_json_bytes(value)


def _validate_ape(payload: bytes, *, source_kind: str) -> tuple[int, ...]:
    if type(payload) is not bytes or len(payload) != APE_BYTES:
        raise DeepSeekV4CompressorExecutableBuildError(
            f"APE payload must contain exactly {APE_BYTES} bytes"
        )
    digest = _sha256(payload)
    if source_kind == "official" and digest != OFFICIAL_APE_SHA256:
        raise DeepSeekV4CompressorExecutableBuildError(
            "official APE payload differs from the canonical layer-2 tensor"
        )
    codes = tuple(code for (code,) in struct.iter_unpack("<I", payload))
    for index, code in enumerate(codes):
        if code & 0x7F800000 == 0x7F800000:
            raise DeepSeekV4CompressorExecutableBuildError(
                f"APE contains nonfinite binary32 at element {index}"
            )
    return codes


def _reshape_ape(codes: tuple[int, ...]) -> tuple[tuple[int, ...], ...]:
    return tuple(
        tuple(codes[row * PROJECTED_WIDTH : (row + 1) * PROJECTED_WIDTH])
        for row in range(RATIO)
    )


def _f32_payload(value: object) -> bytes:
    flattened: list[int] = []

    def visit(item: object) -> None:
        if type(item) is int:
            flattened.append(item)
            return
        if type(item) not in {tuple, list}:
            raise DeepSeekV4CompressorExecutableBuildError(
                "known-answer F32 value is not a rectangular integer tensor"
            )
        for child in item:
            visit(child)

    visit(value)
    return b"".join(struct.pack("<I", code) for code in flattened)


def _bf16_payload(value: object) -> bytes:
    flattened: list[int] = []

    def visit(item: object) -> None:
        if type(item) is int:
            flattened.append(item)
            return
        if type(item) not in {tuple, list}:
            raise DeepSeekV4CompressorExecutableBuildError(
                "known-answer BF16 value is not a rectangular integer tensor"
            )
        for child in item:
            visit(child)

    visit(value)
    return b"".join(struct.pack("<H", code) for code in flattened)


def known_answer_inputs_from_ape(
    ape_codes: tuple[tuple[int, ...], ...],
) -> tuple[tuple, tuple]:
    """Generate the full-width APE-cancellation known-answer input.

    Scores are the sign-negated APE codes.  The four current-half KV rows are
    constants 1, 2, 3, and 4, so the first overlap pool output is exactly 2.5
    in every one of the 512 columns.
    """

    zero = encode_binary32_rne(0)
    rows_kv: list[tuple[int, ...]] = []
    rows_score: list[tuple[int, ...]] = []
    for phase in range(RATIO):
        value = encode_binary32_rne(phase + 1)
        rows_kv.append((zero,) * HEAD_DIM + (value,) * HEAD_DIM)
        rows_score.append(tuple(code ^ 0x80000000 for code in ape_codes[phase]))
    return ((tuple(rows_kv),), ((tuple(rows_score),)))


def _known_answer(ape_codes: tuple[tuple[int, ...], ...]) -> dict[str, Any]:
    projected_kv, projected_scores = known_answer_inputs_from_ape(ape_codes)
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
        ape_codes,
        session_ids=(KNOWN_SESSION_ID,),
        start_pos=0,
    )
    if not state_result.should_compress or state_result.pool_inputs is None:
        raise DeepSeekV4CompressorExecutableBuildError(
            "known-answer vector did not expose one complete pool group"
        )
    pool = compress_pool_f32(
        state_result.pool_inputs.kv_f32_codes,
        state_result.pool_inputs.score_f32_codes,
        ratio=RATIO,
    )
    converted = binary32_tensor_to_bf16_rne(pool.pooled_f32_codes)
    cache_rows = tuple(
        tuple((row,) for row in sequence) for sequence in converted.bf16_codes
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
    pooled_payload = _f32_payload(pool.pooled_f32_codes)
    converted_payload = _bf16_payload(converted.bf16_codes)
    view_payload = _bf16_payload(view.bf16_codes)
    expected_f32 = encode_binary32_rne(5)  # replaced below by exact 5/2 encoding
    expected_f32 = 0x40200000
    if any(code != expected_f32 for sequence in pool.pooled_f32_codes for row in sequence for code in row):
        raise DeepSeekV4CompressorExecutableBuildError(
            "known-answer pooled values differ from exact binary32 2.5"
        )
    if any(code != 0x4020 for sequence in converted.bf16_codes for row in sequence for code in row):
        raise DeepSeekV4CompressorExecutableBuildError(
            "known-answer converted values differ from exact BF16 2.5"
        )
    return {
        "counters": {
            "compressed_kv_commit": asdict(write.counters),
            "conversion": asdict(converted.counters),
            "pool": asdict(pool.counters),
            "raw_state_prepare": asdict(state_result.counters),
            "valid_prefix_view": asdict(view.counters),
        },
        "expected": {
            "completed_rows_per_batch": 1,
            "converted_bf16_code": "0x4020",
            "converted_bf16_sha256": _sha256(converted_payload),
            "pooled_binary32_code": "0x40200000",
            "pooled_f32_sha256": _sha256(pooled_payload),
            "valid_prefix_lengths": [1],
            "valid_view_bf16_sha256": _sha256(view_payload),
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


def _counter_contract() -> dict[str, Any]:
    stages = {
        "compressed_kv_commit": [field.name for field in fields(CompressedKVWriteCounters)],
        "conversion": [field.name for field in fields(Binary32ToBF16Counters)],
        "pool": [field.name for field in fields(CompressionPoolCounters)],
        "raw_state_prepare": [field.name for field in fields(CompressionStateCounters)],
        "valid_prefix_view": [field.name for field in fields(CompressedKVValidViewCounters)],
    }
    return {
        "counter_kind": "logical_semantic_accounting_only",
        "physical_interpretation": None,
        "schema": COUNTER_CONTRACT_SCHEMA,
        "stages": stages,
    }


def _execution_contract() -> dict[str, Any]:
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


def _coverage(*, source_kind: str) -> dict[str, Any]:
    return {
        "covered": [
            "official_full_size_ape_load" if source_kind == "official" else "synthetic_full_size_ape_load",
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


def _source_binding(*, source_kind: str, ape_sha256: str) -> dict[str, Any]:
    official = source_kind == "official"
    return {
        "application_id": OFFICIAL_APPLICATION_ID if official else None,
        "ape_sha256": ape_sha256,
        "canonical_relative_path": OFFICIAL_TENSOR_PATH if official else None,
        "evidence_eligible": official,
        "model_id": MODEL_ID,
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


def build_deepseek_v4_compressor_executable_deployment(
    ape_path: Path,
    output_dir: Path,
    *,
    source_kind: Literal["official", "synthetic"] = "official",
) -> dict[str, Any]:
    """Build, publish create-once, and independently verify one deployment."""

    if source_kind not in {"official", "synthetic"}:
        raise DeepSeekV4CompressorExecutableBuildError(
            "source_kind must be exactly 'official' or 'synthetic'"
        )
    try:
        ape_payload = Path(ape_path).read_bytes()
    except OSError as exc:
        raise DeepSeekV4CompressorExecutableBuildError(
            f"cannot read APE source: {exc}"
        ) from exc
    flat_ape = _validate_ape(ape_payload, source_kind=source_kind)
    ape_codes = _reshape_ape(flat_ape)
    ape_sha256 = _sha256(ape_payload)

    program = assemble()
    program_payload = encode(program)
    if len(program_payload) != PROGRAM_BYTES or _sha256(program_payload) != PROGRAM_SHA256:
        raise DeepSeekV4CompressorExecutableBuildError("assembled program identity drifted")
    schedule = build_logical_schedule(ape_sha256=ape_sha256)
    certificate = build_logical_schedule_certificate(
        schedule,
        ape_sha256=ape_sha256,
    )
    payloads: dict[str, bytes] = {
        ENTRYPOINT["ape"]: ape_payload,
        ENTRYPOINT["counter_contract"]: _json(_counter_contract()),
        ENTRYPOINT["coverage"]: _json(_coverage(source_kind=source_kind)),
        ENTRYPOINT["execution_contract"]: _json(_execution_contract()),
        ENTRYPOINT["known_answer"]: _json(_known_answer(ape_codes)),
        ENTRYPOINT["logical_schedule"]: _json(schedule),
        ENTRYPOINT["logical_schedule_certificate"]: _json(certificate),
        ENTRYPOINT["program"]: program_payload,
        ENTRYPOINT["program_contract"]: _json(
            build_program_contract(
                program_sha256=PROGRAM_SHA256,
                ape_sha256=ape_sha256,
            )
        ),
        ENTRYPOINT["program_disassembly"]: disassemble(program).encode("utf-8"),
        ENTRYPOINT["source_binding"]: _json(
            _source_binding(source_kind=source_kind, ape_sha256=ape_sha256)
        ),
    }
    roles = {
        "ape": "checkpoint_ape_f32" if source_kind == "official" else "synthetic_ape_f32",
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
    artifacts = [
        _artifact_record(ENTRYPOINT[key], roles[key], payloads[ENTRYPOINT[key]])
        for key in sorted(ENTRYPOINT)
    ]
    core = {
        "artifacts": artifacts,
        "claim_boundary": list(CLAIM_BOUNDARY),
        "compiler": {"name": COMPILER_NAME, "version": COMPILER_VERSION},
        "entrypoint": dict(ENTRYPOINT),
        "model_id": MODEL_ID,
        "schema": DEPLOYMENT_SCHEMA,
        "source_kind": source_kind,
        "status": DEPLOYMENT_STATUS,
    }
    manifest = dict(core)
    manifest["build_id"] = _sha256(_json(core))
    payloads["deployment_manifest.json"] = _json(manifest)
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
            label="DeepSeek V4 compressor executable deployment",
            maximum_depth=4,
            maximum_entries=64,
        )
        report = verify_deepseek_v4_compressor_executable_deployment(
            Path(output_dir)
        )
    except (SecureArtifactError, OSError, ValueError) as exc:
        raise DeepSeekV4CompressorExecutableBuildError(
            f"cannot publish verified compressor deployment: {exc}"
        ) from exc
    return report


__all__ = [
    "CLAIM_BOUNDARY",
    "COMPILER_NAME",
    "COMPILER_VERSION",
    "COUNTER_CONTRACT_SCHEMA",
    "COVERAGE_SCHEMA",
    "DEPLOYMENT_SCHEMA",
    "DEPLOYMENT_STATUS",
    "DeepSeekV4CompressorExecutableBuildError",
    "ENTRYPOINT",
    "EXECUTION_CONTRACT_SCHEMA",
    "INITIAL_BATCH_CAPACITY",
    "INITIAL_CACHE_CAPACITY",
    "KNOWN_ANSWER_SCHEMA",
    "KNOWN_SESSION_ID",
    "MAX_REQUEST_SEQUENCE",
    "OFFICIAL_APE_SHA256",
    "OFFICIAL_APPLICATION_ID",
    "OFFICIAL_TENSOR_NAME",
    "OFFICIAL_TENSOR_PATH",
    "OFFICIAL_VERIFICATION_ID",
    "SOURCE_BINDING_SCHEMA",
    "build_deepseek_v4_compressor_executable_deployment",
    "known_answer_inputs_from_ape",
]
