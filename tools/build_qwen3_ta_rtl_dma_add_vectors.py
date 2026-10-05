#!/usr/bin/env python3
"""Compose source-bound DMA/ADD program-order RTL vectors.

The records are unchanged records from the frozen Qwen command program.  They
are intentionally not adjacent graph operations: the bounded composition uses
the real DMA payload as the ADD right operand to exercise a shared SRAM data
dependency.  The emitted claim boundary records that distinction explicitly.
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
from runtime.reference.tensor_accelerator_elementwise import (  # noqa: E402
    bf16_add_rne as reference_add,
)
from runtime.tensor_accelerator.elementwise import (  # noqa: E402
    bf16_add_rne,
)


SCHEMA = "opentallas.tensor_accelerator.qwen_rtl_dma_add_vectors.v1"
BUILD_ID = "3460d88ce16f5ef0ca4d1277daf8ebb19ae555e88822f95d55deb4aa8cad290f"
PROGRAM_SHA256 = "f0ce6b50b01f462f837a28504e6ff9a024a24d24abf339f924875d0c2059bcec"
DMA_VECTOR_ID = "98806ae5e1b8f3dbe1e516084b099a5f592f98acf6adb74edb0198d82ae10216"
ADD_VECTOR_ID = "e625aabe70b198319b76f8928d0b99ffe88d6d9e846eb8e0ddaeb3ba72eb7413"
DMA_PAYLOAD_SHA256 = (
    "00695bad97c2abc77a9d1ce57e4d4a5e5c2b574387fcb4029ef5ce12239b2530"
)
LEFT_PAYLOAD_SHA256 = (
    "6f57745a3765e8651c07b849d199577ec673d24cc40beb25bbaa72c6aadf73bb"
)
ELEMENTS = 4096


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(
        description="Build a bounded source-bound Qwen DMA then ADD RTL sequence"
    )
    result.add_argument("--dma-vectors", required=True, type=Path)
    result.add_argument("--add-vectors", required=True, type=Path)
    result.add_argument("--output", required=True, type=Path)
    return result


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _identity(value: dict[str, Any], field: str) -> str:
    body = {key: item for key, item in value.items() if key != field}
    return _sha256(canonical_json_bytes(body))


def _codes_payload(codes: list[int]) -> bytes:
    return np.ascontiguousarray(codes, dtype="<u2").tobytes(order="C")


def build(*, dma_vectors_path: Path, add_vectors_path: Path) -> dict[str, Any]:
    dma = load_strict_json(dma_vectors_path)
    add = load_strict_json(add_vectors_path)
    if (
        dma.get("vector_set_id") != DMA_VECTOR_ID
        or dma.get("vector_set_id") != _identity(dma, "vector_set_id")
        or add.get("vector_set_id") != ADD_VECTOR_ID
        or add.get("vector_set_id") != _identity(add, "vector_set_id")
        or dma.get("build_id") != BUILD_ID
        or add.get("build_id") != BUILD_ID
        or dma.get("command_program_sha256") != PROGRAM_SHA256
        or add.get("command_program_sha256") != PROGRAM_SHA256
    ):
        raise ValueError("retained DMA/ADD source identities differ")

    dma_command = dma.get("command", {})
    add_command = add.get("command", {})
    dma_fields = dma_command.get("expected_fields", {})
    add_fields = add_command.get("expected_fields", {})
    payload = bytes.fromhex(str(dma.get("hbm", {}).get("payload_hex", "")))
    left = list(add.get("left", {}).get("codes", []))
    if (
        dma_command.get("expected_index") != 1
        or dma_fields.get("opcode") != 1
        or dma_fields.get("destination") != add_fields.get("source1")
        or add_command.get("expected_index") != 5131
        or add_fields.get("opcode") != 0x22
        or len(payload) != ELEMENTS * 2
        or _sha256(payload) != DMA_PAYLOAD_SHA256
        or len(left) != ELEMENTS
        or _sha256(_codes_payload(left)) != LEFT_PAYLOAD_SHA256
    ):
        raise ValueError("retained DMA/ADD composition boundary differs")

    right_array = np.frombuffer(payload, dtype="<u2").copy().reshape(1, ELEMENTS)
    left_array = np.asarray(left, dtype=np.uint16).reshape(1, ELEMENTS)
    optimized = bf16_add_rne(left_array, right_array)
    reference = reference_add(
        [left_array[0].astype(int).tolist()],
        [right_array[0].astype(int).tolist()],
    )
    expected = optimized.values.reshape(-1).astype(int).tolist()
    if (
        reference.values != (tuple(expected),)
        or reference.output_saturated_element_count
        != optimized.output_saturated_element_count
    ):
        raise ValueError("independent DMA/ADD composition arithmetic differs")

    expected_payload = _codes_payload(expected)
    body: dict[str, Any] = {
        "add_source_vector_id": ADD_VECTOR_ID,
        "build_id": BUILD_ID,
        "claim_boundary": {
            "authentic_command_records": True,
            "behavioral_hbm_and_sram": True,
            "complete_layer_execution": False,
            "graph_valid_qwen_operation_sequence": False,
            "program_order_and_fail_stop": True,
            "qualified_hbm_phy": False,
            "qualified_sram_macro": False,
            "shared_sram_data_dependency": True,
            "ta_rtl_6_closed": False,
            "timing_or_performance": False,
        },
        "command_program_sha256": PROGRAM_SHA256,
        "commands": [
            {"last": False, **dma_command},
            {"last": True, **add_command},
        ],
        "composition": {
            "add_destination_address": add_fields["destination"],
            "add_element_count": ELEMENTS,
            "add_left_address": add_fields["source0"],
            "add_left_payload_sha256": LEFT_PAYLOAD_SHA256,
            "add_right_address": add_fields["source1"],
            "add_right_payload_sha256": DMA_PAYLOAD_SHA256,
            "dma_destination_address": dma_fields["destination"],
            "dma_payload_sha256": DMA_PAYLOAD_SHA256,
            "expected_output_payload_sha256": _sha256(expected_payload),
            "expected_saturation_count": optimized.output_saturated_element_count,
            "submitted_command_indices": [1, 5131],
        },
        "dma_payload_hex": payload.hex(),
        "dma_source_vector_id": DMA_VECTOR_ID,
        "expected_codes": expected,
        "left_codes": left,
        "schema": SCHEMA,
    }
    return {**body, "vector_set_id": _identity(body, "vector_set_id")}


def main(argv: list[str] | None = None) -> int:
    arguments = parser().parse_args(argv)
    if arguments.output.exists():
        parser().error(f"--output already exists: {arguments.output}")
    vectors = build(
        dma_vectors_path=arguments.dma_vectors,
        add_vectors_path=arguments.add_vectors,
    )
    schema = load_strict_json(
        ROOT
        / "schemas/compiler/tensor_accelerator/"
        "qwen_rtl_dma_add_vectors_v1.schema.json"
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
