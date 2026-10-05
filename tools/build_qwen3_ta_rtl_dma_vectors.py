#!/usr/bin/env python3
"""Build authentic layer-0 DMA_HBM_TO_SRAM RTL vectors from Qwen evidence."""

from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path
import sys
from typing import Any

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from compiler.frontend.checkpoint import (  # noqa: E402
    LockedCheckpointReader,
    load_checkpoint_lock,
)
from compiler.tensor_accelerator.common import (  # noqa: E402
    canonical_json_bytes,
    load_strict_json,
)


SCHEMA = "opentallas.tensor_accelerator.qwen_rtl_dma_vectors.v1"
BUILD_ID = "3460d88ce16f5ef0ca4d1277daf8ebb19ae555e88822f95d55deb4aa8cad290f"
PROGRAM_SHA256 = "f0ce6b50b01f462f837a28504e6ff9a024a24d24abf339f924875d0c2059bcec"
COMMAND_VECTOR_SET_ID = (
    "420ada71f902c8e43b9e5866d9c57ab8e3a1ced59e25c01b20793c94cf45b1a2"
)
CHECKPOINT_LOCK_ID = (
    "fa32932d73c1f605a69db3a803f1f25ef5b022a98cc3c6b5fe42b7f7af024e2a"
)
PHYSICAL_PLAN_ID = (
    "ba1d95462450d2cd059e6b55271c73ea90895515c9a4129bba1b51df265109c3"
)
TENSOR_NAME = "model.layers.0.input_layernorm.weight"
PAYLOAD_SHA256 = "00695bad97c2abc77a9d1ce57e4d4a5e5c2b574387fcb4029ef5ce12239b2530"
TRANSFER_BYTES = 8192
HBM_BURST_BYTES = 64
SRAM_WORD_BYTES = 16
OPERATION = {
    "command_count": 2,
    "command_start": 1,
    "kernel_index": 1,
    "operation_id": "node.0001",
    "selected_command_index": 1,
    "tensor_id": TENSOR_NAME,
}


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(
        description="Build authentic Qwen HBM-to-SRAM DMA RTL vectors"
    )
    result.add_argument("--snapshot", required=True, type=Path)
    result.add_argument("--checkpoint-lock", required=True, type=Path)
    result.add_argument("--physical-plan", required=True, type=Path)
    result.add_argument("--command-vectors", required=True, type=Path)
    result.add_argument("--output", required=True, type=Path)
    return result


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _identity(value: dict[str, Any], field: str) -> str:
    body = {key: item for key, item in value.items() if key != field}
    return _sha256(canonical_json_bytes(body))


