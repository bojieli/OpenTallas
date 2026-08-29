#!/usr/bin/env python3
"""Build source-bound RTL vectors for indexed Qwen RoPE execution."""

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
from runtime.reference.tensor_accelerator_rope import (  # noqa: E402
    NUMERIC_CONTRACT as REFERENCE_CONTRACT,
    rope_bf16 as reference_rope,
)
from runtime.tensor_accelerator.rope import (  # noqa: E402
    NUMERIC_CONTRACT,
    rope_bf16,
)


SCHEMA = "opentallas.tensor_accelerator.qwen_rtl_rope_vectors.v1"
PROGRAM_SHA256 = "f0ce6b50b01f462f837a28504e6ff9a024a24d24abf339f924875d0c2059bcec"
HEAD_RMS_VECTOR_ID = (
    "9d6ff4c9ad10e03592d02ec3edebaf6bc341285fac8c69bc09b7daa7891ee791"
)
PHYSICAL_PLAN_ID = "ba1d95462450d2cd059e6b55271c73ea90895515c9a4129bba1b51df265109c3"
KERNEL_IR_ID = "270b7609f2ea101593b3870a498bda3320336c94b27862dca7f991352727e050"
GRAPH_ID = "989ab0d4dae37c783e2eff349e1ed1fe16279288e12a19a94975f43b0254426f"
SHARD_SHA256 = "4cc984816239b7b9215743b405300e1ecfe26ac1bb62177f2874c20b3889b62b"
QUALIFICATION_ID = "42be4b6e14ca271c583e0b8f4bb0bc9a5e854e4e5aa918b0e90acc6217d763ae"
EXECUTION_REPORT_ID = (
    "77b849e49608cacf9522eb16fad289385523c39618425e1e1c5f30126e504746"
)
REQUEST_ID = "0876463dce42a04c27836502e83e202c2d7b95fe0b166d42f6d3cd1e5417dcd0"
TABLE_SHA256 = "82b9d0c0dc0c98906ced230591852dbd27d73760de42df8de253ae29243034b9"
ROW0_SHA256 = "b262f6c135906b739518f2c53c49f425e115901a9e6469e024ee3921efd62e56"
ROW7999_SHA256 = "c3245faed3b4547a5bcb76623152d12a210c5229e59fc72fa41aacb6b16a1af7"
Q_INPUT_SHA256 = "bf01d5254a7616bfffac6f789fbae1b94c68c5201944c8faf297b803987a401c"
K_INPUT_SHA256 = "71af5033456b74d137d248f4019f848aedb8c8f758f952612082ad48d50f6a66"
Q7999_SHA256 = "a846335c825cf9fb06213220acf157c6a805376b1324a7cec09d6fa4621e718d"
K7999_SHA256 = "ce427ae533331720b9b58dde633e3ca352fa9fe0d3dd09d8cab222b799963858"
SHARD_BASE = 15 << 30
TABLE_ADDRESS = 16_384_425_984
TABLE_OFFSET = TABLE_ADDRESS - SHARD_BASE
TABLE_ROWS = 8_000
ROW_BYTES = 512
TABLE_BYTES = TABLE_ROWS * ROW_BYTES
COMMAND_START = 3_079
COMMAND_END = 3_080
QUERY_HEADS = 32
KEY_HEADS = 8
HEAD_WIDTH = 128
QUERY_ELEMENTS = QUERY_HEADS * HEAD_WIDTH
KEY_ELEMENTS = KEY_HEADS * HEAD_WIDTH
TOTAL_ELEMENTS = QUERY_ELEMENTS + KEY_ELEMENTS

OPTIMIZED_ORACLE = ROOT / "runtime/tensor_accelerator/rope.py"
SCALAR_ORACLE = ROOT / "runtime/reference/tensor_accelerator_rope.py"


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--head-rmsnorm-vectors", required=True, type=Path)
    result.add_argument("--kernel-ir", required=True, type=Path)
    result.add_argument("--physical-plan", required=True, type=Path)
    result.add_argument("--command-program", required=True, type=Path)
    result.add_argument("--hbm-shard", required=True, type=Path)
    result.add_argument("--execution-report", required=True, type=Path)
    result.add_argument("--execution-request", required=True, type=Path)
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


