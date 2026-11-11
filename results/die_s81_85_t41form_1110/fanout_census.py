"""T41FORM fanout census: loads (cell input pins + output ports) per net of each module of a gate netlist
(per module definition: a kept-hierarchy module counts once; net key = module:net).
usage: python3 -I fanout_census.py NETLIST.v LIMIT OUT.json"""
import json, re, sys
from collections import Counter, defaultdict
path, limit, out = sys.argv[1], int(sys.argv[2]), sys.argv[3]
OUT_PINS = {"Y", "Q", "QN", "CON", "SN", "H", "L"}
full = open(path).read()
loads = Counter(); drv = {}
outports = set()
mods = re.findall(r"^module\s+(\\\S+|\S+?)\s*\((.*?)^endmodule", full, re.M | re.S)
inst_re = re.compile(r"^\s*([A-Za-z_][\w$]*)\s+(\\\S+|[A-Za-z_][\w$\[\].]*)\s*\((.*?)\);", re.M | re.S)
pin_re = re.compile(r"\.(\w+)\s*\(\s*(\\\S+\s|[^()]*?)\s*\)")
ncell = 0
nmods = 0
for mname, txt in mods:
  nmods += 1
  mname = mname.strip()
  for d, rng, names in re.findall(r"^\s*(input|output|inout)\s+(\[[^\]]+\])?\s*([^;]+);", txt, re.M):
    if d == "output":
        for n in names.split(","):
            outports.add(mname + ":" + n.strip())
  for cell, inst, body in inst_re.findall(txt):
    if cell in ("module", "input", "output", "wire", "assign"):
        continue
    ncell += 1
    for pin, net in pin_re.findall(body):
        net = net.strip()
        if not net or net.startswith("{") or "'" in net:
            continue
        net = mname + ":" + net
        if pin in OUT_PINS:
            drv[net] = cell
        else:
            loads[net] += 1
  for a, b in re.findall(r"^\s*assign\s+(\S+)\s*=\s*(\S+?)\s*;", txt, re.M):
    if mname + ":" + a.split("[")[0] in outports:
        loads[mname + ":" + b] += 1
def cls(n):
    n = n.rsplit(":", 1)[-1]
    if re.search(r"(^|[./\\])clk(_t\d+|_c\d+)?(\b|\s|$)|fclk|clk_t\d", n): return "clock"
    if re.search(r"rst|reset|start", n): return "reset/start"
    if "u_dsel" in n or "u_sel" in n or re.search(r"dch\[\d+\]", n): return "dsel_select"
    return "data/control"
over = sorted(((c, n) for n, c in loads.items() if c > limit), reverse=True)
by = defaultdict(list)
for c, n in over:
    by[cls(n)].append((n, c, drv.get(n, "port/assign")))
rec = dict(schema="opentallas.t41form.fanout_census.v1", netlist=path, modules=nmods, cells=ncell, nets_with_loads=len(loads), limit=limit,
           nets_over=len(over), max_fanout=over[0][0] if over else max(loads.values()),
           by_class={k: dict(n=len(v), max=max(x[1] for x in v), top=v[:15]) for k, v in by.items()},
           hist={k: sum(1 for c in loads.values() if lo <= c <= hi) for k, (lo, hi) in
                 {"1": (1, 1), "2-8": (2, 8), "9-24": (9, 24), "25-64": (25, 64), "65-256": (65, 256), ">256": (257, 10**9)}.items()})
json.dump(rec, open(out, "w"), indent=1)
print(json.dumps({k: rec[k] for k in ("modules", "cells", "limit", "nets_over", "max_fanout", "hist")}))
for k, v in rec["by_class"].items():
    print(k, v["n"], "max", v["max"], [t[:2] for t in v["top"][:4]])
