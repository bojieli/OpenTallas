#!/usr/bin/env python3
"""Build source-bound vectors for the first Qwen q_proj DMA/MATMUL pair.

Command 3 stages the first immutable q_proj BF16 weight tile and command 4
initializes one 64-lane FP32 accumulator tile from the first 256 values emitted
by command 2.  This is a graph-valid command slice, not the complete 2,048-
command node.0002 operation.
"""

from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path
import struct
import sys
from typing import Any

from jsonschema import Draft202012Validator
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from compiler.tensor_accelerator.common import (  # noqa: E402
    canonical_json_bytes,
    load_strict_json,
)
from compiler.tensor_accelerator.production_command import (  # noqa: E402
    ABI_MAJOR,
    ABI_MINOR,
    COMMAND_WITH_CRC,
    MATMUL_INIT,
    Opcode,
    command_abi,
    decode,
)
from runtime.reference.formats import (  # noqa: E402
    binary32_add,
    binary32_multiply,
)
from runtime.reference.tensor_accelerator_bf16 import (  # noqa: E402
    NUMERIC_CONTRACT,
)
from runtime.tensor_accelerator.bf16 import (  # noqa: E402
    accumulate_bf16_tile_fp32,
)


SCHEMA = "opentallas.tensor_accelerator.qwen_rtl_dma_matmul_vectors.v1"
BUILD_ID = "3460d88ce16f5ef0ca4d1277daf8ebb19ae555e88822f95d55deb4aa8cad290f"
PROGRAM_SHA256 = "f0ce6b50b01f462f837a28504e6ff9a024a24d24abf339f924875d0c2059bcec"
COMMAND_VECTOR_ID = "420ada71f902c8e43b9e5866d9c57ab8e3a1ced59e25c01b20793c94cf45b1a2"
RMSNORM_VECTOR_ID = "ce2a725cc574f334273dbfdc93e6fab7fc4da48df8d2d4087f22307635212d81"
PHYSICAL_PLAN_ID = "ba1d95462450d2cd059e6b55271c73ea90895515c9a4129bba1b51df265109c3"
KERNEL_IR_ID = "270b7609f2ea101593b3870a498bda3320336c94b27862dca7f991352727e050"
GRAPH_ID = "989ab0d4dae37c783e2eff349e1ed1fe16279288e12a19a94975f43b0254426f"
SHARD_SHA256 = "656958bc279d27f01126b855c25daeddc42f37f69445e97c2df432cee6dffb37"
PARENT_DEPLOYED_SHA256 = (
    "27406586791294918cb04052d91f7d47c41aac1af56650c4b47f68ac00f1ff9b"
)
PARENT_SOURCE_SHA256 = (
    "fd56b85bf301661c8655ed517928304d25df7d6b3ea3d9be85c021159d61bad8"
)
INPUT_SHA256 = "3e95a6a07ba5eff942a866e767b856aeb6d83def5b7f12d55983acb2afdb2551"
WEIGHT_TILE_SHA256 = "c9b6213f04cfd269acdb7124e76d3b9775965145d15defb663f02e21e34418bc"
ACCUMULATOR_SHA256 = "c82ca04197419306b6bbc545be882163e3ccccfb013773107541d3441dee8776"
COMMAND_COUNT = 924_386
SHARD_BASE = 1 << 30
SHARD_OFFSET = 170_950_656
INPUT_ELEMENTS = 256
OUTPUT_ELEMENTS = 64
WEIGHT_ELEMENTS = INPUT_ELEMENTS * OUTPUT_ELEMENTS
WEIGHT_BYTES = WEIGHT_ELEMENTS * 2


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(
        description="Build authentic Qwen command-3/4 DMA/MATMUL RTL vectors"
    )
    result.add_argument("--command-vectors", required=True, type=Path)
    result.add_argument("--rmsnorm-vectors", required=True, type=Path)
    result.add_argument("--kernel-ir", required=True, type=Path)
    result.add_argument("--physical-plan", required=True, type=Path)
    result.add_argument("--command-program", required=True, type=Path)
    result.add_argument("--hbm-shard", required=True, type=Path)
    result.add_argument("--output", required=True, type=Path)
    return result


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _identity(value: dict[str, Any], field: str) -> str:
    body = {key: item for key, item in value.items() if key != field}
    return _sha256(canonical_json_bytes(body))


