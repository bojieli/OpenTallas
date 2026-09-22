#!/usr/bin/env python3
"""Exercise lane numerical/fault vectors through variable-latency bundle service."""

from pathlib import Path
import argparse
import os
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.rtl_abi3_lane_campaign import RTL_SOURCES  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--suite", choices=["d1", "groups"], default="groups")
    ap.add_argument("--build", type=Path, default=ROOT / "build/runtime_lane_bundle")
    args = ap.parse_args()
    out = args.build.resolve()
    out.mkdir(parents=True, exist_ok=True)
    top = (ROOT / "rtl/test/a3_lane_pipelined_top.sv").read_text()
    for line in top.splitlines():
        if "if (d_" in line and "rd" not in line and "<=" in line:
            # Only four DUT operand memory read assignments; reference ports
            # and result capture remain unmodified.
            if any(f"d_{p}_data <=" in line for p in ["a", "b", "s", "t"]):
                top = top.replace(line, "")
    # The source aligns spaces differently on the scale assignments.
    import re

    top = re.sub(
        r"^\s*if \(d_[abst]_en[^\n]*d_[abst]_data\s*<=.*$", "", top, flags=re.M
    )
    top = top.replace(
        "reg  [63:0] d_a_data, d_b_data;", "wire [63:0] d_a_data, d_b_data;"
    )
    top = top.replace(
        "reg  [31:0] d_s_data, d_t_data;", "wire [31:0] d_s_data, d_t_data;"
    )
    adapter = """
    wire lane_request,lane_issue,lane_credit,svc_valid,rsp_ready;
    wire [31:0] preview_a,preview_b,preview_s,preview_t;
    wire [127:0] svc_addr;
    wire [191:0] bundle;
    reg [191:0] rsp_data=0;
    reg rsp_valid=0,pending=0;
    reg [7:0] ticks=0;
    reg [3:0] delay_left=0;
    integer requests=0,responses=0,issues=0;
    wire svc_ready=!pending && !rsp_valid && ticks[1:0]!=0;
    assign {d_t_data,d_s_data,d_b_data,d_a_data}=bundle;
    ot_a3_operand_bundle_bridge bridge(
      .clk(clk),.rst_n(rst_n),.clear(start_dut),
      .lane_request(lane_request),.lane_address({preview_t,preview_s,preview_b,preview_a}),
      .lane_issue(lane_issue),.lane_credit(lane_credit),.lane_data(bundle),
      .service_valid(svc_valid),.service_ready(svc_ready),.service_address(svc_addr),
      .response_valid(rsp_valid),.response_ready(rsp_ready),.response_data(rsp_data));
    always @(posedge clk) begin
      if(!rst_n || start_dut) begin
        ticks<=0;pending<=0;rsp_valid<=0;delay_left<=0;
      end else begin
        ticks<=ticks+1'b1;
        if(svc_valid && svc_ready) begin
          rsp_data<={m3_mem[svc_addr[127:96]],m2_mem[svc_addr[95:64]],
                    m1_mem[svc_addr[63:32]],m0_mem[svc_addr[31:0]]};
          pending<=1;delay_left<={1'b0,ticks[2:0]}+1'b1;
          requests<=requests+1;
        end
        if(pending) begin
          if(delay_left==0) begin pending<=0;rsp_valid<=1;end
          else delay_left<=delay_left-1'b1;
        end
        if(rsp_valid && rsp_ready) begin rsp_valid<=0;responses<=responses+1;end
        if(lane_issue) begin
          if(!lane_credit)$fatal(1,"issue without bundle reservation");
          issues<=issues+1;
        end
      end
    end
    final begin
      if(issues==0 || issues>responses || responses>requests)$fatal(1,"bundle accounting");
      $display("BUNDLES requests=%0d responses=%0d issues=%0d",requests,responses,issues);
    end
"""
    top = top.replace(
        "    ot_a3_lane_pipelined #(", adapter + "\n    ot_a3_lane_pipelined #("
    )
    top = top.replace(
        ".ACC_SLOTS(ACC_SLOTS)", ".ACC_SLOTS(ACC_SLOTS), .OPERAND_CREDITS(1)"
    )
    top = top.replace(
        ".start(start_dut),",
        """.start(start_dut),.operand_credit(lane_credit),
        .operand_request(lane_request),.operand_issue(lane_issue),
        .operand_a_addr(preview_a),.operand_b_addr(preview_b),
        .operand_s_addr(preview_s),.operand_t_addr(preview_t),""",
    )
    (out / "top.sv").write_text(top)
    subprocess.run(
        [
            sys.executable,
            str(ROOT / "tools/build_abi3_lane_vectors.py"),
            "--suite",
            args.suite,
            "--out-dir",
            str(out),
            "--profile",
            "quick",
        ],
        check=True,
        cwd=ROOT,
        stdout=subprocess.DEVNULL,
    )
    tool = (
        Path(
            os.environ.get(
                "OPENTALLAS_TOOL_ROOT", Path.home() / ".local/opentallas-tools"
            )
        )
        / "verilator-5.050/bin/verilator"
    )
    sources = [
        ROOT / p
        for p in (
            *RTL_SOURCES,
            "rtl/proto/ot_fp32_add_rne_pipe.sv",
            "rtl/proto/ot_fp32_mul_rne_pipe.sv",
            "rtl/abi3/ot_a3_operand_bundle_bridge.sv",
        )
    ]
    with (out / "compile.log").open("w") as log:
        subprocess.run(
            [
                str(tool),
                "--binary",
                "--timing",
                "-Wno-fatal",
                "--top-module",
                "tb_a3_lane_pipelined",
                "--Mdir",
                str(out / "obj"),
                "-o",
                "sim",
                *map(str, sources),
                str(out / "top.sv"),
                str(ROOT / "rtl/test/tb_a3_lane_pipelined.sv"),
            ],
            stdout=log,
            stderr=subprocess.STDOUT,
            check=True,
        )
    result = subprocess.run(
        [str(out / "obj/sim")], cwd=out, capture_output=True, text=True, timeout=120
    )
    (out / "simulation.log").write_text(result.stdout + result.stderr)
    if (
        result.returncode
        or "FAIL" in result.stdout
        or "PASS: ABI3 pipelined lane" not in result.stdout
    ):
        raise SystemExit((result.stdout + result.stderr)[-6000:])
    print(
        "\n".join(
            line
            for line in result.stdout.splitlines()
            if line.startswith(("PASS:", "BUNDLES", "checks="))
        )
    )


if __name__ == "__main__":
    main()
