#!/usr/bin/env python3
"""Build authentic layer-0 ADD_BF16 RTL vectors from frozen Qwen evidence."""

from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path
import sys
from typing import Any, Callable

from jsonschema import Draft202012Validator
import numpy as np

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
from runtime.reference.tensor_accelerator_elementwise import (  # noqa: E402
    ElementwiseReferenceError,
    bf16_add_rne as reference_add,
)
from runtime.tensor_accelerator.bf16 import (  # noqa: E402
    dense_bf16_linear_bf16,
)
from runtime.tensor_accelerator.elementwise import (  # noqa: E402
    ElementwiseKernelError,
    bf16_add_rne,
)


SCHEMA = "opentallas.tensor_accelerator.qwen_rtl_add_vectors.v1"
BUILD_ID = "3460d88ce16f5ef0ca4d1277daf8ebb19ae555e88822f95d55deb4aa8cad290f"
PROGRAM_SHA256 = "f0ce6b50b01f462f837a28504e6ff9a024a24d24abf339f924875d0c2059bcec"
COMMAND_VECTOR_SET_ID = (
    "420ada71f902c8e43b9e5866d9c57ab8e3a1ced59e25c01b20793c94cf45b1a2"
)
CHECKPOINT_LOCK_ID = (
    "fa32932d73c1f605a69db3a803f1f25ef5b022a98cc3c6b5fe42b7f7af024e2a"
)
ATTENTION_REPORT_ID = (
    "cf62189cc5d3e4e370b76e68767e6630e884077bb8dc39e3ba7c05646f43ef13"
)
QUALIFICATION_REPORT_ID = (
    "94cc82dd113e16f05795c0de36930800701014e37e08267ce355ecfba3cfeea9"
)
KERNEL_IR_ID = "270b7609f2ea101593b3870a498bda3320336c94b27862dca7f991352727e050"
PHYSICAL_PLAN_ID = (
    "ba1d95462450d2cd059e6b55271c73ea90895515c9a4129bba1b51df265109c3"
)
HIDDEN_SHA256 = "6f57745a3765e8651c07b849d199577ec673d24cc40beb25bbaa72c6aadf73bb"
ATTENTION_SHA256 = (
    "d53e8a3890eb01357fb60ec2607a716179cec0eb556e28629963af655cd3e1fb"
)
PROJECTED_SHA256 = (
    "341ef1b0843309008fd558042d0c56733b82bca5cc0753a80424338a29defae5"
)
POST_ATTENTION_SHA256 = (
    "f872ce6f57ca36a30edf6abccfa2877bbb7234a905fe9e1417d99ea89ee79ec3"
)
HIDDEN_WIDTH = 4096
EMBEDDING_NAME = "model.embed_tokens.weight"
WEIGHT_NAME = "model.layers.0.self_attn.o_proj.weight"
OPERATION = {
    "command_count": 1,
    "command_start": 5131,
    "inputs": ["hidden.0", "layer.0.attention_projected"],
    "kernel_index": 11,
    "operation_id": "node.0011",
    "output": "layer.0.post_attention",
}


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(
        description="Build full authentic Qwen ADD_BF16 RTL operands and outputs"
    )
    result.add_argument("--snapshot", required=True, type=Path)
    result.add_argument("--checkpoint-lock", required=True, type=Path)
    result.add_argument("--attention-execution", required=True, type=Path)
    result.add_argument("--qualification", required=True, type=Path)
    result.add_argument("--command-vectors", required=True, type=Path)
    result.add_argument("--kernel-ir", required=True, type=Path)
    result.add_argument("--physical-plan", required=True, type=Path)
    result.add_argument("--output", required=True, type=Path)
    return result


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _identity(value: dict[str, Any], field: str) -> str:
    body = {key: item for key, item in value.items() if key != field}
    return _sha256(canonical_json_bytes(body))


def _codes_payload(codes: np.ndarray[Any, Any]) -> bytes:
    return np.ascontiguousarray(codes, dtype="<u2").tobytes(order="C")