def _validate_sources(
    head_vectors: dict[str, Any],
    kernel_ir: dict[str, Any],
    physical_plan: dict[str, Any],
    qualification: dict[str, Any],
) -> None:
    _validate_identity(head_vectors, "vector_set_id", HEAD_RMS_VECTOR_ID)
    _validate_identity(kernel_ir, "kernel_ir_id", KERNEL_IR_ID)
    _validate_identity(physical_plan, "physical_plan_id", PHYSICAL_PLAN_ID)
    _validate_identity(qualification, "report_id", QUALIFICATION_ID)
    if (
        head_vectors.get("command_program_sha256") != PROGRAM_SHA256
        or kernel_ir.get("graph_id") != GRAPH_ID
        or physical_plan.get("graph_id") != GRAPH_ID
        or NUMERIC_CONTRACT != REFERENCE_CONTRACT
    ):
        raise ValueError("RoPE source identity differs")
    expected_range = {
        "command_count": 2,
        "command_start": COMMAND_START,
        "kernel_index": 7,
        "operation_id": "node.0007",
    }
    observed = [
        item
        for item in physical_plan["command_program"]["kernel_command_ranges"]
        if item["kernel_index"] == 7
    ]
    if observed != [expected_range]:
        raise ValueError("RoPE command range differs")
    kernel = kernel_ir["kernels"][7]
    if (
        kernel["source_operation_id"] != "node.0007"
        or kernel["kind"] != "ROPE"
        or kernel["numeric_contract"] != NUMERIC_CONTRACT
        or kernel["shape"] != {"head_dim": HEAD_WIDTH}
        or kernel["attributes"]["query_heads"] != QUERY_HEADS
        or kernel["attributes"]["key_value_heads"] != KEY_HEADS
        or kernel["attributes"]["max_positions"] != TABLE_ROWS
    ):
        raise ValueError("RoPE kernel contract differs")
    table = physical_plan["hbm"]["coefficient_table"]
    if table != {
        "address": TABLE_ADDRESS,
        "layout": "position_major_cos_then_sin_bf16",
        "offset_bytes": TABLE_ADDRESS,
        "payload_sha256": TABLE_SHA256,
        "positions": TABLE_ROWS,
        "row_bytes": ROW_BYTES,
        "size_bytes": TABLE_BYTES,
    }:
        raise ValueError("RoPE HBM table mapping differs")
    if (
        qualification.get("status") != "pass"
        or qualification["input"] != {
            "embedding_row_payload_sha256": (
                "6f57745a3765e8651c07b849d199577ec673d24cc40beb25bbaa72c6aadf73bb"
            ),
            "position_id": 7999,
            "token_id": 0,
        }
        or qualification["rope"]["coefficient_table_payload_sha256"]
        != TABLE_SHA256
        or qualification["rope"]["coefficient_row_payload_sha256"]
        != ROW7999_SHA256
        or qualification["outputs"]["q_rotary"]["payload_sha256"]
        != Q7999_SHA256
        or qualification["outputs"]["k_rotary"]["payload_sha256"]
        != K7999_SHA256
    ):
        raise ValueError("position-7999 RoPE qualification differs")


