#!/usr/bin/env python3
"""Correlate real Qwen production command records in two RTL simulators."""

from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import tempfile
from typing import Any, Sequence

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from compiler.tensor_accelerator.common import (  # noqa: E402
    canonical_json_bytes,
    load_strict_json,
)


SCHEMA = "opentallas.tensor_accelerator.qwen_rtl_command_campaign.v1"
VECTOR_SCHEMA = "opentallas.tensor_accelerator.qwen_rtl_command_vectors.v1"
RTL_PATH = ROOT / "rtl/ot_ta_command_decoder.sv"
CAMPAIGN_SCHEMA_PATH = (
    ROOT
    / "schemas/compiler/tensor_accelerator/qwen_rtl_command_campaign_v1.schema.json"
)
VECTOR_SCHEMA_PATH = (
    ROOT / "schemas/compiler/tensor_accelerator/qwen_rtl_command_vectors_v1.schema.json"
)
VECTOR_BUILDER_PATH = ROOT / "tools/build_qwen3_ta_rtl_command_vectors.py"


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(
        description="Run Icarus and Verilator over Qwen production command vectors"
    )
    result.add_argument("--vectors", required=True, type=Path)
    result.add_argument("--output", required=True, type=Path)
    return result


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _body_id(value: dict[str, Any], field: str) -> str:
    return hashlib.sha256(
        canonical_json_bytes({key: item for key, item in value.items() if key != field})
    ).hexdigest()


def _version(command: Sequence[str]) -> str:
    executable = shutil.which(command[0])
    if executable is None:
        raise RuntimeError(f"required tool is unavailable: {command[0]}")
    result = subprocess.run(
        list(command),
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=30,
        check=False,
    )
    lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    if result.returncode != 0 or not lines:
        raise RuntimeError(f"cannot query tool version: {shlex.join(command)}")
    return lines[0]


def _literal(width: int, value: int) -> str:
    digits = (width + 3) // 4
    return f"{width}'h{value:0{digits}x}"


def _check_call(vector: dict[str, Any]) -> str:
    fields = vector["expected_fields"]
    values = [
        f'"{vector["name"]}"',
        f"512'h{vector['record_hex']}",
        _literal(16, vector["abi_major"]),
        _literal(16, vector["abi_minor"]),
        _literal(32, vector["expected_index"]),
        _literal(4, vector["expected_error"]),
        _literal(8, fields["opcode"]),
        _literal(8, fields["engine"]),
        _literal(16, fields["flags"]),
        _literal(32, fields["index"]),
        _literal(32, fields["kernel_index"]),
        _literal(64, fields["source0"]),
        _literal(64, fields["source1"]),
        _literal(64, fields["destination"]),
        _literal(64, fields["auxiliary"]),
        _literal(32, fields["size0"]),
        _literal(32, fields["size1"]),
        _literal(32, fields["size2"]),
        _literal(32, fields["size3"]),
    ]
    return "        check_vector(" + ", ".join(values) + ");"


