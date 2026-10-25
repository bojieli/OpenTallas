#!/usr/bin/env python3
"""PATH-HBM-SM 10-25: per-flow alignment + pin-to-pin reach audit of the hnx-sm4p cluster halves (GEOM-REVIEW 10:29
items (4)/(f)).  Connectivity = yosys JSON of the half RTL with the 8 child modules blackboxed (conn_<h>.json); flows
traced child/half pin -> pure relay flops (D == a traced bit) -> child/half pin.  Pin positions = kit pin tables
(_views/<module>.pins.json) at the spec origins (MX mirrors y) and the half pins tcl.  Output flows_<h>.tsv + summary."""
import json, re, sys, collections
from pathlib import Path
A = Path(sys.argv[1]); G = Path(sys.argv[2]); h = sys.argv[3]
spec = json.load(open(A / f"half_{h}.json"))
W, H = spec["outline"]["w"], spec["outline"]["h"]
J = json.load(open(A / f"conn_{h}.json"))
top = J["modules"][spec["top"]]
# child pin positions
pins = {}
for c in spec["children"]:
    mod = c["view"].split("/")[-1]
    v = json.load(open(G / f"views_{mod}.json"))["view_list"][0]
    cw, ch = v["outline_um"]
    for p in json.load(open(G / Path(v["pins_file"]).name)):
        y = ch - p["y"] if c["orient"] == "MX" else p["y"]
        pins[(c["inst"], p["name"])] = (c["at"][0] + p["x"], c["at"][1] + y)
for m in re.finditer(r"place_pin -pin_name \{([^}]+)\} -layer (\w+) -location \{([-0-9.]+) ([-0-9.]+)\}", open(A / f"half_{h}_pins.tcl").read()):
    pins[("TOP", m.group(1))] = (float(m.group(3)), float(m.group(4)))
child_insts = {c["inst"]: c["view"].split("/")[-1] for c in spec["children"]}
# bit -> endpoints
drv, snk = {}, collections.defaultdict(list)
def pname(port, i, n):
    return port if n == 1 else f"{port}[{i}]"
for pn, p in top["ports"].items():
    for i, b in enumerate(p["bits"]):
        if isinstance(b, int):
            (drv.__setitem__(b, ("TOP", pname(pn, i, len(p["bits"])))) if p["direction"] == "input" else snk[b].append(("TOP", pname(pn, i, len(p["bits"])))))
relay = {}   # D bit -> list of Q bits (pure relay flops)
nflop = 0
miss = collections.Counter()
for cn, c in top["cells"].items():
    t = c["type"]
    if t in ("$dff", "$adff", "$sdff", "$dffe", "$adffe", "$sdffe"):
        nflop += sum(1 for _ in c["connections"]["Q"])
        for d, q in zip(c["connections"]["D"], c["connections"]["Q"]):
            if isinstance(d, int) and isinstance(q, int):
                relay.setdefault(d, []).append(q)
        continue
    inst = cn.lstrip("\\")
    if inst in child_insts:
        dirs = c.get("port_directions", {})
        for pn, bits in c["connections"].items():
            for i, b in enumerate(bits):
                if not isinstance(b, int):
                    continue
                ep = (inst, pname(pn, i, len(bits)))
                if ep not in pins:
                    miss[inst] += 1
                if dirs.get(pn) == "output":
                    drv[b] = ep
                else:
                    snk[b].append(ep)
flows = collections.defaultdict(list)
for b, src in drv.items():
    if src[0] == "TOP" and False:
        continue
    frontier, st, seen = [b], 0, {b}
    while frontier and st <= 8:
        nxt = []
        for x in frontier:
            for e in snk.get(x, []):
                if e[0] != src[0] or True:
                    flows[(src[0], re.sub(r"\[\d+\]$", "", src[1]), e[0], re.sub(r"\[\d+\]$", "", e[1]), st)].append((src, e))
            for q in relay.get(x, []):
                if q not in seen:
                    seen.add(q); nxt.append(q)
        frontier, st = nxt, st + 1
rows = []
for (si, sp, di, dp, st), prs in flows.items():
    if si == di:
        continue
    ps = [(pins.get(s), pins.get(d)) for s, d in prs]
    ps = [(a, b) for a, b in ps if a and b]
    if not ps:
        continue
    dx = max(abs(a[0] - b[0]) for a, b in ps); dy = max(abs(a[1] - b[1]) for a, b in ps)
    man = max(abs(a[0] - b[0]) + abs(a[1] - b[1]) for a, b in ps)
    sx = (min(a[0] for a, _ in ps), max(a[0] for a, _ in ps)); sy = (min(a[1] for a, _ in ps), max(a[1] for a, _ in ps))
    tx = (min(b[0] for _, b in ps), max(b[0] for _, b in ps)); ty = (min(b[1] for _, b in ps), max(b[1] for _, b in ps))
    rows.append(dict(src=f"{si}.{sp}", dst=f"{di}.{dp}", relay_stages=st, bits=len(ps),
                     src_span=f"x{sx[0]:.0f}-{sx[1]:.0f} y{sy[0]:.0f}-{sy[1]:.0f}", dst_span=f"x{tx[0]:.0f}-{tx[1]:.0f} y{ty[0]:.0f}-{ty[1]:.0f}",
                     max_dx=round(dx, 1), max_dy=round(dy, 1), max_manhattan=round(man, 1),
                     reach_per_stage=round(man / (st + 1), 1)))
rows.sort(key=lambda r: -r["max_manhattan"])
with open(A / f"flows_{h}.tsv", "w") as f:
    keys = list(rows[0].keys()) if rows else []
    f.write("\t".join(keys) + "\n")
    for r in rows:
        f.write("\t".join(str(r[k]) for k in keys) + "\n")
over = [r for r in rows if r["reach_per_stage"] > 405]
print(json.dumps(dict(half=h, flops_glue=nflop, flows=len(rows), bits=sum(r["bits"] for r in rows),
                      over_405_per_stage=len(over), worst=rows[:8], unplaced_child_pins=dict(miss)), indent=1))
