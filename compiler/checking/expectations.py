"""Static semantic-accounting expectations independent of the interpreter."""

from __future__ import annotations

from typing import Any

from compiler.ir.model import Model


EXPECTATION_SCHEMA = "opentallas.execution_expectations.v1"
COUNTER_KEYS = (
    "activation_tensor_reads",
    "completion_events",
    "elementwise_add_operations",
    "logical_activation_bytes_read",
    "logical_activation_bytes_written",
    "logical_rom_bytes_read",
    "micro_ops_executed",
    "rom_tensor_reads",
    "scalar_accumulate_add_operations",
    "scalar_multiply_operations",
    "semantic_operations_executed",
)


def empty_counters() -> dict[str, int]:
    return {key: 0 for key in COUNTER_KEYS}


def build_execution_expectations(model: Model) -> dict[str, Any]:
    """Derive exact functional counts without invoking service-engine code."""

    tensors = model.tensor_by_id
    counters = empty_counters()
    counters["micro_ops_executed"] = len(model.operations) + 1
    counters["semantic_operations_executed"] = len(model.operations)
    counters["completion_events"] = 1
    per_operation: list[dict[str, Any]] = []

    for operation in model.operations:
        delta = empty_counters()
        delta["semantic_operations_executed"] = 1
        delta["micro_ops_executed"] = 1
        for tensor_id in operation.inputs:
            tensor = tensors[tensor_id]
            if tensor.storage == "rom":
                delta["rom_tensor_reads"] += 1
                delta["logical_rom_bytes_read"] += tensor.size_bytes
            else:
                delta["activation_tensor_reads"] += 1
                delta["logical_activation_bytes_read"] += tensor.size_bytes
        output = tensors[operation.output]
        delta["logical_activation_bytes_written"] += output.size_bytes

        if operation.kind == "ROM_MATMUL":
            batch, reduction = tensors[operation.inputs[0]].shape
            rows, _ = tensors[operation.inputs[1]].shape
            scalar_products = batch * rows * reduction
            delta["scalar_multiply_operations"] += scalar_products
            delta["scalar_accumulate_add_operations"] += scalar_products
        elif operation.kind == "VECTOR_ADD":
            delta["elementwise_add_operations"] += output.element_count

        for key in COUNTER_KEYS:
            if key not in {"micro_ops_executed", "semantic_operations_executed"}:
                counters[key] += delta[key]
        per_operation.append(
            {
                "counters": {key: value for key, value in delta.items() if value},
                "operation_id": operation.operation_id,
                "operation_index": operation.index,
            }
        )

    per_operation.append(
        {
            "counters": {"completion_events": 1, "micro_ops_executed": 1},
            "operation_id": "$complete",
            "operation_index": len(model.operations),
        }
    )
    return {
        "counters": counters,
        "hardware_accounting": {
            "cycles": None,
            "flits": None,
            "hbm_transactions": None,
            "stalls": None,
            "status": "not modeled by the functional fixture",
        },
        "model_id": model.model_id,
        "per_operation": per_operation,
        "schema": EXPECTATION_SCHEMA,
        "semantics": (
            "Logical tensor bytes count each semantic tensor operand once per operation; "
            "they are not cache, bus, HBM, ROM-port, or physical-cycle measurements. "
            "Each dot-product term contributes one multiply and one accumulator update."
        ),
    }
