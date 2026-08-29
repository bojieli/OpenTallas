#!/usr/bin/env python3
"""Build source-bound RTL vectors for layer-0 Q/K per-head RMSNorm."""

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
    command_abi,
    decode,
)
from runtime.reference.tensor_accelerator_rmsnorm import (  # noqa: E402
    NUMERIC_CONTRACT as REFERENCE_CONTRACT,
    rms_norm_bf16 as reference_rmsnorm,
)
from runtime.tensor_accelerator.rmsnorm import (  # noqa: E402
    NUMERIC_CONTRACT,
    rms_norm_bf16,
)


SCHEMA = "opentallas.tensor_accelerator.qwen_rtl_head_rmsnorm_vectors.v1"
PROGRAM_SHA256 = "f0ce6b50b01f462f837a28504e6ff9a024a24d24abf339f924875d0c2059bcec"
COMMAND_VECTOR_ID = "420ada71f902c8e43b9e5866d9c57ab8e3a1ced59e25c01b20793c94cf45b1a2"
Q_VECTOR_ID = "32dbdaa446fc4192f31a0a26394e04094e74c6459858d8a6b0135c11fc9e324b"
KV_VECTOR_ID = "ee711ae0b31985d0215b9f0c14233c3a2cb0cade3f79809bfc00493d369d5873"
PHYSICAL_PLAN_ID = "ba1d95462450d2cd059e6b55271c73ea90895515c9a4129bba1b51df265109c3"
KERNEL_IR_ID = "270b7609f2ea101593b3870a498bda3320336c94b27862dca7f991352727e050"
GRAPH_ID = "989ab0d4dae37c783e2eff349e1ed1fe16279288e12a19a94975f43b0254426f"
SHARD_SHA256 = "656958bc279d27f01126b855c25daeddc42f37f69445e97c2df432cee6dffb37"
QUALIFICATION_ID = "42be4b6e14ca271c583e0b8f4bb0bc9a5e854e4e5aa918b0e90acc6217d763ae"
EXECUTION_REPORT_ID = "77b849e49608cacf9522eb16fad289385523c39618425e1e1c5f30126e504746"
SHARD_BASE = 1 << 30
WEIGHT_OFFSET = 221_282_304
WEIGHT_BYTES = 512
WEIGHT_SHA256 = "8de1e5fb0a491567ccbb301547a3ef8d4c826f702cab737dd6eeb3a216017dd1"
WIDTH = 128
EPSILON_CODE = 0x358637BD
COMMAND_START = 3_075
COMMAND_END = 3_078
COMMAND_COUNT = 4
TOTAL_ROWS = 40
TOTAL_ELEMENTS = 5_120

