#!/usr/bin/env python3
"""OSS-CLOCK-3: cut one trunk SUBTREE out of an mscts trunk spec (e.g. a quarter of the QC E0 slice) for a quick
transistor-level check.  mscts_subslice.py SPEC.json TRUNK_NODE_ID OUT.json
The subtree's top node becomes the entry; sinks = those whose leaf (rect / nearest) is under it; crossings with both
ends inside; keepouts unchanged (the tool filters by geometry)."""
import json
import sys

spec, top, outp = json.load(open(sys.argv[1])), sys.argv[2], sys.argv[3]
nodes = {n["id"]: n for n in spec["trunk"]["nodes"]}
kids = {}
for n in spec["trunk"]["nodes"]:
    kids.setdefault(n.get("parent"), []).append(n["id"])
keep, st = [], [top]
while st:
    x = st.pop()
    keep.append(x)
    st += kids.get(x, [])
leaves_all = [i for i in nodes if not kids.get(i)]


def leaf_of(s):
    for c in leaves_all:
        r = nodes[c].get("rect")
        if r and r[0] <= s["xy"][0] <= r[2] and r[1] <= s["xy"][1] <= r[3]:
            return c
    return min(leaves_all, key=lambda c: abs(nodes[c]["xy"][0] - s["xy"][0]) + abs(nodes[c]["xy"][1] - s["xy"][1]))


sinks = [s for s in spec["sinks"] if leaf_of(s) in keep]
names = {s["name"] for s in sinks}
tn = []
for i in keep:
    n = dict(nodes[i])
    if i == top:
        n["parent"] = None
    tn.append(n)
out = dict(spec, name=f"{spec['name']}_sub_{top}", entry=nodes[top]["xy"], sinks=sinks,
           crossings=[x for x in spec["crossings"] if x[0] in names and x[1] in names],
           trunk=dict(entry=nodes[top]["xy"], nodes=tn))
json.dump(out, open(outp, "w"), indent=0)
print(json.dumps(dict(top=top, trunk_nodes=len(tn), sinks=len(sinks), crossings=len(out["crossings"]))))
