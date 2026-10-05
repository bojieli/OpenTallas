"""Independent reconstruction, legality, and execution-accounting checker."""

from __future__ import annotations

from pathlib import Path
import struct
from typing import Any, Mapping

from .capability import Capability, load_capability
from .command import Command, Opcode, decode
from .common import (
    ArtifactError,
    canonical_json_bytes,
    exact_keys,
    load_strict_json,
    require_int,
    require_sha256,
    sha256_bytes,
)
from .lowering import KERNEL_IR_SCHEMA
from .model import ModelGraph, Tensor, load_model_graph
from .physical import HBM_IMAGE_PATH, PHYSICAL_PLAN_SCHEMA, STAGING_ID


CHECK_SCHEMA = "opentallas.tensor_accelerator.independent_check.v1"
EXPECTATIONS_SCHEMA = "opentallas.tensor_accelerator.execution_expectations.v1"
COUNTER_KEYS = (
    "commands_executed",
    "completion_events",
    "control_cycles",
    "cycles",
    "dma_commands",
    "dma_cycles",
    "elementwise_add_operations",
    "hbm_read_transactions",
    "hbm_transferred_bytes_read",
    "hbm_useful_bytes_read",
    "host_input_bytes_written",
    "scalar_accumulate_add_operations",
    "scalar_multiply_operations",
    "semantic_operations_executed",
    "sram_bytes_read",
    "sram_bytes_written",
    "tensor_commands",
    "tensor_cycles",
    "vector_commands",
    "vector_cycles",
)


class IndependentCheckError(RuntimeError):
    """Raised when generated artifacts do not independently reconstruct."""


def _ceil_div(value: int, divisor: int) -> int:
    return (value + divisor - 1) // divisor


def _body_id(value: Mapping[str, Any], id_key: str) -> str:
    body = dict(value)
    body.pop(id_key, None)
    return sha256_bytes(canonical_json_bytes(body))


def _decode_payload(tensor: Tensor, payload: bytes) -> tuple[int, ...]:
    if tensor.dtype == "i8":
        if len(payload) != len(tensor.values or ()):
            raise IndependentCheckError(
                f"i8 payload length differs for {tensor.tensor_id!r}"
            )
        return tuple(struct.unpack(f"<{len(payload)}b", payload))
    if tensor.dtype == "i32":
        if len(payload) % 4:
            raise IndependentCheckError(
                f"i32 payload alignment differs for {tensor.tensor_id!r}"
            )
        return tuple(struct.unpack(f"<{len(payload) // 4}i", payload))
    raise IndependentCheckError(
        f"independent payload decoder lacks dtype {tensor.dtype!r}"
    )


def _validate_runtime_graph(root: Path, model: ModelGraph) -> None:
    runtime_graph = load_strict_json(root / "ir/model_graph.json")
    if runtime_graph != model.to_dict(include_values=False):
        raise IndependentCheckError(
            "runtime Model Graph IR differs from payload-free source semantics"
        )


