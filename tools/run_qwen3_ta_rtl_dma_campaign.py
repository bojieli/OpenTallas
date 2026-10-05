#!/usr/bin/env python3
"""Correlate one authentic Qwen HBM-to-SRAM DMA command in two simulators."""

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


SCHEMA = "opentallas.tensor_accelerator.qwen_rtl_dma_campaign.v1"
VECTOR_SCHEMA = "opentallas.tensor_accelerator.qwen_rtl_dma_vectors.v1"
RTL_PATHS = (
    ROOT / "rtl/ot_ta_command_decoder.sv",
    ROOT / "rtl/ot_ta_dma_hbm_to_sram.sv",
)
CAMPAIGN_SCHEMA_PATH = (
    ROOT / "schemas/compiler/tensor_accelerator/qwen_rtl_dma_campaign_v1.schema.json"
)
VECTOR_SCHEMA_PATH = (
    ROOT / "schemas/compiler/tensor_accelerator/qwen_rtl_dma_vectors_v1.schema.json"
)
VECTOR_BUILDER_PATH = ROOT / "tools/build_qwen3_ta_rtl_dma_vectors.py"


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(
        description="Run Icarus and Verilator over an authentic Qwen DMA"
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
    compile_code, compile_log = _run(compile_command, cwd=ROOT, timeout=180)
    if compile_code == 0:
        run_code, run_log = _run(run_command, cwd=build, timeout=180)
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
    command = vectors["command"]
    fields = command["expected_fields"]
    size = vectors["hbm"]["size_bytes"]
    bursts = vectors["hbm"]["burst_count"]
    writes = vectors["sram"]["write_count"]
    return f"""`timescale 1ns/1ps
module tb_qwen_ta_dma;
    reg clk = 0;
    reg rst_n = 0;
    reg cmd_valid = 0;
    wire cmd_ready;
    reg [15:0] abi_major = 0;
    reg [15:0] abi_minor = 0;
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
    wire sram_write_valid;
    reg sram_write_ready = 0;
    wire [63:0] sram_write_address;
    wire [127:0] sram_write_data;
    wire [15:0] sram_write_byte_enable;
    wire done_valid;
    reg done_ready = 0;
    wire [7:0] done_error;
    wire [31:0] done_command_index;
    wire [31:0] done_hbm_request_count;
    wire [31:0] done_hbm_response_count;
    wire [31:0] done_hbm_bytes_read;
    wire [31:0] done_sram_write_count;
    wire [31:0] done_sram_bytes_written;

    reg [7:0] payload_mem [0:{size - 1}];
    reg [7:0] destination_mem [0:{size - 1}];
    reg model_clear = 0;
    reg fault_mode = 0;
    reg pending_response = 0;
    integer pending_burst = 0;
    integer pending_delay = 0;
    integer cycles = 0;
    integer request_count = 0;
    integer response_count = 0;
    integer write_count = 0;
    integer request_stalls = 0;
    integer write_stalls = 0;
    integer lane = 0;
    integer byte_index = 0;

    always #5 clk = ~clk;

    ot_ta_dma_hbm_to_sram dut (
        .clk(clk), .rst_n(rst_n), .cmd_valid(cmd_valid),
        .cmd_ready(cmd_ready), .abi_major(abi_major), .abi_minor(abi_minor),
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
        .sram_write_valid(sram_write_valid),
        .sram_write_ready(sram_write_ready),
        .sram_write_address(sram_write_address),
        .sram_write_data(sram_write_data),
        .sram_write_byte_enable(sram_write_byte_enable),
        .done_valid(done_valid), .done_ready(done_ready),
        .done_error(done_error), .done_command_index(done_command_index),
        .done_hbm_request_count(done_hbm_request_count),
        .done_hbm_response_count(done_hbm_response_count),
        .done_hbm_bytes_read(done_hbm_bytes_read),
        .done_sram_write_count(done_sram_write_count),
        .done_sram_bytes_written(done_sram_bytes_written)
    );

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            hbm_request_ready <= 0;
            hbm_response_valid <= 0;
            hbm_response_data <= 0;
            hbm_response_error <= 0;
            sram_write_ready <= 0;
            pending_response <= 0;
            pending_burst <= 0;
            pending_delay <= 0;
            cycles <= 0;
            request_count <= 0;
            response_count <= 0;
            write_count <= 0;
            request_stalls <= 0;
            write_stalls <= 0;
        end else if (model_clear) begin
            hbm_request_ready <= 0;
            hbm_response_valid <= 0;
            hbm_response_data <= 0;
            hbm_response_error <= 0;
            sram_write_ready <= 0;
            pending_response <= 0;
            pending_burst <= 0;
            pending_delay <= 0;
            cycles <= 0;
            request_count <= 0;
            response_count <= 0;
            write_count <= 0;
            request_stalls <= 0;
            write_stalls <= 0;
        end else begin
            cycles <= cycles + 1;
            hbm_request_ready <= (cycles % 5) != 1;
            sram_write_ready <= (cycles % 7) != 3;

            if (hbm_request_valid && !hbm_request_ready)
                request_stalls <= request_stalls + 1;
            if (sram_write_valid && !sram_write_ready)
                write_stalls <= write_stalls + 1;

            if (hbm_response_valid && hbm_response_ready) begin
                hbm_response_valid <= 0;
                hbm_response_error <= 0;
                response_count <= response_count + 1;
            end

            if (hbm_request_valid && hbm_request_ready) begin
                if (pending_response || hbm_response_valid)
                    $fatal(1, "more than one HBM request is outstanding");
                if (hbm_request_address !== 64'd{fields['source0']} +
                    request_count*64 || hbm_request_bytes !== 16'd64)
                    $fatal(1, "HBM request differs at %0d", request_count);
                pending_response <= 1;
                pending_burst <= request_count;
                pending_delay <= (request_count % 4) + 1;
                request_count <= request_count + 1;
            end

            if (pending_response) begin
                if (pending_delay == 0 && !hbm_response_valid) begin
                    for (lane = 0; lane < 64; lane = lane + 1)
                        hbm_response_data[lane*8 +: 8] <=
                            payload_mem[pending_burst*64 + lane];
                    hbm_response_error <= fault_mode ? 2'd1 : 2'd0;
                    hbm_response_valid <= 1;
                    pending_response <= 0;
                end else begin
                    pending_delay <= pending_delay - 1;
                end
            end

            if (sram_write_valid && sram_write_ready) begin
                if (fault_mode)
                    $fatal(1, "faulting HBM response modified SRAM");
                if (sram_write_address !== 64'd{fields['destination']} +
                    write_count*16 || sram_write_byte_enable !== 16'hffff)
                    $fatal(1, "SRAM write metadata differs at %0d", write_count);
                for (lane = 0; lane < 16; lane = lane + 1) begin
                    if (sram_write_data[lane*8 +: 8] !==
                        payload_mem[write_count*16 + lane])
                        $fatal(1, "SRAM write data differs at %0d", write_count);
                    destination_mem[write_count*16 + lane] <=
                        sram_write_data[lane*8 +: 8];
                end
                write_count <= write_count + 1;
            end

            if (cycles > {size * 16})
                $fatal(1, "DMA campaign timed out");
        end
    end

    task automatic run_hbm_fault;
        begin
            model_clear = 1;
            @(negedge clk);
            model_clear = 0;
            fault_mode = 1;
            while (!cmd_ready) @(negedge clk);
            cmd_valid = 1;
            @(negedge clk);
            cmd_valid = 0;
            while (!done_valid) @(negedge clk);
            if (done_error !== 8'd11 || done_hbm_request_count !== 1 ||
                done_hbm_response_count !== 1 || done_hbm_bytes_read !== 0 ||
                done_sram_write_count !== 0 ||
                done_sram_bytes_written !== 0 || request_count !== 1 ||
                response_count !== 1 || write_count !== 0 ||
                pending_response || hbm_response_valid || sram_write_valid)
                $fatal(1, "HBM fault completion differs");
            done_ready = 1;
            @(negedge clk);
            done_ready = 0;
            fault_mode = 0;
        end
    endtask

    initial begin
        $readmemh("payload.hex", payload_mem);
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
            done_hbm_request_count !== {bursts} ||
            done_hbm_response_count !== {bursts} ||
            done_hbm_bytes_read !== {size} ||
            done_sram_write_count !== {writes} ||
            done_sram_bytes_written !== {size} ||
            request_count !== {bursts} || response_count !== {bursts} ||
            write_count !== {writes} || request_stalls == 0 ||
            write_stalls == 0 || pending_response || hbm_response_valid)
            $fatal(1, "DMA completion or transaction counters differ");
        for (byte_index = 0; byte_index < {size}; byte_index = byte_index + 1)
            if (destination_mem[byte_index] !== payload_mem[byte_index])
                $fatal(1, "destination SRAM differs at byte %0d", byte_index);
        repeat (3) begin
            @(negedge clk);
            if (!done_valid || done_hbm_bytes_read !== {size} ||
                done_sram_bytes_written !== {size})
                $fatal(1, "DMA completion was not stable under backpressure");
        end
        done_ready = 1;
        @(negedge clk);
        done_ready = 0;
        run_hbm_fault();
        $display("PASS: Qwen DMA RTL bytes={size} hbm_requests={bursts} sram_writes={writes} faults=1 vector_set={vectors['vector_set_id']}");
        $finish;
    end
endmodule
"""


def _harness(vectors: dict[str, Any]) -> str:
    command = vectors["command"]
    fields = command["expected_fields"]
    size = vectors["hbm"]["size_bytes"]
    bursts = vectors["hbm"]["burst_count"]
    writes = vectors["sram"]["write_count"]
    record = int(command["record_hex"], 16)
    words = ", ".join(
        f"0x{(record >> (index * 32)) & 0xffffffff:08x}U" for index in range(16)
    )
    return f"""#include "Vot_ta_dma_hbm_to_sram.h"
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
constexpr uint32_t kSize = {size}U;
constexpr uint32_t kBursts = {bursts}U;
constexpr uint32_t kWrites = {writes}U;
constexpr uint64_t kHbmBase = {fields['source0']}ULL;
constexpr uint64_t kSramBase = {fields['destination']}ULL;
constexpr std::array<uint32_t, 16> kCommand = {{{{{words}}}}};

[[noreturn]] void fail(const std::string& message) {{
    std::cerr << "FAIL: " << message << "\\n";
    std::exit(1);
}}

void require(bool condition, const std::string& message) {{
    if (!condition) fail(message);
}}

std::vector<uint8_t> load_hex(const char* path) {{
    std::ifstream stream(path);
    if (!stream) fail(std::string("cannot open ") + path);
    std::vector<uint8_t> result;
    uint32_t value = 0;
    while (stream >> std::hex >> value) {{
        if (value > 0xffU) fail(std::string("wide value in ") + path);
        result.push_back(static_cast<uint8_t>(value));
    }}
    if (result.size() != kSize) fail(std::string("count differs in ") + path);
    return result;
}}

void eval_low(Vot_ta_dma_hbm_to_sram& dut) {{
    dut.clk = 0;
    dut.eval();
}}

void tick(Vot_ta_dma_hbm_to_sram& dut) {{
    dut.clk = 1;
    dut.eval();
    dut.clk = 0;
    dut.eval();
}}

void set_response(Vot_ta_dma_hbm_to_sram& dut,
                  const std::vector<uint8_t>& payload, uint32_t burst) {{
    for (uint32_t word = 0; word < 16U; ++word) {{
        uint32_t value = 0;
        for (uint32_t lane = 0; lane < 4U; ++lane)
            value |= static_cast<uint32_t>(payload[burst * 64U + word * 4U + lane])
                     << (lane * 8U);
        dut.hbm_response_data[word] = value;
    }}
}}

}}  // namespace

int main(int argc, char** argv) {{
    Verilated::commandArgs(argc, argv);
    Vot_ta_dma_hbm_to_sram dut;
    const auto payload = load_hex("payload.hex");
    std::vector<uint8_t> destination(kSize, 0xffU);

    dut.rst_n = 0;
    dut.cmd_valid = 0;
    dut.hbm_request_ready = 0;
    dut.hbm_response_valid = 0;
    dut.hbm_response_error = 0;
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
    uint32_t pending_burst = 0;
    uint32_t pending_delay = 0;
    bool response_valid = false;
    uint32_t request_count = 0;
    uint32_t response_count = 0;
    uint32_t write_count = 0;
    uint32_t request_stalls = 0;
    uint32_t write_stalls = 0;
    uint32_t cycles = 0;
    while (!dut.done_valid) {{
        const bool request_ready = (cycles % 5U) != 1U;
        const bool write_ready = (cycles % 7U) != 3U;
        dut.hbm_request_ready = request_ready;
        dut.hbm_response_valid = response_valid;
        dut.hbm_response_error = 0;
        dut.sram_write_ready = write_ready;
        eval_low(dut);
        const bool request_fire = dut.hbm_request_valid && request_ready;
        const bool response_fire = response_valid && dut.hbm_response_ready;
        const bool write_fire = dut.sram_write_valid && write_ready;
        if (dut.hbm_request_valid && !request_ready) ++request_stalls;
        if (dut.sram_write_valid && !write_ready) ++write_stalls;
        if (request_fire) {{
            require(!pending && !response_valid,
                    "more than one HBM request is outstanding");
            require(dut.hbm_request_address == kHbmBase + request_count * 64ULL &&
                        dut.hbm_request_bytes == 64U,
                    "HBM request differs at " + std::to_string(request_count));
        }}
        if (write_fire) {{
            require(write_count < kWrites,
                    "too many SRAM writes");
            require(dut.sram_write_address == kSramBase + write_count * 16ULL &&
                        dut.sram_write_byte_enable == 0xffffU,
                    "SRAM write metadata differs at " +
                        std::to_string(write_count));
            for (uint32_t lane = 0; lane < 16U; ++lane) {{
                const uint32_t word = lane / 4U;
                const uint32_t shift = (lane % 4U) * 8U;
                const uint8_t value =
                    static_cast<uint8_t>(dut.sram_write_data[word] >> shift);
                require(value == payload[write_count * 16U + lane],
                        "SRAM write data differs at " +
                            std::to_string(write_count));
                destination[write_count * 16U + lane] = value;
            }}
        }}

        const bool pending_before = pending;
        tick(dut);
        if (response_fire) {{
            response_valid = false;
            ++response_count;
        }}
        if (pending_before) {{
            if (pending_delay == 0U && !response_valid) {{
                set_response(dut, payload, pending_burst);
                response_valid = true;
                pending = false;
            }} else {{
                --pending_delay;
            }}
        }}
        if (request_fire) {{
            pending = true;
            pending_burst = request_count;
            pending_delay = (request_count % 4U) + 1U;
            ++request_count;
        }}
        if (write_fire) ++write_count;
        if (++cycles > kSize * 16U) fail("DMA campaign timed out");
    }}
    require(dut.done_error == 0 &&
                dut.done_command_index == {command['expected_index']}U,
            "DMA completion identity differs");
    require(dut.done_hbm_request_count == kBursts &&
                dut.done_hbm_response_count == kBursts &&
                dut.done_hbm_bytes_read == kSize && request_count == kBursts &&
                response_count == kBursts,
            "HBM completion counters differ");
    require(dut.done_sram_write_count == kWrites &&
                dut.done_sram_bytes_written == kSize && write_count == kWrites,
            "SRAM completion counters differ");
    require(request_stalls > 0 && write_stalls > 0,
            "DMA stalls were not exercised");
    require(!pending && !response_valid,
            "HBM response remained outstanding at completion");
    require(destination == payload, "destination SRAM payload differs");
    for (unsigned hold = 0; hold < 3; ++hold) {{
        tick(dut);
        require(dut.done_valid && dut.done_hbm_bytes_read == kSize &&
                    dut.done_sram_bytes_written == kSize,
                "DMA completion was not stable under backpressure");
    }}
    dut.done_ready = 1;
    tick(dut);
    dut.done_ready = 0;

    for (unsigned wait = 0; !dut.cmd_ready && wait < 8; ++wait) tick(dut);
    require(dut.cmd_ready, "fault command interface was not ready");
    dut.cmd_valid = 1;
    eval_low(dut);
    tick(dut);
    dut.cmd_valid = 0;
    bool fault_pending = false;
    bool fault_response_valid = false;
    uint32_t fault_delay = 0;
    uint32_t fault_requests = 0;
    uint32_t fault_responses = 0;
    uint32_t fault_cycles = 0;
    while (!dut.done_valid) {{
        dut.hbm_request_ready = (fault_cycles % 3U) != 1U;
        dut.hbm_response_valid = fault_response_valid;
        dut.hbm_response_error = fault_response_valid ? 1U : 0U;
        dut.sram_write_ready = 1;
        eval_low(dut);
        require(!dut.sram_write_valid,
                "faulting HBM response attempted to modify SRAM");
        const bool request_fire = dut.hbm_request_valid && dut.hbm_request_ready;
        const bool response_fire = fault_response_valid &&
                                   dut.hbm_response_ready;
        require(!request_fire || (!fault_pending && !fault_response_valid),
                "fault path issued multiple HBM requests");
        if (request_fire)
            require(dut.hbm_request_address == kHbmBase &&
                        dut.hbm_request_bytes == 64U,
                    "fault HBM request differs");
        tick(dut);
        if (response_fire) {{
            fault_response_valid = false;
            ++fault_responses;
        }}
        if (fault_pending) {{
            if (fault_delay == 0U && !fault_response_valid) {{
                set_response(dut, payload, 0);
                fault_response_valid = true;
                fault_pending = false;
            }} else {{
                --fault_delay;
            }}
        }}
        if (request_fire) {{
            fault_pending = true;
            fault_delay = 2;
            ++fault_requests;
        }}
        if (++fault_cycles > 64U) fail("fault DMA command timed out");
    }}
    require(dut.done_error == 11U && dut.done_hbm_request_count == 1U &&
                dut.done_hbm_response_count == 1U &&
                dut.done_hbm_bytes_read == 0U &&
                dut.done_sram_write_count == 0U &&
                dut.done_sram_bytes_written == 0U && fault_requests == 1U &&
                fault_responses == 1U && !fault_pending &&
                !fault_response_valid,
            "HBM fault completion differs");
    dut.done_ready = 1;
    tick(dut);
    dut.final();
    std::cout << "PASS: Qwen DMA RTL bytes={size} hbm_requests={bursts} "
              << "sram_writes={writes} faults=1 "
              << "vector_set={vectors['vector_set_id']}\\n";
    return 0;
}}
"""


def _write_payload(path: Path, payload_hex: str) -> None:
    path.write_text(
        "".join(f"{value:02x}\n" for value in bytes.fromhex(payload_hex)),
        encoding="ascii",
    )


def run(vectors_path: Path) -> dict[str, Any]:
    vectors = load_strict_json(vectors_path)
    vector_schema = load_strict_json(VECTOR_SCHEMA_PATH)
    Draft202012Validator.check_schema(vector_schema)
    Draft202012Validator(vector_schema).validate(vectors)
    if vectors.get("schema") != VECTOR_SCHEMA or vectors.get(
        "vector_set_id"
    ) != _body_id(vectors, "vector_set_id"):
        raise ValueError("Qwen RTL DMA vector identity differs")
    size = vectors["hbm"]["size_bytes"]
    bursts = vectors["hbm"]["burst_count"]
    writes = vectors["sram"]["write_count"]
    marker = (
        f"PASS: Qwen DMA RTL bytes={size} hbm_requests={bursts} "
        f"sram_writes={writes} faults=1 vector_set={vectors['vector_set_id']}"
    )
    with tempfile.TemporaryDirectory(prefix="opentallas-qwen-ta-dma-") as tmp:
        build = Path(tmp)
        testbench = build / "tb_qwen_ta_dma.sv"
        harness = build / "qwen_ta_dma_harness.cpp"
        payload = build / "payload.hex"
        testbench.write_text(_testbench(vectors), encoding="utf-8")
        harness.write_text(_harness(vectors), encoding="utf-8")
        _write_payload(payload, vectors["hbm"]["payload_hex"])
        iverilog_binary = build / "qwen_ta_dma.vvp"
        verilator_dir = build / "verilator"
        cases = [
            _case(
                "iverilog",
                [
                    "iverilog",
                    "-g2012",
                    "-Wall",
                    "-s",
                    "tb_qwen_ta_dma",
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
                    "ot_ta_dma_hbm_to_sram",
                    "--Mdir",
                    str(verilator_dir),
                    *(str(path) for path in RTL_PATHS),
                    str(harness),
                    "-CFLAGS",
                    "-std=c++17",
                ],
                [str(verilator_dir / "Vot_ta_dma_hbm_to_sram")],
                build=build,
                marker=marker,
            ),
        ]
        generated = {
            "generated/payload.hex": _sha256_file(payload),
            "generated/qwen_ta_dma_harness.cpp": _sha256_file(harness),
            "generated/tb_qwen_ta_dma.sv": _sha256_file(testbench),
        }
    passed = all(case["status"] == "pass" for case in cases)
    fields = vectors["command"]["expected_fields"]
    body = {
        "build_id": vectors["build_id"],
        "cases": cases,
        "claim_boundary": vectors["claim_boundary"],
        "command_program_sha256": vectors["command_program_sha256"],
        "correlation": {
            "command_index": vectors["command"]["expected_index"],
            "expected_payload_sha256": vectors["hbm"]["payload_sha256"],
            "hbm_address": fields["source0"],
            "hbm_burst_bytes": vectors["hbm"]["burst_bytes"],
            "hbm_bytes_read": size,
            "hbm_error_cases": 1,
            "hbm_request_count": bursts,
            "maximum_outstanding_hbm_requests": 1,
            "sram_address": fields["destination"],
            "sram_bytes_written": size,
            "sram_word_bytes": vectors["sram"]["word_bytes"],
            "sram_write_count": writes,
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