def _capture_range(start: int, size: int) -> tuple[bytearray, Callable[[bytes], None]]:
    captured = bytearray()
    cursor = 0

    def consume(chunk: bytes) -> None:
        nonlocal cursor
        end = cursor + len(chunk)
        overlap_start = max(cursor, start)
        overlap_end = min(end, start + size)
        if overlap_start < overlap_end:
            captured.extend(chunk[overlap_start - cursor : overlap_end - cursor])
        cursor = end

    return captured, consume


def _directed_case(name: str, left: int, right: int) -> dict[str, Any]:
    if ((left | right) & 0x7F80) == 0x7F80 and (
        (left & 0x7F80) == 0x7F80 or (right & 0x7F80) == 0x7F80
    ):
        try:
            reference_add([[left]], [[right]])
        except ElementwiseReferenceError:
            return {
                "expected": 0,
                "expected_error": 1,
                "left": left,
                "name": name,
                "right": right,
                "saturated": False,
            }
        raise ValueError(f"directed nonfinite case {name} did not fail")
    try:
        optimized = bf16_add_rne([[left]], [[right]])
        reference = reference_add([[left]], [[right]])
    except (ElementwiseKernelError, ElementwiseReferenceError) as exc:
        if "overflow" not in str(exc):
            raise
        return {
            "expected": 0,
            "expected_error": 2,
            "left": left,
            "name": name,
            "right": right,
            "saturated": False,
        }
    expected = int(optimized.values[0, 0])
    saturated = optimized.output_saturated_element_count == 1
    if reference.values != ((expected,),) or (
        reference.output_saturated_element_count == 1
    ) != saturated:
        raise ValueError(f"directed case {name} implementations differ")
    return {
        "expected": expected,
        "expected_error": 0,
        "left": left,
        "name": name,
        "right": right,
        "saturated": saturated,
    }


def _directed_vectors() -> list[dict[str, Any]]:
    inputs = [
        ("positive_zero", 0x0000, 0x0000),
        ("negative_zero", 0x8000, 0x8000),
        ("mixed_zero", 0x0000, 0x8000),
        ("known_positive", 0x3F80, 0x3F00),
        ("known_mixed", 0x4000, 0xBF80),
        ("exact_cancellation", 0x3F80, 0xBF80),
        ("minimum_subnormal", 0x0001, 0x0001),
        ("subnormal_to_normal", 0x007F, 0x0001),
        ("negative_subnormal", 0x8001, 0x8001),
        ("subnormal_cancellation", 0x007F, 0x807E),
        ("tie_even", 0x3F80, 0x3B80),
        ("tie_odd", 0x3F81, 0x3B80),
        ("large_exponent_gap", 0x5F00, 0x0001),
        ("near_cancellation", 0x4F01, 0xCF00),
        ("positive_saturation", 0x7E02, 0x7F5F),
        ("negative_saturation", 0xFE02, 0xFF5F),
        ("positive_overflow", 0x7F7F, 0x7F7F),
        ("negative_overflow", 0xFF7F, 0xFF7F),
        ("infinity_input", 0x7F80, 0x3F80),
        ("nan_input", 0x3F80, 0x7FC1),
    ]
    return [_directed_case(*item) for item in inputs]


