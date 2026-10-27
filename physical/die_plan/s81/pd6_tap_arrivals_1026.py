#!/usr/bin/env python3
"""PATH-S81-PD6: die_sta_related tap_arrivals_<C>.json from the S81 combo die GRT (die_trial region-tree clock).

    pd6_tap_arrivals_1026.py TREE_JSON ARR_TXT CORNER OUT_JSON

TREE_JSON = kit/clock/tree.json (die_trial build_htree, region mode): nodes {id: x, y, parent, kids, level,
region_root?}, taps [{port, part, xy, node}], node_buf {id: cell}, parent_of {cell: parent cell}.
ARR_TXT = out_<C>/arr_<C>.txt written by the combo run on GRT RC (estimate_parasitics -global_routing):
  T <tap port> <late> <early> <slew>        propagated arrival at the partition tap port
  N <cell> <late Y> <early Y> <slew A> <slew Y>
Node naming: 'h' = die root (b0); each child appends its index in the parent's kids list as one char, so a prefix is
an ancestor (die_sta_related --cppr-lca takes the longest common prefix = last common tree node).
cppr_node of a tap = its region root's path (classification intra/seam/landed + shared droop); the CPPR/AOCV node with
--cppr-lca is the true LCA.  Stages = clock cells (tree buffers + repeaters) from b0 to the driving cell, inclusive.
"""
import json
import sys
from collections import Counter


def main(tree_p, arr_p, corner, out_p):
    T = json.load(open(tree_p))
    nodes = {int(k): v for k, v in T["nodes"].items()}
    nb = {int(k): v for k, v in T["node_buf"].items()}
    par = T["parent_of"]
    arrT, arrN = {}, {}
    for ln in open(arr_p):
        f = ln.split()
        if not f:
            continue
        if f[0] == "T":
            arrT[f[1]] = (float(f[2]), float(f[3]), float(f[4]))
        elif f[0] == "N":
            arrN[f[1]] = (float(f[2]), float(f[3]))
    root = [i for i, n in nodes.items() if n["parent"] is None]
    assert len(root) == 1, root
    path = {root[0]: "h"}
    order = [root[0]]
    for i in order:
        for j, k in enumerate(nodes[i]["kids"]):
            assert j < 75
            path[k] = path[i] + chr(48 + j)
            order.append(k)
    assert len(path) == len(nodes), (len(path), len(nodes))
    depth = {}

    def stages(cell):
        chain = []
        c = cell
        while c not in depth:
            chain.append(c)
            p = par.get(c)
            if p is None:
                depth[c] = 1
                chain.pop()
                break
            c = p
        d = depth[c]
        for x in reversed(chain):
            d += 1
            depth[x] = d
        return depth[cell]

    reg_of = {}
    for i in order:
        n = nodes[i]
        if n.get("region_root"):
            reg_of[i] = (path[i], n["region_root"])
        elif n["parent"] is not None and n["parent"] in reg_of:
            reg_of[i] = reg_of[n["parent"]]
    node_late, node_early, node_st, node_xy, rng = {}, {}, {}, {}, {}
    miss = 0
    for i, n in nodes.items():
        c = nb[i]
        if c not in arrN:
            miss += 1
            continue
        p = path[i]
        node_late[p], node_early[p] = arrN[c]
        rng[p] = round(arrN[c][0] - arrN[c][1], 4)
        node_st[p] = stages(c)
        node_xy[p] = [n["x"], n["y"]]
    taps, tmiss = [], 0
    for t in T["taps"]:
        if t["port"] not in arrT:
            tmiss += 1
            continue
        late, early, slew = arrT[t["port"]]
        rp, rn = reg_of.get(t["node"], ("h", None))
        taps.append(dict(port=t["port"], part=t["part"], tap=t.get("tap"), late_ps=late, early_ps=early, slew_ps=slew,
                         cppr_node=rp, region=rn, tree_path=path[t["node"]], leaf_node=t["node"],
                         stages_from_root=stages(nb[t["node"]]), xy_um=t["xy"]))
    meta = dict(corner=corner, basis="S81 combo die GRT incl clock (die_trial region trees, routed GRT RC, "
                "estimate_parasitics -global_routing), PATH-S81-PD6 converter", tree=tree_p, arr=arr_p,
                cppr_node_range_ps=rng, node_late_ps=node_late, node_early_ps=node_early, node_stages=node_st,
                node_xy_um=node_xy, nodes_missing_arrival=miss, taps_missing_arrival=tmiss,
                regions=len(set(t["region"] for t in taps)),
                taps_without_region=sum(1 for t in taps if t["region"] is None),
                stages_hist=dict(Counter(t["stages_from_root"] for t in taps)))
    json.dump(dict(meta, taps=taps), open(out_p, "w"))
    print(f"{corner}: taps {len(taps)} (missing {tmiss}) nodes {len(node_late)} (missing {miss}) regions {meta['regions']} "
          f"no-region {meta['taps_without_region']} late {min(t['late_ps'] for t in taps):.1f}-{max(t['late_ps'] for t in taps):.1f} "
          f"stages {min(t['stages_from_root'] for t in taps)}-{max(t['stages_from_root'] for t in taps)}")


if __name__ == "__main__":
    main(*sys.argv[1:5])
