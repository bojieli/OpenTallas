# our planner's routed stats for the region below the LCA: cells, per-path stages, latency LCA->tap, spread (incl declared insertion)
import json, sys, re, collections
reg, ctree, arrTT, arrFF, legs = sys.argv[1:6]
r = json.load(open(reg)); lca = r["lca"]
T = json.load(open(sys.argv[6])); N = T["nodes"]
sub = set()
for t in r["taps"]:
    n = t["node"]["id"]
    while n != lca: sub.add(n); n = N[str(n)]["parent"]
cells = {}
for l in open(ctree):
    m = re.match(r"\s*(\w+_ASAP7_75t_R)\s+(\S+)\s*\(\.A\((\S+)\),\s*\.Y\((\S+)\)\)", l)
    if m: cells[m.group(2)] = (m.group(1), m.group(3), m.group(4))
drv = {v[2]: k for k, v in cells.items()}
def nid(c):
    m = re.match(r"[br](\d+)", c); return int(m.group(1)) if m else None
mine = {c for c in cells if nid(c) in sub}
# wire: sum of node->parent manhattan for sub nodes (planned, pre-route) + detours
wl = sum(abs(N[str(n)]["x"] - N[str(N[str(n)]["parent"])]["x"]) + abs(N[str(n)]["y"] - N[str(N[str(n)]["parent"])]["y"]) + N[str(n)].get("detour_um", 0) for n in sub)
def rd(f):
    a, m = {}, {}
    for l in open(f):
        s = l.split()
        if s[0] == "T": a[s[1]] = float(s[2])
        if s[0] == "M": m[s[1]] = float(s[2])
    return a, m
out = dict(cells_below_lca=len(mine), cell_types=collections.Counter(cells[c][0] for c in mine), planned_wire_um=round(wl, 1))
# per-tap stage count below LCA: walk drivers from tap net
for C, f in (("TT", arrTT), ("FF", arrFF)):
    a, m = rd(f); root = m.get(f"b{lca}")
    lat = [a[t["port"]] - root for t in r["taps"]]
    out[C] = dict(lca_arr=root, lat_min=round(min(lat), 1), lat_max=round(max(lat), 1),
                  spread_incl_ins=round(max(a[t["port"]] + r.get("lat_" + C, {}).get(t["port"], 0) for t in r["taps"]) - min(a[t["port"]] + r.get("lat_" + C, {}).get(t["port"], 0) for t in r["taps"]), 1))
    gl = [a[t["port"]] - root for t in r["taps"] if "__clk_c" not in t["port"]]
    out[C]["glue_lat_min_max"] = [round(min(gl), 1), round(max(gl), 1)]
print(json.dumps(out))
