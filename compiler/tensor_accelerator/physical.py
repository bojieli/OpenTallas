"""Deterministic HBM placement, SRAM allocation, and command generation."""

from __future__ import annotations

from dataclasses import dataclass
import struct
from typing import Any, Mapping

from .capability import Capability
from .command import Command, Engine, NO_KERNEL, Opcode
from .common import align_up, canonical_json_bytes, sha256_bytes
from .model import ModelGraph, Tensor


PHYSICAL_PLAN_SCHEMA = "opentallas.tensor_accelerator.physical_plan.v1"
HBM_IMAGE_PATH = "memory/hbm_weights.bin"
STAGING_ID = "sram.weight_staging"


class PhysicalPlanError(RuntimeError):
    """Raised when a legal HBM/SRAM deployment cannot be constructed."""


def encode_tensor_payload(tensor: Tensor) -> bytes:
    if tensor.values is None:
        raise PhysicalPlanError(f"tensor {tensor.tensor_id!r} lacks payload values")
    if tensor.dtype == "i8":
        try:
            return struct.pack(f"<{len(tensor.values)}b", *tensor.values)
        except struct.error as exc:  # Parser validation should make this unreachable.
            raise PhysicalPlanError(
                f"cannot encode i8 tensor {tensor.tensor_id!r}: {exc}"
            ) from exc
    if tensor.dtype == "i32":
        try:
            return struct.pack(f"<{len(tensor.values)}i", *tensor.values)
        except struct.error as exc:
            raise PhysicalPlanError(
                f"cannot encode i32 tensor {tensor.tensor_id!r}: {exc}"
            ) from exc
    raise PhysicalPlanError(
        f"payload encoding for dtype {tensor.dtype!r} is not qualified"
    )


def _build_hbm(
    model: ModelGraph,
    capability: Capability,
) -> tuple[bytes, list[dict[str, Any]]]:
    cursor = 0
    image = bytearray()
    allocations: list[dict[str, Any]] = []
    symbols = model.symbol_by_id
    for tensor in model.tensors:
        if tensor.role not in {"weight", "constant"}:
            continue
        payload = encode_tensor_payload(tensor)
        expected_size = tensor.size_bytes(symbols)
        if len(payload) != expected_size:
            raise PhysicalPlanError(
                f"encoded tensor {tensor.tensor_id!r} size differs from semantic size"
            )
        address = align_up(cursor, capability.hbm.burst_bytes)
        if address > len(image):
            image.extend(bytes(address - len(image)))
        image.extend(payload)
        cursor = address + len(payload)
        allocations.append(
            {
                "address": address,
                "dtype": tensor.dtype,
                "payload_sha256": sha256_bytes(payload),
                "shape": list(tensor.resolved_shape(symbols)),
                "size_bytes": len(payload),
                "tensor_id": tensor.tensor_id,
            }
        )
    final_size = align_up(cursor, capability.hbm.burst_bytes)
    image.extend(bytes(final_size - len(image)))
    if len(image) > capability.hbm.capacity_bytes:
        raise PhysicalPlanError(
            f"HBM image requires {len(image)} bytes, capability has "
            f"{capability.hbm.capacity_bytes}"
        )
    return bytes(image), allocations


@dataclass
class _BankAllocator:
    capability: Capability
    cursors: list[int]

    @classmethod
    def create(cls, capability: Capability) -> "_BankAllocator":
        return cls(capability, [0] * capability.sram.banks)

    def allocate(
        self,
        *,
        size_bytes: int,
        preferred_bank: int,
        label: str,
    ) -> tuple[int, int, int]:
        word = self.capability.sram.word_bytes
        candidates = [
            (preferred_bank + offset) % self.capability.sram.banks
            for offset in range(self.capability.sram.banks)
        ]
        for bank in candidates:
            local = align_up(self.cursors[bank], word)
            end = local + size_bytes
            if end <= self.capability.sram.bytes_per_bank:
                self.cursors[bank] = end
                global_address = bank * self.capability.sram.bytes_per_bank + local
                return bank, local, global_address
        raise PhysicalPlanError(
            f"SRAM cannot allocate {size_bytes} bytes for {label!r}"
        )


def _lifetimes(model: ModelGraph) -> dict[str, tuple[int, int]]:
    first: dict[str, int] = {}
    last: dict[str, int] = {}
    for operation in model.operations:
        for tensor_id in operation.inputs:
            first.setdefault(tensor_id, 0)
            last[tensor_id] = operation.index
        for tensor_id in operation.outputs:
            first.setdefault(tensor_id, operation.index)
            last.setdefault(tensor_id, operation.index)
    terminal = len(model.operations)
    for tensor_id in model.outputs:
        last[tensor_id] = terminal
    return {tensor_id: (first[tensor_id], last[tensor_id]) for tensor_id in first}