def _validate_sources(
    qualification: dict[str, Any],
    command_vectors: dict[str, Any],
    kernel_ir: dict[str, Any],
    physical_plan: dict[str, Any],
) -> dict[str, Any]:
    if (
        qualification.get("report_id") != QUALIFICATION_REPORT_ID
        or qualification.get("report_id") != _identity(qualification, "report_id")
        or qualification.get("status") != "pass"
        or qualification.get("intermediates", {})
        .get("attention_projected", {})
        .get("payload_sha256")
        != PROJECTED_SHA256
        or qualification.get("intermediates", {})
        .get("post_attention", {})
        .get("payload_sha256")
        != POST_ATTENTION_SHA256
        or command_vectors.get("vector_set_id") != COMMAND_VECTOR_SET_ID
        or command_vectors.get("command_program_sha256") != PROGRAM_SHA256
        or kernel_ir.get("kernel_ir_id") != KERNEL_IR_ID
        or physical_plan.get("physical_plan_id") != PHYSICAL_PLAN_ID
        or physical_plan.get("command_program", {}).get("sha256") != PROGRAM_SHA256
    ):
        raise ValueError("Qwen ADD source evidence differs from the frozen release")
    commands = [
        item for item in command_vectors.get("vectors", []) if item.get("name") == "add_bf16"
    ]
    kernels = [
        item for item in kernel_ir.get("kernels", []) if item.get("index") == 11
    ]
    ranges = [
        item
        for item in physical_plan.get("command_program", {}).get(
            "kernel_command_ranges", []
        )
        if item.get("kernel_index") == 11
    ]
    if len(commands) != 1 or len(kernels) != 1 or len(ranges) != 1:
        raise ValueError("Qwen ADD command/kernel coverage differs")
    kernel = kernels[0]
    if (
        kernel.get("kind") != "ADD"
        or kernel.get("numeric_contract") != "bf16_add_rne_v1"
        or kernel.get("inputs") != OPERATION["inputs"]
        or kernel.get("outputs") != [OPERATION["output"]]
        or {key: ranges[0][key] for key in ranges[0]} != {
            "command_count": 1,
            "command_start": 5131,
            "kernel_index": 11,
            "operation_id": "node.0011",
        }
    ):
        raise ValueError("Qwen ADD semantic/physical binding differs")
    command = commands[0]
    if command.get("expected_fields") != {
        "auxiliary": 0,
        "destination": 3 * 1024 * 1024,
        "engine": 3,
        "flags": 0,
        "index": 5131,
        "kernel_index": 11,
        "opcode": 0x22,
        "size0": 1,
        "size1": HIDDEN_WIDTH,
        "size2": 0,
        "size3": 0,
        "source0": 1 * 1024 * 1024,
        "source1": 2 * 1024 * 1024,
    }:
        raise ValueError("Qwen ADD command fields differ")
    return command


