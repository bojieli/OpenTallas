import json, sys
from collections import defaultdict
plan = json.load(open(sys.argv[1])); S = json.load(open(sys.argv[2])); T = sys.argv[3]
parts = {p["name"]: p for p in plan["partitions"]}
inst = defaultdict(list)
for name, c in S["cell_sites"].items():
    if c["kind"].startswith("chan") or parts[c["part"]]["type"] != T: continue
    p = parts[c["part"]]; (x0, y0), (w, h) = p["origin_um"], plan["partition_types"][p["type"]]["outline_um"]; o = p.get("orient", "R0")
    x, y = c["origin_um"]
    tx = (x0 + w - x - c["w"]) if o in ("MY", "R180") else x - x0
    ty = (y0 + h - y - 0.27) if o in ("MX", "R180") else y - y0
    inst[(c["part"], o)].append((round(tx, 3), round(ty, 3), c["kind"]))
ks = sorted(inst)
a = next(k for k in ks if k[1] == "MX"); b = next(k for k in ks if k[1] != "MX")
A, B = set(inst[a]), set(inst[b])
print(a, len(A), b, len(B)); print("onlyA", sorted(A - B)[:8]); print("onlyB", sorted(B - A)[:8])
