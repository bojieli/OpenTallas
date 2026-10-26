#!/usr/bin/env python3
"""Old-vs-new lockstep bench for a +1-cycle input pin-register stage (S81-KITS-RTLC 10-24).

    rtl_delay_eq.py --top MOD --file CHANGED.sv [--ref-rev origin/main] --out DIR [--cycles N] [--seed S]
                    [--clk ck] [--rst rs] [--default none|async|rel1] [--cls 'PORT[hi:lo]=async' ...]
                    [--define D ...] [--dut-rev REV] -- OTHER_SOURCES...

DUT = MOD from the working-tree CHANGED.sv (or CHANGED.sv at --dut-rev: the pre-fix form, a mutant that must FAIL).
REF = the same file at --ref-rev (every module it defines renamed ref_*), fed EVERY input one edge later through bench
registers whose reset class mirrors the DUT's new input stage: none (reset-free), async (async clear by --rst low) or
rel1 (async clear by a bench copy of 'rn': clear while --rst is low, released one edge after it, as dsfd_qbank_S).  So
the bench proves: DUT(t) == REF(inputs at t-1) for every output bit, every cycle (the change is exactly one landing
edge on every input and nothing else).  Random inputs every cycle; --rst low for 4 cycles at the start and 2 cycles
every ~1000.  Prints DELAYEQ ... PASS / FAIL.  iverilog -g2012 + vvp."""
import argparse, re, subprocess, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
import die_port_bind as B

ap = argparse.ArgumentParser()
ap.add_argument("--top", required=True); ap.add_argument("--file", required=True)
ap.add_argument("--ref-rev", default="origin/main"); ap.add_argument("--dut-rev", default="")
ap.add_argument("--out", required=True)
ap.add_argument("--cycles", type=int, default=5000); ap.add_argument("--seed", type=int, default=1)
ap.add_argument("--clk", default="ck"); ap.add_argument("--rst", default="rs")
ap.add_argument("--default", default="none", choices=["none", "async", "rel1"])
ap.add_argument("--cls", action="append", default=[], help="PORT or PORT[k] or PORT[hi:lo] = none|async|rel1")
ap.add_argument("--define", action="append", default=[])
ap.add_argument("srcs", nargs="*")
a = ap.parse_args()
out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
show = lambda rev: subprocess.run(["git", "-C", str(ROOT), "show", f"{rev}:{a.file}"], check=True, capture_output=True,
                                  text=True).stdout
new_text = show(a.dut_rev) if a.dut_rev else (ROOT / a.file).read_text()
(out / "dut.sv").write_text(new_text)
ref_text = show(a.ref_rev)
mods = [m.name for m in B.parse_modules(ref_text, a.file)]
for m in sorted(mods, key=len, reverse=True):
    ref_text = re.sub(r"\b" + re.escape(m) + r"\b", "ref_" + m, ref_text)
(out / "ref.sv").write_text(ref_text)
top = [m for m in B.parse_modules(new_text, a.file) if m.name == a.top][0]
env = top.env({})
ports = [(p, top.ports[p][0], top.width(p, env)) for p in top.order]
cls = {}
for c in a.cls:
    lhs, v = c.split("=")
    mm = re.fullmatch(r"(\w+)(?:\[(\d+)(?::(\d+))?\])?", lhs.strip())
    p, hi, lo = mm.group(1), mm.group(2), mm.group(3)
    w = dict((q, ww) for q, _, ww in ports)[p]
    bits = range(w) if hi is None else ([int(hi)] if lo is None else range(int(lo), int(hi) + 1))
    for b in bits:
        cls[(p, b)] = v.strip()
L = ["`timescale 1ns/1ps", "module tb_delayeq;", f"reg {a.clk} = 0; always #0.5 {a.clk} = ~{a.clk};",
     "integer n, j, err = 0, ncmp = 0; reg [31:0] rs_ = 32'h1;",
     "function automatic [31:0] r32(); begin rs_ = rs_ ^ (rs_ << 13); rs_ = rs_ ^ (rs_ >> 17); rs_ = rs_ ^ (rs_ << 5); r32 = rs_; end endfunction"]
ins, outs = [], []
for p, d, w in ports:
    if p == a.clk:
        continue
    if d == "input":
        L.append(f"reg [{w - 1}:0] {p} = 0; reg [{w - 1}:0] q_{p};")
        if p != a.rst:
            ins.append((p, w))
    else:
        L.append(f"wire [{w - 1}:0] d_{p}, r_{p}; integer act_{p} = 0; reg [{w - 1}:0] last_{p};")
        outs.append((p, w))