def _validate_kernel_ir(
    raw: dict[str, Any],
    model: ModelGraph,
    capability: Capability,
) -> list[dict[str, Any]]:
    exact_keys(
        raw,
        {
            "schema",
            "kernel_ir_id",
            "capability_id",
            "model_id",
            "numeric_profile",
            "kernels",
        },
        set(),
        "Tensor Kernel IR",
    )
    if raw["schema"] != KERNEL_IR_SCHEMA:
        raise IndependentCheckError("unsupported Tensor Kernel IR schema")
    if raw["kernel_ir_id"] != _body_id(raw, "kernel_ir_id"):
        raise IndependentCheckError("Tensor Kernel IR identity mismatch")
    if (
        raw["capability_id"] != capability.capability_id
        or raw["model_id"] != model.model_id
        or raw["numeric_profile"] != model.numeric_profile
    ):
        raise IndependentCheckError("Tensor Kernel IR identity binding mismatch")
    kernels = raw["kernels"]
    if not isinstance(kernels, list) or len(kernels) != len(model.operations):
        raise IndependentCheckError("Tensor Kernel IR does not cover every operation")
    tensors = model.tensor_by_id
    symbols = model.symbol_by_id
    for index, (kernel, operation) in enumerate(
        zip(kernels, model.operations, strict=True)
    ):
        if not isinstance(kernel, dict):
            raise IndependentCheckError(f"kernel {index} must be an object")
        if (
            kernel.get("index") != index
            or kernel.get("kernel_id") != f"kernel.{index:04d}"
            or kernel.get("operation_id") != operation.operation_id
            or kernel.get("inputs") != list(operation.inputs)
            or kernel.get("outputs") != list(operation.outputs)
            or kernel.get("numeric") != dict(operation.numeric)
        ):
            raise IndependentCheckError(
                f"kernel {index} does not exactly represent its model operation"
            )
        left = tensors[operation.inputs[0]]
        right = tensors[operation.inputs[1]]
        output = tensors[operation.outputs[0]]
        traffic = {
            "input0": left.size_bytes(symbols),
            "input1": right.size_bytes(symbols),
            "output": output.size_bytes(symbols),
        }
        if kernel.get("traffic_bytes") != traffic:
            raise IndependentCheckError(f"kernel {index} traffic bytes differ")
        if operation.kind == "MATMUL":
            m, k = left.resolved_shape(symbols)
            n, right_k = right.resolved_shape(symbols)
            if right_k != k:
                raise IndependentCheckError(f"kernel {index} reduction differs")
            if (
                kernel.get("kind") != "GEMM_I8_I8_I32"
                or kernel.get("shape") != {"k": k, "m": m, "n": n}
            ):
                raise IndependentCheckError(f"kernel {index} GEMM shape differs")
            tile = kernel.get("tile")
            if (
                not isinstance(tile, dict)
                or set(tile) != {"k", "m", "n"}
                or not 1 <= tile["m"] <= min(m, capability.tensor.max_m)
                or not 1 <= tile["n"] <= min(n, capability.tensor.max_n)
                or not 1 <= tile["k"] <= min(k, capability.tensor.max_k)
            ):
                raise IndependentCheckError(f"kernel {index} has an illegal GEMM tile")
        elif operation.kind == "ADD":
            elements = left.element_count(symbols)
            if (
                kernel.get("kind") != "ADD_I32"
                or kernel.get("shape") != {"elements": elements}
            ):
                raise IndependentCheckError(f"kernel {index} ADD shape differs")
            tile = kernel.get("tile")
            if (
                not isinstance(tile, dict)
                or set(tile) != {"elements"}
                or not 1
                <= tile["elements"]
                <= min(
                    elements,
                    capability.vector.elements_per_cycle
                    * capability.vector.count,
                )
            ):
                raise IndependentCheckError(f"kernel {index} has an illegal ADD tile")
        else:
            raise IndependentCheckError(
                f"kernel {index} operation {operation.kind!r} is not qualified"
            )
    return kernels