def _testbench(vectors: dict[str, Any]) -> str:
    calls = "\n".join(
        _check_call(vector)
        for vector in vectors["vectors"] + vectors["negative_vectors"]
    )
    expected_checks = len(vectors["vectors"]) + len(vectors["negative_vectors"])
    return f"""`timescale 1ns/1ps
module tb_ta_command_decoder;
    reg clk = 1'b0;
    reg rst_n = 1'b0;
    reg in_valid = 1'b0;
    wire in_ready;
    reg [15:0] abi_major = 0;
    reg [15:0] abi_minor = 0;
    reg [31:0] expected_index = 0;
    reg [511:0] command_record = 0;
    wire out_valid;
    reg out_ready = 1'b1;
    wire out_legal;
    wire [3:0] out_error;
    wire [7:0] out_opcode;
    wire [7:0] out_engine;
    wire [15:0] out_flags;
    wire [31:0] out_index;
    wire [31:0] out_kernel_index;
    wire [63:0] out_source0;
    wire [63:0] out_source1;
    wire [63:0] out_destination;
    wire [63:0] out_auxiliary;
    wire [31:0] out_size0;
    wire [31:0] out_size1;
    wire [31:0] out_size2;
    wire [31:0] out_size3;
    integer checks = 0;

    always #5 clk = ~clk;

    ot_ta_command_decoder dut (
        .clk(clk), .rst_n(rst_n), .in_valid(in_valid), .in_ready(in_ready),
        .abi_major(abi_major), .abi_minor(abi_minor),
        .expected_index(expected_index), .command_record(command_record),
        .out_valid(out_valid), .out_ready(out_ready), .out_legal(out_legal),
        .out_error(out_error), .out_opcode(out_opcode), .out_engine(out_engine),
        .out_flags(out_flags), .out_index(out_index),
        .out_kernel_index(out_kernel_index), .out_source0(out_source0),
        .out_source1(out_source1), .out_destination(out_destination),
        .out_auxiliary(out_auxiliary), .out_size0(out_size0),
        .out_size1(out_size1), .out_size2(out_size2), .out_size3(out_size3)
    );

    task automatic check_vector;
        input [8*64-1:0] name;
        input [511:0] record_value;
        input [15:0] major_value;
        input [15:0] minor_value;
        input [31:0] expected_index_value;
        input [3:0] expected_error_value;
        input [7:0] expected_opcode_value;
        input [7:0] expected_engine_value;
        input [15:0] expected_flags_value;
        input [31:0] expected_record_index_value;
        input [31:0] expected_kernel_value;
        input [63:0] expected_source0_value;
        input [63:0] expected_source1_value;
        input [63:0] expected_destination_value;
        input [63:0] expected_auxiliary_value;
        input [31:0] expected_size0_value;
        input [31:0] expected_size1_value;
        input [31:0] expected_size2_value;
        input [31:0] expected_size3_value;
        begin
            @(negedge clk);
            if (!in_ready) $fatal(1, "%0s: decoder was not ready", name);
            command_record = record_value;
            abi_major = major_value;
            abi_minor = minor_value;
            expected_index = expected_index_value;
            in_valid = 1'b1;
            @(negedge clk);
            in_valid = 1'b0;
            if (!out_valid) $fatal(1, "%0s: decoder produced no result", name);
            if (out_error !== expected_error_value)
                $fatal(1, "%0s: error %0d != %0d", name, out_error, expected_error_value);
            if (out_legal !== (expected_error_value == 0))
                $fatal(1, "%0s: legality differs", name);
            if (out_opcode !== expected_opcode_value ||
                out_engine !== expected_engine_value ||
                out_flags !== expected_flags_value ||
                out_index !== expected_record_index_value ||
                out_kernel_index !== expected_kernel_value ||
                out_source0 !== expected_source0_value ||
                out_source1 !== expected_source1_value ||
                out_destination !== expected_destination_value ||
                out_auxiliary !== expected_auxiliary_value ||
                out_size0 !== expected_size0_value ||
                out_size1 !== expected_size1_value ||
                out_size2 !== expected_size2_value ||
                out_size3 !== expected_size3_value)
                $fatal(1, "%0s: decoded fields differ", name);
            checks = checks + 1;
        end
    endtask

    initial begin
        repeat (3) @(negedge clk);
        rst_n = 1'b1;
{calls}
        @(negedge clk);
        if (checks != {expected_checks}) $fatal(1, "check count differs");
        $display("PASS: Qwen production command RTL vectors checks=%0d vector_set={vectors["vector_set_id"]}", checks);
        $finish;
    end
endmodule
"""


def _cpp_u64(value: int) -> str:
    return f"0x{value:016x}ULL"


