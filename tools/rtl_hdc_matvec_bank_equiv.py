#!/usr/bin/env python3
"""Compare the banked Qwen matvec against its pinned pre-refactor RTL.

The historical RTL is retrieved from git at run time, so this gate does not
add a second production matvec file. It exercises complete split operations
at G=4 and G=64, including the last active row and inactive output groups.
"""
import argparse
import hashlib
import json
import re
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = "a4870d3b"
SOURCES = [
    "rtl/hdc/ot_hdc_matvec.sv", "rtl/hdc/ot_hdc_fpu.sv",
    "rtl/hdc/ot_hdc_fp32_mul_pipe.sv", "rtl/hdc/ot_hdc_fastfp.sv",
    "rtl/hdc/ot_hdc_delay.sv", "rtl/hdc/ot_hdc_sfu.sv",
    "rtl/proto/ot_fp32_add_rne_pipe.sv",
]


def digest(data):
    return hashlib.sha256(data).hexdigest()


OUTPUTS = {
    "ready": "", "idle": "", "wrom_re": "", "wrom_addr": "[23:0]",
    "scale_re": "", "scale_gre": "[G-1:0]", "scale_addr": "[G*24-1:0]",
    "kv_re": "", "kv_addr": "[G*24-1:0]", "x_re": "[G-1:0]",
    "x_addr": "[G*24-1:0]", "ov": "", "o_we": "[G-1:0]",
    "o_addr": "[G*24-1:0]", "o_mask": "[G*W-1:0]",
    "o_data": "[G*W*32-1:0]", "am_idx": "[15:0]", "am_val": "[31:0]",
    "am_any": "", "mx_we": "", "mx_addr": "[23:0]",
    "mx_mask": "[W-1:0]", "mx_data": "[W*32-1:0]",
    "progress": "[15:0]", "fault": "",
}

INPUTS = {
    "clk": "clk", "rst_n": "rst_n", "go": "go", "i_nout": "nout",
    "i_tiles": "16'd1", "i_k": "16'd2", "i_wsrc": "1'b0",
    "i_wbase": "24'd100", "i_ts": "24'd0", "i_ks": "24'd0",
    "i_js": "24'd0", "i_xbase": "24'd0", "i_xks": "24'd0",
    "i_xjs": "24'd0", "i_xcs": "24'd0", "i_jsh": "3'd0",
    "i_split": "split", "i_wcs": "24'd0", "i_round": "1'b1",
    "i_obase": "24'd0", "i_ots": "24'd8", "i_ojs": "24'd1",
    "i_mmode": "1'b0", "i_oen": "1'b1", "i_amax": "1'b1",
    "i_rmax": "1'b0", "i_mbase": "24'd0", "wrom_q": "wrom_q",
    "scale_q": "scale_q", "kv_q": "{G*W*32{1'b0}}", "x_q": "x_q",
}