def _validate_hbm(
    root: Path,
    plan_hbm: Any,
    model: ModelGraph,
    capability: Capability,
) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
    if not isinstance(plan_hbm, dict):
        raise IndependentCheckError("physical plan HBM record must be an object")
    exact_keys(
        plan_hbm,
        {"allocations", "image", "padding_bytes_must_be_zero"},
        set(),
        "physical plan HBM",
    )
    if plan_hbm["padding_bytes_must_be_zero"] is not True:
        raise IndependentCheckError("HBM padding-zero rule is not enabled")
    image_record = plan_hbm["image"]
    if not isinstance(image_record, dict):
        raise IndependentCheckError("HBM image record must be an object")
    exact_keys(
        image_record,
        {"path", "sha256", "size_bytes"},
        set(),
        "HBM image record",
    )
    if image_record["path"] != HBM_IMAGE_PATH:
        raise IndependentCheckError("HBM image path differs from the ABI")
    image_path = root / HBM_IMAGE_PATH
    image = image_path.read_bytes()
    if image_record["size_bytes"] != len(image):
        raise IndependentCheckError("HBM image byte count mismatch")
    if image_record["sha256"] != sha256_bytes(image):
        raise IndependentCheckError("HBM image SHA-256 mismatch")
    if len(image) > capability.hbm.capacity_bytes:
        raise IndependentCheckError("HBM image exceeds capability capacity")
    if len(image) % capability.hbm.burst_bytes:
        raise IndependentCheckError("HBM image is not burst aligned")

    expected_tensors = [
        tensor
        for tensor in model.tensors
        if tensor.role in {"weight", "constant"}
    ]
    raw_allocations = plan_hbm["allocations"]
    if (
        not isinstance(raw_allocations, list)
        or len(raw_allocations) != len(expected_tensors)
    ):
        raise IndependentCheckError("HBM allocation count differs from initializers")
    occupied: list[tuple[int, int, str]] = []
    by_tensor: dict[str, dict[str, Any]] = {}
    reconstructed: list[dict[str, Any]] = []
    symbols = model.symbol_by_id
    for index, (raw, tensor) in enumerate(
        zip(raw_allocations, expected_tensors, strict=True)
    ):
        if not isinstance(raw, dict):
            raise IndependentCheckError(f"HBM allocation {index} is not an object")
        exact_keys(
            raw,
            {
                "address",
                "dtype",
                "payload_sha256",
                "shape",
                "size_bytes",
                "tensor_id",
            },
            set(),
            f"HBM allocation {index}",
        )
        address = require_int(
            raw["address"], f"HBM allocation {index}.address", minimum=0
        )
        size = require_int(
            raw["size_bytes"], f"HBM allocation {index}.size_bytes", minimum=1
        )
        require_sha256(raw["payload_sha256"], f"HBM allocation {index}.payload_sha256")
        if (
            raw["tensor_id"] != tensor.tensor_id
            or raw["dtype"] != tensor.dtype
            or raw["shape"] != list(tensor.resolved_shape(symbols))
            or size != tensor.size_bytes(symbols)
        ):
            raise IndependentCheckError(
                f"HBM allocation {index} differs from tensor {tensor.tensor_id!r}"
            )
        if address % capability.hbm.burst_bytes:
            raise IndependentCheckError(
                f"HBM tensor {tensor.tensor_id!r} is not burst aligned"
            )
        end = address + size
        if end > len(image):
            raise IndependentCheckError(
                f"HBM tensor {tensor.tensor_id!r} exceeds the image"
            )
        if occupied and address < occupied[-1][1]:
            raise IndependentCheckError("HBM allocations overlap or are unordered")
        occupied.append((address, end, tensor.tensor_id))
        payload = image[address:end]
        if sha256_bytes(payload) != raw["payload_sha256"]:
            raise IndependentCheckError(
                f"HBM payload hash mismatch for {tensor.tensor_id!r}"
            )
        decoded = _decode_payload(tensor, payload)
        if decoded != tensor.values:
            raise IndependentCheckError(
                f"HBM payload values differ for {tensor.tensor_id!r}"
            )
        by_tensor[tensor.tensor_id] = raw
        reconstructed.append(
            {
                "payload_sha256": raw["payload_sha256"],
                "size_bytes": size,
                "tensor_id": tensor.tensor_id,
            }
        )
    cursor = 0
    for start, end, _ in occupied:
        if any(image[cursor:start]):
            raise IndependentCheckError("HBM inter-allocation padding is nonzero")
        cursor = end
    if any(image[cursor:]):
        raise IndependentCheckError("HBM terminal padding is nonzero")
    return by_tensor, reconstructed


def _expected_lifetimes(model: ModelGraph) -> dict[str, tuple[int, int]]:
    first: dict[str, int] = {}
    last: dict[str, int] = {}
    for operation in model.operations:
        for tensor_id in operation.inputs:
            first.setdefault(tensor_id, 0)
            last[tensor_id] = operation.index
        for tensor_id in operation.outputs:
            first.setdefault(tensor_id, operation.index)
            last.setdefault(tensor_id, operation.index)
    for tensor_id in model.outputs:
        last[tensor_id] = len(model.operations)
    return {key: (first[key], last[key]) for key in first}


