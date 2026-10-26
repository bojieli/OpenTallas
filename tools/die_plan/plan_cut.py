#!/usr/bin/env python3
"""PATH-HBM-R7 (12.9d predict-before-build, owner 10-12 "cut analysis before RTL"): partition-internal CUT LOWER BOUND.

Read-only on the plan.  For every partition type with internal_stations it computes, independent of any router or
road model, the bits that MUST cross each straight cut line of the type outline and compares them with the M4-M7
tracks crossing that line (12.1a: partition-internal routes stay <= M7):

  NETS     internal_stations grouped by source (launch, from_um): one multi-sink net per source (a broadcast is one
           Steiner tree, not N point-to-point roads); bits = widest station of the group.
  DEMAND   a net crosses a vertical cut x when its endpoint bbox spans x (any tree connecting the endpoints crosses it
           at least once) -> bits; same for horizontal cuts.  This is a LOWER bound of the real crossing count.
  SUPPLY   tracks crossing the cut on the layers that run across it: H layers M4 + M6 for a vertical cut, V layers
           M5 + M7 for a horizontal cut, each length / pitch x (1 - lower_pg_frac); M4/M5 are blocked over hard cores
           (core_obs_top M5), M6/M7 are free over cores.
  USE      demand / supply per cut; the corridor_tracks gate needs <= 0.6 (12.7b) on every gcell, so a cut use above
           0.6 proves corridor_tracks FAILs for ANY road plan inside that outline.
  RELAXED  (--relaxed) the same cut bound with the hard cores moved to their wirelength-optimal positions (iterated
           bit-weighted medians of their connections, face pins fixed, overlaps ALLOWED, no core blockage): a lower
           bound for every possible re-pack of the same outline / face-pin assignment / station topology.

Outputs JSON (--out) with per-type rows; exit 0 always (diagnostic predictor; the gate verdict is the master plan's).
All numbers are plan arithmetic: UNCHECKED until NUMBER-CHECK (12.9f).
"""
import argparse
import collections
import json
import sys
from pathlib import Path

PITCH = {"M4": 0.048, "M5": 0.048, "M6": 0.064, "M7": 0.064}
STEP = 4.32


def _nets(t):
    src = collections.defaultdict(list)
    for s in t.get("internal_stations", []):
        src[(s.get("launch"), tuple(s["from_um"]))].append(s)
    out = []
    for (launch, _), ss in src.items():
        out.append(dict(bits=max(s["bits"] for s in ss), pts=[list(ss[0]["from_um"])] + [list(s["to_um"]) for s in ss],
                        face=str(launch or "").startswith("face"), sinks=len(ss)))
    return out


def _cores(t):
    return {h["inst"]: (h["origin_um"][0], h["origin_um"][1], h["origin_um"][0] + h["outline_um"][0],
                        h["origin_um"][1] + h["outline_um"][1]) for h in t.get("hard_cores", [])}


def _cut_profile(W, H, nets, cores, lower_pg_frac=0.25, blocked=True):
    import numpy as np
    X = np.arange(STEP, W - 1e-6, STEP)
    Y = np.arange(STEP, H - 1e-6, STEP)
    dx, dy = np.zeros(len(X)), np.zeros(len(Y))
    dxc, dyc = np.zeros(len(X)), np.zeros(len(Y))
    for n in nets:
        xs = [p[0] for p in n["pts"]]
        ys = [p[1] for p in n["pts"]]
        mx = (X > min(xs)) & (X < max(xs))
        my = (Y > min(ys)) & (Y < max(ys))
        dx[mx] += n["bits"]
        dy[my] += n["bits"]
        if not n["face"]:
            dxc[mx] += n["bits"]
            dyc[my] += n["bits"]
    f = 1.0 - lower_pg_frac
    bx = np.zeros(len(X))
    by = np.zeros(len(Y))
    if blocked:
        for (x0, y0, x1, y1) in cores.values():
            bx[(X > x0) & (X < x1)] += min(y1, H) - max(y0, 0.0)
            by[(Y > y0) & (Y < y1)] += min(x1, W) - max(x0, 0.0)
    bx = np.minimum(bx, H)
    by = np.minimum(by, W)
    cx = (H - bx) * f / PITCH["M4"] + H * f / PITCH["M6"]
    cy = (W - by) * f / PITCH["M5"] + W * f / PITCH["M7"]
    ux, uy = dx / cx, dy / cy
    res = {}
    for ax, u, d, dc, c, V in (("x", ux, dx, dxc, cx, X), ("y", uy, dy, dyc, cy, Y)):
        if not len(u):
            res[ax] = dict(cuts=0)
            continue
        i = int(u.argmax())
        res[ax] = dict(cuts=int(len(u)), max_use=round(float(u.max()), 3), at_um=round(float(V[i]), 3),
                       bits=int(d[i]), face_bits=int(d[i] - dc[i]), tracks=int(c[i]),
                       core_core_max_use=round(float((dc / c).max()), 3),
                       cuts_over_0p6=int((u > 0.6 + 1e-9).sum()))
    return res


