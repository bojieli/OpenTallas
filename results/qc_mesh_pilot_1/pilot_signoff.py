#!/usr/bin/env python3
"""QC-MESH-PILOT-1: routed pilot -> explicit_mesh_signoff rec (shared MC basis) -> pair U per glue pair (the
die_sta_related.mesh_signoff U formula: max(max|d_s|, |mu|+3 sd) + gradient), plus the off-mesh A0 core-tap branch.
usage: pilot_signoff.py rec  TRIAL_DIR STAGE(grt|drt)            -> TRIAL/rec_STAGE.json
       pilot_signoff.py pair TRIAL_DIR STAGE ARR14_TT ARR14_FF   -> TRIAL/pair_STAGE.json (needs mc_STAGE_{TT,FF}.json)
Every number UNCHECKED until NUMBER-CHECK."""
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[2] / "tools" / "die_plan"
sys.path.insert(0, str(TOOLS))
import explicit_mesh_signoff as EMS   # noqa: E402


def read_tree(p):
    t = defaultdict(dict)
    for ln in open(p):
        f = ln.split()
        if len(f) < 5:
            continue
        try:
            v = tuple(float(x) for x in f[2:5])
        except ValueError:
            continue
        t[f[1]][f[0]] = v
    return t


def graph(g):
    """explicit conductor graph: M9 straps at vx split at every M8 crossing + driver point; M8 straps at hy split at
    every M9 crossing + tap point; VIA89 edge at each crossing."""
    y0, y1 = g["y_span"]
    x0, x1 = g["x_span"]
    drv_pts = defaultdict(set)
    for d, (x, y) in g["drv_xy"].items():
        drv_pts[x].add(y)
    tap_pts = defaultdict(set)
    for t, (x, y) in g["tap_node"].items():
        tap_pts[y].add(x)
    E = []
    for x in g["vx"]:
        ys = sorted({y0, y1} | set(g["hy"]) | drv_pts[x])
        E += [[["M9", x, a], ["M9", x, b]] for a, b in zip(ys, ys[1:])]
    for y in g["hy"]:
        xs = sorted({x0, x1} | set(g["vx"]) | tap_pts[y])
        E += [[["M8", a, y], ["M8", b, y]] for a, b in zip(xs, xs[1:])]
        E += [[["M8", x, y], ["M9", x, y]] for x in g["vx"]]
    return dict(edges=E)


def cmd_rec(trial, stage):
    T = Path(trial)
    J = json.load(open(T / "pilot.json"))
    g, cells, nets = J["geom"], J["cells"], J["nets"]
    tr = {c: read_tree(T / f"tree_{stage}_{c}.txt") for c in ("TT", "FF") if (T / f"tree_{stage}_{c}.txt").exists()}
    if "FF" not in tr:
        tr["FF"] = tr["TT"]
        print("WARNING: no FF arrivals for", stage, "-> FF = TT (labelled)")
    parent = {}
    for n, v in nets.items():
        if v["kind"] != "tree" or n == "n_E0" or n.startswith(("n_E1", "n_Q")):
            continue
        for l in v["loads"]:
            if l == "E0":
                continue
            parent[l] = None if v["drv"] == "port:root" else v["drv"]
    depth = {}

    def dep(c):
        if c not in depth:
            depth[c] = 1 if parent[c] is None else dep(parent[c]) + 1
        return depth[c]
    hyrow = dict(zip(g["rows"], g["hy"]))
    g["drv_xy"] = {}
    for d in g["drivers"]:
        i = int(d[1])
        g["drv_xy"][d] = [g["vx"][i], round(cells[d]["y"] + 0.135, 4)]
    g["tap_node"] = {}
    for l in g["mesh_loads"]:
        x, y = g["tap_xy"][l]
        g["tap_node"][l] = [x, hyrow[y]]
    G = graph(g)
    segs, rcm = EMS.mesh_rc(G, "4w", "r6")
    nodes = []
    for c in sorted(parent, key=lambda c: (dep(c), c)):
        drv = c in g["drivers"]
        pin = "A" if drv else "Y"
        arr = {}
        for k, t in tr.items():
            v = t[c][pin]
            arr[k] = dict(late=v[0], early=v[1], slew=v[2])
        p = parent[c]
        leg = abs(cells[c]["x"] - cells[p]["x"]) + abs(cells[c]["y"] - cells[p]["y"]) if p else 0.0
        nodes.append(dict(tag=c, parent=p, depth=dep(c), driver=drv, mult=1, xy=[cells[c]["x"], cells[c]["y"]], arr=arr,
                          anchor=["M9", g["drv_xy"][c][0], g["drv_xy"][c][1]] if drv else None, units=[c], leg_um=max(leg, 1.0)))
    key = lambda p: f"{p[0]}:{float(p[1]):.4f}:{float(p[2]):.4f}"
    taps = [dict(port=l, part=g["part"], kind="published_grid_clock", endpoint_port=l, node=key(["M8"] + g["tap_node"][l]),
                 xy=g["tap_node"][l], pin_xy=g["tap_xy"][l], jog_um=abs(g["tap_xy"][l][1] - g["tap_node"][l][1]),
                 stub_um=0.0, load_ff=2.3) for l in g["mesh_loads"]]
    root = [n for n in nodes if n["parent"] is None][0]
    rec = dict(schema="opentallas.explicit_mesh_rec.v1", source=str(T.resolve()), ndr="4w", rc=rcm, nodes=nodes, segs=segs,
               taps=taps, root_xy=root["xy"], root=root["tag"], tap_load_ff={"published_grid_clock": 2.3},
               graph=dict(edges=len(G["edges"]), components=1), stage=stage, checked="UNCHECKED")
    (T / f"rec_{stage}.json").write_text(json.dumps(rec))
    dg = [n for n in nodes if n["driver"]]
    for k in tr:
        a = [n["arr"][k]["late"] for n in dg]
        print(stage, k, "drivers", len(dg), "driver A late", round(min(a), 2), "..", round(max(a), 2), "spread", round(max(a) - min(a), 2),
              "mesh C pF", round(sum(s[3] for s in segs) / 1e3, 3), "segs", len(segs))


