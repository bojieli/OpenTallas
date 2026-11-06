#!/usr/bin/env python3
"""HBM-FORM-TIMING-11 part 37 lock-step bench generator: old plan module ot_hgi_sfu_core_split3__ctl (oneclk wrapper around the
gold ot_hgi_sfu_split3_ctl_core) vs the part-37 plan module (glue -> __split -> rest_1c + pipe_1c with the local reset copy),
renamed ..__p37 in the bench copy.  Random inputs every cycle, reset events (rst_n 5-cycle power-on, rst_lg_n pulse,
rst_n 2-cycle and 1-cycle pulses mid-run), every output compared every cycle.   gen_tb37.py WRAPPER.sv CYCLES > tb.v"""
import re, sys
src = open(sys.argv[1]).read(); CYC = int(sys.argv[2])
hd = src[src.index("module ot_hgi_sfu_core_split3__ctl ("):]; hd = hd[:hd.index(");")]
ports = [(d, int(a) + 1 if a else 1, n) for d, a, n in re.findall(r"(input|output) wire (?:\[(\d+):0\] )?(\w+)", hd)]
o = ["`timescale 1ns/1ps", "module tb;", " reg clk = 0; integer cyc = 0, errs = 0, i;"]
for d, w, n in ports:
    if d == "input" and n != "clk": o.append(f" reg [{w-1}:0] {n};")
    if d == "output": o.append(f" wire [{w-1}:0] g_{n}, s_{n};")
conn = lambda p: ", ".join(f".{n}({'clk' if n == 'clk' else (p + n if d == 'output' else n)})" for d, w, n in ports)
o.append(f" ot_hgi_sfu_core_split3__ctl gold({conn('g_')});")
o.append(f" ot_hgi_sfu_core_split3__ctl__p37 gate({conn('s_')});")
o.append(" always #0.5 clk = ~clk;")
o.append(" task rnd; begin")
for d, w, n in ports:
    if d == "input" and not n.startswith("rst") and n != "clk":
        o.append(f"  for (i = 0; i < {w}; i = i + 32) {n} = ({n} << 32) | $random;" if w > 32 else f"  {n} = $random;")
o.append(" end endtask")
o.append(" initial begin")
o.append("  rst_n = 0; rst_lg_n = 0; rnd;\n  repeat (5) @(negedge clk) rnd;\n  rst_n = 1; rst_lg_n = 4'hf;")
o.append(f"  while (cyc < {CYC}) begin\n   @(negedge clk); rnd; cyc = cyc + 1;")
o.append("   if (cyc == 300) rst_lg_n = 4'h5;\n   if (cyc == 303) rst_lg_n = 4'hf;\n   if (cyc == 500) rst_n = 0;\n   if (cyc == 502) rst_n = 1;\n"
         "   if (cyc == 650) rst_n = 0;\n   if (cyc == 651) rst_n = 1;")
for d, w, n in ports:
    if d == "output":
        o.append(f"   if (g_{n} !== s_{n}) begin errs = errs + 1; if (errs < 12) $display(\"MISMATCH cyc %0d {n}\", cyc); end")
o.append("  end\n  $display(\"BENCH_DONE cycles %0d errors %0d\", cyc, errs); $finish;\n end\nendmodule")
print("\n".join(o))
