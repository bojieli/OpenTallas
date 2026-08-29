#!/usr/bin/env python3
"""Build source-bound vectors for the first full-K Qwen q_proj block.

Authentic commands 3 through 34 stage sixteen consecutive BF16 weight tiles
and execute the sixteen increasing-K MATMUL segments needed to finalize the
first 64 q_proj outputs.  This is 1/64 of graph operation ``node.0002``; it is
not the complete 4,096-output projection.
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
from runtime.reference.formats import (  # noqa: E402
    binary32_add,
    binary32_bits_to_bf16_rne,
    binary32_multiply,
)
from runtime.reference.tensor_accelerator_bf16 import (  # noqa: E402
    NUMERIC_CONTRACT,
)
from runtime.tensor_accelerator.bf16 import (  # noqa: E402
    accumulate_bf16_tile_fp32,
    finalize_bf16_accumulator,
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
INPUT_SHA256 = "976d6de1a3ed91a066c7efed4354e578edf366a3b51a7e6077d68282981ffa58"
WEIGHT_PAYLOAD_SHA256 = (
    "87bb7ad73d67888d91510a5443e2672172fcfccf52a5cd8b31acbe1f80c6be03"
)
FINAL_ACCUMULATOR_SHA256 = (
    "9ca6beb437222939a843d9a12d2fc93440de926cf7e0a5b3af40ce2c63a28f49"
)
FINAL_OUTPUT_SHA256 = "c485049ad6aa3e7c6e641defacfabee7de0c159cd8d45a65e74409493d17eb5e"
WEIGHT_TILE_SHA256 = (
    "c9b6213f04cfd269acdb7124e76d3b9775965145d15defb663f02e21e34418bc",
    "b40907adcc84082f95f5b879ea2558de18400d16fba5fd46cef5a00ba1e7789a",
    "059de4d766ac7776b26bdffead4aca2bde528d6a47ab0ea8e9a0ec4938b02622",
    "9b9f34fe47f6e0531f35af0cfdc32260046d2553a5f54753ea7a9b1fd63d2114",
    "4fdace78c77f1e0a6615cadeb769e0ebc798b8319e5c975c760a3e55346e1808",
    "01c2bbcbfe574c184ac88beeedfd64bc282db4cd41c1df485e94cccbffe9f975",
    "d28db45041a5cb1ce724b46c0001e37c65b5a91496b45df3275abb1eecae6b42",
    "376d6ead9910bfb6ce51dea8e0ee03709a2fce44aecf271094376a2f81174072",
    "d057e2f603a21086402479d6aeb52cad856783cb4286e59a53b64a7b5f502b53",
    "27c79119a4c35faaa0fb999948bd2b1525e54c643d9d9fd63cba2f8df4c2e2db",
    "e1a287af7cd48492bea49f321c11ccf6aa8926b13a209b31be559375a733bbed",
    "3a3ce8f3ef5fd03a8c92c3ea2540a76a92da2d2b1c9aa5a9b1516a3853b45f9d",
    "d012a2be1595a186be84f71a8e701685849b031d9ea544044852a94b187066e7",
    "423cbd65a987519cd57d31df43badd29afd48b82cdd01e18b2f5b5174d667af2",
    "7f5c879de60efcf7742e36f066b0b53e855418438c1ca721ad717776348f5f35",
    "67ed4d75b08c6b1b86844d5a399f982c78812983b2889bdddfd2216ff11e580e",
)
ACCUMULATOR_TILE_SHA256 = (
    "c82ca04197419306b6bbc545be882163e3ccccfb013773107541d3441dee8776",
    "f905ee10060fd1e644ce112cbb4ceb76301b137f11496ea450356aeb7fe6cdd5",
    "37b03a33974b135e8daf10c76097472dbf411662cde6d302416ee9fb68525251",
    "725e00fc2af84a32ddd61cd10be0df4489e5c0962e3c9efe80565a87de7a2e8b",
    "10534daf27c76eadafd9b32b0ee61f9c1f886a7894f0a862193012d54ab391b6",
    "b3bfd7a823b9fae4a44a8ab12a5a093ba5c66548beb737cd663b2cefb65193b2",
    "8779fb637f0e9e6a19edfaf14149259c361983b029be60202c3ceb5019e89804",
    "fb79aed6e391f8ef5d609354fc9d787148058d480e653f32f9131e32e196a030",
    "641a7f3db8e0b855c6290150a8196c5f9fd1fdeb40d20df6036db9118470ce26",
    "e45ac193c77c4a3586f93b823233356a56a1f4d399f7bf8ae9b398b7d316308d",
    "11706457687d43bf5883181f8a88c78238fb49bf1d08dabf10c72b8e01c428f6",
    "bc643cbba5ccf0039f5614e6a8f2f257f721b1c0eb60d57e64d278325bc9c267",
    "297adc2cdaa9746609a1ec2e913a2369a040af3bb29c07a14b7b9dc25a9c4fe8",
    "60d088395bbbbb76c1a8127fde8389e58a739c3236a1da40c7b5e1127fa6431b",
    "b0313cbb67e4c759c94fafc5bee72fdd3c0ac37b12e2187d47b40d32aaba74a2",
    "9ca6beb437222939a843d9a12d2fc93440de926cf7e0a5b3af40ce2c63a28f49",
)
COMMAND_COUNT = 924_386
SHARD_BASE = 1 << 30
SHARD_OFFSET = 170_950_656
K_TILES = 16
INPUTS_PER_TILE = 256
INPUT_ELEMENTS = K_TILES * INPUTS_PER_TILE
OUTPUT_ELEMENTS = 64
WEIGHT_ELEMENTS_PER_TILE = INPUTS_PER_TILE * OUTPUT_ELEMENTS
WEIGHT_ELEMENTS = K_TILES * WEIGHT_ELEMENTS_PER_TILE
WEIGHT_BYTES_PER_TILE = WEIGHT_ELEMENTS_PER_TILE * 2
WEIGHT_BYTES = WEIGHT_ELEMENTS * 2
INPUT_BASE = 3_145_728
WEIGHT_BASE = 4_194_304
ACCUMULATOR_BASE = 5_242_880
AUXILIARY_BASE = 6_291_456
HBM_BASE = 1_244_692_480


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(
        description="Build authentic Qwen commands 3-34 DMA/MATMUL RTL vectors"
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


def _validate_sources(
    command_vectors: dict[str, Any],
    rmsnorm_vectors: dict[str, Any],
    kernel_ir: dict[str, Any],
    physical_plan: dict[str, Any],
) -> None:
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
    _validate_sources(command_vectors, rmsnorm_vectors, kernel_ir, physical_plan)

    program = command_program_path.read_bytes()
    if _sha256(program) != PROGRAM_SHA256 or command_abi(program) != (
        ABI_MAJOR,
        ABI_MINOR,
    ):
        raise ValueError("complete Qwen command program differs")
    commands = decode(program)
    if len(commands) != COMMAND_COUNT:
        raise ValueError("complete Qwen command count differs")

    retained_matmul = next(
        item
        for item in command_vectors["vectors"]
        if item["name"] == "matmul_bf16_tile"
    )
    command_evidence: list[dict[str, Any]] = []
    for tile in range(K_TILES):
        dma_index = 3 + 2 * tile
        matmul_index = dma_index + 1
        dma = commands[dma_index]
        matmul = commands[matmul_index]
        flags = MATMUL_INIT if tile == 0 else MATMUL_FINAL if tile == 15 else 0
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
            "source0": HBM_BASE + tile * WEIGHT_BYTES_PER_TILE,
            "source1": 0,
        }
        expected_matmul = {
            "auxiliary": AUXILIARY_BASE,
            "destination": ACCUMULATOR_BASE,
            "engine": 2,
            "flags": flags,
            "index": matmul_index,
            "kernel_index": 2,
            "opcode": int(Opcode.MATMUL_BF16_TILE),
            "size0": 1,
            "size1": OUTPUT_ELEMENTS,
            "size2": INPUTS_PER_TILE,
            "size3": 0,
            "source0": INPUT_BASE + tile * INPUTS_PER_TILE * 2,
            "source1": WEIGHT_BASE,
        }
        dma_vector = _vector(
            f"dma_q_proj_weight_tile_k{tile:02d}",
            _raw_record(program, dma_index),
            last=False,
        )
        matmul_vector = _vector(
            f"matmul_bf16_tile_k{tile:02d}",
            _raw_record(program, matmul_index),
            last=tile == K_TILES - 1,
        )
        if (
            dma_vector["expected_fields"] != expected_dma
            or matmul_vector["expected_fields"] != expected_matmul
            or dma.destination != matmul.source1
        ):
            raise ValueError(f"authentic command pair differs at K tile {tile}")
        if tile == 0 and (
            matmul_vector["record_hex"] != retained_matmul["record_hex"]
            or matmul_vector["expected_fields"] != retained_matmul["expected_fields"]
        ):
            raise ValueError("retained command-4 vector correlation differs")
        command_evidence.extend((dma_vector, matmul_vector))

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
            "command_count": 2048,
            "command_start": 3,
            "kernel_index": 2,
            "operation_id": "node.0002",
        }
        or tensor["address"] != HBM_BASE
        or tensor["access_unit_bytes"] != WEIGHT_BYTES_PER_TILE
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
            "tile_bytes": WEIGHT_BYTES_PER_TILE,
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
        or HBM_BASE - SHARD_BASE != SHARD_OFFSET
    ):
        raise ValueError("immutable HBM shard identity differs")
    with hbm_shard_path.open("rb") as handle:
        handle.seek(SHARD_OFFSET)
        weight_payload = handle.read(WEIGHT_BYTES)
    if (
        len(weight_payload) != WEIGHT_BYTES
        or _sha256(weight_payload) != WEIGHT_PAYLOAD_SHA256
    ):
        raise ValueError("first full-K q_proj weight block differs")

    input_codes = list(rmsnorm_vectors["expected_codes"][:INPUT_ELEMENTS])
    input_payload = struct.pack(f"<{INPUT_ELEMENTS}H", *input_codes)
    if _sha256(input_payload) != INPUT_SHA256:
        raise ValueError("full command-2 output row differs")

    optimized_accumulator: np.ndarray[Any, np.dtype[np.uint32]] | None = None
    scalar_accumulator = [0] * OUTPUT_ELEMENTS
    expected_accumulator_tiles: list[list[int]] = []
    tile_evidence: list[dict[str, Any]] = []
    for tile in range(K_TILES):
        weight_start = tile * WEIGHT_BYTES_PER_TILE
        weight_tile = weight_payload[
            weight_start : weight_start + WEIGHT_BYTES_PER_TILE
        ]
        inputs = np.asarray(
            input_codes[tile * INPUTS_PER_TILE : (tile + 1) * INPUTS_PER_TILE],
            dtype=np.uint16,
        ).reshape(1, INPUTS_PER_TILE)
        weights = np.frombuffer(weight_tile, dtype="<u2").reshape(
            OUTPUT_ELEMENTS, INPUTS_PER_TILE
        )
        optimized_accumulator = accumulate_bf16_tile_fp32(
            inputs, weights, optimized_accumulator
        ).values
        for output, row in enumerate(weights.astype(int).tolist()):
            accumulator = scalar_accumulator[output]
            for left, right in zip(
                inputs.reshape(-1).astype(int).tolist(), row, strict=True
            ):
                accumulator = binary32_add(
                    accumulator,
                    binary32_multiply(left << 16, right << 16),
                )
            scalar_accumulator[output] = accumulator
        optimized_codes = optimized_accumulator.reshape(-1).astype(int).tolist()
        accumulator_payload = struct.pack(f"<{OUTPUT_ELEMENTS}I", *scalar_accumulator)
        if (
            scalar_accumulator != optimized_codes
            or _sha256(weight_tile) != WEIGHT_TILE_SHA256[tile]
            or _sha256(accumulator_payload) != ACCUMULATOR_TILE_SHA256[tile]
            or any((code >> 23) & 0xFF == 0xFF for code in scalar_accumulator)
        ):
            raise ValueError(f"independent arithmetic differs at K tile {tile}")
        expected_accumulator_tiles.append(list(scalar_accumulator))
        tile_evidence.append(
            {
                "accumulator_payload_sha256": ACCUMULATOR_TILE_SHA256[tile],
                "dma_command_index": 3 + 2 * tile,
                "dma_source_address": HBM_BASE + tile * WEIGHT_BYTES_PER_TILE,
                "flags": MATMUL_INIT
                if tile == 0
                else MATMUL_FINAL
                if tile == 15
                else 0,
                "input_address": INPUT_BASE + tile * INPUTS_PER_TILE * 2,
                "k_tile_index": tile,
                "matmul_command_index": 4 + 2 * tile,
                "weight_payload_sha256": WEIGHT_TILE_SHA256[tile],
            }
        )

    assert optimized_accumulator is not None
    optimized_output = finalize_bf16_accumulator(optimized_accumulator)
    scalar_conversions = [
        binary32_bits_to_bf16_rne(code) for code in scalar_accumulator
    ]
    output_codes = [value.code for value in scalar_conversions]
    saturation_count = sum(int(value.saturated) for value in scalar_conversions)
    output_payload = struct.pack(f"<{OUTPUT_ELEMENTS}H", *output_codes)
    final_accumulator_payload = struct.pack(f"<{OUTPUT_ELEMENTS}I", *scalar_accumulator)
    if (
        output_codes != optimized_output.values.reshape(-1).astype(int).tolist()
        or saturation_count != optimized_output.output_saturated_element_count
        or saturation_count != 0
        or _sha256(final_accumulator_payload) != FINAL_ACCUMULATOR_SHA256
        or _sha256(output_payload) != FINAL_OUTPUT_SHA256
    ):
        raise ValueError("final BF16 correlation differs")

    body: dict[str, Any] = {
        "build_id": BUILD_ID,
        "claim_boundary": {
            "authentic_command_records": True,
            "behavioral_hbm_and_sram": True,
            "bf16_final_output_written": True,
            "complete_first_output_block": True,
            "complete_layer_execution": False,
            "complete_matmul_commands": True,
            "complete_q_projection_graph_operation": False,
            "graph_valid_qwen_command_slice": True,
            "preloaded_attention_norm_row": True,
            "program_order_and_fail_stop": True,
            "qualified_hbm_phy": False,
            "qualified_sram_macro": False,
            "raw_fp32_accumulator_tile_written": True,
            "ta_rtl_6_closed": False,
            "timing_or_performance": False,
        },
        "command_program_sha256": PROGRAM_SHA256,
        "command_vector_set_id": COMMAND_VECTOR_ID,
        "commands": command_evidence,
        "composition": {
            "accumulator_address": ACCUMULATOR_BASE,
            "accumulator_count": OUTPUT_ELEMENTS,
            "accumulator_payload_sha256": FINAL_ACCUMULATOR_SHA256,
            "auxiliary_address": AUXILIARY_BASE,
            "auxiliary_payload_sha256": FINAL_OUTPUT_SHA256,
            "auxiliary_saturation_count": saturation_count,
            "auxiliary_write_count": OUTPUT_ELEMENTS,
            "dma_destination_address": WEIGHT_BASE,
            "graph_command_count": 2048,
            "graph_command_end": 2050,
            "graph_command_start": 3,
            "graph_operation_id": "node.0002",
            "graph_output_block_count": 64,
            "input_address": INPUT_BASE,
            "input_element_count": INPUT_ELEMENTS,
            "input_payload_sha256": INPUT_SHA256,
            "k_tile_count": K_TILES,
            "matmul_add_count": WEIGHT_ELEMENTS,
            "matmul_multiply_count": WEIGHT_ELEMENTS,
            "output_block_count": 1,
            "output_tile_index": 0,
            "parent_deployed_weight_payload_sha256": PARENT_DEPLOYED_SHA256,
            "parent_source_weight_payload_sha256": PARENT_SOURCE_SHA256,
            "submitted_command_indices": list(range(3, 35)),
            "weight_address": WEIGHT_BASE,
            "weight_element_count": WEIGHT_ELEMENTS,
            "weight_payload_sha256": WEIGHT_PAYLOAD_SHA256,
            "weight_tile_count": K_TILES,
        },
        "expected_accumulator_codes": list(scalar_accumulator),
        "expected_accumulator_tiles": expected_accumulator_tiles,
        "expected_output_codes": output_codes,
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
        "tiles": tile_evidence,
        "weight_payload_hex": weight_payload.hex(),
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
        ROOT
        / "schemas/compiler/tensor_accelerator/qwen_rtl_dma_matmul_vectors_v1.schema.json"
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
