from __future__ import annotations

import hashlib
from pathlib import Path
import shutil
import zlib

from jsonschema import Draft202012Validator
import pytest

from compiler.tensor_accelerator.common import canonical_json_bytes, load_strict_json
from compiler.tensor_accelerator import production_command
from compiler.tensor_accelerator.production_command import (
    ABI_MAJOR,
    ABI_MINOR,
    COMMAND_WITH_CRC,
    EXPECTED_ENGINE,
    OPCODE_MIN_MINOR,
    Engine,
    Opcode,
    ProductionCommand,
    ProductionCommandError,
)
from tools import run_qwen3_ta_rtl_command_campaign as campaign_runner


ROOT = Path(__file__).resolve().parents[2]
VECTORS_PATH = (
    ROOT / "testdata/compiler/tensor_accelerator/qwen3_rtl_command_vectors.json"
)
CAMPAIGN_PATH = (
    ROOT / "results/tensor_accelerator/qwen3_rtl_command_campaign.json"
)
VECTOR_SCHEMA_PATH = (
    ROOT
    / "schemas/compiler/tensor_accelerator/qwen_rtl_command_vectors_v1.schema.json"
)
CAMPAIGN_SCHEMA_PATH = (
    ROOT
    / "schemas/compiler/tensor_accelerator/qwen_rtl_command_campaign_v1.schema.json"
)
EXPECTED_VECTOR_SET_ID = (
    "420ada71f902c8e43b9e5866d9c57ab8e3a1ced59e25c01b20793c94cf45b1a2"
)
EXPECTED_CAMPAIGN_ID = (
    "a058f6ce18a22a8d43625a4013f892e74464135d03406512b24fa190309277a5"
)
FIELD_NAMES = (
    "opcode",
    "engine",
    "flags",
    "index",
    "kernel_index",
    "source0",
    "source1",
    "destination",
    "auxiliary",
    "size0",
    "size1",
    "size2",
    "size3",
)


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_file(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _body_id(value: dict[str, object], identity: str) -> str:
    body = {key: item for key, item in value.items() if key != identity}
    return _sha256_bytes(canonical_json_bytes(body))


def _raw(vector: dict[str, object]) -> bytes:
    return int(str(vector["record_hex"]), 16).to_bytes(
        COMMAND_WITH_CRC.size, "little"
    )


def _fields(vector: dict[str, object]) -> dict[str, int]:
    values = COMMAND_WITH_CRC.unpack(_raw(vector))
    return dict(zip(FIELD_NAMES, values[:-1], strict=True))


def _reference_error(vector: dict[str, object]) -> int:
    """Apply the RTL admission checks in their specified priority order."""
    raw = _raw(vector)
    values = COMMAND_WITH_CRC.unpack(raw)
    fields = _fields(vector)
    if zlib.crc32(raw[:-4]) & 0xFFFFFFFF != values[-1]:
        return 1
    try:
        opcode = Opcode(fields["opcode"])
    except ValueError:
        return 2
    try:
        engine = Engine(fields["engine"])
    except ValueError:
        return 3
    if engine != EXPECTED_ENGINE[opcode]:
        return 3
    abi_major = int(vector["abi_major"])
    abi_minor = int(vector["abi_minor"])
    if (
        abi_major != ABI_MAJOR
        or abi_minor > ABI_MINOR
        or abi_minor < OPCODE_MIN_MINOR[opcode]
    ):
        return 4
    command = ProductionCommand(
        index=fields["index"],
        opcode=opcode,
        engine=engine,
        flags=fields["flags"],
        kernel_index=fields["kernel_index"],
        source0=fields["source0"],
        source1=fields["source1"],
        destination=fields["destination"],
        auxiliary=fields["auxiliary"],
        size0=fields["size0"],
        size1=fields["size1"],
        size2=fields["size2"],
        size3=fields["size3"],
    )
    try:
        production_command._validate_command(  # type: ignore[attr-defined]
            command, command.index, abi_minor=abi_minor
        )
    except ProductionCommandError:
        return 5
    if command.index != int(vector["expected_index"]):
        return 6
    return 0


def test_retained_vectors_are_schema_valid_content_addressed_and_complete() -> None:
    vectors = load_strict_json(VECTORS_PATH)
    schema = load_strict_json(VECTOR_SCHEMA_PATH)
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(vectors)

    assert VECTORS_PATH.read_bytes() == canonical_json_bytes(vectors)
    assert vectors["vector_set_id"] == EXPECTED_VECTOR_SET_ID
    assert vectors["vector_set_id"] == _body_id(vectors, "vector_set_id")
    assert vectors["abi_major"] == ABI_MAJOR
    assert vectors["abi_minor"] == ABI_MINOR
    assert vectors["command_count"] == 924_386
    assert vectors["command_program_sha256"] == campaign_runner.load_strict_json(
        CAMPAIGN_PATH
    )["command_program_sha256"]

    positive = vectors["vectors"]
    assert {item["expected_fields"]["opcode"] for item in positive} == {
        int(opcode) for opcode in Opcode
    }
    assert {item["name"] for item in positive} == {
        opcode.name.lower() for opcode in Opcode
    }
    for vector in positive:
        raw = _raw(vector)
        fields = _fields(vector)
        assert fields == vector["expected_fields"]
        assert zlib.crc32(raw[:-4]) & 0xFFFFFFFF == COMMAND_WITH_CRC.unpack(raw)[-1]
        opcode = Opcode(fields["opcode"])
        assert fields["engine"] == int(EXPECTED_ENGINE[opcode])
        assert vector["abi_minor"] >= OPCODE_MIN_MINOR[opcode]
        assert vector["expected_index"] == fields["index"]
        assert vector["expected_error"] == _reference_error(vector) == 0


def test_negative_vectors_lock_error_precedence() -> None:
    vectors = load_strict_json(VECTORS_PATH)
    negative = vectors["negative_vectors"]
    expected = {
        "bad_crc": 1,
        "unknown_opcode": 2,
        "wrong_engine": 3,
        "unsupported_abi_major": 4,
        "opcode_requires_newer_minor": 4,
        "illegal_fields": 5,
        "noncontiguous_index": 6,
    }
    assert [item["name"] for item in negative] == list(expected)
    assert {item["name"]: item["expected_error"] for item in negative} == expected
    for vector in negative:
        assert _fields(vector) == vector["expected_fields"]
        assert vector["expected_error"] == _reference_error(vector)

    unknown = next(item for item in negative if item["name"] == "unknown_opcode")
    assert unknown["expected_fields"]["opcode"] not in {int(item) for item in Opcode}
    assert unknown["expected_fields"]["engine"] != int(Engine.CONTROL)
    illegal = next(item for item in negative if item["name"] == "illegal_fields")
    assert illegal["expected_fields"]["size0"] == 0
    noncontiguous = next(
        item for item in negative if item["name"] == "noncontiguous_index"
    )
    assert noncontiguous["expected_fields"]["index"] != noncontiguous[
        "expected_index"
    ]


def test_retained_campaign_is_schema_valid_and_source_bound() -> None:
    vectors = load_strict_json(VECTORS_PATH)
    campaign = load_strict_json(CAMPAIGN_PATH)
    schema = load_strict_json(CAMPAIGN_SCHEMA_PATH)
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(campaign)

    assert CAMPAIGN_PATH.read_bytes() == canonical_json_bytes(campaign)
    assert campaign["campaign_id"] == EXPECTED_CAMPAIGN_ID
    assert campaign["campaign_id"] == _body_id(campaign, "campaign_id")
    assert campaign["vector_set_id"] == EXPECTED_VECTOR_SET_ID
    assert campaign["status"] == "pass"
    assert campaign["decoder_crc_bytes_per_cycle"] == 4
    assert campaign["decoder_crc_latency_cycles"] == 15
    assert campaign["claim_boundary"] == {
        "complete_kernel_execution": False,
        "complete_layer_execution": False,
        "production_command_record_admission": True,
        "ta_rtl_6_closed": False,
        "timing_or_performance": False,
    }

    marker = (
        "PASS: Qwen production command RTL vectors checks=19 "
        f"vector_set={EXPECTED_VECTOR_SET_ID}"
    )
    assert [case["name"] for case in campaign["cases"]] == [
        "iverilog",
        "verilator",
    ]
    for case in campaign["cases"]:
        retained_log = case["compile_log"] + case["run_log"]
        assert case["status"] == "pass"
        assert case["compile_returncode"] == 0
        assert case["run_returncode"] == 0
        assert case["log_sha256"] == _sha256_bytes(retained_log.encode("utf-8"))
        assert marker in case["run_log"]
        assert "/tmp/" not in case["command"]
        assert str(ROOT) not in case["command"]

    static_sources = {
        "rtl/ot_ta_command_decoder.sv": ROOT / "rtl/ot_ta_command_decoder.sv",
        "schemas/compiler/tensor_accelerator/qwen_rtl_command_campaign_v1.schema.json": CAMPAIGN_SCHEMA_PATH,
        "schemas/compiler/tensor_accelerator/qwen_rtl_command_vectors_v1.schema.json": VECTOR_SCHEMA_PATH,
        "testdata/compiler/tensor_accelerator/qwen3_rtl_command_vectors.json": VECTORS_PATH,
        "tools/build_qwen3_ta_rtl_command_vectors.py": ROOT
        / "tools/build_qwen3_ta_rtl_command_vectors.py",
        "tools/run_qwen3_ta_rtl_command_campaign.py": ROOT
        / "tools/run_qwen3_ta_rtl_command_campaign.py",
    }
    expected_sources = {
        name: _sha256_file(path) for name, path in static_sources.items()
    }
    expected_sources.update(
        {
            "generated/ta_command_harness.cpp": _sha256_bytes(
                campaign_runner._verilator_harness(vectors).encode("utf-8")
            ),
            "generated/tb_ta_command_decoder.sv": _sha256_bytes(
                campaign_runner._testbench(vectors).encode("utf-8")
            ),
        }
    )
    assert campaign["source_sha256"] == expected_sources


@pytest.mark.skipif(
    any(shutil.which(tool) is None for tool in ("iverilog", "vvp", "verilator")),
    reason="Icarus and Verilator are required for the correlation replay",
)
def test_retained_two_simulator_campaign_replays_exactly() -> None:
    retained = load_strict_json(CAMPAIGN_PATH)
    replayed = campaign_runner.run(VECTORS_PATH)
    assert canonical_json_bytes(replayed) == canonical_json_bytes(retained)
