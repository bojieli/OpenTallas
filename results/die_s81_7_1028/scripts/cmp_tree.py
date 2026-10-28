#!/usr/bin/env python3
"""DIE-S81-7: compare two clock tree.json: nodes/taps identical outside region R? (x, y, parent path, kids count)"""
import json, sys
a, b = (json.load(open(f)) for f in sys.argv[1:3]); R = sys.argv[3] if len(sys.argv) > 3 else None
def sig(t):
    N = {int(k): v for k, v in t["nodes"].items()}
    path = {0: "h"}; st = [0]
    while st:
        i = st.pop()
        for k, c in enumerate(N[i]["kids"]):
            path[c] = path[i] + str(k); st.append(c)
    # region membership: dme tag or region_root
    out = {}
    for i, n in N.items():
        out[path[i]] = (round(n["x"], 3), round(n["y"], 3), n.get("dme") or n.get("region_root"), len(n["kids"]))
    return out
sa, sb = sig(a), sig(b)
diff = [p for p in set(sa) | set(sb) if sa.get(p) != sb.get(p)]
inR = [p for p in diff if (sa.get(p) or sb.get(p))[2] == R]
print("nodes a/b", len(sa), len(sb), "differ", len(diff), "of which in", R, len(inR), "outside", len(diff) - len(inR))
print("outside examples", [(p, sa.get(p), sb.get(p)) for p in diff if p not in inR][:5])
print("wire_um a/b", a["meta"].get("wire_um"), b["meta"].get("wire_um"), "repeaters", a["meta"].get("repeaters"), b["meta"].get("repeaters"))