def _validate_sram(
    plan_sram: Any,
    model: ModelGraph,
    capability: Capability,
) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    if not isinstance(plan_sram, dict):
        raise IndependentCheckError("physical plan SRAM record must be an object")
    exact_keys(
        plan_sram,
        {
            "allocations",
            "banks",
            "bytes_per_bank",
            "capacity_bytes",
            "staging",
            "word_bytes",
        },
        set(),
        "physical plan SRAM",
    )
    if (
        plan_sram["banks"] != capability.sram.banks
        or plan_sram["bytes_per_bank"] != capability.sram.bytes_per_bank
        or plan_sram["capacity_bytes"] != capability.sram.capacity_bytes
        or plan_sram["word_bytes"] != capability.sram.word_bytes
    ):
        raise IndependentCheckError("SRAM physical plan differs from capability")
    expected = [
        tensor
        for tensor in model.tensors
        if tensor.role not in {"weight", "constant"}
    ]
    allocations = plan_sram["allocations"]
    if not isinstance(allocations, list) or len(allocations) != len(expected):
        raise IndependentCheckError("SRAM allocation count differs from runtime tensors")
    lifetimes = _expected_lifetimes(model)
    symbols = model.symbol_by_id
    intervals: list[tuple[int, int, str]] = []
    by_tensor: dict[str, dict[str, Any]] = {}
    for index, (raw, tensor) in enumerate(zip(allocations, expected, strict=True)):
        if not isinstance(raw, dict):
            raise IndependentCheckError(f"SRAM allocation {index} is not an object")
        exact_keys(
            raw,
            {
                "address",
                "bank",
                "dtype",
                "lifetime",
                "offset_bytes",
                "role",
                "shape",
                "size_bytes",
                "tensor_id",
            },
            set(),
            f"SRAM allocation {index}",
        )
        bank = require_int(
            raw["bank"],
            f"SRAM allocation {index}.bank",
            minimum=0,
            maximum=capability.sram.banks - 1,
        )
        offset = require_int(
            raw["offset_bytes"], f"SRAM allocation {index}.offset_bytes", minimum=0
        )
        address = require_int(
            raw["address"], f"SRAM allocation {index}.address", minimum=0
        )
        size = require_int(
            raw["size_bytes"], f"SRAM allocation {index}.size_bytes", minimum=1
        )
        if (
            raw["tensor_id"] != tensor.tensor_id
            or raw["dtype"] != tensor.dtype
            or raw["role"] != tensor.role
            or raw["shape"] != list(tensor.resolved_shape(symbols))
            or size != tensor.size_bytes(symbols)
        ):
            raise IndependentCheckError(
                f"SRAM allocation {index} differs from tensor {tensor.tensor_id!r}"
            )
        if (
            offset % capability.sram.word_bytes
            or address != bank * capability.sram.bytes_per_bank + offset
            or offset + size > capability.sram.bytes_per_bank
        ):
            raise IndependentCheckError(
                f"SRAM allocation {tensor.tensor_id!r} has illegal bank bounds"
            )
        start, end = lifetimes[tensor.tensor_id]
        if raw["lifetime"] != {
            "end_operation": end,
            "start_operation": start,
        }:
            raise IndependentCheckError(
                f"SRAM allocation {tensor.tensor_id!r} lifetime differs"
            )
        intervals.append((address, address + size, tensor.tensor_id))
        by_tensor[tensor.tensor_id] = raw
    staging = plan_sram["staging"]
    if not isinstance(staging, dict):
        raise IndependentCheckError("SRAM staging record is not an object")
    exact_keys(
        staging,
        {"address", "bank", "id", "offset_bytes", "size_bytes"},
        set(),
        "SRAM staging",
    )
    if staging["id"] != STAGING_ID:
        raise IndependentCheckError("SRAM staging identity differs")
    stage_bank = require_int(
        staging["bank"],
        "SRAM staging.bank",
        minimum=0,
        maximum=capability.sram.banks - 1,
    )
    stage_offset = require_int(
        staging["offset_bytes"], "SRAM staging.offset_bytes", minimum=0
    )
    stage_address = require_int(
        staging["address"], "SRAM staging.address", minimum=0
    )
    stage_size = require_int(
        staging["size_bytes"], "SRAM staging.size_bytes", minimum=1
    )
    if (
        stage_address
        != stage_bank * capability.sram.bytes_per_bank + stage_offset
        or stage_offset % capability.sram.word_bytes
        or stage_size % capability.sram.word_bytes
        or stage_offset + stage_size > capability.sram.bytes_per_bank
    ):
        raise IndependentCheckError("SRAM staging has illegal bank bounds")
    intervals.append((stage_address, stage_address + stage_size, STAGING_ID))
    intervals.sort()
    for left, right in zip(intervals, intervals[1:]):
        if right[0] < left[1]:
            raise IndependentCheckError(
                f"SRAM intervals {left[2]!r} and {right[2]!r} overlap"
            )
    return by_tensor, staging


