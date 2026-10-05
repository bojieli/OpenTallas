#!/usr/bin/env python3
"""Run a dual-simulator, fail-stop Qwen DMA-plus-ADD RTL campaign."""

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


SCHEMA = "opentallas.tensor_accelerator.qwen_rtl_dma_add_campaign.v1"
VECTOR_SCHEMA = "opentallas.tensor_accelerator.qwen_rtl_dma_add_vectors.v1"
RTL_PATHS = (
    ROOT / "rtl/ot_ta_command_decoder.sv",
    ROOT / "rtl/ot_bf16_add_rne.sv",
    ROOT / "rtl/ot_ta_add_bf16_executor.sv",
    ROOT / "rtl/ot_ta_add_bf16_sram_engine.sv",
    ROOT / "rtl/ot_ta_dma_hbm_to_sram.sv",
    ROOT / "rtl/ot_ta_dma_add_sequencer.sv",
)
VECTOR_SCHEMA_PATH = (
    ROOT
    / "schemas/compiler/tensor_accelerator/qwen_rtl_dma_add_vectors_v1.schema.json"
)
CAMPAIGN_SCHEMA_PATH = (
    ROOT
    / "schemas/compiler/tensor_accelerator/qwen_rtl_dma_add_campaign_v1.schema.json"
)
VECTOR_BUILDER_PATH = ROOT / "tools/build_qwen3_ta_rtl_dma_add_vectors.py"


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(
        description="Run Icarus and Verilator over an ordered Qwen DMA/ADD slice"
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
    if shutil.which(command[0]) is None:
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
    compile_code, compile_log = _run(compile_command, cwd=ROOT, timeout=240)
    if compile_code == 0:
        run_code, run_log = _run(run_command, cwd=build, timeout=240)
    else:
        run_code, run_log = None, ""
    retained_compile = _normalize(compile_log, build=build)
    retained_run = _normalize(run_log, build=build)
    complete_log = retained_compile + retained_run
    passed = compile_code == 0 and run_code == 0 and marker in retained_run
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


def _testbench(vectors: dict[str, Any]) -> str:
    dma = vectors["commands"][0]
    add = vectors["commands"][1]
    composition = vectors["composition"]
    count = composition["add_element_count"]
    saturation = composition["expected_saturation_count"]
    return f"""`timescale 1ns/1ps
module tb_qwen_ta_dma_add;
    localparam integer ELEMENTS = {count};
    localparam integer DMA_BYTES = {count * 2};
    localparam integer DMA_WRITES = {count // 8};
    localparam [63:0] HBM_BASE = 64'd{dma['expected_fields']['source0']};
    localparam [63:0] LEFT_BASE = 64'd{composition['add_left_address']};
    localparam [63:0] RIGHT_BASE = 64'd{composition['add_right_address']};
    localparam [63:0] DEST_BASE = 64'd{composition['add_destination_address']};

    reg clk = 0;
    reg rst_n = 0;
    reg cmd_valid = 0;
    wire cmd_ready;
    reg cmd_last = 0;
    reg [15:0] abi_major = 2;
    reg [15:0] abi_minor = 5;
    reg [31:0] expected_command_index = 0;
    reg [511:0] command_record = 0;
    wire hbm_request_valid;
    reg hbm_request_ready = 0;
    wire [63:0] hbm_request_address;
    wire [15:0] hbm_request_bytes;
    reg hbm_response_valid = 0;
    wire hbm_response_ready;
    reg [511:0] hbm_response_data = 0;
    reg [1:0] hbm_response_error = 0;
    wire sram_read_valid;
    reg sram_read_ready = 0;
    wire [63:0] sram_read_address;
    reg sram_response_valid = 0;
    wire sram_response_ready;
    reg [15:0] sram_response_data = 0;
    wire sram_write_valid;
    reg sram_write_ready = 0;
    wire [63:0] sram_write_address;
    wire [127:0] sram_write_data;
    wire [15:0] sram_write_byte_enable;
    wire program_active;
    wire program_done_valid;
    reg program_done_ready = 0;
    wire [7:0] program_done_error;
    wire [31:0] program_done_failing_command_index;
    wire [31:0] program_done_last_command_index;
    wire [31:0] program_done_commands_accepted;
    wire [31:0] program_done_commands_completed;
    wire [31:0] program_done_hbm_request_count;
    wire [31:0] program_done_hbm_response_count;
    wire [31:0] program_done_hbm_bytes_read;
    wire [31:0] program_done_sram_read_count;
    wire [31:0] program_done_sram_bytes_read;
    wire [31:0] program_done_sram_write_count;
    wire [31:0] program_done_sram_bytes_written;
    wire [31:0] program_done_element_count;
    wire [31:0] program_done_saturation_count;

    reg [7:0] payload_mem [0:DMA_BYTES-1];
    reg [15:0] left_mem [0:ELEMENTS-1];
    reg [15:0] right_expected_mem [0:ELEMENTS-1];
    reg [15:0] right_mem [0:ELEMENTS-1];
    reg [15:0] expected_mem [0:ELEMENTS-1];
    reg [15:0] destination_mem [0:ELEMENTS-1];

    reg fault_hbm = 0;
    reg pending_hbm = 0;
    integer pending_hbm_burst = 0;
    integer pending_hbm_delay = 0;
    reg pending_read = 0;
    reg [15:0] pending_read_data = 0;
    integer pending_read_delay = 0;
    integer cycles = 0;
    integer hbm_requests = 0;
    integer hbm_responses = 0;
    integer dma_writes = 0;
    integer sram_reads = 0;
    integer sram_read_responses = 0;
    integer add_writes = 0;
    integer request_stalls = 0;
    integer read_stalls = 0;
    integer write_stalls = 0;
    integer lane;
    integer index;
    integer timeout;

    always #5 clk = ~clk;

    ot_ta_dma_add_sequencer dut (
        .clk(clk), .rst_n(rst_n), .cmd_valid(cmd_valid),
        .cmd_ready(cmd_ready), .cmd_last(cmd_last),
        .abi_major(abi_major), .abi_minor(abi_minor),
        .expected_command_index(expected_command_index),
        .command_record(command_record),
        .hbm_request_valid(hbm_request_valid),
        .hbm_request_ready(hbm_request_ready),
        .hbm_request_address(hbm_request_address),
        .hbm_request_bytes(hbm_request_bytes),
        .hbm_response_valid(hbm_response_valid),
        .hbm_response_ready(hbm_response_ready),
        .hbm_response_data(hbm_response_data),
        .hbm_response_error(hbm_response_error),
        .sram_read_valid(sram_read_valid),
        .sram_read_ready(sram_read_ready),
        .sram_read_address(sram_read_address),
        .sram_response_valid(sram_response_valid),
        .sram_response_ready(sram_response_ready),
        .sram_response_data(sram_response_data),
        .sram_write_valid(sram_write_valid),
        .sram_write_ready(sram_write_ready),
        .sram_write_address(sram_write_address),
        .sram_write_data(sram_write_data),
        .sram_write_byte_enable(sram_write_byte_enable),
        .program_active(program_active),
        .program_done_valid(program_done_valid),
        .program_done_ready(program_done_ready),
        .program_done_error(program_done_error),
        .program_done_failing_command_index(
            program_done_failing_command_index),
        .program_done_last_command_index(program_done_last_command_index),
        .program_done_commands_accepted(program_done_commands_accepted),
        .program_done_commands_completed(program_done_commands_completed),
        .program_done_hbm_request_count(program_done_hbm_request_count),
        .program_done_hbm_response_count(program_done_hbm_response_count),
        .program_done_hbm_bytes_read(program_done_hbm_bytes_read),
        .program_done_sram_read_count(program_done_sram_read_count),
        .program_done_sram_bytes_read(program_done_sram_bytes_read),
        .program_done_sram_write_count(program_done_sram_write_count),
        .program_done_sram_bytes_written(
            program_done_sram_bytes_written),
        .program_done_element_count(program_done_element_count),
        .program_done_saturation_count(program_done_saturation_count)
    );

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            hbm_request_ready <= 0;
            hbm_response_valid <= 0;
            hbm_response_data <= 0;
            hbm_response_error <= 0;
            sram_read_ready <= 0;
            sram_response_valid <= 0;
            sram_response_data <= 0;
            sram_write_ready <= 0;
            pending_hbm <= 0;
            pending_hbm_burst <= 0;
            pending_hbm_delay <= 0;
            pending_read <= 0;
            pending_read_data <= 0;
            pending_read_delay <= 0;
            cycles <= 0;
            hbm_requests <= 0;
            hbm_responses <= 0;
            dma_writes <= 0;
            sram_reads <= 0;
            sram_read_responses <= 0;
            add_writes <= 0;
            request_stalls <= 0;
            read_stalls <= 0;
            write_stalls <= 0;
        end else begin
            cycles <= cycles + 1;
            hbm_request_ready <= (cycles % 5) != 1;
            sram_read_ready <= cycles[0];
            sram_write_ready <= (cycles % 7) != 3;

            if (hbm_request_valid && !hbm_request_ready)
                request_stalls <= request_stalls + 1;
            if (sram_read_valid && !sram_read_ready)
                read_stalls <= read_stalls + 1;
            if (sram_write_valid && !sram_write_ready)
                write_stalls <= write_stalls + 1;

            if (hbm_response_valid && hbm_response_ready) begin
                hbm_response_valid <= 0;
                hbm_response_error <= 0;
                hbm_responses <= hbm_responses + 1;
            end
            if (hbm_request_valid && hbm_request_ready) begin
                if (pending_hbm || hbm_response_valid)
                    $fatal(1, "more than one HBM request outstanding");
                if (hbm_request_address !== HBM_BASE + hbm_requests*64 ||
                    hbm_request_bytes !== 16'd64)
                    $fatal(1, "HBM request differs at %0d", hbm_requests);
                pending_hbm <= 1;
                pending_hbm_burst <= hbm_requests;
                pending_hbm_delay <= (hbm_requests % 4) + 1;
                hbm_requests <= hbm_requests + 1;
            end
            if (pending_hbm) begin
                if (pending_hbm_delay == 0 && !hbm_response_valid) begin
                    for (lane = 0; lane < 64; lane = lane + 1)
                        hbm_response_data[lane*8 +: 8] <=
                            payload_mem[pending_hbm_burst*64 + lane];
                    hbm_response_error <= fault_hbm ? 2'd1 : 2'd0;
                    hbm_response_valid <= 1;
                    pending_hbm <= 0;
                end else begin
                    pending_hbm_delay <= pending_hbm_delay - 1;
                end
            end

            if (sram_response_valid && sram_response_ready) begin
                sram_response_valid <= 0;
                sram_read_responses <= sram_read_responses + 1;
            end
            if (sram_read_valid && sram_read_ready) begin
                if (pending_read || sram_response_valid)
                    $fatal(1, "more than one SRAM read outstanding");
                if (dma_writes != DMA_WRITES)
                    $fatal(1, "ADD read bypassed incomplete DMA");
                if (sram_read_address >= LEFT_BASE &&
                    sram_read_address < LEFT_BASE + DMA_BYTES) begin
                    index = (sram_read_address - LEFT_BASE) / 2;
                    pending_read_data <= left_mem[index];
                end else if (sram_read_address >= RIGHT_BASE &&
                             sram_read_address < RIGHT_BASE + DMA_BYTES) begin
                    index = (sram_read_address - RIGHT_BASE) / 2;
                    pending_read_data <= right_mem[index];
                end else begin
                    $fatal(1, "SRAM read outside operands");
                end
                pending_read <= 1;
                pending_read_delay <= (sram_reads % 3) + 1;
                sram_reads <= sram_reads + 1;
            end
            if (pending_read) begin
                if (pending_read_delay == 0 && !sram_response_valid) begin
                    sram_response_data <= pending_read_data;
                    sram_response_valid <= 1;
                    pending_read <= 0;
                end else begin
                    pending_read_delay <= pending_read_delay - 1;
                end
            end

            if (sram_write_valid && sram_write_ready) begin
                if (sram_write_address >= RIGHT_BASE &&
                    sram_write_address < RIGHT_BASE + DMA_BYTES) begin
                    if (sram_write_byte_enable !== 16'hffff ||
                        sram_write_address !== RIGHT_BASE + dma_writes*16)
                        $fatal(1, "DMA SRAM write metadata differs");
                    for (lane = 0; lane < 8; lane = lane + 1) begin
                        index = dma_writes*8 + lane;
                        if (sram_write_data[lane*16 +: 16] !==
                            right_expected_mem[index])
                            $fatal(1, "DMA SRAM write data differs at %0d", index);
                        right_mem[index] <= sram_write_data[lane*16 +: 16];
                    end
                    dma_writes <= dma_writes + 1;
                end else if (sram_write_address >= DEST_BASE &&
                             sram_write_address < DEST_BASE + DMA_BYTES) begin
                    index = (sram_write_address - DEST_BASE) / 2;
                    if (sram_write_byte_enable !== 16'h0003 ||
                        sram_write_data[15:0] !== expected_mem[index] ||
                        index != add_writes)
                        $fatal(1, "ADD SRAM write differs at %0d", index);
                    destination_mem[index] <= sram_write_data[15:0];
                    add_writes <= add_writes + 1;
                end else begin
                    $fatal(1, "SRAM write outside composed regions");
                end
            end
        end
    end

    task reset_case(input reg inject_hbm_fault);
        integer clear_index;
        begin
            rst_n = 0;
            cmd_valid = 0;
            cmd_last = 0;
            program_done_ready = 0;
            fault_hbm = inject_hbm_fault;
            for (clear_index = 0; clear_index < ELEMENTS;
                 clear_index = clear_index + 1) begin
                right_mem[clear_index] = 0;
                destination_mem[clear_index] = 0;
            end
            repeat (3) @(posedge clk);
            @(negedge clk);
            rst_n = 1;
        end
    endtask

    task submit_command(
        input [511:0] record,
        input [31:0] expected_index,
        input reg last
    );
        begin
            timeout = 0;
            while (!cmd_ready) begin
                @(posedge clk);
                timeout = timeout + 1;
                if (timeout > 200000)
                    $fatal(1, "command ready timeout");
            end
            @(negedge clk);
            command_record = record;
            expected_command_index = expected_index;
            cmd_last = last;
            cmd_valid = 1;
            @(posedge clk);
            if (!cmd_ready)
                $fatal(1, "command handshake disappeared");
            @(negedge clk);
            cmd_valid = 0;
        end
    endtask

    task await_done;
        begin
            timeout = 0;
            while (!program_done_valid) begin
                @(posedge clk);
                timeout = timeout + 1;
                if (timeout > 250000)
                    $fatal(1, "program completion timeout");
            end
            if (cmd_ready)
                $fatal(1, "command accepted while completion pending");
        end
    endtask

    task acknowledge_done;
        begin
            repeat (3) begin
                @(posedge clk);
                if (!program_done_valid)
                    $fatal(1, "program completion was not stable");
            end
            @(negedge clk);
            program_done_ready = 1;
            @(posedge clk);
            @(negedge clk);
            program_done_ready = 0;
        end
    endtask

    task prove_success;
        integer check_index;
        begin
            reset_case(0);
            submit_command(512'h{dma['record_hex']}, 32'd1, 0);
            submit_command(512'h{add['record_hex']}, 32'd5131, 1);
            await_done();
            if (program_done_error != 0 ||
                program_done_failing_command_index != 32'hffff_ffff ||
                program_done_last_command_index != 5131 ||
                program_done_commands_accepted != 2 ||
                program_done_commands_completed != 2 ||
                program_done_hbm_request_count != 128 ||
                program_done_hbm_response_count != 128 ||
                program_done_hbm_bytes_read != 8192 ||
                program_done_sram_read_count != 8192 ||
                program_done_sram_bytes_read != 16384 ||
                program_done_sram_write_count != 4608 ||
                program_done_sram_bytes_written != 16384 ||
                program_done_element_count != 4096 ||
                program_done_saturation_count != {saturation})
                $fatal(1, "successful program counters differ");
            if (hbm_requests != 128 || hbm_responses != 128 ||
                dma_writes != 512 || sram_reads != 8192 ||
                sram_read_responses != 8192 || add_writes != 4096)
                $fatal(1, "successful model counters differ");
            if (request_stalls == 0 || read_stalls == 0 || write_stalls == 0)
                $fatal(1, "backpressure was not exercised");
            for (check_index = 0; check_index < ELEMENTS;
                 check_index = check_index + 1)
                if (destination_mem[check_index] !== expected_mem[check_index])
                    $fatal(1, "destination differs at %0d", check_index);
            acknowledge_done();
        end
    endtask

    task prove_crc_fail_stop;
        begin
            reset_case(0);
            submit_command(512'h{dma['record_hex']} ^ (512'd1 << 100),
                           32'd1, 0);
            await_done();
            if (program_done_error != 1 ||
                program_done_failing_command_index != 1 ||
                program_done_commands_accepted != 1 ||
                program_done_commands_completed != 0 ||
                hbm_requests != 0 || dma_writes != 0 || sram_reads != 0)
                $fatal(1, "CRC fail-stop result differs");
            @(negedge clk);
            command_record = 512'h{add['record_hex']};
            expected_command_index = 5131;
            cmd_last = 1;
            cmd_valid = 1;
            repeat (3) begin
                @(posedge clk);
                if (cmd_ready || sram_read_valid || sram_write_valid)
                    $fatal(1, "successor escaped CRC fail-stop");
            end
            @(negedge clk);
            cmd_valid = 0;
            acknowledge_done();
        end
    endtask

    task prove_hbm_fail_stop;
        begin
            reset_case(1);
            submit_command(512'h{dma['record_hex']}, 32'd1, 0);
            await_done();
            if (program_done_error != 11 ||
                program_done_failing_command_index != 1 ||
                program_done_commands_accepted != 1 ||
                program_done_commands_completed != 0 ||
                program_done_hbm_request_count != 1 ||
                program_done_hbm_response_count != 1 ||
                program_done_hbm_bytes_read != 0 ||
                program_done_sram_write_count != 0 ||
                hbm_requests != 1 || hbm_responses != 1 ||
                dma_writes != 0 || sram_reads != 0)
                $fatal(1, "HBM fail-stop result differs");
            acknowledge_done();
        end
    endtask

    task prove_nonmonotonic_rejection;
        begin
            reset_case(0);
            submit_command(512'h{dma['record_hex']}, 32'd1, 0);
            submit_command(512'h{add['record_hex']}, 32'd1, 1);
            await_done();
            if (program_done_error != 12 ||
                program_done_failing_command_index != 1 ||
                program_done_commands_accepted != 2 ||
                program_done_commands_completed != 1 ||
                program_done_hbm_request_count != 128 ||
                program_done_sram_write_count != 512 ||
                hbm_requests != 128 || dma_writes != 512 ||
                sram_reads != 0 || add_writes != 0)
                $fatal(1, "nonmonotonic rejection differs");
            acknowledge_done();
        end
    endtask

    initial begin
        $readmemh("payload.hex", payload_mem);
        $readmemh("left.hex", left_mem);
        $readmemh("right.hex", right_expected_mem);
        $readmemh("expected.hex", expected_mem);
        prove_success();
        prove_crc_fail_stop();
        prove_hbm_fail_stop();
        prove_nonmonotonic_rejection();
        $display("PASS: Qwen DMA+ADD RTL sequence commands=2 elements=4096 faults=3 vector_set={vectors['vector_set_id']}");
        $finish;
    end
endmodule
"""


def _harness(vectors: dict[str, Any]) -> str:
    dma = vectors["commands"][0]
    add = vectors["commands"][1]
    composition = vectors["composition"]
    dma_record = int(dma["record_hex"], 16)
    add_record = int(add["record_hex"], 16)
    dma_words = ", ".join(
        f"0x{(dma_record >> (index * 32)) & 0xffffffff:08x}U"
        for index in range(16)
    )
    add_words = ", ".join(
        f"0x{(add_record >> (index * 32)) & 0xffffffff:08x}U"
        for index in range(16)
    )
    return f"""#include "Vot_ta_dma_add_sequencer.h"
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
constexpr uint32_t kElements = {composition['add_element_count']}U;
constexpr uint32_t kBytes = kElements * 2U;
constexpr uint64_t kHbmBase = {dma['expected_fields']['source0']}ULL;
constexpr uint64_t kLeftBase = {composition['add_left_address']}ULL;
constexpr uint64_t kRightBase = {composition['add_right_address']}ULL;
constexpr uint64_t kDestination = {composition['add_destination_address']}ULL;
constexpr uint32_t kExpectedSaturation =
    {composition['expected_saturation_count']}U;
constexpr std::array<uint32_t, 16> kDma = {{{{{dma_words}}}}};
constexpr std::array<uint32_t, 16> kAdd = {{{{{add_words}}}}};

[[noreturn]] void fail(const std::string& message) {{
    std::cerr << "FAIL: " << message << "\\n";
    std::exit(1);
}}

void require(bool condition, const std::string& message) {{
    if (!condition) fail(message);
}}

template <typename T>
std::vector<T> load_hex(const char* path, uint32_t maximum) {{
    std::ifstream stream(path);
    if (!stream) fail(std::string("cannot open ") + path);
    std::vector<T> result;
    uint32_t value = 0;
    while (stream >> std::hex >> value) {{
        if (value > maximum) fail(std::string("wide value in ") + path);
        result.push_back(static_cast<T>(value));
    }}
    return result;
}}

void eval_low(Vot_ta_dma_add_sequencer& dut) {{
    dut.clk = 0;
    dut.eval();
}}

void tick(Vot_ta_dma_add_sequencer& dut) {{
    dut.clk = 1;
    dut.eval();
    dut.clk = 0;
    dut.eval();
}}

void set_record(Vot_ta_dma_add_sequencer& dut,
                const std::array<uint32_t, 16>& record) {{
    for (uint32_t word = 0; word < record.size(); ++word)
        dut.command_record[word] = record[word];
}}

struct Model {{
    Vot_ta_dma_add_sequencer& dut;
    const std::vector<uint8_t>& payload;
    const std::vector<uint16_t>& left;
    const std::vector<uint16_t>& right_expected;
    const std::vector<uint16_t>& expected;
    std::vector<uint16_t> right = std::vector<uint16_t>(kElements, 0);
    std::vector<uint16_t> destination = std::vector<uint16_t>(kElements, 0);
    bool fault_hbm = false;
    bool hbm_pending = false;
    uint32_t hbm_pending_burst = 0;
    uint32_t hbm_delay = 0;
    bool hbm_response = false;
    uint32_t hbm_response_burst = 0;
    bool read_pending = false;
    uint16_t read_pending_data = 0;
    uint32_t read_delay = 0;
    bool read_response = false;
    uint16_t read_response_data = 0;
    uint32_t cycles = 0;
    uint32_t hbm_requests = 0;
    uint32_t hbm_responses = 0;
    uint32_t dma_writes = 0;
    uint32_t reads = 0;
    uint32_t read_responses = 0;
    uint32_t add_writes = 0;
    uint32_t request_stalls = 0;
    uint32_t read_stalls = 0;
    uint32_t write_stalls = 0;

    void set_hbm_response() {{
        for (uint32_t word = 0; word < 16U; ++word) {{
            uint32_t value = 0;
            for (uint32_t lane = 0; lane < 4U; ++lane)
                value |= static_cast<uint32_t>(payload[
                    hbm_response_burst * 64U + word * 4U + lane])
                         << (lane * 8U);
            dut.hbm_response_data[word] = value;
        }}
    }}

    void step() {{
        dut.hbm_request_ready = (cycles % 5U) != 1U;
        dut.hbm_response_valid = hbm_response;
        dut.hbm_response_error = hbm_response && fault_hbm ? 1U : 0U;
        if (hbm_response) set_hbm_response();
        dut.sram_read_ready = (cycles & 1U) != 0U;
        dut.sram_response_valid = read_response;
        dut.sram_response_data = read_response_data;
        dut.sram_write_ready = (cycles % 7U) != 3U;
        eval_low(dut);

        const bool request_fire = dut.hbm_request_valid &&
                                  dut.hbm_request_ready;
        const bool hbm_response_fire = hbm_response &&
                                       dut.hbm_response_ready;
        const bool read_fire = dut.sram_read_valid && dut.sram_read_ready;
        const bool read_response_fire = read_response &&
                                        dut.sram_response_ready;
        const bool write_fire = dut.sram_write_valid && dut.sram_write_ready;
        if (dut.hbm_request_valid && !dut.hbm_request_ready) ++request_stalls;
        if (dut.sram_read_valid && !dut.sram_read_ready) ++read_stalls;
        if (dut.sram_write_valid && !dut.sram_write_ready) ++write_stalls;

        if (request_fire) {{
            require(!hbm_pending && !hbm_response,
                    "multiple HBM requests outstanding");
            require(dut.hbm_request_address == kHbmBase + hbm_requests * 64ULL &&
                        dut.hbm_request_bytes == 64U,
                    "HBM request differs at " + std::to_string(hbm_requests));
        }}

        uint16_t requested_data = 0;
        if (read_fire) {{
            require(!read_pending && !read_response,
                    "multiple SRAM reads outstanding");
            if (dut.sram_read_address >= kLeftBase &&
                dut.sram_read_address < kLeftBase + kBytes) {{
                const uint32_t index =
                    static_cast<uint32_t>((dut.sram_read_address-kLeftBase)/2U);
                requested_data = left[index];
            }} else if (dut.sram_read_address >= kRightBase &&
                       dut.sram_read_address < kRightBase + kBytes) {{
                const uint32_t index = static_cast<uint32_t>(
                    (dut.sram_read_address-kRightBase)/2U);
                requested_data = right[index];
            }} else {{
                fail("SRAM read outside operand ranges");
            }}
        }}

        bool write_is_dma = false;
        if (write_fire) {{
            if (dut.sram_write_address >= kRightBase &&
                dut.sram_write_address < kRightBase + kBytes) {{
                write_is_dma = true;
                require(dut.sram_write_byte_enable == 0xffffU &&
                            dut.sram_write_address ==
                                kRightBase + dma_writes * 16ULL,
                        "DMA SRAM metadata differs");
                for (uint32_t lane = 0; lane < 8U; ++lane) {{
                    const uint32_t index = dma_writes * 8U + lane;
                    const uint32_t word = lane / 2U;
                    const uint32_t shift = (lane % 2U) * 16U;
                    const uint16_t value = static_cast<uint16_t>(
                        dut.sram_write_data[word] >> shift);
                    require(value == right_expected[index],
                            "DMA SRAM data differs at " +
                                std::to_string(index));
                    right[index] = value;
                }}
            }} else if (dut.sram_write_address >= kDestination &&
                       dut.sram_write_address < kDestination + kBytes) {{
                const uint32_t index = static_cast<uint32_t>(
                    (dut.sram_write_address-kDestination)/2U);
                const uint16_t value =
                    static_cast<uint16_t>(dut.sram_write_data[0]);
                if (!(dut.sram_write_byte_enable == 3U &&
                      index == add_writes && value == expected[index]))
                    fail("ADD SRAM write differs index=" +
                         std::to_string(index) + " writes=" +
                         std::to_string(add_writes) + " value=" +
                         std::to_string(value) + " expected=" +
                         std::to_string(expected[index]) + " dma_writes=" +
                         std::to_string(dma_writes));
                destination[index] = value;
            }} else {{
                fail("SRAM write outside composed ranges");
            }}
        }}

        const bool hbm_pending_before = hbm_pending;
        const bool read_pending_before = read_pending;
        tick(dut);

        if (hbm_response_fire) {{
            hbm_response = false;
            ++hbm_responses;
        }}
        if (hbm_pending_before) {{
            if (hbm_delay == 0U && !hbm_response) {{
                hbm_response_burst = hbm_pending_burst;
                hbm_response = true;
                hbm_pending = false;
            }} else {{
                --hbm_delay;
            }}
        }}
        if (request_fire) {{
            hbm_pending = true;
            hbm_pending_burst = hbm_requests;
            hbm_delay = (hbm_requests % 4U) + 1U;
            ++hbm_requests;
        }}
        if (read_response_fire) {{
            read_response = false;
            ++read_responses;
        }}
        if (read_pending_before) {{
            if (read_delay == 0U && !read_response) {{
                read_response_data = read_pending_data;
                read_response = true;
                read_pending = false;
            }} else {{
                --read_delay;
            }}
        }}
        if (read_fire) {{
            read_pending = true;
            read_pending_data = requested_data;
            read_delay = (reads % 3U) + 1U;
            ++reads;
        }}
        if (write_fire) {{
            if (write_is_dma)
                ++dma_writes;
            else
                ++add_writes;
        }}
        ++cycles;
    }}
}};

void reset(Vot_ta_dma_add_sequencer& dut) {{
    dut.rst_n = 0;
    dut.cmd_valid = 0;
    dut.cmd_last = 0;
    dut.abi_major = 2;
    dut.abi_minor = 5;
    dut.hbm_request_ready = 0;
    dut.hbm_response_valid = 0;
    dut.hbm_response_error = 0;
    dut.sram_read_ready = 0;
    dut.sram_response_valid = 0;
    dut.sram_response_data = 0;
    dut.sram_write_ready = 0;
    dut.program_done_ready = 0;
    for (uint32_t cycle = 0; cycle < 3U; ++cycle) tick(dut);
    dut.rst_n = 1;
    eval_low(dut);
    require(dut.cmd_ready, "command interface was not ready after reset");
}}

void submit(Vot_ta_dma_add_sequencer& dut, Model& model,
            const std::array<uint32_t,16>& record, uint32_t index,
            bool last) {{
    for (uint32_t wait = 0; !dut.cmd_ready; ++wait) {{
        if (wait > 250000U) fail("command ready timeout");
        model.step();
    }}
    set_record(dut, record);
    dut.expected_command_index = index;
    dut.cmd_last = last;
    dut.cmd_valid = 1;
    eval_low(dut);
    require(dut.cmd_ready, "command handshake disappeared");
    tick(dut);
    dut.cmd_valid = 0;
}}

void drive_done(Vot_ta_dma_add_sequencer& dut, Model& model) {{
    for (uint32_t wait = 0; !dut.program_done_valid; ++wait) {{
        if (wait > 250000U) fail("program completion timeout");
        model.step();
    }}
    require(!dut.cmd_ready, "command ready while completion pending");
}}

void acknowledge(Vot_ta_dma_add_sequencer& dut) {{
    for (uint32_t hold = 0; hold < 3U; ++hold) {{
        tick(dut);
        require(dut.program_done_valid,
                "program completion was not stable");
    }}
    dut.program_done_ready = 1;
    tick(dut);
    dut.program_done_ready = 0;
}}

}}  // namespace

int main(int argc, char** argv) {{
    Verilated::commandArgs(argc, argv);
    Vot_ta_dma_add_sequencer dut;
    const auto payload = load_hex<uint8_t>("payload.hex", 0xffU);
    const auto left = load_hex<uint16_t>("left.hex", 0xffffU);
    const auto right = load_hex<uint16_t>("right.hex", 0xffffU);
    const auto expected = load_hex<uint16_t>("expected.hex", 0xffffU);
    require(payload.size() == kBytes && left.size() == kElements &&
                right.size() == kElements && expected.size() == kElements,
            "hex vector lengths differ");

    reset(dut);
    Model success{{dut, payload, left, right, expected}};
    submit(dut, success, kDma, 1U, false);
    submit(dut, success, kAdd, 5131U, true);
    drive_done(dut, success);
    require(dut.program_done_error == 0U &&
                dut.program_done_failing_command_index == 0xffffffffU &&
                dut.program_done_last_command_index == 5131U &&
                dut.program_done_commands_accepted == 2U &&
                dut.program_done_commands_completed == 2U &&
                dut.program_done_hbm_request_count == 128U &&
                dut.program_done_hbm_response_count == 128U &&
                dut.program_done_hbm_bytes_read == 8192U &&
                dut.program_done_sram_read_count == 8192U &&
                dut.program_done_sram_bytes_read == 16384U &&
                dut.program_done_sram_write_count == 4608U &&
                dut.program_done_sram_bytes_written == 16384U &&
                dut.program_done_element_count == 4096U &&
                dut.program_done_saturation_count == kExpectedSaturation,
            "successful program counters differ");
    require(success.hbm_requests == 128U && success.hbm_responses == 128U &&
                success.dma_writes == 512U && success.reads == 8192U &&
                success.read_responses == 8192U &&
                success.add_writes == 4096U &&
                success.destination == expected,
            "successful memory model differs");
    require(success.request_stalls && success.read_stalls &&
                success.write_stalls,
            "backpressure was not exercised");
    acknowledge(dut);

    reset(dut);
    Model crc{{dut, payload, left, right, expected}};
    auto corrupt_dma = kDma;
    corrupt_dma[3] ^= 0x10U;
    submit(dut, crc, corrupt_dma, 1U, false);
    drive_done(dut, crc);
    require(dut.program_done_error == 1U &&
                dut.program_done_failing_command_index == 1U &&
                dut.program_done_commands_accepted == 1U &&
                dut.program_done_commands_completed == 0U &&
                crc.hbm_requests == 0U && crc.dma_writes == 0U &&
                crc.reads == 0U,
            "CRC fail-stop differs");
    set_record(dut, kAdd);
    dut.expected_command_index = 5131U;
    dut.cmd_last = 1;
    dut.cmd_valid = 1;
    for (uint32_t hold = 0; hold < 3U; ++hold) {{
        crc.step();
        require(!dut.cmd_ready && !dut.sram_read_valid,
                "successor escaped CRC fail-stop");
    }}
    dut.cmd_valid = 0;
    acknowledge(dut);

    reset(dut);
    Model hbm_fault{{dut, payload, left, right, expected}};
    hbm_fault.fault_hbm = true;
    submit(dut, hbm_fault, kDma, 1U, false);
    drive_done(dut, hbm_fault);
    require(dut.program_done_error == 11U &&
                dut.program_done_failing_command_index == 1U &&
                dut.program_done_commands_accepted == 1U &&
                dut.program_done_commands_completed == 0U &&
                dut.program_done_hbm_request_count == 1U &&
                dut.program_done_hbm_response_count == 1U &&
                dut.program_done_hbm_bytes_read == 0U &&
                dut.program_done_sram_write_count == 0U &&
                hbm_fault.hbm_requests == 1U &&
                hbm_fault.hbm_responses == 1U &&
                hbm_fault.dma_writes == 0U && hbm_fault.reads == 0U,
            "HBM fail-stop differs");
    acknowledge(dut);

    reset(dut);
    Model order{{dut, payload, left, right, expected}};
    submit(dut, order, kDma, 1U, false);
    submit(dut, order, kAdd, 1U, true);
    drive_done(dut, order);
    require(dut.program_done_error == 12U &&
                dut.program_done_failing_command_index == 1U &&
                dut.program_done_commands_accepted == 2U &&
                dut.program_done_commands_completed == 1U &&
                dut.program_done_hbm_request_count == 128U &&
                dut.program_done_sram_write_count == 512U &&
                order.hbm_requests == 128U && order.dma_writes == 512U &&
                order.reads == 0U && order.add_writes == 0U,
            "nonmonotonic rejection differs");
    acknowledge(dut);

    dut.final();
    std::cout << "PASS: Qwen DMA+ADD RTL sequence commands=2 elements=4096 "
              << "faults=3 vector_set={vectors['vector_set_id']}\\n";
    return 0;
}}
"""


def _write_hex(path: Path, values: list[int], digits: int) -> None:
    path.write_text(
        "".join(f"{value:0{digits}x}\n" for value in values), encoding="ascii"
    )


def run(vectors_path: Path) -> dict[str, Any]:
    vectors = load_strict_json(vectors_path)
    vector_schema = load_strict_json(VECTOR_SCHEMA_PATH)
    Draft202012Validator.check_schema(vector_schema)
    Draft202012Validator(vector_schema).validate(vectors)
    if (
        vectors.get("schema") != VECTOR_SCHEMA
        or vectors.get("vector_set_id") != _body_id(vectors, "vector_set_id")
    ):
        raise ValueError("Qwen RTL DMA/ADD vector identity differs")

    marker = (
        "PASS: Qwen DMA+ADD RTL sequence commands=2 elements=4096 faults=3 "
        f"vector_set={vectors['vector_set_id']}"
    )
    with tempfile.TemporaryDirectory(
        prefix="opentallas-qwen-ta-dma-add-"
    ) as tmp:
        build = Path(tmp)
        testbench = build / "tb_qwen_ta_dma_add.sv"
        harness = build / "qwen_ta_dma_add_harness.cpp"
        payload_path = build / "payload.hex"
        left_path = build / "left.hex"
        right_path = build / "right.hex"
        expected_path = build / "expected.hex"
        testbench.write_text(_testbench(vectors), encoding="utf-8")
        harness.write_text(_harness(vectors), encoding="utf-8")
        payload = bytes.fromhex(vectors["dma_payload_hex"])
        _write_hex(payload_path, list(payload), 2)
        _write_hex(left_path, vectors["left_codes"], 4)
        _write_hex(
            right_path,
            [int.from_bytes(payload[index : index + 2], "little")
             for index in range(0, len(payload), 2)],
            4,
        )
        _write_hex(expected_path, vectors["expected_codes"], 4)
        iverilog_binary = build / "qwen_ta_dma_add.vvp"
        verilator_dir = build / "verilator"
        cases = [
            _case(
                "iverilog",
                [
                    "iverilog", "-g2012", "-Wall", "-s",
                    "tb_qwen_ta_dma_add", "-o", str(iverilog_binary),
                    *(str(path) for path in RTL_PATHS), str(testbench),
                ],
                ["vvp", str(iverilog_binary)],
                build=build,
                marker=marker,
            ),
            _case(
                "verilator",
                [
                    "verilator", "--cc", "--exe", "--build", "-Wall",
                    "-Wno-fatal", "--top-module", "ot_ta_dma_add_sequencer",
                    "--Mdir", str(verilator_dir),
                    *(str(path) for path in RTL_PATHS), str(harness),
                    "-CFLAGS", "-std=c++17",
                ],
                [str(verilator_dir / "Vot_ta_dma_add_sequencer")],
                build=build,
                marker=marker,
            ),
        ]
        generated = {
            "generated/expected.hex": _sha256_file(expected_path),
            "generated/left.hex": _sha256_file(left_path),
            "generated/payload.hex": _sha256_file(payload_path),
            "generated/qwen_ta_dma_add_harness.cpp": _sha256_file(harness),
            "generated/right.hex": _sha256_file(right_path),
            "generated/tb_qwen_ta_dma_add.sv": _sha256_file(testbench),
        }

    passed = all(case["status"] == "pass" for case in cases)
    composition = vectors["composition"]
    body = {
        "build_id": vectors["build_id"],
        "cases": cases,
        "claim_boundary": vectors["claim_boundary"],
        "command_program_sha256": vectors["command_program_sha256"],
        "correlation": {
            "add_element_count": composition["add_element_count"],
            "add_output_payload_sha256": composition[
                "expected_output_payload_sha256"
            ],
            "add_sram_read_count": composition["add_element_count"] * 2,
            "add_sram_write_count": composition["add_element_count"],
            "command_indices": composition["submitted_command_indices"],
            "crc_fail_stop_cases": 1,
            "dma_hbm_bytes": len(bytes.fromhex(vectors["dma_payload_hex"])),
            "dma_hbm_request_count": 128,
            "dma_sram_write_count": 512,
            "hbm_response_fail_stop_cases": 1,
            "nonmonotonic_fail_stop_cases": 1,
            "shared_sram_address": composition["dma_destination_address"],
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
            str(VECTOR_BUILDER_PATH.relative_to(ROOT)): _sha256_file(
                VECTOR_BUILDER_PATH
            ),
            str(Path(__file__).resolve().relative_to(ROOT)): _sha256_file(
                Path(__file__).resolve()
            ),
            str(vectors_path.resolve().relative_to(ROOT)): _sha256_file(
                vectors_path
            ),
            **generated,
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
