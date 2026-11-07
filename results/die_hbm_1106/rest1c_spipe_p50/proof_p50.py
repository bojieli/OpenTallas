#!/usr/bin/env python3
"""HBM-FORM-TIMING-13 d44v part 50 proof inputs: yosys delay-equivalence of the __spipe1 form.
  ok   = gold: part-37 rest_1c (module renamed ..._p37) + ONE register on u_core_u_vm_scalar_data outside it
         vs gate: part-50 rest_1c with OT_REST1C_SCALAR_PIPE1 (every port must match, cycle for cycle);
  dflt = part-50 rest_1c WITHOUT the define vs part-37 rest_1c (exact, 0 cycles);
  mut  = gold vs gate with u_core_u_vm_scalar_data bits 0/1 swapped (must FAIL: 2 unproven).
    proof_p50.py P37_REST_1C_SV P50_REST_1C_SV REST_CORE_SV OUTDIR"""
import re
import sys
from pathlib import Path

p37, p50, core, out = map(Path, sys.argv[1:5])
out.mkdir(parents=True, exist_ok=True)
M = "ot_hgi_sfu_split3_ctl_rest_1c"
B = "u_core_u_vm_scalar_data"
s37 = p37.read_text().replace(f"module {M} (", f"module {M}_p37 (", 1)
(out / "p37.sv").write_text(s37)
hd = s37[s37.index(f"module {M}_p37 ("):]
hd = hd[:hd.index(");")]
ports = re.findall(r"(input|output) wire (\[\d+:\d+\] )?(\w+)", hd)
assert len(ports) == 107 and any(n == B for _, _, n in ports), len(ports)
decl = ",\n".join(f"    {d} wire {w or ''}{n}" for d, w, n in ports)


def conn(sub=None):
    return ", ".join(f".{n}({sub if (sub and n == B) else n})" for _, _, n in ports)


def mod(name, body):
    return [f"module {name} (", decl, ");"] + body + ["endmodule"]


v = ["`default_nettype none"]
v += mod("gold", [f"    wire [127:0] x; reg [127:0] q; always @(posedge clk) q <= x; assign {B} = q;",
                  f"    {M}_p37 u ({conn('x')});"])
v += mod("gate", [f"    {M} u ({conn()});"])
v += mod("mut", ["    wire [127:0] y;",
                 f"    assign {B} = {{y[127:2], y[0], y[1]}}; // MUTANT: swap 2 scalar-data bits",
                 f"    {M} u ({conn('y')});"])
v += mod("g37", [f"    {M}_p37 u ({conn()});"])
v += ["`default_nettype wire", ""]
(out / "wrap.sv").write_text("\n".join(v))
for name, define, g, t in (("eq50_ok", True, "gold", "gate"), ("eq50_mut", True, "gold", "mut"),
                           ("eq50_dflt", False, "g37", "gate")):
    d = "-DOT_REST1C_SCALAR_PIPE1 " if define else ""
    ys = [f"read_verilog -sv {d}/w/p37.sv /w/p50.sv /w/core.sv /w/wrap.sv",
          "hierarchy -check", "proc", "flatten", "opt_clean",
          f"equiv_make {g} {t} eq", "hierarchy -top eq", "async2sync",
          "equiv_struct", "equiv_simple", "equiv_induct", "equiv_status", "equiv_status -assert"]
    (out / f"{name}.ys").write_text("\n".join(ys) + "\n")
(out / "p50.sv").write_text(p50.read_text())
(out / "core.sv").write_text(core.read_text())
print("ports", len(ports), "out", out)
