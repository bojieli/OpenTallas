#!/usr/bin/env python3
"""l48x vs l48z AUTO-GEOM (3_place, GRT 0-iteration) table over all HEAD types. usage: g2table.py PLAN REJUDGE_X GEOM_Z OUT_TSV"""
import json, sys
from pathlib import Path
plan, rx, gz, out = sys.argv[1:5]
types = sorted(json.load(open(plan))["partition_types"])
CHANGED = {"hd_st_n3_turn", "hd_st_n3_transit", "hd_mesh_e", "hd_spn_eshim_tx"}
R = ["pin_reg_max", "pin_reg_p90", "r2r", "r2r_count", "relay_collapse", "clock_reach", "aspect", "grt"]
def load(p):
    p = Path(p)
    if not p.exists(): return None
    a = json.load(open(p)); return {r["rule"]: (r["status"], r["value"]) for r in a["rules"]}
rows = ["type\tl48z_delta\tsource_x\tsource_z\t" + "\t".join(f"{r}_x\t{r}_z" for r in R) + "\tnew_fail_z"]
for t in types:
    x = load(f"{rx}/{t}.json"); zp = Path(f"{gz}/{t}/auto_geom.json"); z = load(zp)
    sx = "CHECKED(l48x wave, main rules)" if x else "UNCHECKED(no l48x wave geom)"
    if z: sz = "CHECKED(l48z kit)"
    elif t in CHANGED: sz = "MISSING"
    else: z, sz = x, ("SAME(type byte-identical)" if x else "UNCHECKED(type byte-identical)")
    f = lambda d, r: "" if not d or r not in d else ("%s%s" % (d[r][1], "!" if d[r][0] == "FAIL" else ("i" if d[r][0] == "INFO" else "")))
    nf = sorted(r for r in (z or {}) if z[r][0] == "FAIL" and not (x and x.get(r, ("",))[0] == "FAIL")) if z and z is not x else []
    rows.append("\t".join([t, "yes" if t in CHANGED else "no", sx, sz] + [f(d, r) for r in R for d in (x, z)] + [",".join(nf)]))
Path(out).write_text("\n".join(rows) + "\n"); print("\n".join(rows))
