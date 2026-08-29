#!/usr/bin/env python3
"""Build compact source-bound RTL vectors for complete Qwen q_proj node.0002.

The artifact retains every authentic command and every expected visible RTL
result, but deliberately does not retain the 32 MiB deployed weight slice.  A
replay must supply the immutable, hash-locked HBM shard and streams the slice
into temporary simulator input files.
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
    MATMUL_FINAL,
    MATMUL_INIT,
    Opcode,
    command_abi,
    decode,
)
from runtime.reference.tensor_accelerator_bf16 import (  # noqa: E402
    NUMERIC_CONTRACT,
)
from runtime.tensor_accelerator.bf16 import (  # noqa: E402
    accumulate_bf16_tile_fp32,
    finalize_bf16_accumulator,
)


SCHEMA = "opentallas.tensor_accelerator.qwen_rtl_q_proj_vectors.v1"
BUILD_ID = "3460d88ce16f5ef0ca4d1277daf8ebb19ae555e88822f95d55deb4aa8cad290f"
PROGRAM_SHA256 = "f0ce6b50b01f462f837a28504e6ff9a024a24d24abf339f924875d0c2059bcec"
COMMAND_VECTOR_ID = "420ada71f902c8e43b9e5866d9c57ab8e3a1ced59e25c01b20793c94cf45b1a2"
RMSNORM_VECTOR_ID = "ce2a725cc574f334273dbfdc93e6fab7fc4da48df8d2d4087f22307635212d81"
FIRST_BLOCK_VECTOR_ID = "4fe481b232112fe5b494cab1ca4445159b91a512a524471bee18267fe5525129"
PHYSICAL_PLAN_ID = "ba1d95462450d2cd059e6b55271c73ea90895515c9a4129bba1b51df265109c3"
KERNEL_IR_ID = "270b7609f2ea101593b3870a498bda3320336c94b27862dca7f991352727e050"
GRAPH_ID = "989ab0d4dae37c783e2eff349e1ed1fe16279288e12a19a94975f43b0254426f"
SHARD_SHA256 = "656958bc279d27f01126b855c25daeddc42f37f69445e97c2df432cee6dffb37"
DEPLOYED_WEIGHT_SHA256 = (
    "27406586791294918cb04052d91f7d47c41aac1af56650c4b47f68ac00f1ff9b"
)
SOURCE_WEIGHT_SHA256 = (
    "fd56b85bf301661c8655ed517928304d25df7d6b3ea3d9be85c021159d61bad8"
)
INPUT_SHA256 = "976d6de1a3ed91a066c7efed4354e578edf366a3b51a7e6077d68282981ffa58"
FULL_OUTPUT_SHA256 = "b900b79fd38ff6a9bff470ac27e9672b0c3724b84f6a1f7e964c2ec0918ea0ff"
EXECUTION_REPORT_ID = (
    "77b849e49608cacf9522eb16fad289385523c39618425e1e1c5f30126e504746"
)
EXECUTION_REPORT_SHA256 = (
    "4ddc5212edb5942f2b0d43a630da30fc7912309029cd917ce692bb6e663299f0"
)
REFERENCE_ID = "9033bc2ca0d078ff1bf85a624c952f207d2d8042eb0a1bc8bd1830d9b28007fb"
REFERENCE_SHA256 = "5ed2ab5c12998e63627ffcda33a631b98ea48d811da1d23c6e7035ce375cad80"

COMMAND_COUNT = 924_386
GRAPH_COMMAND_START = 3
GRAPH_COMMAND_COUNT = 2_048
GRAPH_COMMAND_END = GRAPH_COMMAND_START + GRAPH_COMMAND_COUNT - 1
SHARD_BASE = 1 << 30
SHARD_OFFSET = 170_950_656
OUTPUT_BLOCKS = 64
K_TILES = 16
INPUTS_PER_TILE = 256
INPUT_ELEMENTS = K_TILES * INPUTS_PER_TILE
OUTPUTS_PER_BLOCK = 64
OUTPUT_ELEMENTS = OUTPUT_BLOCKS * OUTPUTS_PER_BLOCK
WEIGHT_ELEMENTS_PER_TILE = INPUTS_PER_TILE * OUTPUTS_PER_BLOCK
WEIGHT_BYTES_PER_TILE = WEIGHT_ELEMENTS_PER_TILE * 2
WEIGHT_BYTES_PER_BLOCK = K_TILES * WEIGHT_BYTES_PER_TILE
WEIGHT_BYTES = OUTPUT_BLOCKS * WEIGHT_BYTES_PER_BLOCK
WEIGHT_ELEMENTS = WEIGHT_BYTES // 2
INPUT_BASE = 3_145_728
WEIGHT_BASE = 4_194_304
ACCUMULATOR_BASE = 5_242_880
AUXILIARY_BASE = 6_291_456
HBM_BASE = 1_244_692_480


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(
        description="Build authentic Qwen command-3-through-2050 q_proj vectors"
    )
    result.add_argument("--command-vectors", required=True, type=Path)
    result.add_argument("--rmsnorm-vectors", required=True, type=Path)
    result.add_argument("--first-block-vectors", required=True, type=Path)
    result.add_argument("--kernel-ir", required=True, type=Path)
    result.add_argument("--physical-plan", required=True, type=Path)
    result.add_argument("--command-program", required=True, type=Path)
    result.add_argument("--hbm-shard", required=True, type=Path)
    result.add_argument("--execution-report", required=True, type=Path)
    result.add_argument("--independent-reference", required=True, type=Path)
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


def _vector(name: str, raw: bytes, *, last: bool) -> dict[str, Any]:
    fields = _fields(raw)
    return {
        "abi_major": ABI_MAJOR,
        "abi_minor": ABI_MINOR,
        "expected_error": 0,
        "expected_fields": fields,
        "expected_index": fields["index"],
        "last": last,
        "name": name,
        "record_hex": f"{int.from_bytes(raw, 'little'):0128x}",
    }


def _raw_record(payload: bytes, index: int) -> bytes:
    start = 32 + index * COMMAND_WITH_CRC.size
    return payload[start : start + COMMAND_WITH_CRC.size]


def _validate_identity(value: dict[str, Any], field: str, expected: str) -> None:
    if value.get(field) != expected or value.get(field) != _identity(value, field):
        raise ValueError(f"retained {field} differs")


def _validate_sources(
    command_vectors: dict[str, Any],
    rmsnorm_vectors: dict[str, Any],
    first_block_vectors: dict[str, Any],
    kernel_ir: dict[str, Any],
    physical_plan: dict[str, Any],
) -> None:
    _validate_identity(command_vectors, "vector_set_id", COMMAND_VECTOR_ID)
    _validate_identity(rmsnorm_vectors, "vector_set_id", RMSNORM_VECTOR_ID)
    _validate_identity(first_block_vectors, "vector_set_id", FIRST_BLOCK_VECTOR_ID)
    _validate_identity(kernel_ir, "kernel_ir_id", KERNEL_IR_ID)
    _validate_identity(physical_plan, "physical_plan_id", PHYSICAL_PLAN_ID)
    for source in (command_vectors, rmsnorm_vectors, first_block_vectors):
        if (
            source.get("build_id") != BUILD_ID
            or source.get("command_program_sha256") != PROGRAM_SHA256
        ):
            raise ValueError("retained Qwen build/program identity differs")
    if (
        kernel_ir.get("graph_id") != GRAPH_ID
        or physical_plan.get("graph_id") != GRAPH_ID
        or physical_plan.get("semantic_kernel_ir_id") != KERNEL_IR_ID
    ):
        raise ValueError("retained Qwen graph/physical identity differs")


def _validate_execution_evidence(
    execution_path: Path,
    reference_path: Path,
) -> None:
    if _sha256_file(execution_path) != EXECUTION_REPORT_SHA256:
        raise ValueError("full-model execution report bytes differ")
    if _sha256_file(reference_path) != REFERENCE_SHA256:
        raise ValueError("full-model independent reference bytes differ")
    execution = load_strict_json(execution_path)
    reference = load_strict_json(reference_path)
    event = next(
        item for item in execution["events"] if item["operation_id"] == "node.0002"
    )
    if (
        execution.get("report_id") != EXECUTION_REPORT_ID
        or execution.get("status") != "pass"
        or event
        != {
            "command_count": GRAPH_COMMAND_COUNT,
            "command_start": GRAPH_COMMAND_START,
            "kernel_index": 2,
            "kind": "MATMUL",
            "operation_id": "node.0002",
            "outputs": {
                "layer.0.q_raw": {
                    "payload_sha256": FULL_OUTPUT_SHA256,
                    "size_bytes": OUTPUT_ELEMENTS * 2,
                }
            },
        }
        or reference.get("reference_id") != REFERENCE_ID
        or reference.get("execution_report_id") != EXECUTION_REPORT_ID
        or reference.get("status") != "pass"
        or not reference.get("checks", {}).get("all_617_operation_outputs_exact")
        or not reference.get("checks", {}).get("independent_scalar_kernel_cross_checks")
        or not reference.get("checks", {}).get("row_major_checkpoint_not_tiled_hbm_source")
        or not reference.get("checks", {}).get("segmented_k_not_fused_matrix_execution")
    ):
        raise ValueError("full-model execution/reference correlation differs")


def build(
    *,
    command_vectors_path: Path,
    rmsnorm_vectors_path: Path,
    first_block_vectors_path: Path,
    kernel_ir_path: Path,
    physical_plan_path: Path,
    command_program_path: Path,
    hbm_shard_path: Path,
    execution_report_path: Path,
    independent_reference_path: Path,
) -> dict[str, Any]:
    command_vectors = load_strict_json(command_vectors_path)
    rmsnorm_vectors = load_strict_json(rmsnorm_vectors_path)
    first_block_vectors = load_strict_json(first_block_vectors_path)
    kernel_ir = load_strict_json(kernel_ir_path)
    physical_plan = load_strict_json(physical_plan_path)
    _validate_sources(
        command_vectors,
        rmsnorm_vectors,
        first_block_vectors,
        kernel_ir,
        physical_plan,
    )
    _validate_execution_evidence(execution_report_path, independent_reference_path)

    program = command_program_path.read_bytes()
    if _sha256(program) != PROGRAM_SHA256 or command_abi(program) != (
        ABI_MAJOR,
        ABI_MINOR,
    ):
        raise ValueError("complete Qwen command program differs")
    commands = decode(program)
    if len(commands) != COMMAND_COUNT:
        raise ValueError("complete Qwen command count differs")

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
    if (
        operation_range
        != {
            "command_count": GRAPH_COMMAND_COUNT,
            "command_start": GRAPH_COMMAND_START,
            "kernel_index": 2,
            "operation_id": "node.0002",
        }
        or tensor["address"] != HBM_BASE
        or tensor["access_unit_bytes"] != WEIGHT_BYTES_PER_TILE
        or tensor["deployed_payload_sha256"] != DEPLOYED_WEIGHT_SHA256
        or tensor["source"]["payload_sha256"] != SOURCE_WEIGHT_SHA256
        or tensor["source"]["shape"] != [4096, 4096]
        or tensor["layout_details"]
        != {
            "k": 4096,
            "k_tile": 256,
            "k_tiles": K_TILES,
            "n": 4096,
            "n_tile": OUTPUTS_PER_BLOCK,
            "n_tiles": OUTPUT_BLOCKS,
            "order": "n_tile_then_k_tile",
            "tile_bytes": WEIGHT_BYTES_PER_TILE,
            "tile_count": OUTPUT_BLOCKS * K_TILES,
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
        or HBM_BASE - SHARD_BASE != SHARD_OFFSET
    ):
        raise ValueError("immutable HBM shard identity differs")

    input_codes = list(rmsnorm_vectors["expected_codes"][:INPUT_ELEMENTS])
    input_payload = struct.pack(f"<{INPUT_ELEMENTS}H", *input_codes)
    if _sha256(input_payload) != INPUT_SHA256:
        raise ValueError("full command-2 output row differs")

    command_evidence: list[dict[str, Any]] = []
    for output_block in range(OUTPUT_BLOCKS):
        for k_tile in range(K_TILES):
            pair = output_block * K_TILES + k_tile
            dma_index = GRAPH_COMMAND_START + 2 * pair
            matmul_index = dma_index + 1
            flags = (
                MATMUL_INIT
                if k_tile == 0
                else MATMUL_FINAL
                if k_tile == K_TILES - 1
                else 0
            )
            expected_dma = {
                "auxiliary": 0,
                "destination": WEIGHT_BASE,
                "engine": 1,
                "flags": 0,
                "index": dma_index,
                "kernel_index": 2,
                "opcode": int(Opcode.DMA_HBM_TO_SRAM),
                "size0": WEIGHT_BYTES_PER_TILE,
                "size1": 0,
                "size2": 0,
                "size3": 0,
                "source0": HBM_BASE + pair * WEIGHT_BYTES_PER_TILE,
                "source1": 0,
            }
            expected_matmul = {
                "auxiliary": AUXILIARY_BASE + output_block * OUTPUTS_PER_BLOCK * 2,
                "destination": ACCUMULATOR_BASE,
                "engine": 2,
                "flags": flags,
                "index": matmul_index,
                "kernel_index": 2,
                "opcode": int(Opcode.MATMUL_BF16_TILE),
                "size0": 1,
                "size1": OUTPUTS_PER_BLOCK,
                "size2": INPUTS_PER_TILE,
                "size3": 0,
                "source0": INPUT_BASE + k_tile * INPUTS_PER_TILE * 2,
                "source1": WEIGHT_BASE,
            }
            dma_vector = _vector(
                f"dma_q_proj_n{output_block:02d}_k{k_tile:02d}",
                _raw_record(program, dma_index),
                last=False,
            )
            matmul_vector = _vector(
                f"matmul_q_proj_n{output_block:02d}_k{k_tile:02d}",
                _raw_record(program, matmul_index),
                last=matmul_index == GRAPH_COMMAND_END,
            )
            if (
                dma_vector["expected_fields"] != expected_dma
                or matmul_vector["expected_fields"] != expected_matmul
                or commands[dma_index].destination != commands[matmul_index].source1
            ):
                raise ValueError(
                    f"authentic command pair differs at N={output_block} K={k_tile}"
                )
            command_evidence.extend((dma_vector, matmul_vector))
    for complete, retained in zip(
        command_evidence[:32], first_block_vectors["commands"], strict=True
    ):
        if (
            complete["abi_major"] != retained["abi_major"]
            or complete["abi_minor"] != retained["abi_minor"]
            or complete["expected_error"] != retained["expected_error"]
            or complete["expected_fields"] != retained["expected_fields"]
            or complete["expected_index"] != retained["expected_index"]
            or complete["record_hex"] != retained["record_hex"]
        ):
            raise ValueError("complete command sequence changes a first-block record")
    if command_evidence[31]["last"] or not first_block_vectors["commands"][31]["last"]:
        raise ValueError("command-34 nested-boundary terminality differs")

    expected_accumulator_tiles: list[list[int]] = []
    expected_output_codes: list[int] = []
    final_accumulator_codes: list[int] = []
    block_evidence: list[dict[str, Any]] = []
    tile_evidence: list[dict[str, Any]] = []
    weight_digest = hashlib.sha256()
    all_accumulator_digest = hashlib.sha256()
    with hbm_shard_path.open("rb") as handle:
        handle.seek(SHARD_OFFSET)
        for output_block in range(OUTPUT_BLOCKS):
            block_payload = handle.read(WEIGHT_BYTES_PER_BLOCK)
            if len(block_payload) != WEIGHT_BYTES_PER_BLOCK:
                raise ValueError("Qwen q_proj HBM slice is truncated")
            weight_digest.update(block_payload)
            optimized_accumulator: np.ndarray[Any, np.dtype[np.uint32]] | None = None
            block_tile_start = len(expected_accumulator_tiles)
            for k_tile in range(K_TILES):
                tile_start = k_tile * WEIGHT_BYTES_PER_TILE
                weight_tile = block_payload[
                    tile_start : tile_start + WEIGHT_BYTES_PER_TILE
                ]
                inputs = np.asarray(
                    input_codes[
                        k_tile * INPUTS_PER_TILE : (k_tile + 1) * INPUTS_PER_TILE
                    ],
                    dtype=np.uint16,
                ).reshape(1, INPUTS_PER_TILE)
                weights = np.frombuffer(weight_tile, dtype="<u2").reshape(
                    OUTPUTS_PER_BLOCK, INPUTS_PER_TILE
                )
                optimized_accumulator = accumulate_bf16_tile_fp32(
                    inputs, weights, optimized_accumulator
                ).values
                accumulator_codes = (
                    optimized_accumulator.reshape(-1).astype(int).tolist()
                )
                if any((code >> 23) & 0xFF == 0xFF for code in accumulator_codes):
                    raise ValueError(
                        f"nonfinite q_proj accumulator at N={output_block} K={k_tile}"
                    )
                accumulator_payload = struct.pack(
                    f"<{OUTPUTS_PER_BLOCK}I", *accumulator_codes
                )
                all_accumulator_digest.update(accumulator_payload)
                expected_accumulator_tiles.append(accumulator_codes)
                pair = output_block * K_TILES + k_tile
                tile_evidence.append(
                    {
                        "accumulator_payload_sha256": _sha256(accumulator_payload),
                        "dma_command_index": GRAPH_COMMAND_START + 2 * pair,
                        "dma_source_address": HBM_BASE + pair * WEIGHT_BYTES_PER_TILE,
                        "flags": MATMUL_INIT
                        if k_tile == 0
                        else MATMUL_FINAL
                        if k_tile == K_TILES - 1
                        else 0,
                        "input_address": INPUT_BASE + k_tile * INPUTS_PER_TILE * 2,
                        "k_tile_index": k_tile,
                        "matmul_command_index": GRAPH_COMMAND_START + 2 * pair + 1,
                        "output_block_index": output_block,
                        "weight_payload_sha256": _sha256(weight_tile),
                    }
                )
            assert optimized_accumulator is not None
            finalized = finalize_bf16_accumulator(optimized_accumulator)
            block_accumulators = optimized_accumulator.reshape(-1).astype(int).tolist()
            block_outputs = finalized.values.reshape(-1).astype(int).tolist()
            block_accumulator_payload = struct.pack(
                f"<{OUTPUTS_PER_BLOCK}I", *block_accumulators
            )
            block_output_payload = struct.pack(
                f"<{OUTPUTS_PER_BLOCK}H", *block_outputs
            )
            final_accumulator_codes.extend(block_accumulators)
            expected_output_codes.extend(block_outputs)
            block_evidence.append(
                {
                    "accumulator_payload_sha256": _sha256(
                        block_accumulator_payload
                    ),
                    "auxiliary_address": (
                        AUXILIARY_BASE + output_block * OUTPUTS_PER_BLOCK * 2
                    ),
                    "command_end": GRAPH_COMMAND_START
                    + (output_block + 1) * K_TILES * 2
                    - 1,
                    "command_start": GRAPH_COMMAND_START
                    + output_block * K_TILES * 2,
                    "output_block_index": output_block,
                    "output_payload_sha256": _sha256(block_output_payload),
                    "output_saturation_count": (
                        finalized.output_saturated_element_count
                    ),
                    "tile_evidence_start": block_tile_start,
                    "weight_payload_sha256": _sha256(block_payload),
                }
            )

    if weight_digest.hexdigest() != DEPLOYED_WEIGHT_SHA256:
        raise ValueError("complete deployed q_proj payload differs")
    if (
        expected_accumulator_tiles[:K_TILES]
        != first_block_vectors["expected_accumulator_tiles"]
        or expected_output_codes[:OUTPUTS_PER_BLOCK]
        != first_block_vectors["expected_output_codes"]
    ):
        raise ValueError("complete arithmetic does not preserve exact first block")
    output_payload = struct.pack(f"<{OUTPUT_ELEMENTS}H", *expected_output_codes)
    final_accumulator_payload = struct.pack(
        f"<{OUTPUT_ELEMENTS}I", *final_accumulator_codes
    )
    saturation_count = sum(
        item["output_saturation_count"] for item in block_evidence
    )
    if _sha256(output_payload) != FULL_OUTPUT_SHA256:
        raise ValueError("complete q_proj output differs from independent execution")

    body: dict[str, Any] = {
        "blocks": block_evidence,
        "build_id": BUILD_ID,
        "claim_boundary": {
            "architectural_simulator_output_correlated": True,
            "authentic_command_records": True,
            "behavioral_hbm_and_sram": True,
            "complete_layer_execution": False,
            "complete_q_projection_graph_operation": True,
            "graph_valid_qwen_command_slice": True,
            "independent_reference_all_operations_exact": True,
            "preloaded_attention_norm_row": True,
            "program_order_and_fail_stop": True,
            "qualified_hbm_phy": False,
            "qualified_sram_macro": False,
            "raw_weight_payload_retained": False,
            "ta_rtl_6_closed": False,
            "timing_or_performance": False,
        },
        "command_program_sha256": PROGRAM_SHA256,
        "command_vector_set_id": COMMAND_VECTOR_ID,
        "commands": command_evidence,
        "composition": {
            "accumulator_address": ACCUMULATOR_BASE,
            "accumulator_payload_sha256": _sha256(final_accumulator_payload),
            "all_accumulator_tiles_sha256": all_accumulator_digest.hexdigest(),
            "auxiliary_address": AUXILIARY_BASE,
            "auxiliary_payload_sha256": FULL_OUTPUT_SHA256,
            "auxiliary_saturation_count": saturation_count,
            "auxiliary_write_count": OUTPUT_ELEMENTS,
            "dma_destination_address": WEIGHT_BASE,
            "graph_command_count": GRAPH_COMMAND_COUNT,
            "graph_command_end": GRAPH_COMMAND_END,
            "graph_command_start": GRAPH_COMMAND_START,
            "graph_operation_id": "node.0002",
            "input_address": INPUT_BASE,
            "input_element_count": INPUT_ELEMENTS,
            "input_payload_sha256": INPUT_SHA256,
            "k_tile_count_per_output_block": K_TILES,
            "matmul_add_count": WEIGHT_ELEMENTS,
            "matmul_multiply_count": WEIGHT_ELEMENTS,
            "output_block_count": OUTPUT_BLOCKS,
            "output_element_count": OUTPUT_ELEMENTS,
            "parent_deployed_weight_payload_sha256": DEPLOYED_WEIGHT_SHA256,
            "parent_source_weight_payload_sha256": SOURCE_WEIGHT_SHA256,
            "submitted_command_count": GRAPH_COMMAND_COUNT,
            "weight_address": WEIGHT_BASE,
            "weight_element_count": WEIGHT_ELEMENTS,
            "weight_payload_sha256": DEPLOYED_WEIGHT_SHA256,
            "weight_tile_count": OUTPUT_BLOCKS * K_TILES,
        },
        "expected_accumulator_tiles": expected_accumulator_tiles,
        "expected_final_accumulator_codes": final_accumulator_codes,
        "expected_output_codes": expected_output_codes,
        "first_block_vector_set_id": FIRST_BLOCK_VECTOR_ID,
        "graph_id": GRAPH_ID,
        "hbm_shard": {
            "logical_base_address": SHARD_BASE,
            "path": shard_record["path"],
            "sha256": SHARD_SHA256,
            "size_bytes": shard_record["size_bytes"],
            "slice_offset_bytes": SHARD_OFFSET,
            "slice_size_bytes": WEIGHT_BYTES,
        },
        "input_codes": input_codes,
        "kernel_ir_id": KERNEL_IR_ID,
        "numeric_contract": NUMERIC_CONTRACT,
        "physical_plan_id": PHYSICAL_PLAN_ID,
        "rmsnorm_source_vector_id": RMSNORM_VECTOR_ID,
        "schema": SCHEMA,
        "source_execution": {
            "execution_report_id": EXECUTION_REPORT_ID,
            "execution_report_sha256": EXECUTION_REPORT_SHA256,
            "independent_reference_id": REFERENCE_ID,
            "independent_reference_sha256": REFERENCE_SHA256,
            "node_0002_output_sha256": FULL_OUTPUT_SHA256,
        },
        "tiles": tile_evidence,
    }
    return {**body, "vector_set_id": _identity(body, "vector_set_id")}


def main(argv: list[str] | None = None) -> int:
    arguments = parser().parse_args(argv)
    if arguments.output.exists():
        parser().error(f"--output already exists: {arguments.output}")
    vectors = build(
        command_vectors_path=arguments.command_vectors,
        rmsnorm_vectors_path=arguments.rmsnorm_vectors,
        first_block_vectors_path=arguments.first_block_vectors,
        kernel_ir_path=arguments.kernel_ir,
        physical_plan_path=arguments.physical_plan,
        command_program_path=arguments.command_program,
        hbm_shard_path=arguments.hbm_shard,
        execution_report_path=arguments.execution_report,
        independent_reference_path=arguments.independent_reference,
    )
    schema = load_strict_json(
        ROOT
        / "schemas/compiler/tensor_accelerator/qwen_rtl_q_proj_vectors_v1.schema.json"
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
