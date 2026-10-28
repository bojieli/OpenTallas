"""Calibrate the planner's stage model d = d0 + k1 L_load + k2 L^2 + ks L_in (2-load node, input slew) against STA on the same
cells/RC the tree uses.  Emits a chain set; after OpenSTA runs, fit() returns stage_ps/stage_cell_ps/d0_frac-style
keys for clkplan.model (model JSON = technology data, no code change).

    python3 -m mscts.calib gen DIR          -> DIR/region_tree.{v,spef}, sta_<C>.tcl (chains of stages, lengths LS)
    python3 -m mscts.calib fit DIR [--corner TT] -> prints fitted (d0, k1, k2, k1_shared) and a model JSON fragment
"""
import json
import sys
from pathlib import Path

from . import netlist as NL

LS = [0.0, 25.0, 50.0, 100.0, 150.0, 200.0, 300.0, 400.0, 450.0, 600.0]


def chains():
    bufs, edges, sinks, meas = [], [], [], []
    # single-load chains: a -(L)-> b -(L)-> c  measure b->c
    for i, L in enumerate(LS):
        a, b, c = f"a{i}", f"b{i}", f"c{i}"
        bufs += [a, b, c]
        edges += [(a, b, L), (b, c, L)]
        sinks.append(c)
        meas.append(dict(kind="single", L=L, frm=b, to=c))
    # two-load node: p -(300)-> m ; m -(La)-> u ; m -(Lb)-> v ; measure m->u, m->v
    k = 0
    for La in (50.0, 200.0, 400.0):
        for Lb in (0.0, 200.0, 400.0):
            p, m, u, v = f"p{k}", f"m{k}", f"u{k}", f"v{k}"
            bufs += [p, m, u, v]
            edges += [(p, m, 300.0), (m, u, La), (m, v, Lb)]
            sinks += [u, v]
            meas.append(dict(kind="pair", La=La, Lb=Lb, frm=m, to=u, to2=v))
            k += 1
    return bufs, edges, sinks, meas


def gen(d):
    d = Path(d)
    d.mkdir(parents=True, exist_ok=True)
    bufs, edges, sinks, meas = chains()
    heads = [b for b in bufs if b not in {l for _, l, _ in edges}]
    # one source drives every chain head through a zero-length star (STA only measures differences)
    root = "root"
    edges = [(root, h, 0.0) for h in heads] + edges
    bufs = [root] + bufs
    (d / "region_tree.v").write_text(NL.verilog(bufs, edges, root, sinks))
    (d / "region_tree.spef").write_text(NL.spef(bufs, edges, sinks))
    allp = sorted({m["frm"] for m in meas} | {m["to"] for m in meas} | {m.get("to2") for m in meas if m.get("to2")})
    for c in ("TT", "FF"):
        t = NL.sta_tcl(f"lib_{c}.lib", allp, root).replace("sta_arr.txt", f"sta_arr_{c}.txt")
        t = t.replace(f"x_{root}/A ", f"x_{root}/A ")
        (d / f"sta_{c}.tcl").write_text(t)
    (d / "meas.json").write_text(json.dumps(meas))


def fit(d, corner):
    import numpy as np
    d = Path(d)
    meas = json.loads((d / "meas.json").read_text())
    st = {}
    for ln in (d / f"sta_arr_{corner}.txt").read_text().splitlines():
        p, v = ln.split()
        st[p.split("/")[0][2:]] = float(v)
    X, y = [], []
    for m in meas:
        if m["kind"] == "single":
            X.append([1.0, m["L"], m["L"] ** 2, m["L"]])      # input slew from the same-length feeding wire
            y.append(st[m["to"]] - st[m["frm"]])
        else:
            for L, tgt in ((m["La"], m["to"]), (m["Lb"], m["to2"])):
                X.append([1.0, m["La"] + m["Lb"], L ** 2, 300.0])
                y.append(st[tgt] - st[m["frm"]])
    X, y = np.array(X), np.array(y)
    c, *_ = np.linalg.lstsq(X, y, rcond=None)
    res = y - X @ c
    out = dict(corner=corner, d0=round(c[0], 4), k1=round(c[1], 6), k2=round(c[2], 8), ks=round(c[3], 6),
               resid_max_ps=round(float(abs(res).max()), 3))
    print(json.dumps(out))
    return out


def spice_scale(files):
    """per-sink least squares spice = s x model over mscts.run compare outputs (compare_<C>.json) of ONE corner.
    -> dict(scale, sinks, resid_min, resid_max); the scale goes into the model JSON as spice_scale {corner: s}."""
    X = []
    for f in files:
        d = json.loads(Path(f).read_text())
        X += [(r["model"], r["spice"]) for r in d["rows"] if r["spice"] == r["spice"] and r["model"] > 0]
    s = sum(m * p for m, p in X) / sum(m * m for m, _ in X)
    r = [p - s * m for m, p in X]
    n = len(X)
    mx, my = sum(m for m, _ in X) / n, sum(p for _, p in X) / n
    a = sum((m - mx) * (p - my) for m, p in X) / sum((m - mx) ** 2 for m, _ in X)
    b = my - a * mx
    ra = [p - (a * m + b) for m, p in X]
    # 'slope' (affine fit) is the per-stage scale to use: the constant b is a root offset (absolute insertion only;
    # it cancels in skew and in every crossing d)
    out = dict(scale=round(s, 4), sinks=n, resid_min_ps=round(min(r), 2), resid_max_ps=round(max(r), 2),
               slope=round(a, 4), offset_ps=round(b, 1), affine_resid_ps=[round(min(ra), 2), round(max(ra), 2)])
    print(json.dumps(out))
    return out


if __name__ == "__main__":
    if sys.argv[1] == "gen":
        gen(sys.argv[2])
    elif sys.argv[1] == "spice-scale":
        spice_scale(sys.argv[2:])
    else:
        fit(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else "TT")
