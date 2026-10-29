#!/usr/bin/env python3
"""DIE-S81-19 bk_sel structural-form ESTIMATE (12.14b, no build). Input: DIE-S81-18 bksel_est_bk_sel.json (go15 legs,
cal residual vs max root->tap path wire). Model: worst residual ~ slope x max path wire, slope bracketed by the three
measured (path, resid) points; path of a centroid-rooted local tree in a w x h box ~ (w/2 + h/2) x detour 1.15.
Cross-subtree related pairs add the feed/mesh skew between sub-roots (S81 has no measured mesh -> UNCHECKED)."""
import json, sys
e = json.load(open(sys.argv[1]))
out = {}
for C in ("TT", "FF"):
    d = e[C]; W, H = d["span_um"]
    pts = [(d["one_root_max_path_wire_um"], d["one_root_resid_max_ps"]), (d["half0"]["max_path_wire_um"], d["half0"]["resid_max_ps"]),
           (d["half1"]["max_path_wire_um"], d["half1"]["resid_max_ps"])]
    s = [r / p for p, r in pts]; lo, hi = min(s), max(s)
    forms = {}
    for name, nx, ny in (("2 roots (x cut, S81-18)", 2, 1), ("4 local trees 4x1", 4, 1), ("8 local trees 4x2", 4, 2),
                         ("12 local trees 6x2", 6, 2)):
        w, h = W / nx, H / ny; path = (w / 2 + h / 2) * 1.15
        forms[name] = dict(subbox_um=[round(w), round(h)], taps_per_tree=round(d["taps"] / (nx * ny), 1), path_um=round(path),
                           resid_ps=[round(lo * path, 1), round(hi * path, 1)])
    out[C] = dict(slope_ps_per_um=[round(lo, 4), round(hi, 4)], forms=forms)
json.dump(out, open(sys.argv[2], "w"), indent=1)
for C, v in out.items():
    print(C, "slope", v["slope_ps_per_um"])
    for k, f in v["forms"].items(): print("  ", k, f)
