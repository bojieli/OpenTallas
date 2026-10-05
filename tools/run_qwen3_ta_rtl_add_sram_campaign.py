#!/usr/bin/env python3
"""Execute the authentic Qwen ADD_BF16 command through SRAM transactions."""

from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path
import shlex
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
from tools import run_qwen3_ta_rtl_add_campaign as stream_campaign  # noqa: E402


SCHEMA = "opentallas.tensor_accelerator.qwen_rtl_add_sram_campaign.v1"
VECTOR_SCHEMA = "opentallas.tensor_accelerator.qwen_rtl_add_vectors.v1"
RTL_PATHS = (
    ROOT / "rtl/ot_ta_command_decoder.sv",
    ROOT / "rtl/ot_bf16_add_rne.sv",
    ROOT / "rtl/ot_ta_add_bf16_executor.sv",
    ROOT / "rtl/ot_ta_add_bf16_sram_engine.sv",
)
CAMPAIGN_SCHEMA_PATH = (
    ROOT
    / "schemas/compiler/tensor_accelerator/qwen_rtl_add_sram_campaign_v1.schema.json"
)
VECTOR_SCHEMA_PATH = (
    ROOT / "schemas/compiler/tensor_accelerator/qwen_rtl_add_vectors_v1.schema.json"
)
STREAM_CAMPAIGN_PATH = ROOT / "tools/run_qwen3_ta_rtl_add_campaign.py"


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(
        description="Run two simulators over authentic SRAM-bound Qwen ADD RTL"
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


def _case(
    name: str,
    compile_command: list[str],
    run_command: list[str],
    *,
    build: Path,
    marker: str,
) -> dict[str, Any]:
    compile_code, compile_log = stream_campaign._run(
        compile_command, cwd=ROOT, timeout=180
    )
    if compile_code == 0:
        run_code, run_log = stream_campaign._run(run_command, cwd=build, timeout=180)
    else:
        run_code, run_log = None, ""
    retained_compile = stream_campaign._normalize(compile_log, build=build)
    retained_run = stream_campaign._normalize(run_log, build=build)
    complete_log = retained_compile + retained_run
    passed = compile_code == 0 and run_code == 0 and marker in retained_run
    return {
        "command": stream_campaign._normalize(
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


def _testbench(vectors: dict[str, Any]) -> str:
    command = vectors["command"]
    fields = command["expected_fields"]
    count = vectors["operand_count"]
    reads = count * 2
    return f"""`timescale 1ns/1ps
module tb_qwen_ta_add_sram;
    reg clk = 0;
    reg rst_n = 0;
    reg cmd_valid = 0;
    wire cmd_ready;
    reg [15:0] abi_major = 0;
    reg [15:0] abi_minor = 0;
    reg [31:0] expected_command_index = 0;
    reg [511:0] command_record = 0;
    wire read_valid;
    reg read_ready = 0;
    wire [63:0] read_address;
    reg response_valid = 0;
    wire response_ready;
    reg [15:0] response_data = 0;
    wire write_valid;
    reg write_ready = 0;
    wire [63:0] write_address;
    wire [15:0] write_data;
    wire [1:0] write_byte_enable;
    wire done_valid;
    reg done_ready = 0;
    wire [7:0] done_error;
    wire [31:0] done_command_index;
    wire [31:0] done_element_count;
    wire [31:0] done_saturation_count;
    wire [31:0] done_sram_read_count;
    wire [31:0] done_sram_write_count;

    reg [15:0] left_mem [0:{count - 1}];
    reg [15:0] right_mem [0:{count - 1}];
    reg [15:0] expected_mem [0:{count - 1}];
    reg [15:0] destination_mem [0:{count - 1}];
    reg model_clear = 0;
    reg fault_mode = 0;
    reg [15:0] fault_left = 0;
    reg [15:0] fault_right = 0;
    reg pending_read = 0;
    reg [15:0] pending_data = 0;
    integer pending_delay = 0;
    integer cycles = 0;
    integer read_requests = 0;
    integer read_responses = 0;
    integer writes = 0;
    integer read_stalls = 0;
    integer write_stalls = 0;
    integer index = 0;

    always #5 clk = ~clk;

    ot_ta_add_bf16_sram_engine dut (
        .clk(clk), .rst_n(rst_n), .cmd_valid(cmd_valid),
        .cmd_ready(cmd_ready), .abi_major(abi_major), .abi_minor(abi_minor),
        .expected_command_index(expected_command_index),
        .command_record(command_record), .sram_read_valid(read_valid),
        .sram_read_ready(read_ready), .sram_read_address(read_address),
        .sram_response_valid(response_valid),
        .sram_response_ready(response_ready),
        .sram_response_data(response_data), .sram_write_valid(write_valid),
        .sram_write_ready(write_ready), .sram_write_address(write_address),
        .sram_write_data(write_data),
        .sram_write_byte_enable(write_byte_enable), .done_valid(done_valid),
        .done_ready(done_ready), .done_error(done_error),
        .done_command_index(done_command_index),
        .done_element_count(done_element_count),
        .done_saturation_count(done_saturation_count),
        .done_sram_read_count(done_sram_read_count),
        .done_sram_write_count(done_sram_write_count)
    );

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            read_ready <= 0;
            write_ready <= 0;
            response_valid <= 0;
            response_data <= 0;
            pending_read <= 0;
            pending_data <= 0;
            pending_delay <= 0;
            cycles <= 0;
            read_requests <= 0;
            read_responses <= 0;
            writes <= 0;
            read_stalls <= 0;
            write_stalls <= 0;
        end else if (model_clear) begin
            read_ready <= 0;
            write_ready <= 0;
            response_valid <= 0;
            response_data <= 0;
            pending_read <= 0;
            pending_data <= 0;
            pending_delay <= 0;
            cycles <= 0;
            read_requests <= 0;
            read_responses <= 0;
            writes <= 0;
            read_stalls <= 0;
            write_stalls <= 0;
        end else begin
            cycles <= cycles + 1;
            read_ready <= cycles[0];
            write_ready <= !cycles[0];

            if (read_valid && !read_ready)
                read_stalls <= read_stalls + 1;
            if (write_valid && !write_ready)
                write_stalls <= write_stalls + 1;

            if (response_valid && response_ready) begin
                response_valid <= 0;
                read_responses <= read_responses + 1;
            end

            if (read_valid && read_ready) begin
                if (pending_read || response_valid)
                    $fatal(1, "more than one SRAM read is outstanding");
                if ((read_requests % 2) == 0) begin
                    index = read_requests / 2;
                    if (read_address !== 64'd{fields['source0']} + index*2)
                        $fatal(1, "source0 read address differs at %0d", index);
                    pending_data <= fault_mode ? fault_left : left_mem[index];
                end else begin
                    index = read_requests / 2;
                    if (read_address !== 64'd{fields['source1']} + index*2)
                        $fatal(1, "source1 read address differs at %0d", index);
                    pending_data <= fault_mode ? fault_right : right_mem[index];
                end
                pending_delay <= (read_requests % 3) + 1;
                pending_read <= 1;
                read_requests <= read_requests + 1;
            end

            if (pending_read) begin
                if (pending_delay == 0 && !response_valid) begin
                    response_data <= pending_data;
                    response_valid <= 1;
                    pending_read <= 0;
                end else begin
                    pending_delay <= pending_delay - 1;
                end
            end

            if (write_valid && write_ready) begin
                if (fault_mode)
                    $fatal(1, "faulting arithmetic modified SRAM");
                if (write_address !== 64'd{fields['destination']} + writes*2 ||
                    write_data !== expected_mem[writes] ||
                    write_byte_enable !== 2'b11)
                    $fatal(1, "SRAM write differs at %0d", writes);
                destination_mem[writes] <= write_data;
                writes <= writes + 1;
            end

            if (cycles > {count * 40})
                $fatal(1, "SRAM ADD campaign timed out");
        end
    end

    task automatic run_fault;
        input [15:0] left_value;
        input [15:0] right_value;
        input [7:0] expected_error;
        begin
            model_clear = 1;
            @(negedge clk);
            model_clear = 0;
            fault_mode = 1;
            fault_left = left_value;
            fault_right = right_value;
            while (!cmd_ready) @(negedge clk);
            cmd_valid = 1;
            @(negedge clk);
            cmd_valid = 0;
            while (!done_valid) @(negedge clk);
            if (done_error !== expected_error || done_element_count !== 1 ||
                done_saturation_count !== 0 || done_sram_read_count !== 2 ||
                done_sram_write_count !== 0 || read_requests !== 2 ||
                read_responses !== 2 || writes !== 0 || pending_read ||
                response_valid || write_valid)
                $fatal(1, "faulting SRAM completion differs");
            done_ready = 1;
            @(negedge clk);
            done_ready = 0;
            fault_mode = 0;
        end
    endtask

    initial begin
        $readmemh("left.hex", left_mem);
        $readmemh("right.hex", right_mem);
        $readmemh("expected.hex", expected_mem);
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

        while (!done_valid) @(negedge clk);
        if (done_error !== 0 ||
            done_command_index !== 32'd{command['expected_index']} ||
            done_element_count !== {count} || done_saturation_count !== 0 ||
            done_sram_read_count !== {reads} ||
            done_sram_write_count !== {count} ||
            read_requests !== {reads} || read_responses !== {reads} ||
            writes !== {count} || read_stalls == 0 || write_stalls == 0 ||
            pending_read || response_valid)
            $fatal(1, "SRAM completion or transaction counters differ");
        for (index = 0; index < {count}; index = index + 1)
            if (destination_mem[index] !== expected_mem[index])
                $fatal(1, "destination SRAM differs at %0d", index);
        repeat (3) begin
            @(negedge clk);
            if (!done_valid || done_element_count !== {count} ||
                done_sram_read_count !== {reads} ||
                done_sram_write_count !== {count})
                $fatal(1, "completion was not stable under backpressure");
        end
        done_ready = 1;
        @(negedge clk);
        done_ready = 0;
        run_fault(16'h7f80, 16'h3f80, 8'd9);
        run_fault(16'h7f7f, 16'h7f7f, 8'd10);
        $display("PASS: Qwen ADD_BF16 SRAM RTL command elements={count} reads={reads} writes={count} faults=2 vector_set={vectors['vector_set_id']}");
        $finish;
    end
endmodule
"""


def _harness(vectors: dict[str, Any]) -> str:
    command = vectors["command"]
    fields = command["expected_fields"]
    count = vectors["operand_count"]
    record = int(command["record_hex"], 16)
    words = ", ".join(
        f"0x{(record >> (index * 32)) & 0xffffffff:08x}U" for index in range(16)
    )
    return f"""#include "Vot_ta_add_bf16_sram_engine.h"
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
constexpr uint32_t kCount = {count}U;
constexpr uint32_t kReads = {count * 2}U;
constexpr uint64_t kSource0 = {fields['source0']}ULL;
constexpr uint64_t kSource1 = {fields['source1']}ULL;
constexpr uint64_t kDestination = {fields['destination']}ULL;
constexpr std::array<uint32_t, 16> kCommand = {{{{{words}}}}};

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

void eval_low(Vot_ta_add_bf16_sram_engine& dut) {{
    dut.clk = 0;
    dut.eval();
}}

void tick(Vot_ta_add_bf16_sram_engine& dut) {{
    dut.clk = 1;
    dut.eval();
    dut.clk = 0;
    dut.eval();
}}

}}  // namespace

int main(int argc, char** argv) {{
    Verilated::commandArgs(argc, argv);
    Vot_ta_add_bf16_sram_engine dut;
    const auto left = load_hex("left.hex");
    const auto right = load_hex("right.hex");
    const auto expected = load_hex("expected.hex");
    std::vector<uint16_t> destination(kCount, 0xffffU);

    dut.rst_n = 0;
    dut.cmd_valid = 0;
    dut.sram_read_ready = 0;
    dut.sram_response_valid = 0;
    dut.sram_response_data = 0;
    dut.sram_write_ready = 0;
    dut.done_ready = 0;
    for (unsigned cycle = 0; cycle < 3; ++cycle) tick(dut);
    dut.rst_n = 1;
    eval_low(dut);

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

    bool pending = false;
    uint16_t pending_data = 0;
    uint32_t pending_delay = 0;
    bool response_valid = false;
    uint16_t response_data = 0;
    uint32_t read_requests = 0;
    uint32_t read_responses = 0;
    uint32_t writes = 0;
    uint32_t read_stalls = 0;
    uint32_t write_stalls = 0;
    uint32_t cycles = 0;

    while (!dut.done_valid) {{
        const bool read_ready = (cycles & 1U) != 0U;
        const bool write_ready = (cycles & 1U) == 0U;
        dut.sram_read_ready = read_ready;
        dut.sram_write_ready = write_ready;
        dut.sram_response_valid = response_valid;
        dut.sram_response_data = response_data;
        eval_low(dut);

        const bool read_fire = dut.sram_read_valid && read_ready;
        const bool response_fire = response_valid && dut.sram_response_ready;
        const bool write_fire = dut.sram_write_valid && write_ready;
        if (dut.sram_read_valid && !read_ready) ++read_stalls;
        if (dut.sram_write_valid && !write_ready) ++write_stalls;

        uint16_t requested_data = 0;
        if (read_fire) {{
            require(!pending && !response_valid,
                    "more than one SRAM read is outstanding");
            const uint32_t index = read_requests / 2U;
            if ((read_requests % 2U) == 0U) {{
                require(dut.sram_read_address == kSource0 + index * 2ULL,
                        "source0 read address differs at " +
                            std::to_string(index));
                requested_data = left[index];
            }} else {{
                require(dut.sram_read_address == kSource1 + index * 2ULL,
                        "source1 read address differs at " +
                            std::to_string(index));
                requested_data = right[index];
            }}
        }}
        if (write_fire) {{
            require(writes < kCount, "too many SRAM writes");
            require(dut.sram_write_address == kDestination + writes * 2ULL,
                    "write address differs at " + std::to_string(writes));
            require(dut.sram_write_data == expected[writes],
                    "write data differs at " + std::to_string(writes));
            require(dut.sram_write_byte_enable == 3U,
                    "write byte enable differs");
            destination[writes] = dut.sram_write_data;
        }}

        const bool pending_before = pending;
        tick(dut);

        if (response_fire) {{
            response_valid = false;
            ++read_responses;
        }}
        if (pending_before) {{
            if (pending_delay == 0U && !response_valid) {{
                response_data = pending_data;
                response_valid = true;
                pending = false;
            }} else {{
                --pending_delay;
            }}
        }}
        if (read_fire) {{
            pending = true;
            pending_data = requested_data;
            pending_delay = (read_requests % 3U) + 1U;
            ++read_requests;
        }}
        if (write_fire) ++writes;
        if (++cycles > kCount * 40U) fail("SRAM ADD campaign timed out");
    }}

    require(dut.done_error == 0, "completion error differs");
    require(dut.done_command_index == {command['expected_index']}U,
            "completion command index differs");
    require(dut.done_element_count == kCount,
            "completion element count differs");
    require(dut.done_saturation_count == 0,
            "completion saturation count differs");
    require(dut.done_sram_read_count == kReads && read_requests == kReads &&
                read_responses == kReads,
            "SRAM read counts differ");
    require(dut.done_sram_write_count == kCount && writes == kCount,
            "SRAM write counts differ");
    require(read_stalls > 0 && write_stalls > 0,
            "SRAM stalls were not exercised");
    require(!pending && !response_valid,
            "SRAM read remained outstanding at completion");
    require(destination == expected, "destination SRAM payload differs");

    for (unsigned hold = 0; hold < 3; ++hold) {{
        tick(dut);
        require(dut.done_valid && dut.done_element_count == kCount &&
                    dut.done_sram_read_count == kReads &&
                    dut.done_sram_write_count == kCount,
                "completion was not stable under backpressure");
    }}
    dut.done_ready = 1;
    tick(dut);
    dut.done_ready = 0;

    const auto run_fault = [&](uint16_t left_code, uint16_t right_code,
                               uint8_t expected_error) {{
        for (unsigned wait = 0; !dut.cmd_ready && wait < 8; ++wait) tick(dut);
        require(dut.cmd_ready, "fault command interface was not ready");
        dut.cmd_valid = 1;
        eval_low(dut);
        tick(dut);
        dut.cmd_valid = 0;

        bool fault_pending = false;
        uint16_t fault_pending_data = 0;
        bool fault_response_valid = false;
        uint16_t fault_response_data = 0;
        uint32_t fault_reads = 0;
        uint32_t fault_responses = 0;
        uint32_t fault_cycles = 0;
        while (!dut.done_valid) {{
            dut.sram_read_ready = (fault_cycles % 3U) != 1U;
            dut.sram_write_ready = (fault_cycles % 5U) != 2U;
            dut.sram_response_valid = fault_response_valid;
            dut.sram_response_data = fault_response_data;
            eval_low(dut);
            require(!dut.sram_write_valid,
                    "faulting arithmetic attempted to modify SRAM");
            const bool read_fire = dut.sram_read_valid && dut.sram_read_ready;
            const bool response_fire = fault_response_valid &&
                                       dut.sram_response_ready;
            uint16_t requested_data = 0;
            if (read_fire) {{
                require(!fault_pending && !fault_response_valid,
                        "fault path issued multiple SRAM reads");
                const uint32_t index = fault_reads / 2U;
                const bool left_operand = (fault_reads % 2U) == 0U;
                const uint64_t expected_address =
                    (left_operand ? kSource0 : kSource1) + index * 2ULL;
                require(dut.sram_read_address == expected_address,
                        "fault SRAM read address differs");
                requested_data = left_operand ? left_code : right_code;
            }}
            tick(dut);
            if (response_fire) {{
                fault_response_valid = false;
                ++fault_responses;
            }}
            if (fault_pending && !fault_response_valid) {{
                fault_response_data = fault_pending_data;
                fault_response_valid = true;
                fault_pending = false;
            }}
            if (read_fire) {{
                fault_pending = true;
                fault_pending_data = requested_data;
                ++fault_reads;
            }}
            if (++fault_cycles > 64U) fail("fault SRAM command timed out");
        }}
        require(dut.done_error == expected_error &&
                    dut.done_element_count == 1U &&
                    dut.done_saturation_count == 0U &&
                    dut.done_sram_read_count == 2U &&
                    dut.done_sram_write_count == 0U && fault_reads == 2U &&
                    fault_responses == 2U && !fault_pending &&
                    !fault_response_valid,
                "fault SRAM completion differs");
        dut.done_ready = 1;
        tick(dut);
        dut.done_ready = 0;
    }};
    run_fault(0x7f80U, 0x3f80U, 9U);
    run_fault(0x7f7fU, 0x7f7fU, 10U);
    dut.final();
    std::cout << "PASS: Qwen ADD_BF16 SRAM RTL command elements={count} "
              << "reads={count * 2} writes={count} faults=2 "
              << "vector_set={vectors['vector_set_id']}\\n";
    return 0;
}}
"""


def run(vectors_path: Path) -> dict[str, Any]:
    vectors = load_strict_json(vectors_path)
    vector_schema = load_strict_json(VECTOR_SCHEMA_PATH)
    Draft202012Validator.check_schema(vector_schema)
    Draft202012Validator(vector_schema).validate(vectors)
    if vectors.get("schema") != VECTOR_SCHEMA or vectors.get(
        "vector_set_id"
    ) != _body_id(vectors, "vector_set_id"):
        raise ValueError("Qwen RTL ADD vector identity differs")

    count = vectors["operand_count"]
    reads = count * 2
    marker = (
        f"PASS: Qwen ADD_BF16 SRAM RTL command elements={count} "
        f"reads={reads} writes={count} faults=2 "
        f"vector_set={vectors['vector_set_id']}"
    )
    with tempfile.TemporaryDirectory(prefix="opentallas-qwen-ta-add-sram-") as tmp:
        build = Path(tmp)
        testbench = build / "tb_qwen_ta_add_sram.sv"
        harness = build / "qwen_ta_add_sram_harness.cpp"
        testbench.write_text(_testbench(vectors), encoding="utf-8")
        harness.write_text(_harness(vectors), encoding="utf-8")
        stream_campaign._write_hex(build / "left.hex", vectors["left"]["codes"])
        stream_campaign._write_hex(build / "right.hex", vectors["right"]["codes"])
        stream_campaign._write_hex(
            build / "expected.hex", vectors["expected"]["codes"]
        )
        iverilog_binary = build / "qwen_ta_add_sram.vvp"
        verilator_dir = build / "verilator"
        cases = [
            _case(
                "iverilog",
                [
                    "iverilog",
                    "-g2012",
                    "-Wall",
                    "-s",
                    "tb_qwen_ta_add_sram",
                    "-o",
                    str(iverilog_binary),
                    *(str(path) for path in RTL_PATHS),
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
                    "ot_ta_add_bf16_sram_engine",
                    "--Mdir",
                    str(verilator_dir),
                    *(str(path) for path in RTL_PATHS),
                    str(harness),
                    "-CFLAGS",
                    "-std=c++17",
                ],
                [str(verilator_dir / "Vot_ta_add_bf16_sram_engine")],
                build=build,
                marker=marker,
            ),
        ]
        generated = {
            "generated/expected.hex": _sha256_file(build / "expected.hex"),
            "generated/left.hex": _sha256_file(build / "left.hex"),
            "generated/qwen_ta_add_sram_harness.cpp": _sha256_file(harness),
            "generated/right.hex": _sha256_file(build / "right.hex"),
            "generated/tb_qwen_ta_add_sram.sv": _sha256_file(testbench),
        }

    fields = vectors["command"]["expected_fields"]
    passed = all(case["status"] == "pass" for case in cases)
    body = {
        "build_id": vectors["build_id"],
        "cases": cases,
        "claim_boundary": {
            "behavioral_sram_model": True,
            "complete_add_command": True,
            "complete_layer_execution": False,
            "memory_request_writeback_control": True,
            "qualified_sram_macro": False,
            "ta_rtl_6_closed": False,
            "timing_or_performance": False,
        },
        "command_program_sha256": vectors["command_program_sha256"],
        "correlation": {
            "add_input_sram_bytes_read": reads * 2,
            "add_output_sram_bytes_written": count * 2,
            "command_index": vectors["command"]["expected_index"],
            "destination_address": fields["destination"],
            "expected_output_sha256": vectors["expected"]["payload_sha256"],
            "fault_write_suppression_cases": 2,
            "maximum_outstanding_reads": 1,
            "operand_count": count,
            "residual_additions": count,
            "source0_address": fields["source0"],
            "source1_address": fields["source1"],
            "sram_read_transactions": reads,
            "sram_write_transactions": count,
        },
        "schema": SCHEMA,
        "simulators": ["iverilog", "verilator"],
        "source_sha256": {
            **{str(path.relative_to(ROOT)): _sha256_file(path) for path in RTL_PATHS},
            str(CAMPAIGN_SCHEMA_PATH.relative_to(ROOT)): _sha256_file(
                CAMPAIGN_SCHEMA_PATH
            ),
            str(VECTOR_SCHEMA_PATH.relative_to(ROOT)): _sha256_file(
                VECTOR_SCHEMA_PATH
            ),
            str(STREAM_CAMPAIGN_PATH.relative_to(ROOT)): _sha256_file(
                STREAM_CAMPAIGN_PATH
            ),
            str(Path(__file__).resolve().relative_to(ROOT)): _sha256_file(
                Path(__file__).resolve()
            ),
            str(vectors_path.resolve().relative_to(ROOT)): _sha256_file(vectors_path),
            **generated,
        },
        "status": "pass" if passed else "fail",
        "tools": {
            "iverilog": stream_campaign._version(["iverilog", "-V"]),
            "verilator": stream_campaign._version(["verilator", "--version"]),
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
