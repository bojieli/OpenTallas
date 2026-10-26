#!/usr/bin/env python3
"""Emit a lockstep SV testbench: legacy core top vs its __q3sync copy, identical
stimulus, all clock ports on one clock, all reset ports driven by one reset
held for --hold cycles (cold), then a warm reset at --warm for --hold cycles.
Outputs are compared on every negedge outside [reset assert, release + 0) windows;
any mismatch after release is a FAIL (exit code 1 via $fatal).
Usage: q3_lockstep_tb.py <core_top.sv> <module> --out tb.sv [--cycles N --hold H --warm W --seed S]
"""
import argparse, re

ap = argparse.ArgumentParser()
ap.add_argument("src"); ap.add_argument("module")
ap.add_argument("--out", required=True)
ap.add_argument("--cycles", type=int, default=4000)
ap.add_argument("--hold", type=int, default=64)
ap.add_argument("--warm", type=int, default=2000)
ap.add_argument("--seed", type=int, default=1)
ap.add_argument("--vprob", type=int, default=4, help="1-bit non-clock/reset inputs high with prob 1/vprob")
a = ap.parse_args()
txt = open(a.src).read()
m = re.search(r"module\s+" + re.escape(a.module) + r"\s*\((.*?)\);", txt, re.S)
ports = []
for pm in re.finditer(r"(input|output)\s+(?:wire|logic|reg)?\s*(\[\s*(\d+)\s*:\s*0\s*\])?\s*(\w+)", m.group(1)):
    ports.append((pm.group(1), int(pm.group(3)) + 1 if pm.group(3) else 1, pm.group(4)))
isclk = lambda n: re.search(r"(^|_)(clk|ck)(_|$|\d)", n) is not None
isrst = lambda n: "rst" in n
L = []
L.append("`timescale 1ns/1ps\nmodule tb;\n  reg clk = 0; reg rst_n = 0; integer cyc = 0; integer mism = 0; integer cmp = 0; integer act = 0; integer rmism = 0;")
L.append("  always #1 clk = ~clk;")
for d, w, n in ports:
    if d == "input" and not isclk(n) and not isrst(n):
        L.append("  reg [%d:0] i_%s = 0;" % (w - 1, n))
    if d == "output":
        L.append("  wire [%d:0] o_%s_L, o_%s_S;" % (w - 1, n, n))
L.append("  reg [%d:0] prevL = 0;" % (sum(w for d, w, n in ports if d == "output") - 1))
for suf, mod in (("L", a.module), ("S", a.module + "__q3sync")):
    conns = []
    for d, w, n in ports:
        if d == "input":
            e = ("{%d{clk}}" % w) if isclk(n) else ("{%d{rst_n}}" % w) if isrst(n) else "i_" + n
        else:
            e = "o_%s_%s" % (n, suf)
        conns.append("    .%s(%s)" % (n, e))
    L.append("  %s u_%s (\n%s);" % (mod, suf, ",\n".join(conns)))
L.append("  function automatic [4095:0] rnd(input integer w); integer k; begin rnd = 0; for (k = 0; k < 4096; k = k + 32) rnd[k +: 32] = $urandom; end endfunction")
L.append("  integer seed_dummy;")
L.append("  initial begin seed_dummy = $urandom(%d); end" % a.seed)
L.append("  wire in_rst = (cyc < %d) || (cyc >= %d && cyc < %d);" % (a.hold, a.warm, a.warm + a.hold))
L.append("  always @(negedge clk) begin")
L.append("    cyc <= cyc + 1;")
L.append("    rst_n <= !((cyc + 1 < %d) || (cyc + 1 >= %d && cyc + 1 < %d));" % (a.hold, a.warm, a.warm + a.hold))
for d, w, n in ports:
    if d == "input" and not isclk(n) and not isrst(n):
        if w == 1:
            L.append("    i_%s <= (($urandom %% %d) == 0);" % (n, a.vprob))
        else:
            L.append("    i_%s <= rnd(%d);" % (n, w))
outs=[n for d,w,n in ports if d=="output"]
L.append("    if (in_rst && ({%s} !== {%s})) rmism = rmism + 1;" % (",".join("o_%s_L"%n for n in outs), ",".join("o_%s_S"%n for n in outs)))
L.append("    if (!in_rst) begin cmp = cmp + 1;")
for d, w, n in ports:
    if d == "output":
        L.append("      if (o_%s_L !== o_%s_S) begin mism = mism + 1; if (mism < 20) $display(\"MISMATCH cyc=%%0d %s\", cyc); end" % (n, n, n))
L.append("      if ({%s} != prevL) act = act + 1;" % ",".join("o_%s_L"%n for n in outs))
L.append("    end")
L.append("    prevL <= {%s};" % ",".join("o_%s_L"%n for n in outs))
L.append("    if (cyc == %d) begin $display(\"LOCKSTEP compared_cycles=%%0d mismatches=%%0d output_change_cycles=%%0d in_reset_window_diff_cycles=%%0d hold=%d warm=%d\", cmp, mism, act, rmism); if (mism != 0) $fatal(1, \"LOCKSTEP FAIL\"); else $display(\"LOCKSTEP PASS\"); $finish; end" % (a.cycles, a.hold, a.warm))
L.append("  end\nendmodule")
open(a.out, "w").write("\n".join(L) + "\n")
print("ports", len(ports), "clocks", sum(isclk(p[2]) for p in ports), "resets", sum(isrst(p[2]) for p in ports))
