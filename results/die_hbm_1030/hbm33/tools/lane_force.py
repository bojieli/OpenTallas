#!/usr/bin/env python3
"""DIE-HBM-33 die-local driver (no shared tool change): run tools/die_plan/lane_add.py with a FORCED abutment chain per pair.
usage: lane_force.py WT PLANDIR ROWS OUT CHAINS.json [--first-id N] [--guard-um G]
CHAINS.json = {"SRC>DST": [part, ...]}; pairs not listed use the lane_add candidates."""
import json, sys, argparse
ap = argparse.ArgumentParser(); ap.add_argument("wt"); ap.add_argument("plan"); ap.add_argument("rows"); ap.add_argument("out")
ap.add_argument("chains"); ap.add_argument("--first-id", type=int, default=600); ap.add_argument("--guard-um", type=float, default=2.0)
ap.add_argument("--near-um", type=float, default=20000.0); ap.add_argument("--max-hops", type=int, default=16)
ap.add_argument("--keep-x", action="append", default=[], help="PART:X0:X1 = station FF homes of PART only at die x in [X0,X1] (forces the chain order through the previous partition)")
a = ap.parse_args()
sys.path.insert(0, a.wt + "/tools/die_plan")
import lane_add as LA
CH = json.load(open(a.chains))
orig = LA.Builder.template
def template(self, s, d):
    c = CH.get(f"{s}>{d}")
    if c:
        assert c[0] == s and c[-1] == d, c
        for u, v in zip(c, c[1:]):
            assert LA.shared_edge(self.P, u, v), f"not abutting {u}|{v}"
        return [("path", None, c)]
    return orig(self, s, d)
LA.Builder.template = template
import os
DEBUG = os.environ.get("LF_DEBUG") == "1"
KEEP = {}
for k in a.keep_x:
    p, x0, x1 = k.split(":"); KEEP[p] = (float(x0), float(x1))
if KEEP:
    import schema as S
    _pmb = S.placed_macro_boxes
    _cur = {}
    orig_resite = LA.Builder.resite
    def resite(self, chain, slots, start, end):
        # add a full-height pseudo keep-out box over the excluded x range of each KEEP partition (type frame)
        saved = {}
        for p, (x0, x1) in KEEP.items():
            if p in [sl[0] for sl in slots]:
                X0, Y0, X1, Y1 = self.P.rect(p)
                saved[p] = [(X0 - 1, Y0 - 1, x0, Y1 + 1), (x1, Y0 - 1, X1 + 1, Y1 + 1)]
        def pmb(t, halo=0.0, _o=_pmb):
            d = dict(_o(t, halo=halo))
            for p, bx in saved.items():
                if self.P.ptype(p) is t:
                    for i, (a0, b0, a1, b1) in enumerate(bx):
                        c0, c1 = self.P.to_type(p, (a0, b0)), self.P.to_type(p, (a1, b1))
                        d[f"__keepx{i}"] = (min(c0[0], c1[0]), min(c0[1], c1[1]), max(c0[0], c1[0]), max(c0[1], c1[1]))
            return d
        S.placed_macro_boxes = pmb
        import station_resite as SR
        _r = SR.route; got = {}
        def route(*aa, **kk):
            got["r"] = _r(*aa, **kk); return got["r"]
        SR.route = route
        try:
            out = orig_resite(self, chain, slots, start, end)
            if out is None and DEBUG:
                mids = [sl[0] for sl in slots]
                X0 = min(self.P.rect(p)[0] for p in mids); Y0 = min(self.P.rect(p)[1] for p in mids)
                r = got.get("r")
                print("DEBUG resite fail", chain[0], chain[-1], "K", sum(sl[8] for sl in slots), "per-slot k", [sl[8] for sl in slots],
                      "route", "None" if r is None else len(r), "start", start, "end", end)
                if r:
                    seq = []
                    for rx, ry in r:
                        x, y = rx + X0, ry + Y0
                        seq.append(next((p for p in mids if self.P.rect(p)[0] <= x <= self.P.rect(p)[2] and self.P.rect(p)[1] <= y <= self.P.rect(p)[3]), "?"))
                    print("DEBUG owners", seq)
                    print("DEBUG route_um/len", [(sl[0], round(sl[10]), seq.count(sl[0])) for sl in slots], "smax", self.smax)
            return out
        finally:
            S.placed_macro_boxes = _pmb; SR.route = _r
    LA.Builder.resite = resite