rst_w = dict((q, ww) for q, _, ww in ports)[a.rst]
R = f"{a.rst}[0]" if rst_w > 1 else a.rst
L.append(f"reg rn_b; always @(posedge {a.clk} or negedge {R}) if (!{R}) rn_b <= 1'b0; else rn_b <= 1'b1;")
L.append(f"always @(*) q_{a.rst} = {a.rst};")
for p, w in ins:
    for b in range(w):
        k = cls.get((p, b), a.default)
        if k == "none":
            L.append(f"always @(posedge {a.clk}) q_{p}[{b}] <= {p}[{b}];")
        elif k == "async":
            L.append(f"always @(posedge {a.clk} or negedge {R}) if (!{R}) q_{p}[{b}] <= 1'b0; else q_{p}[{b}] <= {p}[{b}];")
        else:
            L.append(f"always @(posedge {a.clk} or negedge rn_b) if (!rn_b) q_{p}[{b}] <= 1'b0; else q_{p}[{b}] <= {p}[{b}];")
conn = lambda pre, ip: ", ".join([f".{a.clk}({a.clk})", f".{a.rst}({a.rst})"] + [f".{p}({ip}{p})" for p, _ in ins] +
                                 [f".{p}({pre}_{p})" for p, _ in outs])
L.append(f"{a.top} dut ({conn('d', '')});")
L.append(f"ref_{a.top} rf ({conn('r', 'q_')});")
L.append("initial begin")
L.append(f"  rs_ = 32'h1 ^ {a.seed} * 32'h9e3779b9; for (n = 0; n < 4; n = n + 1) j = r32();")
L.append(f"  {a.rst} = 0; repeat (4) @(negedge {a.clk}); {a.rst} = {{{rst_w}{{1'b1}}}};")
L.append(f"  for (n = 0; n < {a.cycles}; n = n + 1) begin")
for p, w in ins:
    L.append(f"    for (j = 0; j < {w}; j = j + 32) {p} = ({p} << 32) | r32();")
L.append(f"    {a.rst} = (n % 1009 < 2) ? {{{rst_w}{{1'b0}}}} : {{{rst_w}{{1'b1}}}};")
L.append(f"    @(posedge {a.clk}); #0.1; ncmp = ncmp + 1;")
for p, w in outs:
    L.append(f"    if (n > 1 && d_{p} !== r_{p}) begin err = err + 1; if (err < 8) $display(\"DELAYEQ MISMATCH {p} cycle %0d dut %h ref %h\", n, d_{p}, r_{p}); end")
    L.append(f"    if (n > 0 && d_{p} !== last_{p}) act_{p} = act_{p} + 1; last_{p} = d_{p};")
L.append(f"    @(negedge {a.clk});")
L.append("  end")
acts = " ".join(f"{p}=%0d" for p, _ in outs)
L.append(f"  $display(\"DELAYEQ_ACT {acts}\", {', '.join('act_' + p for p, _ in outs)});")
L.append(f"  $display(\"DELAYEQ {a.top} cycles=%0d outputs={len(outs)} err=%0d\", ncmp, err);")
L.append("  if (err == 0) $display(\"PASS\"); else $display(\"FAIL\");")
L.append("  $finish;\nend\nendmodule")
(out / "tb.sv").write_text("\n".join(L) + "\n")
defs = [f"-D{d}" for d in a.define]
srcs = [str(ROOT / s) for s in a.srcs] + [str(out / "dut.sv"), str(out / "ref.sv"), str(out / "tb.sv")]
b = subprocess.run(["iverilog", "-g2012", *defs, "-s", "tb_delayeq", "-o", str(out / "sim"), *srcs], capture_output=True,
                   text=True)
(out / "build.log").write_text(b.stdout + b.stderr)
if b.returncode:
    print("BUILD_FAILED"); print(b.stderr[-2000:]); sys.exit(3)
r = subprocess.run(["vvp", "-n", str(out / "sim")], capture_output=True, text=True)
(out / "run.log").write_text(r.stdout + r.stderr)
for ln in r.stdout.splitlines():
    if ln.startswith(("DELAYEQ", "PASS", "FAIL")):
        print(ln)
sys.exit(0 if "\nPASS" in "\n" + r.stdout else 1)
