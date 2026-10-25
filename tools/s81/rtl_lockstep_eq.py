#!/usr/bin/env python3
"""Old-vs-new lockstep equivalence bench for a 0-cycle RTL change (S81-KITS-RTLB 10-24).

    rtl_lockstep_eq.py --top MOD --file CHANGED.sv [--ref-rev origin/main] --out DIR [--cycles N] [--seed S]
                       [--clk clk] [--rst-re REGEX] [--define D ...] [--param K=V ...] -- OTHER_SOURCES...

DUT = MOD from the working-tree CHANGED.sv; REF = the same file at --ref-rev with every module it defines renamed ref_*.
Both see the same random inputs every cycle (reset ports: low for 4 cycles at start and for 2 cycles every ~1000);
EVERY output bit is compared after every rising edge from the first release on.  The bench also counts, per output port,
the cycles it changed (activity; a port that never moves is reported).  Prints LOCKSTEP ... PASS / FAIL.
--idle-blocks B: all inputs 0 in every odd block of B cycles (a sticky / hold output must keep its value through
quiet stretches; catches non-sticky pin-flop mutants).  Runs iverilog -g2012 + vvp (small cores)."""
import argparse, re, subprocess, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
import die_port_bind as B

ap = argparse.ArgumentParser()
ap.add_argument("--top", required=True); ap.add_argument("--file", required=True)
ap.add_argument("--ref-rev", default="origin/main"); ap.add_argument("--out", required=True)
ap.add_argument("--cycles", type=int, default=20000); ap.add_argument("--seed", type=int, default=1)
ap.add_argument("--clk", default="clk"); ap.add_argument("--rst-re", default=r"^(rst_n|rst|rs|rn)$")
ap.add_argument("--define", action="append", default=[]); ap.add_argument("--param", action="append", default=[])
ap.add_argument("--vprob", type=int, default=0, help="if >0: 1-bit inputs named *_v / *v / go* are 1 with this %% only")
ap.add_argument("--idle-blocks", type=int, default=0, help="if >0: inputs are all 0 in every odd block of this many cycles")
ap.add_argument("srcs", nargs="*")
a = ap.parse_args()
out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
new_text = (ROOT / a.file).read_text()
ref_text = subprocess.run(["git", "-C", str(ROOT), "show", f"{a.ref_rev}:{a.file}"], check=True, capture_output=True,
                          text=True).stdout
mods = [m.name for m in B.parse_modules(ref_text, a.file)]
for m in sorted(mods, key=len, reverse=True):
    ref_text = re.sub(r"\b" + re.escape(m) + r"\b", "ref_" + m, ref_text)
(out / "ref.sv").write_text(ref_text)
top = [m for m in B.parse_modules(new_text, a.file) if m.name == a.top][0]
pov = dict(kv.split("=", 1) for kv in a.param)
env = top.env({k: int(v) for k, v in pov.items()})
ports = [(p, top.ports[p][0], top.width(p, env)) for p in top.order]
pmap = ", ".join(f".{k}({v})" for k, v in pov.items())
pinst = f" #({pmap})" if pmap else ""
L = ["`timescale 1ns/1ps", f"module tb_lockstep;", f"reg {a.clk} = 0; always #0.5 {a.clk} = ~{a.clk};",
     "integer n, j, err = 0, ncmp = 0; reg [31:0] rs_ = 32'h1;",
     "function automatic [31:0] r32(); begin rs_ = rs_ ^ (rs_ << 13); rs_ = rs_ ^ (rs_ >> 17); rs_ = rs_ ^ (rs_ << 5); r32 = rs_; end endfunction"]
ins, outs, rsts = [], [], []
for p, d, w in ports:
    if p == a.clk:
        continue
    if d == "input":
        L.append(f"reg [{w - 1}:0] {p} = 0;")
        (rsts if re.match(a.rst_re, p) else ins).append((p, w))
    else:
        L.append(f"wire [{w - 1}:0] d_{p}, r_{p}; integer act_{p} = 0; reg [{w - 1}:0] last_{p};")
        outs.append((p, w))
conn = lambda pre: ", ".join([f".{a.clk}({a.clk})"] + [f".{p}({p})" for p, _ in ins + rsts] + [f".{p}({pre}_{p})" for p, _ in outs])
L.append(f"{a.top}{pinst} dut ({conn('d')});")
L.append(f"ref_{a.top}{pinst} rf ({conn('r')});")
L.append("initial begin")
L.append(f"  rs_ = 32'h1 ^ {a.seed} * 32'h9e3779b9; for (n = 0; n < 4; n = n + 1) j = r32();")
for p, w in rsts:
    L.append(f"  {p} = 0;")
L.append("  repeat (4) @(negedge clk);")
for p, w in rsts:
    L.append(f"  {p} = {{{w}{{1'b1}}}};")
L.append(f"  for (n = 0; n < {a.cycles}; n = n + 1) begin")
idle = f"({a.idle_blocks} > 0 && (n / {max(a.idle_blocks, 1)}) % 2 == 1)"
for p, w in ins:
    if a.vprob and w == 1 and re.search(r"(_v|v|^go.*|_go)$", p):
        L.append(f"    {p} = (r32() % 100) < {a.vprob};")
    else:
        L.append(f"    for (j = 0; j < {w}; j = j + 32) {p} = ({p} << 32) | r32();")
    L.append(f"    if {idle} {p} = 0;")
for p, w in rsts:
    L.append(f"    {p} = (n % 1009 < 2) ? {{{w}{{1'b0}}}} : {{{w}{{1'b1}}}};")
L.append("    @(posedge clk); #0.1; ncmp = ncmp + 1;")
for p, w in outs:
    L.append(f"    if (d_{p} !== r_{p}) begin err = err + 1; if (err < 8) $display(\"LOCKSTEP MISMATCH {p} cycle %0d dut %h ref %h\", n, d_{p}, r_{p}); end")
    L.append(f"    if (n > 0 && d_{p} !== last_{p}) act_{p} = act_{p} + 1; last_{p} = d_{p};")
L.append("    @(negedge clk);")
L.append("  end")
acts = " ".join(f"{p}=%0d" for p, _ in outs)
L.append(f"  $display(\"LOCKSTEP_ACT {acts}\", {', '.join('act_' + p for p, _ in outs)});")
L.append(f"  $display(\"LOCKSTEP {a.top} cycles=%0d outputs={len(outs)} err=%0d\", ncmp, err);")
L.append("  if (err == 0) $display(\"PASS\"); else $display(\"FAIL\");")
L.append("  $finish;\nend\nendmodule")
(out / "tb.sv").write_text("\n".join(L) + "\n")
defs = [f"-D{d}" for d in a.define]
srcs = [str(ROOT / s) for s in a.srcs] + [str(ROOT / a.file), str(out / "ref.sv"), str(out / "tb.sv")]
b = subprocess.run(["iverilog", "-g2012", *defs, "-s", "tb_lockstep", "-o", str(out / "sim"), *srcs], capture_output=True, text=True)
(out / "build.log").write_text(b.stdout + b.stderr)
if b.returncode:
    print("BUILD_FAILED"); print(b.stderr[-2000:]); sys.exit(3)
r = subprocess.run(["vvp", "-n", str(out / "sim")], capture_output=True, text=True)
(out / "run.log").write_text(r.stdout + r.stderr)
for ln in r.stdout.splitlines():
    if ln.startswith(("LOCKSTEP", "PASS", "FAIL")):
        print(ln)
sys.exit(0 if "\nPASS" in "\n" + r.stdout else 1)
