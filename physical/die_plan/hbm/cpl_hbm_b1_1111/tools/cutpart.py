"""Per-partition cut ratios (check.py check_cuts model, every partition segment, not only the worst) for the
changed partitions.  Run from the worktree tools/die_plan dir.  usage: cutpart.py PLAN.json OUT.json PART,PART,..."""
import json, sys, math
from pathlib import Path
sys.path.insert(0, ".")
import check as C
from die_trial import die_core_rects, ft_band_rects

plan, outp, parts = sys.argv[1], sys.argv[2], sys.argv[3].split(",")
raw = json.load(open(plan))
P = C.S.Plan(raw, Path(plan))
geo = {lid: C.lane_geometry(P, lid) for lid in P.lanes}
EPS = C.EPS
cores = {L: die_core_rects(P, L) for L in {l for ls in C.PART_FT_LAYERS.values() for l in ls}}
bands = ft_band_rects(P)
step = P.budgets["cut_step_um"]
segs = []
owned = C.cut_owned_segments(P, geo)
for lid, (pts, _, _) in geo.items():
    w = P.ports[P.lanes[lid]["ports"][0]]["width"]
    tags = owned.get(lid) or {}
    for i, (p, q) in enumerate(zip(pts, pts[1:])):
        segs.append((p, q, w, tags.get(i)))
rects = {n: P.rect(n) for n in P.parts}
out = []
for orient, D in (("vertical", P.W), ("horizontal", P.H)):
    wire_dir = "H" if orient == "vertical" else "V"
    for k in range(1, int(D // step) + 1):
        c = k * step
        if c >= D - EPS: break
        rel = [pn for pn in parts if (lambda r: (r[0] < c - EPS and r[2] > c + EPS) if orient == "vertical" else (r[1] < c - EPS and r[3] > c + EPS))(rects[pn])]
        if not rel: continue
        hits = []
        for p, q, w, own in segs:
            a, b = (p[0], q[0]) if orient == "vertical" else (p[1], q[1])
            if min(a, b) < c - EPS and max(a, b) > c + EPS:
                y_ = p[1] if orient == "vertical" else p[0]
                pt = (c, y_) if orient == "vertical" else (y_, c)
                ch = next((kk for kk, r in (own or {}).items() if r[0] + EPS < pt[0] < r[2] - EPS and r[1] + EPS < pt[1] < r[3] - EPS), None)
                if ch is not None: continue
                hits.append((y_, w))
        for pn in rel:
            r = rects[pn]
            lo, hi = (r[1], r[3]) if orient == "vertical" else (r[0], r[2])
            t = P.ptype(pn); frac = t.get("ft_track_frac", C.FT_TRACK_FRAC); seg_cap = 0.0; cap0 = 0.0; flo = 0.0
            for L in C.PART_FT_LAYERS[wire_dir]:
                if L not in P.layers: continue
                obs = [((cr[1], cr[3]) if orient == "vertical" else (cr[0], cr[2])) for cr in cores[L]
                       if ((cr[0] + EPS < c < cr[2] - EPS) if orient == "vertical" else (cr[1] + EPS < c < cr[3] - EPS))]
                res = [(*((br[2], br[4]) if orient == "vertical" else (br[1], br[3])), br[5]) for br in bands if br[0] == L and
                       ((br[1] + EPS < c < br[3] - EPS) if orient == "vertical" else (br[2] + EPS < c < br[4] - EPS))]
                seg_cap += C.cut_interval_tracks(lo, hi, P.layers[L]["pitch_um"], frac, obs, res)
                cap0 += C.cut_interval_tracks(lo, hi, P.layers[L]["pitch_um"], frac, [], res)
                if obs: flo = max(flo, frac / P.layers[L]["pitch_um"])
                if L in ("M4", "M5"): flo = frac / P.layers[L]["pitch_um"]
            sb = sum(w for y, w in hits if lo - EPS <= y <= hi + EPS)
            out.append(dict(orient=orient, at=c, part=pn, bits=sb, cap=round(seg_cap, 1), cap0=round(cap0, 1), f_lo=flo, ratio=round(sb / seg_cap, 4) if seg_cap else None))
json.dump(out, open(outp, "w"))
print(len(out))