def testbench():
    decls = "\n".join(
        f"  wire {width} {prefix}_{name};"
        for prefix in ("ref", "dut") for name, width in OUTPUTS.items())
    instances = []
    for prefix, module in (("ref", "ot_hdc_matvec_ref"),
                           ("dut", "ot_hdc_matvec")):
        ports = {**INPUTS, **{name: f"{prefix}_{name}" for name in OUTPUTS}}
        binds = ",\n".join(f"    .{name}({value})" for name, value in ports.items())
        instances.append(f"  {module} #(.G(G),.W(W),.IL(8),.INT8_WEIGHT(1)) u_{prefix} (\n{binds}\n  );")
    checks = "\n".join(
        f"    if (ref_{name} !== dut_{name}) $fatal(1, \"G=%0d split=%0d nout=%0d cycle=%0d {name} differs\", G, split, nout, cycle);"
        for name in OUTPUTS)
    return f'''`timescale 1ns/1ps
module tb_hdc_matvec_bank_equiv;
  parameter integer G = 4;
  localparam integer W = 16;
  reg clk=0, rst_n=0, go=0;
  reg [3:0] split=0;
  reg [15:0] nout=1;
  integer cycle=0, cases=0;
  always #5 clk=~clk;
  wire [G*W*8-1:0] wrom_q = {{G*W{{8'h01}}}};
  wire [G*W*16-1:0] scale_q = {{G*W{{16'h3F80}}}};
  wire [G*32-1:0] x_q = {{G{{32'h3F800000}}}};
{decls}
{chr(10).join(instances)}
  always @(negedge clk) if (rst_n) begin
    cycle=cycle+1;
{checks}
  end
  task run_case(input integer s, input integer rows);
    begin
      @(negedge clk); rst_n=0; go=0;
      repeat (4) @(negedge clk);
      split=s[3:0]; nout=rows[15:0]; rst_n=1;
      @(negedge clk); go=1;
      @(negedge clk); go=0;
      repeat (120) @(negedge clk);
      cases=cases+1;
    end
  endtask
  integer s;
  initial begin
    for (s=0; s<=$clog2(G); s=s+1) begin
      run_case(s,1);
      if ((G>>s)>0) run_case(s,(G>>s)*W*8-1);
    end
    $display("PASS bank equivalence G=%0d cases=%0d cycles=%0d",G,cases,cycle);
    $finish;
  end
  initial begin #1000000; $fatal(1,"equivalence timeout"); end
endmodule
'''


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--groups", type=int, choices=(4, 64), required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    original = subprocess.check_output(
        ["git", "show", f"{BASE}:rtl/hdc/ot_hdc_matvec.sv"], cwd=ROOT)
    old = original.decode()
    old, count = re.subn(r"\bmodule ot_hdc_matvec\b", "module ot_hdc_matvec_ref", old, count=1)
    if count != 1:
        raise RuntimeError("pinned reference module not found")
    with tempfile.TemporaryDirectory(prefix="qwen_bank_equiv_") as temp:
        temp = Path(temp)
        (temp / "reference.sv").write_text(old)
        (temp / "tb.sv").write_text(testbench())
        cmd = ["iverilog", "-g2012", "-s", "tb_hdc_matvec_bank_equiv",
               f"-Ptb_hdc_matvec_bank_equiv.G={args.groups}", "-o", str(temp / "sim.vvp"),
               str(temp / "tb.sv"), str(temp / "reference.sv"),
               *map(lambda s: str(ROOT / s), SOURCES)]
        compile_run = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True)
        sim_run = subprocess.run(["vvp", str(temp / "sim.vvp")], cwd=ROOT,
                                 text=True, capture_output=True) if compile_run.returncode == 0 else None
        (args.out / "compile.log").write_text(compile_run.stdout + compile_run.stderr)
        (args.out / "sim.log").write_text(sim_run.stdout + sim_run.stderr if sim_run else "")
        result = {
            "schema": "opentallas.qwen-matvec-bank-equivalence.v1",
            "claim_boundary": "Independent pinned pre-refactor RTL versus banked RTL, G4/G64 synthetic INT8 split ops; not a real checkpoint token or P&R.",
            "groups": args.groups, "reference_commit": BASE,
            "reference_sha256": digest(original),
            "source_sha256": {p: digest((ROOT / p).read_bytes()) for p in SOURCES},
            "testbench_sha256": digest(testbench().encode()),
            "compile_returncode": compile_run.returncode,
            "sim_returncode": sim_run.returncode if sim_run else None,
            "compile_log_sha256": digest((args.out / "compile.log").read_bytes()),
            "sim_log_sha256": digest((args.out / "sim.log").read_bytes()),
            "status": "pass" if sim_run and sim_run.returncode == 0 and
                      "PASS bank equivalence" in sim_run.stdout else "fail",
        }
        (args.out / "result.json").write_text(json.dumps(result, indent=2) + "\n")
        print(json.dumps({k: result[k] for k in ("groups", "status", "compile_returncode", "sim_returncode")}))
        if result["status"] != "pass":
            raise SystemExit(1)


if __name__ == "__main__":
    main()
