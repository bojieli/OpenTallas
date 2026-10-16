#!/usr/bin/env python3
"""Exercise the real synthesis pin wrapper, including the forwarded clock.

The baseline comparison uses the actual RTL core delayed by exactly one ck edge.
The independent numeric lane test checks every scheduled word and fault bit.
mut_clock regenerates the historical broken wrapper with fi0 captured on ck.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
TOP = "dsfd_r2l_vr_1024x1__ha_SW"
KIT = ROOT / "physical/ref_tile/s81net_r2l_vr_1024x1__ha_sw"


def run(cmd, **kwargs):
    return subprocess.run(cmd, check=True, text=True, **kwargs)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("mode", choices=["pass", "mut_clock"])
    ap.add_argument("out", type=Path)
    args = ap.parse_args()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    spec = json.loads((KIT / "spec.json").read_text())
    # Use the same production hook and elaborated port list as the route.
    # No copied or independently implemented wrapper generator is involved.
    env = os.environ.copy()
    env.update(DESIGN_NAME=TOP, OT_PIN_REGS_CLOCK="ck", RESULTS_DIR=str(out),
               OT_PIN_REGS_EXCLUDE=("^(di0|rs)$" if args.mode == "mut_clock"
                                    else spec["pin_regs"]["exclude"]))
    script = "\n".join([
        "yosys read_verilog -sv " + " ".join(spec["sources"]),
        f"yosys hierarchy -check -top {TOP}",
        "source physical/common_flow/ot_pin_regs.tcl",
        "yosys proc",
        f"yosys write_verilog -noattr {out / 'synth_sim.v'}",
    ]) + "\n"
    (out / "generate.tcl").write_text(script)
    with (out / "yosys.log").open("w") as log:
        run(["yosys", "-Q", "-T", "-c", str(out / "generate.tcl")],
            cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT)
    table = (out / "ot_pin_regs.tsv").read_text()
    want = "fi0\tinput\t1\t" + ("1\tpin register" if args.mode == "mut_clock" else "0\texcluded")
    if want not in table or "o\toutput\t1027\t1\tpin register" not in table:
        raise RuntimeError("production wrapper port-stage table mismatch")
    tb = (ROOT / "rtl/dsrom_sys/s81_static_net/test/tb_dsfd_hend_static.sv").read_text()
    # Drive all 1,024 payload bits, rather than extending a 96-bit sample.
    tb = tb.replace("x = {$random(s), $random(s), $random(s)};",
                    "for (integer wb=0; wb<PW; wb=wb+32) x[wb +: 32] = $random(s);")
    shadow = f"""
    wire [1026:0] core_o;
    {TOP}__ot_pr_core ref_core (.ck(ck), .o(core_o), .rs(rs), .di0(di[DW-1:0]), .fi0(fi[0]));
    reg [1026:0] previous;
    integer wrap_checks = 0;
    always @(posedge ck) begin
        previous <= core_o;
        #1;
        if (rs && t > 120) begin
            wrap_checks = wrap_checks + 1;
            if (o !== previous) begin
                bad = bad + 1;
                if (bad < 5) $display("WRAPPER shadow mismatch at tick %0d", t);
            end
        end
    end
"""
    tb = tb.replace("    // checker\n", shadow + "\n    // checker\n")
    tb = tb.replace("        if (bad) begin", "        if (wrap_checks < 150) bad = bad + 1;\n"
                    '        $display("WRAPPER shadow %0d checks", wrap_checks);\n'
                    "        if (bad) begin")
    (out / "tb.sv").write_text(tb)
    failures = 0
    total = 0
    for phase in [0, 4, 9]:
        run(["iverilog", "-g2012", "-DR2L", f"-DDUT={TOP}",
             "-DPORTS=, .di0(di[DW-1:0]), .fi0(fi[0])", "-s", "tb_dsfd_hend_static",
             "-Ptb_dsfd_hend_static.PW=1024", f"-Ptb_dsfd_hend_static.PH={phase}",
             "-o", str(out / "sim"), str(out / "synth_sim.v"), str(out / "tb.sv")], cwd=ROOT)
        result = subprocess.run(["vvp", "-n", str(out / "sim")], text=True,
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        (out / f"phase{phase}.log").write_text(result.stdout)
        print(result.stdout[-1800:], end="")
        total += 1
        if result.returncode or "HEND_STATIC PASS" not in result.stdout:
            failures += 1
    if args.mode == "pass":
        if failures:
            print(f"R2L_PIN_WRAPPER FAIL {failures}/{total}")
            return 1
        print("R2L_PIN_WRAPPER PASS three phases, full1024-bit payload, output exactly core+1ckedge")
        return 0
    if failures != total:
        print(f"R2L_PIN_WRAPPER MUTANT ESCAPED {failures}/{total}")
        return 1
    print(f"R2L_PIN_WRAPPER MUTANT REJECTED {failures}/{total}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
