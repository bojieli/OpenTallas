"""DIE-KV-12: min-pulse-width die netlist (COORD 08:43/08:49: MPW on real register clock pins, both edges, not the
clock-only netlist).

die_mpw = die_trial STA die top (kit sta/die_top.v: all 160 partitions as stand-ins with their real DFFHQNx1 face flops behind
the OT_CLAT kit-insertion contract cell) + the built die clock tree (clock/ctree.v) inlined FLAT in the top with the combo
names (cells / internal nets ck_<x>, tap nets t_<inst>__<pin>, root = die clk port), every partition clock pin wired to ITS OWN
tap net (instead of the ideal 'clk' net of the die-STA top).
Routed clock delays = the combo GRT SDF (write_sdf after estimate_parasitics -global_routing): clock cells kept as written;
interconnects root -> clk, and leaf -> t_<tap> port re-pointed to the OT_CLAT input pin(s) of that tap inside the partition.
MAXONLY=1: early = late = the combo max delay (one corner, no OCV in this check; = the duty readout's slack_max_* basis).

usage: mk_mpw.py KIT CLKDIR SDF CORNER OUTDIR
"""
import os
import re
import sys
from pathlib import Path

kit, ckd, sdfp, corner, out = sys.argv[1:6]
out = Path(out)
out.mkdir(parents=True, exist_ok=True)
top = Path(kit, "sta/die_top.v").read_text()
cv = Path(ckd, "ctree.v").read_text()
mc = re.search(r"module\s+ctree\s*\(([^)]*)\);", cv, re.S)
cports = [p.strip() for p in mc.group(1).split(",") if p.strip()]
taps = set(p for p in cports if p.startswith("t_"))
P = set(cports)


def f(n):
    return "clk" if n == "root" else (n if n in P else "ck_" + n)


body = []
for line in cv[mc.end():cv.rindex("endmodule")].split("\n"):
    s = line.strip()
    if not s or s.startswith(("input", "output")):
        continue
    m = re.match(r"wire\s+(\w+)\s*;", s)
    if m:
        body.append(f"    wire {f(m.group(1))};")
        continue
    m = re.match(r"(\w+)\s+(\w+)\s*\((.*)\);", s)
    if m:
        conns = re.sub(r"\.(\w+)\((\w+)\)", lambda q: f".{q.group(1)}({f(q.group(2))})", m.group(3))
        body.append(f"    {m.group(1)} ck_{m.group(2)} ({conns});")
        continue
    m = re.match(r"assign\s+(\w+)\s*=\s*(\w+)\s*;", s)
    if m:
        body.append(f"    assign {f(m.group(1))} = {f(m.group(2))};")
        continue
    raise SystemExit("unparsed: " + s)

# stand-in clock pin -> OT_CLAT instance(s) on it, per module
clat = {}
for v in Path(kit, "sta/parts").glob("*/6_final.v"):
    t = v.read_text()
    mod = re.search(r"module\s+(\w+)", t).group(1)
    d = {}
    for m in re.finditer(r"OT_CLAT_\w+\s+(\w+)\s*\(\s*\.A\((\w+)\)", t):
        d.setdefault(m.group(2), []).append(m.group(1))
    clat[mod] = d

# ---- die top: per-instance clock pins -> own tap net
inst = mod = None
used, unmapped, loads = set(), [], {}
o = []
for ln in top.split("\n"):
    m = re.match(r"\s*(\w+)\s+(\w+)\s*\($", ln)
    if m and m.group(1) != "module":
        mod, inst = m.group(1), m.group(2)
    mm = re.match(r"(\s*)\.(clk(?:_t\d+)?)\(clk\)(,?)\s*$", ln)
    if mm and inst:
        t = f"t_{inst}__{mm.group(2)}"
        if t in taps:
            used.add(t)
            ln = f"{mm.group(1)}.{mm.group(2)}({t}){mm.group(3)}"
            loads[t] = [f"{inst}/{c}/A" for c in clat.get(mod, {}).get(mm.group(2), [])]
        else:
            unmapped.append(t)
    if re.match(r"\s*\);\s*$", ln):
        inst = None
    o.append(ln)
v = "\n".join(o)
mh = re.search(r"module\s+(\w+)\s*\(", v)
v = v.replace(f"module {mh.group(1)} (", "module die_mpw (", 1)
k = v.index(");", mh.end()) + 2
v = v[:k] + "\n" + "".join(f"    wire {t};\n" for t in sorted(taps)) + "\n".join(body) + "\n" + v[k:]
(out / "die_mpw.v").write_text(v)

# ---- SDF
txt = Path(sdfp).read_text()
head = re.sub(r'\(DESIGN\s+"[^"]*"\)', '(DESIGN "die_mpw")', txt[:txt.index("(CELL")])
cells = re.findall(r"\(CELL\s*\n.*?\n\s*\)\s*\n(?=\s*\(CELL|\s*\)\s*$)", txt[txt.index("(CELL"):], re.S)
keptc, ninter, ninst = [], 0, 0
for c in cells:
    mi = re.search(r"\(INSTANCE\s*([^)]*)\)", c)
    iname = mi.group(1).strip() if mi else ""
    if iname == "":
        L = []
        for ln in c.split("\n"):
            mm = re.match(r"(\s*)\(INTERCONNECT\s+(\S+)\s+(\S+)\s+(.*)$", ln)
            if not mm:
                L.append(ln.replace('(CELLTYPE "die_combo")', '(CELLTYPE "die_mpw")'))
                continue
            a, b, rest = mm.group(2), mm.group(3), mm.group(4)
            if a == "root" and b.startswith("ck_"):
                L.append(f"{mm.group(1)}(INTERCONNECT clk {b} {rest}")
                ninter += 1
            elif a.startswith("ck_") and b.startswith("ck_"):
                L.append(ln)
                ninter += 1
            elif a.startswith("ck_") and b in taps:
                for pin in loads.get(b, []):
                    L.append(f"{mm.group(1)}(INTERCONNECT {a} {pin} {rest}")
                    ninter += 1
        keptc.append("\n".join(L))
    elif iname.startswith("ck_"):
        keptc.append(c)
        ninst += 1
sdf = head + "".join(k_.rstrip() + "\n" for k_ in keptc) + ")\n"
if os.environ.get("MAXONLY") == "1":
    sdf = re.sub(r"\(([-\d.]+)::([-\d.]+)\)", lambda m: f"({m.group(2)}::{m.group(2)})", sdf)
(out / f"die_{corner}.sdf").write_text(sdf)
missing = sorted(taps - used)
print(f"die_mpw: taps {len(taps)} wired {len(used)} unwired_taps {len(missing)} unmapped_pins {len(unmapped)} "
      f"taps_without_clat {sum(1 for t in used if not loads.get(t))} sdf_cells {ninst} interconnects {ninter} "
      f"maxonly {os.environ.get('MAXONLY') == '1'}")
if missing:
    print("unwired taps (first 10):", missing[:10])
if unmapped:
    print("partition clock pins without a tap (first 10):", unmapped[:10])