def _validate_physical_plan(
    root: Path,
    raw: dict[str, Any],
    model: ModelGraph,
    capability: Capability,
) -> tuple[
    dict[str, dict[str, Any]],
    dict[str, dict[str, Any]],
    dict[str, Any],
    list[dict[str, Any]],
]:
    exact_keys(
        raw,
        {
            "schema",
            "physical_plan_id",
            "address_unit",
            "capability_id",
            "model_id",
            "hbm",
            "sram",
        },
        set(),
        "physical plan",
    )
    if raw["schema"] != PHYSICAL_PLAN_SCHEMA:
        raise IndependentCheckError("unsupported physical-plan schema")
    if raw["physical_plan_id"] != _body_id(raw, "physical_plan_id"):
        raise IndependentCheckError("physical-plan identity mismatch")
    if (
        raw["address_unit"] != "byte"
        or raw["capability_id"] != capability.capability_id
        or raw["model_id"] != model.model_id
    ):
        raise IndependentCheckError("physical-plan identity binding mismatch")
    hbm, reconstructed = _validate_hbm(root, raw["hbm"], model, capability)
    sram, staging = _validate_sram(raw["sram"], model, capability)
    return hbm, sram, staging, reconstructed


def _bank(address: int, capability: Capability) -> int:
    bank = address // capability.sram.bytes_per_bank
    if bank < 0 or bank >= capability.sram.banks:
        raise IndependentCheckError(f"SRAM address {address} has no legal bank")
    return bank


def _read_cycles(
    ranges: list[tuple[int, int]],
    capability: Capability,
) -> int:
    words_by_bank: dict[int, int] = {}
    for address, size in ranges:
        bank = _bank(address, capability)
        words_by_bank[bank] = words_by_bank.get(bank, 0) + _ceil_div(
            size, capability.sram.word_bytes
        )
    if not words_by_bank:
        return 0
    return max(
        capability.sram.read_latency_cycles
        + _ceil_div(words, capability.sram.read_ports_per_bank)
        for words in words_by_bank.values()
    )


def _write_cycles(address: int, size: int, capability: Capability) -> int:
    _bank(address, capability)
    words = _ceil_div(size, capability.sram.word_bytes)
    return capability.sram.write_latency_cycles + _ceil_div(
        words, capability.sram.write_ports_per_bank
    )