def _cpp_vector(vector: dict[str, Any]) -> str:
    fields = vector["expected_fields"]
    record = int(vector["record_hex"], 16)
    words = ", ".join(
        f"0x{(record >> (32 * index)) & 0xffff_ffff:08x}U"
        for index in range(16)
    )
    return f"""        {{
            "{vector['name']}",
            {{{words}}},
            {vector['abi_major']}U, {vector['abi_minor']}U,
            0x{vector['expected_index']:08x}U, {vector['expected_error']}U,
            0x{fields['opcode']:02x}U, 0x{fields['engine']:02x}U,
            0x{fields['flags']:04x}U, 0x{fields['index']:08x}U,
            0x{fields['kernel_index']:08x}U,
            {_cpp_u64(fields['source0'])}, {_cpp_u64(fields['source1'])},
            {_cpp_u64(fields['destination'])}, {_cpp_u64(fields['auxiliary'])},
            0x{fields['size0']:08x}U, 0x{fields['size1']:08x}U,
            0x{fields['size2']:08x}U, 0x{fields['size3']:08x}U
        }}"""


def _verilator_harness(vectors: dict[str, Any]) -> str:
    all_vectors = vectors["vectors"] + vectors["negative_vectors"]
    initializers = ",\n".join(_cpp_vector(vector) for vector in all_vectors)
    return f"""#include "Vot_ta_command_decoder.h"
#include "verilated.h"

#include <array>
#include <cstdint>
#include <cstdlib>
#include <iostream>
#include <string>

double sc_time_stamp() {{ return 0.0; }}

namespace {{

struct Vector {{
    const char* name;
    std::array<uint32_t, 16> record;
    uint16_t abi_major;
    uint16_t abi_minor;
    uint32_t expected_index;
    uint8_t error;
    uint8_t opcode;
    uint8_t engine;
    uint16_t flags;
    uint32_t index;
    uint32_t kernel;
    uint64_t source0;
    uint64_t source1;
    uint64_t destination;
    uint64_t auxiliary;
    uint32_t size0;
    uint32_t size1;
    uint32_t size2;
    uint32_t size3;
}};

const std::array<Vector, {len(all_vectors)}> kVectors = {{{{
{initializers}
}}}};

[[noreturn]] void fail(const Vector& vector, const char* field,
                       uint64_t actual, uint64_t expected) {{
    std::cerr << "FAIL: " << vector.name << ": " << field
              << " actual=0x" << std::hex << actual
              << " expected=0x" << expected << "\\n";
    std::exit(1);
}}

void require_equal(const Vector& vector, const char* field,
                   uint64_t actual, uint64_t expected) {{
    if (actual != expected) fail(vector, field, actual, expected);
}}

void rise(Vot_ta_command_decoder& dut) {{
    dut.clk = 1;
    dut.eval();
}}

void fall(Vot_ta_command_decoder& dut) {{
    dut.clk = 0;
    dut.eval();
}}

void reset(Vot_ta_command_decoder& dut) {{
    dut.clk = 0;
    dut.rst_n = 0;
    dut.in_valid = 0;
    dut.out_ready = 1;
    dut.eval();
    for (unsigned cycle = 0; cycle < 3; ++cycle) {{
        rise(dut);
        fall(dut);
    }}
    dut.rst_n = 1;
    dut.eval();
}}

void check(Vot_ta_command_decoder& dut, const Vector& vector) {{
    for (unsigned word = 0; word < vector.record.size(); ++word)
        dut.command_record[word] = vector.record[word];
    dut.abi_major = vector.abi_major;
    dut.abi_minor = vector.abi_minor;
    dut.expected_index = vector.expected_index;
    dut.in_valid = 1;
    dut.eval();
    require_equal(vector, "in_ready", dut.in_ready, 1);

    rise(dut);
    require_equal(vector, "out_valid", dut.out_valid, 1);
    require_equal(vector, "out_legal", dut.out_legal, vector.error == 0);
    require_equal(vector, "out_error", dut.out_error, vector.error);
    require_equal(vector, "out_opcode", dut.out_opcode, vector.opcode);
    require_equal(vector, "out_engine", dut.out_engine, vector.engine);
    require_equal(vector, "out_flags", dut.out_flags, vector.flags);
    require_equal(vector, "out_index", dut.out_index, vector.index);
    require_equal(vector, "out_kernel_index", dut.out_kernel_index, vector.kernel);
    require_equal(vector, "out_source0", dut.out_source0, vector.source0);
    require_equal(vector, "out_source1", dut.out_source1, vector.source1);
    require_equal(vector, "out_destination", dut.out_destination, vector.destination);
    require_equal(vector, "out_auxiliary", dut.out_auxiliary, vector.auxiliary);
    require_equal(vector, "out_size0", dut.out_size0, vector.size0);
    require_equal(vector, "out_size1", dut.out_size1, vector.size1);
    require_equal(vector, "out_size2", dut.out_size2, vector.size2);
    require_equal(vector, "out_size3", dut.out_size3, vector.size3);
    fall(dut);
}}

}}  // namespace

int main(int argc, char** argv) {{
    Verilated::commandArgs(argc, argv);
    Vot_ta_command_decoder dut;
    reset(dut);
    for (const Vector& vector : kVectors) check(dut, vector);
    dut.in_valid = 0;
    rise(dut);
    if (dut.out_valid) {{
        std::cerr << "FAIL: output valid did not clear\\n";
        return 1;
    }}
    fall(dut);
    dut.final();
    std::cout << "PASS: Qwen production command RTL vectors checks={len(all_vectors)} "
              << "vector_set={vectors['vector_set_id']}\\n";
    return 0;
}}
"""


