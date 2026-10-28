import sys, json
from pathlib import Path
sys.path.insert(0, sys.argv[1]); import die_sta_related as R
R.CPPR_LCA = True
P = Path(sys.argv[2]); a, b = sys.argv[3], sys.argv[4]
for c in ("FF",):
    meta, taps = R.load_taps(P, c); meta, taps = R.scale_clock(meta, taps, R.SPICE_CLOCK_CAL[c])
    dreg = R.droop_regions(P, taps, "mesh", str(P / "droop_regions.json"))
    f = R.clock_ocv_fn("table", "shared", dict(meta, corner=c), taps, 250.0, region=dreg)
    A, B_ = taps[a], taps[b]; node = R.pair_node(A, B_); la, ea, lc, ec = R.arr4(A, B_, node)
    cr = R.credit(meta["cppr_node_range_ps"], node, la, ea, lc, ec)
    print(c, "node", node, "la ea lc ec", round(la,1), round(ea,1), round(lc,1), round(ec,1), "cr", round(cr,1), "ocv_hold", round(f(a, b, "hold"),1), "A", {k: A.get(k) for k in ("part","cppr_node","stages_from_root","xy_um","kind","role")}, "B", {k: B_.get(k) for k in ("part","cppr_node","stages_from_root","xy_um","kind","role")})
    print(sorted(A.keys()))
