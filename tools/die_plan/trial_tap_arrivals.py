#!/usr/bin/env python3
"""Export routed die_trial region clocks to die_sta_related tap-arrival format.

Usage: trial_tap_arrivals.py TREE_JSON ARR_TXT CORNER OUT_JSON
Legacy trees retain geometric paths. Padded trees use physical cell parents,
including repeaters and pads; CPPR grouping remains the declared region.
FLOW-ONEMODEL-2: MEASURED falling-edge arrivals by construction.  F rows (tap) and
M rows (clock cell) of the arrivals file (die_trial.clock_edge_readout, header
'# OT_EDGES v1': 'F port late early', 'M cell late early', source FALL edge,
polarity-resolved) become fall_late_ps/fall_early_ps per tap and
node_fall_late_ps/node_fall_early_ps per tree node key, the fields
die_sta_related and count_align_plan time fall-edge samples on.  Legacy rows
without the header: 'F port late early' (FLOW-GEN-1 / DIE-KV-13 form) as is;
'F port fall rise slew' (DIE-QC-11 mk_clkfirst form) as the fall-minus-rise
delta on the T row.  No F/M rows = unchanged output.
"""
import argparse
import json
import re
from pathlib import Path

CH = "0123456789abcdefghijklmnopqrstuvwxyz"


EDGES_HDR = "# OT_EDGES v1"


def read_arr(arr):
    """(T {port: (late, early, slew...)}, N {cell: (late, early)}, F {port: (late, early)}, M {cell: (late, early)})"""
    lines = Path(arr).read_text().splitlines()
    hdr = any(ln.startswith(EDGES_HDR) for ln in lines[:5])
    A, N, Fr, M = {}, {}, {}, {}
    for ln in lines:
        f = ln.split()
        if not f or f[0] not in ("T", "N", "F", "M"):
            continue
        v = tuple(map(float, f[2:]))
        if f[0] == "T":
            A[f[1]] = v[:3]
        elif f[0] == "N":
            N[f[1]] = v[:2]
        elif f[0] == "M":
            M[f[1]] = v[:2]
        else:
            Fr[f[1]] = v
    F = {}
    for p, v in Fr.items():
        if hdr or len(v) == 2:
            F[p] = v[:2]
        elif p in A:      # DIE-QC-11 legacy 'F port fall_late rise_late slew': fall - rise delta on the T row
            F[p] = (v[0], A[p][1] + v[0] - v[1])
    return A, N, F, M


def export(tree, arr, corner, components=False):
    T = json.loads(Path(tree).read_text())
    nodes = {int(k): v for k, v in T["nodes"].items()}
    buf = {int(k): v for k, v in T["node_buf"].items()}
    po = T["parent_of"]
    A, N, F, M = read_arr(arr)
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
    # CLK-INV-CAL-1 + COORD ruling ba28d3143: the export DECLARES the die clock cell (die_sta_related fails closed without
    # it): die_trial tree.json meta clock_cell, else the majority master of the built ctree.v beside tree.json
    tm = (T.get("meta") or {}).get("clock_cell")
    nl = Path(tree).parent / "ctree.v"
    if tm is None and nl.is_file():
        txt = nl.read_text()
        ninv = len(re.findall(r"^\s*CKINVDCx16_ASAP7_75t_R\s", txt, re.M))
        nbuf = len(re.findall(r"^\s*BUFx24_ASAP7_75t_R\s", txt, re.M))
        tm = ("inv" if ninv > nbuf else "buf") if (ninv or nbuf) else None
    if tm is not None:
        meta["clock_cell"] = "inv" if tm == "inv2" else tm

    def put_cell(key, cell, xy):
        if cell not in N:
            raise ValueError(f"{arr}: missing N arrival for physical clock cell {cell}; export b*/r*/p*")
        la, ea = N[cell]
        if components:
            meta.setdefault("node_cell", {})[key] = cell
        meta["node_late_ps"][key] = la
        meta["node_early_ps"][key] = ea
        meta["node_stages"][key] = stages(cell)
        meta["node_xy_um"][key] = xy
        meta["cppr_node_range_ps"][key] = round(la - ea, 4)
        if cell in M:
            meta.setdefault("node_fall_late_ps", {})[key], meta.setdefault("node_fall_early_ps", {})[key] = M[cell]

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
                         stages_from_root=stages(driver) + 1, xy_um=t["xy"], node=t["node"],
                         **(dict(fall_late_ps=F[t["port"]][0], fall_early_ps=F[t["port"]][1]) if t["port"] in F else {})))
    if F or M:
        meta["fall_arrivals"] = dict(source="FLOW-ONEMODEL-2 trial_tap_arrivals F/M rows",
                                     taps_with_fall=sum(1 for x in taps if "fall_late_ps" in x), taps=len(taps),
                                     nodes_with_fall=len(meta.get("node_fall_late_ps", {})),
                                     nodes=len(meta["node_late_ps"]))
    result = dict(meta, taps=taps, regions=len(regions))
    if components:
        from clock_components import annotate
        result = annotate(result, Path(tree).parent / "ctree.v", arr)
    return result, miss


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("tree"); ap.add_argument("arr"); ap.add_argument("corner"); ap.add_argument("out")
    ap.add_argument("--clock-components", action="store_true",
                    help="export measured per-master clock delay components (requires both-edge T/N/F/M readout)")
    a = ap.parse_args()
    result, missing = export(a.tree, a.arr, a.corner, components=a.clock_components)
    Path(a.out).write_text(json.dumps(result))
    print(a.corner, "taps", len(result["taps"]), "missing", missing, "regions", result["regions"],
          "nodes", len(result["node_late_ps"]), "fall taps", sum(1 for x in result["taps"] if "fall_late_ps" in x),
          "fall nodes", len(result.get("node_fall_late_ps", {})))


if __name__ == "__main__":
    main()
