#!/usr/bin/env python3
"""Build source-bound vectors for adjacent Qwen DMA then RMSNorm RTL.

The two command records are copied unchanged from the retained production Qwen
command program.  Command 1 stages ``model.layers.0.input_layernorm.weight``
and command 2 consumes that exact SRAM payload with preloaded ``hidden.0`` to
execute the complete physical command range for graph operation ``node.0001``.
"""

from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path
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
from runtime.reference.tensor_accelerator_rmsnorm import (  # noqa: E402
    NUMERIC_CONTRACT,
    rms_norm_bf16 as reference_rmsnorm,
)
from runtime.tensor_accelerator.rmsnorm import (  # noqa: E402
    rms_norm_bf16,
)


SCHEMA = "opentallas.tensor_accelerator.qwen_rtl_dma_rmsnorm_vectors.v1"
BUILD_ID = "3460d88ce16f5ef0ca4d1277daf8ebb19ae555e88822f95d55deb4aa8cad290f"
PROGRAM_SHA256 = "f0ce6b50b01f462f837a28504e6ff9a024a24d24abf339f924875d0c2059bcec"
COMMAND_VECTOR_ID = "420ada71f902c8e43b9e5866d9c57ab8e3a1ced59e25c01b20793c94cf45b1a2"
DMA_VECTOR_ID = "98806ae5e1b8f3dbe1e516084b099a5f592f98acf6adb74edb0198d82ae10216"
INPUT_VECTOR_ID = "e625aabe70b198319b76f8928d0b99ffe88d6d9e846eb8e0ddaeb3ba72eb7413"
QUALIFICATION_ID = "542afccabfde8b5f9628a1b27ba394312305780db5f850a276f651c64e7dd972"
KERNEL_IR_ID = "270b7609f2ea101593b3870a498bda3320336c94b27862dca7f991352727e050"
GRAPH_ID = "989ab0d4dae37c783e2eff349e1ed1fe16279288e12a19a94975f43b0254426f"
INPUT_SHA256 = "6f57745a3765e8651c07b849d199577ec673d24cc40beb25bbaa72c6aadf73bb"
WEIGHT_SHA256 = "00695bad97c2abc77a9d1ce57e4d4a5e5c2b574387fcb4029ef5ce12239b2530"
NORMALIZED_SHA256 = "bf4b81b7e711157b4e8c91bde7294d3be647844dbd7336d462201a246a1da28d"
OUTPUT_SHA256 = "976d6de1a3ed91a066c7efed4354e578edf366a3b51a7e6077d68282981ffa58"
ELEMENTS = 4096


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(
        description="Build authentic adjacent Qwen DMA/RMSNorm RTL vectors"
    )
    result.add_argument("--command-vectors", required=True, type=Path)
    result.add_argument("--dma-vectors", required=True, type=Path)
    result.add_argument("--input-vectors", required=True, type=Path)
    result.add_argument("--qualification", required=True, type=Path)
    result.add_argument("--kernel-ir", required=True, type=Path)
    result.add_argument("--output", required=True, type=Path)
    return result


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _identity(value: dict[str, Any], field: str) -> str:
    body = {key: item for key, item in value.items() if key != field}
    return _sha256(canonical_json_bytes(body))


def _codes_payload(codes: list[int]) -> bytes:
    return np.ascontiguousarray(codes, dtype="<u2").tobytes(order="C")


