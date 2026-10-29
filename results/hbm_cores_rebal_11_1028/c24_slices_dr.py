#!/usr/bin/env python3
"""HBM-CORES-REBAL-11: add the C24 plan-fixed driver_rect_um (c24_side.json core_arrays, from REBAL-6 dr_*.json) to
the mk_c20 slices of lanes_plain canon + programme_store_r10, and write the plan-fixed macro placement tables.
Uses the shared master_plan.pushdown_island(driver_rect=...) exactly as master_plan's in_core_islands caller does
(leaves only).  Refuses if the slice island rects differ from the array island rects (same 12.8b grid required).
  c24_slices_dr.py WT SIDE_JSON SLICEDIR OUTDIR mod1,mod2"""
import json, sys
from pathlib import Path
WT, side, sdir, out, mods = sys.argv[1], Path(sys.argv[2]), Path(sys.argv[3]), Path(sys.argv[4]), sys.argv[5].split(",")
sys.path.insert(0, f"{WT}/tools/die_plan")
import master_plan as MP  # noqa: E402
A = json.loads(side.read_text())["core_arrays"]
rep = {}
for m in mods:
    a = A[m]; p = sdir / f"{m}.json"; sl = json.loads(p.read_text())
    pd = sl["pushdown"]["islands"]
    assert len(pd) == len(a["islands"]), (m, len(pd), len(a["islands"]))
    ce = sl["islands"][0]["centre_um"]
    assert [list(map(float, ce))] == [list(map(float, x)) for x in a["plan_clock_entries"]] or \
        max(abs(ce[0] - a["plan_clock_entries"][0][0]), abs(ce[1] - a["plan_clock_entries"][0][1])) < 0.05, (m, ce)
    sl_isl = sl["islands"]
    n_dr = 0; det = []
    for i, ai in enumerate(a["islands"]):
        r = sl_isl[i]["rect_um"]
        assert [round(float(v), 3) for v in r] == [round(float(v), 3) for v in ai["rect_um"]], (m, i, r, ai["rect_um"])
        dr = ai.get("driver_rect_um")
        if i == 0:
            # entry island: driver box must sit on the entry (detour 0); slice entry form unchanged
            assert dr is None or ai["detour_um"] == 0.0, (m, ai)
            continue
        if dr is None:
            continue
        q = pd[i]
        sub = sl["in_core_islands"]
        args = (i, sl_isl[i]["rect_um"], sl_isl[i]["centre_um"], "tree_leaf", sub.get("leaf_reach_um", 0.0), 0)
        assert MP.pushdown_island(*args, pin_dx_um=1.08) == q, (m, i, "mk_c20 island not reproduced")
        pd[i] = MP.pushdown_island(*args, pin_dx_um=1.08, driver_rect=dr)
        n_dr += 1; det.append(ai["detour_um"])
    sl["note"] += f" | HBM-CORES-REBAL-11: C24 driver_rect_um on {n_dr} leaf islands (c24_side.json core_arrays)"
    p.write_text(json.dumps(sl, indent=1))
    mp = [dict(k=x["inst"][len("u_fcore."):], origin_um=x["origin_um"], orient=x["orient"], macro=a["macro_master"])
          for x in a["macro_placement"]]
    assert all(x["inst"].startswith("u_fcore.") for x in a["macro_placement"])
    (out / f"mp_{m}.json").write_text(json.dumps(dict(
        source=f"C24 plan 3ab76af4 c24_side.json core_arrays[{m}] ({a['source']})", macro_placement=mp), indent=1))
    rep[m] = dict(driver_rects=n_dr, max_detour_um=max(det or [0]), macros=len(mp))
print(json.dumps(rep))
