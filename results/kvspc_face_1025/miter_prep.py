"""KV-CORE-RTL/PC 10-25 miter prep: original kit core (<mod>_o) vs kvspc_face_ports-transformed core.
python3 miter_prep.py BASE_KIT_DIR MOD OUT_DIR MUT HARDEN_DIR"""
import re, sys, shutil, random
from pathlib import Path
K, mod, T, mut, H = Path(sys.argv[1]), sys.argv[2], Path(sys.argv[3]), int(sys.argv[4]), sys.argv[5]
sys.path.insert(0, H)
import kvspc_face_ports as X
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
for p in (K / "rtl").iterdir():
    if p.suffix in (".svh", ".vh"):
        shutil.copy(p, T / "o" / p.name); shutil.copy(p, T / "n" / p.name)
X.apply_kit(T / "n", mod, mut)
# behavioural SRAM models for the black boxes (both copies)
for side, sfx in (("o", "_o"), ("n", "")):
    for f in files:
        if f.endswith("_bb.v"):
            t = (K / "rtl" / f).read_text().replace("(* blackbox *)", "")
            m = re.search(r"module (\w+)", t).group(1)
            d, w = map(int, re.search(r"_(\d+)x(\d+)_", m).groups())
            a = (d - 1).bit_length()
            t = t.replace(f"module {m} ", f"module {m}{sfx} ").replace("output wire [", "output reg [")
            beh = (f" reg [{w-1}:0] mem [0:{d-1}];\n always @(posedge clk) begin if (r_ce_in) rd_out <= mem[r_addr_in];"
                   f" if (w_ce_in) mem[w_addr_in] <= (mem[w_addr_in] & ~w_mask_in) | (wd_in & w_mask_in); end\nendmodule")
            t = t[:t.rindex("endmodule")] + beh + "\n"
            (T / side / f).write_text(t)
# ports of the original wrapper
src = (K / "rtl" / f"{mod}.sv").read_text()
hdr = src[src.index(f"module {mod} ("):src.index(");", src.index(f"module {mod} ("))]
ports = re.findall(r"(input|output) wire \[(\d+):0\] (\w+)", hdr)
new_hdr = (T / "n" / f"{mod}.sv").read_text()
new_hdr = new_hdr[new_hdr.index(f"module {mod} ("):new_hdr.index(");", new_hdr.index(f"module {mod} ("))]
nports = re.findall(r"(input|output) wire \[(\d+):(\d+)\] (\w+)", new_hdr)
clocks = {"ck", "hck", "pc__front_hbm_data", "pc__return_hbm_data"}
L = ["`timescale 1ns/1ps", "module tb;", "  reg clk = 0; always #0.5 clk = ~clk;", "  integer seed = 11, edges = 0, mism = 0, hq = 0, nk = 0, nfi = 0, nfo = 0, nles = 0;"]
ins = [(n, int(h)) for d, h, n in ports if d == "input" and n not in clocks]
outs = [(n, int(h)) for d, h, n in ports if d == "output"]
for n, h in ins:
    L.append(f"  reg [{h}:0] {n} = 0;")
for n, h in outs:
    L.append(f"  wire [{h}:0] {n}_o, {n}_n;")
L.append("  reg fi_d = 0; always @(posedge clk) fi_d <= pc__fi[0];" if any(n == "pc__fi" for n, _ in ins) else "")
co = [f".{n}({n})" for n, h in ins if n != "pc__fi"] + (["  .pc__fi(fi_d)"] if any(n == "pc__fi" for n, _ in ins) else [])
co += [".ck(clk)", ".hck(clk)", ".pc__front_hbm_data({4{clk}})", ".pc__return_hbm_data({4{clk}})"]
co += [f".{n}({n}_o)" for n, h in outs]
L.append(f"  {mod}_o u_o (" + ", ".join(co) + ");")
cn = []
for d, h, l, n in nports:
    if n == "ck":
        cn.append(".ck(clk)")
    elif d == "input":
        cn.append(f".{n}({n if not re.search(r'_(259|15|31)$', n) else re.sub(r'_(259|15|31)$', '', n)}[{h}:{l}])")
    else:
        cn.append(f".{n}({n}_n)")