def _relax(W, H, nets, cores, iters=30):
    """bit-weighted-median core positions (overlaps allowed) -> nets with moved endpoints."""
    import numpy as np
    rect = {i: (r[0], r[1], r[2] - r[0], r[3] - r[1]) for i, r in cores.items()}

    def on(p):
        for i, (x, y, w, h) in rect.items():
            if x - 0.5 <= p[0] <= x + w + 0.5 and y - 0.5 <= p[1] <= y + h + 0.5:
                return i
        return None
    E = []
    for n in nets:
        e = []
        for p in n["pts"]:
            i = on(p)
            e.append((i, p[0] - rect[i][0] - rect[i][2] / 2, p[1] - rect[i][1] - rect[i][3] / 2) if i else
                     (None, p[0], p[1]))
        E.append(e)
    pos = {i: [x + w / 2, y + h / 2] for i, (x, y, w, h) in rect.items()}
    by_core = collections.defaultdict(list)
    for k, e in enumerate(E):
        for q in e:
            if q[0]:
                by_core[q[0]].append(k)

    def pts(e):
        return [(pos[i][0] + dx, pos[i][1] + dy) if i else (dx, dy) for i, dx, dy in e]
    for _ in range(iters):
        for i, ks in by_core.items():
            xs, ys, ws = [], [], []
            for k in set(ks):
                others = [p for q, p in zip(E[k], pts(E[k])) if q[0] != i]
                for p in others:
                    xs.append(p[0])
                    ys.append(p[1])
                    ws.append(nets[k]["bits"] / len(others))
            if not ws:
                continue
            w = np.array(ws)
            o = np.argsort(xs)
            cw = np.cumsum(w[o])
            mx = np.array(xs)[o][np.searchsorted(cw, cw[-1] / 2)]
            o = np.argsort(ys)
            cw = np.cumsum(w[o])
            my = np.array(ys)[o][np.searchsorted(cw, cw[-1] / 2)]
            cw_, ch_ = rect[i][2], rect[i][3]
            pos[i] = [min(max(mx, cw_ / 2), W - cw_ / 2), min(max(my, ch_ / 2), H - ch_ / 2)]
    return [dict(n, pts=[list(p) for p in pts(e)]) for n, e in zip(nets, E)]


def analyse(P, types=None, relaxed=False, lower_pg_frac=0.25):
    T = P["partition_types"]
    rows = {}
    for tn in sorted(types or T):
        t = T[tn]
        if not t.get("internal_stations"):
            continue
        W, H = t["outline_um"]
        nets = _nets(t)
        cores = _cores(t)
        p2p = sum(s["bits"] * (abs(s["from_um"][0] - s["to_um"][0]) + abs(s["from_um"][1] - s["to_um"][1]))
                  for s in t["internal_stations"])
        hp = sum(n["bits"] * (max(p[0] for p in n["pts"]) - min(p[0] for p in n["pts"]) +
                              max(p[1] for p in n["pts"]) - min(p[1] for p in n["pts"])) for n in nets)
        row = dict(outline_um=[W, H], stations=len(t["internal_stations"]), nets=len(nets),
                   multi_sink_nets=sum(1 for n in nets if n["sinks"] > 1),
                   bits_um_point_to_point=round(p2p), bits_um_tree_hpwl=round(hp),
                   cut=_cut_profile(W, H, nets, cores, lower_pg_frac))
        if relaxed:
            rn = _relax(W, H, nets, cores)
            row["relaxed_cut"] = _cut_profile(W, H, rn, cores, lower_pg_frac, blocked=False)
        u = max(row["cut"][a].get("max_use", 0) for a in "xy")
        row["verdict"] = "FAIL" if u > 0.6 + 1e-9 else "PASS"
        if relaxed:
            ur = max(row["relaxed_cut"][a].get("max_use", 0) for a in "xy")
            row["repack_can_pass"] = ur <= 0.6 + 1e-9
        rows[tn] = row
    return dict(schema="opentallas.plan_cut.v1", limit=0.6, lower_pg_frac=lower_pg_frac,
                fails=sorted(k for k, r in rows.items() if r["verdict"] == "FAIL"),
                repack_cannot_pass=sorted(k for k, r in rows.items() if r.get("repack_can_pass") is False),
                types=rows, note="cut LOWER bound (tree-aware); UNCHECKED until NUMBER-CHECK (12.9f)")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("plan", help="die_plan.json")
    ap.add_argument("--types", default="", help="comma list (default: every type with internal_stations)")
    ap.add_argument("--relaxed", action="store_true", help="also the relaxed WL-optimal re-pack bound")
    ap.add_argument("--lower-pg-frac", type=float, default=0.25)
    ap.add_argument("--out")
    a = ap.parse_args(argv)
    P = json.loads(Path(a.plan).read_text())
    rep = analyse(P, [x for x in a.types.split(",") if x] or None, a.relaxed, a.lower_pg_frac)
    rep["plan"] = str(a.plan)
    s = json.dumps(rep, indent=1)
    if a.out:
        Path(a.out).write_text(s + "\n")
    for tn, r in rep["types"].items():
        c = r["cut"]
        line = (f"{tn:14s} {r['verdict']} cut use x {c['x'].get('max_use')} y {c['y'].get('max_use')} "
                f"(core-core x {c['x'].get('core_core_max_use')} y {c['y'].get('core_core_max_use')})")
        if "relaxed_cut" in r:
            rc = r["relaxed_cut"]
            line += f" | relaxed re-pack x {rc['x'].get('max_use')} y {rc['y'].get('max_use')}"
        print(line)
    print("FAIL:", rep["fails"])
    if a.relaxed:
        print("no re-pack can pass:", rep["repack_cannot_pass"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
