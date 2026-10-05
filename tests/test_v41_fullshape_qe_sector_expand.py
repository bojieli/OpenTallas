"""Source-pinned packed FP8/FP4 sector-to-QE-port RTL gate."""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import numpy as np
import pytest

from tools import v41_fullshape_qe_stream_image as Q


def _words(name: str):
    source = Q.ROOT / "results/rtl/hdc_v41x_fullshape_200k_l0_rank0_image.json"
    folder = Path("/tmp/codex_v41_fullshape_golden/images/ctx200000_L00_r0")
    manifest = json.loads(source.read_text())
    codes, scales, fp4 = Q.source_matrix(manifest, folder, name)
    logical, packed, geometry = Q.pack_stream(codes, scales, fp4)
    Q.verify_stream(logical, packed, codes, scales, geometry)
    return logical, packed, fp4


def test_packed_sector_expansion_matches_real_checkpoint(tmp_path: Path):
    if not shutil.which("iverilog"):
        pytest.skip("iverilog unavailable")
    if not Path("/tmp/codex_v41_fullshape_golden/images/ctx200000_L00_r0/w.wq_a.bin").is_file():
        pytest.skip("source-pinned full-shape checkpoint scratch unavailable")
    vectors = []
    for name in ("wq_a", "exp110.w1"):
        logical, packed, fp4 = _words(name)
        for index in (0, len(logical)//2, len(logical)-1):
            vectors.append((packed[index].tobytes(), logical[index].tobytes(), fp4))
    body = []
    for i, (packed, expected, fp4) in enumerate(vectors):
        body.append(f"""
        in_valid = 1; in_fp4 = 1'b{int(fp4)};
        in_sector_valid = 17'h{0x1ff if fp4 else 0x1ffff:x};
        in_packed = 4352'h{int.from_bytes(packed, 'little'):x};
        #1;
        if (!out_valid || out_fault || out_word !== 4352'h{int.from_bytes(expected, 'little'):x})
            $fatal(1, "real word {i} mismatch");
        in_sector_valid = 0; #1;
        if (out_valid || !out_fault || out_word !== 4352'b0)
            $fatal(1, "missing-sector fail-closed {i}");
        """)
    tb = tmp_path / "tb.sv"
    tb.write_text("""`timescale 1ns/1ps
module tb;
reg in_valid, in_fp4;
reg [16:0] in_sector_valid;
reg [4351:0] in_packed;
wire out_valid, out_fault;
wire [4351:0] out_word;
ot_hdc_v41x_qe_sector_expand dut(.*);
initial begin
""" + "\n".join(body) + "\n$display(\"PASS QE sector expansion\"); $finish; end\nendmodule\n")
    exe = tmp_path / "sim"
    source = Q.ROOT / "rtl/hdc/v41x/ot_hdc_v41x_qe_sector_expand.sv"
    subprocess.run(["iverilog", "-g2012", "-s", "tb", "-o", str(exe), str(source), str(tb)],
                   check=True, capture_output=True, text=True)
    run = subprocess.run(["vvp", str(exe)], check=True, capture_output=True, text=True)
    assert "PASS QE sector expansion" in run.stdout


def test_fp4_expansion_scale_and_nibble_order(tmp_path: Path):
    """Independent hand vector: low nibble first and signed exponent kept."""
    if not shutil.which("iverilog"):
        pytest.skip("iverilog unavailable")
    raw = bytearray(288)
    raw[0] = 0xA3
    raw[16:18] = (-6).to_bytes(2, "little", signed=True)
    exp = bytearray(544)
    exp[0:2] = bytes((3, 10))
    exp[32:34] = raw[16:18]
    tb = tmp_path / "tb.sv"
    tb.write_text(f"""`timescale 1ns/1ps
module tb;
reg in_valid=1, in_fp4=1;
reg [16:0] in_sector_valid=17'h1ff;
reg [4351:0] in_packed=4352'h{int.from_bytes(raw,'little'):x};
wire out_valid, out_fault;
wire [4351:0] out_word;
ot_hdc_v41x_qe_sector_expand dut(.*);
initial begin #1;
 if (!out_valid || out_fault || out_word !== 4352'h{int.from_bytes(exp,'little'):x})
   $fatal(1,"FP4 hand vector");
 $finish; end
endmodule
""")
    exe = tmp_path / "sim"
    subprocess.run(["iverilog", "-g2012", "-s", "tb", "-o", str(exe),
                    str(Q.ROOT / "rtl/hdc/v41x/ot_hdc_v41x_qe_sector_expand.sv"), str(tb)], check=True)
    subprocess.run(["vvp", str(exe)], check=True)
