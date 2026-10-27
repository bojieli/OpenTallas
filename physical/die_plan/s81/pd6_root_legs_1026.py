#!/usr/bin/env python3
"""PATH-S81-PD6: decompose each region's clock insertion = H-tree (die root -> last pure H-tree node above the region
root) + region-root leg (that node -> region root) + region tree (root -> taps).  Usage: PROOF TREE CORNER OUT"""
import json
import sys


def main(proof, tree_p, C, out):
    T = json.load(open(tree_p))
    nodes = {int(k): v for k, v in T["nodes"].items()}
    A = json.load(open(f"{proof}/tap_arrivals_{C}.json"))
    nl = A["node_late_ps"]
    st = A["node_stages"]
    path = {}
    root = [i for i, n in nodes.items() if n["parent"] is None][0]
    path[root] = "h"
    order = [root]
    for i in order:
        for j, k in enumerate(nodes[i]["kids"]):
            path[k] = path[i] + chr(48 + j)
            order.append(k)
    rows = []
    taps_by_reg = {}
    for t in A["taps"]:
        taps_by_reg.setdefault(t["region"], []).append(t)
    for i in order:
        n = nodes[i]
        if not n.get("region_root"):
            continue
        # walk up to the first ancestor with 2 kids at level <= 14 (H-tree branch point)
        a = n["parent"]
        wire = 0.0
        prev = i
        while a is not None and not (len(nodes[a]["kids"]) == 2 and nodes[a]["level"] <= 14):
            wire += abs(nodes[a]["x"] - nodes[prev]["x"]) + abs(nodes[a]["y"] - nodes[prev]["y"])
            prev, a = a, nodes[a]["parent"]
        wire += abs(nodes[a]["x"] - nodes[prev]["x"]) + abs(nodes[a]["y"] - nodes[prev]["y"])
        tl = taps_by_reg.get(n["region_root"], [])
        if not tl:
            continue
        rp = path[i]
        hp = path[a]
        rx = n["region"]
        rows.append(dict(region=n["region_root"], htree_node=hp, htree_level=nodes[a]["level"],
                         htree_arr=round(nl[hp], 1), leg_ps=round(nl[rp] - nl[hp], 1), leg_um=round(wire, 1),
                         leg_stages=st[rp] - st[hp], root_arr=round(nl[rp], 1),
                         req_disp_um=round(abs(n["x"] - n["req_xy"][0]) + abs(n["y"] - n["req_xy"][1]), 1),
                         region_wh_um=[round(rx[2] - rx[0], 1), round(rx[3] - rx[1], 1)],
                         tree_min=round(min(t["late_ps"] for t in tl) - nl[rp], 1),
                         tree_max=round(max(t["late_ps"] for t in tl) - nl[rp], 1),
                         depth_min=min(t["stages_from_root"] for t in tl) - st[rp],
                         depth_max=max(t["stages_from_root"] for t in tl) - st[rp],
                         tap_min=round(min(t["late_ps"] for t in tl), 1), tap_max=round(max(t["late_ps"] for t in tl), 1),
                         ntaps=len(tl), parts=len(set(t["part"] for t in tl))))
    json.dump(rows, open(out, "w"), indent=1)
    import statistics as S
    def rng(k):
        v = [r[k] for r in rows]
        return f"{k}: min {min(v)} p50 {S.median(v)} max {max(v)} spread {round(max(v)-min(v),1)}"
    print(C, len(rows), "regions")
    for k in ("htree_arr", "leg_ps", "leg_um", "leg_stages", "root_arr", "tree_min", "tree_max", "depth_min", "depth_max",
              "tap_min", "tap_max"):
        print(" ", rng(k))
    lg = sorted(rows, key=lambda r: -r["leg_ps"])[:6]
    print("  longest legs:", [(r["region"], r["leg_ps"], r["leg_um"], r["leg_stages"]) for r in lg])
    tm = sorted(rows, key=lambda r: -r["tree_max"])[:6]
    print("  deepest trees:", [(r["region"], r["tree_max"], r["depth_max"], r["region_wh_um"], r["parts"]) for r in tm])
    # correlation of root arrival with leg
    hv = [r["htree_arr"] for r in rows]
    print("  share of root-arrival spread: htree", round(max(hv) - min(hv), 1), "leg", round(max(r["leg_ps"] for r in rows) - min(r["leg_ps"] for r in rows), 1))


if __name__ == "__main__":
    main(*sys.argv[1:5])
