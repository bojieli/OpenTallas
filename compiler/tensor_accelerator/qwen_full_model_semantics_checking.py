"""Independent inverse checking for complete Qwen neutral-kernel coverage.

The checker deliberately does not import the semantic lowering implementation.
It rereads the Model Graph IR and capability, authenticates emitted artifacts,
and independently derives operation, shape, state, and neutrality obligations.
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any, Mapping

from .common import (
    ArtifactError,
    canonical_json_bytes,
    exact_keys,
    load_strict_json,
    require_int,
    require_sha256,
    sha256_bytes,
    sha256_file,
)
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


CHECK_SCHEMA = "opentallas.tensor_accelerator.qwen_full_model_semantic_check.v1"
COVERAGE_SCHEMA = "opentallas.tensor_accelerator.qwen_full_model_semantic_coverage.v1"
KERNEL_SCHEMA = "opentallas.production_tensor_kernel_ir.v1"
OPERATION_COUNT = 617
TENSOR_COUNT = 1053
STATE_RESOURCE_COUNT = 36
MIN_CONTEXT_CAPACITY = 8000
MAX_CONTEXT_CAPACITY = 40960
QUERY_HEADS = 32
KEY_VALUE_HEADS = 8
HEAD_DIM = 128
EXPECTED_COUNTS = {
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
EXPECTED_CONTRACTS = {
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
EXPECTED_QUALIFICATION_ROLES_BY_KIND = {
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
EXPECTED_QUALIFICATIONS = {
    "attention": {
        "contracts": (
            "bf16_byte_preserving_state_v1",
            "qwen3_gqa_fp32_softmax_bf16_v1",
        ),
        "schema": "opentallas.tensor_accelerator.attention_qualification.v1",
    },
    "final_output": {
        "contracts": (
            "bf16_bf16_fp32_sequential_rne_v1",
            "exact_index_select_v1",
            "qwen3_rmsnorm_fp32_bf16_v1",
        ),
        "schema": "opentallas.tensor_accelerator.qwen_final_output_qualification.v1",
    },
    "layer": {
        "contracts": (
            "bf16_add_rne_v1",
            "bf16_payload_lookup_v1",
            "bf16_bf16_fp32_sequential_rne_v1",
            "qwen3_rmsnorm_fp32_bf16_v1",
            "qwen3_silu_mul_bf16_v1",
        ),
        "schema": "opentallas.tensor_accelerator.layer_qualification.v1",
    },
    "qkv": {
        "contracts": (
            "bf16_payload_lookup_v1",
            "bf16_bf16_fp32_sequential_rne_v1",
            "qwen3_rmsnorm_fp32_bf16_v1",
            "qwen3_rope_fp32_bf16_v1",
        ),
        "schema": "opentallas.tensor_accelerator.qkv_qualification.v1",
    },
}


class QwenFullModelSemanticCheckError(ArtifactError):
    """Raised when emitted complete-graph semantic artifacts do not invert."""


def _load_canonical(path: Path, label: str) -> dict[str, Any]:
    try:
        payload = Path(path).read_bytes()
        value = load_strict_json(Path(path))
    except (OSError, ArtifactError) as exc:
        raise QwenFullModelSemanticCheckError(f"cannot load {label}: {exc}") from exc
    if payload != canonical_json_bytes(value):
        raise QwenFullModelSemanticCheckError(f"{label} is not canonical JSON")
    return value


def _identity(value: Mapping[str, Any], field: str, label: str) -> None:
    observed = require_sha256(value.get(field), f"{label}.{field}")
    expected = sha256_bytes(
        canonical_json_bytes({key: item for key, item in value.items() if key != field})
    )
    if observed != expected:
        raise QwenFullModelSemanticCheckError(f"{label} identity differs")


def _tensor(model: ProductionModelGraph, tensor_id: str) -> ProductionTensor:
    tensor = model.tensor_by_id.get(tensor_id)
    if tensor is None:
        raise QwenFullModelSemanticCheckError(f"tensor {tensor_id!r} is missing")
    return tensor


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
        raise QwenFullModelSemanticCheckError(
            "independent Qwen context-capacity symbol differs"
        )
    return symbol.maximum


def _row_extent(
    model: ProductionModelGraph,
    tensor: ProductionTensor,
    kernel_width: int,
) -> int | dict[str, Any]:
    if (
        tensor.dtype != "bf16"
        or len(tensor.shape) != 3
        or tensor.shape[0] != 1
        or not isinstance(tensor.shape[2], int)
        or tensor.shape[2] % kernel_width
    ):
        raise QwenFullModelSemanticCheckError(
            f"tensor {tensor.tensor_id!r} cannot define logical rows"
        )
    rows = tensor.shape[1]
    multiplier = tensor.shape[2] // kernel_width
    if isinstance(rows, int):
        return rows * multiplier
    if rows != "span_tokens":
        raise QwenFullModelSemanticCheckError(
            f"tensor {tensor.tensor_id!r} does not use the span_tokens row symbol"
        )
    symbol = model.symbol_by_id.get(rows)
    if symbol is None:
        raise QwenFullModelSemanticCheckError(
            f"tensor {tensor.tensor_id!r} has an unknown row symbol"
        )
    return {
        "maximum": symbol.maximum * multiplier,
        "multiplier": multiplier,
        "symbol": rows,
    }


def _operation_ids_sha256(model: ProductionModelGraph) -> str:
    return sha256_bytes(
        canonical_json_bytes([operation.operation_id for operation in model.operations])
    )


def _state_ids_sha256(model: ProductionModelGraph) -> str:
    return sha256_bytes(
        canonical_json_bytes([state.state_id for state in model.state_resources])
    )


def _check_model_contract(model: ProductionModelGraph) -> tuple[str, int]:
    expected_operation_ids = tuple(
        [f"node.{index:04d}" for index in range(OPERATION_COUNT - 1)] + ["state.commit"]
    )
    expected_state_ids = tuple(
        f"kv.layer.{layer}" for layer in range(STATE_RESOURCE_COUNT)
    )
    if (
        model.model_id != "qwen3-8b"
        or model.numeric_profile != "qwen3_bf16_gqa_target_v1"
        or len(model.operations) != OPERATION_COUNT
        or len(model.tensors) != TENSOR_COUNT
        or len(model.state_resources) != STATE_RESOURCE_COUNT
        or tuple(operation.operation_id for operation in model.operations)
        != expected_operation_ids
        or tuple(state.state_id for state in model.state_resources)
        != expected_state_ids
    ):
        raise QwenFullModelSemanticCheckError(
            "independent complete-graph identity/cardinality differs"
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
        raise QwenFullModelSemanticCheckError(
            "independent Qwen runtime-symbol bounds differ"
        )
    for state in model.state_resources:
        if (
            state.state_class != "kv_cache"
            or state.dtype != "bf16"
            or state.shape != (2, 1, KEY_VALUE_HEADS, "context_capacity", HEAD_DIM)
            or state.layout != "kvbhsd"
            or state.initialization != "zero"
        ):
            raise QwenFullModelSemanticCheckError(
                f"state resource {state.state_id!r} contract differs"
            )
    counts = dict(sorted(Counter(op.kind for op in model.operations).items()))
    if counts != EXPECTED_COUNTS:
        raise QwenFullModelSemanticCheckError(
            "independent Qwen operation-kind coverage differs"
        )
    for operation in model.operations:
        if (
            operation.numeric_contract != EXPECTED_CONTRACTS.get(operation.kind)
            or operation.phases != ("prefill", "decode")
            or operation.predicate != {"kind": "always"}
        ):
            raise QwenFullModelSemanticCheckError(
                f"operation {operation.operation_id!r} semantic contract differs"
            )
    role_counts = Counter(tensor.role for tensor in model.tensors)
    if role_counts != {
        "activation": 652,
        "input": 1,
        "output": 1,
        "weight": 399,
    }:
        raise QwenFullModelSemanticCheckError(
            "independent Qwen tensor-role coverage differs"
        )
    bound = [tensor for tensor in model.tensors if tensor.binding is not None]
    checkpoint_lock_ids = {
        tensor.binding.checkpoint_lock_id
        for tensor in bound
        if tensor.binding is not None
    }
    if (
        len(bound) != 399
        or any(tensor.role != "weight" for tensor in bound)
        or len(checkpoint_lock_ids) != 1
    ):
        raise QwenFullModelSemanticCheckError(
            "independent Qwen checkpoint-binding coverage differs"
        )
    actions_by_state: dict[str, list[str]] = {
        state_id: [] for state_id in expected_state_ids
    }
    for operation in model.operations:
        for effect in operation.effects:
            if effect.state_id not in actions_by_state:
                raise QwenFullModelSemanticCheckError(
                    "independent Qwen state-effect identity differs"
                )
            actions_by_state[effect.state_id].append(effect.action)
    expected_actions = ["read_committed", "prepare", "read_prepared", "commit"]
    if any(actions != expected_actions for actions in actions_by_state.values()):
        raise QwenFullModelSemanticCheckError(
            "independent Qwen state transaction sequence differs"
        )
    terminal = model.operations[-1]
    if (
        terminal.kind != "STATE_COMMIT"
        or terminal.operation_id != "state.commit"
        or tuple(effect.state_id for effect in terminal.effects) != expected_state_ids
        or any(effect.action != "commit" for effect in terminal.effects)
    ):
        raise QwenFullModelSemanticCheckError(
            "independent Qwen terminal atomic commit differs"
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
        raise QwenFullModelSemanticCheckError(
            "independent Qwen entrypoint coverage differs"
        )
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
        raise QwenFullModelSemanticCheckError(
            "independent Qwen dynamic request boundary differs"
        )
    for operation in model.operations:
        _check_source_operation_contract(model, operation)
    return checkpoint_lock_ids.pop(), context_capacity


def _check_capability_contract(
    capability: ProductionCapability, context_capacity: int
) -> None:
    required_contracts = set(EXPECTED_CONTRACTS.values()) - {"bf16_payload_lookup_v1"}
    vector = capability.vector_engine
    state = capability.state_engine
    if (
        capability.architecture != "opentallas-tensor-accelerator"
        or (capability.command_abi_major, capability.command_abi_minor) != (2, 5)
        or "qwen3-8b" not in capability.declared_model_profiles
        or vector is None
        or state is None
        or vector.max_attention_context_tokens != context_capacity
        or vector.max_rope_positions != context_capacity
        or vector.max_query_heads != QUERY_HEADS
        or vector.max_key_value_heads != KEY_VALUE_HEADS
        or vector.rope_head_dim != HEAD_DIM
        or vector.attention_head_dim != HEAD_DIM
        or vector.softmax_reduction_lanes != 8
        or state.max_resources_per_transaction < STATE_RESOURCE_COUNT
        or capability.hbm.external_at_130nm_boundary is not True
        or not required_contracts <= set(capability.qualified_numeric_contracts)
    ):
        raise QwenFullModelSemanticCheckError(
            "independent development capability contract differs"
        )


def _check_coverage(
    model: ProductionModelGraph,
    source_capability: ProductionCapability,
    checkpoint_lock_id: str,
    coverage: dict[str, Any],
) -> None:
    required = {
        "capability",
        "checkpoint_lock_id",
        "claim_boundary",
        "graph_id",
        "kernel_count",
        "model_id",
        "numeric_profile",
        "operation_count",
        "operation_ids_sha256",
        "operator_families",
        "qualification_evidence",
        "report_id",
        "schema",
        "state_coverage",
        "status",
        "tensor_coverage",
        "unknown_operation_count",
        "unknown_operations",
    }
    try:
        exact_keys(coverage, required, set(), "semantic coverage")
    except ArtifactError as exc:
        raise QwenFullModelSemanticCheckError(str(exc)) from exc
    _identity(coverage, "report_id", "semantic coverage")
    if (
        coverage.get("schema") != COVERAGE_SCHEMA
        or coverage.get("status") != "pass"
        or coverage.get("graph_id") != model.graph_id
        or coverage.get("model_id") != model.model_id
        or coverage.get("numeric_profile") != model.numeric_profile
        or coverage.get("operation_count") != len(model.operations)
        or coverage.get("kernel_count") != len(model.operations)
        or coverage.get("operation_ids_sha256") != _operation_ids_sha256(model)
        or coverage.get("unknown_operation_count") != 0
        or coverage.get("unknown_operations") != []
    ):
        raise QwenFullModelSemanticCheckError(
            "semantic coverage graph/operation boundary differs"
        )
    if coverage.get("checkpoint_lock_id") != checkpoint_lock_id:
        raise QwenFullModelSemanticCheckError(
            "semantic coverage checkpoint identity differs"
        )
    source_state = source_capability.state_engine
    if source_state is None:
        raise QwenFullModelSemanticCheckError(
            "semantic coverage capability lacks transactional state"
        )
    capability = coverage.get("capability")
    if (
        not isinstance(capability, dict)
        or capability.get("capability_id") != source_capability.capability_id
        or capability.get("command_abi")
        != {
            "major": source_capability.command_abi_major,
            "minor": source_capability.command_abi_minor,
        }
        or capability.get("external_hbm_at_130nm_boundary")
        is not source_capability.hbm.external_at_130nm_boundary
        or require_int(
            capability.get("max_resources_per_transaction"),
            "max_resources_per_transaction",
            minimum=STATE_RESOURCE_COUNT,
        )
        != source_state.max_resources_per_transaction
    ):
        raise QwenFullModelSemanticCheckError(
            "semantic coverage capability boundary differs"
        )
    claim = coverage.get("claim_boundary")
    if claim != {
        "complete_graph_operation_coverage": True,
        "complete_graph_state_contract_coverage": True,
        "complete_neutral_kernel_lowering": True,
        "full_model_execution": False,
        "physical_plan": False,
        "timing_or_performance": False,
    }:
        raise QwenFullModelSemanticCheckError(
            "semantic coverage claim boundary differs"
        )
    observed_families = coverage.get("operator_families")
    if not isinstance(observed_families, list):
        raise QwenFullModelSemanticCheckError(
            "operator family coverage is not an array"
        )
    family_counts = {
        item.get("kind"): item.get("operation_count")
        for item in observed_families
        if isinstance(item, dict)
    }
    if family_counts != EXPECTED_COUNTS or len(observed_families) != len(
        EXPECTED_COUNTS
    ):
        raise QwenFullModelSemanticCheckError("operator family counts differ")
    graph_contracts = {
        kind: {
            operation.numeric_contract
            for operation in model.operations
            if operation.kind == kind
        }
        for kind in EXPECTED_COUNTS
    }
    for item in observed_families:
        if (
            set(item)
            != {
                "kind",
                "numeric_contract",
                "operation_count",
                "qualification_report_ids",
                "status",
            }
            or graph_contracts[item["kind"]] != {item["numeric_contract"]}
            or item["status"] != "covered"
            or not isinstance(item["qualification_report_ids"], list)
            or not item["qualification_report_ids"]
        ):
            raise QwenFullModelSemanticCheckError(
                f"operator family {item.get('kind')!r} contract differs"
            )
        for report_id in item["qualification_report_ids"]:
            require_sha256(report_id, "qualification report ID")
    evidence = coverage.get("qualification_evidence")
    if not isinstance(evidence, list) or [
        item.get("role") for item in evidence if isinstance(item, dict)
    ] != ["attention", "final_output", "layer", "qkv"]:
        raise QwenFullModelSemanticCheckError(
            "qualification evidence role coverage differs"
        )
    evidence_ids = {item["report_id"] for item in evidence}
    referenced_ids = {
        report_id
        for family in observed_families
        for report_id in family["qualification_report_ids"]
    }
    if referenced_ids != evidence_ids:
        raise QwenFullModelSemanticCheckError(
            "operator family qualification references differ"
        )
    report_id_by_role = {item["role"]: item["report_id"] for item in evidence}
    for family in observed_families:
        expected_report_ids = [
            report_id_by_role[role]
            for role in EXPECTED_QUALIFICATION_ROLES_BY_KIND[family["kind"]]
        ]
        if family["qualification_report_ids"] != expected_report_ids:
            raise QwenFullModelSemanticCheckError(
                f"operator family {family['kind']!r} qualification binding differs"
            )
    for item in evidence:
        if set(item) != {
            "covered_numeric_contracts",
            "payload_sha256",
            "report_id",
            "role",
            "schema",
            "size_bytes",
        }:
            raise QwenFullModelSemanticCheckError(
                f"qualification evidence {item.get('role')!r} keys differ"
            )
        require_sha256(item["payload_sha256"], "qualification payload")
        require_sha256(item["report_id"], "qualification report")
        require_int(item["size_bytes"], "qualification size", minimum=1)
    state = coverage.get("state_coverage")
    if state != {
        "commit_effect_count": STATE_RESOURCE_COUNT,
        "prepare_effect_count": STATE_RESOURCE_COUNT,
        "read_committed_effect_count": STATE_RESOURCE_COUNT,
        "read_prepared_effect_count": STATE_RESOURCE_COUNT,
        "resource_count": STATE_RESOURCE_COUNT,
        "resource_ids_sha256": _state_ids_sha256(model),
        "terminal_commit_operation_id": "state.commit",
    }:
        raise QwenFullModelSemanticCheckError("state-resource coverage differs")
    role_counts = Counter(tensor.role for tensor in model.tensors)
    tensor = coverage.get("tensor_coverage")
    if tensor != {
        "activation_count": role_counts["activation"],
        "checkpoint_bound_weight_count": sum(
            item.binding is not None for item in model.tensors
        ),
        "input_count": role_counts["input"],
        "output_count": role_counts["output"],
        "tensor_count": len(model.tensors),
        "weight_count": role_counts["weight"],
    }:
        raise QwenFullModelSemanticCheckError("tensor coverage differs")


def _check_qualification_sources(
    coverage: Mapping[str, Any],
    model: ProductionModelGraph,
    *,
    attention_path: Path,
    final_output_path: Path,
    layer_path: Path,
    qkv_path: Path,
) -> None:
    paths = {
        "attention": Path(attention_path),
        "final_output": Path(final_output_path),
        "layer": Path(layer_path),
        "qkv": Path(qkv_path),
    }
    evidence = coverage["qualification_evidence"]
    by_role = {item["role"]: item for item in evidence}
    if set(by_role) != set(paths):
        raise QwenFullModelSemanticCheckError(
            "qualification evidence source roles differ"
        )
    for role in sorted(paths):
        value = _load_canonical(paths[role], f"{role} qualification source")
        _identity(value, "report_id", f"{role} qualification source")
        if value.get("status") != "pass":
            raise QwenFullModelSemanticCheckError(
                f"{role} qualification source does not pass"
            )
        if role == "attention":
            contracts = tuple(
                sorted((value.get("numeric_contract"), value.get("state_contract")))
            )
        else:
            raw_contracts = value.get("numeric_contracts")
            if not isinstance(raw_contracts, list):
                raise QwenFullModelSemanticCheckError(
                    f"{role} qualification source lacks numeric contracts"
                )
            contracts = tuple(raw_contracts)
        if (
            role in {"final_output", "layer", "qkv"}
            and value.get("checkpoint_lock_id") != coverage["checkpoint_lock_id"]
        ):
            raise QwenFullModelSemanticCheckError(
                f"{role} qualification checkpoint identity differs"
            )
        if role == "final_output" and value.get("graph_id") != model.graph_id:
            raise QwenFullModelSemanticCheckError(
                "final-output qualification graph identity differs"
            )
        expected = EXPECTED_QUALIFICATIONS[role]
        payload_sha256, size_bytes = sha256_file(paths[role])
        if (
            value.get("schema") != expected["schema"]
            or contracts != expected["contracts"]
            or by_role[role]
            != {
                "covered_numeric_contracts": list(contracts),
                "payload_sha256": payload_sha256,
                "report_id": value["report_id"],
                "role": role,
                "schema": value["schema"],
                "size_bytes": size_bytes,
            }
        ):
            raise QwenFullModelSemanticCheckError(
                f"{role} qualification source binding differs"
            )


def _expected_vector_shape(
    model: ProductionModelGraph,
    operation: ProductionOperation,
    width: int,
) -> dict[str, Any]:
    output = _tensor(model, operation.outputs[0])
    return {"rows": _row_extent(model, output, width), "width": width}


def _operation_layer(operation: ProductionOperation) -> int | None:
    if 1 <= operation.index <= 612:
        return (operation.index - 1) // 17
    return None


def _expect_source_tensor(
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
        raise QwenFullModelSemanticCheckError(
            f"tensor {tensor.tensor_id!r} source contract differs"
        )


def _check_source_operation_contract(
    model: ProductionModelGraph,
    operation: ProductionOperation,
) -> None:
    expected_arity = {
        "ADD": (2, 1),
        "ATTENTION": (2, 1),
        "EMBEDDING_LOOKUP": (2, 1),
        "KV_PREPARE": (2, 1),
        "LAST_TOKEN_SELECT": (1, 1),
        "MATMUL": (2, 1),
        "RMS_NORM": (2, 1),
        "ROPE": (2, 2),
        "SILU_MUL": (2, 1),
        "STATE_COMMIT": (1, 1),
    }
    if (len(operation.inputs), len(operation.outputs)) != expected_arity.get(
        operation.kind
    ):
        raise QwenFullModelSemanticCheckError(
            f"operation {operation.operation_id!r} source arity differs"
        )
    layer = _operation_layer(operation)
    if operation.kind == "EMBEDDING_LOOKUP":
        tokens = _tensor(model, operation.inputs[0])
        weight = _tensor(model, operation.inputs[1])
        output = _tensor(model, operation.outputs[0])
        _expect_source_tensor(tokens, dtype="i64", role="input", rank=2)
        _expect_source_tensor(weight, dtype="bf16", role="weight", rank=2)
        _expect_source_tensor(output, dtype="bf16", rank=3)
        if (
            tokens.shape != (1, "span_tokens")
            or weight.shape != (151936, 4096)
            or output.shape != (1, "span_tokens", 4096)
            or operation.attributes
            != {
                "source_kind": "TOKEN_EMBEDDING_LOOKUP",
                "weight_ids": [weight.tensor_id],
            }
        ):
            raise QwenFullModelSemanticCheckError(
                "embedding source operation contract differs"
            )
    elif operation.kind == "MATMUL":
        source = _tensor(model, operation.inputs[0])
        weight = _tensor(model, operation.inputs[1])
        output = _tensor(model, operation.outputs[0])
        _expect_source_tensor(source, dtype="bf16", rank=3)
        _expect_source_tensor(weight, dtype="bf16", role="weight", rank=2)
        _expect_source_tensor(output, dtype="bf16", rank=3)
        width, reduction = weight.shape
        expected_attributes: dict[str, Any] = {
            "source_kind": "LINEAR",
            "transpose_weight": True,
            "weight_ids": [weight.tensor_id],
        }
        if layer is not None:
            expected_attributes["layer"] = layer
        if (
            not isinstance(width, int)
            or not isinstance(reduction, int)
            or source.shape[-1] != reduction
            or output.shape[-1] != width
            or source.shape[:2] != output.shape[:2]
            or operation.attributes != expected_attributes
        ):
            raise QwenFullModelSemanticCheckError(
                f"matrix source operation {operation.operation_id!r} differs"
            )
        _row_extent(model, output, width)
    elif operation.kind == "RMS_NORM":
        source = _tensor(model, operation.inputs[0])
        weight = _tensor(model, operation.inputs[1])
        output = _tensor(model, operation.outputs[0])
        _expect_source_tensor(source, dtype="bf16", rank=3)
        _expect_source_tensor(weight, dtype="bf16", role="weight", rank=1)
        _expect_source_tensor(output, dtype="bf16", rank=3)
        width = weight.shape[0]
        expected_attributes = {
            "epsilon": 1e-6,
            "normalization_width": width,
            "source_kind": "RMS_NORM",
            "weight_ids": [weight.tensor_id],
        }
        if layer is not None:
            expected_attributes["layer"] = layer
        if (
            not isinstance(width, int)
            or source.shape != output.shape
            or operation.attributes != expected_attributes
        ):
            raise QwenFullModelSemanticCheckError(
                f"RMSNorm source operation {operation.operation_id!r} differs"
            )
        _row_extent(model, output, width)
    elif operation.kind == "ADD":
        left = _tensor(model, operation.inputs[0])
        right = _tensor(model, operation.inputs[1])
        output = _tensor(model, operation.outputs[0])
        for tensor in (left, right, output):
            _expect_source_tensor(tensor, dtype="bf16", rank=3)
        if (
            left.shape != right.shape
            or left.shape != output.shape
            or operation.attributes != {"layer": layer, "source_kind": "RESIDUAL_ADD"}
        ):
            raise QwenFullModelSemanticCheckError(
                f"add source operation {operation.operation_id!r} differs"
            )
        width = output.shape[-1]
        if not isinstance(width, int):
            raise QwenFullModelSemanticCheckError("add source width is not static")
        _row_extent(model, output, width)
    elif operation.kind == "SILU_MUL":
        gate = _tensor(model, operation.inputs[0])
        up = _tensor(model, operation.inputs[1])
        output = _tensor(model, operation.outputs[0])
        for tensor in (gate, up, output):
            _expect_source_tensor(tensor, dtype="bf16", rank=3)
        if (
            gate.shape != up.shape
            or gate.shape != output.shape
            or output.shape[-1] != 12288
            or operation.attributes != {"layer": layer, "source_kind": "SILU_MUL"}
        ):
            raise QwenFullModelSemanticCheckError(
                f"SiLU source operation {operation.operation_id!r} differs"
            )
        _row_extent(model, output, 12288)
    elif operation.kind == "ROPE":
        q_input = _tensor(model, operation.inputs[0])
        k_input = _tensor(model, operation.inputs[1])
        q_output = _tensor(model, operation.outputs[0])
        k_output = _tensor(model, operation.outputs[1])
        for tensor in (q_input, k_input, q_output, k_output):
            _expect_source_tensor(tensor, dtype="bf16", rank=3)
        if (
            q_input.shape != q_output.shape
            or k_input.shape != k_output.shape
            or q_input.shape != (1, "span_tokens", QUERY_HEADS * HEAD_DIM)
            or k_input.shape != (1, "span_tokens", KEY_VALUE_HEADS * HEAD_DIM)
            or operation.attributes
            != {
                "head_dim": HEAD_DIM,
                "layer": layer,
                "position_symbol": "position_start",
                "source_kind": "ROPE",
            }
        ):
            raise QwenFullModelSemanticCheckError(
                f"RoPE source operation {operation.operation_id!r} differs"
            )
    elif operation.kind == "KV_PREPARE":
        key = _tensor(model, operation.inputs[0])
        value = _tensor(model, operation.inputs[1])
        handle = _tensor(model, operation.outputs[0])
        _expect_source_tensor(key, dtype="bf16", rank=3)
        _expect_source_tensor(value, dtype="bf16", rank=3)
        _expect_source_tensor(handle, dtype="u32", rank=1)
        if (
            key.shape != (1, "span_tokens", KEY_VALUE_HEADS * HEAD_DIM)
            or value.shape != key.shape
            or handle.shape != (1,)
            or operation.attributes != {"layer": layer, "source_kind": "KV_COMMIT"}
        ):
            raise QwenFullModelSemanticCheckError(
                f"KV-prepare source operation {operation.operation_id!r} differs"
            )
    elif operation.kind == "ATTENTION":
        query = _tensor(model, operation.inputs[0])
        handle = _tensor(model, operation.inputs[1])
        output = _tensor(model, operation.outputs[0])
        _expect_source_tensor(query, dtype="bf16", rank=3)
        _expect_source_tensor(handle, dtype="u32", rank=1)
        _expect_source_tensor(output, dtype="bf16", rank=3)
        if (
            query.shape != (1, "span_tokens", QUERY_HEADS * HEAD_DIM)
            or output.shape != query.shape
            or handle.shape != (1,)
            or operation.attributes
            != {
                "head_dim": HEAD_DIM,
                "key_value_heads": KEY_VALUE_HEADS,
                "layer": layer,
                "query_heads": QUERY_HEADS,
                "scale_denominator_sqrt": HEAD_DIM,
                "source_kind": "GQA_CAUSAL_ATTENTION",
            }
        ):
            raise QwenFullModelSemanticCheckError(
                f"attention source operation {operation.operation_id!r} differs"
            )
    elif operation.kind == "LAST_TOKEN_SELECT":
        source = _tensor(model, operation.inputs[0])
        output = _tensor(model, operation.outputs[0])
        _expect_source_tensor(source, dtype="bf16", rank=3)
        _expect_source_tensor(output, dtype="bf16", rank=3)
        if (
            source.shape != (1, "span_tokens", 4096)
            or output.shape != (1, 1, 4096)
            or operation.attributes != {"source_kind": "LAST_TOKEN_SELECT"}
        ):
            raise QwenFullModelSemanticCheckError(
                "last-token source operation contract differs"
            )
    elif operation.kind == "STATE_COMMIT":
        source = _tensor(model, operation.inputs[0])
        output = _tensor(model, operation.outputs[0])
        _expect_source_tensor(source, dtype="bf16", rank=3)
        _expect_source_tensor(output, dtype="bf16", rank=3)
        if (
            source.shape != (1, 1, 151936)
            or output.shape != source.shape
            or operation.attributes != {"atomic_state_count": STATE_RESOURCE_COUNT}
        ):
            raise QwenFullModelSemanticCheckError(
                "state-commit source operation contract differs"
            )

    if operation.kind == "KV_PREPARE" and layer is not None:
        state_id = f"kv.layer.{layer}"
        expected_effects = (("read_committed", state_id), ("prepare", state_id))
    elif operation.kind == "ATTENTION" and layer is not None:
        expected_effects = (("read_prepared", f"kv.layer.{layer}"),)
    elif operation.kind == "STATE_COMMIT":
        expected_effects = tuple(
            ("commit", f"kv.layer.{index}") for index in range(STATE_RESOURCE_COUNT)
        )
    else:
        expected_effects = ()
    observed_effects = tuple(
        (effect.action, effect.state_id) for effect in operation.effects
    )
    if observed_effects != expected_effects:
        raise QwenFullModelSemanticCheckError(
            f"operation {operation.operation_id!r} source state effects differ"
        )


def _check_kernel_shape(
    model: ProductionModelGraph,
    operation: ProductionOperation,
    kernel: Mapping[str, Any],
) -> None:
    context_capacity = _context_capacity(model)
    shape = kernel.get("shape")
    if not isinstance(shape, dict):
        raise QwenFullModelSemanticCheckError(
            f"kernel {operation.operation_id!r} lacks a shape"
        )
    if operation.kind == "MATMUL":
        source = _tensor(model, operation.inputs[0])
        weight = _tensor(model, operation.inputs[1])
        output = _tensor(model, operation.outputs[0])
        width, reduction = weight.shape
        if (
            not isinstance(width, int)
            or not isinstance(reduction, int)
            or source.shape[-1] != reduction
            or output.shape[-1] != width
            or shape
            != {
                "reduction_width": reduction,
                "rows": _row_extent(model, output, width),
                "width": width,
            }
        ):
            raise QwenFullModelSemanticCheckError(
                f"matrix kernel {operation.operation_id!r} shape differs"
            )
    elif operation.kind == "RMS_NORM":
        width = operation.attributes.get("normalization_width")
        if not isinstance(width, int) or shape != _expected_vector_shape(
            model, operation, width
        ):
            raise QwenFullModelSemanticCheckError(
                f"RMSNorm kernel {operation.operation_id!r} shape differs"
            )
    elif operation.kind in {"ADD", "EMBEDDING_LOOKUP", "SILU_MUL"}:
        output = _tensor(model, operation.outputs[0])
        width = output.shape[-1]
        if not isinstance(width, int) or shape != _expected_vector_shape(
            model, operation, width
        ):
            raise QwenFullModelSemanticCheckError(
                f"vector kernel {operation.operation_id!r} shape differs"
            )
    elif operation.kind == "ROPE":
        if shape != {"head_dim": HEAD_DIM}:
            raise QwenFullModelSemanticCheckError("RoPE kernel shape differs")
    elif operation.kind == "KV_PREPARE":
        if shape != {
            "head_dim": HEAD_DIM,
            "key_value_heads": KEY_VALUE_HEADS,
            "max_context_tokens": context_capacity,
            "tokens_symbol": "span_tokens",
        }:
            raise QwenFullModelSemanticCheckError("KV-prepare kernel shape differs")
    elif operation.kind == "ATTENTION":
        if shape != {
            "head_dim": HEAD_DIM,
            "key_value_heads": KEY_VALUE_HEADS,
            "max_context_tokens": context_capacity,
            "query_heads": QUERY_HEADS,
            "query_tokens_symbol": "span_tokens",
        }:
            raise QwenFullModelSemanticCheckError("attention kernel shape differs")
    elif operation.kind == "LAST_TOKEN_SELECT":
        if shape != {
            "maximum_rows": context_capacity,
            "rows_symbol": "span_tokens",
            "width": 4096,
        }:
            raise QwenFullModelSemanticCheckError("selection kernel shape differs")
    elif operation.kind == "STATE_COMMIT":
        resources = [effect.state_id for effect in operation.effects]
        if (
            shape != {"atomic_state_count": len(resources)}
            or kernel.get("state_resources") != resources
        ):
            raise QwenFullModelSemanticCheckError("commit kernel coverage differs")
    else:  # pragma: no cover - complete kind counts guard this path.
        raise QwenFullModelSemanticCheckError(f"unknown kernel kind {operation.kind!r}")


def _check_kernel_attributes(
    model: ProductionModelGraph,
    operation: ProductionOperation,
    kernel: Mapping[str, Any],
) -> None:
    context_capacity = _context_capacity(model)
    attributes = kernel.get("attributes")
    if not isinstance(attributes, dict):
        raise QwenFullModelSemanticCheckError(
            f"kernel {operation.operation_id!r} lacks attributes"
        )
    expected: dict[str, Any]
    if operation.kind == "ADD":
        expected = {
            "addition": "binary32_rne",
            "input_dtype": "bf16",
            "output_dtype": "bf16",
            "output_rounding": "rne",
            "zero_canonicalization": "positive",
        }
    elif operation.kind == "ATTENTION":
        expected = {
            "causal_mask_bf16_code": 0xFF7F,
            "prepared_state_visibility": "transaction_private",
            "probability_dtype": "bf16",
            "query_heads_per_key_value_head": QUERY_HEADS // KEY_VALUE_HEADS,
            "scale_bf16_code": 0x3DB5,
            "score_reduction_order": "strictly_increasing_head_dimension",
            "softmax_compute_dtype": "fp32",
            "softmax_reduction_lanes": 8,
            "value_reduction_order": "strictly_increasing_context",
        }
    elif operation.kind == "EMBEDDING_LOOKUP":
        expected = {
            "index_conversion": "checked_nonnegative_u32",
            "index_dtype": "u32",
            "output_dtype": "bf16",
            "source_index_dtype": "i64",
            "source_index_max_exclusive": 151936,
            "source_index_min": 0,
        }
    elif operation.kind == "KV_PREPARE":
        resources = [
            effect.state_id
            for effect in operation.effects
            if effect.action == "prepare"
        ]
        if len(resources) != 1:
            raise QwenFullModelSemanticCheckError(
                f"KV prepare {operation.operation_id!r} state binding differs"
            )
        expected = {
            "append_position_symbol": "position_start",
            "generation_check": "exact_expected_generation",
            "state_resource": resources[0],
            "transaction_scope": "model_forward_request",
            "visibility": "transaction_private_until_commit",
        }
    elif operation.kind == "LAST_TOKEN_SELECT":
        expected = {
            "index_dtype": "u32",
            "input_dtype": "bf16",
            "output_dtype": "bf16",
            "selection": "last_logical_row",
        }
    elif operation.kind == "MATMUL":
        expected = {
            "accumulator_dtype": "fp32",
            "input_dtype": "bf16",
            "output_dtype": "bf16",
            "output_rounding": "rne",
            "reduction_order": "strictly_increasing_k",
            "transpose_weight": True,
        }
    elif operation.kind == "RMS_NORM":
        expected = {
            "epsilon_binary32_code": 897988541,
            "final_weight_product": "bf16_multiply_then_bf16_rne",
            "normalized_boundary": "bf16_rne_before_weight",
            "reduction_order": "canonical_balanced_binary32_tree",
            "rsqrt": "correctly_rounded_binary32_rne",
        }
    elif operation.kind == "ROPE":
        expected = {
            "coefficient_layout": "cos_head_dim_then_sin_head_dim",
            "key_value_heads": KEY_VALUE_HEADS,
            "max_positions": context_capacity,
            "position_count_symbol": "span_tokens",
            "position_progression": "consecutive_from_start",
            "position_symbol": "position_start",
            "query_heads": QUERY_HEADS,
            "rotation": "concat_neg_second_half_first_half",
        }
    elif operation.kind == "SILU_MUL":
        expected = {
            "activation_boundary": "bf16_rne_before_up_multiply",
            "exponential": "correctly_rounded_binary32_rne",
            "input_dtype": "bf16",
            "output_dtype": "bf16",
            "output_rounding": "rne",
            "sigmoid": "stable_sign_selected_binary32",
            "zero_canonicalization": "positive",
        }
    elif operation.kind == "STATE_COMMIT":
        expected = {
            "atomic": True,
            "coverage": "complete_operation",
            "generation_increment": 1,
            "source_atomic_state_count": STATE_RESOURCE_COUNT,
            "transaction_scope": "model_forward_request",
        }
    else:  # pragma: no cover - complete kind counts guard this path.
        raise QwenFullModelSemanticCheckError(
            f"kernel {operation.operation_id!r} kind is unknown"
        )
    if attributes != expected:
        raise QwenFullModelSemanticCheckError(
            f"kernel {operation.operation_id!r} numeric attributes differ"
        )


def _check_kernel_ir(
    model: ProductionModelGraph,
    coverage: Mapping[str, Any],
    kernel_ir: dict[str, Any],
) -> None:
    try:
        exact_keys(
            kernel_ir,
            {
                "graph_id",
                "kernel_ir_id",
                "kernels",
                "qualification_report_id",
                "schema",
            },
            set(),
            "complete neutral Kernel IR",
        )
    except ArtifactError as exc:
        raise QwenFullModelSemanticCheckError(str(exc)) from exc
    _identity(kernel_ir, "kernel_ir_id", "complete neutral Kernel IR")
    kernels = kernel_ir.get("kernels")
    if (
        kernel_ir.get("schema") != KERNEL_SCHEMA
        or kernel_ir.get("graph_id") != model.graph_id
        or kernel_ir.get("qualification_report_id") != coverage["report_id"]
        or not isinstance(kernels, list)
        or len(kernels) != len(model.operations)
    ):
        raise QwenFullModelSemanticCheckError(
            "complete neutral Kernel IR boundary differs"
        )
    for index, (operation, kernel) in enumerate(
        zip(model.operations, kernels, strict=True)
    ):
        if (
            not isinstance(kernel, dict)
            or kernel.get("index") != index
            or kernel.get("source_operation_id") != operation.operation_id
            or kernel.get("kind") != operation.kind
            or kernel.get("numeric_contract") != operation.numeric_contract
            or kernel.get("inputs") != list(operation.inputs)
            or kernel.get("outputs") != list(operation.outputs)
        ):
            raise QwenFullModelSemanticCheckError(
                f"kernel {index} does not map operation {operation.operation_id!r}"
            )
        _check_kernel_shape(model, operation, kernel)
        _check_kernel_attributes(model, operation, kernel)
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
            raise QwenFullModelSemanticCheckError(
                "backend-specific data leaked into complete neutral Kernel IR"
            )


def check_qwen_full_model_semantics(
    *,
    model_graph_path: Path,
    capability_path: Path,
    coverage_path: Path,
    kernel_ir_path: Path,
    qkv_qualification_path: Path,
    attention_qualification_path: Path,
    layer_qualification_path: Path,
    final_output_qualification_path: Path,
) -> dict[str, Any]:
    """Independently reconstruct complete Qwen semantic coverage."""

    try:
        model = load_production_model_graph(Path(model_graph_path))
        capability = load_production_capability(Path(capability_path))
    except (ProductionModelGraphError, ProductionCapabilityError) as exc:
        raise QwenFullModelSemanticCheckError(
            f"independent semantic source admission failed: {exc}"
        ) from exc
    checkpoint_lock_id, context_capacity = _check_model_contract(model)
    _check_capability_contract(capability, context_capacity)
    coverage = _load_canonical(Path(coverage_path), "semantic coverage")
    kernel_ir = _load_canonical(Path(kernel_ir_path), "complete neutral Kernel IR")
    _check_coverage(model, capability, checkpoint_lock_id, coverage)
    _check_qualification_sources(
        coverage,
        model,
        attention_path=Path(attention_qualification_path),
        final_output_path=Path(final_output_qualification_path),
        layer_path=Path(layer_qualification_path),
        qkv_path=Path(qkv_qualification_path),
    )
    _check_kernel_ir(model, coverage, kernel_ir)
    if (
        len(model.operations) != OPERATION_COUNT
        or len(model.state_resources) != STATE_RESOURCE_COUNT
        or dict(sorted(Counter(op.kind for op in model.operations).items()))
        != EXPECTED_COUNTS
    ):
        raise QwenFullModelSemanticCheckError(
            "independent complete-graph cardinality differs"
        )
    body = {
        "capability_id": capability.capability_id,
        "checks": {
            "artifact_identities": True,
            "backend_neutral": True,
            "dynamic_shapes": True,
            "kernel_indices_contiguous": True,
            "numeric_contracts_exact": True,
            "operation_coverage_exact": True,
            "qualification_references_complete": True,
            "state_coverage_exact": True,
            "tensor_coverage_exact": True,
        },
        "coverage_report_id": coverage["report_id"],
        "graph_id": model.graph_id,
        "kernel_ir_id": kernel_ir["kernel_ir_id"],
        "operation_count": len(model.operations),
        "operation_ids_sha256": _operation_ids_sha256(model),
        "schema": CHECK_SCHEMA,
        "state_resource_count": len(model.state_resources),
        "state_resource_ids_sha256": _state_ids_sha256(model),
        "status": "pass",
    }
    result = dict(body)
    result["check_id"] = sha256_bytes(canonical_json_bytes(body))
    return result


__all__ = [
    "CHECK_SCHEMA",
    "QwenFullModelSemanticCheckError",
    "check_qwen_full_model_semantics",
]
