"""Real-checkpoint qualification for Qwen layer-0 Q/K/V preparation."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
import struct
import tempfile
from typing import Any, Mapping, Sequence

import numpy as np

from compiler.frontend.checkpoint import (
    CheckpointError,
    LockedCheckpointReader,
    load_checkpoint_lock,
)
from runtime.reference.tensor_accelerator_bf16 import (
    BF16MatrixReferenceError,
    dense_bf16_linear_selected_rows_bf16 as reference_selected_rows,
)
from runtime.reference.tensor_accelerator_rmsnorm import (
    EPSILON_CODE,
    RMSNormReferenceError,
    rms_norm_bf16 as reference_rmsnorm,
)
from runtime.reference.tensor_accelerator_rope import (
    INV_FREQ_BINARY32_CODES,
    RoPEReferenceError,
    rope_bf16 as reference_rope,
)
from runtime.tensor_accelerator.bf16 import (
    BF16KernelError,
    dense_bf16_linear_bf16,
)
from runtime.tensor_accelerator.rmsnorm import (
    RMSNormKernelError,
    rms_norm_bf16,
)
from runtime.tensor_accelerator.rope import (
    RoPEKernelError,
    coefficient_table_bf16,
    rope_bf16,
)

from .common import (
    ArtifactError,
    canonical_json_bytes,
    exact_keys,
    load_strict_json,
    require_int,
    require_sha256,
    sha256_bytes,
)


SCHEMA = "opentallas.tensor_accelerator.qkv_qualification.v1"
MATRIX_CONTRACT = "bf16_bf16_fp32_sequential_rne_v1"
RMSNORM_CONTRACT = "qwen3_rmsnorm_fp32_bf16_v1"
ROPE_CONTRACT = "qwen3_rope_fp32_bf16_v1"
LOOKUP_CONTRACT = "bf16_payload_lookup_v1"
HIDDEN_WIDTH = 4096
QUERY_HEADS = 32
KEY_VALUE_HEADS = 8
HEAD_DIM = 128
CONTEXT_POSITIONS = 8000
COEFFICIENT_TABLE_SHA256 = (
    "82b9d0c0dc0c98906ced230591852dbd27d73760de42df8de253ae29243034b9"
)
PINNED_SOURCE_SHA256 = (
    "704c914530530a1acb0b443add1f520404e3ac2c28c0ab7e16f80f86cfe8ccb2"
)
OFFICIAL_KNOWN_ANSWER_SHA256 = {
    "attention_norm": "976d6de1a3ed91a066c7efed4354e578edf366a3b51a7e6077d68282981ffa58",
    "k_norm": "71af5033456b74d137d248f4019f848aedb8c8f758f952612082ad48d50f6a66",
    "k_raw": "dd690fbd9886a0af94cc6b2477ef5bfcc84fe66cac66f345f2ec654a83b28403",
    "k_rotary": "ce427ae533331720b9b58dde633e3ca352fa9fe0d3dd09d8cab222b799963858",
    "q_norm": "bf01d5254a7616bfffac6f789fbae1b94c68c5201944c8faf297b803987a401c",
    "q_raw": "b900b79fd38ff6a9bff470ac27e9672b0c3724b84f6a1f7e964c2ec0918ea0ff",
    "q_rotary": "a846335c825cf9fb06213220acf157c6a805376b1324a7cec09d6fa4621e718d",
    "v": "b07011da7a3d58dcccceb91e596ceebc2084ab3c2fc9d0b6a9a8704e91ef8dc5",
}
SOURCE_SPECS = {
    "embedding": ("model.embed_tokens.weight", 2),
    "input_norm_weight": ("model.layers.0.input_layernorm.weight", 1),
    "q_projection_weight": ("model.layers.0.self_attn.q_proj.weight", 2),
    "k_projection_weight": ("model.layers.0.self_attn.k_proj.weight", 2),
    "v_projection_weight": ("model.layers.0.self_attn.v_proj.weight", 2),
    "q_norm_weight": ("model.layers.0.self_attn.q_norm.weight", 1),
    "k_norm_weight": ("model.layers.0.self_attn.k_norm.weight", 1),
}


class QKVQualificationError(ArtifactError):
    """Raised when Q/K/V source or differential evidence is incomplete."""


def _record(raw: Mapping[str, Any], label: str, rank: int) -> dict[str, Any]:
    if not isinstance(raw, Mapping):
        raise QKVQualificationError(f"{label} must be a tensor record")
    shape = raw.get("shape")
    if (
        raw.get("dtype") != "BF16"
        or not isinstance(raw.get("name"), str)
        or not raw["name"]
        or not isinstance(shape, list)
        or len(shape) != rank
    ):
        raise QKVQualificationError(f"{label} must be a rank-{rank} BF16 tensor")
    parsed_shape = [
        require_int(value, f"{label}.shape[{index}]", minimum=1, maximum=1 << 30)
        for index, value in enumerate(shape)
    ]
    elements = 1
    for extent in parsed_shape:
        elements *= extent
    size_bytes = 2 * elements
    if raw.get("size_bytes") != size_bytes:
        raise QKVQualificationError(f"{label} byte size differs from shape")
    return {
        "dtype": "BF16",
        "name": raw["name"],
        "payload_sha256": require_sha256(
            raw.get("payload_sha256"), f"{label}.payload_sha256"
        ),
        "shape": parsed_shape,
        "size_bytes": size_bytes,
    }


def _codes(payload: bytes, shape: Sequence[int], label: str) -> np.ndarray:
    elements = 1
    for extent in shape:
        elements *= extent
    if not isinstance(payload, bytes) or len(payload) != 2 * elements:
        raise QKVQualificationError(f"{label} payload byte count differs")
    return np.frombuffer(payload, dtype="<u2").reshape(tuple(shape))


def _payload(values: np.ndarray) -> bytes:
    return np.ascontiguousarray(values, dtype="<u2").tobytes(order="C")


def _hash(values: np.ndarray) -> str:
    return hashlib.sha256(_payload(values)).hexdigest()


def _indices(raw: Sequence[int], extent: int, label: str) -> tuple[int, ...]:
    if isinstance(raw, (str, bytes, bytearray)) or not isinstance(raw, Sequence):
        raise QKVQualificationError(f"{label} must be a sequence")
    result = tuple(
        require_int(value, f"{label}[{index}]", minimum=0, maximum=extent - 1)
        for index, value in enumerate(raw)
    )
    if not result or result != tuple(sorted(set(result))):
        raise QKVQualificationError(
            f"{label} must be nonempty, unique, and strictly increasing"
        )
    return result


def _projection(
    inputs: np.ndarray,
    weight_payload: bytes,
    weight: Mapping[str, Any],
    selected: Sequence[int],
    label: str,
) -> tuple[np.ndarray, int, list[int]]:
    weights = _codes(weight_payload, weight["shape"], f"{label} weight")
    indices = _indices(selected, weight["shape"][0], f"{label} selected rows")
    try:
        executed = dense_bf16_linear_bf16(
            inputs,
            weights,
            input_tile_rows=1,
            output_tile_rows=64,
        )
        reference = reference_selected_rows(
            inputs.tolist(),
            weights[list(indices)].tolist(),
            output_row_indices=indices,
            declared_output_count=weight["shape"][0],
        )
    except (BF16KernelError, BF16MatrixReferenceError) as exc:
        raise QKVQualificationError(f"{label} projection failed: {exc}") from exc
    observed = [int(executed.values[0, index]) for index in indices]
    if tuple(observed) != reference.values[0]:
        raise QKVQualificationError(
            f"{label} optimized projection differs from scalar reference"
        )
    return executed.values, executed.output_saturated_element_count, observed


def _checked_rmsnorm(
    inputs: np.ndarray,
    weights: np.ndarray,
    label: str,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, int, int]:
    try:
        executed = rms_norm_bf16(inputs, weights, epsilon_code=EPSILON_CODE)
        reference = reference_rmsnorm(
            inputs.tolist(),
            weights.tolist(),
            epsilon_code=EPSILON_CODE,
        )
    except (RMSNormKernelError, RMSNormReferenceError) as exc:
        raise QKVQualificationError(f"{label} RMSNorm failed: {exc}") from exc
    values = tuple(tuple(int(item) for item in row) for row in executed.values.tolist())
    normalized = tuple(
        tuple(int(item) for item in row) for row in executed.normalized_values.tolist()
    )
    means = tuple(int(item) for item in executed.mean_square_codes.tolist())
    inverse = tuple(int(item) for item in executed.inverse_rms_codes.tolist())
    if (
        values != reference.values
        or normalized != reference.normalized_values
        or means != reference.mean_square_codes
        or inverse != reference.inverse_rms_codes
        or executed.normalized_saturated_element_count
        != reference.normalized_saturated_element_count
        or executed.output_saturated_element_count
        != reference.output_saturated_element_count
    ):
        raise QKVQualificationError(
            f"{label} optimized RMSNorm differs from scalar reference"
        )
    return (
        executed.values,
        executed.normalized_values,
        executed.mean_square_codes,
        executed.inverse_rms_codes,
        executed.normalized_saturated_element_count,
        executed.output_saturated_element_count,
    )


def _source_record(metadata: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "payload_sha256": metadata["payload_sha256"],
        "shape": metadata["shape"],
        "tensor": metadata["name"],
    }


def qualify_qkv_payloads(
    *,
    checkpoint_lock_id: str,
    token_id: int,
    position_id: int,
    records: Mapping[str, Mapping[str, Any]],
    payloads: Mapping[str, bytes],
    selected_projection_rows: Mapping[str, Sequence[int]],
    selected_output_elements: Mapping[str, Sequence[int]],
) -> dict[str, Any]:
    """Execute and independently check full-width layer-0 Q/K/V preparation."""

    lock_id = require_sha256(checkpoint_lock_id, "checkpoint_lock_id")
    if set(records) != set(SOURCE_SPECS) or set(payloads) != set(SOURCE_SPECS):
        raise QKVQualificationError("Q/K/V source role coverage differs")
    metadata: dict[str, dict[str, Any]] = {}
    for role, (expected_name, rank) in SOURCE_SPECS.items():
        item = _record(records[role], role, rank)
        if item["name"] != expected_name:
            raise QKVQualificationError(f"{role} tensor identity differs")
        payload = payloads[role]
        if role == "embedding":
            if len(payload) != 2 * HIDDEN_WIDTH:
                raise QKVQualificationError("embedding row payload byte count differs")
        elif hashlib.sha256(payload).hexdigest() != item["payload_sha256"]:
            raise QKVQualificationError(f"{role} payload identity differs")
        metadata[role] = item

    if (
        metadata["embedding"]["shape"][1] != HIDDEN_WIDTH
        or metadata["input_norm_weight"]["shape"] != [HIDDEN_WIDTH]
        or metadata["q_projection_weight"]["shape"]
        != [QUERY_HEADS * HEAD_DIM, HIDDEN_WIDTH]
        or metadata["k_projection_weight"]["shape"]
        != [KEY_VALUE_HEADS * HEAD_DIM, HIDDEN_WIDTH]
        or metadata["v_projection_weight"]["shape"]
        != [KEY_VALUE_HEADS * HEAD_DIM, HIDDEN_WIDTH]
        or metadata["q_norm_weight"]["shape"] != [HEAD_DIM]
        or metadata["k_norm_weight"]["shape"] != [HEAD_DIM]
    ):
        raise QKVQualificationError("Q/K/V source shapes differ from the frozen graph")
    token = require_int(
        token_id,
        "token_id",
        minimum=0,
        maximum=metadata["embedding"]["shape"][0] - 1,
    )
    position = require_int(
        position_id,
        "position_id",
        minimum=0,
        maximum=CONTEXT_POSITIONS - 1,
    )
    embedding = _codes(payloads["embedding"], [1, HIDDEN_WIDTH], "embedding row")
    input_norm_weight = _codes(
        payloads["input_norm_weight"], [HIDDEN_WIDTH], "input norm weight"
    )
    (
        attention_norm,
        attention_normalized,
        attention_means,
        attention_inverse,
        attention_normalized_saturations,
        attention_output_saturations,
    ) = _checked_rmsnorm(embedding, input_norm_weight, "layer input")

    required_projection_keys = {"q", "k", "v"}
    if set(selected_projection_rows) != required_projection_keys:
        raise QKVQualificationError("selected projection role coverage differs")
    q_raw, q_projection_saturations, q_selected = _projection(
        attention_norm,
        payloads["q_projection_weight"],
        metadata["q_projection_weight"],
        selected_projection_rows["q"],
        "Q",
    )
    k_raw, k_projection_saturations, k_selected = _projection(
        attention_norm,
        payloads["k_projection_weight"],
        metadata["k_projection_weight"],
        selected_projection_rows["k"],
        "K",
    )
    v_raw, v_projection_saturations, v_selected = _projection(
        attention_norm,
        payloads["v_projection_weight"],
        metadata["v_projection_weight"],
        selected_projection_rows["v"],
        "V",
    )

    q_heads = q_raw.reshape(QUERY_HEADS, HEAD_DIM)
    k_heads = k_raw.reshape(KEY_VALUE_HEADS, HEAD_DIM)
    v_heads = v_raw.reshape(KEY_VALUE_HEADS, HEAD_DIM)
    q_norm_weight = _codes(payloads["q_norm_weight"], [HEAD_DIM], "Q norm weight")
    k_norm_weight = _codes(payloads["k_norm_weight"], [HEAD_DIM], "K norm weight")
    (
        q_norm,
        q_normalized,
        q_means,
        q_inverse,
        q_normalized_saturations,
        q_norm_saturations,
    ) = _checked_rmsnorm(q_heads, q_norm_weight, "Q head")
    (
        k_norm,
        k_normalized,
        k_means,
        k_inverse,
        k_normalized_saturations,
        k_norm_saturations,
    ) = _checked_rmsnorm(k_heads, k_norm_weight, "K head")

    coefficient_table = coefficient_table_bf16(CONTEXT_POSITIONS)
    coefficient_payload = _payload(coefficient_table)
    if hashlib.sha256(coefficient_payload).hexdigest() != COEFFICIENT_TABLE_SHA256:
        raise QKVQualificationError("qualified RoPE coefficient table identity differs")
    coefficient_row = coefficient_table[position]
    cosine = coefficient_row[:HEAD_DIM]
    sine = coefficient_row[HEAD_DIM:]
    try:
        executed_rope = rope_bf16(q_norm, k_norm, coefficient_row)
        scalar_rope = reference_rope(
            q_norm.tolist(),
            k_norm.tolist(),
            cosine.tolist(),
            sine.tolist(),
        )
    except (RoPEKernelError, RoPEReferenceError) as exc:
        raise QKVQualificationError(f"RoPE execution failed: {exc}") from exc
    q_rotary = executed_rope.query_values
    k_rotary = executed_rope.key_values
    if (
        tuple(tuple(int(item) for item in row) for row in q_rotary.tolist())
        != scalar_rope.query_values
        or tuple(tuple(int(item) for item in row) for row in k_rotary.tolist())
        != scalar_rope.key_values
        or executed_rope.multiplication_saturated_element_count
        != scalar_rope.multiplication_saturated_element_count
        or executed_rope.addition_saturated_element_count
        != scalar_rope.addition_saturated_element_count
    ):
        raise QKVQualificationError("optimized RoPE differs from scalar reference")

    if set(selected_output_elements) != required_projection_keys:
        raise QKVQualificationError("selected output role coverage differs")
    flattened = {
        "q": q_rotary.reshape(-1),
        "k": k_rotary.reshape(-1),
        "v": v_heads.reshape(-1),
    }
    output_indices = {
        role: _indices(
            selected_output_elements[role],
            values.size,
            f"{role} selected output elements",
        )
        for role, values in flattened.items()
    }
    observed_known_answers = {
        "attention_norm": _hash(attention_norm),
        "k_norm": _hash(k_norm),
        "k_raw": _hash(k_raw),
        "k_rotary": _hash(k_rotary),
        "q_norm": _hash(q_norm),
        "q_raw": _hash(q_raw),
        "q_rotary": _hash(q_rotary),
        "v": _hash(v_heads),
    }
    if observed_known_answers != OFFICIAL_KNOWN_ANSWER_SHA256:
        raise QKVQualificationError(
            "target Q/K/V path differs from the frozen official known answer"
        )

    projection_elements = QUERY_HEADS * HEAD_DIM + 2 * KEY_VALUE_HEADS * HEAD_DIM
    rms_rows = 1 + QUERY_HEADS + KEY_VALUE_HEADS
    rms_elements = HIDDEN_WIDTH + QUERY_HEADS * HEAD_DIM + KEY_VALUE_HEADS * HEAD_DIM
    rope_elements = (QUERY_HEADS + KEY_VALUE_HEADS) * HEAD_DIM
    inv_frequency_payload = b"".join(
        struct.pack("<I", code) for code in INV_FREQ_BINARY32_CODES
    )
    body: dict[str, Any] = {
        "accounting": {
            "coefficient_table_bytes": len(coefficient_payload),
            "epsilon_additions": rms_rows,
            "final_weight_multiplications": rms_elements,
            "input_square_multiplications": rms_elements,
            "mean_divisions": rms_rows,
            "normalization_multiplications": rms_elements,
            "projection_accumulation_additions": projection_elements * HIDDEN_WIDTH,
            "projection_multiplications": projection_elements * HIDDEN_WIDTH,
            "reciprocal_square_roots": rms_rows,
            "reduction_additions": (
                HIDDEN_WIDTH - 1 + (QUERY_HEADS + KEY_VALUE_HEADS) * (HEAD_DIM - 1)
            ),
            "rope_additions": rope_elements,
            "rope_multiplications": 2 * rope_elements,
        },
        "checkpoint_lock_id": lock_id,
        "input": {
            "embedding_row_payload_sha256": hashlib.sha256(
                payloads["embedding"]
            ).hexdigest(),
            "position_id": position,
            "token_id": token,
        },
        "intermediates": {
            "attention_norm": {
                "inverse_rms_binary32_codes_sha256": hashlib.sha256(
                    attention_inverse.astype("<u4", copy=False).tobytes()
                ).hexdigest(),
                "mean_square_binary32_codes_sha256": hashlib.sha256(
                    attention_means.astype("<u4", copy=False).tobytes()
                ).hexdigest(),
                "normalized_payload_sha256": _hash(attention_normalized),
                "payload_sha256": _hash(attention_norm),
                "shape": [1, HIDDEN_WIDTH],
            },
            "k_norm": {
                "inverse_rms_binary32_codes_sha256": hashlib.sha256(
                    k_inverse.astype("<u4", copy=False).tobytes()
                ).hexdigest(),
                "mean_square_binary32_codes_sha256": hashlib.sha256(
                    k_means.astype("<u4", copy=False).tobytes()
                ).hexdigest(),
                "normalized_payload_sha256": _hash(k_normalized),
                "payload_sha256": _hash(k_norm),
                "shape": [KEY_VALUE_HEADS, HEAD_DIM],
            },
            "k_raw": {"payload_sha256": _hash(k_raw), "shape": [1, 1024]},
            "q_norm": {
                "inverse_rms_binary32_codes_sha256": hashlib.sha256(
                    q_inverse.astype("<u4", copy=False).tobytes()
                ).hexdigest(),
                "mean_square_binary32_codes_sha256": hashlib.sha256(
                    q_means.astype("<u4", copy=False).tobytes()
                ).hexdigest(),
                "normalized_payload_sha256": _hash(q_normalized),
                "payload_sha256": _hash(q_norm),
                "shape": [QUERY_HEADS, HEAD_DIM],
            },
            "q_raw": {"payload_sha256": _hash(q_raw), "shape": [1, 4096]},
        },
        "numeric_contracts": [
            LOOKUP_CONTRACT,
            MATRIX_CONTRACT,
            RMSNORM_CONTRACT,
            ROPE_CONTRACT,
        ],
        "official_reference": {
            "implementation": "pinned_transformers_qwen3_cpu_bf16",
            "known_answer_payload_sha256": observed_known_answers,
            "source_sha256": PINNED_SOURCE_SHA256,
            "status": "exact_match",
        },
        "outputs": {
            "k_rotary": {
                "payload_sha256": _hash(k_rotary),
                "shape": [KEY_VALUE_HEADS, HEAD_DIM],
            },
            "q_rotary": {
                "payload_sha256": _hash(q_rotary),
                "shape": [QUERY_HEADS, HEAD_DIM],
            },
            "v": {
                "payload_sha256": _hash(v_heads),
                "shape": [KEY_VALUE_HEADS, HEAD_DIM],
            },
        },
        "projection_saturated_element_count": {
            "k": k_projection_saturations,
            "q": q_projection_saturations,
            "v": v_projection_saturations,
        },
        "rmsnorm_saturated_element_count": {
            "attention_norm_normalized": attention_normalized_saturations,
            "attention_norm_output": attention_output_saturations,
            "k_normalized": k_normalized_saturations,
            "k_output": k_norm_saturations,
            "q_normalized": q_normalized_saturations,
            "q_output": q_norm_saturations,
        },
        "rope": {
            "addition_saturated_element_count": (
                executed_rope.addition_saturated_element_count
            ),
            "coefficient_row_payload_sha256": _hash(coefficient_row),
            "coefficient_table_payload_sha256": COEFFICIENT_TABLE_SHA256,
            "coefficient_table_shape": [CONTEXT_POSITIONS, 2 * HEAD_DIM],
            "inverse_frequency_binary32_payload_sha256": hashlib.sha256(
                inv_frequency_payload
            ).hexdigest(),
            "multiplication_saturated_element_count": (
                executed_rope.multiplication_saturated_element_count
            ),
        },
        "schema": SCHEMA,
        "selected_reference": {
            "output": {
                role: {
                    "codes": [int(flattened[role][index]) for index in indices],
                    "element_indices": list(indices),
                }
                for role, indices in output_indices.items()
            },
            "projection": {
                "k": {
                    "codes": k_selected,
                    "rows": list(selected_projection_rows["k"]),
                },
                "q": {
                    "codes": q_selected,
                    "rows": list(selected_projection_rows["q"]),
                },
                "v": {
                    "codes": v_selected,
                    "rows": list(selected_projection_rows["v"]),
                },
            },
            "status": "exact_match",
        },
        "sources": {role: _source_record(metadata[role]) for role in sorted(metadata)},
        "status": "pass",
    }
    return {**body, "report_id": sha256_bytes(canonical_json_bytes(body))}


def _capture_row(shape: tuple[int, int], row: int) -> tuple[bytearray, Any]:
    row_bytes = shape[1] * 2
    start = row * row_bytes
    captured = bytearray()
    cursor = 0

    def consume(chunk: bytes) -> None:
        nonlocal cursor
        end = cursor + len(chunk)
        overlap_start = max(cursor, start)
        overlap_end = min(end, start + row_bytes)
        if overlap_start < overlap_end:
            captured.extend(chunk[overlap_start - cursor : overlap_end - cursor])
        cursor = end

    return captured, consume


def qualify_locked_qkv(
    *,
    snapshot: Path,
    checkpoint_lock_path: Path,
    token_id: int,
    position_id: int,
    selected_projection_rows: Mapping[str, Sequence[int]],
    selected_output_elements: Mapping[str, Sequence[int]],
) -> dict[str, Any]:
    """Authenticate all source tensors and qualify the connected Q/K/V path."""

    records: dict[str, Mapping[str, Any]] = {}
    payloads: dict[str, bytes] = {}
    try:
        lock = load_checkpoint_lock(Path(checkpoint_lock_path))
        with LockedCheckpointReader(Path(snapshot), lock) as reader:
            embedding_raw = reader.tensor_record(SOURCE_SPECS["embedding"][0])
            embedding = _record(embedding_raw, "embedding", 2)
            token = require_int(
                token_id,
                "token_id",
                minimum=0,
                maximum=embedding["shape"][0] - 1,
            )
            captured, consumer = _capture_row(tuple(embedding["shape"]), token)
            reader.consume_tensor_payload(embedding["name"], consumer)
            records["embedding"] = embedding_raw
            payloads["embedding"] = bytes(captured)
            for role, (tensor_name, _) in SOURCE_SPECS.items():
                if role == "embedding":
                    continue
                captured_payload = bytearray()
                records[role] = reader.consume_tensor_payload(
                    tensor_name, captured_payload.extend
                )
                payloads[role] = bytes(captured_payload)
    except (CheckpointError, ArtifactError) as exc:
        raise QKVQualificationError(f"locked checkpoint read failed: {exc}") from exc
    return qualify_qkv_payloads(
        checkpoint_lock_id=lock["lock_id"],
        token_id=token,
        position_id=position_id,
        records=records,
        payloads=payloads,
        selected_projection_rows=selected_projection_rows,
        selected_output_elements=selected_output_elements,
    )


def load_qkv_qualification(path: Path) -> dict[str, Any]:
    """Load one canonical passing Q/K/V qualification report."""

    try:
        payload = Path(path).read_bytes()
        value = load_strict_json(Path(path))
    except (OSError, ArtifactError) as exc:
        raise QKVQualificationError(f"cannot load Q/K/V qualification: {exc}") from exc
    if payload != canonical_json_bytes(value):
        raise QKVQualificationError("Q/K/V qualification is not canonical JSON")
    exact_keys(
        value,
        {
            "accounting",
            "checkpoint_lock_id",
            "input",
            "intermediates",
            "numeric_contracts",
            "official_reference",
            "outputs",
            "projection_saturated_element_count",
            "report_id",
            "rmsnorm_saturated_element_count",
            "rope",
            "schema",
            "selected_reference",
            "sources",
            "status",
        },
        set(),
        "Q/K/V qualification",
    )
    body = {key: item for key, item in value.items() if key != "report_id"}
    if (
        value["schema"] != SCHEMA
        or value["status"] != "pass"
        or require_sha256(value["report_id"], "report_id")
        != sha256_bytes(canonical_json_bytes(body))
        or value["rope"]["coefficient_table_payload_sha256"] != COEFFICIENT_TABLE_SHA256
    ):
        raise QKVQualificationError("Q/K/V qualification identity/status differs")
    return value


def publish_qkv_qualification(report: Mapping[str, Any], output_path: Path) -> None:
    """Atomically publish canonical Q/K/V qualification without overwrite."""

    if not isinstance(report, Mapping):
        raise QKVQualificationError("qualification report must be an object")
    body = {key: item for key, item in report.items() if key != "report_id"}
    if (
        report.get("schema") != SCHEMA
        or report.get("status") != "pass"
        or report.get("report_id") != sha256_bytes(canonical_json_bytes(body))
    ):
        raise QKVQualificationError("qualification report identity/status differs")
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        dir=output.parent,
        prefix=f".{output.name}.",
        suffix=".tmp",
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(canonical_json_bytes(dict(report)))
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.link(temporary, output)
        except FileExistsError as exc:
            raise QKVQualificationError(
                f"report already exists and will not be overwritten: {output}"
            ) from exc
    finally:
        temporary.unlink(missing_ok=True)


__all__ = [
    "COEFFICIENT_TABLE_SHA256",
    "CONTEXT_POSITIONS",
    "HEAD_DIM",
    "KEY_VALUE_HEADS",
    "OFFICIAL_KNOWN_ANSWER_SHA256",
    "PINNED_SOURCE_SHA256",
    "QKVQualificationError",
    "QUERY_HEADS",
    "SCHEMA",
    "load_qkv_qualification",
    "publish_qkv_qualification",
    "qualify_locked_qkv",
    "qualify_qkv_payloads",
]