def build(
    *,
    snapshot: Path,
    checkpoint_lock_path: Path,
    attention_execution_path: Path,
    qualification_path: Path,
    command_vectors_path: Path,
    kernel_ir_path: Path,
    physical_plan_path: Path,
) -> dict[str, Any]:
    qualification = load_strict_json(qualification_path)
    command_vectors = load_strict_json(command_vectors_path)
    kernel_ir = load_strict_json(kernel_ir_path)
    physical_plan = load_strict_json(physical_plan_path)
    command = _validate_sources(
        qualification, command_vectors, kernel_ir, physical_plan
    )
    attention_execution = load_strict_json(attention_execution_path)
    attention = attention_execution.get("outputs", {}).get("attention", {})
    if (
        attention_execution.get("report_id") != ATTENTION_REPORT_ID
        or attention_execution.get("report_id")
        != _identity(attention_execution, "report_id")
        or attention_execution.get("status") != "pass"
        or attention.get("payload_sha256") != ATTENTION_SHA256
        or attention.get("shape") != [1, 32, 128]
        or len(attention.get("codes", [])) != HIDDEN_WIDTH
    ):
        raise ValueError("Qwen attention execution differs from the frozen release")
    attention_codes = np.asarray(attention["codes"], dtype=np.uint16).reshape(
        1, HIDDEN_WIDTH
    )
    if _sha256(_codes_payload(attention_codes)) != ATTENTION_SHA256:
        raise ValueError("Qwen attention payload identity differs")

    lock = load_checkpoint_lock(checkpoint_lock_path)
    if lock.get("lock_id") != CHECKPOINT_LOCK_ID:
        raise ValueError("Qwen checkpoint lock differs")
    with LockedCheckpointReader(snapshot, lock) as reader:
        embedding_record = reader.tensor_record(EMBEDDING_NAME)
        if embedding_record.get("shape") != [151936, HIDDEN_WIDTH]:
            raise ValueError("Qwen embedding shape differs")
        hidden_raw, hidden_consumer = _capture_range(0, HIDDEN_WIDTH * 2)
        reader.consume_tensor_payload(EMBEDDING_NAME, hidden_consumer)
        weight_raw = bytearray()
        weight_record = reader.consume_tensor_payload(WEIGHT_NAME, weight_raw.extend)
    if (
        len(hidden_raw) != HIDDEN_WIDTH * 2
        or _sha256(bytes(hidden_raw)) != HIDDEN_SHA256
        or weight_record.get("shape") != [HIDDEN_WIDTH, HIDDEN_WIDTH]
    ):
        raise ValueError("Qwen ADD checkpoint operands differ")
    hidden = np.frombuffer(bytes(hidden_raw), dtype="<u2").reshape(1, HIDDEN_WIDTH)
    weights = np.frombuffer(bytes(weight_raw), dtype="<u2").reshape(
        HIDDEN_WIDTH, HIDDEN_WIDTH
    )
    projected_result = dense_bf16_linear_bf16(
        attention_codes, weights, input_tile_rows=1, output_tile_rows=64
    )
    projected = projected_result.values
    if (
        projected_result.output_saturated_element_count != 0
        or _sha256(_codes_payload(projected)) != PROJECTED_SHA256
    ):
        raise ValueError("Qwen attention projection differs from qualification")
    added = bf16_add_rne(hidden, projected)
    reference = reference_add(hidden.tolist(), projected.tolist())
    output_codes = tuple(int(item) for item in added.values.reshape(-1).tolist())
    if (
        added.output_saturated_element_count != 0
        or reference.output_saturated_element_count != 0
        or reference.values != (output_codes,)
        or _sha256(_codes_payload(added.values)) != POST_ATTENTION_SHA256
    ):
        raise ValueError("Qwen ADD output differs from independent qualification")

    fields = command["expected_fields"]
    body = {
        "abi": {"major": 2, "minor": 5},
        "attention_execution_report_id": ATTENTION_REPORT_ID,
        "build_id": BUILD_ID,
        "checkpoint_lock_id": CHECKPOINT_LOCK_ID,
        "claim_boundary": {
            "complete_add_command": True,
            "complete_layer_execution": False,
            "external_sram_stream_boundary": True,
            "memory_macro_execution": False,
            "ta_rtl_6_closed": False,
            "timing_or_performance": False,
        },
        "command": command,
        "command_program_sha256": PROGRAM_SHA256,
        "command_vector_set_id": COMMAND_VECTOR_SET_ID,
        "directed_vectors": _directed_vectors(),
        "expected": {
            "address": fields["destination"],
            "codes": list(output_codes),
            "payload_sha256": POST_ATTENTION_SHA256,
            "tensor_id": OPERATION["output"],
        },
        "kernel_ir_id": KERNEL_IR_ID,
        "left": {
            "address": fields["source0"],
            "codes": [int(item) for item in hidden.reshape(-1).tolist()],
            "payload_sha256": HIDDEN_SHA256,
            "tensor_id": OPERATION["inputs"][0],
        },
        "numeric_contract": "bf16_add_rne_v1",
        "operand_count": HIDDEN_WIDTH,
        "operation": OPERATION,
        "physical_plan_id": PHYSICAL_PLAN_ID,
        "qualification_report_id": QUALIFICATION_REPORT_ID,
        "right": {
            "address": fields["source1"],
            "codes": [int(item) for item in projected.reshape(-1).tolist()],
            "payload_sha256": PROJECTED_SHA256,
            "tensor_id": OPERATION["inputs"][1],
        },
        "schema": SCHEMA,
    }
    return {**body, "vector_set_id": _sha256(canonical_json_bytes(body))}


def main(argv: list[str] | None = None) -> int:
    arguments = parser().parse_args(argv)
    if arguments.output.exists():
        parser().error(f"--output already exists: {arguments.output}")
    value = build(
        snapshot=arguments.snapshot,
        checkpoint_lock_path=arguments.checkpoint_lock,
        attention_execution_path=arguments.attention_execution,
        qualification_path=arguments.qualification,
        command_vectors_path=arguments.command_vectors,
        kernel_ir_path=arguments.kernel_ir,
        physical_plan_path=arguments.physical_plan,
    )
    schema = load_strict_json(
        ROOT
        / "schemas/compiler/tensor_accelerator/qwen_rtl_add_vectors_v1.schema.json"
    )
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(value)
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    with arguments.output.open("xb") as handle:
        handle.write(canonical_json_bytes(value))
        handle.flush()
        os.fsync(handle.fileno())
    print(value["vector_set_id"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
