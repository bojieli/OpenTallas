#!/usr/bin/env python3
"""DIE-HBM-35 estimate (12.13 locality first): connectivity-driven row order for the NE half (NW mirrors).
Demand W = planned bus widths (bind_latency buses src/dst) + strict-bind UNPLANNED bits (bind_report errors).
Rows: S row (y 4510-6065) and N row (y 10385-11958) members keep outline + row y; order changes, packed from the row's
original x0 (abutting).  Cost = sum W * Manhattan(centres); local search (all swaps + insertions) to a local optimum.
Also prints: bits that must cross the b0xx strip column (hub-side x < 23258.88 <-> east of it) before/after.
usage: est_rows.py PLAN BIND_LATENCY BIND_REPORT OUT_JSON"""
import sys, json, re, collections, itertools
P = json.load(open(sys.argv[1]))
T = P["partition_types"]
geo = {}
for x in P["partitions"]:
    w, h = T[x["type"]]["outline_um"]
    if "90" in x["orient"] or "270" in x["orient"]:
        w, h = h, w
    geo[x["name"]] = [x["origin_um"][0], x["origin_um"][1], w, h]
W = collections.Counter()
for b in json.load(open(sys.argv[2]))["buses"]:
    W[tuple(sorted((b["src"], b["dst"])))] += b["width"]
unpl = collections.Counter()
for e in json.load(open(sys.argv[3]))["errors"]:
    m = re.match(r"UNPLANNED (\S+) -> (\S+): (\d+) as-built", e)
    if m:
        k = tuple(sorted((m[1], m[2])))
        W[k] += int(m[3]); unpl[k] += int(m[3])
def rowmembers(y0):
    return sorted([n for n, g in geo.items() if n.startswith("NE_") and abs(g[1] - y0) < 1], key=lambda n: geo[n][0])
SROW, NROW = rowmembers(4510.08), rowmembers(10385.28)
def cen(g, n):
    x, y, w, h = g[n]; return (x + w / 2, y + h / 2)
def cost(g, only=None):
    c = 0.0
    for (a, b), v in W.items():
        if a not in g or b not in g:
            continue
        if only and a not in only and b not in only:
            continue
        (xa, ya), (xb, yb) = cen(g, a), cen(g, b)
        c += v * (abs(xa - xb) + abs(ya - yb))
    return c
def place(g, row, order):
    x = min(g[n][0] for n in row)
    for n in order:
        g[n][0] = x; x += g[n][2]
XB = 23258.88
def column_bits(g):
    s = 0
    for (a, b), v in W.items():
        if a in g and b in g and a.startswith(("NE_", "root")) and b.startswith(("NE_", "root")):
            ca, cb = cen(g, a)[0], cen(g, b)[0]
            if (ca < XB) != (cb < XB) and not (a.startswith("NE_b0") or b.startswith("NE_b0") or "io" in a or "io" in b):
                s += v
    return s
def unpl_cost(g):
    return sum(v * (abs(cen(g, a)[0] - cen(g, b)[0]) + abs(cen(g, a)[1] - cen(g, b)[1])) for (a, b), v in unpl.items() if a in g and b in g)
g0 = {k: list(v) for k, v in geo.items()}
res = dict(before=dict(cost=cost(g0), unplanned_bit_um=unpl_cost(g0), column_bits=column_bits(g0), S=SROW, N=NROW))
fixed = set(sys.argv[5].split(",")) if len(sys.argv) > 5 and sys.argv[5] else set()
g = {k: list(v) for k, v in geo.items()}
for row in (SROW, NROW):
    order = list(row)
    best = cost(g, set(row))
    improved = True
    while improved:
        improved = False
        for i, j in itertools.permutations(range(len(order)), 2):
            if order[i] in fixed or order[j] in fixed:
                continue
            for mode in ("swap", "ins"):
                o = list(order)
                if mode == "swap":
                    o[i], o[j] = o[j], o[i]
                else:
                    o.insert(j, o.pop(i))
                if any(o.index(f) != order.index(f) for f in fixed if f in o):
                    continue
                place(g, row, o)
                c = cost(g, set(row))
                if c < best - 1e-6:
                    best, order, improved = c, o, True
                else:
                    place(g, row, order)
        place(g, row, order)
    res["S_order" if row is SROW else "N_order"] = order
res["after"] = dict(cost=cost(g), unplanned_bit_um=unpl_cost(g), column_bits=column_bits(g))
res["moves_um"] = {n: round(g[n][0] - geo[n][0], 2) for n in SROW + NROW if abs(g[n][0] - geo[n][0]) > 0.01}
json.dump(res, open(sys.argv[4], "w"), indent=1)
print(json.dumps(res, indent=1))