def build(
    *,
    command_vectors_path: Path,
    dma_vectors_path: Path,
    input_vectors_path: Path,
    qualification_path: Path,
    kernel_ir_path: Path,
) -> dict[str, Any]:
    commands = load_strict_json(command_vectors_path)
    dma = load_strict_json(dma_vectors_path)
    inputs = load_strict_json(input_vectors_path)
    qualification = load_strict_json(qualification_path)
    kernel_ir = load_strict_json(kernel_ir_path)
    if (
        commands.get("vector_set_id") != COMMAND_VECTOR_ID
        or commands.get("vector_set_id") != _identity(commands, "vector_set_id")
        or dma.get("vector_set_id") != DMA_VECTOR_ID
        or dma.get("vector_set_id") != _identity(dma, "vector_set_id")
        or inputs.get("vector_set_id") != INPUT_VECTOR_ID
        or inputs.get("vector_set_id") != _identity(inputs, "vector_set_id")
        or qualification.get("report_id") != QUALIFICATION_ID
        or qualification.get("report_id") != _identity(qualification, "report_id")
        or kernel_ir.get("kernel_ir_id") != KERNEL_IR_ID
        or kernel_ir.get("kernel_ir_id") != _identity(kernel_ir, "kernel_ir_id")
        or kernel_ir.get("graph_id") != GRAPH_ID
    ):
        raise ValueError("retained Qwen source identities differ")
    for source in (commands, dma, inputs):
        if (
            source.get("build_id") != BUILD_ID
            or source.get("command_program_sha256") != PROGRAM_SHA256
        ):
            raise ValueError("retained Qwen build/program identity differs")

    command_by_name = {
        item.get("name"): item for item in commands.get("vectors", [])
    }
    dma_command = dma.get("command", {})
    rms_command = command_by_name.get("rmsnorm_bf16", {})
    dma_fields = dma_command.get("expected_fields", {})
    rms_fields = rms_command.get("expected_fields", {})
    if (
        dma_command != command_by_name.get("dma_hbm_to_sram")
        or dma_command.get("expected_index") != 1
        or rms_command.get("expected_index") != 2
        or dma_fields.get("opcode") != 1
        or rms_fields.get("opcode") != 0x20
        or dma_fields.get("destination") != rms_fields.get("source1")
        or rms_fields.get("size0") != 1
        or rms_fields.get("size1") != ELEMENTS
        or rms_fields.get("size2") != 0x358637BD
    ):
        raise ValueError("authentic DMA/RMSNorm command relationship differs")

    input_codes = list(inputs.get("left", {}).get("codes", []))
    weight_payload = bytes.fromhex(str(dma.get("hbm", {}).get("payload_hex", "")))
    weight_codes = np.frombuffer(weight_payload, dtype="<u2").astype(int).tolist()
    if (
        len(input_codes) != ELEMENTS
        or len(weight_codes) != ELEMENTS
        or _sha256(_codes_payload(input_codes)) != INPUT_SHA256
        or _sha256(weight_payload) != WEIGHT_SHA256
        or inputs.get("left", {}).get("address") != rms_fields.get("source0")
    ):
        raise ValueError("authentic RMSNorm operand payload differs")

    kernel = kernel_ir.get("kernels", [None, None])[1]
    if kernel != {
        "attributes": {
            "epsilon_binary32_code": 897988541,
            "final_weight_product": "bf16_multiply_then_bf16_rne",
            "normalized_boundary": "bf16_rne_before_weight",
            "reduction_order": "canonical_balanced_binary32_tree",
            "rsqrt": "correctly_rounded_binary32_rne",
        },
        "index": 1,
        "inputs": ["hidden.0", "model.layers.0.input_layernorm.weight"],
        "kind": "RMS_NORM",
        "numeric_contract": NUMERIC_CONTRACT,
        "outputs": ["layer.0.attention_norm"],
        "shape": {
            "rows": {"maximum": 8000, "multiplier": 1, "symbol": "span_tokens"},
            "width": 4096,
        },
        "source_operation_id": "node.0001",
    }:
        raise ValueError("Qwen kernel IR operation node.0001 differs")

    optimized = rms_norm_bf16(
        np.asarray(input_codes, dtype=np.uint16).reshape(1, ELEMENTS),
        np.asarray(weight_codes, dtype=np.uint16),
    )
    reference = reference_rmsnorm([input_codes], weight_codes)
    normalized_codes = optimized.normalized_values[0].astype(int).tolist()
    expected_codes = optimized.values[0].astype(int).tolist()
    if (
        reference.normalized_values != (tuple(normalized_codes),)
        or reference.values != (tuple(expected_codes),)
        or tuple(int(value) for value in optimized.mean_square_codes.tolist())
        != reference.mean_square_codes
        or tuple(int(value) for value in optimized.inverse_rms_codes.tolist())
        != reference.inverse_rms_codes
        or optimized.normalized_saturated_element_count
        != reference.normalized_saturated_element_count
        or optimized.output_saturated_element_count
        != reference.output_saturated_element_count
        or _sha256(_codes_payload(normalized_codes)) != NORMALIZED_SHA256
        or _sha256(_codes_payload(expected_codes)) != OUTPUT_SHA256
    ):
        raise ValueError("independent DMA/RMSNorm arithmetic correlation differs")

    q_input = qualification.get("input", {})
    q_weight = qualification.get("weight", {})
    q_output = qualification.get("output", {})
    if (
        qualification.get("numeric_contract") != NUMERIC_CONTRACT
        or q_input.get("row_payload_sha256") != INPUT_SHA256
        or q_weight.get("payload_sha256") != WEIGHT_SHA256
        or q_output.get("normalized_payload_sha256") != NORMALIZED_SHA256
        or q_output.get("payload_sha256") != OUTPUT_SHA256
        or q_output.get("mean_square_binary32_code")
        != reference.mean_square_codes[0]
        or q_output.get("inverse_rms_binary32_code")
        != reference.inverse_rms_codes[0]
    ):
        raise ValueError("retained checkpoint RMSNorm qualification differs")

    body: dict[str, Any] = {
        "build_id": BUILD_ID,
        "checkpoint_lock_id": qualification["checkpoint_lock_id"],
        "claim_boundary": {
            "authentic_command_records": True,
            "behavioral_hbm_and_sram": True,
            "complete_layer_execution": False,
            "complete_rmsnorm_graph_operation": True,
            "graph_valid_qwen_operation_sequence": True,
            "preloaded_hidden_input": True,
            "program_order_and_fail_stop": True,
            "qualified_hbm_phy": False,
            "qualified_sram_macro": False,
            "ta_rtl_6_closed": False,
            "timing_or_performance": False,
        },
        "command_program_sha256": PROGRAM_SHA256,
        "command_vector_set_id": COMMAND_VECTOR_ID,
        "commands": [
            {"last": False, **dma_command},
            {"last": True, **rms_command},
        ],
        "composition": {
            "dma_destination_address": dma_fields["destination"],
            "expected_output_payload_sha256": OUTPUT_SHA256,
            "expected_output_saturation_count": (
                reference.output_saturated_element_count
            ),
            "expected_normalized_payload_sha256": NORMALIZED_SHA256,
            "expected_normalized_saturation_count": (
                reference.normalized_saturated_element_count
            ),
            "graph_operation_id": "node.0001",
            "input_address": rms_fields["source0"],
            "input_payload_sha256": INPUT_SHA256,
            "inverse_rms_binary32_code": reference.inverse_rms_codes[0],
            "mean_square_binary32_code": reference.mean_square_codes[0],
            "output_address": rms_fields["destination"],
            "rmsnorm_element_count": ELEMENTS,
            "submitted_command_indices": [1, 2],
            "weight_address": rms_fields["source1"],
            "weight_payload_sha256": WEIGHT_SHA256,
        },
        "dma_payload_hex": weight_payload.hex(),
        "dma_source_vector_id": DMA_VECTOR_ID,
        "expected_codes": expected_codes,
        "graph_id": GRAPH_ID,
        "input_codes": input_codes,
        "input_source_vector_id": INPUT_VECTOR_ID,
        "kernel_ir_id": KERNEL_IR_ID,
        "normalized_codes": normalized_codes,
        "numeric_contract": NUMERIC_CONTRACT,
        "qualification_report_id": QUALIFICATION_ID,
        "schema": SCHEMA,
    }
    return {**body, "vector_set_id": _identity(body, "vector_set_id")}


def main(argv: list[str] | None = None) -> int:
    arguments = parser().parse_args(argv)
    if arguments.output.exists():
        parser().error(f"--output already exists: {arguments.output}")
    vectors = build(
        command_vectors_path=arguments.command_vectors,
        dma_vectors_path=arguments.dma_vectors,
        input_vectors_path=arguments.input_vectors,
        qualification_path=arguments.qualification,
        kernel_ir_path=arguments.kernel_ir,
    )
    schema = load_strict_json(
        ROOT
        / "schemas/compiler/tensor_accelerator/"
        "qwen_rtl_dma_rmsnorm_vectors_v1.schema.json"
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
