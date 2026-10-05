"""Complete neutral-kernel coverage for the production Qwen3-8B graph.

This module closes the semantic lowering boundary only.  It emits one neutral
kernel for every operation in the pinned 617-operation Model Graph IR and binds
those kernels to independently retained numeric qualifications.  It does not
allocate HBM or SRAM, emit commands, execute the model, or claim full-model
correctness.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Mapping, Sequence

from .attention_qualification import load_attention_qualification
from .common import (
    ArtifactError,
    canonical_json_bytes,
    sha256_bytes,
    sha256_file,
)
from .layer_qualification import load_layer_qualification
from .production_capability import (
    ProductionCapability,
    ProductionCapabilityError,
    load_production_capability,
)
from .production_model import (
    ProductionModelGraph,
    ProductionModelGraphError,
    ProductionOperation,
    ProductionTensor,
    load_production_model_graph,
)
from .qkv_qualification import load_qkv_qualification
from .qwen_final_output_qualification import (
    load_qwen_final_output_qualification,
)


COVERAGE_SCHEMA = "opentallas.tensor_accelerator.qwen_full_model_semantic_coverage.v1"
KERNEL_SCHEMA = "opentallas.production_tensor_kernel_ir.v1"
MODEL_ID = "qwen3-8b"
NUMERIC_PROFILE = "qwen3_bf16_gqa_target_v1"
OPERATION_COUNT = 617
TENSOR_COUNT = 1053
STATE_RESOURCE_COUNT = 36
LAYER_COUNT = 36
MIN_CONTEXT_CAPACITY = 8000
MAX_CONTEXT_CAPACITY = 40960
HIDDEN_WIDTH = 4096
INTERMEDIATE_WIDTH = 12288
VOCABULARY_SIZE = 151936
QUERY_HEADS = 32
KEY_VALUE_HEADS = 8
HEAD_DIM = 128

CONTRACT_BY_KIND = {
    "ADD": "bf16_add_rne_v1",
    "ATTENTION": "qwen3_gqa_fp32_softmax_bf16_v1",
    "EMBEDDING_LOOKUP": "bf16_payload_lookup_v1",
    "KV_PREPARE": "bf16_byte_preserving_state_v1",
    "LAST_TOKEN_SELECT": "exact_index_select_v1",
    "MATMUL": "bf16_bf16_fp32_sequential_rne_v1",
    "RMS_NORM": "qwen3_rmsnorm_fp32_bf16_v1",
    "ROPE": "qwen3_rope_fp32_bf16_v1",
    "SILU_MUL": "qwen3_silu_mul_bf16_v1",
    "STATE_COMMIT": "bf16_byte_preserving_state_v1",
}
EXPECTED_KIND_COUNTS = {
    "ADD": 72,
    "ATTENTION": 36,
    "EMBEDDING_LOOKUP": 1,
    "KV_PREPARE": 36,
    "LAST_TOKEN_SELECT": 1,
    "MATMUL": 253,
    "RMS_NORM": 145,
    "ROPE": 36,
    "SILU_MUL": 36,
    "STATE_COMMIT": 1,
}
EVIDENCE_ROLES_BY_KIND = {
    "ADD": ("layer",),
    "ATTENTION": ("attention",),
    "EMBEDDING_LOOKUP": ("qkv",),
    "KV_PREPARE": ("attention",),
    "LAST_TOKEN_SELECT": ("final_output",),
    "MATMUL": ("final_output", "layer", "qkv"),
    "RMS_NORM": ("final_output", "layer", "qkv"),
    "ROPE": ("qkv",),
    "SILU_MUL": ("layer",),
    "STATE_COMMIT": ("attention",),
}
EVIDENCE_CONTRACTS = {
    "attention": (
        "bf16_byte_preserving_state_v1",
        "qwen3_gqa_fp32_softmax_bf16_v1",
    ),
    "final_output": (
        "bf16_bf16_fp32_sequential_rne_v1",
        "exact_index_select_v1",
        "qwen3_rmsnorm_fp32_bf16_v1",
    ),
    "layer": (
        "bf16_add_rne_v1",
        "bf16_payload_lookup_v1",
        "bf16_bf16_fp32_sequential_rne_v1",
        "qwen3_rmsnorm_fp32_bf16_v1",
        "qwen3_silu_mul_bf16_v1",
    ),
    "qkv": (
        "bf16_payload_lookup_v1",
        "bf16_bf16_fp32_sequential_rne_v1",
        "qwen3_rmsnorm_fp32_bf16_v1",
        "qwen3_rope_fp32_bf16_v1",
    ),
}


class QwenFullModelSemanticError(ArtifactError):
    """Raised when complete Qwen semantic coverage cannot be proven."""


def _identified(body: Mapping[str, Any], field: str) -> dict[str, Any]:
    result = dict(body)
    result[field] = sha256_bytes(canonical_json_bytes(body))
    return result


def _canonical_payload(path: Path, label: str) -> tuple[str, int]:
    try:
        payload = Path(path).read_bytes()
    except OSError as exc:
        raise QwenFullModelSemanticError(f"cannot read {label}: {exc}") from exc
    digest, size = sha256_file(Path(path))
    if not payload.endswith(b"\n"):
        raise QwenFullModelSemanticError(f"{label} is not canonical JSON")
    return digest, size


def _tensor(model: ProductionModelGraph, tensor_id: str) -> ProductionTensor:
    tensor = model.tensor_by_id.get(tensor_id)
    if tensor is None:
        raise QwenFullModelSemanticError(f"tensor {tensor_id!r} is missing")
    return tensor


def _expect_tensor(
    tensor: ProductionTensor,
    *,
    dtype: str,
    role: str | None = None,
    rank: int | None = None,
) -> None:
    if (
        tensor.dtype != dtype
        or (role is not None and tensor.role != role)
        or (rank is not None and len(tensor.shape) != rank)
    ):
        raise QwenFullModelSemanticError(
            f"tensor {tensor.tensor_id!r} contract differs"
        )


def _runtime_symbol_maximum(model: ProductionModelGraph, symbol_id: str) -> int:
    symbol = model.symbol_by_id.get(symbol_id)
    if symbol is None:
        raise QwenFullModelSemanticError(f"dynamic row symbol {symbol_id!r} is missing")
    return symbol.maximum


def _context_capacity(model: ProductionModelGraph) -> int:
    symbol = model.symbol_by_id.get("context_capacity")
    if (
        symbol is None
        or symbol.binding != {"kind": "compile_time"}
        or symbol.minimum != symbol.maximum
        or symbol.default != symbol.maximum
        or symbol.multiple_of != symbol.maximum
        or not MIN_CONTEXT_CAPACITY <= symbol.maximum <= MAX_CONTEXT_CAPACITY
    ):
        raise QwenFullModelSemanticError(
            "Qwen compile-time context-capacity symbol differs"
        )
    return symbol.maximum


def _row_extent(
    model: ProductionModelGraph,
    tensor: ProductionTensor,
    *,
    kernel_width: int,
) -> int | dict[str, Any]:
    _expect_tensor(tensor, dtype="bf16", rank=3)
    batch, rows, storage_width = tensor.shape
    if batch != 1 or not isinstance(storage_width, int) or storage_width < 1:
        raise QwenFullModelSemanticError(
            f"tensor {tensor.tensor_id!r} is not a batch-one row tensor"
        )
    if storage_width % kernel_width:
        raise QwenFullModelSemanticError(
            f"tensor {tensor.tensor_id!r} width is not divisible by kernel width"
        )
    multiplier = storage_width // kernel_width
    if isinstance(rows, int):
        return rows * multiplier
    if rows != "span_tokens":
        raise QwenFullModelSemanticError(
            f"tensor {tensor.tensor_id!r} does not use the span_tokens row symbol"
        )
    maximum = _runtime_symbol_maximum(model, rows) * multiplier
    return {"maximum": maximum, "multiplier": multiplier, "symbol": rows}


def _operation_ids_sha256(operations: Sequence[ProductionOperation]) -> str:
    return sha256_bytes(
        canonical_json_bytes([operation.operation_id for operation in operations])
    )


def _state_ids_sha256(model: ProductionModelGraph) -> str:
    return sha256_bytes(
        canonical_json_bytes([state.state_id for state in model.state_resources])
    )


def _validate_complete_graph(model: ProductionModelGraph) -> tuple[str, int]:
    if (
        model.model_id != MODEL_ID
        or model.numeric_profile != NUMERIC_PROFILE
        or len(model.operations) != OPERATION_COUNT
        or len(model.tensors) != TENSOR_COUNT
        or len(model.state_resources) != STATE_RESOURCE_COUNT
    ):
        raise QwenFullModelSemanticError("Qwen full-graph cardinality differs")
    expected_operation_ids = tuple(
        [f"node.{index:04d}" for index in range(OPERATION_COUNT - 1)] + ["state.commit"]
    )
    if tuple(operation.operation_id for operation in model.operations) != (
        expected_operation_ids
    ):
        raise QwenFullModelSemanticError("Qwen operation identity/order differs")
    expected_state_ids = tuple(
        f"kv.layer.{layer}" for layer in range(STATE_RESOURCE_COUNT)
    )
    if tuple(state.state_id for state in model.state_resources) != expected_state_ids:
        raise QwenFullModelSemanticError("Qwen state-resource identity/order differs")
    for state in model.state_resources:
        if (
            state.state_class != "kv_cache"
            or state.dtype != "bf16"
            or state.shape != (2, 1, KEY_VALUE_HEADS, "context_capacity", HEAD_DIM)
            or state.layout != "kvbhsd"
            or state.initialization != "zero"
        ):
            raise QwenFullModelSemanticError(
                f"state resource {state.state_id!r} contract differs"
            )
    context_capacity = _context_capacity(model)
    expected_symbols = [
        {
            "binding": {"kind": "compile_time"},
            "default": context_capacity,
            "id": "context_capacity",
            "maximum": context_capacity,
            "minimum": context_capacity,
            "multiple_of": context_capacity,
        },
        {
            "binding": {"field": "position_end", "kind": "request"},
            "default": 1,
            "id": "position_end",
            "maximum": context_capacity,
            "minimum": 1,
            "multiple_of": 1,
        },
        {
            "binding": {"field": "position_start", "kind": "request"},
            "default": 0,
            "id": "position_start",
            "maximum": context_capacity - 1,
            "minimum": 0,
            "multiple_of": 1,
        },
        {
            "binding": {"field": "span_tokens", "kind": "request"},
            "default": 1,
            "id": "span_tokens",
            "maximum": context_capacity,
            "minimum": 1,
            "multiple_of": 1,
        },
    ]
    if [symbol.to_dict() for symbol in model.symbols] != expected_symbols:
        raise QwenFullModelSemanticError("Qwen runtime-symbol bounds differ")
    counts = Counter(operation.kind for operation in model.operations)
    if dict(sorted(counts.items())) != EXPECTED_KIND_COUNTS:
        raise QwenFullModelSemanticError("Qwen operation-kind coverage differs")
    for operation in model.operations:
        expected_contract = CONTRACT_BY_KIND.get(operation.kind)
        if (
            expected_contract is None
            or operation.numeric_contract != expected_contract
            or operation.phases != ("prefill", "decode")
            or operation.predicate != {"kind": "always"}
        ):
            raise QwenFullModelSemanticError(
                f"operation {operation.operation_id!r} semantic contract differs"
            )
    role_counts = Counter(tensor.role for tensor in model.tensors)
    if role_counts != {
        "activation": 652,
        "input": 1,
        "output": 1,
        "weight": 399,
    }:
        raise QwenFullModelSemanticError("Qwen tensor-role coverage differs")
    bound = [tensor for tensor in model.tensors if tensor.binding is not None]
    if len(bound) != 399 or any(tensor.role != "weight" for tensor in bound):
        raise QwenFullModelSemanticError("Qwen checkpoint-binding coverage differs")
    checkpoint_lock_ids = {
        tensor.binding.checkpoint_lock_id
        for tensor in bound
        if tensor.binding is not None
    }
    if len(checkpoint_lock_ids) != 1:
        raise QwenFullModelSemanticError("Qwen graph checkpoint-lock identities differ")

    expected_state_ids = tuple(
        f"kv.layer.{layer}" for layer in range(STATE_RESOURCE_COUNT)
    )
    common_entrypoint = {
        "inputs": ("input.token_ids",),
        "outputs": ("output.committed_logits",),
        "states": expected_state_ids,
    }
    prefill_predicate = {
        "kind": "all",
        "terms": [
            {
                "kind": "affine",
                "operator": "eq",
                "terms": [
                    {"coefficient": 1, "symbol": "position_end"},
                    {"coefficient": -1, "symbol": "position_start"},
                    {"coefficient": -1, "symbol": "span_tokens"},
                ],
                "value": 0,
            },
            {
                "kind": "compare",
                "operator": "le",
                "symbol": "position_end",
                "value": context_capacity,
            },
        ],
    }
    if len(model.entrypoints) != 2:
        raise QwenFullModelSemanticError("Qwen entrypoint coverage differs")
    prefill, decode = model.entrypoints
    if (
        prefill.phase != "prefill"
        or prefill.inputs != common_entrypoint["inputs"]
        or prefill.outputs != common_entrypoint["outputs"]
        or prefill.states != common_entrypoint["states"]
        or prefill.predicate != prefill_predicate
        or decode.phase != "decode"
        or decode.inputs != common_entrypoint["inputs"]
        or decode.outputs != common_entrypoint["outputs"]
        or decode.states != common_entrypoint["states"]
        or decode.predicate
        != {
            **prefill_predicate,
            "terms": [
                *prefill_predicate["terms"],
                {
                    "kind": "compare",
                    "operator": "eq",
                    "symbol": "span_tokens",
                    "value": 1,
                },
            ],
        }
    ):
        raise QwenFullModelSemanticError("Qwen dynamic request boundary differs")

    actions_by_state: dict[str, list[str]] = defaultdict(list)
    for operation in model.operations:
        for effect in operation.effects:
            actions_by_state[effect.state_id].append(effect.action)
    if set(actions_by_state) != set(expected_state_ids):
        raise QwenFullModelSemanticError("Qwen state-effect coverage differs")
    expected_actions = ["read_committed", "prepare", "read_prepared", "commit"]
    if any(actions != expected_actions for actions in actions_by_state.values()):
        raise QwenFullModelSemanticError("Qwen state transaction sequence differs")
    terminal = model.operations[-1]
    if (
        terminal.kind != "STATE_COMMIT"
        or terminal.operation_id != "state.commit"
        or tuple(effect.state_id for effect in terminal.effects) != expected_state_ids
        or any(effect.action != "commit" for effect in terminal.effects)
    ):
        raise QwenFullModelSemanticError("Qwen terminal atomic commit differs")
    return checkpoint_lock_ids.pop(), context_capacity


def _load_qualification_evidence(
    *,
    qkv_path: Path,
    attention_path: Path,
    layer_path: Path,
    final_output_path: Path,
    graph_id: str,
) -> tuple[list[dict[str, Any]], str]:
    try:
        loaded = {
            "attention": load_attention_qualification(Path(attention_path)),
            "final_output": load_qwen_final_output_qualification(
                Path(final_output_path)
            ),
            "layer": load_layer_qualification(Path(layer_path)),
            "qkv": load_qkv_qualification(Path(qkv_path)),
        }
    except ArtifactError as exc:
        raise QwenFullModelSemanticError(
            f"Qwen qualification evidence admission failed: {exc}"
        ) from exc
    paths = {
        "attention": Path(attention_path),
        "final_output": Path(final_output_path),
        "layer": Path(layer_path),
        "qkv": Path(qkv_path),
    }
    checkpoint_ids = {
        report["checkpoint_lock_id"]
        for role, report in loaded.items()
        if role in {"final_output", "layer", "qkv"}
    }
    if len(checkpoint_ids) != 1:
        raise QwenFullModelSemanticError(
            "Qwen qualification checkpoint identities differ"
        )
    if loaded["final_output"].get("graph_id") != graph_id:
        raise QwenFullModelSemanticError(
            "final-output qualification graph identity differs"
        )
    records: list[dict[str, Any]] = []
    for role in sorted(loaded):
        report = loaded[role]
        observed_contracts: tuple[str, ...]
        if role == "attention":
            observed_contracts = tuple(
                sorted((report["numeric_contract"], report["state_contract"]))
            )
        else:
            observed_contracts = tuple(report["numeric_contracts"])
        if observed_contracts != EVIDENCE_CONTRACTS[role]:
            raise QwenFullModelSemanticError(
                f"{role} qualification numeric-contract coverage differs"
            )
        payload_sha256, size_bytes = _canonical_payload(
            paths[role], f"{role} qualification"
        )
        records.append(
            {
                "covered_numeric_contracts": list(observed_contracts),
                "payload_sha256": payload_sha256,
                "report_id": report["report_id"],
                "role": role,
                "schema": report["schema"],
                "size_bytes": size_bytes,
            }
        )
    return records, checkpoint_ids.pop()


def _validate_capability(
    capability: ProductionCapability, context_capacity: int
) -> None:
    required_contracts = set(CONTRACT_BY_KIND.values()) - {"bf16_payload_lookup_v1"}
    if (
        (capability.command_abi_major, capability.command_abi_minor) != (2, 5)
        or capability.vector_engine is None
        or capability.state_engine is None
        or capability.vector_engine.max_attention_context_tokens != context_capacity
        or capability.vector_engine.max_rope_positions != context_capacity
        or capability.state_engine.max_resources_per_transaction < STATE_RESOURCE_COUNT
        or not required_contracts <= set(capability.qualified_numeric_contracts)
        or capability.hbm.external_at_130nm_boundary is not True
    ):
        raise QwenFullModelSemanticError(
            "development capability does not cover Qwen neutral semantics"
        )


def _base_kernel(operation: ProductionOperation) -> dict[str, Any]:
    return {
        "index": operation.index,
        "inputs": list(operation.inputs),
        "kind": operation.kind,
        "numeric_contract": operation.numeric_contract,
        "outputs": list(operation.outputs),
        "source_operation_id": operation.operation_id,
    }


def _operation_layer(operation: ProductionOperation) -> int | None:
    if 1 <= operation.index <= 612:
        return (operation.index - 1) // 17
    return None


def _expect_attributes(
    operation: ProductionOperation,
    expected: Mapping[str, Any],
) -> None:
    if operation.attributes != expected:
        raise QwenFullModelSemanticError(
            f"operation {operation.operation_id!r} source attributes differ"
        )


def _validate_operation_effects(operation: ProductionOperation) -> None:
    layer = _operation_layer(operation)
    if operation.kind == "KV_PREPARE" and layer is not None:
        state_id = f"kv.layer.{layer}"
        expected = (("read_committed", state_id), ("prepare", state_id))
    elif operation.kind == "ATTENTION" and layer is not None:
        expected = (("read_prepared", f"kv.layer.{layer}"),)
    elif operation.kind == "STATE_COMMIT":
        expected = tuple(
            ("commit", f"kv.layer.{layer}") for layer in range(STATE_RESOURCE_COUNT)
        )
    else:
        expected = ()
    observed = tuple((effect.action, effect.state_id) for effect in operation.effects)
    if observed != expected:
        raise QwenFullModelSemanticError(
            f"operation {operation.operation_id!r} state effects differ"
        )


def _embedding_kernel(
    model: ProductionModelGraph, operation: ProductionOperation
) -> dict[str, Any]:
    if len(operation.inputs) != 2 or len(operation.outputs) != 1:
        raise QwenFullModelSemanticError("embedding operation arity differs")
    token_ids = _tensor(model, operation.inputs[0])
    weight = _tensor(model, operation.inputs[1])
    output = _tensor(model, operation.outputs[0])
    _expect_tensor(token_ids, dtype="i64", role="input", rank=2)
    _expect_tensor(weight, dtype="bf16", role="weight", rank=2)
    if token_ids.shape != (1, "span_tokens"):
        raise QwenFullModelSemanticError("embedding token shape differs")
    if weight.shape != (VOCABULARY_SIZE, HIDDEN_WIDTH):
        raise QwenFullModelSemanticError("embedding weight shape differs")
    _expect_attributes(
        operation,
        {
            "source_kind": "TOKEN_EMBEDDING_LOOKUP",
            "weight_ids": [weight.tensor_id],
        },
    )
    rows = _row_extent(model, output, kernel_width=HIDDEN_WIDTH)
    return {
        **_base_kernel(operation),
        "attributes": {
            "index_conversion": "checked_nonnegative_u32",
            "index_dtype": "u32",
            "output_dtype": "bf16",
            "source_index_dtype": "i64",
            "source_index_max_exclusive": VOCABULARY_SIZE,
            "source_index_min": 0,
        },
        "shape": {"rows": rows, "width": HIDDEN_WIDTH},
    }


def _matmul_kernel(
    model: ProductionModelGraph, operation: ProductionOperation
) -> dict[str, Any]:
    if len(operation.inputs) != 2 or len(operation.outputs) != 1:
        raise QwenFullModelSemanticError(
            f"matrix operation {operation.operation_id!r} arity differs"
        )
    source = _tensor(model, operation.inputs[0])
    weight = _tensor(model, operation.inputs[1])
    output = _tensor(model, operation.outputs[0])
    _expect_tensor(source, dtype="bf16", rank=3)
    _expect_tensor(weight, dtype="bf16", role="weight", rank=2)
    _expect_tensor(output, dtype="bf16", rank=3)
    expected_attributes: dict[str, Any] = {
        "source_kind": "LINEAR",
        "transpose_weight": True,
        "weight_ids": [weight.tensor_id],
    }
    layer = _operation_layer(operation)
    if layer is not None:
        expected_attributes["layer"] = layer
    _expect_attributes(operation, expected_attributes)
    width, reduction_width = weight.shape
    if (
        not isinstance(width, int)
        or not isinstance(reduction_width, int)
        or source.shape[-1] != reduction_width
        or output.shape[-1] != width
        or source.shape[:2] != output.shape[:2]
    ):
        raise QwenFullModelSemanticError(
            f"matrix operation {operation.operation_id!r} shape differs"
        )
    rows = _row_extent(model, output, kernel_width=width)
    return {
        **_base_kernel(operation),
        "attributes": {
            "accumulator_dtype": "fp32",
            "input_dtype": "bf16",
            "output_dtype": "bf16",
            "output_rounding": "rne",
            "reduction_order": "strictly_increasing_k",
            "transpose_weight": True,
        },
        "shape": {
            "reduction_width": reduction_width,
            "rows": rows,
            "width": width,
        },
    }


def _rmsnorm_kernel(
    model: ProductionModelGraph, operation: ProductionOperation
) -> dict[str, Any]:
    if len(operation.inputs) != 2 or len(operation.outputs) != 1:
        raise QwenFullModelSemanticError(
            f"RMSNorm operation {operation.operation_id!r} arity differs"
        )
    source = _tensor(model, operation.inputs[0])
    weight = _tensor(model, operation.inputs[1])
    output = _tensor(model, operation.outputs[0])
    _expect_tensor(source, dtype="bf16", rank=3)
    _expect_tensor(output, dtype="bf16", rank=3)
    width = operation.attributes.get("normalization_width")
    if not isinstance(width, int):
        raise QwenFullModelSemanticError(
            f"RMSNorm operation {operation.operation_id!r} width differs"
        )
    expected_attributes = {
        "epsilon": 1e-6,
        "normalization_width": width,
        "source_kind": "RMS_NORM",
        "weight_ids": [weight.tensor_id],
    }
    layer = _operation_layer(operation)
    if layer is not None:
        expected_attributes["layer"] = layer
    _expect_attributes(operation, expected_attributes)
    if weight.shape != (width,) or source.shape != output.shape:
        raise QwenFullModelSemanticError(
            f"RMSNorm operation {operation.operation_id!r} attributes differ"
        )
    _expect_tensor(weight, dtype="bf16", role="weight", rank=1)
    rows = _row_extent(model, output, kernel_width=width)
    return {
        **_base_kernel(operation),
        "attributes": {
            "epsilon_binary32_code": 897988541,
            "final_weight_product": "bf16_multiply_then_bf16_rne",
            "normalized_boundary": "bf16_rne_before_weight",
            "reduction_order": "canonical_balanced_binary32_tree",
            "rsqrt": "correctly_rounded_binary32_rne",
        },
        "shape": {"rows": rows, "width": width},
    }


def _add_kernel(
    model: ProductionModelGraph, operation: ProductionOperation
) -> dict[str, Any]:
    if len(operation.inputs) != 2 or len(operation.outputs) != 1:
        raise QwenFullModelSemanticError(
            f"add operation {operation.operation_id!r} arity differs"
        )
    left = _tensor(model, operation.inputs[0])
    right = _tensor(model, operation.inputs[1])
    output = _tensor(model, operation.outputs[0])
    _expect_tensor(left, dtype="bf16", rank=3)
    _expect_tensor(right, dtype="bf16", rank=3)
    _expect_tensor(output, dtype="bf16", rank=3)
    layer = _operation_layer(operation)
    _expect_attributes(
        operation,
        {"layer": layer, "source_kind": "RESIDUAL_ADD"},
    )
    if left.shape != right.shape or left.shape != output.shape:
        raise QwenFullModelSemanticError(
            f"add operation {operation.operation_id!r} shape differs"
        )
    width = output.shape[-1]
    if not isinstance(width, int):
        raise QwenFullModelSemanticError("add output width is not static")
    rows = _row_extent(model, output, kernel_width=width)
    return {
        **_base_kernel(operation),
        "attributes": {
            "addition": "binary32_rne",
            "input_dtype": "bf16",
            "output_dtype": "bf16",
            "output_rounding": "rne",
            "zero_canonicalization": "positive",
        },
        "shape": {"rows": rows, "width": width},
    }


def _silu_kernel(
    model: ProductionModelGraph, operation: ProductionOperation
) -> dict[str, Any]:
    if len(operation.inputs) != 2 or len(operation.outputs) != 1:
        raise QwenFullModelSemanticError(
            f"SiLU operation {operation.operation_id!r} arity differs"
        )
    gate = _tensor(model, operation.inputs[0])
    up = _tensor(model, operation.inputs[1])
    output = _tensor(model, operation.outputs[0])
    _expect_tensor(gate, dtype="bf16", rank=3)
    _expect_tensor(up, dtype="bf16", rank=3)
    _expect_tensor(output, dtype="bf16", rank=3)
    layer = _operation_layer(operation)
    _expect_attributes(operation, {"layer": layer, "source_kind": "SILU_MUL"})
    if (
        gate.shape != up.shape
        or gate.shape != output.shape
        or output.shape[-1] != INTERMEDIATE_WIDTH
    ):
        raise QwenFullModelSemanticError(
            f"SiLU operation {operation.operation_id!r} shape differs"
        )
    rows = _row_extent(model, output, kernel_width=INTERMEDIATE_WIDTH)
    return {
        **_base_kernel(operation),
        "attributes": {
            "activation_boundary": "bf16_rne_before_up_multiply",
            "exponential": "correctly_rounded_binary32_rne",
            "input_dtype": "bf16",
            "output_dtype": "bf16",
            "output_rounding": "rne",
            "sigmoid": "stable_sign_selected_binary32",
            "zero_canonicalization": "positive",
        },
        "shape": {"rows": rows, "width": INTERMEDIATE_WIDTH},
    }


def _rope_kernel(
    model: ProductionModelGraph, operation: ProductionOperation
) -> dict[str, Any]:
    context_capacity = _context_capacity(model)
    if len(operation.inputs) != 2 or len(operation.outputs) != 2:
        raise QwenFullModelSemanticError(
            f"RoPE operation {operation.operation_id!r} arity differs"
        )
    q_input = _tensor(model, operation.inputs[0])
    k_input = _tensor(model, operation.inputs[1])
    q_output = _tensor(model, operation.outputs[0])
    k_output = _tensor(model, operation.outputs[1])
    for tensor in (q_input, k_input, q_output, k_output):
        _expect_tensor(tensor, dtype="bf16", rank=3)
    layer = _operation_layer(operation)
    _expect_attributes(
        operation,
        {
            "head_dim": HEAD_DIM,
            "layer": layer,
            "position_symbol": "position_start",
            "source_kind": "ROPE",
        },
    )
    if (
        q_input.shape != q_output.shape
        or k_input.shape != k_output.shape
        or q_input.shape[-1] != QUERY_HEADS * HEAD_DIM
        or k_input.shape[-1] != KEY_VALUE_HEADS * HEAD_DIM
    ):
        raise QwenFullModelSemanticError(
            f"RoPE operation {operation.operation_id!r} shape differs"
        )
    return {
        **_base_kernel(operation),
        "attributes": {
            "coefficient_layout": "cos_head_dim_then_sin_head_dim",
            "key_value_heads": KEY_VALUE_HEADS,
            "max_positions": context_capacity,
            "position_count_symbol": "span_tokens",
            "position_progression": "consecutive_from_start",
            "position_symbol": "position_start",
            "query_heads": QUERY_HEADS,
            "rotation": "concat_neg_second_half_first_half",
        },
        "shape": {"head_dim": HEAD_DIM},
    }


def _prepare_kernel(
    model: ProductionModelGraph, operation: ProductionOperation
) -> dict[str, Any]:
    context_capacity = _context_capacity(model)
    if len(operation.inputs) != 2 or len(operation.outputs) != 1:
        raise QwenFullModelSemanticError(
            f"KV prepare operation {operation.operation_id!r} arity differs"
        )
    key = _tensor(model, operation.inputs[0])
    value = _tensor(model, operation.inputs[1])
    handle = _tensor(model, operation.outputs[0])
    _expect_tensor(key, dtype="bf16", rank=3)
    _expect_tensor(value, dtype="bf16", rank=3)
    resources = [
        effect.state_id for effect in operation.effects if effect.action == "prepare"
    ]
    layer = _operation_layer(operation)
    _expect_attributes(operation, {"layer": layer, "source_kind": "KV_COMMIT"})
    if (
        len(resources) != 1
        or key.shape != value.shape
        or key.shape[-1] != KEY_VALUE_HEADS * HEAD_DIM
        or handle.dtype != "u32"
        or handle.shape != (1,)
    ):
        raise QwenFullModelSemanticError(
            f"KV prepare operation {operation.operation_id!r} contract differs"
        )
    return {
        **_base_kernel(operation),
        "attributes": {
            "append_position_symbol": "position_start",
            "generation_check": "exact_expected_generation",
            "state_resource": resources[0],
            "transaction_scope": "model_forward_request",
            "visibility": "transaction_private_until_commit",
        },
        "shape": {
            "head_dim": HEAD_DIM,
            "key_value_heads": KEY_VALUE_HEADS,
            "max_context_tokens": context_capacity,
            "tokens_symbol": "span_tokens",
        },
    }


def _attention_kernel(
    model: ProductionModelGraph, operation: ProductionOperation
) -> dict[str, Any]:
    context_capacity = _context_capacity(model)
    if len(operation.inputs) != 2 or len(operation.outputs) != 1:
        raise QwenFullModelSemanticError(
            f"attention operation {operation.operation_id!r} arity differs"
        )
    query = _tensor(model, operation.inputs[0])
    handle = _tensor(model, operation.inputs[1])
    output = _tensor(model, operation.outputs[0])
    _expect_tensor(query, dtype="bf16", rank=3)
    _expect_tensor(output, dtype="bf16", rank=3)
    layer = _operation_layer(operation)
    _expect_attributes(
        operation,
        {
            "head_dim": HEAD_DIM,
            "key_value_heads": KEY_VALUE_HEADS,
            "layer": layer,
            "query_heads": QUERY_HEADS,
            "scale_denominator_sqrt": HEAD_DIM,
            "source_kind": "GQA_CAUSAL_ATTENTION",
        },
    )
    if (
        query.shape != output.shape
        or query.shape[-1] != QUERY_HEADS * HEAD_DIM
        or handle.dtype != "u32"
    ):
        raise QwenFullModelSemanticError(
            f"attention operation {operation.operation_id!r} contract differs"
        )
    return {
        **_base_kernel(operation),
        "attributes": {
            "causal_mask_bf16_code": 0xFF7F,
            "prepared_state_visibility": "transaction_private",
            "probability_dtype": "bf16",
            "query_heads_per_key_value_head": QUERY_HEADS // KEY_VALUE_HEADS,
            "scale_bf16_code": 0x3DB5,
            "score_reduction_order": "strictly_increasing_head_dimension",
            "softmax_compute_dtype": "fp32",
            "softmax_reduction_lanes": 8,
            "value_reduction_order": "strictly_increasing_context",
        },
        "shape": {
            "head_dim": HEAD_DIM,
            "key_value_heads": KEY_VALUE_HEADS,
            "max_context_tokens": context_capacity,
            "query_heads": QUERY_HEADS,
            "query_tokens_symbol": "span_tokens",
        },
    }


def _selection_kernel(
    model: ProductionModelGraph, operation: ProductionOperation
) -> dict[str, Any]:
    context_capacity = _context_capacity(model)
    if len(operation.inputs) != 1 or len(operation.outputs) != 1:
        raise QwenFullModelSemanticError("last-token selection arity differs")
    source = _tensor(model, operation.inputs[0])
    output = _tensor(model, operation.outputs[0])
    _expect_tensor(source, dtype="bf16", rank=3)
    _expect_tensor(output, dtype="bf16", rank=3)
    if source.shape != (1, "span_tokens", HIDDEN_WIDTH) or output.shape != (
        1,
        1,
        HIDDEN_WIDTH,
    ):
        raise QwenFullModelSemanticError("last-token selection shape differs")
    _expect_attributes(operation, {"source_kind": "LAST_TOKEN_SELECT"})
    return {
        **_base_kernel(operation),
        "attributes": {
            "index_dtype": "u32",
            "input_dtype": "bf16",
            "output_dtype": "bf16",
            "selection": "last_logical_row",
        },
        "shape": {
            "maximum_rows": context_capacity,
            "rows_symbol": "span_tokens",
            "width": HIDDEN_WIDTH,
        },
    }


def _commit_kernel(
    model: ProductionModelGraph, operation: ProductionOperation
) -> dict[str, Any]:
    if len(operation.inputs) != 1 or len(operation.outputs) != 1:
        raise QwenFullModelSemanticError("state commit arity differs")
    source = _tensor(model, operation.inputs[0])
    output = _tensor(model, operation.outputs[0])
    _expect_tensor(source, dtype="bf16", rank=3)
    _expect_tensor(output, dtype="bf16", rank=3)
    resources = tuple(effect.state_id for effect in operation.effects)
    _expect_attributes(operation, {"atomic_state_count": STATE_RESOURCE_COUNT})
    if (
        source.shape != (1, 1, VOCABULARY_SIZE)
        or output.shape != source.shape
        or len(resources) != STATE_RESOURCE_COUNT
        or any(effect.action != "commit" for effect in operation.effects)
    ):
        raise QwenFullModelSemanticError("state commit contract differs")
    return {
        **_base_kernel(operation),
        "attributes": {
            "atomic": True,
            "coverage": "complete_operation",
            "generation_increment": 1,
            "source_atomic_state_count": STATE_RESOURCE_COUNT,
            "transaction_scope": "model_forward_request",
        },
        "shape": {"atomic_state_count": STATE_RESOURCE_COUNT},
        "state_resources": list(resources),
    }


def _kernel(
    model: ProductionModelGraph, operation: ProductionOperation
) -> dict[str, Any]:
    builders = {
        "ADD": _add_kernel,
        "ATTENTION": _attention_kernel,
        "EMBEDDING_LOOKUP": _embedding_kernel,
        "KV_PREPARE": _prepare_kernel,
        "LAST_TOKEN_SELECT": _selection_kernel,
        "MATMUL": _matmul_kernel,
        "RMS_NORM": _rmsnorm_kernel,
        "ROPE": _rope_kernel,
        "SILU_MUL": _silu_kernel,
        "STATE_COMMIT": _commit_kernel,
    }
    try:
        _validate_operation_effects(operation)
        return builders[operation.kind](model, operation)
    except KeyError as exc:  # pragma: no cover - complete-graph validation guards this.
        raise QwenFullModelSemanticError(
            f"operation kind {operation.kind!r} has no neutral lowering"
        ) from exc


def build_qwen_full_model_semantics(
    *,
    model_graph_path: Path,
    capability_path: Path,
    qkv_qualification_path: Path,
    attention_qualification_path: Path,
    layer_qualification_path: Path,
    final_output_qualification_path: Path,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Build complete semantic coverage and one 617-kernel neutral artifact."""

    try:
        model = load_production_model_graph(Path(model_graph_path))
        capability = load_production_capability(Path(capability_path))
    except (ProductionModelGraphError, ProductionCapabilityError) as exc:
        raise QwenFullModelSemanticError(
            f"Qwen full-model semantic source admission failed: {exc}"
        ) from exc
    graph_checkpoint_lock_id, context_capacity = _validate_complete_graph(model)
    _validate_capability(capability, context_capacity)
    kernels = [_kernel(model, operation) for operation in model.operations]
    if (
        len(kernels) != OPERATION_COUNT
        or [kernel["index"] for kernel in kernels] != list(range(OPERATION_COUNT))
        or [kernel["source_operation_id"] for kernel in kernels]
        != [operation.operation_id for operation in model.operations]
    ):
        raise QwenFullModelSemanticError("complete neutral-kernel coverage differs")
    evidence, checkpoint_lock_id = _load_qualification_evidence(
        qkv_path=Path(qkv_qualification_path),
        attention_path=Path(attention_qualification_path),
        layer_path=Path(layer_qualification_path),
        final_output_path=Path(final_output_qualification_path),
        graph_id=model.graph_id,
    )
    if checkpoint_lock_id != graph_checkpoint_lock_id:
        raise QwenFullModelSemanticError(
            "Qwen graph and qualification checkpoint identities differ"
        )
    report_id_by_role = {record["role"]: record["report_id"] for record in evidence}
    kind_counts = Counter(operation.kind for operation in model.operations)
    families = [
        {
            "kind": kind,
            "numeric_contract": CONTRACT_BY_KIND[kind],
            "operation_count": kind_counts[kind],
            "qualification_report_ids": [
                report_id_by_role[role] for role in EVIDENCE_ROLES_BY_KIND[kind]
            ],
            "status": "covered",
        }
        for kind in sorted(CONTRACT_BY_KIND)
    ]
    effect_counts = Counter(
        effect.action for operation in model.operations for effect in operation.effects
    )
    role_counts = Counter(tensor.role for tensor in model.tensors)
    coverage_body: dict[str, Any] = {
        "capability": {
            "capability_id": capability.capability_id,
            "command_abi": {
                "major": capability.command_abi_major,
                "minor": capability.command_abi_minor,
            },
            "external_hbm_at_130nm_boundary": True,
            "max_resources_per_transaction": (
                capability.state_engine.max_resources_per_transaction
                if capability.state_engine is not None
                else 0
            ),
        },
        "checkpoint_lock_id": checkpoint_lock_id,
        "claim_boundary": {
            "complete_graph_operation_coverage": True,
            "complete_graph_state_contract_coverage": True,
            "complete_neutral_kernel_lowering": True,
            "full_model_execution": False,
            "physical_plan": False,
            "timing_or_performance": False,
        },
        "graph_id": model.graph_id,
        "kernel_count": len(model.operations),
        "model_id": model.model_id,
        "numeric_profile": model.numeric_profile,
        "operation_count": len(model.operations),
        "operation_ids_sha256": _operation_ids_sha256(model.operations),
        "operator_families": families,
        "qualification_evidence": evidence,
        "schema": COVERAGE_SCHEMA,
        "state_coverage": {
            "commit_effect_count": effect_counts["commit"],
            "prepare_effect_count": effect_counts["prepare"],
            "read_committed_effect_count": effect_counts["read_committed"],
            "read_prepared_effect_count": effect_counts["read_prepared"],
            "resource_count": len(model.state_resources),
            "resource_ids_sha256": _state_ids_sha256(model),
            "terminal_commit_operation_id": model.operations[-1].operation_id,
        },
        "status": "pass",
        "tensor_coverage": {
            "activation_count": role_counts["activation"],
            "checkpoint_bound_weight_count": sum(
                tensor.binding is not None for tensor in model.tensors
            ),
            "input_count": role_counts["input"],
            "output_count": role_counts["output"],
            "tensor_count": len(model.tensors),
            "weight_count": role_counts["weight"],
        },
        "unknown_operation_count": 0,
        "unknown_operations": [],
    }
    coverage = _identified(coverage_body, "report_id")
    kernel_body = {
        "graph_id": model.graph_id,
        "kernels": kernels,
        "qualification_report_id": coverage["report_id"],
        "schema": KERNEL_SCHEMA,
    }
    kernel_ir = _identified(kernel_body, "kernel_ir_id")
    encoded = canonical_json_bytes(kernel_ir)
    for forbidden in (
        b"HBM_",
        b"ROM_",
        b"SRAM_",
        b"bank_id",
        b"command_opcode",
        b"physical_address",
    ):
        if forbidden in encoded:
            raise QwenFullModelSemanticError(
                "backend-specific state leaked into complete neutral Kernel IR"
            )
    return coverage, kernel_ir


__all__ = [
    "CONTRACT_BY_KIND",
    "COVERAGE_SCHEMA",
    "EXPECTED_KIND_COUNTS",
    "KERNEL_SCHEMA",
    "QwenFullModelSemanticError",
    "build_qwen_full_model_semantics",
]