L.append(f"  {mod} u_n (" + ", ".join(cn) + ");")
cmp_o = [f"{n}_o" for n, h in outs if n != "pc__ko"]
cmp_n = [f"{n}_n" for n, h in outs if n != "pc__ko"]
L.append("  wire [9999:0] vo = {" + ", ".join(cmp_o) + "};")
L.append("  wire [9999:0] vn = {" + ", ".join(cmp_n) + "};")
hasko = any(n == "pc__ko" for n, _ in outs)
if hasko:
    L.append("  reg [32:0] ko_ref = 0; always @(posedge clk) ko_ref <= pc__ko_o;")
L.append("  always @(posedge clk) hq <= hrst_n[0] ? (hq > 0 ? hq - 1 : 0) : 4;")
L.append("  always @(negedge clk) if (rst_n[0] && hrst_n[0] && hq == 0) begin edges = edges + 1;")
L.append("    if (vo !== vn) begin mism = mism + 1; if (mism < 8) begin")
for n, h in outs:
    if n != "pc__ko":
        L.append(f"      if ({n}_o !== {n}_n) $display(\"MISMATCH edge=%0d {n}\", edges);")
L.append("    end end")
if hasko:
    L.append("    if (pc__ko_n !== ko_ref) begin mism = mism + 1; if (mism < 8) $display(\"MISMATCH edge=%0d ko\", edges); end")
    L.append("    nk = nk + (pc__ko_n[0] ? 1 : 0); nfi = nfi + pc__fi[0];")
if any(n == "pc__fo" for n, _ in outs):
    L.append("    nfo = nfo + pc__fo_o[0];")
L.append("    nles = nles + pc__land_es_o[0];")
L.append("  end")
# stimulus: sparse random (each bus random with p=1/4, else 0) so sticky faults do not saturate at once
L.append("  integer c = 0, r; reg [31:0] rr;")
L.append("  initial begin rst_n = 0; hrst_n = 0; pc__cfg_stack = 2'd1;" + (" pc__pc = 5'd5;" if any(n == "pc__pc" for n, _ in ins) else "") + " end")
L.append("  always @(negedge clk) begin")
L.append("    c = c + 1;")
L.append("    rst_n[0] = !(c < 8 || (c % 2000 >= 1999 || c % 2000 < 5)); hrst_n[0] = rst_n[0];")
for n, h in ins:
    if n in ("rst_n", "hrst_n", "pc__pc", "pc__cfg_stack"):
        continue
    if n == "pc__fi":
        L.append("    pc__fi[0] = ((c % 2000) >= 10 && (c % 2000) < 14) || (c >= 3000 && ($random(seed) & 255) == 0);")
        continue
    words = (h + 32) // 32
    L.append(f"    r = $random(seed); for (integer w = 0; w < {words}; w = w + 1) begin rr = ((r & 15) == 0) ? $random(seed) : 0; {n}[w*32 +: 32] = rr; end"
             if h >= 31 else f"    r = $random(seed); {n} = ((r & 15) == 0) ? {h+1}'($random(seed)) : 0;")
L.append("    if (c % 700 == 0) $display(\"DBG c=%0d fo=%b les0=%b ki0=%b\", c, " + ("pc__fo_o[0]" if any(n == "pc__fo" for n, _ in outs) else "1'b0") + ", pc__land_es_o[0], pc__ki[0]);")
L.append("  end")
L.append("  initial begin")
L.append("    #6008;")
L.append("    $display(\"KVSPC MITER %s mismatches=%0d edges=%0d ko_v=%0d fi=%0d fo_edges=%0d land_es_v=%0d\", "
         "(mism == 0 && edges > 1000) ? \"PASS\" : \"FAIL\", mism, edges, nk, nfi, nfo, nles);")
L.append("    $finish; end")
L.append("endmodule")
(T / "tb.sv").write_text("\n".join(L) + "\n")
fl = [f"o/{f}" for f in files] + [f"n/{f}" for f in files]
(T / "files.f").write_text("\n".join(fl) + "\n")
print(T, len(files), "files, ins", len(ins), "outs", len(outs), "new ports", len(nports))
