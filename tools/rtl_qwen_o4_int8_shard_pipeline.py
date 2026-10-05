#!/usr/bin/env python3
"""Check ROM-word capture, signed INT8 decode and request/result alignment."""
from __future__ import annotations

import hashlib
import json
import pathlib
import struct
import subprocess
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
SOURCES = (
    "physical/asap7_memory_macros/ot_rom_8192x266_m8/ot_rom_8192x266_m8.v",
    "physical/qwen_o4_int8_shard/ot_qwen_o4_int8_shard.sv",
    "rtl/hdc/ot_hdc_qwen_int8_arith.sv",
    "rtl/hdc/ot_hdc_fpu.sv",
    "rtl/hdc/ot_hdc_fp32_mul_pipe.sv",
    "rtl/test/tb_qwen_o4_int8_shard_pipeline.sv",
)
HASH_SOURCES = SOURCES + ("tools/rtl_qwen_o4_int8_shard_pipeline.py",)


def f32_bits(value: float) -> int:
    return struct.unpack(">I", struct.pack(">f", value))[0]


def main() -> None:
    # Eight addresses share one physical 2,128-bit ROM row (mux eight).
    # This exercises changing address, lane and activation every cycle.
    row = 0
    codes: dict[tuple[int, int], int] = {}
    for addr in range(8):
        for lane in range(32):
            code = (addr * 37 + lane * 29) & 255
            if (addr, lane) == (7, 31):
                code = 128
            codes[addr, lane] = code
            for bit in range(8):
                row |= ((code >> bit) & 1) << ((8 * lane + bit) * 8 + addr)
    x_bits = (0x3F80, 0xBF80, 0x4000, 0x3F00, 0x3FC0, 0x0000)
    requests = []
    for i in range(128):
        ce = int(i < 64 or i % 4 != 3)
        addr = i % 8
        lane = (i * 13) % 32
        if i == 62:
            addr, lane = 7, 31
        x0 = x_bits[i % len(x_bits)]
        x1 = x_bits[(i + 2) % len(x_bits)]
        x = x0 if lane < 16 else x1
        code = codes[addr, lane]
        signed = code if code < 128 else code - 256
        xvalue = struct.unpack(">f", struct.pack(">I", x << 16))[0]
        product = f32_bits(signed * xvalue)
        if signed == 0 or xvalue == 0:
            product = 0  # canonical +0, including negative zero inputs
        word = ((((((ce << 13) | addr) << 16 | x1) << 16 | x0) << 5 | lane) << 32) | product
        requests.append(f"{word:021x}")

    with tempfile.TemporaryDirectory(prefix="qwen-o4-rom-pipe-") as scratch:
        work = pathlib.Path(scratch)
        # $readmemh accepts a short image; the ROM initializes other rows to 0.
        (work / "via.mem").write_text(f"{row:0532x}\n")
        (work / "requests.mem").write_text("\n".join(requests) + "\n")
        exe = work / "obj" / "Vtb_qwen_o4_int8_shard_pipeline"
        compile_result = subprocess.run(
            ["/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin/verilator", "--binary", "--timing", "-Wno-fatal",
             "--top-module", "tb_qwen_o4_int8_shard_pipeline", "--Mdir", str(work / "obj"),
             "-j", "4", *(str(ROOT / s) for s in SOURCES)],
            capture_output=True, text=True,
        )
        if compile_result.returncode:
            raise RuntimeError(compile_result.stdout + compile_result.stderr)
        run = subprocess.run([str(exe)], cwd=work, capture_output=True, text=True)
        if run.returncode or "PASS Qwen INT8 ROM shard" not in run.stdout:
            raise RuntimeError(run.stdout + run.stderr)
        print(run.stdout.strip())

    record = {
        "schema": "qwen-o4-int8-rom-shard-pipeline/1",
        "scope": "one analytical 266-bit ROM, 32 INT8 product lanes, streamed addresses/lane selects",
        "exact_products": 112,
        "request_to_result_edges": 7,
        "initiation_interval_cycles": 1,
        "sources_sha256": {s: hashlib.sha256((ROOT / s).read_bytes()).hexdigest() for s in HASH_SOURCES},
    }
    output = ROOT / "results/rtl/qwen_o4_int8_rom_shard_pipeline.json"
    output.write_text(json.dumps(record, indent=2) + "\n")
    print(output.relative_to(ROOT))


if __name__ == "__main__":
    main()