def build(
    *,
    snapshot: Path,
    checkpoint_lock_path: Path,
    physical_plan_path: Path,
    command_vectors_path: Path,
) -> dict[str, Any]:
    physical_plan = load_strict_json(physical_plan_path)
    command_vectors = load_strict_json(command_vectors_path)
    if (
        physical_plan.get("physical_plan_id") != PHYSICAL_PLAN_ID
        or physical_plan.get("command_program", {}).get("sha256") != PROGRAM_SHA256
        or command_vectors.get("build_id") != BUILD_ID
        or command_vectors.get("vector_set_id") != COMMAND_VECTOR_SET_ID
        or command_vectors.get("command_program_sha256") != PROGRAM_SHA256
    ):
        raise ValueError("Qwen DMA physical or command evidence differs")

    commands = [
        item
        for item in command_vectors.get("vectors", [])
        if item.get("name") == "dma_hbm_to_sram"
    ]
    weights = [
        item
        for item in physical_plan.get("hbm", {}).get("weights", [])
        if item.get("consumer_kernel_index") == 1
    ]
    ranges = [
        item
        for item in physical_plan.get("command_program", {}).get(
            "kernel_command_ranges", []
        )
        if item.get("kernel_index") == 1
    ]
    if len(commands) != 1 or len(weights) != 1 or len(ranges) != 1:
        raise ValueError("Qwen DMA command or physical coverage differs")
    command = commands[0]
    weight = weights[0]
    if (
        ranges[0] != {
            "command_count": 2,
            "command_start": 1,
            "kernel_index": 1,
            "operation_id": "node.0001",
        }
        or command.get("expected_fields")
        != {
            "auxiliary": 0,
            "destination": 2 * 1024 * 1024,
            "engine": 1,
            "flags": 0,
            "index": 1,
            "kernel_index": 1,
            "opcode": 1,
            "size0": TRANSFER_BYTES,
            "size1": 0,
            "size2": 0,
            "size3": 0,
            "source0": 1244659712,
            "source1": 0,
        }
        or weight.get("tensor_id") != TENSOR_NAME
        or weight.get("layout") != "direct_vector_bf16"
        or weight.get("address") != command["expected_fields"]["source0"]
        or weight.get("size_bytes") != TRANSFER_BYTES
        or weight.get("deployed_payload_sha256") != PAYLOAD_SHA256
        or weight.get("source", {}).get("payload_sha256") != PAYLOAD_SHA256
    ):
        raise ValueError("Qwen DMA semantic, command, or HBM binding differs")

    lock = load_checkpoint_lock(checkpoint_lock_path)
    if lock.get("lock_id") != CHECKPOINT_LOCK_ID:
        raise ValueError("Qwen checkpoint lock differs")
    payload = bytearray()
    with LockedCheckpointReader(snapshot, lock) as reader:
        record = reader.consume_tensor_payload(TENSOR_NAME, payload.extend)
    if (
        record.get("shape") != [4096]
        or record.get("dtype") != "BF16"
        or len(payload) != TRANSFER_BYTES
        or _sha256(bytes(payload)) != PAYLOAD_SHA256
    ):
        raise ValueError("Qwen DMA checkpoint payload differs")

    fields = command["expected_fields"]
    body = {
        "build_id": BUILD_ID,
        "checkpoint_lock_id": CHECKPOINT_LOCK_ID,
        "claim_boundary": {
            "complete_dma_command": True,
            "complete_layer_execution": False,
            "external_hbm_response_boundary": True,
            "qualified_hbm_phy": False,
            "qualified_sram_macro": False,
            "ta_rtl_6_closed": False,
            "timing_or_performance": False,
        },
        "command": command,
        "command_program_sha256": PROGRAM_SHA256,
        "command_vector_set_id": COMMAND_VECTOR_SET_ID,
        "hbm": {
            "address": fields["source0"],
            "burst_bytes": HBM_BURST_BYTES,
            "burst_count": TRANSFER_BYTES // HBM_BURST_BYTES,
            "payload_hex": bytes(payload).hex(),
            "payload_sha256": PAYLOAD_SHA256,
            "size_bytes": TRANSFER_BYTES,
        },
        "operation": OPERATION,
        "physical_plan_id": PHYSICAL_PLAN_ID,
        "schema": SCHEMA,
        "sram": {
            "address": fields["destination"],
            "word_bytes": SRAM_WORD_BYTES,
            "write_count": TRANSFER_BYTES // SRAM_WORD_BYTES,
        },
    }
    return {**body, "vector_set_id": _identity(body, "vector_set_id")}


def main(argv: list[str] | None = None) -> int:
    arguments = parser().parse_args(argv)
    if arguments.output.exists():
        parser().error(f"--output already exists: {arguments.output}")
    vectors = build(
        snapshot=arguments.snapshot,
        checkpoint_lock_path=arguments.checkpoint_lock,
        physical_plan_path=arguments.physical_plan,
        command_vectors_path=arguments.command_vectors,
    )
    schema_path = (
        ROOT
        / "schemas/compiler/tensor_accelerator/qwen_rtl_dma_vectors_v1.schema.json"
    )
    schema = load_strict_json(schema_path)
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(vectors)
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    with arguments.output.open("xb") as handle:
        handle.write(canonical_json_bytes(vectors))
        handle.flush()
        os.fsync(handle.fileno())
    print(vectors["vector_set_id"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