def _run(command: list[str], *, cwd: Path, timeout: int) -> tuple[int, str]:
    environment = {
        key: value for key, value in os.environ.items() if not key.startswith("MAKE")
    }
    result = subprocess.run(
        command,
        cwd=cwd,
        env=environment,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=timeout,
        check=False,
    )
    return result.returncode, result.stdout


def _normalize_evidence(value: str, *, build: Path) -> str:
    """Remove host/worktree-specific paths from retained deterministic evidence."""
    return value.replace(str(build), "<BUILD>").replace(str(ROOT), "<ROOT>")


def _case(
    name: str,
    compile_command: list[str],
    run_command: list[str],
    *,
    build: Path,
    marker: str,
) -> dict[str, Any]:
    compile_code, compile_log = _run(compile_command, cwd=ROOT, timeout=180)
    if compile_code == 0:
        run_code, run_log = _run(run_command, cwd=ROOT, timeout=60)
    else:
        run_code, run_log = None, ""
    retained_compile_log = _normalize_evidence(compile_log, build=build)
    retained_run_log = _normalize_evidence(run_log, build=build)
    log = retained_compile_log + retained_run_log
    log_path = build / f"{name}.log"
    log_path.write_text(log, encoding="utf-8")
    passed = compile_code == 0 and run_code == 0 and marker in log
    return {
        "command": _normalize_evidence(
            shlex.join(compile_command) + " && " + shlex.join(run_command),
            build=build,
        ),
        "compile_log": retained_compile_log,
        "compile_returncode": compile_code,
        "log_sha256": hashlib.sha256(log.encode("utf-8")).hexdigest(),
        "name": name,
        "run_log": retained_run_log,
        "run_returncode": run_code,
        "status": "pass" if passed else "fail",
    }


