"""estimate R8 pad flops: per-sink chains (as bound today) vs delay trees along the lane forwarding tree"""
import json, sys
from collections import defaultdict
bg = json.load(open(sys.argv[1]))
mode = sys.argv[2] if len(sys.argv) > 2 else "landed"   # landed (bus_groups landed_stages) or table FILE
pad_of = None
if len(sys.argv) > 3:
    t = json.load(open(sys.argv[3]))
    pad_of = {m["id"]: m["pad"] for m in t["members"]}
def mkey(g, m):
    sb = ",".join(f"{a}:{b}" for a, b in m["sink_bits"])
    return f"{g['sink']}.{m['sink_port']}[{sb}]<-{m['source']}@{m['asbuilt_stages']}"
# per source bit: node (partition) -> list of local pads; node parent from the lane name
bits = defaultdict(lambda: defaultdict(list))
parent = defaultdict(dict)
chain = 0
for g in bg["landing"]:
    for m in g["members"]:
        pad = pad_of.get(mkey(g, m), 0) if pad_of is not None else m["landed_stages"] - m["bound_stages"]
        if m.get("lane") in (None, "spine"):
            continue
        srcpart = g["src_part"]
        lane = m["lane"]
        lsrc = lane.split("__")[0]
        sb = [i for a, b in m["source_bits"] for i in range(a, b + 1)]
        for s in sb:
            key = (m["source"], s)
            bits[key][g["sink_part"]].append(pad)
            parent[key][g["sink_part"]] = lsrc
            bits[key].setdefault(srcpart, [])
seen = set()
for key, nodes in bits.items():
    for p, pads in nodes.items():
        for x in set(pads):
            chain += x
tree = 0
for key, nodes in bits.items():
    par = parent[key]
    kids = defaultdict(list)
    for c, p in par.items():
        kids[p].append(c)
        nodes.setdefault(p, [])
    allnodes = set(nodes)
    roots = [n for n in allnodes if n not in par]
    R = {}
    def req(v, depth=0):
        if v in R:
            return R[v]
        cand = list(nodes[v]) + [req(c, depth + 1) for c in kids[v]]
        R[v] = min(cand) if cand else 0
        return R[v]
    for v in allnodes:
        req(v)
    for v in allnodes:
        loc = list(nodes[v]) + [R[c] for c in kids[v]]
        U = R[v] if v in par else 0
        tree += (max(loc) - U) if loc else 0
print(json.dumps(dict(bits=len(bits), chain_shared=chain, tree=tree)))
