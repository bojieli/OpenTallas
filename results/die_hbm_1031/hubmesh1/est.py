#!/usr/bin/env python3
"""HBM-HUBMESH-1 estimate: linear-RC transient of a uniform hub mesh (qc_clk_mesh2.solve_netlist, main, unchanged) with
the ngspice-fit BUFx24 Thevenin (qc_mesh_pilot_1/thev_m1.json).  Straps 4W R6 RC, stubs 2W M8 (plan LAYER_RC x NDR),
tap load 2.3 fF (published_grid_clock).  Reports nominal tap skew (equal driver arrivals), the pass-through of a pre-mesh
driver residual, strap/stub cap, stub lengths.  Estimate only."""
import json, math, random, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "tools" / "die_plan"))
import qc_clk_mesh2 as Q

SEG = 54.0
R4 = Q.RC_R6["4w"]
STUB = (Q.LAYER_RC["M8"][0] * 1e3 * 0.5, Q.LAYER_RC["M8"][1] * 1.1)  # ohm/um, fF/um 2W M8


def build(hub, nc, nh, nd, stub_ndr=STUB):
    W, H = hub["W"], hub["H"]
    ox, oy = hub["origin"]
    taps = [(t["tap"], t["x"] - ox, t["y"] - oy) for t in hub["taps"] if t["tap"] != "clk"]
    xs = [(i + 0.5) * W / nc for i in range(nc)]
    ys = [(j + 0.5) * H / nh for j in range(nh)]
    dys = [(k + 0.5) * H / nd for k in range(nd)]
    R, C = [], {}
    pts_v = {x: set(ys) | set(dys) | {0.0, H} for x in xs}
    pts_h = {y: set(xs) | {0.0, W} for y in ys}
    att = []
    for name, x, y in taps:
        dv = min(xs, key=lambda a: abs(a - x)); dh = min(ys, key=lambda b: abs(b - y))
        if abs(dv - x) <= abs(dh - y):
            pts_v[dv].add(y); att.append((name, ("V", dv, y), abs(dv - x)))
        else:
            pts_h[dh].add(x); att.append((name, ("H", dh, x), abs(dh - y)))

    def node(k, a, b):
        return f"{k}:{a:.3f}:{b:.3f}"

    def wire(n0, n1, L, r, c):
        k = max(1, math.ceil(L / SEG)); prev = n0
        for s in range(k):
            nx = n1 if s == k - 1 else f"{n0}>{n1}#{s}"
            R.append((prev, nx, r * L / k)); C[prev] = C.get(prev, 0) + c * L / k / 2; C[nx] = C.get(nx, 0) + c * L / k / 2
            prev = nx
    cap = dict(strap=0.0, stub=0.0)
    for x, ps in pts_v.items():
        ps = sorted(p for p in ps if 0 <= p <= H)
        for a, b in zip(ps, ps[1:]):
            if b > a:
                wire(node("V", x, a), node("V", x, b), b - a, *R4["M9"]); cap["strap"] += R4["M9"][1] * (b - a)
    for y, ps in pts_h.items():
        ps = sorted(p for p in ps if 0 <= p <= W)
        for a, b in zip(ps, ps[1:]):
            if b > a:
                wire(node("H", y, a), node("H", y, b), b - a, *R4["M8"]); cap["strap"] += R4["M8"][1] * (b - a)
    for x in xs:   # vias at crossings
        for y in ys:
            R.append((node("V", x, y), node("H", y, x), 0.5))
    tapn = []
    for name, (k, a, b), L in att:
        n0 = node(k, a, b); n1 = "T_" + name
        if L > 0.5:
            wire(n0, n1, L, *stub_ndr); cap["stub"] += stub_ndr[1] * L
        else:
            R.append((n0, n1, 1.0))
        C[n1] = C.get(n1, 0) + Q.BUF_CIN_FF
        tapn.append((name, n1, L))
    drv = [dict(node=node("V", x, y), arr=0.0, dvn=[0.0], dvp=[0.0]) for x in xs for y in dys]
    return R, C, drv, tapn, cap


def run(hub, nc, nh, nd, corner, resid=0.0, seed=1):
    R, C, drv, tapn, cap = build(hub, nc, nh, nd)
    rnd = random.Random(seed)
    for d in drv:
        d["arr"] = rnd.uniform(-resid / 2, resid / 2) if resid else 0.0
    thev = json.load(open(Path(__file__).parent / "thev_m1.json"))
    N = dict(R=R, C=C, drv=drv, xnodes={n: v for n, v, _ in tapn}, taps=[])
    res, t0 = Q.solve_netlist(N, corner, thev, dt=0.5, t_extra=1500.0)
    arr = [res[("x", n)] + t0 for n, _, _ in tapn]
    return dict(nc=nc, nh=nh, nd=nd, drivers=len(drv), corner=corner, resid=resid, skew=max(arr) - min(arr),
                mean=sum(arr) / len(arr), cap_pf=round((cap["strap"] + cap["stub"] + Q.BUF_CIN_FF * len(tapn)) / 1e3, 2),
                strap_pf=round(cap["strap"] / 1e3, 2), stub_max=max(L for *_, L in tapn), stub_mean=sum(L for *_, L in tapn) / len(tapn))


if __name__ == "__main__":
    hubs = json.load(open(Path(__file__).parent / "hm_hubtaps.json"))
    out = []
    for hubname in sys.argv[1].split(","):
        for spec in sys.argv[2].split(";"):
            nc, nh, nd = (int(v) for v in spec.split(","))
            for corner in ("TT", "FF"):
                for resid in (0.0, 60.0):
                    r = run(hubs[hubname], nc, nh, nd, corner, resid)
                    r["hub"] = hubname
                    print(json.dumps({k: (round(v, 1) if isinstance(v, float) else v) for k, v in r.items()}), flush=True)
                    out.append(r)
