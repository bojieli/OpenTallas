"""Model Graph to target-numeric Tensor Kernel IR lowering."""

from __future__ import annotations

from collections import Counter
from typing import Any

from .capability import Capability
from .common import canonical_json_bytes, sha256_bytes
from .model import ModelGraph, QUALIFIED_FIXTURE_PROFILE


KERNEL_IR_SCHEMA = "opentallas.tensor_kernel_ir.v1"
OPERATOR_COVERAGE_SCHEMA = "opentallas.tensor_accelerator.operator_coverage.v1"
SUPPORTED_OPERATION_KINDS = frozenset({"MATMUL", "ADD"})


class LoweringError(RuntimeError):
    """Raised when a graph cannot be completely and legally lowered."""


def _validate_capability(model: ModelGraph, capability: Capability) -> None:
    if model.numeric_profile not in capability.numeric_profiles:
        raise LoweringError(
            f"capability does not support numeric profile {model.numeric_profile!r}"
        )
    if len(model.symbols) > capability.limits["max_runtime_symbols"]:
        raise LoweringError("model exceeds capability runtime-symbol limit")
    symbols = model.symbol_by_id
    for tensor in model.tensors:
        if len(tensor.shape) > capability.limits["max_rank"]:
            raise LoweringError(
                f"tensor {tensor.tensor_id!r} exceeds capability rank limit"
            )
        if tensor.size_bytes(symbols) > capability.limits["max_tensor_bytes"]:
            raise LoweringError(
                f"tensor {tensor.tensor_id!r} exceeds capability byte limit"
            )


def operator_coverage(model: ModelGraph) -> dict[str, Any]:
    counts = Counter(operation.kind for operation in model.operations)
    unsupported = sorted(set(counts) - SUPPORTED_OPERATION_KINDS)
    return {
        "encountered_operations": [
            {"count": counts[kind], "kind": kind} for kind in sorted(counts)
        ],
        "model_id": model.model_id,
        "numeric_profile": model.numeric_profile,
        "schema": OPERATOR_COVERAGE_SCHEMA,
        "status": "pass" if not unsupported else "fail",
        "supported_operations": sorted(SUPPORTED_OPERATION_KINDS),
        "unsupported_operations": unsupported,
        "unsupported_operation_count": sum(counts[kind] for kind in unsupported),
    }


def lower_model(model: ModelGraph, capability: Capability) -> dict[str, Any]:
    """Lower a fully validated graph to target-numeric kernel records."""

    _validate_capability(model, capability)
    coverage = operator_coverage(model)
    if coverage["unsupported_operation_count"]:
        raise LoweringError(
            "unlowered operations remain: "
            + ", ".join(coverage["unsupported_operations"])
        )
    if model.numeric_profile != QUALIFIED_FIXTURE_PROFILE:
        raise LoweringError(
            f"numeric profile {model.numeric_profile!r} has no qualified kernel lowering yet"
        )
    tensors = model.tensor_by_id
    symbols = model.symbol_by_id
    kernels: list[dict[str, Any]] = []
    for operation in model.operations:
        if operation.kind == "MATMUL":
            left = tensors[operation.inputs[0]]
            right = tensors[operation.inputs[1]]
            output = tensors[operation.outputs[0]]
            m, k = left.resolved_shape(symbols)
            n, weight_k = right.resolved_shape(symbols)
            if k != weight_k:
                raise LoweringError(f"MATMUL {operation.operation_id!r} reduction mismatch")
            if (
                m > capability.tensor.max_m
                or n > capability.tensor.max_n
                or k > capability.tensor.max_k
            ):
                raise LoweringError(
                    f"MATMUL {operation.operation_id!r} exceeds tensor-engine bounds"
                )
            kernel = {
                "index": operation.index,
                "inputs": list(operation.inputs),
                "kind": "GEMM_I8_I8_I32",
                "kernel_id": f"kernel.{operation.index:04d}",
                "numeric": dict(operation.numeric),
                "operation_id": operation.operation_id,
                "outputs": list(operation.outputs),
                "shape": {"k": k, "m": m, "n": n},
                "tile": {
                    "k": min(k, capability.tensor.max_k),
                    "m": min(m, capability.tensor.max_m),
                    "n": min(n, capability.tensor.max_n),
                },
                "traffic_bytes": {
                    "input0": left.size_bytes(symbols),
                    "input1": right.size_bytes(symbols),
                    "output": output.size_bytes(symbols),
                },
            }
        elif operation.kind == "ADD":
            left = tensors[operation.inputs[0]]
            right = tensors[operation.inputs[1]]
            output = tensors[operation.outputs[0]]
            elements = left.element_count(symbols)
            if right.role != "weight":
                raise LoweringError(
                    f"fixture ADD {operation.operation_id!r} requires a weight second input"
                )
            if left.dtype != "i32" or right.dtype != "i32" or output.dtype != "i32":
                raise LoweringError(
                    f"fixture ADD {operation.operation_id!r} requires i32 tensors"
                )
            kernel = {
                "index": operation.index,
                "inputs": list(operation.inputs),
                "kind": "ADD_I32",
                "kernel_id": f"kernel.{operation.index:04d}",
                "numeric": dict(operation.numeric),
                "operation_id": operation.operation_id,
                "outputs": list(operation.outputs),
                "shape": {"elements": elements},
                "tile": {
                    "elements": min(
                        elements,
                        capability.vector.elements_per_cycle
                        * capability.vector.count,
                    )
                },
                "traffic_bytes": {
                    "input0": left.size_bytes(symbols),
                    "input1": right.size_bytes(symbols),
                    "output": output.size_bytes(symbols),
                },
            }
        else:  # pragma: no cover - coverage check is deliberately fail-closed.
            raise LoweringError(f"operation {operation.kind!r} reached no lowering")
        kernels.append(kernel)
    body = {
        "capability_id": capability.capability_id,
        "kernels": kernels,
        "model_id": model.model_id,
        "numeric_profile": model.numeric_profile,
        "schema": KERNEL_IR_SCHEMA,
    }
    return {**body, "kernel_ir_id": sha256_bytes(canonical_json_bytes(body))}
