"""R14 lane probe: one period-0 local row x-tree from the R13 export, dry-built alone on the real QC plan PG in
(A) single line (all cells on one VSS-phase row) vs (B) one lane per tree level (8.64-um VSS-phase lanes).  UNCHECKED."""
import json, collections, sys, copy
d = json.load(open(sys.argv[1])); out = sys.argv[2]
cs, nets = d["cell_sites"], d["nets"]
G = collections.defaultdict(list)
for n, v in cs.items(): G["g%d" % v["group"]].append(n)
inc = {n["load"]: n for n in nets}
kids = collections.defaultdict(list)
for n in nets: kids[n["drv"]].append(n)
taps = sorted({"g%d" % v["group"] for v in cs.values() if v["kind"] == "col_tap" and 3880 < v["origin_um"][1] < 3960 and 2100 < v["origin_um"][0] < 4200})
print("taps", taps)
# local root: walk up M8 nets until the incoming net is M9 (column y-tree) -> that group is the local root
def up(g):
    while g in inc and inc[g]["layer"] == "M8": g = inc[g]["drv"]
    return g
roots = {up(t) for t in taps}; print("local roots", roots)
root = roots.pop()
sel, sub, lvl, order = {root}, [], {root: 0}, [root]
for g in order:
    for n in kids[g]:
        if n["layer"] != "M8": continue
        sub.append(n); sel.add(n["load"]); order.append(n["load"])
        # level = number of tree NODES (branch points / leaves) above: reps keep their edge's level
        # lane = node depth: a node / leaf goes one 8.64-um lane past its parent node; repeaters stay on the lane of
        # the node that drives their edge (so every lane holds only x-disjoint edges: no folding on one line)
        k_ = cs[G[n["load"]][0]]["kind"]
        lvl[n["load"]] = lvl[g] + (1 if k_ in ("top_node", "col_tap") else 0)
print("groups", len(sel), "nets", len(sub), "levels", collections.Counter(lvl.values()))
def spec(lanes, base=3922.56, pitch=8.64):
    c = {}
    for g in sel:
        us = sorted(G[g], key=lambda u: cs[u]["origin_um"][1])
        y0 = base + (lvl[g] * pitch if lanes else 0.0)
        for i, u in enumerate(us):
            v = copy.deepcopy(cs[u]); v["origin_um"] = [v["origin_um"][0], round(y0 + i * 0.27, 4)]; c[u] = v
    return dict(cell_sites=c, nets=sub, exact_reserve=True)
json.dump(spec(False), open(out + "_A.json", "w"))
json.dump(spec(True), open(out + "_B.json", "w"))