OPERATIONS: tuple[dict[str, Any], ...] = (
    {
        "name": "q_head_rmsnorm",
        "operation_id": "node.0005",
        "kernel_index": 5,
        "command_start": 3_075,
        "rows": 32,
        "input_address": 6_291_456,
        "weight_hbm_address": 1_295_024_128,
        "weight_sram_address": 9_437_184,
        "output_address": 11_534_336,
        "input_sha256": (
            "b900b79fd38ff6a9bff470ac27e9672b0c3724b84f6a1f7e964c2ec0918ea0ff"
        ),
        "weight_sha256": (
            "ad88a3013b2d8ecd138c36460751296c56bed2eff2d5d3a66377db04fd9e0799"
        ),
        "normalized_sha256": (
            "48bc058ec9c12bae7b8b94dc2d5761e36cc508f4f7b02265c708662d89a369ca"
        ),
        "mean_square_sha256": (
            "e10c17ec2a238ecebbad32e5c85a6822babfec8ac7650eb7bba2a67fc0003cb2"
        ),
        "inverse_rms_sha256": (
            "12a8e58463d481658ffee21140fd06ecc6ff799fcd27b2cab650aa7508f89aa9"
        ),
        "output_sha256": (
            "bf01d5254a7616bfffac6f789fbae1b94c68c5201944c8faf297b803987a401c"
        ),
    },
    {
        "name": "k_head_rmsnorm",
        "operation_id": "node.0006",
        "kernel_index": 6,
        "command_start": 3_077,
        "rows": 8,
        "input_address": 7_340_032,
        "weight_hbm_address": 1_295_024_384,
        "weight_sram_address": 10_485_760,
        "output_address": 12_591_104,
        "input_sha256": (
            "dd690fbd9886a0af94cc6b2477ef5bfcc84fe66cac66f345f2ec654a83b28403"
        ),
        "weight_sha256": (
            "aaf5042c20082b5c13daed62ad9627f426cda5edc38eca48bd3f956da4eb05cd"
        ),
        "normalized_sha256": (
            "5c947fbf3d9502d2ad1142fc6584d0cad5503f7c39bc4ed14ee8f773200e1e27"
        ),
        "mean_square_sha256": (
            "b1d45efa4ea83b59c1638bf041adc2e30dfb98c8b4ea2d156c247213ff05f065"
        ),
        "inverse_rms_sha256": (
            "b088f0e2a9c0cb618be3df9e9752be637198b2eb8e1a457fa7862a12691f1d71"
        ),
        "output_sha256": (
            "71af5033456b74d137d248f4019f848aedb8c8f758f952612082ad48d50f6a66"
        ),
    },
)


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--command-vectors", required=True, type=Path)
    result.add_argument("--q-projection-vectors", required=True, type=Path)
    result.add_argument("--kv-projection-vectors", required=True, type=Path)
    result.add_argument("--kernel-ir", required=True, type=Path)
    result.add_argument("--physical-plan", required=True, type=Path)
    result.add_argument("--command-program", required=True, type=Path)
    result.add_argument("--hbm-shard", required=True, type=Path)
    result.add_argument("--execution-report", required=True, type=Path)
    result.add_argument("--qkv-qualification", required=True, type=Path)
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
        "opcode": values[0],
        "engine": values[1],
        "flags": values[2],
        "index": values[3],
        "kernel_index": values[4],
        "source0": values[5],
        "source1": values[6],
        "destination": values[7],
        "auxiliary": values[8],
        "size0": values[9],
        "size1": values[10],
        "size2": values[11],
        "size3": values[12],
    }


def _command(raw: bytes, *, last: bool) -> dict[str, Any]:
    fields = _fields(raw)
    return {
        "abi_major": ABI_MAJOR,
        "abi_minor": ABI_MINOR,
        "expected_error": 0,
        "expected_fields": fields,
        "expected_index": fields["index"],
        "last": last,
        "name": f"command_{fields['index']}",
        "record_hex": f"{int.from_bytes(raw, 'little'):0128x}",
    }


def _codes(payload: bytes) -> list[int]:
    return list(struct.unpack(f"<{len(payload) // 2}H", payload))


def _payload(codes: list[int]) -> bytes:
    return struct.pack(f"<{len(codes)}H", *codes)


def _u32_payload(codes: list[int]) -> bytes:
    return struct.pack(f"<{len(codes)}I", *codes)


