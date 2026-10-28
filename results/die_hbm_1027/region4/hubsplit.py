#!/usr/bin/env python3
"""DIE-HBM-4 (12.14b ESTIMATE, no build): split each soft hub (8.22 x 4.32 mm) into W/E clock regions so in-region spread
<= 150 ps (12.15c).  Scans the vertical cut x (hub-local) for the fewest hub-internal station bits crossing it; members
(hard cores + soft contents) go to the side of their centre; each half's spread uses the member bbox (spread.py model).
Writes a slim split plan (parts/ports/die only) with 2 synthetic ports per hub (W->E, E->W bits of the cut stations),
external ports reassigned by face window, and the region map with R(hub) -> R(hub)W / R(hub)E.
usage: hubsplit.py PLAN MAP OUTDIR"""
import json, math, sys, copy, collections
from pathlib import Path
P = json.load(open(sys.argv[1])); MP = json.load(open(sys.argv[2]))["part_region"]; OUT = Path(sys.argv[3])
V = (219.2, 278.6, 366.4)
def spread(w, h, v):   # mm -> ps (spread.py model, UNCHECKED)
    I = v * (w + h) / 2
    return I * (0.0511 + 0.03 + 0.0021 * math.hypot(w, h)) + 20
T = P["partition_types"]; rep = {}
newparts, newtypes = [], {}
for p in P["partitions"]:
    t = T[p["type"]]
    if p["name"].endswith("_hub") and not t.get("hard"):
        W, H = t["outline_um"]
        mem = [(c["origin_um"], c["outline_um"]) for c in t["hard_cores"]] + \
              [(c["origin_um"], c["outline_um"]) for c in t["contents"] if c.get("origin_um") and c.get("outline_um")]
        st = t["internal_stations"]
        best = None; scan = []
        for i in range(int(2900 / 8.64), int(5300 / 8.64) + 1):
            xc = i * 8.64
            bw = sum(s["bits"] for s in st if s["from_um"][0] < xc <= s["to_um"][0])
            be = sum(s["bits"] for s in st if s["to_um"][0] < xc <= s["from_um"][0])
            L = [m for m in mem if m[0][0] + m[1][0] / 2 < xc]; R = [m for m in mem if m[0][0] + m[1][0] / 2 >= xc]
            xl = max([xc] + [m[0][0] + m[1][0] for m in L]); xr = min([xc] + [m[0][0] for m in R])
            strad = sum(1 for m in mem if m[0][0] < xc < m[0][0] + m[1][0])
            wl, wr = xl / 1000, (W - xr) / 1000
            s279 = max(spread(wl, H / 1000, 278.6), spread(wr, H / 1000, 278.6))
            row = dict(x=round(xc, 2), bits_we=bw, bits_ew=be, straddle=strad, wL=round(wl, 3), wR=round(wr, 3),
                       spread279=round(s279, 1))
            scan.append(row)
            if s279 <= 150 and (best is None or bw + be < best["bits_we"] + best["bits_ew"]):
                best = row
        xc = best["x"]
        rep[p["name"]] = dict(best=best, stations=len(st), station_bits=sum(s["bits"] for s in st),
                              spread_unsplit={v: round(spread(W / 1000, H / 1000, v), 1) for v in V},
                              spread_halves={v: [round(spread(best["wL"], H / 1000, v), 1),
                                                 round(spread(best["wR"], H / 1000, v), 1)] for v in V},
                              scan_min_bits=min(r["bits_we"] + r["bits_ew"] for r in scan),
                              scan_mid=[r for r in scan if abs(r["x"] - W / 2) < 5])
        x0, y0 = p["origin_um"]
        for side, ox, w in (("W", x0, xc), ("E", x0 + xc, W - xc)):
            tn = p["type"] + "_" + side
            newtypes[tn] = dict(outline_um=[w, H], hard=False)
            newparts.append(dict(name=p["name"] + side, type=tn, origin_um=[ox, y0]))
        rep[p["name"]]["cut_abs_x"] = x0 + xc; rep[p["name"]]["x0"] = x0
        bf = collections.defaultdict(collections.Counter)   # bus -> face-point x (the station end on the outline), bit-weighted
        for s in st:
            if s["conn"].startswith("bus:"):
                pt = min((s["from_um"], s["to_um"]), key=lambda a: min(a[0], W - a[0], a[1], H - a[1]))
                bf[s["conn"][4:]][round(pt[0], 1)] += s["bits"]
        rep[p["name"]]["bus_face_x"] = {b: c.most_common(1)[0][0] for b, c in bf.items()}
    else:
        newtypes[p["type"]] = dict(outline_um=t["outline_um"], hard=bool(t.get("hard")))
        newparts.append(dict(name=p["name"], type=p["type"], origin_um=p["origin_um"]))
ports = []
for q in P["ports"]:
    q = copy.deepcopy(q)
    for e in ("src", "dst"):
        n = q[e]["part"]
        if n in rep:
            f = q.get("face"); win = q.get("window_um")
            cut = rep[n]["cut_abs_x"]
            fx = rep[n]["bus_face_x"].get(q[e].get("bus"))
            if fx is not None: side = "W" if fx < cut - rep[n]["x0"] else "E"
            elif f == "W": side = "W"
            elif f == "E": side = "E"
            elif win: side = "W" if (win[0] + win[1]) / 2 < cut else "E"
            else: side = "?"
            rep[n].setdefault("port_src", collections.Counter())["face_pt" if fx is not None else "window"] += 1
            rep[n].setdefault("port_side", collections.Counter())[side] += 1
            q[e]["part"] = n + side
    ports.append(q)
for n, r in rep.items():
    b = r["best"]
    ports.append(dict(id=f"HX_{n}_WE", src=dict(part=n + "W"), dst=dict(part=n + "E"), width=b["bits_we"], kind="data"))
    ports.append(dict(id=f"HX_{n}_EW", src=dict(part=n + "E"), dst=dict(part=n + "W"), width=b["bits_ew"], kind="data"))
OUT.mkdir(parents=True, exist_ok=True)
json.dump(dict(partition_types=newtypes, partitions=newparts, ports=ports, die=P["die"], budgets=P.get("budgets", {})),
          open(OUT / "plan_hubsplit.json", "w"))
mp = {}
for n, g in MP.items():
    if n in rep:
        mp[n + "W"] = g + "W"; mp[n + "E"] = g + "E"
    else:
        mp[n] = g
json.dump(dict(part_region=mp), open(OUT / "map_hubsplit.json", "w"), sort_keys=True)
json.dump(rep, open(OUT / "hubsplit_report.json", "w"), indent=1, default=dict)
print(json.dumps(rep, default=dict, indent=1))
