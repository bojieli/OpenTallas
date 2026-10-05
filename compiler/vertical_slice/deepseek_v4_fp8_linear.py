"""Compile canonical DeepSeek V4 query-A tensors into an FP8 linear slice."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
import hashlib
import os
from pathlib import Path
import shutil
import struct
import tempfile
from typing import Any

from compiler.checking.deepseek_v4_application import (
    MANIFEST_FILENAME,
    VERIFICATION_FILENAME,
    verify_canonical_application,
)
from compiler.checking.deepseek_v4_fp8_linear_slice import (
    verify_deepseek_v4_fp8_linear_roundtrip,
)
from compiler.frontend.checkpoint import validate_checkpoint_lock
from compiler.frontend.deepseek_v4 import (
    MODEL_ID,
    REPOSITORY,
    REVISION,
    load_official_config,
    validate_official_checkpoint_lock,
)
from compiler.ir.model import canonical_json_bytes, load_strict_json, write_canonical_json
from compiler.microcode.deepseek_v4_fp8_linear import (
    ABI_MAJOR,
    ABI_MINOR,
    DENSE_BLOCK_SIZE,
    assemble,
    disassemble,
    encode,
)


DEPLOYMENT_SCHEMA = "opentallas.deepseek_v4_fp8_linear_deployment.v1"
SEMANTIC_SCHEMA = "opentallas.deepseek_v4_fp8_linear_slice.v1"
TENSOR_SCHEMA = "opentallas.deepseek_v4_fp8_linear_tensors.v1"
EXPECTATION_SCHEMA = "opentallas.deepseek_v4_fp8_linear_expectations.v1"
COVERAGE_SCHEMA = "opentallas.deepseek_v4_fp8_linear_coverage.v1"
FULL_DEPLOYMENT_SCHEMA = "opentallas.deepseek_v4_fp8_linear_full_deployment.v1"
FULL_SEMANTIC_SCHEMA = "opentallas.deepseek_v4_fp8_linear_full.v1"
FULL_TENSOR_SCHEMA = "opentallas.deepseek_v4_fp8_linear_full_tensors.v1"
FULL_COVERAGE_SCHEMA = "opentallas.deepseek_v4_fp8_linear_full_coverage.v1"
COMPILER_VERSION = "0.1.0"

WEIGHT_NAME = "layers.0.attn.wq_a.weight"
SCALE_NAME = "layers.0.attn.wq_a.scale"
DEFAULT_OUTPUT_ROWS = (0, 127, 128, 1023)
MAX_SELECTED_OUTPUT_ROWS = 64
MAX_FEATURE_EXTENT = 65_536
MAX_WEIGHT_PAYLOAD_BYTES = 8 * 1024 * 1024
MAX_FULL_PRODUCTS_PER_INPUT_ROW = 8 * 1024 * 1024


class DeepSeekV4FP8LinearBuildError(RuntimeError):
    """Raised when canonical query-A tensors cannot form the FP8 linear slice."""


def _sha256_file(path: Path) -> tuple[str, int]:
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as handle:
        while chunk := handle.read(8 * 1024 * 1024):
            digest.update(chunk)
            size += len(chunk)
    return digest.hexdigest(), size


def _safe_source(root: Path, value: Any, label: str) -> Path:
    if not isinstance(value, str) or not value or "\\" in value or "\x00" in value:
        raise DeepSeekV4FP8LinearBuildError(f"{label} is not a safe relative path")
    relative = Path(value)
    if relative.is_absolute() or any(
        part in {"", ".", ".."} for part in relative.parts
    ):
        raise DeepSeekV4FP8LinearBuildError(f"{label} is not a safe relative path")
    if relative.as_posix() != value:
        raise DeepSeekV4FP8LinearBuildError(f"{label} is not canonical POSIX")
    current = root
    for part in relative.parts:
        current /= part
        if current.is_symlink():
            raise DeepSeekV4FP8LinearBuildError(f"{label} traverses a symlink")
    try:
        current.resolve().relative_to(root.resolve())
    except ValueError as exc:
        raise DeepSeekV4FP8LinearBuildError(f"{label} escapes its application") from exc
    if not current.is_file():
        raise DeepSeekV4FP8LinearBuildError(f"{label} is not a regular file")
    return current


def _copy_locked(
    source: Path,
    destination: Path,
    *,
    expected_sha256: str,
    expected_size: int,
) -> tuple[str, int]:
    destination.parent.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256()
    size = 0
    try:
        with source.open("rb") as source_handle, destination.open("xb") as output:
            while chunk := source_handle.read(8 * 1024 * 1024):
                digest.update(chunk)
                size += len(chunk)
                output.write(chunk)
    except OSError as exc:
        raise DeepSeekV4FP8LinearBuildError(
            f"cannot copy canonical artifact {source.name!r}: {exc}"
        ) from exc
    observed = digest.hexdigest()
    if (observed, size) != (expected_sha256, expected_size):
        raise DeepSeekV4FP8LinearBuildError(
            f"canonical artifact {source.name!r} changed during compilation"
        )
    return observed, size


def _output_rows(value: Sequence[int], output_features: int) -> tuple[int, ...]:
    if isinstance(value, (str, bytes, bytearray)) or not isinstance(value, Sequence):
        raise DeepSeekV4FP8LinearBuildError("output_rows must be a sequence")
    result = []
    for index, row in enumerate(value):
        if (
            isinstance(row, bool)
            or not isinstance(row, int)
            or not 0 <= row < output_features
        ):
            raise DeepSeekV4FP8LinearBuildError(
                f"output_rows[{index}] must be in [0, {output_features})"
            )
        result.append(row)
    rows = tuple(result)
    if not rows or rows != tuple(sorted(set(rows))):
        raise DeepSeekV4FP8LinearBuildError(
            "output_rows must be non-empty, unique, and strictly increasing"
        )
    if len(rows) > MAX_SELECTED_OUTPUT_ROWS:
        raise DeepSeekV4FP8LinearBuildError(
            f"output_rows exceeds the {MAX_SELECTED_OUTPUT_ROWS}-row slice bound"
        )
    return rows


def _assignments(
    application: Mapping[str, Any], name: str
) -> list[Mapping[str, Any]]:
    raw = application.get("assignments")
    if not isinstance(raw, list):
        raise DeepSeekV4FP8LinearBuildError("canonical assignments are absent")
    records = [
        record
        for record in raw
        if isinstance(record, Mapping) and record.get("name") == name
    ]
    records.sort(key=lambda record: record.get("rank", -1))
    return records


def _validate_resource(
    application: Mapping[str, Any],
    name: str,
    *,
    storage_dtype: str,
    logical_dtype: str,
) -> tuple[list[Mapping[str, Any]], list[int]]:
    records = _assignments(application, name)
    if not records or [record.get("rank") for record in records] != list(
        range(len(records))
    ):
        raise DeepSeekV4FP8LinearBuildError(
            f"{name!r} must cover contiguous ranks from zero"
        )
    first = records[0]
    shape = first.get("shape")
    if (
        not isinstance(shape, list)
        or len(shape) != 2
        or any(
            isinstance(extent, bool) or not isinstance(extent, int) or extent < 1
            for extent in shape
        )
    ):
        raise DeepSeekV4FP8LinearBuildError(f"{name!r} shape is invalid")
    digest = first.get("sha256")
    payload_bytes = first.get("payload_bytes")
    for record in records:
        source = record.get("source")
        if (
            record.get("transform") != "identity"
            or record.get("storage_dtype") != storage_dtype
            or record.get("logical_dtype") != logical_dtype
            or record.get("shape") != shape
            or record.get("sha256") != digest
            or record.get("payload_bytes") != payload_bytes
            or not isinstance(source, Mapping)
            or source.get("name") != name
            or source.get("shape") != shape
            or source.get("storage_dtype") != storage_dtype
            or source.get("slice") is not None
        ):
            raise DeepSeekV4FP8LinearBuildError(
                f"{name!r} rank {record.get('rank')!r} is not an identical replica"
            )
    return records, shape


def _validate_payload_codes(path: Path, *, forbidden: frozenset[int], label: str) -> None:
    try:
        with path.open("rb") as handle:
            offset = 0
            while chunk := handle.read(8 * 1024 * 1024):
                for index, code in enumerate(chunk):
                    if code in forbidden:
                        raise DeepSeekV4FP8LinearBuildError(
                            f"{label} contains reserved code 0x{code:02x} at byte "
                            f"{offset + index}"
                        )
                offset += len(chunk)
    except OSError as exc:
        raise DeepSeekV4FP8LinearBuildError(f"cannot validate {label}: {exc}") from exc


def _artifact_record(path: Path, root: Path, role: str) -> dict[str, Any]:
    digest, size = _sha256_file(path)
    return {
        "path": path.relative_to(root).as_posix(),
        "role": role,
        "sha256": digest,
        "size_bytes": size,
    }


def _build_into(
    *,
    application_root: Path,
    application: Mapping[str, Any],
    verification: Mapping[str, Any],
    root: Path,
    requested_rows: Sequence[int],
    full_operator: bool,
) -> dict[str, Any]:
    raw_assignments = application.get("assignments")
    if not isinstance(raw_assignments, list) or any(
        not isinstance(record, Mapping) for record in raw_assignments
    ):
        raise DeepSeekV4FP8LinearBuildError("canonical assignments are malformed")
    assignment_names = {record.get("name") for record in raw_assignments}
    if assignment_names != {WEIGHT_NAME, SCALE_NAME}:
        raise DeepSeekV4FP8LinearBuildError(
            "FP8 linear application must contain exactly query-A weight and scale"
        )
    weights, weight_shape = _validate_resource(
        application,
        WEIGHT_NAME,
        storage_dtype="F8_E4M3",
        logical_dtype="FP8_E4M3FN",
    )
    scales, scale_shape = _validate_resource(
        application,
        SCALE_NAME,
        storage_dtype="F8_E8M0",
        logical_dtype="UE8M0_SCALE",
    )
    if len(weights) != len(scales):
        raise DeepSeekV4FP8LinearBuildError(
            "weight and scale replicas cover different ranks"
        )
    output_features, input_features = weight_shape
    if (
        output_features > MAX_FEATURE_EXTENT
        or input_features > MAX_FEATURE_EXTENT
    ):
        raise DeepSeekV4FP8LinearBuildError(
            f"FP8 feature extents must not exceed {MAX_FEATURE_EXTENT}"
        )
    expected_scale_shape = [
        (output_features + DENSE_BLOCK_SIZE - 1) // DENSE_BLOCK_SIZE,
        input_features // DENSE_BLOCK_SIZE,
    ]
    if input_features % DENSE_BLOCK_SIZE or scale_shape != expected_scale_shape:
        raise DeepSeekV4FP8LinearBuildError(
            "FP8 weight and scale shapes violate 128-by-128 tile orientation"
        )
    expected_weight_bytes = output_features * input_features
    expected_scale_bytes = expected_scale_shape[0] * expected_scale_shape[1]
    if expected_weight_bytes > MAX_WEIGHT_PAYLOAD_BYTES:
        raise DeepSeekV4FP8LinearBuildError(
            "FP8 weight payload exceeds the deployment memory budget"
        )
    if full_operator and expected_weight_bytes > MAX_FULL_PRODUCTS_PER_INPUT_ROW:
        raise DeepSeekV4FP8LinearBuildError(
            "complete FP8 operator exceeds the exact-arithmetic work budget"
        )
    if (
        weights[0].get("payload_bytes") != expected_weight_bytes
        or scales[0].get("payload_bytes") != expected_scale_bytes
    ):
        raise DeepSeekV4FP8LinearBuildError(
            "FP8 weight or scale payload size differs from its declared shape"
        )
    output_rows = (
        tuple(range(output_features))
        if full_operator
        else _output_rows(requested_rows, output_features)
    )
    official = application.get("evidence_scope") == "official_checkpoint"
    if official and (
        weight_shape != [1024, 4096]
        or scale_shape != [8, 32]
        or len(weights) != 4
    ):
        raise DeepSeekV4FP8LinearBuildError(
            "official query-A dimensions differ from the pinned V4 release"
        )

    weight_source = _safe_source(
        application_root, weights[0]["path"], "FP8 weight source"
    )
    scale_source = _safe_source(
        application_root, scales[0]["path"], "E8M0 scale source"
    )
    weight_relative = "rom/query_a.weight.bin"
    scale_relative = "rom/query_a.scale.bin"
    selection_relative = "rom/output_rows.bin"
    weight_digest, weight_size = _copy_locked(
        weight_source,
        root / weight_relative,
        expected_sha256=weights[0]["sha256"],
        expected_size=weights[0]["payload_bytes"],
    )
    scale_digest, scale_size = _copy_locked(
        scale_source,
        root / scale_relative,
        expected_sha256=scales[0]["sha256"],
        expected_size=scales[0]["payload_bytes"],
    )
    _validate_payload_codes(
        root / weight_relative,
        forbidden=frozenset({0x7F, 0xFF}),
        label="FP8 weight payload",
    )
    _validate_payload_codes(
        root / scale_relative,
        forbidden=frozenset({0xFF}),
        label="E8M0 scale payload",
    )
    (root / selection_relative).write_bytes(
        struct.pack(f"<{len(output_rows)}I", *output_rows)
    )
    selection_digest, selection_size = _sha256_file(root / selection_relative)
    tensor_manifest = {
        "output_selection": {
            "dtype": "U32",
            "path": selection_relative,
            "rows": list(output_rows),
            "sha256": selection_digest,
            "size_bytes": selection_size,
        },
        "scale": {
            "dtype": "F8_E8M0",
            "path": scale_relative,
            "replicated_ranks": [record["rank"] for record in scales],
            "sha256": scale_digest,
            "shape": scale_shape,
            "size_bytes": scale_size,
            "source_assignment_path": scales[0]["path"],
        },
        "schema": FULL_TENSOR_SCHEMA if full_operator else TENSOR_SCHEMA,
        "weight": {
            "dtype": "F8_E4M3",
            "path": weight_relative,
            "replicated_ranks": [record["rank"] for record in weights],
            "sha256": weight_digest,
            "shape": weight_shape,
            "size_bytes": weight_size,
            "source_assignment_path": weights[0]["path"],
        },
    }
    write_canonical_json(root / "tensor_manifest.json", tensor_manifest)

    source_record = application["source"]
    semantic_dimensions = {
        "block_size": DENSE_BLOCK_SIZE,
        "input_features": input_features,
        "output_features": output_features,
    }
    if not full_operator:
        semantic_dimensions["selected_output_rows"] = list(output_rows)
    semantic = {
        "claim_boundary": (
            "Complete layer-0 query-A FP8_LINEAR outputs for supplied BF16 rows; "
            "not input normalization, attention, or a transformer block."
            if full_operator
            else (
                "Selected logical output rows of layer-0 query-A FP8_LINEAR only; "
                "not complete query projection, attention, or a transformer block."
            )
        ),
        "dimensions": semantic_dimensions,
        "model_id": MODEL_ID,
        "numeric_profile": (
            "deepseek_v4_dense_fp8_full_v1"
            if full_operator
            else "deepseek_v4_dense_fp8_selected_rows_v1"
        ),
        "operation": {
            "input": "input_bf16_codes",
            "kind": "FP8_LINEAR" if full_operator else "FP8_LINEAR_SELECTED_ROWS",
            "output": "output_bf16_codes",
            "scale_resource": SCALE_NAME,
            "weight_resource": WEIGHT_NAME,
        },
        "schema": FULL_SEMANTIC_SCHEMA if full_operator else SEMANTIC_SCHEMA,
        "source": {
            "application_id": application["application_id"],
            "application_status": application["status"],
            "checkpoint_lock_id": source_record["checkpoint_lock_id"],
            "evidence_scope": application["evidence_scope"],
            "repository": source_record["repository"],
            "revision": source_record["revision"],
            "verification_id": verification["verification_id"],
        },
    }
    write_canonical_json(root / "model.ir.json", semantic)
    instructions = assemble()
    (root / "microcode.bin").write_bytes(encode(instructions))
    (root / "microcode.disasm").write_text(
        disassemble(instructions), encoding="ascii", newline="\n"
    )
    expectations = {
        "counter_coefficients_per_input_row": {
            "activation_blocks_quantized": input_features // DENSE_BLOCK_SIZE,
            "activation_values_quantized": input_features,
            "bf16_outputs_written": len(output_rows),
            "binary32_block_reduction_adds": len(output_rows)
            * (input_features // DENSE_BLOCK_SIZE - 1),
            "binary32_product_accumulates": len(output_rows) * input_features,
            "logical_input_bytes_read": input_features * 2,
            "logical_output_bytes_written": len(output_rows) * 2,
            "logical_rom_bytes_read": len(output_rows)
            * (input_features + input_features // DENSE_BLOCK_SIZE),
            "matrix_block_dots": len(output_rows)
            * (input_features // DENSE_BLOCK_SIZE),
        },
        "fixed_counters": {
            "completion_events": 1,
            "micro_ops_executed": 2,
            "semantic_operations_executed": 1,
        },
        "hardware_accounting": {
            "cycles": None,
            "hbm_transactions": None,
            "stalls": None,
            "status": "not modeled by the functional FP8 linear slice",
        },
        "schema": EXPECTATION_SCHEMA,
    }
    write_canonical_json(root / "execution_expectations.json", expectations)
    coverage = {
        "implemented_operator_kind": (
            "FP8_LINEAR" if full_operator else "FP8_LINEAR_SELECTED_ROWS"
        ),
        "model_id": MODEL_ID,
        "schema": FULL_COVERAGE_SCHEMA if full_operator else COVERAGE_SCHEMA,
        "status": (
            "complete_operator_arithmetic_only"
            if full_operator
            else "selected_output_rows_arithmetic_slice_only"
        ),
        "underlying_graph_operator_kind": "FP8_LINEAR",
    }
    write_canonical_json(root / "operator_coverage.json", coverage)
    roundtrip = verify_deepseek_v4_fp8_linear_roundtrip(root, application_root)
    write_canonical_json(root / "roundtrip_report.json", roundtrip)

    roles = {
        "execution_expectations.json": "execution_expectations",
        "microcode.bin": "microcode",
        "microcode.disasm": "microcode_disassembly",
        "model.ir.json": "semantic_ir",
        "operator_coverage.json": "operator_coverage",
        "roundtrip_report.json": "roundtrip_report",
        scale_relative: "scale_table",
        selection_relative: "output_selection",
        "tensor_manifest.json": "tensor_manifest",
        weight_relative: "weight_matrix",
    }
    artifacts = [
        _artifact_record(root / relative, root, roles[relative])
        for relative in sorted(roles)
    ]
    identity = {
        "artifacts": artifacts,
        "compiler_version": COMPILER_VERSION,
        "microcode_abi": {
            "major": ABI_MAJOR,
            "minor": ABI_MINOR,
            "name": "deepseek_v4_fp8_linear",
        },
        "model_id": MODEL_ID,
        "source_application_id": application["application_id"],
    }
    build_id = hashlib.sha256(canonical_json_bytes(identity)).hexdigest()
    deployment_claims = (
        [
            "Executes every logical output row of one FP8_LINEAR operator.",
            "Does not execute input normalization, attention, a transformer block, logits, or decode state.",
            "Functional counters are not hardware cycles, PPA, or NVIDIA comparison evidence.",
        ]
        if full_operator
        else [
            "Executes selected logical output rows of one FP8_LINEAR operator.",
            "Does not execute all query-A rows, attention, a transformer block, logits, or decode state.",
            "Functional counters are not hardware cycles, PPA, or NVIDIA comparison evidence.",
        ]
    )
    deployment = {
        "artifacts": artifacts,
        "build_id": build_id,
        "claim_boundary": deployment_claims,
        "compiler": {
            "name": (
                "opentallas-deepseek-v4-fp8-linear-compiler"
                if full_operator
                else "opentallas-deepseek-v4-fp8-linear-slice-compiler"
            ),
            "version": COMPILER_VERSION,
        },
        "entrypoint": {
            "execution_expectations": "execution_expectations.json",
            "microcode": "microcode.bin",
            "semantic_ir": "model.ir.json",
            "tensor_manifest": "tensor_manifest.json",
        },
        "microcode_abi": identity["microcode_abi"],
        "model_id": MODEL_ID,
        "schema": FULL_DEPLOYMENT_SCHEMA if full_operator else DEPLOYMENT_SCHEMA,
        "source_application_id": application["application_id"],
        "status": (
            "real_checkpoint_complete_fp8_linear_operator"
            if full_operator and official
            else (
                "development_fixture_complete_fp8_linear_operator_not_release_evidence"
                if full_operator
                else (
                    "real_checkpoint_selected_fp8_linear_rows_not_full_operator"
                    if official
                    else "development_fixture_selected_fp8_linear_rows_not_release_evidence"
                )
            )
        ),
    }
    write_canonical_json(root / "deployment_manifest.json", deployment)
    return deployment


def _build_deepseek_v4_fp8_linear_deployment(
    *,
    snapshot: Path,
    lock: dict[str, Any],
    application_root: Path,
    output: Path,
    output_rows: Sequence[int],
    full_operator: bool,
) -> dict[str, Any]:
    """Verify a canonical application and atomically build the arithmetic slice."""

    validate_checkpoint_lock(lock)
    application_root = Path(application_root).resolve()
    output = Path(output).resolve()
    if not application_root.is_dir():
        raise DeepSeekV4FP8LinearBuildError(
            f"canonical application is not a directory: {application_root}"
        )
    if output.exists():
        raise DeepSeekV4FP8LinearBuildError(f"output already exists: {output}")
    if output == Path(output.anchor):
        raise DeepSeekV4FP8LinearBuildError("output must not be a filesystem root")
    try:
        application = load_strict_json(application_root / MANIFEST_FILENAME)
        retained = load_strict_json(application_root / VERIFICATION_FILENAME)
    except (OSError, ValueError) as exc:
        raise DeepSeekV4FP8LinearBuildError(
            f"cannot load canonical application evidence: {exc}"
        ) from exc
    verification = verify_canonical_application(application_root, snapshot, lock)
    if retained != verification:
        raise DeepSeekV4FP8LinearBuildError(
            "retained canonical verification differs from independent replay"
        )
    official = application.get("evidence_scope") == "official_checkpoint"
    if official:
        validate_official_checkpoint_lock(lock, load_official_config())
        source = application.get("source")
        if not isinstance(source, Mapping) or (
            source.get("repository"), source.get("revision")
        ) != (REPOSITORY, REVISION):
            raise DeepSeekV4FP8LinearBuildError(
                "official application is not the pinned V4 Flash release"
            )
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(
        tempfile.mkdtemp(prefix=f".{output.name}.tmp-", dir=output.parent)
    )
    try:
        deployment = _build_into(
            application_root=application_root,
            application=application,
            verification=verification,
            root=temporary,
            requested_rows=output_rows,
            full_operator=full_operator,
        )
        os.replace(temporary, output)
        return deployment
    except Exception:
        if temporary.exists():
            shutil.rmtree(temporary)
        raise


def build_deepseek_v4_fp8_linear_deployment(
    *,
    snapshot: Path,
    lock: dict[str, Any],
    application_root: Path,
    output: Path,
    output_rows: Sequence[int] = DEFAULT_OUTPUT_ROWS,
) -> dict[str, Any]:
    """Build the bounded selected-row diagnostic profile."""

    return _build_deepseek_v4_fp8_linear_deployment(
        snapshot=snapshot,
        lock=lock,
        application_root=application_root,
        output=output,
        output_rows=output_rows,
        full_operator=False,
    )


def build_deepseek_v4_fp8_linear_full_deployment(
    *,
    snapshot: Path,
    lock: dict[str, Any],
    application_root: Path,
    output: Path,
) -> dict[str, Any]:
    """Build a complete-output FP8_LINEAR operator deployment."""

    return _build_deepseek_v4_fp8_linear_deployment(
        snapshot=snapshot,
        lock=lock,
        application_root=application_root,
        output=output,
        output_rows=(),
        full_operator=True,
    )


__all__ = [
    "DEFAULT_OUTPUT_ROWS",
    "DeepSeekV4FP8LinearBuildError",
    "build_deepseek_v4_fp8_linear_deployment",
    "build_deepseek_v4_fp8_linear_full_deployment",
]