def cmd_pair(trial, stage, a14tt, a14ff):
    T = Path(trial)
    J = json.load(open(T / "pilot.json"))
    g = J["geom"]
    out = dict(trial=str(T), part=g["part"], stage=stage, corners={}, checked="UNCHECKED")
    for C, a14 in (("TT", a14tt), ("FF", a14ff)):
        S = json.load(open(T / f"mc_{stage}_{C}.json"))
        L = S["loads"]
        arr, gv = S["arr"], S["grad_vec_ps"]
        U = []
        for i in range(len(L)):
            for j in range(i + 1, len(L)):
                ds = [s[i] - s[j] for s in arr]
                mc = ds[1:]
                mu = sum(mc) / len(mc)
                sd = (sum((v - mu) ** 2 for v in mc) / max(1, len(mc) - 1)) ** 0.5
                gd = math.hypot(gv[i][0] - gv[j][0], gv[i][1] - gv[j][1])
                U.append((max(max(abs(v) for v in ds), abs(mu) + 3 * sd) + gd, L[i], L[j]))
        U.sort()
        nom = dict(zip(L, arr[0]))
        tr = read_tree(T / f"tree_{stage}_{C}.txt") if (T / f"tree_{stage}_{C}.txt").exists() else read_tree(T / f"tree_{stage}_TT.txt")
        core = {c: tr[c]["A"][0] for c in tr if c.startswith("L_clk_c")}
        mesh_med = sorted(nom.values())[len(nom) // 2]
        # trial14 routed: the region's own early offset (glue median - core median) = the planned core earliness
        t14 = {}
        for ln in open(a14):
            f = ln.split()
            if f and f[0] == "T" and f"t_{g['part']}__" in f[1]:
                t14[f[1].split("__")[1]] = float(f[2])
        gl14 = sorted(v for k, v in t14.items() if not k.startswith("clk_c"))
        co14 = sorted(v for k, v in t14.items() if k.startswith("clk_c"))
        early_req = gl14[len(gl14) // 2] - co14[len(co14) // 2]
        early_got = {c: round(mesh_med - v, 2) for c, v in core.items()}
        out["corners"][C] = dict(
            mc=S["summary"], pairs=len(U), pair_U_max_ps=round(U[-1][0], 2), pair_U_p50_ps=round(U[len(U) // 2][0], 2),
            worst_pair=U[-1][1:], nominal_skew_ps=round(max(nom.values()) - min(nom.values()), 2),
            insertion_root_to_mesh_median_ps=round(mesh_med, 2), insertion_root_to_mesh_range_ps=[round(min(nom.values()), 2), round(max(nom.values()), 2)],
            trial14_glue_spread_ps=round(gl14[-1] - gl14[0], 2), trial14_glue_median_minus_core_median_ps=round(early_req, 2),
            core_tap_early_vs_mesh_ps=early_got, core_early_error_ps=round(max(abs(v - early_req) for v in early_got.values()), 2))
        print(C, json.dumps(out["corners"][C]))
    (T / f"pair_{stage}.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    a = sys.argv[1:]
    if a[0] == "rec":
        cmd_rec(a[1], a[2])
    elif a[0] == "pair":
        cmd_pair(*a[1:6])
    else:
        raise SystemExit(__doc__)
