"""positive-offset leaf cycles (bound landed - as-built summed around a loop) in a region of a bound QC top"""
import json, re, sys
from collections import defaultdict
bdir, region = sys.argv[1], re.compile(sys.argv[2])
sinks = json.load(open(f"{bdir}/bind_sinks.json"))
bg = json.load(open(f"{bdir}/bus_groups.json"))
asb = {}
for g in bg["landing"]:
    for m in g["members"]:
        for i in [i for a, b in m["sink_bits"] for i in range(a, b + 1)]:
            asb[(g["sink"], m["sink_port"], i)] = m["asbuilt_stages"]
E = {}   # (src, dst) -> (max offset, ports)
for k, v in sinks.items():
    if v[0] != "pin" or not v[1]:
        continue
    leafport, bit = k.rsplit("[", 1)
    leaf, port = leafport.rsplit(".", 1)
    src = v[1].rsplit("[", 1)[0].rsplit(".", 1)[0]
    if not region.match(leaf) or not region.match(src):
        continue
    if "rst" in port:
        continue
    a = asb.get((leaf, port, int(bit[:-1])))
    off = 0 if a is None else v[2] - a
    key = (src, leaf)
    if key not in E or off > E[key][0]:
        E[key] = (off, port, v[1].rsplit("[", 1)[0].rsplit(".", 1)[1])
import networkx as nx
G = nx.DiGraph()
for (s, d), (o, p, sp) in E.items():
    G.add_edge(s, d, w=o, p=f"{sp}->{p}")
print("nodes", G.number_of_nodes(), "edges", G.number_of_edges())
pos = []
for scc in nx.strongly_connected_components(G):
    if len(scc) < 2:
        continue
    H = G.subgraph(scc)
    n = 0
    for cyc in nx.simple_cycles(H, length_bound=int(sys.argv[3]) if len(sys.argv) > 3 else 4):
        w = sum(H[cyc[i]][cyc[(i + 1) % len(cyc)]]["w"] for i in range(len(cyc)))
        if w != 0:
            pos.append((w, [(cyc[i].split(".")[-1], H[cyc[i]][cyc[(i + 1) % len(cyc)]]["p"], H[cyc[i]][cyc[(i + 1) % len(cyc)]]["w"]) for i in range(len(cyc))]))
        n += 1
        if n > 20000:
            break
pos.sort(key=lambda x: -abs(x[0]))
print("nonzero cycles", len(pos))
seen = set()
for w, c in pos[:40]:
    print(w, c)
