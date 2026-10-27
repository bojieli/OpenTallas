import json, sys, statistics as S
d = json.load(open(sys.argv[1]))
rows = d["rows"]
for c in ("TT", "FF"):
    v = sorted(rows, key=lambda r: -r[c]["sta_unc_ps"])
    print(c, "pairs", len(rows))
    for k in ("aocv_random_ps", "aocv_distance_ps", "mesh_mc_var_ps", "sta_unc_ps", "noncommon_ps", "mesh_uncertainty_ps", "nominal_dt_ps"):
        x = sorted(r[c][k] for r in rows)
        print(f"  {k:22s} min {x[0]:8.2f} med {S.median(x):8.2f} max {x[-1]:8.2f}")
    for r in v[:4]:
        print("  worst", r["a"], r["b"], {k: r[c][k] for k in ("aocv_random_ps", "aocv_distance_ps", "mesh_mc_var_ps", "sta_unc_ps", "noncommon_ps")}, "bbox", r["bbox_diag_mm"])
