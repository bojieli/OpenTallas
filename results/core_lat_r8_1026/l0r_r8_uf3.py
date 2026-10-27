#!/usr/bin/env python3
"""S81-CORE-LAT-R8: re-predict an R8 frozen l0r plan with MODEL-REFIT-3 uf_phys3 v1 (COORD 18:1x: "use it for all
predictions"; pre-build guard TT 250+-9, FF 202.5+-10, predicted window <= 14).

Adapter only: builds the uf_phys Plan object (nodes / kids / nets) directly from the plan record instead of an mscts
spec Tcl -- every driver net = its planned maze segment (2-pin) or, for a landed node, segment to the hub + Manhattan
stubs to the co-located children; leaf nets = the named sinks at their GPL xy.  Kernel, parameters (PMAX/PMIN of
uf_phys3_v1.json), basis (GRT, rc_cal 0.8/0.9) unchanged.  The fit builds used standard-width trunks: the NDR2W trunk
is reported as an extrapolation variant (R45 x0.5, C45 x1.25), never as the gate number.
usage: l0r_r8_uf3.py R8.json GEO(.gz) LIBDIR(with invbuf_tt.lib/invbuf_ff.lib) FIT.json OUT.json
PLAN MODEL, UNCHECKED."""
import gzip, json, statistics as st, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[0] / "model_refit2_1026" / "py"))
sys.path.insert(0, str(HERE.parents[0] / "model_refit3_1026" / "py"))
import uf_phys as U    # noqa: E402
import uf_phys3 as V3  # noqa: E402

GUARD = {"TT": (250.0, 9.0), "FF": (202.5, 10.0)}
WMAX = 14.0


class PlanFromRecord:
    def __init__(self, rec, geo):
        op = gzip.open if geo.endswith(".gz") else open
        sxy = {}
        for l in op(geo, "rt"):
            f = l.split()
            if f and f[0] == "SINK":
                sxy["%s/%s" % (f[4], f[5])] = (float(f[1]), float(f[2]))
        self.nodes, self.kids, self.nets = {}, {}, {}
        par = {}
        for name, p, xy, cell, kind in rec["nodes_xy"]:
            self.nodes[name] = dict(cell=cell, kind="leaf" if kind == "leaf" else "buf", xy=tuple(xy))
            if p is not None:
                self.kids.setdefault(p, []).append(name); par[name] = p
        for leaf, sinks in rec["leaf_sinks"].items():
            self.nodes[leaf]["sinks"] = [sxy[s] for s in sinks]
        seg, hub = {}, {}
        for w in rec["wire_paths"]:
            e = w["edge"]; k = len(w["segs"])
            names = [e + "_br"] + [e + "_r%d" % i for i in range(k - 1)] + [e]
            for i in range(k):
                seg[names[i]] = w["segs"][i]
                hub[names[i]] = tuple(w["paths"][i][-1])
        for d, ch in self.kids.items():
            dxy = self.nodes[d]["xy"]
            if d in seg and len(ch) == 1 and self.nodes[ch[0]]["xy"] == hub[d]:
                pts = [dxy, hub[d]]; E = [(0, 1, seg[d])]; pin = {ch[0]: 1}
            elif d in seg:                       # landed: segment to the hub, stubs to the co-located children
                h = hub[d]; pts = [dxy, h] + [self.nodes[c]["xy"] for c in ch]
                E = [(0, 1, seg[d])] + [(1, i + 2, U.man(h, self.nodes[c]["xy"])) for i, c in enumerate(ch)]
                pin = {c: i + 2 for i, c in enumerate(ch)}
            else:                                # entry root: local fan to its co-located branch buffers
                pts = [dxy] + [self.nodes[c]["xy"] for c in ch]
                E = [(0, i + 1, U.man(dxy, self.nodes[c]["xy"])) for i, c in enumerate(ch)]
                pin = {c: i + 1 for i, c in enumerate(ch)}
            self.nets[d] = dict(pts=pts, edges=E, pin=pin, detour=1.0)


def summ(v):
    v = list(v)
    return dict(mean=round(st.mean(v), 2), min=round(min(v), 2), max=round(max(v), 2), window=round(max(v) - min(v), 2))


def predict(plan, L, pmax, pmin):
    tt = V3.basis_leaf(plan, L, "TT", "max", pmax)
    ffr, _ = V3.predict3(plan, L, "FF", edge="rise", **pmin)
    fff, _ = V3.predict3(plan, L, "FF", edge="fall", **pmin)
    ff = {k: min(ffr[k], fff[k]) for k in ffr}
    return dict(TT_rise=summ(tt.values()), FF_early=summ(ff.values()))


def main():
    rj, geo, libdir, fit, out = sys.argv[1:6]
    rec = json.load(open(rj))[0]
    F = json.load(open(fit)); pmax, pmin = dict(F["PMAX"]), dict(F["PMIN"])
    cells = sorted({n[3] for n in rec["nodes_xy"]})
    for c in cells:
        if c not in U.SIZES:
            U.SIZES.append(c)
    L = U.load_libs(libdir)
    plan = PlanFromRecord(rec, geo)
    o = dict(plan=rec["name"], fit=F["name"], basis="GRT", gate=predict(plan, L, pmax, pmin))
    r0, c0 = U.R45, U.C45
    U.R45, U.C45 = r0 * 0.5, c0 * 1.25
    o["ndr2w_trunk_extrapolation"] = predict(plan, L, pmax, pmin)
    U.R45, U.C45 = r0, c0
    g = o["gate"]
    chk = dict(TT_mean=abs(g["TT_rise"]["mean"] - 250.0) <= 9.0, FF_mean=abs(g["FF_early"]["mean"] - 202.5) <= 10.0,
               TT_window=g["TT_rise"]["window"] <= WMAX, FF_window=g["FF_early"]["window"] <= WMAX)
    o["guard"] = dict(rule="COORD 18:1x: TT 250+-9, FF 202.5+-10, window <= 14 (uf_phys3 v1, std-width trunk = gate number)",
                      checks=chk, verdict="PASS" if all(chk.values()) else "FAIL")
    o["scope"] = "PLAN MODEL uf_phys3 v1 via record adapter, UNCHECKED"
    Path(out).write_text(json.dumps(o, indent=1))
    print("UF3 %s TT %.2f w%.2f | FF %.2f w%.2f | guard %s | NDR-extrap TT %.2f w%.2f FF %.2f w%.2f" % (
        rec["name"], g["TT_rise"]["mean"], g["TT_rise"]["window"], g["FF_early"]["mean"], g["FF_early"]["window"],
        o["guard"]["verdict"], o["ndr2w_trunk_extrapolation"]["TT_rise"]["mean"], o["ndr2w_trunk_extrapolation"]["TT_rise"]["window"],
        o["ndr2w_trunk_extrapolation"]["FF_early"]["mean"], o["ndr2w_trunk_extrapolation"]["FF_early"]["window"]))


if __name__ == "__main__":
    main()
