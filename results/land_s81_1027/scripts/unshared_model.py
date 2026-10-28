"""LAND-S81-1: plan-model unshared clock per landed crossing (LCA of the two partition-entry chains in clk/tree.json).
Per cell delay = D0 + K * Manhattan(cell, parent cell) (region_clock.STAGE TT). Reports unshared max(side) vs the
LAND-HEAD-2 / COORD 19:14 target (<= ~3.4 ns TT), with and without the --region-equal pad stages (q*).
usage: unshared_model.py TREE.json LANDED_CROSSINGS.json OUT.json"""
import json
import sys
from collections import Counter

D0, K = 52.713, 0.058822
tree = json.load(open(sys.argv[1]))
lc = json.load(open(sys.argv[2]))
par, site = tree["parent_of"], tree["sites"]
memo = {}


def dly(c, pads):
    key = (c, pads)
    if key in memo:
        return memo[key]
    chain = []
    x = c
    while x is not None and (x, pads) not in memo:
        chain.append(x)
        x = par.get(x)
    base = memo[(x, pads)] if x is not None else 0.0
    for y in reversed(chain):
        p = par.get(y)
        if y.startswith("q") and not pads:
            v = base
        else:
            L = abs(site[y][0] - site[p][0]) + abs(site[y][1] - site[p][1]) if p else 0.0
            v = base + D0 + K * L
        memo[(y, pads)] = v
        base = v
    return memo[key]


def chain(c):
    out = [c]
    while c in par:
        c = par[c]
        out.append(c)
    return out


tap = {}
for t in tree["taps"]:
    if "__clk_t" in t["port"] or t["tap"].startswith("clk_t") or t["tap"] == "clk":
        tap.setdefault(t["part"], t)
for t in tree["taps"]:
    tap.setdefault(t["part"], t)
res = {}
for pads in (True, False):
    rows = []
    for r in lc["ports"]:
        a, b = tap.get(r["src"]), tap.get(r["dst"])
        if not a or not b:
            continue
        la, lb = tree["node_buf"][str(a["node"])], tree["node_buf"][str(b["node"])]
        ca, cb = chain(la), chain(lb)
        sb = set(cb)
        node = next(c for c in ca if c in sb)
        ua = dly(la, pads) - dly(node, pads)
        ub = dly(lb, pads) - dly(node, pads)
        rows.append(dict(port=r["port"], src=r["src"], dst=r["dst"], lca=node, unshared_ps=round(max(ua, ub), 1),
                         d_nom_ps=round(dly(lb, pads) - dly(la, pads), 1)))
    us = sorted(x["unshared_ps"] for x in rows)
    res["padded" if pads else "unpadded"] = dict(
        crossings=len(rows), unshared_max=us[-1], unshared_p50=us[len(us) // 2],
        over_3400=sum(u > 3400 for u in us), over_2000=sum(u > 2000 for u in us),
        hist_ns=dict(sorted(Counter(int(u // 1000) for u in us).items())),
        max_abs_d_nom=max(abs(x["d_nom_ps"]) for x in rows),
        worst5=sorted(rows, key=lambda x: -x["unshared_ps"])[:5])
json.dump(res, open(sys.argv[3], "w"), indent=1)
for k, v in res.items():
    print(k, json.dumps({kk: vv for kk, vv in v.items() if kk != "worst5"}))
