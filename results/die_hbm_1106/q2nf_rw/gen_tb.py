#!/usr/bin/env python3
"""gen_tb.py RTL.sv TB.sv CYC: whole-core lock-step of ot_q2nf_rest, old form (modules renamed old_*) vs OT_Q2NF_RW.
All clocks = one clock; every data input random every cycle under 4 density modes changed every 100 cycles; reset pulse every
2000 cycles; EVERY output bit compared EVERY cycle with !==.  Macro activity is counted from the macro enables of the new DUT, so
a pass with idle macros would be visible."""
import re, sys
s = open(sys.argv[1]).read(); cyc = sys.argv[3]
top = s[s.index("module ot_q2nf_rest ("):]; hdr = top[:top.index(");")]
ports = [(a, int(b or 0) + 1, c) for a, b, c in re.findall(r"^\s*(input|output)\s+wire\s+(?:\[(\d+):0\]\s+)?(\w+)\s*,?\s*$", hdr, re.M)]
ins = [p for p in ports if p[0] == "input"]; outs = [p for p in ports if p[0] == "output"]
assert len(ports) == hdr.count("input") + hdr.count("output"), (len(ports), hdr.count("input"), hdr.count("output"))
clks = [p for p in ins if p[2].startswith("clk")]; rst = [p for p in ins if p[2] == "rst_n"]; assert len(rst) == 1
data = [p for p in ins if p not in clks and p not in rst]
L = ["`timescale 1ns/1ps", "module tb;", "  logic clk=0, rst_n=0;  always #1 clk=~clk;"]
L += [f"  logic [{w-1}:0] i_{n};" for _, w, n in data] + [f"  wire [{w-1}:0] a_{n}, b_{n};" for _, w, n in outs]
def conn(pre):
    return ",\n    ".join([f".{n}({{{w}{{clk}}}})" for _, w, n in clks] + [".rst_n(rst_n)"] + [f".{n}(i_{n})" for _, _, n in data] + [f".{n}({pre}_{n})" for _, _, n in outs])
L += ["  old_ot_q2nf_rest a(\n    " + conn("a") + ");", "  ot_q2nf_rest b(\n    " + conn("b") + ");"]
L += ["  integer cyc=0, errs=0, mode=0, nz=0, wl=0, ri=0;", "  always @(negedge clk) begin", "    cyc <= cyc+1; rst_n <= (cyc%2000)>=8;", "    if (cyc%100==0) mode=$urandom%4;"]
for _, w, n in data:
    L.append(f"    for (int k=0;k<{w};k+=1) i_{n}[k] = (mode==0)? 1'($urandom) : (mode==1)? 1'($urandom%4==0) : (mode==2)? 1'($urandom%4!=0) : 1'($urandom%8==0);")
L.append("    if (" + " || ".join(f"a_{n}!==b_{n}" for _, _, n in outs) + ") begin errs++; if (errs<6) $display(\"MISMATCH cyc=%0d\", cyc); end")
L.append("    if (" + " || ".join(f"|b_{n}" for _, _, n in outs) + ") nz++;")
for g in (0, 1):
    for bk in range(4):
        L.append(f"    if (b.u_x.\\u_body.g_link[{g}].u_link.g_bank[{bk}].u_store.u_native.wq ) wl++;")
for g in (0, 1, 2):
    L.append(f"    if (b.u_x.\\u_body.g_iss256.u_issuer.fv_c[{g}] ) ri++;")
L.append(f"    if (cyc=={cyc}) begin $display(\"Q2NF_RW LOCKSTEP %s errs=%0d nonzero_cycles=%0d link_writes=%0d issuer_read_en=%0d of %0d\", errs?\"FAIL\":\"PASS\", errs, nz, wl, ri, {cyc}); $finish; end")
L += ["  end", "endmodule"]
open(sys.argv[2], "w").write("\n".join(L) + "\n"); print("tb", len(ins), "inputs", len(outs), "outputs")
