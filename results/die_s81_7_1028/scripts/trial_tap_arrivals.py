#!/usr/bin/env python3
"""LAND-KV-1: export a die_trial region-tree combo GRT result (mk_combo arr_<C>.txt, routed-RC native OpenSTA arrivals)
as the die_sta_related PROOF_DIR format (tap_arrivals_<C>.json), so the shared main die_sta_related.py times it.

    trial_tap_arrivals.py TREE_JSON ARR_TXT CORNER OUT_JSON

taps: port, part, late_ps/early_ps (tap port arrival max/min), slew_ps, cppr_node = the region root name (one clock
group), tree_path ('h' + one child-index char per tree level), stages_from_root (cells root -> tap driver), xy_um.
meta: per tree node (keyed by tree_path prefix, plus the region names and 'h'): node_late_ps / node_early_ps (node
buffer output), node_stages, node_xy_um, cppr_node_range_ps (late - early at the node).  No derate is applied here:
clock OCV is the --clock-ocv table of die_sta_related (the shared model)."""
import json
import sys

tree, arr, corner, out = sys.argv[1:5]
T = json.load(open(tree))
nodes = {int(k): v for k, v in T["nodes"].items()}
po = T["parent_of"]
A, N = {}, {}
for ln in open(arr):
    f = ln.split()
    if not f:
        continue
    if f[0] == "T":
        A[f[1]] = (float(f[2]), float(f[3]), float(f[4]))
    elif f[0] == "N":
        N[f[1]] = (float(f[2]), float(f[3]))
CH = "0123456789abcdefghijklmnopqrstuvwxyz"
path = {}
root = next(i for i, n in nodes.items() if n["parent"] is None)
stack = [(root, "h")]
while stack:
    i, p = stack.pop()
    path[i] = p
    for k, c in enumerate(nodes[i].get("kids", [])):
        stack.append((c, p + CH[k]))


def stages(cell):
    n = 1
    while cell in po:
        cell = po[cell]
        n += 1
    return n


def region_of(i):
    while i is not None:
        if nodes[i].get("region_root"):
            return nodes[i]["region_root"], i
        i = nodes[i]["parent"]
    return "h", root


buf = {int(k): v for k, v in T["node_buf"].items()}
meta = dict(corner=corner, source=f"{arr} (die_trial region trees, combo GRT routed RC, OpenSTA)",
            node_late_ps={}, node_early_ps={}, node_stages={}, node_xy_um={}, cppr_node_range_ps={})


def put(key, i):
    b = buf[i]
    if b not in N:
        return
    la, ea = N[b]
    meta["node_late_ps"][key] = la
    meta["node_early_ps"][key] = ea
    meta["node_stages"][key] = stages(b)
    meta["node_xy_um"][key] = [nodes[i]["x"], nodes[i]["y"]]
    meta["cppr_node_range_ps"][key] = round(la - ea, 4)


for i in nodes:
    put(path[i], i)
put("h", root)
regions = {}
for i, n in nodes.items():
    if n.get("region_root"):
        regions[n["region_root"]] = i
        put(n["region_root"], i)
taps, miss = [], 0
for t in T["taps"]:
    if t["port"] not in A:
        miss += 1
        continue
    la, ea, sl = A[t["port"]]
    reg, _ = region_of(t["node"])
    taps.append(dict(port=t["port"], part=t["part"], late_ps=la, early_ps=ea, slew_ps=sl, cppr_node=reg,
                     tree_path=path[t["node"]], stages_from_root=stages(buf[t["node"]]) + 1, xy_um=t["xy"],
                     node=t["node"]))
json.dump(dict(meta, taps=taps, regions=len(regions)), open(out, "w"))
print(corner, "taps", len(taps), "missing", miss, "regions", len(regions), "nodes", len(meta["node_late_ps"]))