def _build_sram(
    model: ModelGraph,
    capability: Capability,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if capability.sram.banks < 2:
        raise PhysicalPlanError(
            "qualified fixture requires at least two SRAM banks for dual-source reads"
        )
    allocator = _BankAllocator.create(capability)
    symbols = model.symbol_by_id
    lifetimes = _lifetimes(model)
    allocations: list[dict[str, Any]] = []
    runtime_tensors = [
        tensor
        for tensor in model.tensors
        if tensor.role not in {"weight", "constant"}
    ]
    for ordinal, tensor in enumerate(runtime_tensors):
        size = tensor.size_bytes(symbols)
        bank, offset, address = allocator.allocate(
            size_bytes=size,
            preferred_bank=ordinal % capability.sram.banks,
            label=tensor.tensor_id,
        )
        start, end = lifetimes.get(tensor.tensor_id, (0, len(model.operations)))
        allocations.append(
            {
                "address": address,
                "bank": bank,
                "dtype": tensor.dtype,
                "lifetime": {"end_operation": end, "start_operation": start},
                "offset_bytes": offset,
                "role": tensor.role,
                "shape": list(tensor.resolved_shape(symbols)),
                "size_bytes": size,
                "tensor_id": tensor.tensor_id,
            }
        )
    weight_sizes = [
        tensor.size_bytes(symbols)
        for tensor in model.tensors
        if tensor.role in {"weight", "constant"}
    ]
    if not weight_sizes:
        raise PhysicalPlanError("deployment contains no HBM-resident tensors")
    staging_size = align_up(max(weight_sizes), capability.sram.word_bytes)
    # Prefer the last bank to keep the fixture's activation stream separate.
    bank, offset, address = allocator.allocate(
        size_bytes=staging_size,
        preferred_bank=capability.sram.banks - 1,
        label=STAGING_ID,
    )
    staging = {
        "address": address,
        "bank": bank,
        "id": STAGING_ID,
        "offset_bytes": offset,
        "size_bytes": staging_size,
    }
    return allocations, staging


def build_physical_plan(
    model: ModelGraph,
    capability: Capability,
) -> tuple[bytes, dict[str, Any]]:
    hbm_image, hbm_allocations = _build_hbm(model, capability)
    sram_allocations, staging = _build_sram(model, capability)
    body = {
        "address_unit": "byte",
        "capability_id": capability.capability_id,
        "hbm": {
            "allocations": hbm_allocations,
            "image": {
                "path": HBM_IMAGE_PATH,
                "sha256": sha256_bytes(hbm_image),
                "size_bytes": len(hbm_image),
            },
            "padding_bytes_must_be_zero": True,
        },
        "model_id": model.model_id,
        "schema": PHYSICAL_PLAN_SCHEMA,
        "sram": {
            "allocations": sram_allocations,
            "banks": capability.sram.banks,
            "bytes_per_bank": capability.sram.bytes_per_bank,
            "capacity_bytes": capability.sram.capacity_bytes,
            "staging": staging,
            "word_bytes": capability.sram.word_bytes,
        },
    }
    plan = {**body, "physical_plan_id": sha256_bytes(canonical_json_bytes(body))}
    return hbm_image, plan


def _by_tensor(records: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {record["tensor_id"]: record for record in records}


def build_commands(
    model: ModelGraph,
    kernel_ir: Mapping[str, Any],
    physical_plan: Mapping[str, Any],
    capability: Capability,
) -> tuple[Command, ...]:
    hbm = _by_tensor(physical_plan["hbm"]["allocations"])
    sram = _by_tensor(physical_plan["sram"]["allocations"])
    staging = physical_plan["sram"]["staging"]
    commands: list[Command] = []
    for kernel in kernel_ir["kernels"]:
        kernel_index = kernel["index"]
        if kernel["kind"] == "GEMM_I8_I8_I32":
            input_id, weight_id = kernel["inputs"]
            output_id = kernel["outputs"][0]
            weight = hbm[weight_id]
            commands.append(
                Command(
                    index=len(commands),
                    opcode=Opcode.DMA_HBM_TO_SRAM,
                    engine=Engine.DMA,
                    kernel_index=kernel_index,
                    source0=weight["address"],
                    destination=staging["address"],
                    size0=weight["size_bytes"],
                )
            )
            shape = kernel["shape"]
            commands.append(
                Command(
                    index=len(commands),
                    opcode=Opcode.MATMUL_I8_I8_I32,
                    engine=Engine.TENSOR,
                    kernel_index=kernel_index,
                    source0=sram[input_id]["address"],
                    source1=staging["address"],
                    destination=sram[output_id]["address"],
                    size0=shape["m"],
                    size1=shape["n"],
                    size2=shape["k"],
                )
            )
        elif kernel["kind"] == "ADD_I32":
            input_id, weight_id = kernel["inputs"]
            output_id = kernel["outputs"][0]
            weight = hbm[weight_id]
            commands.append(
                Command(
                    index=len(commands),
                    opcode=Opcode.DMA_HBM_TO_SRAM,
                    engine=Engine.DMA,
                    kernel_index=kernel_index,
                    source0=weight["address"],
                    destination=staging["address"],
                    size0=weight["size_bytes"],
                )
            )
            commands.append(
                Command(
                    index=len(commands),
                    opcode=Opcode.ADD_I32,
                    engine=Engine.VECTOR,
                    kernel_index=kernel_index,
                    source0=sram[input_id]["address"],
                    source1=staging["address"],
                    destination=sram[output_id]["address"],
                    size0=kernel["shape"]["elements"],
                )
            )
        else:  # pragma: no cover - the kernel lowerer is fail-closed.
            raise PhysicalPlanError(f"unknown kernel kind {kernel['kind']!r}")
    commands.append(
        Command(
            index=len(commands),
            opcode=Opcode.COMPLETE,
            engine=Engine.CONTROL,
            kernel_index=NO_KERNEL,
        )
    )
    if len(commands) > capability.limits["max_commands"]:
        raise PhysicalPlanError(
            f"program has {len(commands)} commands, capability allows "
            f"{capability.limits['max_commands']}"
        )
    return tuple(commands)