def run(vectors_path: Path) -> dict[str, Any]:
    vectors = load_strict_json(vectors_path)
    vector_schema = load_strict_json(VECTOR_SCHEMA_PATH)
    Draft202012Validator.check_schema(vector_schema)
    Draft202012Validator(vector_schema).validate(vectors)
    if vectors["schema"] != VECTOR_SCHEMA or vectors["vector_set_id"] != _body_id(
        vectors, "vector_set_id"
    ):
        raise ValueError("Qwen RTL vector identity differs")
    marker = (
        "PASS: Qwen production command RTL vectors "
        f"checks={len(vectors['vectors']) + len(vectors['negative_vectors'])} "
        f"vector_set={vectors['vector_set_id']}"
    )
    with tempfile.TemporaryDirectory(prefix="opentallas-qwen-ta-rtl-") as temporary:
        build = Path(temporary)
        testbench = build / "tb_ta_command_decoder.sv"
        testbench.write_text(_testbench(vectors), encoding="utf-8")
        verilator_harness = build / "ta_command_harness.cpp"
        verilator_harness.write_text(_verilator_harness(vectors), encoding="utf-8")
        iverilog_binary = build / "decoder.vvp"
        verilator_dir = build / "verilator"
        cases = [
            _case(
                "iverilog",
                [
                    "iverilog",
                    "-g2012",
                    "-Wall",
                    "-s",
                    "tb_ta_command_decoder",
                    "-o",
                    str(iverilog_binary),
                    str(RTL_PATH),
                    str(testbench),
                ],
                ["vvp", str(iverilog_binary)],
                build=build,
                marker=marker,
            ),
            _case(
                "verilator",
                [
                    "verilator",
                    "--cc",
                    "--exe",
                    "--build",
                    "-Wall",
                    "-Wno-fatal",
                    "--top-module",
                    "ot_ta_command_decoder",
                    "--Mdir",
                    str(verilator_dir),
                    str(RTL_PATH),
                    str(verilator_harness),
                    "-CFLAGS",
                    "-std=c++17",
                ],
                [str(verilator_dir / "Vot_ta_command_decoder")],
                build=build,
                marker=marker,
            ),
        ]
        generated_source_sha256 = {
            "generated/ta_command_harness.cpp": _sha256_file(verilator_harness),
            "generated/tb_ta_command_decoder.sv": _sha256_file(testbench),
        }
    passed = all(case["status"] == "pass" for case in cases)
    body = {
        "build_id": vectors["build_id"],
        "cases": cases,
        "claim_boundary": {
            "complete_kernel_execution": False,
            "complete_layer_execution": False,
            "production_command_record_admission": True,
            "ta_rtl_6_closed": False,
            "timing_or_performance": False,
        },
        "command_program_sha256": vectors["command_program_sha256"],
        "execution_report_id": vectors["execution_report_id"],
        "negative_vector_count": len(vectors["negative_vectors"]),
        "positive_vector_count": len(vectors["vectors"]),
        "schema": SCHEMA,
        "simulators": ["iverilog", "verilator"],
        "source_sha256": {
            str(RTL_PATH.relative_to(ROOT)): _sha256_file(RTL_PATH),
            str(CAMPAIGN_SCHEMA_PATH.relative_to(ROOT)): _sha256_file(
                CAMPAIGN_SCHEMA_PATH
            ),
            str(VECTOR_SCHEMA_PATH.relative_to(ROOT)): _sha256_file(VECTOR_SCHEMA_PATH),
            str(VECTOR_BUILDER_PATH.relative_to(ROOT)): _sha256_file(VECTOR_BUILDER_PATH),
            str(Path(__file__).resolve().relative_to(ROOT)): _sha256_file(
                Path(__file__).resolve()
            ),
            str(vectors_path.resolve().relative_to(ROOT)): _sha256_file(vectors_path),
            **generated_source_sha256,
        },
        "status": "pass" if passed else "fail",
        "tools": {
            "iverilog": _version(["iverilog", "-V"]),
            "verilator": _version(["verilator", "--version"]),
        },
        "vector_set_id": vectors["vector_set_id"],
    }
    return {
        **body,
        "campaign_id": hashlib.sha256(canonical_json_bytes(body)).hexdigest(),
    }


def main(argv: list[str] | None = None) -> int:
    arguments = parser().parse_args(argv)
    if arguments.output.exists():
        parser().error(f"--output already exists: {arguments.output}")
    report = run(arguments.vectors)
    schema = load_strict_json(CAMPAIGN_SCHEMA_PATH)
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(report)
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    with arguments.output.open("xb") as handle:
        handle.write(canonical_json_bytes(report))
        handle.flush()
        os.fsync(handle.fileno())
    print(report["campaign_id"])
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
