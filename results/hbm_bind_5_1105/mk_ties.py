#!/usr/bin/env python3
"""declared_ties rows from a bind_tied.json. Every row is a candidate: COORD 07:3x C4b/C4c/C5 unproven until SS33-TOK; C1 until the RS=1 miter. usage: mk_ties.py TIED MAP PLAN OUT"""
import json, sys, collections
t, mp, pl, out = sys.argv[1:5]
Tied = json.load(open(t)); M = json.load(open(mp))["parts"]; P = json.load(open(pl)); pt = {p["name"]: p["type"] for p in P["partitions"]}
rows = collections.defaultdict(set); vals = {}
for r in Tied:
    src = " ".join(r.get("sources", []))
    top = r["path"].split(".")[0]
    tp = pt.get(M[top][0]) if top in M else None
    types = [tp] if tp else sorted(set(pt.values()))
    for i, v in zip(r["bits"], r["values"]):
        rows[(r["module"], r["port"], i, v)].update(types)
# merge contiguous bits
g = collections.defaultdict(list)
for (m, p, i, v), ts in rows.items(): g[(m, p, v, tuple(sorted(ts)))].append(i)
res = []
for (m, p, v, ts), bits in sorted(g.items()):
    bits = sorted(bits); a = b = bits[0]
    for x in bits[1:] + [None]:
        if x == b + 1 if x is not None else False: b = x; continue
        cls = "C1 single-row calendar, RS=1 miter pending" if "keybuf" in m or "idxn" in m else "C4b/C4c/C5 S-role idle, SS33-TOK token bit-exact pending"
        res.append(dict(types=list(ts), module=m, port=p, bits=[a, b], value=v, proof="UNPROVEN candidate, COORD ruling 07:3x: " + cls))
        if x is not None: a = b = x
json.dump(res, open(out, "w"), indent=1)
print("rows", len(res), "bits", sum(r["bits"][1] - r["bits"][0] + 1 for r in res), "input tied", sum(len(r["bits"]) for r in Tied))
print(collections.Counter(r["module"][:44] + "." + r["port"] for r in res).most_common(12))
