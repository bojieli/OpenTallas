#!/usr/bin/env python3
"""Export routed die_trial region clocks to die_sta_related tap-arrival format.

Usage: trial_tap_arrivals.py TREE_JSON ARR_TXT CORNER OUT_JSON
Legacy trees retain geometric paths. Padded trees use physical cell parents,
including repeaters and pads; CPPR grouping remains the declared region.
"""
import argparse
import json
import re
from pathlib import Path

CH = "0123456789abcdefghijklmnopqrstuvwxyz"


def export(tree, arr, corner):
    T = json.loads(Path(tree).read_text())
    nodes = {int(k): v for k, v in T["nodes"].items()}
    buf = {int(k): v for k, v in T["node_buf"].items()}
    po = T["parent_of"]
    A, N = {}, {}
    for ln in Path(arr).read_text().splitlines():
        f = ln.split()
        if f and f[0] == "T":
            A[f[1]] = tuple(map(float, f[2:5]))
        elif f and f[0] == "N":
            N[f[1]] = tuple(map(float, f[2:4]))
    root = next(i for i, n in nodes.items() if n["parent"] is None)

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

    path = {}
    stack = [(root, "h")]
    while stack:
        i, p = stack.pop()
        path[i] = p
        for k, c in enumerate(nodes[i].get("kids", [])):
            stack.append((c, p + CH[k]))
    meta = dict(corner=corner, source=f"{arr} (die_trial region trees, combo GRT routed RC, OpenSTA)",
                node_late_ps={}, node_early_ps={}, node_stages={}, node_xy_um={}, cppr_node_range_ps={})
    # CLK-INV-CAL-1: an inverter die clock (die_trial --clock-cell inv/inv2: ctree.v beside tree.json) is recorded so
    # die_sta_related picks the inverter model (spice factor + AOCV class Ainv); BUFx24 exports are unchanged
    nl = Path(tree).parent / "ctree.v"
    if nl.is_file():
        txt = nl.read_text()
        ninv = len(re.findall(r"^\s*CKINVDCx16_ASAP7_75t_R\s", txt, re.M))
        if ninv > len(re.findall(r"^\s*BUFx24_ASAP7_75t_R\s", txt, re.M)):
            meta["clock_cell"] = "inv"

    def put_cell(key, cell, xy):
        if cell not in N:
            raise ValueError(f"{arr}: missing N arrival for physical clock cell {cell}; export b*/r*/p*")
        la, ea = N[cell]
        meta["node_late_ps"][key] = la
        meta["node_early_ps"][key] = ea
        meta["node_stages"][key] = stages(cell)
        meta["node_xy_um"][key] = xy
        meta["cppr_node_range_ps"][key] = round(la - ea, 4)

    physical = any("driver" in t for t in T["taps"])
    cell_paths = {}
    if physical:
        children = {}
        for cell, parent in po.items():
            children.setdefault(parent, []).append(cell)
        stack = [(buf[root], "h")]
        while stack:
            cell, p = stack.pop()
            cell_paths[cell] = p
            put_cell(p, cell, T["sites"][cell])
            kids = sorted(children.get(cell, []))
            width = 1
            while 36 ** width < len(kids):
                width += 1
            for k, child in enumerate(kids):
                code = ""
                for _ in range(width):
                    code = CH[k % 36] + code
                    k //= 36
                # A common textual prefix of distinct child labels represents
                # their parent output, never fictitious shared buffer delay.
                for n in range(1, width):
                    put_cell(p + code[:n], cell, T["sites"][cell])
                stack.append((child, p + code))
    else:
        for i in nodes:
            if buf[i] in N:
                put_cell(path[i], buf[i], [nodes[i]["x"], nodes[i]["y"]])

    regions = {}
    for i, n in nodes.items():
        if n.get("region_root"):
            regions[n["region_root"]] = i
            if buf[i] in N:
                put_cell(n["region_root"], buf[i], [n["x"], n["y"]])
    taps, miss = [], 0
    for t in T["taps"]:
        if t["port"] not in A:
            miss += 1
            continue
        if len(A[t["port"]]) != 3:
            raise ValueError(f"{arr}: T {t['port']} needs max/min arrival and measured slew")
        la, ea, sl = A[t["port"]]
        reg, _ = region_of(t["node"])
        driver = t.get("driver", buf[t["node"]])
        taps.append(dict(port=t["port"], part=t["part"], late_ps=la, early_ps=ea, slew_ps=sl,
                         cppr_node=reg, tree_path=cell_paths[driver] if physical else path[t["node"]],
                         stages_from_root=stages(driver) + 1, xy_um=t["xy"], node=t["node"]))
    return dict(meta, taps=taps, regions=len(regions)), miss


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("tree"); ap.add_argument("arr"); ap.add_argument("corner"); ap.add_argument("out")
    a = ap.parse_args()
    result, missing = export(a.tree, a.arr, a.corner)
    Path(a.out).write_text(json.dumps(result))
    print(a.corner, "taps", len(result["taps"]), "missing", missing, "regions", result["regions"],
          "nodes", len(result["node_late_ps"]))


if __name__ == "__main__":
    main()
