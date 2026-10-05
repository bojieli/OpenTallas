"""Authentic Qwen layer-0 post-attention and MLP qualification."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
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
from runtime.reference.tensor_accelerator_elementwise import (
    ElementwiseReferenceError,
    bf16_add_rne as reference_add,
    qwen3_silu_mul_bf16 as reference_silu_mul,
)
from runtime.reference.tensor_accelerator_rmsnorm import (
    EPSILON_CODE,
    RMSNormReferenceError,
    rms_norm_bf16 as reference_rmsnorm,
)
from runtime.tensor_accelerator.bf16 import (
    BF16KernelError,
    dense_bf16_linear_bf16,
)
from runtime.tensor_accelerator.elementwise import (
    ElementwiseKernelError,
    bf16_add_rne,
    qwen3_silu_mul_bf16,
)
from runtime.tensor_accelerator.rmsnorm import (
    RMSNormKernelError,
    rms_norm_bf16,
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


SCHEMA = "opentallas.tensor_accelerator.layer_qualification.v1"
ATTENTION_EXECUTION_SCHEMA = "opentallas.tensor_accelerator.attention_execution.v1"
LOOKUP_CONTRACT = "bf16_payload_lookup_v1"
MATRIX_CONTRACT = "bf16_bf16_fp32_sequential_rne_v1"
ADD_CONTRACT = "bf16_add_rne_v1"
RMSNORM_CONTRACT = "qwen3_rmsnorm_fp32_bf16_v1"
SILU_MUL_CONTRACT = "qwen3_silu_mul_bf16_v1"
HIDDEN_WIDTH = 4096
INTERMEDIATE_WIDTH = 12288
TOKEN_ID = 0
PINNED_SOURCE_SHA256 = (
    "704c914530530a1acb0b443add1f520404e3ac2c28c0ab7e16f80f86cfe8ccb2"
)
PINNED_ATTENTION_BUILD_ID = (
    "df11a02f915722127788d21501609b693b388f0e6c02f8ca4a83dc8f878cac95"
)
PINNED_ATTENTION_REPORT_ID = (
    "cf62189cc5d3e4e370b76e68767e6630e884077bb8dc39e3ba7c05646f43ef13"
)
PINNED_ATTENTION_QUALIFICATION_ID = (
    "82bd8f8b687e6674d72220b6a749e43da5224a22ba3bbeba562284a449d5a5bd"
)
PINNED_ATTENTION_PAYLOAD_SHA256 = (
    "d53e8a3890eb01357fb60ec2607a716179cec0eb556e28629963af655cd3e1fb"
)
REPORT_KEYS = {
    "accounting",
    "attention_input",
    "checkpoint_lock_id",
    "input",
    "intermediates",
    "numeric_contracts",
    "official_source_replay",
    "output",
    "projection_saturated_element_count",
    "report_id",
    "rmsnorm_saturated_element_count",
    "schema",
    "selected_reference",
    "sources",
    "status",
    "vector_saturated_element_count",
}

SOURCE_SPECS = {
    "embedding": ("model.embed_tokens.weight", 2),
    "attention_output_weight": ("model.layers.0.self_attn.o_proj.weight", 2),
    "post_attention_norm_weight": (
        "model.layers.0.post_attention_layernorm.weight",
        1,
    ),
    "gate_projection_weight": ("model.layers.0.mlp.gate_proj.weight", 2),
    "up_projection_weight": ("model.layers.0.mlp.up_proj.weight", 2),
    "down_projection_weight": ("model.layers.0.mlp.down_proj.weight", 2),
}

EXPECTED_SOURCE_PAYLOAD_SHA256 = {
    "embedding": "458b4af1d22ed8d7d12235ed5249a4606c7606e35e775e7ea2244ba623b0312e",
    "attention_output_weight": (
        "d6fec091373ead7a102c480d4642a9b135e9e2cf0d0c289e0425967c96877ac2"
    ),
    "post_attention_norm_weight": (
        "3df17c58e1832b24111c91cb19088b06f816de21702ce58acb514c91568cde5d"
    ),
    "gate_projection_weight": (
        "1f9e6bddfbbfff53f82b684776dd1b36643277b72d40f70abcd287e02ab7ea9e"
    ),
    "up_projection_weight": (
        "ac3f743828a20694255953a4290079eda84f38e48e608a24731fb0510780db35"
    ),
    "down_projection_weight": (
        "56ca545862b9b22d1feb9e00433b6cc8b5c22787c215b911902d3d40ce1e8096"
    ),
}

TARGET_KNOWN_ANSWER_SHA256 = {
    "attention_projected": (
        "341ef1b0843309008fd558042d0c56733b82bca5cc0753a80424338a29defae5"
    ),
    "down": "0833363e36d6e4c020e5502229f48823d40a57186bfe914971d4a729a251fa98",
    "gate": "c0c5409913dba39710879e36204410038d969b6a54eb071ab251f7be614f091d",
    "gated_mlp": (
        "c376bf04ccb73520870bd425b4ec601d778fa2cb969eecb98970a0feaeedf68d"
    ),
    "hidden_0": "6f57745a3765e8651c07b849d199577ec673d24cc40beb25bbaa72c6aadf73bb",
    "hidden_1": "7c65791e13e3814af26b0114a5437a3ff44e91b5728ca5e1f23f1f2b7929bf7a",
    "mlp_norm": "1113ccdb4770808c6d2b2ba072d8c885b2c67d0b89efcb2ef4930a76cb8dcf98",
    "post_attention": (
        "f872ce6f57ca36a30edf6abccfa2877bbb7234a905fe9e1417d99ea89ee79ec3"
    ),
    "silu_activation": (
        "90347986749a6a5a1382b76c820fb7186aff34f89c28a283545c54951f5561fc"
    ),
    "up": "ab3fbfe028419e49d5ad572444af774004c6bf733c69a67705f681d8beaf297c",
}

OFFICIAL_REPLAY_SHA256 = {
    "attention_projected": (
        "b89be17ce761ded2431b183ebfe46e1a7050dd981589a51a740c3502827ffac9"
    ),
    "down": "91637000df1d2acadf48f487e6eaf8224c483ee48406fa12eb9d874e259ae77c",
    "gate": "0b60d0d61f476a22587fa451c03b97c4f28e7e47e95aae0af3fdbeb58f5401a5",
    "gated_mlp": (
        "a013a838e9260e0cd0cb042653618dc4c233e058951e678049cb491a878b7536"
    ),
    "hidden_1": "9d30037a9d3e73b8f9386f7c5460b9a60cd6f2fc4d92d012446a2942633aac4f",
    "mlp_norm": TARGET_KNOWN_ANSWER_SHA256["mlp_norm"],
    "post_attention": TARGET_KNOWN_ANSWER_SHA256["post_attention"],
    "silu_activation": (
        "d47775ee830c6201105278eca715ded759e26c5b4d28bafeed649b45d03cfa08"
    ),
    "up": "ae7c0180306d9cfdac4d33a7da2cc4f4fcdfa2dd7aa204b8a13c3502a26c9a44",
}

OFFICIAL_REPLAY_DIFFERING_ELEMENTS = {
    "attention_projected": 1,
    "down": 24,
    "gate": 3,
    "gated_mlp": 6,
    "hidden_1": 8,
    "mlp_norm": 0,
    "post_attention": 0,
    "silu_activation": 2,
    "up": 4,
}


class LayerQualificationError(ArtifactError):
    """Raised when the authentic layer qualification is incomplete."""


def _report_keys(value: Mapping[str, Any]) -> None:
    try:
        exact_keys(dict(value), REPORT_KEYS, set(), "layer qualification")
    except ArtifactError as exc:
        raise LayerQualificationError(
            f"layer qualification key set differs: {exc}"
        ) from exc


def _record(raw: Mapping[str, Any], label: str, rank: int) -> dict[str, Any]:
    if not isinstance(raw, Mapping):
        raise LayerQualificationError(f"{label} must be a tensor record")
    shape = raw.get("shape")
    if (
        raw.get("dtype") != "BF16"
        or not isinstance(raw.get("name"), str)
        or not raw["name"]
        or not isinstance(shape, list)
        or len(shape) != rank
    ):
        raise LayerQualificationError(f"{label} must be a rank-{rank} BF16 tensor")
    parsed_shape = [
        require_int(value, f"{label}.shape[{index}]", minimum=1, maximum=1 << 30)
        for index, value in enumerate(shape)
    ]
    elements = 1
    for extent in parsed_shape:
        elements *= extent
    size_bytes = 2 * elements
    if raw.get("size_bytes") != size_bytes:
        raise LayerQualificationError(f"{label} byte size differs from shape")
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
        raise LayerQualificationError(f"{label} payload byte count differs")
    values = np.frombuffer(payload, dtype="<u2").reshape(tuple(shape))
    if np.any((values & np.uint16(0x7F80)) == np.uint16(0x7F80)):
        raise LayerQualificationError(f"{label} contains nonfinite BF16")
    return values


def _payload(values: np.ndarray) -> bytes:
    return np.ascontiguousarray(values, dtype="<u2").tobytes(order="C")


def _hash(values: np.ndarray) -> str:
    return hashlib.sha256(_payload(values)).hexdigest()


def _indices(raw: Sequence[int], extent: int, label: str) -> tuple[int, ...]:
    if isinstance(raw, (str, bytes, bytearray)) or not isinstance(raw, Sequence):
        raise LayerQualificationError(f"{label} must be a sequence")
    result = tuple(
        require_int(value, f"{label}[{index}]", minimum=0, maximum=extent - 1)
        for index, value in enumerate(raw)
    )
    if not result or result != tuple(sorted(set(result))):
        raise LayerQualificationError(
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
        raise LayerQualificationError(f"{label} projection failed: {exc}") from exc
    observed = [int(executed.values[0, index]) for index in indices]
    if tuple(observed) != reference.values[0]:
        raise LayerQualificationError(
            f"{label} optimized projection differs from scalar reference"
        )
    return executed.values, executed.output_saturated_element_count, observed


def _checked_add(
    left: np.ndarray,
    right: np.ndarray,
    label: str,
) -> tuple[np.ndarray, int]:
    try:
        executed = bf16_add_rne(left, right)
        reference = reference_add(left.tolist(), right.tolist())
    except (ElementwiseKernelError, ElementwiseReferenceError) as exc:
        raise LayerQualificationError(f"{label} add failed: {exc}") from exc
    if (
        tuple(tuple(int(item) for item in row) for row in executed.values.tolist())
        != reference.values
        or executed.output_saturated_element_count
        != reference.output_saturated_element_count
    ):
        raise LayerQualificationError(
            f"{label} optimized add differs from scalar reference"
        )
    return executed.values, executed.output_saturated_element_count


def _checked_rmsnorm(
    inputs: np.ndarray,
    weights: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, int, int]:
    try:
        executed = rms_norm_bf16(inputs, weights, epsilon_code=EPSILON_CODE)
        reference = reference_rmsnorm(
            inputs.tolist(),
            weights.tolist(),
            epsilon_code=EPSILON_CODE,
        )
    except (RMSNormKernelError, RMSNormReferenceError) as exc:
        raise LayerQualificationError(f"post-attention RMSNorm failed: {exc}") from exc
    values = tuple(tuple(int(item) for item in row) for row in executed.values.tolist())
    normalized = tuple(
        tuple(int(item) for item in row)
        for row in executed.normalized_values.tolist()
    )
    if (
        values != reference.values
        or normalized != reference.normalized_values
        or tuple(int(item) for item in executed.mean_square_codes.tolist())
        != reference.mean_square_codes
        or tuple(int(item) for item in executed.inverse_rms_codes.tolist())
        != reference.inverse_rms_codes
        or executed.normalized_saturated_element_count
        != reference.normalized_saturated_element_count
        or executed.output_saturated_element_count
        != reference.output_saturated_element_count
    ):
        raise LayerQualificationError(
            "post-attention optimized RMSNorm differs from scalar reference"
        )
    return (
        executed.values,
        executed.normalized_values,
        executed.mean_square_codes,
        executed.inverse_rms_codes,
        executed.normalized_saturated_element_count,
        executed.output_saturated_element_count,
    )


def _checked_silu(
    gate: np.ndarray,
    up: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, int, int]:
    try:
        executed = qwen3_silu_mul_bf16(gate, up)
        reference = reference_silu_mul(gate.tolist(), up.tolist())
    except (ElementwiseKernelError, ElementwiseReferenceError) as exc:
        raise LayerQualificationError(f"Qwen SiLU-multiply failed: {exc}") from exc
    activations = tuple(
        tuple(int(item) for item in row)
        for row in executed.activation_values.tolist()
    )
    values = tuple(tuple(int(item) for item in row) for row in executed.values.tolist())
    if (
        activations != reference.activation_values
        or values != reference.values
        or executed.activation_saturated_element_count
        != reference.activation_saturated_element_count
        or executed.output_saturated_element_count
        != reference.output_saturated_element_count
    ):
        raise LayerQualificationError(
            "optimized Qwen SiLU-multiply differs from scalar reference"
        )
    return (
        executed.activation_values,
        executed.values,
        executed.activation_saturated_element_count,
        executed.output_saturated_element_count,
    )


def _source_record(metadata: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "payload_sha256": metadata["payload_sha256"],
        "shape": metadata["shape"],
        "tensor": metadata["name"],
    }


def _binding(value: Mapping[str, Any]) -> dict[str, Any]:
    exact_keys(
        value,
        {
            "build_id",
            "payload_sha256",
            "qualification_report_id",
            "report_id",
        },
        set(),
        "attention binding",
    )
    result = {
        key: require_sha256(value.get(key), f"attention binding.{key}")
        for key in value
    }
    expected = {
        "build_id": PINNED_ATTENTION_BUILD_ID,
        "payload_sha256": PINNED_ATTENTION_PAYLOAD_SHA256,
        "qualification_report_id": PINNED_ATTENTION_QUALIFICATION_ID,
        "report_id": PINNED_ATTENTION_REPORT_ID,
    }
    if result != expected:
        raise LayerQualificationError("attention binding differs")
    return result


def qualify_layer_payloads(
    *,
    checkpoint_lock_id: str,
    token_id: int,
    attention_binding: Mapping[str, Any],
    attention_codes: Sequence[int],
    records: Mapping[str, Mapping[str, Any]],
    payloads: Mapping[str, bytes],
    selected_projection_rows: Mapping[str, Sequence[int]],
    selected_output_elements: Mapping[str, Sequence[int]],
) -> dict[str, Any]:
    """Execute and independently check the authentic layer-0 downstream path."""

    lock_id = require_sha256(checkpoint_lock_id, "checkpoint_lock_id")
    token = require_int(token_id, "token_id", minimum=0, maximum=151935)
    if token != TOKEN_ID:
        raise LayerQualificationError("layer qualification token ID differs")
    bound_attention = _binding(attention_binding)
    if set(records) != set(SOURCE_SPECS) or set(payloads) != set(SOURCE_SPECS):
        raise LayerQualificationError("layer source role coverage differs")
    metadata: dict[str, dict[str, Any]] = {}
    for role, (expected_name, rank) in SOURCE_SPECS.items():
        item = _record(records[role], role, rank)
        if (
            item["name"] != expected_name
            or item["payload_sha256"] != EXPECTED_SOURCE_PAYLOAD_SHA256[role]
        ):
            raise LayerQualificationError(f"{role} tensor identity differs")
        payload = payloads[role]
        if role == "embedding":
            if len(payload) != 2 * HIDDEN_WIDTH:
                raise LayerQualificationError(
                    "embedding row payload byte count differs"
                )
        elif hashlib.sha256(payload).hexdigest() != item["payload_sha256"]:
            raise LayerQualificationError(f"{role} payload identity differs")
        metadata[role] = item

    if (
        metadata["embedding"]["shape"] != [151936, HIDDEN_WIDTH]
        or metadata["attention_output_weight"]["shape"]
        != [HIDDEN_WIDTH, HIDDEN_WIDTH]
        or metadata["post_attention_norm_weight"]["shape"] != [HIDDEN_WIDTH]
        or metadata["gate_projection_weight"]["shape"]
        != [INTERMEDIATE_WIDTH, HIDDEN_WIDTH]
        or metadata["up_projection_weight"]["shape"]
        != [INTERMEDIATE_WIDTH, HIDDEN_WIDTH]
        or metadata["down_projection_weight"]["shape"]
        != [HIDDEN_WIDTH, INTERMEDIATE_WIDTH]
    ):
        raise LayerQualificationError("layer source shapes differ from frozen graph")

    raw_attention = tuple(
        require_int(
            code,
            f"attention_codes[{index}]",
            minimum=0,
            maximum=0xFFFF,
        )
        for index, code in enumerate(attention_codes)
    )
    if len(raw_attention) != HIDDEN_WIDTH:
        raise LayerQualificationError("attention output element coverage differs")
    attention = np.asarray(raw_attention, dtype=np.uint16).reshape(1, HIDDEN_WIDTH)
    if (
        _hash(attention) != PINNED_ATTENTION_PAYLOAD_SHA256
        or np.any((attention & np.uint16(0x7F80)) == np.uint16(0x7F80))
    ):
        raise LayerQualificationError("attention output payload differs")
    hidden_0 = _codes(payloads["embedding"], [1, HIDDEN_WIDTH], "embedding row")

    required_projections = {"attention_output", "down", "gate", "up"}
    if set(selected_projection_rows) != required_projections:
        raise LayerQualificationError("selected projection role coverage differs")
    attention_projected, attention_saturation, attention_selected = _projection(
        attention,
        payloads["attention_output_weight"],
        metadata["attention_output_weight"],
        selected_projection_rows["attention_output"],
        "attention output",
    )
    post_attention, first_add_saturation = _checked_add(
        hidden_0,
        attention_projected,
        "attention residual",
    )
    norm_weight = _codes(
        payloads["post_attention_norm_weight"],
        [HIDDEN_WIDTH],
        "post-attention norm weight",
    )
    (
        mlp_norm,
        mlp_normalized,
        mlp_means,
        mlp_inverse,
        mlp_normalized_saturation,
        mlp_output_saturation,
    ) = _checked_rmsnorm(post_attention, norm_weight)
    gate, gate_saturation, gate_selected = _projection(
        mlp_norm,
        payloads["gate_projection_weight"],
        metadata["gate_projection_weight"],
        selected_projection_rows["gate"],
        "gate",
    )
    up, up_saturation, up_selected = _projection(
        mlp_norm,
        payloads["up_projection_weight"],
        metadata["up_projection_weight"],
        selected_projection_rows["up"],
        "up",
    )
    (
        silu_activation,
        gated_mlp,
        silu_activation_saturation,
        silu_output_saturation,
    ) = _checked_silu(gate, up)
    down, down_saturation, down_selected = _projection(
        gated_mlp,
        payloads["down_projection_weight"],
        metadata["down_projection_weight"],
        selected_projection_rows["down"],
        "down",
    )
    hidden_1, second_add_saturation = _checked_add(
        post_attention,
        down,
        "MLP residual",
    )

    values = {
        "attention_projected": attention_projected,
        "down": down,
        "gate": gate,
        "gated_mlp": gated_mlp,
        "hidden_0": hidden_0,
        "hidden_1": hidden_1,
        "mlp_norm": mlp_norm,
        "post_attention": post_attention,
        "silu_activation": silu_activation,
        "up": up,
    }
    observed_known_answers = {role: _hash(value) for role, value in values.items()}
    if observed_known_answers != TARGET_KNOWN_ANSWER_SHA256:
        raise LayerQualificationError(
            "target layer path differs from frozen checkpoint-derived known answer"
        )

    if set(selected_output_elements) != set(values):
        raise LayerQualificationError("selected layer output role coverage differs")
    output_indices = {
        role: _indices(raw, value.size, f"{role} selected output elements")
        for role, (raw, value) in (
            (role, (selected_output_elements[role], values[role]))
            for role in sorted(values)
        )
    }
    flattened = {role: value.reshape(-1) for role, value in values.items()}
    projection_operations = (
        HIDDEN_WIDTH * HIDDEN_WIDTH
        + 3 * INTERMEDIATE_WIDTH * HIDDEN_WIDTH
    )
    body: dict[str, Any] = {
        "accounting": {
            "epsilon_additions": 1,
            "final_weight_multiplications": HIDDEN_WIDTH,
            "input_square_multiplications": HIDDEN_WIDTH,
            "mean_divisions": 1,
            "normalization_multiplications": HIDDEN_WIDTH,
            "projection_accumulation_additions": projection_operations,
            "projection_multiplications": projection_operations,
            "reciprocal_square_roots": 1,
            "reduction_additions": HIDDEN_WIDTH - 1,
            "residual_additions": 2 * HIDDEN_WIDTH,
            "sigmoid_denominator_additions": INTERMEDIATE_WIDTH,
            "sigmoid_divisions": INTERMEDIATE_WIDTH,
            "sigmoid_exponentials": INTERMEDIATE_WIDTH,
            "silu_multiplications": INTERMEDIATE_WIDTH,
            "up_gate_multiplications": INTERMEDIATE_WIDTH,
        },
        "attention_input": bound_attention,
        "checkpoint_lock_id": lock_id,
        "input": {
            "embedding_row_payload_sha256": _hash(hidden_0),
            "token_id": token,
        },
        "intermediates": {
            "attention_projected": {
                "payload_sha256": _hash(attention_projected),
                "shape": [1, HIDDEN_WIDTH],
            },
            "down": {
                "payload_sha256": _hash(down),
                "shape": [1, HIDDEN_WIDTH],
            },
            "gate": {
                "payload_sha256": _hash(gate),
                "shape": [1, INTERMEDIATE_WIDTH],
            },
            "gated_mlp": {
                "payload_sha256": _hash(gated_mlp),
                "shape": [1, INTERMEDIATE_WIDTH],
            },
            "mlp_norm": {
                "inverse_rms_binary32_codes_sha256": hashlib.sha256(
                    mlp_inverse.astype("<u4", copy=False).tobytes()
                ).hexdigest(),
                "mean_square_binary32_codes_sha256": hashlib.sha256(
                    mlp_means.astype("<u4", copy=False).tobytes()
                ).hexdigest(),
                "normalized_payload_sha256": _hash(mlp_normalized),
                "payload_sha256": _hash(mlp_norm),
                "shape": [1, HIDDEN_WIDTH],
            },
            "post_attention": {
                "payload_sha256": _hash(post_attention),
                "shape": [1, HIDDEN_WIDTH],
            },
            "silu_activation": {
                "payload_sha256": _hash(silu_activation),
                "shape": [1, INTERMEDIATE_WIDTH],
            },
            "up": {
                "payload_sha256": _hash(up),
                "shape": [1, INTERMEDIATE_WIDTH],
            },
        },
        "numeric_contracts": [
            ADD_CONTRACT,
            LOOKUP_CONTRACT,
            MATRIX_CONTRACT,
            RMSNORM_CONTRACT,
            SILU_MUL_CONTRACT,
        ],
        "official_source_replay": {
            "differing_element_count": OFFICIAL_REPLAY_DIFFERING_ELEMENTS,
            "implementation": "pinned_transformers_qwen3_cpu_bf16",
            "known_answer_payload_sha256": OFFICIAL_REPLAY_SHA256,
            "source_sha256": PINNED_SOURCE_SHA256,
            "status": "qualified_deterministic_target_adaptation",
        },
        "output": {
            "hidden_1": {
                "payload_sha256": _hash(hidden_1),
                "shape": [1, HIDDEN_WIDTH],
            }
        },
        "projection_saturated_element_count": {
            "attention_output": attention_saturation,
            "down": down_saturation,
            "gate": gate_saturation,
            "up": up_saturation,
        },
        "rmsnorm_saturated_element_count": {
            "normalized": mlp_normalized_saturation,
            "output": mlp_output_saturation,
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
                "attention_output": {
                    "codes": attention_selected,
                    "rows": list(selected_projection_rows["attention_output"]),
                },
                "down": {
                    "codes": down_selected,
                    "rows": list(selected_projection_rows["down"]),
                },
                "gate": {
                    "codes": gate_selected,
                    "rows": list(selected_projection_rows["gate"]),
                },
                "up": {
                    "codes": up_selected,
                    "rows": list(selected_projection_rows["up"]),
                },
            },
            "status": "exact_match",
        },
        "status": "pass",
        "vector_saturated_element_count": {
            "attention_residual": first_add_saturation,
            "final_residual": second_add_saturation,
            "silu_activation": silu_activation_saturation,
            "silu_output": silu_output_saturation,
        },
        "sources": {role: _source_record(metadata[role]) for role in sorted(metadata)},
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


def _load_attention(path: Path) -> tuple[dict[str, Any], tuple[int, ...]]:
    try:
        payload = Path(path).read_bytes()
        value = load_strict_json(Path(path))
    except (OSError, ArtifactError) as exc:
        raise LayerQualificationError(f"cannot load attention execution: {exc}") from exc
    if payload != canonical_json_bytes(value):
        raise LayerQualificationError("attention execution is not canonical JSON")
    body = {key: item for key, item in value.items() if key != "report_id"}
    if (
        value.get("schema") != ATTENTION_EXECUTION_SCHEMA
        or value.get("status") != "pass"
        or value.get("report_id") != sha256_bytes(canonical_json_bytes(body))
        or value.get("report_id") != PINNED_ATTENTION_REPORT_ID
        or value.get("build_id") != PINNED_ATTENTION_BUILD_ID
        or value.get("qualification_report_id")
        != PINNED_ATTENTION_QUALIFICATION_ID
    ):
        raise LayerQualificationError("attention execution identity/status differs")
    outputs = value.get("outputs")
    attention = outputs.get("attention") if isinstance(outputs, Mapping) else None
    if (
        not isinstance(attention, Mapping)
        or attention.get("dtype") != "bf16"
        or attention.get("shape") != [1, 32, 128]
        or attention.get("size_bytes") != 2 * HIDDEN_WIDTH
        or attention.get("payload_sha256") != PINNED_ATTENTION_PAYLOAD_SHA256
        or not isinstance(attention.get("codes"), list)
    ):
        raise LayerQualificationError("attention execution output differs")
    codes = tuple(
        require_int(
            code,
            f"attention output.codes[{index}]",
            minimum=0,
            maximum=0xFFFF,
        )
        for index, code in enumerate(attention["codes"])
    )
    if len(codes) != HIDDEN_WIDTH:
        raise LayerQualificationError("attention execution code coverage differs")
    if hashlib.sha256(np.asarray(codes, dtype="<u2").tobytes()).hexdigest() != (
        PINNED_ATTENTION_PAYLOAD_SHA256
    ):
        raise LayerQualificationError("attention execution payload hash differs")
    return (
        {
            "build_id": value["build_id"],
            "payload_sha256": attention["payload_sha256"],
            "qualification_report_id": value["qualification_report_id"],
            "report_id": value["report_id"],
        },
        codes,
    )


def qualify_locked_layer(
    *,
    snapshot: Path,
    checkpoint_lock_path: Path,
    attention_execution_path: Path,
    token_id: int,
    selected_projection_rows: Mapping[str, Sequence[int]],
    selected_output_elements: Mapping[str, Sequence[int]],
) -> dict[str, Any]:
    """Authenticate locked sources and qualify the downstream layer-0 path."""

    attention_binding, attention_codes = _load_attention(attention_execution_path)
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
                    tensor_name,
                    captured_payload.extend,
                )
                payloads[role] = bytes(captured_payload)
    except (CheckpointError, ArtifactError) as exc:
        raise LayerQualificationError(f"locked checkpoint read failed: {exc}") from exc
    return qualify_layer_payloads(
        checkpoint_lock_id=lock["lock_id"],
        token_id=token,
        attention_binding=attention_binding,
        attention_codes=attention_codes,
        records=records,
        payloads=payloads,
        selected_projection_rows=selected_projection_rows,
        selected_output_elements=selected_output_elements,
    )


def load_layer_qualification(path: Path) -> dict[str, Any]:
    """Load one canonical passing layer qualification report."""

    try:
        payload = Path(path).read_bytes()
        value = load_strict_json(Path(path))
    except (OSError, ArtifactError) as exc:
        raise LayerQualificationError(f"cannot load layer qualification: {exc}") from exc
    if payload != canonical_json_bytes(value):
        raise LayerQualificationError("layer qualification is not canonical JSON")
    _report_keys(value)
    body = {key: item for key, item in value.items() if key != "report_id"}
    if (
        value.get("schema") != SCHEMA
        or value.get("status") != "pass"
        or require_sha256(value.get("report_id"), "report_id")
        != sha256_bytes(canonical_json_bytes(body))
        or value.get("attention_input", {}).get("report_id")
        != PINNED_ATTENTION_REPORT_ID
        or value.get("output", {}).get("hidden_1", {}).get("payload_sha256")
        != TARGET_KNOWN_ANSWER_SHA256["hidden_1"]
    ):
        raise LayerQualificationError("layer qualification identity/status differs")
    return value


def publish_layer_qualification(report: Mapping[str, Any], output_path: Path) -> None:
    """Atomically publish canonical layer qualification without overwrite."""

    if not isinstance(report, Mapping):
        raise LayerQualificationError("qualification report must be an object")
    _report_keys(report)
    body = {key: item for key, item in report.items() if key != "report_id"}
    if (
        report.get("schema") != SCHEMA
        or report.get("status") != "pass"
        or report.get("report_id") != sha256_bytes(canonical_json_bytes(body))
    ):
        raise LayerQualificationError("qualification report identity/status differs")
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
            raise LayerQualificationError(
                f"qualification report will not be overwritten: {output}"
            ) from exc
    finally:
        temporary.unlink(missing_ok=True)


__all__ = [
    "LayerQualificationError",
    "OFFICIAL_REPLAY_DIFFERING_ELEMENTS",
    "OFFICIAL_REPLAY_SHA256",
    "TARGET_KNOWN_ANSWER_SHA256",
    "load_layer_qualification",
    "publish_layer_qualification",
    "qualify_layer_payloads",
    "qualify_locked_layer",
]
