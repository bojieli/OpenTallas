"""PATH-KV-PC 10-25 miter prep: 4c6e890d93 recut kit core (<mod>_o, kvspc_face_ports applied) vs + kvspc_private_ports.
Expected deltas checked exactly: o_prev (+1 edge, non-head), o_grp[296:295],[293:289] (+1 edge); everything else 0 edges.
python3 miter_prep2.py A_KIT_DIR MOD OUT_DIR MUT HARDEN_DIR PC CFG_STACK"""
import re, sys, shutil
from pathlib import Path
K, mod, T, mut, H = Path(sys.argv[1]), sys.argv[2], Path(sys.argv[3]), int(sys.argv[4]), sys.argv[5]
PCID, STK = int(sys.argv[6]), int(sys.argv[7])
sys.path.insert(0, H)
import kvspc_private_ports as X
head = mod.endswith("_h_head_p")
shutil.rmtree(T, ignore_errors=True); (T / "o").mkdir(parents=True); (T / "n").mkdir()
files = [Path(x).name for x in re.search(r"VERILOG_FILES = (.*)", (K / "config.mk").read_text()).group(1).split()]
names = set()
for f in files:
    names |= set(re.findall(r"^\s*module\s+(\w+)", (K / "rtl" / f).read_text(), re.M))
pat = re.compile(r"\b(" + "|".join(sorted(names, key=len, reverse=True)) + r")\b")
for f in files:
    t = (K / "rtl" / f).read_text()
    (T / "o" / f).write_text(pat.sub(lambda m: m.group(1) + "_o", t))
    shutil.copy(K / "rtl" / f, T / "n" / f)
extra = X.apply_kit(T / "n", mod, mut)
for side, sfx in (("o", "_o"), ("n", "")):
    for f in files:
        if f.endswith("_bb.v"):
            t = (K / "rtl" / f).read_text().replace("(* blackbox *)", "")
            m = re.search(r"module (\w+)", t).group(1)
            d, w = map(int, re.search(r"_(\d+)x(\d+)_", m).groups())
            t = t.replace(f"module {m} ", f"module {m}{sfx} ").replace("output wire [", "output reg [")
            beh = (f" reg [{w-1}:0] mem [0:{d-1}];\n always @(posedge clk) begin if (r_ce_in) rd_out <= mem[r_addr_in];"
                   f" if (w_ce_in) mem[w_addr_in] <= (mem[w_addr_in] & ~w_mask_in) | (wd_in & w_mask_in); end\nendmodule")
            t = t[:t.rindex("endmodule")] + beh + "\n"
            (T / side / f).write_text(t)
src = (K / "rtl" / f"{mod}.sv").read_text()
hdr = src[src.index(f"module {mod} ("):src.index(");", src.index(f"module {mod} ("))]
ports = re.findall(r"(input|output) wire \[(\d+):(\d+)\] (\w+)", hdr)
L = ["`timescale 1ns/1ps", "module tb;", "  reg clk = 0; always #0.5 clk = ~clk;",
     "  integer seed = 11, edges = 0, mism = 0, hq = 0, nfo = 0, ngrp = 0, nprev = 0;"]
ins = [(n, int(h), int(l)) for d, h, l, n in ports if d == "input" and n != "ck"]
outs = [(n, int(h), int(l)) for d, h, l, n in ports if d == "output"]
for n, h, l in ins:
    L.append(f"  reg [{h}:{l}] {n} = 0;")
for n, h, l in outs:
    L.append(f"  wire [{h}:{l}] {n}_o, {n}_n;")
co = [f".{n}({n})" for n, h, l in ins] + [".ck(clk)"]
L.append(f"  {mod}_o u_o (" + ", ".join(co + [f".{n}({n}_o)" for n, h, l in outs]) + ");")
L.append(f"  {mod} u_n (" + ", ".join(co + [f".{n}({n}_n)" for n, h, l in outs]) + ");")
# reference: o_prev and o_grp[296:289] one edge later
L.append("  reg [304:0] grp_d = 0; always @(posedge clk) grp_d <= o_grp_o;")
L.append("  wire [304:0] grp_ref = {o_grp_o[304:297], grp_d[296:295], o_grp_o[294], grp_d[293:289], o_grp_o[288:0]};")
hasprev = any(n == "o_prev" for n, _, _ in outs)
if hasprev:
    L.append("  reg [779:0] prev_d = 0; always @(posedge clk) prev_d <= o_prev_o;")
cmp = [(n, ("grp_ref" if n == "o_grp" else "prev_d" if n == "o_prev" else f"{n}_o")) for n, h, l in outs]
L.append("  always @(posedge clk) hq <= (rst_n[0] && hrst_n[0]) ? (hq > 0 ? hq - 1 : 0) : 6;")
L.append("  always @(negedge clk) if (rst_n[0] && hrst_n[0] && hq == 0) begin edges = edges + 1;")
L.append("    if ({" + ", ".join(f"{n}_n" for n, _ in cmp) + "} !== {" + ", ".join(r for _, r in cmp) + "}) begin mism = mism + 1; if (mism < 8) begin")
for n, r in cmp:
    L.append(f"      if ({n}_n !== {r}) $display(\"MISMATCH edge=%0d {n}\", edges);")
L.append("    end end")
L.append("    nfo = nfo + pc__fo_o[0]; ngrp = ngrp + (|o_grp_o[296:289]); ngrp = ngrp;")
if hasprev:
    L.append("    nprev = nprev + (|o_prev_o[779:2]);")
L.append("  end")
L.append("  integer c = 0, r; reg [31:0] rr;")
L.append(f"  initial begin rst_n = 0; hrst_n = 0; pc__cfg_stack = 2'd{STK};" + (f" pc__pc = 5'd{PCID};" if any(n == "pc__pc" for n, _, _ in ins) else "") + " end")
L.append("  always @(negedge clk) begin")
L.append("    c = c + 1;")
L.append("    rst_n[0] = !(c < 8 || (c % 2000 >= 1999 || c % 2000 < 5)); hrst_n[0] = rst_n[0];")
for n, h, l in ins:
    if n in ("rst_n", "hrst_n", "pc__pc", "pc__cfg_stack"):
        continue
    if n == "pc__fi":
        L.append("    pc__fi[0] = ((c % 2000) >= 10 && (c % 2000) < 14) || (c >= 3000 && ($random(seed) & 255) == 0);")
        continue
    wdt = h - l + 1
    if wdt >= 32:
        words = (wdt + 31) // 32
        L.append(f"    r = $random(seed); for (integer w = 0; w < {words}; w = w + 1) begin rr = ((r & 15) == 0) ? $random(seed) : 0; {n}[{l} + w*32 +: 32] = rr; end")
    else:
        L.append(f"    r = $random(seed); {n} = ((r & 15) == 0) ? {wdt}'($random(seed)) : 0;")
L.append("  end")
L.append("  initial begin")
L.append("    #6008;")
L.append("    $display(\"KVSPC2 MITER %s mismatches=%0d edges=%0d fo_edges=%0d grp_status_edges=%0d prev_edges=%0d\", "
         "(mism == 0 && edges > 1000) ? \"PASS\" : \"FAIL\", mism, edges, nfo, ngrp, nprev);")
L.append("    $finish; end")
L.append("endmodule")
(T / "tb.sv").write_text("\n".join(L) + "\n")
fl = [f"o/{f}" for f in files] + [f"n/{f}" for f in files] + [f"n/{f}" for f in extra]
(T / "files.f").write_text("\n".join(fl) + "\n")
print(T, len(files), "files, ins", len(ins), "outs", len(outs))
