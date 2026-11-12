"""SC-REFLOOR-1: route_supply with net recording; attributes V/H demand in the hot bins to ft slots / rings / cores.
usage: (cwd = src repo) python3 -I rs_attr.py OUTJSON route_supply args...
Runs route_supply.main unchanged, but with cfg record_nets on, and keeps each type's net records + ratio maps."""
import json, sys, os
import numpy as np
sys.path.insert(0, os.path.join(os.getcwd(), "tools", "die_plan"))
import route_supply as rs

OUT = sys.argv[1]
KEEP = {}
_orig = rs.analyze_type


def wrapped(name, t, die_dir, repo, conns, cfg):
    cfg = dict(cfg, record_nets=True)
    r = _orig(name, t, die_dir, repo, conns, cfg)
    if r is not None:
        KEEP[name] = dict(rec=r["_rec"], maps=r["_maps"], sup=r["_sup"], b=r["_bin"], W=t["outline_um"][0],
                          H=t["outline_um"][1], bands=((t.get("clock") or {}).get("landing_contract") or {}).get("bands") or {})
    return r


rs.analyze_type = wrapped
rs.main(sys.argv[2:])

res = {}
for name, k in KEEP.items():
    rH, rV, cls = k["maps"]
    supH, supV = k["sup"]
    b = k["b"]
    ny, nx = rV.shape
    out = {}
    for d, R in (("V", rV), ("H", rH)):
        hot = R > 1.0
        thr = np.percentile(R, 99)
        sel = R >= min(thr, 1.0) if hot.any() else R >= thr
        js, is_ = np.nonzero(sel)
        cen = [((i + 0.5) * b, (j + 0.5) * b) for j, i in zip(js, is_)]
        # attribute: each record's demand density in the selected bins (RUDY uniform over bbox, min 1 bin)
        acc = {}
        tot = 0.0
        for cat, label, x0, x1, y0, y1, n in k["rec"]:
            w, h = max(x1 - x0, b), max(y1 - y0, b)
            amt = (y1 - y0) if d == "V" else (x1 - x0)
            if amt <= 0:
                continue
            dens = n * amt / (w * h)             # track-um per um2
            # overlap with selected bins
            ov = 0
            for (cx, cy) in cen:
                if x0 - b / 2 <= cx <= x0 + w + b / 2 and y0 - b / 2 <= cy <= y0 + h + b / 2:
                    ov += 1
            if ov:
                key = f"{cat}:{label[1] if isinstance(label, tuple) and len(label) > 1 else label}"
                v = dens * ov * b * b / b      # tracks summed over selected bins
                acc[key] = acc.get(key, 0) + v
                tot += v
        top = sorted(acc.items(), key=lambda x: -x[1])[:25]
        # bin locations summary
        out[d] = dict(sel_bins=int(sel.sum()), hot_bins=int(hot.sum()), p99=float(thr),
                      x_range=[float(is_.min() * b), float((is_.max() + 1) * b)] if len(is_) else None,
                      y_range=[float(js.min() * b), float((js.max() + 1) * b)] if len(js) else None,
                      cls=dict(zip(*np.unique(cls[sel], return_counts=True))) if sel.any() else {},
                      top=[(a, round(v / max(tot, 1e-9), 3)) for a, v in top])
        out[d]["cls"] = {str(a): int(c) for a, c in out[d]["cls"].items()}
    # whole-type V/H track-um by category and by ft slot
    cat_tot = {}
    for cat, label, x0, x1, y0, y1, n in k["rec"]:
        key = f"{cat}:{label[1] if isinstance(label, tuple) and len(label) > 1 else label}"
        a = cat_tot.setdefault(key, [0.0, 0.0])
        a[0] += n * (x1 - x0)
        a[1] += n * (y1 - y0)
    out["trackum"] = {kk: [round(v[0]), round(v[1])] for kk, v in sorted(cat_tot.items(), key=lambda x: -x[1][1])}
    out["supply_V_trackum_total"] = float(supV.sum() * b)
    out["supply_H_trackum_total"] = float(supH.sum() * b)
    # row profile: V ratio max per 10.8-um row band and column
    out["rV_colmax"] = [round(float(v), 2) for v in rV.max(axis=0)]
    out["rV_rowmax"] = [round(float(v), 2) for v in rV.max(axis=1)]
    np.savez_compressed(OUT.replace(".json", f"__{name}.npz"), rH=rH, rV=rV, supH=supH, supV=supV)
    res[name] = out
json.dump(res, open(OUT, "w"), indent=1)
