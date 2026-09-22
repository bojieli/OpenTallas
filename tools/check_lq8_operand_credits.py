#!/usr/bin/env python3
"""Run the existing LQ8 quick corpus with deterministic shared operand stalls.

Writes generated bench, images and simulation log under build/runtime_credit_array.
This checks array numerical/fault/lockstep behavior, not SRAM integration.
"""

import sys
from pathlib import Path
import subprocess

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.rtl_abi3_lq8_campaign import RTL_SOURCES  # noqa: E402

root = Path(__file__).resolve().parents[1]
out = root / "build/runtime_credit_array"
out.mkdir(parents=True, exist_ok=True)
s = (root / "rtl/test/a3_lq8_top.sv").read_text()
s = s.replace(
    "    ot_a3_lq8 #(",
    """
    reg [15:0] ticks=0;
    always @(posedge clk) if(!rst_n || start_dut) ticks<=0; else ticks<=ticks+1'b1;
    wire credit = ticks>80 && ticks[5:0]<32 && ticks[1:0]!=0;
    ot_a3_lq8 #(""",
)
s = s.replace(
    ".ACC_SLOTS(ACC_SLOTS)\n    ) u_dut",
    ".ACC_SLOTS(ACC_SLOTS), .OPERAND_CREDITS(1)\n    ) u_dut",
)
s = s.replace(".start(start_dut),", ".start(start_dut), .operand_credit(credit),")
(out / "top.sv").write_text(s)
subprocess.run(
    [
        "python3",
        "tools/build_abi3_lq8_vectors.py",
        "--out-dir",
        str(out),
        "--profile",
        "quick",
    ],
    check=True,
    cwd=root,
    stdout=subprocess.DEVNULL,
)
subprocess.run(
    [
        "iverilog",
        "-g2012",
        "-s",
        "tb_a3_lq8",
        "-o",
        str(out / "sim"),
        *[str(root / p) for p in RTL_SOURCES],
        str(out / "top.sv"),
        str(root / "rtl/test/tb_a3_lq8.sv"),
    ],
    check=True,
)
with (out / "simulation.log").open("w") as f:
    subprocess.run(
        ["vvp", str(out / "sim")],
        cwd=out,
        stdout=f,
        stderr=subprocess.STDOUT,
        check=True,
        timeout=600,
    )
log = (out / "simulation.log").read_text()
if "FAIL" in log or "PASS:" not in log:
    raise SystemExit(log[-4000:])
print(log[-2000:])
