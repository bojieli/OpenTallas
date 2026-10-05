#!/usr/bin/env python3
"""Bind representative RTL command vectors to the complete Qwen program."""

from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path
import struct
import sys
from typing import Any
import zlib

from jsonschema import Draft202012Validator

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
    COMMAND_PREFIX,
    COMMAND_WITH_CRC,
    Opcode,
    ProductionCommand,
    command_abi,
    decode,
)


SCHEMA = "opentallas.tensor_accelerator.qwen_rtl_command_vectors.v1"
PROGRAM_SHA256 = "f0ce6b50b01f462f837a28504e6ff9a024a24d24abf339f924875d0c2059bcec"
BUILD_ID = "3460d88ce16f5ef0ca4d1277daf8ebb19ae555e88822f95d55deb4aa8cad290f"
EXECUTION_REPORT_ID = "77b849e49608cacf9522eb16fad289385523c39618425e1e1c5f30126e504746"
COMMAND_COUNT = 924_386
EXPECTED_OPCODES = tuple(Opcode)


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(
        description="Extract content-bound RTL vectors from the full Qwen command program"
    )
    result.add_argument("--program", required=True, type=Path)
    result.add_argument("--manifest", required=True, type=Path)
    result.add_argument("--execution-report", required=True, type=Path)
    result.add_argument("--output", required=True, type=Path)
    return result


def _body_id(value: dict[str, Any], field: str) -> str:
    return hashlib.sha256(
        canonical_json_bytes({key: item for key, item in value.items() if key != field})
    ).hexdigest()


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


def _record_hex(raw: bytes) -> str:
    if len(raw) != COMMAND_WITH_CRC.size:
        raise ValueError("command record width differs")
    return f"{int.from_bytes(raw, 'little'):0128x}"


def _vector(
    name: str,
    raw: bytes,
    *,
    expected_index: int,
    expected_error: int = 0,
    abi_major: int = ABI_MAJOR,
    abi_minor: int = ABI_MINOR,
) -> dict[str, Any]:
    return {
        "abi_major": abi_major,
        "abi_minor": abi_minor,
        "expected_error": expected_error,
        "expected_fields": _fields(raw),
        "expected_index": expected_index,
        "name": name,
        "record_hex": _record_hex(raw),
    }


def _raw_record(payload: bytes, command: ProductionCommand) -> bytes:
    offset = 32 + command.index * COMMAND_WITH_CRC.size
    return payload[offset : offset + COMMAND_WITH_CRC.size]


def _recrc(raw: bytearray) -> bytes:
    if len(raw) != COMMAND_WITH_CRC.size:
        raise ValueError("command record width differs")
    struct.pack_into("<I", raw, COMMAND_PREFIX.size, zlib.crc32(raw[:-4]) & 0xFFFFFFFF)
    return bytes(raw)


def _validate_sources(
    payload: bytes,
    manifest: dict[str, Any],
    execution: dict[str, Any],
) -> None:
    if (
        hashlib.sha256(payload).hexdigest() != PROGRAM_SHA256
        or command_abi(payload) != (ABI_MAJOR, ABI_MINOR)
        or manifest.get("build_id") != BUILD_ID
        or execution.get("build_id") != BUILD_ID
        or execution.get("report_id") != EXECUTION_REPORT_ID
        or execution.get("command_program_sha256") != PROGRAM_SHA256
        or execution.get("command_count") != COMMAND_COUNT
        or execution.get("status") != "pass"
    ):
        raise ValueError("full Qwen command evidence differs from the frozen release")
    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, list):
        raise ValueError("deployment manifest artifact table differs")
    records = [item for item in artifacts if item.get("path") == "program/commands.bin"]
    if len(records) != 1 or records[0].get("sha256") != PROGRAM_SHA256:
        raise ValueError("deployment manifest command binding differs")


def build(
    program: Path,
    manifest_path: Path,
    execution_path: Path,
) -> dict[str, Any]:
    payload = program.read_bytes()
    manifest = load_strict_json(manifest_path)
    execution = load_strict_json(execution_path)
    _validate_sources(payload, manifest, execution)
    commands = decode(payload)
    if len(commands) != COMMAND_COUNT:
        raise ValueError("decoded command count differs")
    selected: dict[Opcode, ProductionCommand] = {}
    for command in commands:
        selected.setdefault(command.opcode, command)
    if set(selected) != set(EXPECTED_OPCODES):
        raise ValueError("full Qwen command opcode coverage differs")

    vectors = [
        _vector(
            command.opcode.name.lower(),
            _raw_record(payload, command),
            expected_index=command.index,
        )
        for command in (selected[opcode] for opcode in EXPECTED_OPCODES)
    ]

    direct = selected[Opcode.DMA_HBM_TO_SRAM]
    direct_raw = _raw_record(payload, direct)
    corrupted_crc = bytearray(direct_raw)
    corrupted_crc[12] ^= 1

    unknown_opcode = bytearray(direct_raw)
    unknown_opcode[0] = 0x7E
    wrong_engine = bytearray(direct_raw)
    wrong_engine[1] = 2

    add = selected[Opcode.ADD_BF16]
    illegal_add = bytearray(_raw_record(payload, add))
    struct.pack_into("<I", illegal_add, 44, 0)

    indexed_sram = selected[Opcode.DMA_SRAM_INDEXED_TO_SRAM]
    indexed_sram_raw = _raw_record(payload, indexed_sram)
    negative = [
        _vector(
            "bad_crc",
            bytes(corrupted_crc),
            expected_index=direct.index,
            expected_error=1,
        ),
        _vector(
            "unknown_opcode",
            _recrc(unknown_opcode),
            expected_index=direct.index,
            expected_error=2,
        ),
        _vector(
            "wrong_engine",
            _recrc(wrong_engine),
            expected_index=direct.index,
            expected_error=3,
        ),
        _vector(
            "unsupported_abi_major",
            direct_raw,
            expected_index=direct.index,
            expected_error=4,
            abi_major=3,
        ),
        _vector(
            "opcode_requires_newer_minor",
            indexed_sram_raw,
            expected_index=indexed_sram.index,
            expected_error=4,
            abi_minor=4,
        ),
        _vector(
            "illegal_fields",
            _recrc(illegal_add),
            expected_index=add.index,
            expected_error=5,
        ),
        _vector(
            "noncontiguous_index",
            direct_raw,
            expected_index=direct.index + 1,
            expected_error=6,
        ),
    ]
    body = {
        "abi_major": ABI_MAJOR,
        "abi_minor": ABI_MINOR,
        "build_id": BUILD_ID,
        "command_count": COMMAND_COUNT,
        "command_program_sha256": PROGRAM_SHA256,
        "execution_report_id": EXECUTION_REPORT_ID,
        "negative_vectors": negative,
        "schema": SCHEMA,
        "vectors": vectors,
    }
    return {
        **body,
        "vector_set_id": hashlib.sha256(canonical_json_bytes(body)).hexdigest(),
    }


def main(argv: list[str] | None = None) -> int:
    arguments = parser().parse_args(argv)
    if arguments.output.exists():
        parser().error(f"--output already exists: {arguments.output}")
    value = build(arguments.program, arguments.manifest, arguments.execution_report)
    schema = load_strict_json(
        ROOT
        / "schemas/compiler/tensor_accelerator/qwen_rtl_command_vectors_v1.schema.json"
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
