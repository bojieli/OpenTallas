#!/usr/bin/env python3
"""INSERTION-BALANCE (REACH-FIX-2, COORD 11-12): a die_clock.py run (balanced-by-construction H-tree, DIE-S81-88 ready12b
method) -> die_sta_related tap-arrival format, so the die gate chain (DIE-PROTO-2: die_sta_related --cppr-lca, landed /
seam / intra classes, kit contract) times the balanced tree exactly as it times a die_trial kit tree.

usage: dieclock_arrivals.py RUN_DIR CORNER OUT_JSON [--regions-from TAP_ARRIVALS_JSON]

  RUN_DIR   die_clock.py run output (tree.json + arr_<CORNER>.txt from its OpenSTA on ctree.v/ctree.spef)
  tree_path every tap's die_clock cell path (tr0, n0_0, r1_0_0, ...) as a trie code: root 'h' + base-36 child index per
            level (multi-char codes for wide fan-outs, their prefixes carry the parent's arrival), so --cppr-lca credits
            exactly the shared cells of each pair
  node_*    node arrivals from the N rows; a path cell without an N row takes its nearest timed ancestor's arrival
            (less CPPR credit: conservative)
  --regions-from  keep the pair classes of a reference run: every tap's cppr_node = its region in that tap-arrival
            json (same port), so 'landed' names the SAME partition pairs as the reference (a die_trial region run);
            without it every tap is in region 'h' (no landed class).
"""
import argparse
import json
from pathlib import Path

CH = "0123456789abcdefghijklmnopqrstuvwxyz"


EDGES_HDR = "# OT_EDGES v1"


def read_arr(p):
    T, N = {}, {}
    for ln in Path(p).read_text().splitlines():
        f = ln.split()
        if len(f) >= 4 and f[0] == "T":
            T[f[1]] = tuple(map(float, f[2:5]))
        elif len(f) >= 4 and f[0] == "N":
            N[f[1]] = tuple(map(float, f[2:4]))
    return T, N


def read_fall(p):
    """(F {port: (late, early)}, M {cell: (late, early)}) of a both-edge readout (die_clock.sta_tcl, header EDGES_HDR);
    ({}, {}) for a rise-only file.  Without the header an F row is the legacy 'F port fall rise' form and is not read."""
    lines = Path(p).read_text().splitlines()
    if not any(ln.startswith(EDGES_HDR) for ln in lines[:5]):
        return {}, {}
    F, M = {}, {}
    for ln in lines:
        f = ln.split()
        if len(f) >= 4 and f[0] in ("F", "M"):
            (F if f[0] == "F" else M)[f[1]] = tuple(map(float, f[2:4]))
    return F, M


def export(run, corner, regions_from=None):
    run = Path(run)
    tree = json.loads((run / "tree.json").read_text())
    T, N = read_arr(run / ("arr_%s.txt" % corner))
    F, M = read_fall(run / ("arr_%s.txt" % corner))
    reg = {}
    if regions_from:
        ref = json.loads(Path(regions_from).read_text())
        reg = {t["port"]: t.get("cppr_node", "h") for t in ref["taps"]}
    kids = {}
    for t in tree["taps"]:
        p = list(t["path"])
        for i in range(1, len(p)):
            kids.setdefault(tuple(p[:i]), set()).add(p[i])
    meta = dict(corner=corner, source="%s (die_clock.py run: ctree.v + ctree.spef ladder RC, OpenSTA)" % run,
                clock_cell="buf", node_late_ps={}, node_early_ps={}, node_stages={}, node_xy_um={},
                cppr_node_range_ps={})
    code = {}
    timed = {}

    def put(key, cell, depth, inherit):
        la, ea = N[cell] if cell in N else inherit
        meta["node_late_ps"][key] = la
        meta["node_early_ps"][key] = ea
        if cell in M:     # measured fall arrival of this node (R-CLOCK-6 g); an untimed path cell gets none (fails closed)
            meta.setdefault("node_fall_late_ps", {})[key], meta.setdefault("node_fall_early_ps", {})[key] = M[cell]
        meta["node_stages"][key] = depth
        meta["cppr_node_range_ps"][key] = round(la - ea, 4)
        return la, ea

    root = (tree["taps"][0]["path"][0],)
    code[root] = "h"
    timed[root] = put("h", root[0], 1, (0.0, 0.0))
    stack = [root]
    while stack:
        pre = stack.pop()
        ks = sorted(kids.get(pre, ()))
        width = 1
        while 36 ** width < len(ks):
            width += 1
        for k, c in enumerate(ks):
            s, x = "", k
            for _ in range(width):
                s = CH[x % 36] + s
                x //= 36
            for n in range(1, width):        # textual prefixes of wide codes = the parent's output
                put(code[pre] + s[:n], pre[-1], len(pre), timed[pre])
            ch = pre + (c,)
            code[ch] = code[pre] + s
            timed[ch] = put(code[ch], c, len(ch), timed[pre])
            stack.append(ch)
    taps, miss = [], 0
    for t in tree["taps"]:
        port = t["port"]
        if port not in T:
            miss += 1
            continue
        la, ea, sl = T[port]
        p = tuple(t["path"])
        taps.append(dict(port=port, part=t["part"], late_ps=la, early_ps=ea, slew_ps=sl,
                         cppr_node=reg.get(port, "h"), tree_path=code[p], stages_from_root=len(p) + 1,
                         xy_um=t["xy"], node=t.get("leaf"),
                         **(dict(fall_late_ps=F[port][0], fall_early_ps=F[port][1]) if port in F else {})))
    if F or M:
        meta["fall_arrivals"] = dict(source="die_clock.sta_tcl F/M rows (both-edge readout)",
                                     taps_with_fall=sum(1 for x in taps if "fall_late_ps" in x), taps=len(taps),
                                     nodes_with_fall=len(meta.get("node_fall_late_ps", {})))
    return dict(meta, taps=taps, regions=len(set(reg.values()))), miss


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("run")
    ap.add_argument("corner")
    ap.add_argument("out")
    ap.add_argument("--regions-from")
    a = ap.parse_args()
    res, miss = export(a.run, a.corner, a.regions_from)
    if a.regions_from:
        lost = sum(1 for t in res["taps"] if t["cppr_node"] == "h")
        print("regions from", a.regions_from, "taps without a reference region", lost)
    Path(a.out).write_text(json.dumps(res))
    print(a.corner, "taps", len(res["taps"]), "missing", miss, "nodes", len(res["node_late_ps"]),
          "fall taps", sum(1 for x in res["taps"] if "fall_late_ps" in x), "fall nodes", len(res.get("node_fall_late_ps", {})))
    return 1 if miss else 0


if __name__ == "__main__":
    raise SystemExit(main())
