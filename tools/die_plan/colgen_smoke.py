#!/usr/bin/env python3
"""S81-COLGEN-1 11-14: smoke of reset_replicate (C2) and lane_pad_route (C4) on real S81 col types.
usage: colgen_smoke.py PLAN.json --h9r2-type T --h9r2-bound BOUND.sv --h10r1-type T --h10r1-bound BOUND.sv [--out REPORT.json]
  C2: the bound col_h9_r2 module gets the per-region copies of u_d7_6_Y (grid 300 um); checks: every load re-pointed, one
      kept ot_dp_rrelay per region, total stages source -> load unchanged (7), no load left on the old wire.
  C4: the plan type col_h10_r1 gets lane_pad_route for frame_int_i1; checks: no stage in a wall zone, every hop <= 400,
      stage count vs the bound u_lpad_frame_int_i1 depth (kit_istations adds the difference)."""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lane_pad_route as L  # noqa: E402
import reset_replicate as RR  # noqa: E402


def arg(a, k):
    return a[a.index(k) + 1]


def main(a):
    plan = json.loads(Path(a[1]).read_text())
    rep = {}
    # C2
    t9 = plan["partition_types"][arg(a, "--h9r2-type")]
    txt = Path(arg(a, "--h9r2-bound")).read_text()
    new, rows = RR.apply(txt, [dict(driver="u_d7_6_Y", grid_um=300)], RR.positions_from_plan(t9))
    r = rows[0]
    q = r["driver"][2:]
    left = [ln for ln in new.split("\n") if re.search(r"\b" + re.escape(q) + r"\[", ln) and "u_" + q + "_r" not in ln and ".d(" not in ln]
    cells = new.count("ot_dp_rrelay u_" + q + "_r")
    ok9 = cells == r["copies"] > 1 and r["common_depth"] + r["copy_depth"] == r["depth"] == 7 and not left
    rep["C2"] = dict(r, cells_in_text=cells, loads_left_on_old_wire=len(left), ok=ok9)
    # C4
    tn = arg(a, "--h10r1-type")
    t10 = plan["partition_types"][tn]
    e = next(x for x in t10["internal_stations"] if x["conn"] == "bus:frame_int_i1")
    res = L.plan_entry(t10, e)
    zones = [g for _r, g in L.walls(t10)]
    in_zone = [p for p in res["regs_um"] if any(L._inside(p, z, eps=-1e-6) for z in zones)]
    d = re.search(r"ot_dp_dly #\(\.W\(\d+\), \.D\((\d+)\)\) u_lpad_frame_int_i1", Path(arg(a, "--h10r1-bound")).read_text())
    ok10 = not in_zone and res["max_hop_um"] <= L.LIMIT and bool(d)
    rep["C4"] = dict({k: v for k, v in res.items() if k != "route_um"}, route_um=res["route_um"], bound_pad_depth=int(d.group(1)) if d else None,
                     stages_in_wall_zone=len(in_zone), ok=ok10)
    rep["ok"] = ok9 and ok10
    if "--out" in a:
        Path(arg(a, "--out")).write_text(json.dumps(rep, indent=1))
    print(json.dumps({k: (v if k == "ok" else {kk: vv for kk, vv in v.items() if kk not in ("route_um", "hops_um", "region_names", "loads_per_region")})
                      for k, v in rep.items()}, indent=1))
    return 0 if rep["ok"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
