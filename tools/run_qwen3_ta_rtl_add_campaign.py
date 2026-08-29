#!/usr/bin/env python3
"""Correlate one complete authentic Qwen ADD_BF16 command in two simulators."""

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
from typing import Any

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from compiler.tensor_accelerator.common import (  # noqa: E402
    canonical_json_bytes,
    load_strict_json,
)


SCHEMA = "opentallas.tensor_accelerator.qwen_rtl_add_campaign.v1"
VECTOR_SCHEMA = "opentallas.tensor_accelerator.qwen_rtl_add_vectors.v1"
RTL_PATHS = (
    ROOT / "rtl/ot_ta_command_decoder.sv",
    ROOT / "rtl/ot_bf16_add_rne.sv",
    ROOT / "rtl/ot_ta_add_bf16_executor.sv",
)
CAMPAIGN_SCHEMA_PATH = (
    ROOT / "schemas/compiler/tensor_accelerator/qwen_rtl_add_campaign_v1.schema.json"
)
VECTOR_SCHEMA_PATH = (
    ROOT / "schemas/compiler/tensor_accelerator/qwen_rtl_add_vectors_v1.schema.json"
)
VECTOR_BUILDER_PATH = ROOT / "tools/build_qwen3_ta_rtl_add_vectors.py"


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(
        description="Run Icarus and Verilator over a complete authentic Qwen ADD"
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
    body = {key: item for key, item in value.items() if key != field}
    return hashlib.sha256(canonical_json_bytes(body)).hexdigest()


def _version(command: list[str]) -> str:
    executable = shutil.which(command[0])
    if executable is None:
        raise RuntimeError(f"required tool is unavailable: {command[0]}")
    result = subprocess.run(
        command,
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


def _wrapper() -> str:
    return """`timescale 1ns/1ps
module ot_ta_add_campaign_top (
    input wire clk, input wire rst_n,
    input wire cmd_valid, output wire cmd_ready,
    input wire [15:0] abi_major, input wire [15:0] abi_minor,
    input wire [31:0] expected_command_index,
    input wire [511:0] command_record,
    input wire operand_valid, output wire operand_ready,
    input wire [15:0] operand_left, input wire [15:0] operand_right,
    output wire [31:0] operand_index,
    output wire [63:0] operand_source0_address,
    output wire [63:0] operand_source1_address,
    output wire result_valid, input wire result_ready,
    output wire [15:0] result_code, output wire result_saturated,
    output wire [1:0] result_error, output wire [31:0] result_index,
    output wire [63:0] result_destination_address,
    output wire done_valid, input wire done_ready,
    output wire [7:0] done_error,
    output wire [31:0] done_command_index,
    output wire [31:0] done_element_count,
    output wire [31:0] done_saturation_count,
    input wire [15:0] direct_left, input wire [15:0] direct_right,
    output wire [15:0] direct_result,
    output wire direct_saturated, output wire [1:0] direct_error
);
    ot_ta_add_bf16_executor executor (
        .clk(clk), .rst_n(rst_n), .cmd_valid(cmd_valid), .cmd_ready(cmd_ready),
        .abi_major(abi_major), .abi_minor(abi_minor),
        .expected_command_index(expected_command_index),
        .command_record(command_record), .operand_valid(operand_valid),
        .operand_ready(operand_ready), .operand_left(operand_left),
        .operand_right(operand_right), .operand_index(operand_index),
        .operand_source0_address(operand_source0_address),
        .operand_source1_address(operand_source1_address),
        .result_valid(result_valid), .result_ready(result_ready),
        .result_code(result_code), .result_saturated(result_saturated),
        .result_error(result_error), .result_index(result_index),
        .result_destination_address(result_destination_address),
        .done_valid(done_valid), .done_ready(done_ready),
        .done_error(done_error), .done_command_index(done_command_index),
        .done_element_count(done_element_count),
        .done_saturation_count(done_saturation_count)
    );
    ot_bf16_add_rne direct (
        .left_code(direct_left), .right_code(direct_right),
        .result_code(direct_result), .result_saturated(direct_saturated),
        .result_error(direct_error)
    );
endmodule
"""


def _directed_sv(vectors: dict[str, Any]) -> str:
    return "\n".join(
        "        check_directed(\"{name}\", 16'h{left:04x}, 16'h{right:04x}, "
        "16'h{expected:04x}, 2'd{expected_error}, 1'b{saturated});".format(
            **{**vector, "saturated": int(vector["saturated"])}
        )
        for vector in vectors["directed_vectors"]
    )


def _testbench(vectors: dict[str, Any]) -> str:
    command = vectors["command"]
    fields = command["expected_fields"]
    count = vectors["operand_count"]
    return f"""`timescale 1ns/1ps
module tb_qwen_ta_add;
    reg clk = 0;
    reg rst_n = 0;
    reg cmd_valid = 0;
    wire cmd_ready;
    reg [15:0] abi_major = 0;
    reg [15:0] abi_minor = 0;
    reg [31:0] expected_command_index = 0;
    reg [511:0] command_record = 0;
    reg operand_valid = 0;
    wire operand_ready;
    reg [15:0] operand_left = 0;
    reg [15:0] operand_right = 0;
    wire [31:0] operand_index;
    wire [63:0] operand_source0_address;
    wire [63:0] operand_source1_address;
    wire result_valid;
    reg result_ready = 0;
    wire [15:0] result_code;
    wire result_saturated;
    wire [1:0] result_error;
    wire [31:0] result_index;
    wire [63:0] result_destination_address;
    wire done_valid;
    reg done_ready = 0;
    wire [7:0] done_error;
    wire [31:0] done_command_index;
    wire [31:0] done_element_count;
    wire [31:0] done_saturation_count;
    reg [15:0] direct_left = 0;
    reg [15:0] direct_right = 0;
    wire [15:0] direct_result;
    wire direct_saturated;
    wire [1:0] direct_error;
    reg [15:0] left_mem [0:{count - 1}];
    reg [15:0] right_mem [0:{count - 1}];
    reg [15:0] expected_mem [0:{count - 1}];
    integer sent = 0;
    integer received = 0;
    integer cycles = 0;
    integer directed_checks = 0;
    integer exhaustive_checks = 0;
    integer code = 0;

    always #5 clk = ~clk;

    ot_ta_add_campaign_top dut (
        .clk(clk), .rst_n(rst_n), .cmd_valid(cmd_valid), .cmd_ready(cmd_ready),
        .abi_major(abi_major), .abi_minor(abi_minor),
        .expected_command_index(expected_command_index),
        .command_record(command_record), .operand_valid(operand_valid),
        .operand_ready(operand_ready), .operand_left(operand_left),
        .operand_right(operand_right), .operand_index(operand_index),
        .operand_source0_address(operand_source0_address),
        .operand_source1_address(operand_source1_address),
        .result_valid(result_valid), .result_ready(result_ready),
        .result_code(result_code), .result_saturated(result_saturated),
        .result_error(result_error), .result_index(result_index),
        .result_destination_address(result_destination_address),
        .done_valid(done_valid), .done_ready(done_ready),
        .done_error(done_error), .done_command_index(done_command_index),
        .done_element_count(done_element_count),
        .done_saturation_count(done_saturation_count),
        .direct_left(direct_left), .direct_right(direct_right),
        .direct_result(direct_result), .direct_saturated(direct_saturated),
        .direct_error(direct_error)
    );

    task automatic check_directed;
        input [8*64-1:0] name;
        input [15:0] left_value;
        input [15:0] right_value;
        input [15:0] expected_value;
        input [1:0] error_value;
        input saturated_value;
        begin
            direct_left = left_value;
            direct_right = right_value;
            #1;
            if (direct_result !== expected_value || direct_error !== error_value ||
                direct_saturated !== saturated_value)
                $fatal(1, "%0s: directed result differs", name);
            direct_left = right_value;
            direct_right = left_value;
            #1;
            if (direct_result !== expected_value || direct_error !== error_value ||
                direct_saturated !== saturated_value)
                $fatal(1, "%0s: commuted directed result differs", name);
            directed_checks = directed_checks + 1;
        end
    endtask

    task automatic run_executor_fault;
        input [15:0] left_value;
        input [15:0] right_value;
        input [1:0] expected_result_error;
        input [7:0] expected_done_error;
        begin
            result_ready = 0;
            done_ready = 0;
            while (!cmd_ready) @(negedge clk);
            cmd_valid = 1;
            @(negedge clk);
            cmd_valid = 0;
            while (!operand_ready) @(negedge clk);
            operand_left = left_value;
            operand_right = right_value;
            operand_valid = 1;
            @(negedge clk);
            operand_valid = 0;
            while (!result_valid) @(negedge clk);
            if (result_index !== 0 || result_error !== expected_result_error ||
                result_code !== 0 || result_saturated !== 0)
                $fatal(1, "executor fault result differs");
            result_ready = 1;
            @(negedge clk);
            while (!done_valid) @(negedge clk);
            if (done_error !== expected_done_error || done_element_count !== 1 ||
                done_saturation_count !== 0)
                $fatal(1, "executor fault completion differs");
            done_ready = 1;
            @(negedge clk);
            done_ready = 0;
        end
    endtask

    initial begin
        $readmemh("left.hex", left_mem);
        $readmemh("right.hex", right_mem);
        $readmemh("expected.hex", expected_mem);
{_directed_sv(vectors)}
        for (code = 0; code < 65536; code = code + 1) begin
            if ((code & 16'h7f80) != 16'h7f80) begin
                direct_left = code[15:0];
                direct_right = 16'h0000;
                #1;
                if (direct_result !== ((code & 16'h7fff) == 0 ? 16'h0000 : code[15:0]) ||
                    direct_error !== 0 || direct_saturated !== 0)
                    $fatal(1, "zero identity differs at %0h", code);
                exhaustive_checks = exhaustive_checks + 1;
                direct_right = code[15:0] ^ 16'h8000;
                #1;
                if (direct_result !== 0 || direct_error !== 0 ||
                    direct_saturated !== 0)
                    $fatal(1, "cancellation differs at %0h", code);
                exhaustive_checks = exhaustive_checks + 1;
            end
        end
        repeat (3) @(negedge clk);
        rst_n = 1;
        @(negedge clk);
        if (!cmd_ready) $fatal(1, "command interface was not ready");
        abi_major = 16'd{command['abi_major']};
        abi_minor = 16'd{command['abi_minor']};
        expected_command_index = 32'd{command['expected_index']};
        command_record = 512'h{command['record_hex']};
        cmd_valid = 1;
        @(negedge clk);
        cmd_valid = 0;
        while (!operand_ready) @(negedge clk);

        while (received < {count}) begin
            result_ready = (cycles % 7) != 2;
            #1;
            if (result_valid) begin
                if (result_index !== received ||
                    result_destination_address !== 64'd{fields['destination']} + received*2 ||
                    result_code !== expected_mem[received] || result_error !== 0 ||
                    result_saturated !== 0)
                    $fatal(1, "result differs at %0d", received);
                if (result_ready)
                    received = received + 1;
            end
            operand_valid = 0;
            if (sent < {count} && (cycles % 5) != 1 && operand_ready) begin
                if (operand_index !== sent ||
                    operand_source0_address !== 64'd{fields['source0']} + sent*2 ||
                    operand_source1_address !== 64'd{fields['source1']} + sent*2)
                    $fatal(1, "operand address differs at %0d", sent);
                operand_left = left_mem[sent];
                operand_right = right_mem[sent];
                operand_valid = 1;
                sent = sent + 1;
            end
            @(negedge clk);
            cycles = cycles + 1;
            if (cycles > {count * 20}) $fatal(1, "ADD campaign timed out");
        end
        operand_valid = 0;
        result_ready = 1;
        while (!done_valid) @(negedge clk);
        if (done_error !== 0 || done_command_index !== 32'd{command['expected_index']} ||
            done_element_count !== {count} || done_saturation_count !== 0 ||
            sent != {count} || directed_checks != {len(vectors['directed_vectors'])} ||
            exhaustive_checks != 130560)
            $fatal(1, "completion record differs");
        $display("PASS: Qwen ADD_BF16 RTL command elements={count} directed={len(vectors['directed_vectors'])} exhaustive=130560 vector_set={vectors['vector_set_id']}");
        done_ready = 1;
        @(negedge clk);
        done_ready = 0;
        run_executor_fault(16'h7f80, 16'h3f80, 2'd1, 8'd9);
        run_executor_fault(16'h7f7f, 16'h7f7f, 2'd2, 8'd10);
        $display("PASS: Qwen ADD_BF16 RTL executor faults=2");
        $finish;
    end
endmodule
"""


def _directed_cpp(vectors: dict[str, Any]) -> str:
    return ",\n".join(
        '        {{"{name}", 0x{left:04x}U, 0x{right:04x}U, '
        "0x{expected:04x}U, {expected_error}U, {saturated}}}".format(
            **{
                **vector,
                "saturated": "true" if vector["saturated"] else "false",
            }
        )
        for vector in vectors["directed_vectors"]
    )


def _harness(vectors: dict[str, Any]) -> str:
    command = vectors["command"]
    fields = command["expected_fields"]
    record = int(command["record_hex"], 16)
    words = ", ".join(
        f"0x{(record >> (index * 32)) & 0xffffffff:08x}U" for index in range(16)
    )
    return f"""#include "Vot_ta_add_campaign_top.h"
#include "verilated.h"

#include <array>
#include <cstdint>
#include <cstdlib>
#include <fstream>
#include <iostream>
#include <string>
#include <vector>

double sc_time_stamp() {{ return 0.0; }}

namespace {{
constexpr uint32_t kCount = {vectors['operand_count']}U;
constexpr uint64_t kSource0 = {fields['source0']}ULL;
constexpr uint64_t kSource1 = {fields['source1']}ULL;
constexpr uint64_t kDestination = {fields['destination']}ULL;
constexpr std::array<uint32_t, 16> kCommand = {{{{{words}}}}};

struct Directed {{
    const char* name;
    uint16_t left;
    uint16_t right;
    uint16_t expected;
    uint8_t error;
    bool saturated;
}};

const std::array<Directed, {len(vectors['directed_vectors'])}> kDirected = {{{{
{_directed_cpp(vectors)}
}}}};

[[noreturn]] void fail(const std::string& message) {{
    std::cerr << "FAIL: " << message << "\\n";
    std::exit(1);
}}

void require(bool condition, const std::string& message) {{
    if (!condition) fail(message);
}}

std::vector<uint16_t> load_hex(const char* path) {{
    std::ifstream stream(path);
    if (!stream) fail(std::string("cannot open ") + path);
    std::vector<uint16_t> result;
    uint32_t value = 0;
    while (stream >> std::hex >> value) {{
        if (value > 0xffffU) fail(std::string("wide value in ") + path);
        result.push_back(static_cast<uint16_t>(value));
    }}
    if (result.size() != kCount) fail(std::string("count differs in ") + path);
    return result;
}}

void eval_low(Vot_ta_add_campaign_top& dut) {{
    dut.clk = 0;
    dut.eval();
}}

void tick(Vot_ta_add_campaign_top& dut) {{
    dut.clk = 1;
    dut.eval();
    dut.clk = 0;
    dut.eval();
}}

void reset(Vot_ta_add_campaign_top& dut) {{
    dut.rst_n = 0;
    dut.cmd_valid = 0;
    dut.operand_valid = 0;
    dut.result_ready = 0;
    dut.done_ready = 0;
    for (unsigned cycle = 0; cycle < 3; ++cycle) tick(dut);
    dut.rst_n = 1;
    eval_low(dut);
}}

}}  // namespace

int main(int argc, char** argv) {{
    Verilated::commandArgs(argc, argv);
    Vot_ta_add_campaign_top dut;
    const auto left = load_hex("left.hex");
    const auto right = load_hex("right.hex");
    const auto expected = load_hex("expected.hex");

    for (const Directed& vector : kDirected) {{
        dut.direct_left = vector.left;
        dut.direct_right = vector.right;
        eval_low(dut);
        require(dut.direct_result == vector.expected,
                std::string(vector.name) + " result differs");
        require(dut.direct_error == vector.error,
                std::string(vector.name) + " error differs");
        require(static_cast<bool>(dut.direct_saturated) == vector.saturated,
                std::string(vector.name) + " saturation differs");
        dut.direct_left = vector.right;
        dut.direct_right = vector.left;
        eval_low(dut);
        require(dut.direct_result == vector.expected &&
                    dut.direct_error == vector.error &&
                    static_cast<bool>(dut.direct_saturated) == vector.saturated,
                std::string(vector.name) + " commuted result differs");
    }}
    uint32_t exhaustive_checks = 0;
    for (uint32_t code = 0; code < 65536U; ++code) {{
        if ((code & 0x7f80U) == 0x7f80U) continue;
        dut.direct_left = code;
        dut.direct_right = 0;
        eval_low(dut);
        const uint16_t identity = (code & 0x7fffU) == 0
                                  ? 0 : static_cast<uint16_t>(code);
        require(dut.direct_result == identity && dut.direct_error == 0 &&
                    !dut.direct_saturated,
                "zero identity differs at " + std::to_string(code));
        ++exhaustive_checks;
        dut.direct_right = code ^ 0x8000U;
        eval_low(dut);
        require(dut.direct_result == 0 && dut.direct_error == 0 &&
                    !dut.direct_saturated,
                "cancellation differs at " + std::to_string(code));
        ++exhaustive_checks;
    }}
    require(exhaustive_checks == 130560U, "exhaustive check count differs");

    reset(dut);
    require(dut.cmd_ready, "command interface was not ready");
    dut.abi_major = {command['abi_major']}U;
    dut.abi_minor = {command['abi_minor']}U;
    dut.expected_command_index = {command['expected_index']}U;
    for (unsigned word = 0; word < kCommand.size(); ++word)
        dut.command_record[word] = kCommand[word];
    dut.cmd_valid = 1;
    eval_low(dut);
    tick(dut);
    dut.cmd_valid = 0;
    for (unsigned wait = 0; !dut.operand_ready && wait < 20; ++wait) tick(dut);
    require(dut.operand_ready, "executor did not enter active state");

    uint32_t sent = 0;
    uint32_t received = 0;
    uint32_t cycles = 0;
    while (received < kCount) {{
        dut.result_ready = (cycles % 7U) != 2U;
        dut.operand_valid = 0;
        eval_low(dut);
        if (dut.result_valid) {{
            require(dut.result_index == received,
                    "result index differs at " + std::to_string(received));
            require(dut.result_destination_address == kDestination + received * 2ULL,
                    "result address differs at " + std::to_string(received));
            require(dut.result_code == expected[received],
                    "result code differs at " + std::to_string(received));
            require(dut.result_error == 0 && !dut.result_saturated,
                    "result status differs at " + std::to_string(received));
            if (dut.result_ready) ++received;
        }}
        if (sent < kCount && (cycles % 5U) != 1U && dut.operand_ready) {{
            require(dut.operand_index == sent,
                    "operand index differs at " + std::to_string(sent));
            require(dut.operand_source0_address == kSource0 + sent * 2ULL,
                    "source0 address differs at " + std::to_string(sent));
            require(dut.operand_source1_address == kSource1 + sent * 2ULL,
                    "source1 address differs at " + std::to_string(sent));
            dut.operand_left = left[sent];
            dut.operand_right = right[sent];
            dut.operand_valid = 1;
            ++sent;
        }}
        eval_low(dut);
        tick(dut);
        if (++cycles > kCount * 20U) fail("ADD campaign timed out");
    }}
    dut.operand_valid = 0;
    dut.result_ready = 1;
    for (unsigned wait = 0; !dut.done_valid && wait < 8; ++wait) tick(dut);
    require(dut.done_valid, "completion was not produced");
    require(dut.done_error == 0, "completion error differs");
    require(dut.done_command_index == {command['expected_index']}U,
            "completion command index differs");
    require(dut.done_element_count == kCount, "completion element count differs");
    require(dut.done_saturation_count == 0, "completion saturation count differs");
    require(sent == kCount, "sent element count differs");
    dut.done_ready = 1;
    tick(dut);
    dut.done_ready = 0;

    const auto run_fault = [&](uint16_t left_code, uint16_t right_code,
                               uint8_t result_error, uint8_t done_error) {{
        dut.result_ready = 0;
        for (unsigned wait = 0; !dut.cmd_ready && wait < 8; ++wait) tick(dut);
        require(dut.cmd_ready, "fault command interface was not ready");
        dut.cmd_valid = 1;
        eval_low(dut);
        tick(dut);
        dut.cmd_valid = 0;
        for (unsigned wait = 0; !dut.operand_ready && wait < 20; ++wait) tick(dut);
        require(dut.operand_ready, "fault executor did not enter active state");
        dut.operand_left = left_code;
        dut.operand_right = right_code;
        dut.operand_valid = 1;
        eval_low(dut);
        tick(dut);
        dut.operand_valid = 0;
        require(dut.result_valid, "fault result was not produced");
        require(dut.result_index == 0 && dut.result_error == result_error &&
                    dut.result_code == 0 && !dut.result_saturated,
                "fault result differs");
        dut.result_ready = 1;
        eval_low(dut);
        tick(dut);
        require(dut.done_valid, "fault completion was not produced");
        require(dut.done_error == done_error && dut.done_element_count == 1 &&
                    dut.done_saturation_count == 0,
                "fault completion differs");
        dut.done_ready = 1;
        tick(dut);
        dut.done_ready = 0;
    }};
    run_fault(0x7f80U, 0x3f80U, 1U, 9U);
    run_fault(0x7f7fU, 0x7f7fU, 2U, 10U);
    dut.final();
    std::cout << "PASS: Qwen ADD_BF16 RTL command elements={vectors['operand_count']} "
              << "directed={len(vectors['directed_vectors'])} "
              << "exhaustive=130560 "
              << "vector_set={vectors['vector_set_id']}\\n";
    std::cout << "PASS: Qwen ADD_BF16 RTL executor faults=2\\n";
    return 0;
}}
"""


def _write_hex(path: Path, values: list[int]) -> None:
    path.write_text("".join(f"{value:04x}\n" for value in values), encoding="ascii")


def _run(
    command: list[str], *, cwd: Path, timeout: int
) -> tuple[int, str]:
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


def _normalize(value: str, *, build: Path) -> str:
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
        run_code, run_log = _run(run_command, cwd=build, timeout=120)
    else:
        run_code, run_log = None, ""
    retained_compile = _normalize(compile_log, build=build)
    retained_run = _normalize(run_log, build=build)
    complete_log = retained_compile + retained_run
    passed = (
        compile_code == 0
        and run_code == 0
        and marker in retained_run
        and "PASS: Qwen ADD_BF16 RTL executor faults=2" in retained_run
    )
    return {
        "command": _normalize(
            shlex.join(compile_command) + " && " + shlex.join(run_command),
            build=build,
        ),
        "compile_log": retained_compile,
        "compile_returncode": compile_code,
        "log_sha256": hashlib.sha256(complete_log.encode("utf-8")).hexdigest(),
        "name": name,
        "run_log": retained_run,
        "run_returncode": run_code,
        "status": "pass" if passed else "fail",
    }


def run(vectors_path: Path) -> dict[str, Any]:
    vectors = load_strict_json(vectors_path)
    vector_schema = load_strict_json(VECTOR_SCHEMA_PATH)
    Draft202012Validator.check_schema(vector_schema)
    Draft202012Validator(vector_schema).validate(vectors)
    if vectors.get("schema") != VECTOR_SCHEMA or vectors.get(
        "vector_set_id"
    ) != _body_id(vectors, "vector_set_id"):
        raise ValueError("Qwen RTL ADD vector identity differs")
    marker = (
        f"PASS: Qwen ADD_BF16 RTL command elements={vectors['operand_count']} "
        f"directed={len(vectors['directed_vectors'])} "
        "exhaustive=130560 "
        f"vector_set={vectors['vector_set_id']}"
    )
    with tempfile.TemporaryDirectory(prefix="opentallas-qwen-ta-add-") as temporary:
        build = Path(temporary)
        wrapper = build / "ot_ta_add_campaign_top.sv"
        testbench = build / "tb_qwen_ta_add.sv"
        harness = build / "qwen_ta_add_harness.cpp"
        wrapper.write_text(_wrapper(), encoding="utf-8")
        testbench.write_text(_testbench(vectors), encoding="utf-8")
        harness.write_text(_harness(vectors), encoding="utf-8")
        _write_hex(build / "left.hex", vectors["left"]["codes"])
        _write_hex(build / "right.hex", vectors["right"]["codes"])
        _write_hex(build / "expected.hex", vectors["expected"]["codes"])
        iverilog_binary = build / "qwen_ta_add.vvp"
        verilator_dir = build / "verilator"
        cases = [
            _case(
                "iverilog",
                [
                    "iverilog",
                    "-g2012",
                    "-Wall",
                    "-s",
                    "tb_qwen_ta_add",
                    "-o",
                    str(iverilog_binary),
                    *(str(path) for path in RTL_PATHS),
                    str(wrapper),
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
                    "ot_ta_add_campaign_top",
                    "--Mdir",
                    str(verilator_dir),
                    *(str(path) for path in RTL_PATHS),
                    str(wrapper),
                    str(harness),
                    "-CFLAGS",
                    "-std=c++17",
                ],
                [str(verilator_dir / "Vot_ta_add_campaign_top")],
                build=build,
                marker=marker,
            ),
        ]
        generated = {
            "generated/expected.hex": _sha256_file(build / "expected.hex"),
            "generated/left.hex": _sha256_file(build / "left.hex"),
            "generated/ot_ta_add_campaign_top.sv": _sha256_file(wrapper),
            "generated/qwen_ta_add_harness.cpp": _sha256_file(harness),
            "generated/right.hex": _sha256_file(build / "right.hex"),
            "generated/tb_qwen_ta_add.sv": _sha256_file(testbench),
        }
    passed = all(case["status"] == "pass" for case in cases)
    fields = vectors["command"]["expected_fields"]
    body = {
        "build_id": vectors["build_id"],
        "cases": cases,
        "claim_boundary": vectors["claim_boundary"],
        "command_program_sha256": vectors["command_program_sha256"],
        "correlation": {
            "add_input_sram_bytes_read": 2 * vectors["operand_count"] * 2,
            "add_output_sram_bytes_written": vectors["operand_count"] * 2,
            "command_index": vectors["command"]["expected_index"],
            "destination_address": fields["destination"],
            "directed_case_count": len(vectors["directed_vectors"]),
            "expected_output_sha256": vectors["expected"]["payload_sha256"],
            "executor_fault_cases": 2,
            "finite_encoding_checks": 130560,
            "operand_count": vectors["operand_count"],
            "residual_additions": vectors["operand_count"],
            "source0_address": fields["source0"],
            "source1_address": fields["source1"],
        },
        "schema": SCHEMA,
        "simulators": ["iverilog", "verilator"],
        "source_sha256": {
            **{str(path.relative_to(ROOT)): _sha256_file(path) for path in RTL_PATHS},
            str(CAMPAIGN_SCHEMA_PATH.relative_to(ROOT)): _sha256_file(
                CAMPAIGN_SCHEMA_PATH
            ),
            str(VECTOR_SCHEMA_PATH.relative_to(ROOT)): _sha256_file(VECTOR_SCHEMA_PATH),
            str(VECTOR_BUILDER_PATH.relative_to(ROOT)): _sha256_file(VECTOR_BUILDER_PATH),
            str(Path(__file__).resolve().relative_to(ROOT)): _sha256_file(
                Path(__file__).resolve()
            ),
            str(vectors_path.resolve().relative_to(ROOT)): _sha256_file(vectors_path),
            **generated,
        },
        "status": "pass" if passed else "fail",
        "tools": {
            "iverilog": _version(["iverilog", "-V"]),
            "verilator": _version(["verilator", "--version"]),
        },
        "vector_set_id": vectors["vector_set_id"],
    }
    return {**body, "campaign_id": hashlib.sha256(canonical_json_bytes(body)).hexdigest()}


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