def _validate_commands_and_expectations(
    commands: tuple[Command, ...],
    kernels: list[dict[str, Any]],
    model: ModelGraph,
    capability: Capability,
    hbm: Mapping[str, dict[str, Any]],
    sram: Mapping[str, dict[str, Any]],
    staging: Mapping[str, Any],
) -> dict[str, int]:
    expected_count = len(model.operations) * 2 + 1
    if len(commands) != expected_count:
        raise IndependentCheckError(
            f"command count {len(commands)} differs from expected {expected_count}"
        )
    counters = {key: 0 for key in COUNTER_KEYS}
    symbols = model.symbol_by_id
    tensors = model.tensor_by_id
    command_cursor = 0
    for kernel, operation in zip(kernels, model.operations, strict=True):
        dma = commands[command_cursor]
        compute = commands[command_cursor + 1]
        command_cursor += 2
        weight_id = operation.inputs[1]
        weight = hbm[weight_id]
        expected_dma = {
            "kernel_index": operation.index,
            "source0": weight["address"],
            "source1": 0,
            "destination": staging["address"],
            "auxiliary": 0,
            "size0": weight["size_bytes"],
            "size1": 0,
            "size2": 0,
            "size3": 0,
        }
        if dma.opcode != Opcode.DMA_HBM_TO_SRAM or any(
            getattr(dma, field) != value for field, value in expected_dma.items()
        ):
            raise IndependentCheckError(
                f"DMA command for operation {operation.operation_id!r} differs"
            )
        if weight["size_bytes"] > staging["size_bytes"]:
            raise IndependentCheckError(
                f"weight {weight_id!r} exceeds the SRAM staging allocation"
            )
        burst = capability.hbm.burst_bytes
        first_burst = weight["address"] // burst
        last_burst = _ceil_div(weight["address"] + weight["size_bytes"], burst)
        transactions = last_burst - first_burst
        transferred = transactions * burst
        issue_cycles = _ceil_div(
            transferred,
            capability.dma.issue_bytes_per_cycle * capability.dma.count,
        )
        sram_service = _write_cycles(
            staging["address"], weight["size_bytes"], capability
        )
        dma_cycles = capability.hbm.read_latency_cycles + max(
            issue_cycles, sram_service
        )
        counters["dma_commands"] += 1
        counters["dma_cycles"] += dma_cycles
        counters["hbm_read_transactions"] += transactions
        counters["hbm_transferred_bytes_read"] += transferred
        counters["hbm_useful_bytes_read"] += weight["size_bytes"]
        counters["sram_bytes_written"] += weight["size_bytes"]

        left = tensors[operation.inputs[0]]
        output = tensors[operation.outputs[0]]
        left_bytes = left.size_bytes(symbols)
        weight_bytes = tensors[weight_id].size_bytes(symbols)
        output_bytes = output.size_bytes(symbols)
        if operation.kind == "MATMUL":
            m, k = left.resolved_shape(symbols)
            n, _ = tensors[weight_id].resolved_shape(symbols)
            expected_compute = {
                "kernel_index": operation.index,
                "source0": sram[operation.inputs[0]]["address"],
                "source1": staging["address"],
                "destination": sram[operation.outputs[0]]["address"],
                "auxiliary": 0,
                "size0": m,
                "size1": n,
                "size2": k,
                "size3": 0,
            }
            if compute.opcode != Opcode.MATMUL_I8_I8_I32 or any(
                getattr(compute, field) != value
                for field, value in expected_compute.items()
            ):
                raise IndependentCheckError(
                    f"MATMUL command for {operation.operation_id!r} differs"
                )
            macs = m * n * k
            compute_cycles = capability.tensor.setup_cycles + _ceil_div(
                macs,
                capability.tensor.macs_per_cycle * capability.tensor.count,
            )
            cycles = (
                _read_cycles(
                    [
                        (compute.source0, left_bytes),
                        (compute.source1, weight_bytes),
                    ],
                    capability,
                )
                + compute_cycles
                + _write_cycles(compute.destination, output_bytes, capability)
            )
            counters["tensor_commands"] += 1
            counters["tensor_cycles"] += cycles
            counters["scalar_multiply_operations"] += macs
            counters["scalar_accumulate_add_operations"] += macs
        elif operation.kind == "ADD":
            elements = left.element_count(symbols)
            expected_compute = {
                "kernel_index": operation.index,
                "source0": sram[operation.inputs[0]]["address"],
                "source1": staging["address"],
                "destination": sram[operation.outputs[0]]["address"],
                "auxiliary": 0,
                "size0": elements,
                "size1": 0,
                "size2": 0,
                "size3": 0,
            }
            if compute.opcode != Opcode.ADD_I32 or any(
                getattr(compute, field) != value
                for field, value in expected_compute.items()
            ):
                raise IndependentCheckError(
                    f"ADD command for {operation.operation_id!r} differs"
                )
            vector_compute = capability.vector.setup_cycles + _ceil_div(
                elements,
                capability.vector.elements_per_cycle * capability.vector.count,
            )
            cycles = (
                _read_cycles(
                    [
                        (compute.source0, left_bytes),
                        (compute.source1, weight_bytes),
                    ],
                    capability,
                )
                + vector_compute
                + _write_cycles(compute.destination, output_bytes, capability)
            )
            counters["vector_commands"] += 1
            counters["vector_cycles"] += cycles
            counters["elementwise_add_operations"] += elements
        else:
            raise IndependentCheckError(
                f"unqualified operation {operation.kind!r} reached commands"
            )
        counters["sram_bytes_read"] += left_bytes + weight_bytes
        counters["sram_bytes_written"] += output_bytes
        counters["semantic_operations_executed"] += 1

    complete = commands[-1]
    if (
        complete.opcode != Opcode.COMPLETE
        or complete.kernel_index != 0xFFFFFFFF
        or any(
            (
                complete.source0,
                complete.source1,
                complete.destination,
                complete.auxiliary,
                complete.size0,
                complete.size1,
                complete.size2,
                complete.size3,
            )
        )
    ):
        raise IndependentCheckError("terminal COMPLETE command differs")
    input_bytes = sum(
        tensor.size_bytes(symbols) for tensor in model.tensors if tensor.role == "input"
    )
    counters["host_input_bytes_written"] = input_bytes
    counters["sram_bytes_written"] += input_bytes
    counters["completion_events"] = 1
    counters["control_cycles"] = 1
    counters["commands_executed"] = len(commands)
    counters["cycles"] = (
        counters["dma_cycles"]
        + counters["tensor_cycles"]
        + counters["vector_cycles"]
        + counters["control_cycles"]
    )
    return counters