def build(
    *,
    head_rmsnorm_vectors_path: Path,
    kernel_ir_path: Path,
    physical_plan_path: Path,
    command_program_path: Path,
    hbm_shard_path: Path,
    execution_report_path: Path,
    execution_request_path: Path,
    qkv_qualification_path: Path,
) -> dict[str, Any]:
    head_vectors = load_strict_json(head_rmsnorm_vectors_path)
    kernel_ir = load_strict_json(kernel_ir_path)
    physical_plan = load_strict_json(physical_plan_path)
    qualification = load_strict_json(qkv_qualification_path)
    _validate_sources(head_vectors, kernel_ir, physical_plan, qualification)

    request = load_strict_json(execution_request_path)
    _validate_identity(request, "request_id", REQUEST_ID)
    if (
        request.get("position_start") != 0
        or request.get("position_end") != 1
        or request.get("span_tokens") != 1
        or request.get("token_id") != 0
    ):
        raise ValueError("full-model execution request is not position zero")

    execution = load_strict_json(execution_report_path)
    _validate_identity(execution, "report_id", EXECUTION_REPORT_ID)
    event = next(
        item for item in execution["events"] if item["operation_id"] == "node.0007"
    )
    if (
        event["command_start"] != COMMAND_START
        or event["command_count"] != 2
        or event["outputs"]["layer.0.q_rotary"]["payload_sha256"]
        != Q_INPUT_SHA256
        or event["outputs"]["layer.0.k_rotary"]["payload_sha256"]
        != K_INPUT_SHA256
    ):
        raise ValueError("position-zero full-model RoPE execution differs")

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
    if commands[0]["expected_fields"] != {
        "opcode": 2,
        "engine": 1,
        "flags": 0,
        "index": 3079,
        "kernel_index": 7,
        "source0": TABLE_ADDRESS,
        "source1": 4,
        "destination": 13_631_488,
        "auxiliary": 0,
        "size0": ROW_BYTES,
        "size1": ROW_BYTES,
        "size2": TABLE_ROWS,
        "size3": 4,
    } or commands[1]["expected_fields"] != {
        "opcode": 33,
        "engine": 3,
        "flags": 0,
        "index": 3080,
        "kernel_index": 7,
        "source0": 11_534_336,
        "source1": 12_591_104,
        "destination": 14_680_064,
        "auxiliary": 15_728_640,
        "size0": QUERY_HEADS,
        "size1": KEY_HEADS,
        "size2": HEAD_WIDTH,
        "size3": 13_631_488,
    }:
        raise ValueError("authentic RoPE command fields differ")

    expected_name = (
        "hbm.00015.4cc984816239b7b9215743b405300e1ecfe26ac1bb62177f2874c20b3889b62b.bin"
    )
    if (
        hbm_shard_path.name != expected_name
        or hbm_shard_path.stat().st_size != 1 << 30
        or _sha256_file(hbm_shard_path) != SHARD_SHA256
    ):
        raise ValueError("immutable Qwen RoPE HBM shard differs")
    with hbm_shard_path.open("rb") as handle:
        handle.seek(TABLE_OFFSET)
        table_payload = handle.read(TABLE_BYTES)
    if len(table_payload) != TABLE_BYTES or _sha256(table_payload) != TABLE_SHA256:
        raise ValueError("deployed RoPE coefficient table differs")

    q_codes = [int(value) for value in head_vectors["q_output_codes"]]
    k_codes = [int(value) for value in head_vectors["k_output_codes"]]
    if (
        len(q_codes) != QUERY_ELEMENTS
        or len(k_codes) != KEY_ELEMENTS
        or _sha256(_payload(q_codes)) != Q_INPUT_SHA256
        or _sha256(_payload(k_codes)) != K_INPUT_SHA256
    ):
        raise ValueError("retained Q/K normalized inputs differ")
    q_matrix = np.asarray(q_codes, dtype=np.uint16).reshape(
        QUERY_HEADS, HEAD_WIDTH
    )
    k_matrix = np.asarray(k_codes, dtype=np.uint16).reshape(KEY_HEADS, HEAD_WIDTH)

    cases: list[dict[str, Any]] = []
    for position, expected_row_hash, expected_q_hash, expected_k_hash in (
        (0, ROW0_SHA256, Q_INPUT_SHA256, K_INPUT_SHA256),
        (7999, ROW7999_SHA256, Q7999_SHA256, K7999_SHA256),
    ):
        start = position * ROW_BYTES
        row_payload = table_payload[start : start + ROW_BYTES]
        row_codes = _codes(row_payload)
        if len(row_codes) != 2 * HEAD_WIDTH or _sha256(row_payload) != expected_row_hash:
            raise ValueError(f"position-{position} coefficient row differs")
        optimized = rope_bf16(q_matrix, k_matrix, row_codes)
        scalar = reference_rope(
            q_matrix.astype(int).tolist(),
            k_matrix.astype(int).tolist(),
            row_codes[:HEAD_WIDTH],
            row_codes[HEAD_WIDTH:],
        )
        q_output = optimized.query_values.reshape(-1).astype(int).tolist()
        k_output = optimized.key_values.reshape(-1).astype(int).tolist()
        if (
            q_output != [value for row in scalar.query_values for value in row]
            or k_output != [value for row in scalar.key_values for value in row]
            or optimized.multiplication_saturated_element_count
            != scalar.multiplication_saturated_element_count
            or optimized.addition_saturated_element_count
            != scalar.addition_saturated_element_count
            or _sha256(_payload(q_output)) != expected_q_hash
            or _sha256(_payload(k_output)) != expected_k_hash
        ):
            raise ValueError(f"position-{position} optimized/scalar RoPE differs")
        cases.append(
            {
                "addition_saturation_count": (
                    optimized.addition_saturated_element_count
                ),
                "coefficient_codes": row_codes,
                "coefficient_payload_sha256": expected_row_hash,
                "index_payload_hex": struct.pack("<I", position).hex(),
                "k_output_codes": k_output,
                "k_output_payload_sha256": expected_k_hash,
                "multiplication_saturation_count": (
                    optimized.multiplication_saturated_element_count
                ),
                "position": position,
                "q_output_codes": q_output,
                "q_output_payload_sha256": expected_q_hash,
                "selected_hbm_address": TABLE_ADDRESS + position * ROW_BYTES,
            }
        )

    body: dict[str, Any] = {
        "cases": cases,
        "claim_boundary": {
            "all_qkv_preparation_graph_operations_individually_closed": True,
            "architectural_simulator_output_correlated": True,
            "authentic_command_records": True,
            "behavioral_hbm_and_sram": True,
            "complete_layer_execution": False,
            "complete_rope_graph_operation": True,
            "connected_qkv_preparation_program": False,
            "exact_scalar_all_elements": True,
            "generic_position_selection": True,
            "preloaded_q_and_k_normalized_inputs": True,
            "program_order_and_fail_stop": True,
            "qualified_hbm_phy": False,
            "qualified_position_7999_profile_replay": True,
            "qualified_sram_macro": False,
            "ta_rtl_6_closed": False,
            "timing_or_performance": False,
        },
        "command_program_sha256": PROGRAM_SHA256,
        "commands": commands,
        "composition": {
            "addition_count": TOTAL_ELEMENTS,
            "coefficient_read_count": 2 * HEAD_WIDTH,
            "command_count": 2,
            "command_end": COMMAND_END,
            "command_start": COMMAND_START,
            "dma_hbm_bytes": ROW_BYTES,
            "dma_hbm_request_count": ROW_BYTES // 64,
            "dma_index_read_count": 2,
            "dma_sram_write_count": ROW_BYTES // 16,
            "element_count": TOTAL_ELEMENTS,
            "graph_operation_ids": ["node.0007"],
            "key_input_read_count": KEY_ELEMENTS,
            "key_output_write_count": KEY_ELEMENTS,
            "multiplication_count": 2 * TOTAL_ELEMENTS,
            "query_input_read_count": QUERY_ELEMENTS,
            "query_output_write_count": QUERY_ELEMENTS,
        },
        "graph_id": GRAPH_ID,
        "hbm_shard": {
            "logical_base_address": SHARD_BASE,
            "path": f"memory/hbm/{expected_name}",
            "sha256": SHARD_SHA256,
            "size_bytes": 1 << 30,
            "table_offset_bytes": TABLE_OFFSET,
            "table_payload_sha256": TABLE_SHA256,
            "table_size_bytes": TABLE_BYTES,
        },
        "head_rmsnorm_vector_set_id": HEAD_RMS_VECTOR_ID,
        "kernel_ir_id": KERNEL_IR_ID,
        "k_input_codes": k_codes,
        "numeric_contract": NUMERIC_CONTRACT,
        "oracle_sources": {
            "optimized": {
                "path": str(OPTIMIZED_ORACLE.relative_to(ROOT)),
                "sha256": _sha256_file(OPTIMIZED_ORACLE),
            },
            "scalar": {
                "path": str(SCALAR_ORACLE.relative_to(ROOT)),
                "sha256": _sha256_file(SCALAR_ORACLE),
            },
        },
        "physical_plan_id": PHYSICAL_PLAN_ID,
        "q_input_codes": q_codes,
        "qkv_qualification_report_id": QUALIFICATION_ID,
        "schema": SCHEMA,
        "source_execution_report_id": EXECUTION_REPORT_ID,
        "source_execution_request_id": REQUEST_ID,
    }
    return {**body, "vector_set_id": _identity(body, "vector_set_id")}


def main(argv: list[str] | None = None) -> int:
    arguments = parser().parse_args(argv)
    if arguments.output.exists():
        parser().error(f"--output already exists: {arguments.output}")
    vectors = build(
        head_rmsnorm_vectors_path=arguments.head_rmsnorm_vectors,
        kernel_ir_path=arguments.kernel_ir,
        physical_plan_path=arguments.physical_plan,
        command_program_path=arguments.command_program,
        hbm_shard_path=arguments.hbm_shard,
        execution_report_path=arguments.execution_report,
        execution_request_path=arguments.execution_request,
        qkv_qualification_path=arguments.qkv_qualification,
    )
    schema_path = (
        ROOT
        / "schemas/compiler/tensor_accelerator/qwen_rtl_rope_vectors_v1.schema.json"
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