def _validate_sources(
    command_vectors: dict[str, Any],
    q_vectors: dict[str, Any],
    kv_vectors: dict[str, Any],
    kernel_ir: dict[str, Any],
    physical_plan: dict[str, Any],
    qualification: dict[str, Any],
) -> None:
    _validate_identity(command_vectors, "vector_set_id", COMMAND_VECTOR_ID)
    _validate_identity(q_vectors, "vector_set_id", Q_VECTOR_ID)
    _validate_identity(kv_vectors, "vector_set_id", KV_VECTOR_ID)
    _validate_identity(kernel_ir, "kernel_ir_id", KERNEL_IR_ID)
    _validate_identity(physical_plan, "physical_plan_id", PHYSICAL_PLAN_ID)
    _validate_identity(qualification, "report_id", QUALIFICATION_ID)
    if (
        command_vectors.get("command_program_sha256") != PROGRAM_SHA256
        or q_vectors.get("command_program_sha256") != PROGRAM_SHA256
        or kv_vectors.get("command_program_sha256") != PROGRAM_SHA256
        or kernel_ir.get("graph_id") != GRAPH_ID
        or physical_plan.get("graph_id") != GRAPH_ID
        or NUMERIC_CONTRACT != REFERENCE_CONTRACT
    ):
        raise ValueError("head RMSNorm source identity differs")
    expected_ranges = [
        {
            "command_count": 2,
            "command_start": item["command_start"],
            "kernel_index": item["kernel_index"],
            "operation_id": item["operation_id"],
        }
        for item in OPERATIONS
    ]
    observed_ranges = [
        item
        for item in physical_plan["command_program"]["kernel_command_ranges"]
        if item["kernel_index"] in {5, 6}
    ]
    if observed_ranges != expected_ranges:
        raise ValueError("head RMSNorm command ranges differ")
    kernels = kernel_ir["kernels"]
    for item in OPERATIONS:
        kernel = kernels[item["kernel_index"]]
        if (
            kernel["source_operation_id"] != item["operation_id"]
            or kernel["kind"] != "RMS_NORM"
            or kernel["numeric_contract"] != NUMERIC_CONTRACT
            or kernel["shape"]["width"] != WIDTH
        ):
            raise ValueError(f"{item['name']} kernel contract differs")
    qualified = qualification["intermediates"]
    if (
        qualification.get("status") != "pass"
        or qualified["q_norm"]["payload_sha256"]
        != OPERATIONS[0]["output_sha256"]
        or qualified["k_norm"]["payload_sha256"]
        != OPERATIONS[1]["output_sha256"]
    ):
        raise ValueError("head RMSNorm qualification differs")