if os.environ.get("LF_SNAP") == "1":
    import numpy as np
    import check as C
    import schema as S2
    _orig_resite2 = LA.Builder.resite
    def resite_snap(self, chain, slots, start, end):
        """die-local station homes: the lane_add even points on each crossed partition's own route, each snapped to the
        nearest free 4.32-lattice point of THAT partition (interior, off every macro + halo), then the reach check;
        a slot whose hops break reach gets one more station (up to +3).  Falls back to lane_add resite."""
        import station_resite as SR
        G, H = SR.G, SR.HALO
        P = self.P
        def free_pts(p):
            x0, y0, x1, y1 = P.rect(p)
            xs = np.arange(math.ceil((x0 + H) / G), math.floor((x1 - H) / G) + 1) * G
            ys = np.arange(math.ceil((y0 + H) / G), math.floor((y1 - H) / G) + 1) * G
            X, Y = np.meshgrid(xs, ys, indexing="ij"); m = np.ones(X.shape, bool)
            for bx0, by0, bx1, by1 in S2.placed_macro_boxes(P.ptype(p), halo=H).values():
                c0, c1 = P.to_die(p, (bx0, by0)), P.to_die(p, (bx1, by1))
                ux0, ux1 = sorted((c0[0], c1[0])); uy0, uy1 = sorted((c0[1], c1[1]))
                m &= ~((X > ux0 - 1e-6) & (X < ux1 + 1e-6) & (Y > uy0 - 1e-6) & (Y < uy1 + 1e-6))
            return X[m], Y[m]
        fp = {sl[0]: free_pts(sl[0]) for sl in slots}
        def place(sl, k):
            seg, L = sl[12 + 1] if False else None, sl[10]
            return None
        # rebuild the per-slot segments as lane_add stations_for does
        segs = []
        for sl in slots:
            part, i, dfi, wi, li, dfo, wo, lo_, k, regs, L, h, even = sl
            a0 = self.face_pt(P, part, LA.OPP[dfi], wi); b0 = self.face_pt(P, part, dfo, wo)
            segs.append(C.zroute(a0, b0, LA.OPP[dfi], dfo))
        ks = [sl[8] for sl in slots]
        for it in range(40):
            out = []
            for sl, seg, k in zip(slots, segs, ks):
                L = C.plen(seg); X, Y = fp[sl[0]]
                if len(X) == 0:
                    return _orig_resite2(self, chain, slots, start, end)
                rr = []
                for j in range(k):
                    px, py = C.point_at(seg, L * (j + 0.5) / k)
                    q = int(np.argmin(np.abs(X - px) + np.abs(Y - py)))
                    rr.append((round(float(X[q]), 4), round(float(Y[q]), 4)))
                out.append(rr)
            pts = [start] + [r for rr in out for r in rr] + [end]
            hops = [abs(p[0] - q[0]) + abs(p[1] - q[1]) for p, q in zip(pts, pts[1:])]
            bad = [i for i, hh in enumerate(hops) if hh > self.reach + 1e-6]
            if not bad and all(C.plen(seg) / k <= self.smax + 1e-6 for seg, k in zip(segs, ks)):
                return out
            # add a station to the slot owning the first bad hop (or the over-long slot)
            idx = 0; cnt = 0; owner = []
            for si, rr in enumerate(out):
                owner += [si] * len(rr)
            if bad:
                hb = bad[0]
                si = owner[min(hb, len(owner) - 1)] if hb < len(owner) else len(out) - 1
            else:
                si = max(range(len(segs)), key=lambda t: C.plen(segs[t]) / ks[t])
            ks[si] += 1
            if DEBUG:
                print("DEBUG snap it", it, "bad hops", [(b, round(hops[b])) for b in bad][:4], "-> +1 station slot", slots[si][0])
        return _orig_resite2(self, chain, slots, start, end)
    import math
    LA.Builder.resite = resite_snap
_bo = LA.Builder.build_one
def build_one(self, a, b, bits, chain, kind, tl, record=True, part=0):
    r = _bo(self, a, b, bits, chain, kind, tl, record=record, part=part)
    if r is None and DEBUG:
        print("DEBUG build_one fail", a, b, bits, "why", self._why)
    return r
LA.Builder.build_one = build_one
PREF = json.load(open(os.environ["LF_PREFER"])) if os.environ.get("LF_PREFER") else {}
if PREF:
    _al = LA.Builder.alloc
    def alloc(self, a, b, width, prefer=None):
        t = PREF.get(f"{a}|{b}", PREF.get(f"{b}|{a}"))
        return _al(self, a, b, width, prefer=t if t is not None else prefer)
    LA.Builder.alloc = alloc
rep = LA.run(a.plan, a.rows, a.out, a.near_um, a.first_id, a.max_hops, a.guard_um)
print(json.dumps(rep["totals"]))
for r in rep["built"]:
    print("BUILT", r["lane"], r["src"], r["dst"], r["bits"], "cyc", r["cycles"], "st", r["stations"], r.get("split"),
          [w["edge"] + ":" + "%.1f-%.1f" % tuple(w["window_um"]) for w in r["windows"]])
for r in rep["failed"]:
    print("FAILED", json.dumps(r)[:400])
for r in rep["far"]:
    print("FAR", r)