def _fields(raw: bytes) -> dict[str, int]:
    values = COMMAND_WITH_CRC.unpack(raw)
    return {
        "auxiliary": values[8],
        "destination": values[7],
        "engine": values[1],
        "flags": values[2],
        "index": values[3],
        "kernel_index": values[4],
        "opcode": values[0],
        "size0": values[9],
        "size1": values[10],
        "size2": values[11],
        "size3": values[12],
        "source0": values[5],
        "source1": values[6],
    }


def _vector(name: str, raw: bytes) -> dict[str, Any]:
    fields = _fields(raw)
    return {
        "abi_major": ABI_MAJOR,
        "abi_minor": ABI_MINOR,
        "expected_error": 0,
        "expected_fields": fields,
        "expected_index": fields["index"],
        "name": name,
        "record_hex": f"{int.from_bytes(raw, 'little'):0128x}",
    }


def _raw_record(payload: bytes, index: int) -> bytes:
    start = 32 + index * COMMAND_WITH_CRC.size
    return payload[start : start + COMMAND_WITH_CRC.size]


def build(
    *,
    command_vectors_path: Path,
    rmsnorm_vectors_path: Path,
    kernel_ir_path: Path,
    physical_plan_path: Path,
    command_program_path: Path,
    hbm_shard_path: Path,
) -> dict[str, Any]:
    command_vectors = load_strict_json(command_vectors_path)
    rmsnorm_vectors = load_strict_json(rmsnorm_vectors_path)
    kernel_ir = load_strict_json(kernel_ir_path)
    physical_plan = load_strict_json(physical_plan_path)
    if (
        command_vectors.get("vector_set_id") != COMMAND_VECTOR_ID
        or command_vectors.get("vector_set_id")
        != _identity(command_vectors, "vector_set_id")
        or rmsnorm_vectors.get("vector_set_id") != RMSNORM_VECTOR_ID
        or rmsnorm_vectors.get("vector_set_id")
        != _identity(rmsnorm_vectors, "vector_set_id")
        or kernel_ir.get("kernel_ir_id") != KERNEL_IR_ID
        or kernel_ir.get("kernel_ir_id") != _identity(kernel_ir, "kernel_ir_id")
        or kernel_ir.get("graph_id") != GRAPH_ID
        or physical_plan.get("physical_plan_id") != PHYSICAL_PLAN_ID
        or physical_plan.get("physical_plan_id")
        != _identity(physical_plan, "physical_plan_id")
        or physical_plan.get("graph_id") != GRAPH_ID
        or physical_plan.get("semantic_kernel_ir_id") != KERNEL_IR_ID
    ):
        raise ValueError("retained Qwen source identities differ")
    for source in (command_vectors, rmsnorm_vectors):
        if (
            source.get("build_id") != BUILD_ID
            or source.get("command_program_sha256") != PROGRAM_SHA256
        ):
            raise ValueError("retained Qwen build/program identity differs")

    program = command_program_path.read_bytes()
    if _sha256(program) != PROGRAM_SHA256 or command_abi(program) != (
        ABI_MAJOR,
        ABI_MINOR,
    ):
        raise ValueError("complete Qwen command program differs")
    commands = decode(program)
    if len(commands) != COMMAND_COUNT:
        raise ValueError("complete Qwen command count differs")
    dma = commands[3]
    matmul = commands[4]
    expected_dma = {
        "auxiliary": 0,
        "destination": 4_194_304,
        "engine": 1,
        "flags": 0,
        "index": 3,
        "kernel_index": 2,
        "opcode": int(Opcode.DMA_HBM_TO_SRAM),
        "size0": WEIGHT_BYTES,
        "size1": 0,
        "size2": 0,
        "size3": 0,
        "source0": 1_244_692_480,
        "source1": 0,
    }
    expected_matmul = {
        "auxiliary": 6_291_456,
        "destination": 5_242_880,
        "engine": 2,
        "flags": MATMUL_INIT,
        "index": 4,
        "kernel_index": 2,
        "opcode": int(Opcode.MATMUL_BF16_TILE),
        "size0": 1,
        "size1": OUTPUT_ELEMENTS,
        "size2": INPUT_ELEMENTS,
        "size3": 0,
        "source0": 3_145_728,
        "source1": 4_194_304,
    }
    dma_raw = _raw_record(program, 3)
    matmul_raw = _raw_record(program, 4)
    dma_vector = _vector("dma_q_proj_weight_tile", dma_raw)
    matmul_vector = _vector("matmul_bf16_tile", matmul_raw)
    retained_matmul = next(
        item
        for item in command_vectors["vectors"]
        if item["name"] == "matmul_bf16_tile"
    )
    if (
        dma_vector["expected_fields"] != expected_dma
        or matmul_vector["expected_fields"] != expected_matmul
        or matmul_vector != retained_matmul
        or dma.destination != matmul.source1
    ):
        raise ValueError("authentic command-3/4 relationship differs")

    operation_range = next(
        item
        for item in physical_plan["command_program"]["kernel_command_ranges"]
        if item["kernel_index"] == 2
    )
    tensor = next(
        item
        for item in physical_plan["hbm"]["weights"]
        if item["tensor_id"] == "model.layers.0.self_attn.q_proj.weight"
    )
    expected_range = {
        "command_count": 2048,
        "command_start": 3,
        "kernel_index": 2,
        "operation_id": "node.0002",
    }
    if (
        operation_range != expected_range
        or tensor["address"] != dma.source0
        or tensor["access_unit_bytes"] != WEIGHT_BYTES
        or tensor["deployed_payload_sha256"] != PARENT_DEPLOYED_SHA256
        or tensor["source"]["payload_sha256"] != PARENT_SOURCE_SHA256
        or tensor["source"]["shape"] != [4096, 4096]
        or tensor["layout_details"]
        != {
            "k": 4096,
            "k_tile": 256,
            "k_tiles": 16,
            "n": 4096,
            "n_tile": 64,
            "n_tiles": 64,
            "order": "n_tile_then_k_tile",
            "tile_bytes": WEIGHT_BYTES,
            "tile_count": 1024,
        }
    ):
        raise ValueError("Qwen node.0002 physical lowering differs")
    kernel = kernel_ir["kernels"][2]
    if (
        kernel["source_operation_id"] != "node.0002"
        or kernel["kind"] != "MATMUL"
        or kernel["numeric_contract"] != NUMERIC_CONTRACT
        or kernel["inputs"]
        != [
            "layer.0.attention_norm",
            "model.layers.0.self_attn.q_proj.weight",
        ]
        or kernel["outputs"] != ["layer.0.q_raw"]
    ):
        raise ValueError("Qwen kernel IR operation node.0002 differs")

    shard_record = next(
        item
        for item in physical_plan["hbm"]["image"]["shards"]
        if item["logical_offset"] == SHARD_BASE
    )
    if (
        shard_record["sha256"] != SHARD_SHA256
        or shard_record["size_bytes"] != 1 << 30
        or hbm_shard_path.name != Path(shard_record["path"]).name
        or hbm_shard_path.stat().st_size != shard_record["size_bytes"]
        or _sha256_file(hbm_shard_path) != SHARD_SHA256
        or dma.source0 - SHARD_BASE != SHARD_OFFSET
    ):
        raise ValueError("immutable HBM shard identity differs")
    with hbm_shard_path.open("rb") as handle:
        handle.seek(SHARD_OFFSET)
        weight_payload = handle.read(WEIGHT_BYTES)
    if (
        len(weight_payload) != WEIGHT_BYTES
        or _sha256(weight_payload) != WEIGHT_TILE_SHA256
    ):
        raise ValueError("first q_proj weight tile differs")

    input_codes = list(rmsnorm_vectors["expected_codes"][:INPUT_ELEMENTS])
    input_payload = struct.pack(f"<{INPUT_ELEMENTS}H", *input_codes)
    weight_flat = np.frombuffer(weight_payload, dtype="<u2")
    weights = weight_flat.reshape(OUTPUT_ELEMENTS, INPUT_ELEMENTS)
    if _sha256(input_payload) != INPUT_SHA256:
        raise ValueError("first command-2 output slice differs")
    optimized = (
        accumulate_bf16_tile_fp32(
            np.asarray(input_codes, dtype=np.uint16).reshape(1, INPUT_ELEMENTS),
            weights,
        )
        .values.reshape(-1)
        .astype(int)
        .tolist()
    )
    scalar: list[int] = []
    for row in weights.astype(int).tolist():
        accumulator = 0
        for left, right in zip(input_codes, row, strict=True):
            product = binary32_multiply(left << 16, right << 16)
            accumulator = binary32_add(accumulator, product)
        scalar.append(accumulator)
    accumulator_payload = struct.pack(f"<{OUTPUT_ELEMENTS}I", *scalar)
    if (
        scalar != optimized
        or _sha256(accumulator_payload) != ACCUMULATOR_SHA256
        or any((code >> 23) & 0xFF == 0xFF for code in scalar)
    ):
        raise ValueError("independent command-4 arithmetic correlation differs")

    body: dict[str, Any] = {
        "build_id": BUILD_ID,
        "claim_boundary": {
            "authentic_command_records": True,
            "behavioral_hbm_and_sram": True,
            "bf16_final_output_written": False,
            "complete_layer_execution": False,
            "complete_matmul_command": True,
            "complete_q_projection_graph_operation": False,
            "graph_valid_qwen_command_slice": True,
            "preloaded_attention_norm_slice": True,
            "program_order_and_fail_stop": True,
            "qualified_hbm_phy": False,
            "qualified_sram_macro": False,
            "raw_fp32_accumulator_tile_written": True,
            "ta_rtl_6_closed": False,
            "timing_or_performance": False,
        },
        "command_program_sha256": PROGRAM_SHA256,
        "command_vector_set_id": COMMAND_VECTOR_ID,
        "commands": [
            {"last": False, **dma_vector},
            {"last": True, **matmul_vector},
        ],
        "composition": {
            "accumulator_address": matmul.destination,
            "accumulator_count": OUTPUT_ELEMENTS,
            "accumulator_payload_sha256": ACCUMULATOR_SHA256,
            "auxiliary_address": matmul.auxiliary,
            "auxiliary_write_count": 0,
            "dma_destination_address": dma.destination,
            "graph_command_count": 2048,
            "graph_command_end": 2050,
            "graph_command_start": 3,
            "graph_operation_id": "node.0002",
            "input_address": matmul.source0,
            "input_element_count": INPUT_ELEMENTS,
            "input_payload_sha256": INPUT_SHA256,
            "matmul_add_count": WEIGHT_ELEMENTS,
            "matmul_multiply_count": WEIGHT_ELEMENTS,
            "output_tile_index": 0,
            "parent_deployed_weight_payload_sha256": PARENT_DEPLOYED_SHA256,
            "parent_source_weight_payload_sha256": PARENT_SOURCE_SHA256,
            "submitted_command_indices": [3, 4],
            "weight_address": matmul.source1,
            "weight_element_count": WEIGHT_ELEMENTS,
            "weight_tile_index": 0,
            "weight_tile_payload_sha256": WEIGHT_TILE_SHA256,
        },
        "expected_accumulator_codes": scalar,
        "graph_id": GRAPH_ID,
        "hbm_shard": {
            "logical_base_address": SHARD_BASE,
            "path": shard_record["path"],
            "sha256": SHARD_SHA256,
            "size_bytes": shard_record["size_bytes"],
            "tile_offset_bytes": SHARD_OFFSET,
        },
        "input_codes": input_codes,
        "kernel_ir_id": KERNEL_IR_ID,
        "numeric_contract": NUMERIC_CONTRACT,
        "physical_plan_id": PHYSICAL_PLAN_ID,
        "rmsnorm_source_vector_id": RMSNORM_VECTOR_ID,
        "schema": SCHEMA,
        "weight_tile_payload_hex": weight_payload.hex(),
    }
    return {**body, "vector_set_id": _identity(body, "vector_set_id")}


def main(argv: list[str] | None = None) -> int:
    arguments = parser().parse_args(argv)
    if arguments.output.exists():
        parser().error(f"--output already exists: {arguments.output}")
    vectors = build(
        command_vectors_path=arguments.command_vectors,
        rmsnorm_vectors_path=arguments.rmsnorm_vectors,
        kernel_ir_path=arguments.kernel_ir,
        physical_plan_path=arguments.physical_plan,
        command_program_path=arguments.command_program,
        hbm_shard_path=arguments.hbm_shard,
    )
    schema = load_strict_json(
        ROOT / "schemas/compiler/tensor_accelerator/"
        "qwen_rtl_dma_matmul_vectors_v1.schema.json"
    )
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