def check_candidate(
    *,
    source_model: Path,
    source_capability: Path,
    root: Path,
) -> dict[str, Any]:
    """Independently reconstruct one candidate deployment before publication."""

    try:
        model = load_model_graph(source_model, require_initializers=True)
        capability = load_capability(source_capability)
        runtime_capability = load_strict_json(root / "capability.json")
        if runtime_capability != capability.to_dict():
            raise IndependentCheckError(
                "deployed capability differs from the source capability"
            )
        _validate_runtime_graph(root, model)
        kernels = _validate_kernel_ir(
            load_strict_json(root / "ir/tensor_kernel_ir.json"),
            model,
            capability,
        )
        hbm, sram, staging, reconstructed = _validate_physical_plan(
            root,
            load_strict_json(root / "physical/physical_plan.json"),
            model,
            capability,
        )
        command_payload = (root / "program/commands.bin").read_bytes()
        commands = decode(command_payload)
        expected = _validate_commands_and_expectations(
            commands,
            kernels,
            model,
            capability,
            hbm,
            sram,
            staging,
        )
        return {
            "capability_id": capability.capability_id,
            "command_count": len(commands),
            "command_sha256": sha256_bytes(command_payload),
            "expected_counters": expected,
            "hbm_image_sha256": sha256_bytes((root / HBM_IMAGE_PATH).read_bytes()),
            "model_id": model.model_id,
            "physical_plan_id": load_strict_json(
                root / "physical/physical_plan.json"
            )["physical_plan_id"],
            "reconstructed_tensors": reconstructed,
            "schema": CHECK_SCHEMA,
            "semantic_sha256": sha256_bytes(
                canonical_json_bytes(model.to_dict(include_values=True))
            ),
            "status": "pass",
        }
    except IndependentCheckError:
        raise
    except (ArtifactError, OSError, ValueError, KeyError, TypeError) as exc:
        raise IndependentCheckError(f"independent deployment check failed: {exc}") from exc


def expectations_from_check(report: Mapping[str, Any]) -> dict[str, Any]:
    if (
        report.get("schema") != CHECK_SCHEMA
        or report.get("status") != "pass"
        or not isinstance(report.get("expected_counters"), dict)
        or set(report["expected_counters"]) != set(COUNTER_KEYS)
    ):
        raise IndependentCheckError("independent report cannot seed expectations")
    return {
        "capability_id": report["capability_id"],
        "counters": dict(report["expected_counters"]),
        "model_id": report["model_id"],
        "schema": EXPECTATIONS_SCHEMA,
    }
