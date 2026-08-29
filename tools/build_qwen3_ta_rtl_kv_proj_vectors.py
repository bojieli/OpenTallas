#!/usr/bin/env python3
"""Build source-bound RTL vectors for complete layer-0 K/V projections.

The retained artifact contains authentic commands and exact visible arithmetic
results for nodes 0003 and 0004.  It deliberately omits the contiguous 16 MiB
deployed weight slice; campaign replay streams that slice from the immutable
hash-locked HBM shard into a temporary directory.
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


SCHEMA = "opentallas.tensor_accelerator.qwen_rtl_kv_proj_vectors.v1"
BUILD_ID = "3460d88ce16f5ef0ca4d1277daf8ebb19ae555e88822f95d55deb4aa8cad290f"
PROGRAM_SHA256 = "f0ce6b50b01f462f837a28504e6ff9a024a24d24abf339f924875d0c2059bcec"
COMMAND_VECTOR_ID = "420ada71f902c8e43b9e5866d9c57ab8e3a1ced59e25c01b20793c94cf45b1a2"
RMSNORM_VECTOR_ID = "ce2a725cc574f334273dbfdc93e6fab7fc4da48df8d2d4087f22307635212d81"
Q_PROJECTION_VECTOR_ID = (
    "32dbdaa446fc4192f31a0a26394e04094e74c6459858d8a6b0135c11fc9e324b"
)
PHYSICAL_PLAN_ID = "ba1d95462450d2cd059e6b55271c73ea90895515c9a4129bba1b51df265109c3"
KERNEL_IR_ID = "270b7609f2ea101593b3870a498bda3320336c94b27862dca7f991352727e050"
GRAPH_ID = "989ab0d4dae37c783e2eff349e1ed1fe16279288e12a19a94975f43b0254426f"
SHARD_SHA256 = "656958bc279d27f01126b855c25daeddc42f37f69445e97c2df432cee6dffb37"
INPUT_SHA256 = "976d6de1a3ed91a066c7efed4354e578edf366a3b51a7e6077d68282981ffa58"
EXECUTION_REPORT_ID = (
    "77b849e49608cacf9522eb16fad289385523c39618425e1e1c5f30126e504746"
)
EXECUTION_REPORT_SHA256 = (
    "4ddc5212edb5942f2b0d43a630da30fc7912309029cd917ce692bb6e663299f0"
)
REFERENCE_ID = "9033bc2ca0d078ff1bf85a624c952f207d2d8042eb0a1bc8bd1830d9b28007fb"
REFERENCE_SHA256 = "5ed2ab5c12998e63627ffcda33a631b98ea48d811da1d23c6e7035ce375cad80"

COMMAND_COUNT = 924_386
GRAPH_COMMAND_START = 2_051
GRAPH_COMMAND_END = 3_074
GRAPH_COMMAND_COUNT = GRAPH_COMMAND_END - GRAPH_COMMAND_START + 1
SHARD_BASE = 1 << 30
SHARD_OFFSET = 204_505_088
K_TILES = 16
INPUTS_PER_TILE = 256
INPUT_ELEMENTS = K_TILES * INPUTS_PER_TILE
OUTPUTS_PER_BLOCK = 64
OUTPUT_BLOCKS_PER_PROJECTION = 16
PROJECTION_COUNT = 2
OUTPUT_BLOCKS = OUTPUT_BLOCKS_PER_PROJECTION * PROJECTION_COUNT
OUTPUT_ELEMENTS_PER_PROJECTION = OUTPUT_BLOCKS_PER_PROJECTION * OUTPUTS_PER_BLOCK
OUTPUT_ELEMENTS = OUTPUT_ELEMENTS_PER_PROJECTION * PROJECTION_COUNT
WEIGHT_ELEMENTS_PER_TILE = INPUTS_PER_TILE * OUTPUTS_PER_BLOCK
WEIGHT_BYTES_PER_TILE = WEIGHT_ELEMENTS_PER_TILE * 2
WEIGHT_BYTES_PER_BLOCK = K_TILES * WEIGHT_BYTES_PER_TILE
WEIGHT_BYTES_PER_PROJECTION = OUTPUT_BLOCKS_PER_PROJECTION * WEIGHT_BYTES_PER_BLOCK
WEIGHT_BYTES = WEIGHT_BYTES_PER_PROJECTION * PROJECTION_COUNT
WEIGHT_ELEMENTS = WEIGHT_BYTES // 2
INPUT_BASE = 3_145_728
WEIGHT_BASE = 4_194_304
ACCUMULATOR_BASE = 5_242_880

PROJECTIONS: tuple[dict[str, Any], ...] = (
    {
        "auxiliary_base": 7_340_032,
        "command_start": 2_051,
        "deployed_weight_sha256": (
            "0460b9a479fbccdcebf61c86d0dc6eb068be781c51f7b247ed191774db2c28e8"
        ),
        "hbm_base": 1_278_246_912,
        "kernel_index": 3,
        "name": "k_proj",
        "operation_id": "node.0003",
        "output_sha256": (
            "dd690fbd9886a0af94cc6b2477ef5bfcc84fe66cac66f345f2ec654a83b28403"
        ),
        "output_tensor": "layer.0.k_raw",
        "source_weight_sha256": (
            "3ce9fdf6ee30ef2f24ad3629b506415ca91fe40f790e568a9ea3fea2978feee0"
        ),
        "weight_tensor": "model.layers.0.self_attn.k_proj.weight",
    },
    {
        "auxiliary_base": 8_388_608,
        "command_start": 2_563,
        "deployed_weight_sha256": (
            "2b82652e5d6446530230f86a685ef547ba9e94f613c2d2d42ab3388dd7271b1c"
        ),
        "hbm_base": 1_286_635_520,
        "kernel_index": 4,
        "name": "v_proj",
        "operation_id": "node.0004",
        "output_sha256": (
            "b07011da7a3d58dcccceb91e596ceebc2084ab3c2fc9d0b6a9a8704e91ef8dc5"
        ),
        "output_tensor": "layer.0.v",
        "source_weight_sha256": (
            "767a6c48457974bb02dd90aeec270f4d68289527a353c3c28964ab2069a966ee"
        ),
        "weight_tensor": "model.layers.0.self_attn.v_proj.weight",
    },
)


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(
        description="Build authentic Qwen command-2051-through-3074 K/V vectors"
    )
    result.add_argument("--command-vectors", required=True, type=Path)
    result.add_argument("--rmsnorm-vectors", required=True, type=Path)
    result.add_argument("--q-projection-vectors", required=True, type=Path)
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


def _validate_identity(value: dict[str, Any], field: str, expected: str) -> None:
    if value.get(field) != expected or value.get(field) != _identity(value, field):
        raise ValueError(f"retained {field} differs")


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


def _raw_record(payload: bytes, index: int) -> bytes:
    start = 32 + index * COMMAND_WITH_CRC.size
    return payload[start : start + COMMAND_WITH_CRC.size]


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


def _validate_sources(
    command_vectors: dict[str, Any],
    rmsnorm_vectors: dict[str, Any],
    q_projection_vectors: dict[str, Any],
    kernel_ir: dict[str, Any],
    physical_plan: dict[str, Any],
) -> None:
    _validate_identity(command_vectors, "vector_set_id", COMMAND_VECTOR_ID)
    _validate_identity(rmsnorm_vectors, "vector_set_id", RMSNORM_VECTOR_ID)
    _validate_identity(
        q_projection_vectors, "vector_set_id", Q_PROJECTION_VECTOR_ID
    )
    _validate_identity(kernel_ir, "kernel_ir_id", KERNEL_IR_ID)
    _validate_identity(physical_plan, "physical_plan_id", PHYSICAL_PLAN_ID)
    for source in (command_vectors, rmsnorm_vectors, q_projection_vectors):
        if (
            source.get("build_id") != BUILD_ID
            or source.get("command_program_sha256") != PROGRAM_SHA256
        ):
            raise ValueError("retained Qwen build/program identity differs")
    if (
        kernel_ir.get("graph_id") != GRAPH_ID
        or physical_plan.get("graph_id") != GRAPH_ID
        or physical_plan.get("semantic_kernel_ir_id") != KERNEL_IR_ID
        or q_projection_vectors.get("composition", {}).get("graph_command_end")
        != GRAPH_COMMAND_START - 1
    ):
        raise ValueError("retained Qwen graph/adjacent Q projection differs")


def _validate_execution_evidence(execution_path: Path, reference_path: Path) -> None:
    if _sha256_file(execution_path) != EXECUTION_REPORT_SHA256:
        raise ValueError("full-model execution report bytes differ")
    if _sha256_file(reference_path) != REFERENCE_SHA256:
        raise ValueError("full-model independent reference bytes differ")
    execution = load_strict_json(execution_path)
    reference = load_strict_json(reference_path)
    events = {
        item["operation_id"]: item
        for item in execution["events"]
        if item["operation_id"] in {"node.0003", "node.0004"}
    }
    expected_events = {
        spec["operation_id"]: {
            "command_count": 512,
            "command_start": spec["command_start"],
            "kernel_index": spec["kernel_index"],
            "kind": "MATMUL",
            "operation_id": spec["operation_id"],
            "outputs": {
                spec["output_tensor"]: {
                    "payload_sha256": spec["output_sha256"],
                    "size_bytes": OUTPUT_ELEMENTS_PER_PROJECTION * 2,
                }
            },
        }
        for spec in PROJECTIONS
    }
    if (
        execution.get("report_id") != EXECUTION_REPORT_ID
        or execution.get("status") != "pass"
        or events != expected_events
        or reference.get("reference_id") != REFERENCE_ID
        or reference.get("execution_report_id") != EXECUTION_REPORT_ID
        or reference.get("status") != "pass"
        or not reference.get("checks", {}).get("all_617_operation_outputs_exact")
        or not reference.get("checks", {}).get(
            "independent_scalar_kernel_cross_checks"
        )
        or not reference.get("checks", {}).get(
            "row_major_checkpoint_not_tiled_hbm_source"
        )
        or not reference.get("checks", {}).get(
            "segmented_k_not_fused_matrix_execution"
        )
    ):
        raise ValueError("full-model execution/reference correlation differs")


def build(
    *,
    command_vectors_path: Path,
    rmsnorm_vectors_path: Path,
    q_projection_vectors_path: Path,
    kernel_ir_path: Path,
    physical_plan_path: Path,
    command_program_path: Path,
    hbm_shard_path: Path,
    execution_report_path: Path,
    independent_reference_path: Path,
) -> dict[str, Any]:
    command_vectors = load_strict_json(command_vectors_path)
    rmsnorm_vectors = load_strict_json(rmsnorm_vectors_path)
    q_projection_vectors = load_strict_json(q_projection_vectors_path)
    kernel_ir = load_strict_json(kernel_ir_path)
    physical_plan = load_strict_json(physical_plan_path)
    _validate_sources(
        command_vectors,
        rmsnorm_vectors,
        q_projection_vectors,
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

    ranges = {
        item["kernel_index"]: item
        for item in physical_plan["command_program"]["kernel_command_ranges"]
        if item["kernel_index"] in {3, 4}
    }
    weight_records = {
        item["tensor_id"]: item for item in physical_plan["hbm"]["weights"]
    }
    for spec in PROJECTIONS:
        expected_range = {
            "command_count": 512,
            "command_start": spec["command_start"],
            "kernel_index": spec["kernel_index"],
            "operation_id": spec["operation_id"],
        }
        tensor = weight_records[spec["weight_tensor"]]
        kernel = kernel_ir["kernels"][spec["kernel_index"]]
        if (
            ranges.get(spec["kernel_index"]) != expected_range
            or tensor["address"] != spec["hbm_base"]
            or tensor["access_unit_bytes"] != WEIGHT_BYTES_PER_TILE
            or tensor["deployed_payload_sha256"]
            != spec["deployed_weight_sha256"]
            or tensor["source"]["payload_sha256"]
            != spec["source_weight_sha256"]
            or tensor["source"]["shape"] != [1024, 4096]
            or tensor["layout_details"]
            != {
                "k": 4096,
                "k_tile": 256,
                "k_tiles": K_TILES,
                "n": 1024,
                "n_tile": OUTPUTS_PER_BLOCK,
                "n_tiles": OUTPUT_BLOCKS_PER_PROJECTION,
                "order": "n_tile_then_k_tile",
                "tile_bytes": WEIGHT_BYTES_PER_TILE,
                "tile_count": OUTPUT_BLOCKS_PER_PROJECTION * K_TILES,
            }
            or kernel["source_operation_id"] != spec["operation_id"]
            or kernel["kind"] != "MATMUL"
            or kernel["numeric_contract"] != NUMERIC_CONTRACT
            or kernel["inputs"]
            != ["layer.0.attention_norm", spec["weight_tensor"]]
            or kernel["outputs"] != [spec["output_tensor"]]
        ):
            raise ValueError(f"Qwen {spec['operation_id']} physical lowering differs")

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
        or PROJECTIONS[0]["hbm_base"] - SHARD_BASE != SHARD_OFFSET
        or PROJECTIONS[1]["hbm_base"]
        != PROJECTIONS[0]["hbm_base"] + WEIGHT_BYTES_PER_PROJECTION
    ):
        raise ValueError("immutable HBM shard identity differs")

    input_codes = list(rmsnorm_vectors["expected_codes"][:INPUT_ELEMENTS])
    input_payload = struct.pack(f"<{INPUT_ELEMENTS}H", *input_codes)
    if _sha256(input_payload) != INPUT_SHA256:
        raise ValueError("full command-2 output row differs")

    command_evidence: list[dict[str, Any]] = []
    for spec in PROJECTIONS:
        for output_block in range(OUTPUT_BLOCKS_PER_PROJECTION):
            for k_tile in range(K_TILES):
                pair = output_block * K_TILES + k_tile
                dma_index = spec["command_start"] + 2 * pair
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
                    "kernel_index": spec["kernel_index"],
                    "opcode": int(Opcode.DMA_HBM_TO_SRAM),
                    "size0": WEIGHT_BYTES_PER_TILE,
                    "size1": 0,
                    "size2": 0,
                    "size3": 0,
                    "source0": spec["hbm_base"] + pair * WEIGHT_BYTES_PER_TILE,
                    "source1": 0,
                }
                expected_matmul = {
                    "auxiliary": (
                        spec["auxiliary_base"]
                        + output_block * OUTPUTS_PER_BLOCK * 2
                    ),
                    "destination": ACCUMULATOR_BASE,
                    "engine": 2,
                    "flags": flags,
                    "index": matmul_index,
                    "kernel_index": spec["kernel_index"],
                    "opcode": int(Opcode.MATMUL_BF16_TILE),
                    "size0": 1,
                    "size1": OUTPUTS_PER_BLOCK,
                    "size2": INPUTS_PER_TILE,
                    "size3": 0,
                    "source0": INPUT_BASE + k_tile * INPUTS_PER_TILE * 2,
                    "source1": WEIGHT_BASE,
                }
                dma_vector = _vector(
                    f"dma_{spec['name']}_n{output_block:02d}_k{k_tile:02d}",
                    _raw_record(program, dma_index),
                    last=False,
                )
                matmul_vector = _vector(
                    f"matmul_{spec['name']}_n{output_block:02d}_k{k_tile:02d}",
                    _raw_record(program, matmul_index),
                    last=matmul_index == GRAPH_COMMAND_END,
                )
                if (
                    dma_vector["expected_fields"] != expected_dma
                    or matmul_vector["expected_fields"] != expected_matmul
                    or commands[dma_index].destination
                    != commands[matmul_index].source1
                ):
                    raise ValueError(
                        "authentic command pair differs at "
                        f"{spec['name']} N={output_block} K={k_tile}"
                    )
                command_evidence.extend((dma_vector, matmul_vector))

    expected_accumulator_tiles: list[list[int]] = []
    expected_output_codes: list[int] = []
    final_accumulator_codes: list[int] = []
    block_evidence: list[dict[str, Any]] = []
    tile_evidence: list[dict[str, Any]] = []
    projection_evidence: list[dict[str, Any]] = []
    weight_digest = hashlib.sha256()
    all_accumulator_digest = hashlib.sha256()
    with hbm_shard_path.open("rb") as handle:
        handle.seek(SHARD_OFFSET)
        for projection_number, spec in enumerate(PROJECTIONS):
            projection_weight_digest = hashlib.sha256()
            projection_accumulator_digest = hashlib.sha256()
            projection_output_start = len(expected_output_codes)
            projection_final_start = len(final_accumulator_codes)
            projection_tile_start = len(expected_accumulator_tiles)
            projection_saturations = 0
            for output_block in range(OUTPUT_BLOCKS_PER_PROJECTION):
                block_payload = handle.read(WEIGHT_BYTES_PER_BLOCK)
                if len(block_payload) != WEIGHT_BYTES_PER_BLOCK:
                    raise ValueError(f"Qwen {spec['name']} HBM slice is truncated")
                weight_digest.update(block_payload)
                projection_weight_digest.update(block_payload)
                optimized_accumulator: (
                    np.ndarray[Any, np.dtype[np.uint32]] | None
                ) = None
                block_tile_start = len(expected_accumulator_tiles)
                for k_tile in range(K_TILES):
                    tile_start = k_tile * WEIGHT_BYTES_PER_TILE
                    weight_tile = block_payload[
                        tile_start : tile_start + WEIGHT_BYTES_PER_TILE
                    ]
                    inputs = np.asarray(
                        input_codes[
                            k_tile
                            * INPUTS_PER_TILE : (k_tile + 1)
                            * INPUTS_PER_TILE
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
                    if any(
                        (code >> 23) & 0xFF == 0xFF for code in accumulator_codes
                    ):
                        raise ValueError(
                            "nonfinite projection accumulator at "
                            f"{spec['name']} N={output_block} K={k_tile}"
                        )
                    accumulator_payload = struct.pack(
                        f"<{OUTPUTS_PER_BLOCK}I", *accumulator_codes
                    )
                    all_accumulator_digest.update(accumulator_payload)
                    projection_accumulator_digest.update(accumulator_payload)
                    expected_accumulator_tiles.append(accumulator_codes)
                    pair = output_block * K_TILES + k_tile
                    tile_evidence.append(
                        {
                            "accumulator_payload_sha256": _sha256(
                                accumulator_payload
                            ),
                            "dma_command_index": spec["command_start"] + 2 * pair,
                            "dma_source_address": (
                                spec["hbm_base"] + pair * WEIGHT_BYTES_PER_TILE
                            ),
                            "flags": MATMUL_INIT
                            if k_tile == 0
                            else MATMUL_FINAL
                            if k_tile == K_TILES - 1
                            else 0,
                            "global_output_block_index": (
                                projection_number * OUTPUT_BLOCKS_PER_PROJECTION
                                + output_block
                            ),
                            "input_address": (
                                INPUT_BASE + k_tile * INPUTS_PER_TILE * 2
                            ),
                            "k_tile_index": k_tile,
                            "kernel_index": spec["kernel_index"],
                            "matmul_command_index": (
                                spec["command_start"] + 2 * pair + 1
                            ),
                            "output_block_index": output_block,
                            "projection": spec["name"],
                            "weight_payload_sha256": _sha256(weight_tile),
                        }
                    )
                assert optimized_accumulator is not None
                finalized = finalize_bf16_accumulator(optimized_accumulator)
                block_accumulators = (
                    optimized_accumulator.reshape(-1).astype(int).tolist()
                )
                block_outputs = finalized.values.reshape(-1).astype(int).tolist()
                block_accumulator_payload = struct.pack(
                    f"<{OUTPUTS_PER_BLOCK}I", *block_accumulators
                )
                block_output_payload = struct.pack(
                    f"<{OUTPUTS_PER_BLOCK}H", *block_outputs
                )
                final_accumulator_codes.extend(block_accumulators)
                expected_output_codes.extend(block_outputs)
                projection_saturations += finalized.output_saturated_element_count
                block_evidence.append(
                    {
                        "accumulator_payload_sha256": _sha256(
                            block_accumulator_payload
                        ),
                        "auxiliary_address": (
                            spec["auxiliary_base"]
                            + output_block * OUTPUTS_PER_BLOCK * 2
                        ),
                        "command_end": (
                            spec["command_start"]
                            + (output_block + 1) * K_TILES * 2
                            - 1
                        ),
                        "command_start": (
                            spec["command_start"] + output_block * K_TILES * 2
                        ),
                        "global_output_block_index": (
                            projection_number * OUTPUT_BLOCKS_PER_PROJECTION
                            + output_block
                        ),
                        "kernel_index": spec["kernel_index"],
                        "output_block_index": output_block,
                        "output_payload_sha256": _sha256(block_output_payload),
                        "output_saturation_count": (
                            finalized.output_saturated_element_count
                        ),
                        "projection": spec["name"],
                        "tile_evidence_start": block_tile_start,
                        "weight_payload_sha256": _sha256(block_payload),
                    }
                )

            projection_output_payload = struct.pack(
                f"<{OUTPUT_ELEMENTS_PER_PROJECTION}H",
                *expected_output_codes[
                    projection_output_start : projection_output_start
                    + OUTPUT_ELEMENTS_PER_PROJECTION
                ],
            )
            projection_final_payload = struct.pack(
                f"<{OUTPUT_ELEMENTS_PER_PROJECTION}I",
                *final_accumulator_codes[
                    projection_final_start : projection_final_start
                    + OUTPUT_ELEMENTS_PER_PROJECTION
                ],
            )
            if (
                projection_weight_digest.hexdigest()
                != spec["deployed_weight_sha256"]
                or _sha256(projection_output_payload) != spec["output_sha256"]
            ):
                raise ValueError(
                    f"complete {spec['name']} payload differs from source evidence"
                )
            projection_evidence.append(
                {
                    "accumulator_payload_sha256": _sha256(
                        projection_final_payload
                    ),
                    "all_accumulator_tiles_sha256": (
                        projection_accumulator_digest.hexdigest()
                    ),
                    "auxiliary_address": spec["auxiliary_base"],
                    "command_count": 512,
                    "command_end": spec["command_start"] + 511,
                    "command_start": spec["command_start"],
                    "deployed_weight_payload_sha256": (
                        spec["deployed_weight_sha256"]
                    ),
                    "kernel_index": spec["kernel_index"],
                    "operation_id": spec["operation_id"],
                    "output_block_count": OUTPUT_BLOCKS_PER_PROJECTION,
                    "output_element_count": OUTPUT_ELEMENTS_PER_PROJECTION,
                    "output_payload_sha256": spec["output_sha256"],
                    "output_saturation_count": projection_saturations,
                    "projection": spec["name"],
                    "source_weight_payload_sha256": (
                        spec["source_weight_sha256"]
                    ),
                    "tile_evidence_start": projection_tile_start,
                    "weight_address": spec["hbm_base"],
                    "weight_tile_count": (
                        OUTPUT_BLOCKS_PER_PROJECTION * K_TILES
                    ),
                }
            )

    output_payload = struct.pack(f"<{OUTPUT_ELEMENTS}H", *expected_output_codes)
    final_accumulator_payload = struct.pack(
        f"<{OUTPUT_ELEMENTS}I", *final_accumulator_codes
    )
    saturation_count = sum(
        item["output_saturation_count"] for item in projection_evidence
    )
    body: dict[str, Any] = {
        "blocks": block_evidence,
        "build_id": BUILD_ID,
        "claim_boundary": {
            "architectural_simulator_output_correlated": True,
            "authentic_command_records": True,
            "behavioral_hbm_and_sram": True,
            "complete_k_projection_graph_operation": True,
            "complete_layer_execution": False,
            "complete_qkv_preparation": False,
            "complete_v_projection_graph_operation": True,
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
            "auxiliary_saturation_count": saturation_count,
            "auxiliary_write_count": OUTPUT_ELEMENTS,
            "combined_output_payload_sha256": _sha256(output_payload),
            "combined_weight_payload_sha256": weight_digest.hexdigest(),
            "dma_destination_address": WEIGHT_BASE,
            "graph_command_count": GRAPH_COMMAND_COUNT,
            "graph_command_end": GRAPH_COMMAND_END,
            "graph_command_start": GRAPH_COMMAND_START,
            "graph_operation_ids": ["node.0003", "node.0004"],
            "input_address": INPUT_BASE,
            "input_element_count": INPUT_ELEMENTS,
            "input_payload_sha256": INPUT_SHA256,
            "k_tile_count_per_output_block": K_TILES,
            "matmul_add_count": WEIGHT_ELEMENTS,
            "matmul_multiply_count": WEIGHT_ELEMENTS,
            "output_block_count": OUTPUT_BLOCKS,
            "output_element_count": OUTPUT_ELEMENTS,
            "projections": projection_evidence,
            "submitted_command_count": GRAPH_COMMAND_COUNT,
            "weight_element_count": WEIGHT_ELEMENTS,
            "weight_tile_count": OUTPUT_BLOCKS * K_TILES,
        },
        "expected_accumulator_tiles": expected_accumulator_tiles,
        "expected_final_accumulator_codes": final_accumulator_codes,
        "expected_output_codes": expected_output_codes,
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
        "q_projection_vector_set_id": Q_PROJECTION_VECTOR_ID,
        "rmsnorm_source_vector_id": RMSNORM_VECTOR_ID,
        "schema": SCHEMA,
        "source_execution": {
            "execution_report_id": EXECUTION_REPORT_ID,
            "execution_report_sha256": EXECUTION_REPORT_SHA256,
            "independent_reference_id": REFERENCE_ID,
            "independent_reference_sha256": REFERENCE_SHA256,
            "node_0003_output_sha256": PROJECTIONS[0]["output_sha256"],
            "node_0004_output_sha256": PROJECTIONS[1]["output_sha256"],
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
        q_projection_vectors_path=arguments.q_projection_vectors,
        kernel_ir_path=arguments.kernel_ir,
        physical_plan_path=arguments.physical_plan,
        command_program_path=arguments.command_program,
        hbm_shard_path=arguments.hbm_shard,
        execution_report_path=arguments.execution_report,
        independent_reference_path=arguments.independent_reference,
    )
    schema = load_strict_json(
        ROOT
        / "schemas/compiler/tensor_accelerator/"
        "qwen_rtl_kv_proj_vectors_v1.schema.json"
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
