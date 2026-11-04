#!/usr/bin/env python3
"""DIE-HBM-61/SPLIT d44v part 6: connectivity of a SPLIT composition (yosys write_json, subs blackboxed) ->
per sub instance, per port bit: the composition (= kit core) top pin bits it reaches and the peer sub instances.
    split_conn.py NETLIST.json TOP OUT.json"""
import json, sys
from collections import defaultdict
J = json.load(open(sys.argv[1])); top = sys.argv[2]; M = J["modules"][top]
def names(pname, p):
    b = p["bits"]; w = len(b); off = p.get("offset", 0); up = p.get("upto", 0)
    if w == 1 and not off and "[" not in pname and not p.get("_vec"):
        return [pname]
    return [f"{pname}[{(off + w - 1 - i) if up else (off + i)}]" for i in range(w)]
bit_top = defaultdict(list)
for pn, p in M["ports"].items():
    for nm, b in zip(names(pn, p), p["bits"]):
        bit_top[b].append(nm)
subs = {n: c for n, c in M["cells"].items() if c["type"] in J["modules"] and J["modules"][c["type"]].get("attributes", {}).get("blackbox")}
glue = {n: c for n, c in M["cells"].items() if n not in subs}
# glue cells pass connectivity (thin wrapper: assigns / constant ties / small muxes)
adj = defaultdict(set)
for c in glue.values():
    bs = [b for v in c["connections"].values() for b in v if isinstance(b, int)]
    for b in bs:
        adj[b].update(bs)
bit_sub = defaultdict(set)
for n, c in subs.items():
    for v in c["connections"].values():
        for b in v:
            if isinstance(b, int):
                bit_sub[b].add(n)
def reach(b0):
    seen, st = {b0}, [b0]
    while st:
        b = st.pop()
        for x in adj.get(b, ()):
            if x not in seen:
                seen.add(x); st.append(x)
    return seen
out = dict(top=top, subs=[])
for n, c in subs.items():
    mod = J["modules"][c["type"]]; ent = dict(inst=n, module=c["type"], ports={}, bits={})
    for pn, p in mod["ports"].items():
        ent["ports"][pn] = dict(dir=p["direction"], width=len(p["bits"]))
        conn = c["connections"].get(pn, [])
        for nm, b in zip(names(pn, p), conn):
            if not isinstance(b, int):
                ent["bits"][nm] = dict(top=[], peer=[], const=True); continue
            R = reach(b)
            ent["bits"][nm] = dict(top=sorted({t for x in R for t in bit_top.get(x, ())}),
                                   peer=sorted({s for x in R for s in bit_sub.get(x, ()) if s != n}))
    out["subs"].append(ent)
json.dump(out, open(sys.argv[3], "w"))
for s in out["subs"]:
    b = s["bits"].values()
    print(s["inst"], s["module"], len(s["bits"]), "top", sum(1 for x in b if x["top"]), "seam-only", sum(1 for x in b if x["peer"] and not x["top"]),
          "none", sum(1 for x in b if not x["top"] and not x["peer"]))
