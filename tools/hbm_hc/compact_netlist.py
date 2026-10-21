#!/usr/bin/env python3
"""HBM-HC7-TAILK 10-20: commit-size form of a Yosys write_verilog -noattr gate netlist (the gate-level cloned tail child,
tools/hbm_hc/bound_fanout_clone.py + retained re-synth).  Pure text transform, function unchanged:
  * module NAME -> --top (the element name the parent instantiates);
  * 1-bit internal 'wire x;' declarations packed many per line; port declarations kept as written;
  * each cell instance on one line;
  * --clock-net NAME: the unique non-port net that drives CLK pins (the generated /SDIV sink clock, one flop + INV) is
    renamed NAME so the kit SDC can create_generated_clock on its driver pin.
usage: compact_netlist.py IN.v OUT.v --top T [--clock-net sclk] [--header TEXT]
"""
import argparse
import re
import sys

ap = argparse.ArgumentParser()
ap.add_argument("inp"); ap.add_argument("out")
ap.add_argument("--top", required=True)
ap.add_argument("--clock-net")
ap.add_argument("--header", default="")
a = ap.parse_args()

text = open(a.inp).read()
mods = re.findall(r"^module\s+(\S+?)\s*\(", text, re.M)
if len(mods) != 1:
    sys.exit(f"expected one module, found {mods}")
text = re.sub(r"^module\s+" + re.escape(mods[0]) + r"\b", "module " + a.top, text, count=1, flags=re.M)
ports = set(re.findall(r"^\s*(?:input|output|inout)\s+(?:\[[^\]]*\]\s*)?(\S+?)\s*;", text, re.M))
if a.clock_net:
    clk_nets = set(re.findall(r"\.CLK\(([^)\s]+)\)", text)) - ports
    if len(clk_nets) != 1:
        sys.exit(f"--clock-net: expected one non-port CLK net, found {sorted(clk_nets)[:8]}")
    old = clk_nets.pop()
    if re.search(r"\b" + re.escape(a.clock_net) + r"\b", text):
        sys.exit(f"--clock-net {a.clock_net} already used")
    text = re.sub(r"(?<![\w$\\])" + re.escape(old) + r"(?![\w$\[])", a.clock_net, text)
    print(f"clock net {old} -> {a.clock_net}")

out, wires, inst = [], [], None
for line in text.splitlines():
    m = re.match(r"^\s*wire\s+([^\s\[;]+)\s*;\s*$", line)
    if m:
        if m.group(1) not in ports:
            wires.append(m.group(1))
            continue
    if inst is not None:
        inst.append(line.strip())
        if line.strip().endswith(");"):
            out.append("  " + "".join(inst)); inst = None
        continue
    if re.match(r"^\s+\w+_ASAP7_75t_\w+\s+\S+\s*\($", line):
        inst = [line.strip()]
        continue
    out.append(line)
if inst is not None:
    sys.exit("unterminated instance")
# wire block right after the port declarations (before the first instance / assign)
first = next(i for i, l in enumerate(out) if re.match(r"^\s+(\w+_ASAP7_75t_\w+\s|assign\s)", l))
wl, cur = [], []
for w in wires:
    cur.append(w)
    if len(cur) == 24:
        wl.append("  wire " + ", ".join(cur) + ";"); cur = []
if cur:
    wl.append("  wire " + ", ".join(cur) + ";")
hdr = ["// " + h for h in a.header.splitlines()] if a.header else []
res = "\n".join(hdr + out[:first] + wl + out[first:]) + "\n"
open(a.out, "w").write(res)
ncell = sum(1 for l in out if re.match(r"^\s+\w+_ASAP7_75t_\w+\s", l))
print(f"top {a.top} cells {ncell} wires {len(wires)} bytes {len(res)}")