def build(
    *,
    command_vectors_path: Path,
    q_projection_vectors_path: Path,
    kv_projection_vectors_path: Path,
    kernel_ir_path: Path,
    physical_plan_path: Path,
    command_program_path: Path,
    hbm_shard_path: Path,
    execution_report_path: Path,
    qkv_qualification_path: Path,
) -> dict[str, Any]:
    command_vectors = load_strict_json(command_vectors_path)
    q_vectors = load_strict_json(q_projection_vectors_path)
    kv_vectors = load_strict_json(kv_projection_vectors_path)
    kernel_ir = load_strict_json(kernel_ir_path)
    physical_plan = load_strict_json(physical_plan_path)
    qualification = load_strict_json(qkv_qualification_path)
    _validate_sources(
        command_vectors,
        q_vectors,
        kv_vectors,
        kernel_ir,
        physical_plan,
        qualification,
    )

    execution = load_strict_json(execution_report_path)
    _validate_identity(execution, "report_id", EXECUTION_REPORT_ID)
    events = {item["operation_id"]: item for item in execution["events"]}
    if any(
        events[item["operation_id"]]["outputs"][
            "layer.0.q_norm" if item["kernel_index"] == 5 else "layer.0.k_norm"
        ]["payload_sha256"]
        != item["output_sha256"]
        for item in OPERATIONS
    ):
        raise ValueError("full-model head RMSNorm execution differs")

    program = command_program_path.read_bytes()
    if _sha256(program) != PROGRAM_SHA256 or command_abi(program) != (
        ABI_MAJOR,
        ABI_MINOR,
    ):
        raise ValueError("complete Qwen command program differs")
    decoded = decode(program)
    commands: list[dict[str, Any]] = []
    for index in range(COMMAND_START, COMMAND_END + 1):
        start = 32 + index * COMMAND_WITH_CRC.size
        raw = program[start : start + COMMAND_WITH_CRC.size]
        if decoded[index].index != index or len(raw) != COMMAND_WITH_CRC.size:
            raise ValueError(f"command {index} differs")
        commands.append(_command(raw, last=index == COMMAND_END))

    if (
        hbm_shard_path.name
        != "hbm.00001.656958bc279d27f01126b855c25daeddc42f37f69445e97c2df432cee6dffb37.bin"
        or hbm_shard_path.stat().st_size != 1 << 30
        or _sha256_file(hbm_shard_path) != SHARD_SHA256
    ):
        raise ValueError("immutable Qwen HBM shard differs")
    with hbm_shard_path.open("rb") as handle:
        handle.seek(WEIGHT_OFFSET)
        weight_payload = handle.read(WEIGHT_BYTES)
    if len(weight_payload) != WEIGHT_BYTES or _sha256(weight_payload) != WEIGHT_SHA256:
        raise ValueError("head RMSNorm deployed weights differ")

    inputs = [
        [int(value) for value in q_vectors["expected_output_codes"]],
        [int(value) for value in kv_vectors["expected_output_codes"][:1_024]],
    ]
    weights = [_codes(weight_payload[:256]), _codes(weight_payload[256:])]
    operation_evidence: list[dict[str, Any]] = []
    retained: dict[str, list[int]] = {}
    for item, input_codes, weight_codes in zip(
        OPERATIONS, inputs, weights, strict=True
    ):
        rows = item["rows"]
        matrix = np.asarray(input_codes, dtype=np.uint16).reshape(rows, WIDTH)
        optimized = rms_norm_bf16(matrix, weight_codes, epsilon_code=EPSILON_CODE)
        reference = reference_rmsnorm(
            matrix.astype(int).tolist(), weight_codes, epsilon_code=EPSILON_CODE
        )
        optimized_values = optimized.values.reshape(-1).astype(int).tolist()
        normalized = optimized.normalized_values.reshape(-1).astype(int).tolist()
        means = optimized.mean_square_codes.astype(int).tolist()
        inverses = optimized.inverse_rms_codes.astype(int).tolist()
        if (
            optimized_values != [value for row in reference.values for value in row]
            or normalized
            != [value for row in reference.normalized_values for value in row]
            or means != list(reference.mean_square_codes)
            or inverses != list(reference.inverse_rms_codes)
            or optimized.normalized_saturated_element_count
            != reference.normalized_saturated_element_count
            or optimized.output_saturated_element_count
            != reference.output_saturated_element_count
        ):
            raise ValueError(f"{item['name']} optimized/reference result differs")
        hashes = {
            "input_payload_sha256": _sha256(_payload(input_codes)),
            "weight_payload_sha256": _sha256(_payload(weight_codes)),
            "normalized_payload_sha256": _sha256(_payload(normalized)),
            "mean_square_payload_sha256": _sha256(_u32_payload(means)),
            "inverse_rms_payload_sha256": _sha256(_u32_payload(inverses)),
            "output_payload_sha256": _sha256(_payload(optimized_values)),
        }
        expected_hashes = {
            "input_payload_sha256": item["input_sha256"],
            "weight_payload_sha256": item["weight_sha256"],
            "normalized_payload_sha256": item["normalized_sha256"],
            "mean_square_payload_sha256": item["mean_square_sha256"],
            "inverse_rms_payload_sha256": item["inverse_rms_sha256"],
            "output_payload_sha256": item["output_sha256"],
        }
        if hashes != expected_hashes:
            raise ValueError(f"{item['name']} payload differs from source evidence")
        prefix = "q" if item["kernel_index"] == 5 else "k"
        retained[f"{prefix}_input_codes"] = input_codes
        retained[f"{prefix}_weight_codes"] = weight_codes
        retained[f"{prefix}_normalized_codes"] = normalized
        retained[f"{prefix}_mean_square_codes"] = means
        retained[f"{prefix}_inverse_rms_codes"] = inverses
        retained[f"{prefix}_output_codes"] = optimized_values
        operation_evidence.append(
            {
                "command_end": item["command_start"] + 1,
                "command_start": item["command_start"],
                "element_count": rows * WIDTH,
                **hashes,
                "input_address": item["input_address"],
                "kernel_index": item["kernel_index"],
                "normalized_saturation_count": (
                    optimized.normalized_saturated_element_count
                ),
                "operation_id": item["operation_id"],
                "output_address": item["output_address"],
                "output_saturation_count": optimized.output_saturated_element_count,
                "projection": prefix,
                "row_count": rows,
                "weight_hbm_address": item["weight_hbm_address"],
                "weight_sram_address": item["weight_sram_address"],
                "width": WIDTH,
            }
        )

    body: dict[str, Any] = {
        "claim_boundary": {
            "architectural_simulator_output_correlated": True,
            "authentic_command_records": True,
            "behavioral_hbm_and_sram": True,
            "complete_k_head_rmsnorm_graph_operation": True,
            "complete_layer_execution": False,
            "complete_q_head_rmsnorm_graph_operation": True,
            "complete_qkv_preparation": False,
            "exact_scalar_all_rows": True,
            "preloaded_q_and_k_projection_outputs": True,
            "program_order_and_fail_stop": True,
            "qualified_hbm_phy": False,
            "qualified_sram_macro": False,
            "ta_rtl_6_closed": False,
            "timing_or_performance": False,
        },
        "command_program_sha256": PROGRAM_SHA256,
        "command_vector_set_id": COMMAND_VECTOR_ID,
        "commands": commands,
        "composition": {
            "command_count": COMMAND_COUNT,
            "command_end": COMMAND_END,
            "command_start": COMMAND_START,
            "dma_hbm_bytes": WEIGHT_BYTES,
            "dma_hbm_request_count": 8,
            "dma_sram_write_count": 32,
            "epsilon_addition_count": TOTAL_ROWS,
            "final_weight_multiply_count": TOTAL_ELEMENTS,
            "graph_operation_ids": ["node.0005", "node.0006"],
            "input_read_count": TOTAL_ELEMENTS,
            "input_square_multiply_count": TOTAL_ELEMENTS,
            "normalization_multiply_count": TOTAL_ELEMENTS,
            "operations": operation_evidence,
            "reciprocal_square_root_count": TOTAL_ROWS,
            "reduction_add_count": TOTAL_ROWS * (WIDTH - 1),
            "row_count": TOTAL_ROWS,
            "sram_output_write_count": TOTAL_ELEMENTS,
            "weight_read_count": TOTAL_ELEMENTS,
            "width": WIDTH,
        },
        "graph_id": GRAPH_ID,
        "hbm_shard": {
            "logical_base_address": SHARD_BASE,
            "path": (
                "memory/hbm/"
                "hbm.00001.656958bc279d27f01126b855c25daeddc42f37f69445e97c2df432cee6dffb37.bin"
            ),
            "sha256": SHARD_SHA256,
            "size_bytes": 1 << 30,
            "slice_offset_bytes": WEIGHT_OFFSET,
            "slice_size_bytes": WEIGHT_BYTES,
        },
        "kernel_ir_id": KERNEL_IR_ID,
        "kv_projection_vector_set_id": KV_VECTOR_ID,
        "numeric_contract": NUMERIC_CONTRACT,
        "physical_plan_id": PHYSICAL_PLAN_ID,
        "q_projection_vector_set_id": Q_VECTOR_ID,
        "qkv_qualification_report_id": QUALIFICATION_ID,
        "schema": SCHEMA,
        "source_execution_report_id": EXECUTION_REPORT_ID,
        "weight_payload_hex": weight_payload.hex(),
        "weight_payload_sha256": WEIGHT_SHA256,
        **retained,
    }
    return {**body, "vector_set_id": _identity(body, "vector_set_id")}


def main(argv: list[str] | None = None) -> int:
    arguments = parser().parse_args(argv)
    if arguments.output.exists():
        parser().error(f"--output already exists: {arguments.output}")
    vectors = build(
        command_vectors_path=arguments.command_vectors,
        q_projection_vectors_path=arguments.q_projection_vectors,
        kv_projection_vectors_path=arguments.kv_projection_vectors,
        kernel_ir_path=arguments.kernel_ir,
        physical_plan_path=arguments.physical_plan,
        command_program_path=arguments.command_program,
        hbm_shard_path=arguments.hbm_shard,
        execution_report_path=arguments.execution_report,
        qkv_qualification_path=arguments.qkv_qualification,
    )
    schema_path = (
        ROOT
        / "schemas/compiler/tensor_accelerator/"
        "qwen_rtl_head_rmsnorm_vectors_v1.schema.json"
    )
    if schema_path.is_file():
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
