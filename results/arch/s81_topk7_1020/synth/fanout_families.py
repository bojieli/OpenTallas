#!/usr/bin/env python3
"""Name the >32-load families of a flat yosys netlist (1_2_yosys.v): for each net over the limit print driver cell
type/name, the register(s) feeding it (comb: trace back <=4 levels), and a sample of the load cells' output nets.
usage: fanout_families.py NETLIST [LIMIT]"""
import re, sys, collections
p = sys.argv[1]; LIM = int(sys.argv[2]) if len(sys.argv) > 2 else 32
txt = open(p).read()
cells = []  # (type, name, {pin: net})
for m in re.finditer(r"^\s*([A-Za-z0-9_$\\]+)\s+(\\\S+|[A-Za-z0-9_$.\[\]]+)\s*\((.*?)\);", txt, re.S | re.M):
    t, n, body = m.group(1), m.group(2), m.group(3)
    if t in ("module", "input", "output", "wire", "assign", "endmodule"):
        continue
    pins = dict((a, b.strip()) for a, b in re.findall(r"\.(\w+)\(([^()]*)\)", body))
    cells.append((t, n, pins))
OUTP = {"Y", "Q", "QN", "CON", "SN", "L", "H", "rd_out"}
TRANS = re.compile(r"^(BUF|INV|HB)")
drv = {}; loads = collections.defaultdict(list)
for i, (t, n, pins) in enumerate(cells):
    for pn, net in pins.items():
        if not net or net.startswith("1'"):
            continue
        if pn in OUTP or pn.startswith("rd_out"):
            drv[net] = i
        else:
            loads[net].append(i)
def outnet(i):
    t, n, pins = cells[i]
    for k in ("Q", "QN", "Y", "CON", "SN"):
        if k in pins:
            return pins[k]
    return "?"
def isff(i):
    return "DFF" in cells[i][0] or "ASYNC" in cells[i][0]
def back(net, d=0):
    if net not in drv:
        return [net]
    i = drv[net]
    if isff(i) or d >= 4:
        return [cells[i][1]]
    r = []
    for pn, nn in cells[i][2].items():
        if pn not in OUTP:
            r += back(nn, d + 1)
    return r
def tree(net, seen=None):
    out = []
    for j in loads.get(net, []):
        if TRANS.match(cells[j][0]):
            out += tree(outnet(j))
        else:
            out.append(j)
    return out
def isroot(net):
    i = drv.get(net)
    return i is None or not TRANS.match(cells[i][0])
fam = collections.Counter(); rows = []
for net in list(loads):
    if not isroot(net) or net in ("ck",) or net.startswith("_") and net not in drv:
        continue
    ls = tree(net)
    if len(ls) <= LIM:
        continue
    i = drv.get(net)
    dt = cells[i][0] if i is not None else "PORT"
    dn = cells[i][1] if i is not None else net
    src = sorted(set(back(net)))[:6] if i is not None and not isff(i) else [dn]
    lt = collections.Counter(re.sub(r"\[\d+\]|\d+", "#", outnet(j)) for j in ls).most_common(3)
    key = re.sub(r"\d+", "#", " ".join(src[:2]))
    fam[key] += 1
    rows.append((len(ls), dt, dn, net, src, lt))
rows.sort(key=lambda r: -r[0])
print("VIOL", len(rows))
for k, c in fam.most_common(80):
    print("FAM", c, k)
for r in rows[:400]:
    print("NET", r[0], r[1], r[2], "|src", " ".join(r[4]), "|loads", r[5])
