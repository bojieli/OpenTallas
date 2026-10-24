#!/usr/bin/env python3
"""PART-CAP: per-die census of P&R units under the current plans (read-only on physical/die_plan/*/die_plan.json).

For every die: partitions, partition types, hard-core instances / unique core modules, total estimated std cells
(tools/die_plan/cells.py estimates; type cells include their hard cores), the type-cell distribution, and the
internal seam length (shared partition edges, um) + hard-core perimeter.  Then, for a cap C, two first-order estimates:
  flatten:  a type with cells <= C is one P&R run (its hard cores dissolve into it); a type > C keeps cores sized <= C
            (ceil(cells / C) runs).  -> P&R units, unique runs (types + unique cores), core seam perimeter kept.
  regions:  minimum region count if partitions could also merge freely: ceil(total / C) (lower bound).
usage: plan_census.py [--caps 400000,800000,1600000,3000000] [--json OUT]"""
import argparse, json, math, sys, collections
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools/die_plan"))
import cells as CE

DIES = {"s81": "S81 (DeepSeek ROM array die)", "qwen_compute": "Qwen ROM compute", "qwen_kvsys": "Qwen KV/system",
        "hbm": "HBM accelerator d4g"}


def rect(p, t):
    w, h = t["outline_um"]
    if p.get("orient", "R0") in ("R90", "R270", "MXR90", "MYR90"):
        w, h = h, w
    x, y = p["origin_um"]
    return x, y, x + w, y + h


def shared(a, b, eps=0.05):
    if abs(a[2] - b[0]) < eps or abs(b[2] - a[0]) < eps:
        return max(0.0, min(a[3], b[3]) - max(a[1], b[1]))
    if abs(a[3] - b[1]) < eps or abs(b[3] - a[1]) < eps:
        return max(0.0, min(a[2], b[2]) - max(a[0], b[0]))
    return 0.0


def census(d, caps):
    pp = ROOT / f"physical/die_plan/{d}/die_plan.json"
    P = json.load(open(pp))
    est, _ = CE.estimate(P, pp.parent)
    T = P["partition_types"]
    inst = collections.Counter(p["type"] for p in P["partitions"])
    rs = [rect(p, T[p["type"]]) for p in P["partitions"]]
    seam = 0.0
    xs = sorted(range(len(rs)), key=lambda i: rs[i][0])
    for ii, i in enumerate(xs):
        for j in xs[ii + 1:]:
            if rs[j][0] > rs[i][2] + 0.1:
                break
            seam += shared(rs[i], rs[j])
    for i in range(len(rs)):        # y-adjacent pairs not caught by the x sweep (same x span)
        pass
    seam2 = 0.0
    for i in range(len(rs)):
        for j in range(i + 1, len(rs)):
            seam2 += shared(rs[i], rs[j])
    cores = sum(len(T[t].get("hard_cores", [])) * n for t, n in inst.items())
    core_mods = {c.get("module", c.get("inst")) for t in inst for c in T[t].get("hard_cores", [])}
    core_perim = sum(2 * sum(c["outline_um"]) * n for t, n in inst.items() for c in T[t].get("hard_cores", [])
                     if c.get("outline_um"))
    tot = sum(est.get(t, (0, ""))[0] * n for t, n in inst.items())
    out = {"die": d, "label": DIES[d], "partitions": len(P["partitions"]), "types": len(T),
           "hard_core_instances": cores, "unique_core_modules": len(core_mods),
           "pnr_units_now": len(P["partitions"]) + cores, "unique_runs_now": len(T) + len(core_mods),
           "total_cells_est": tot, "partition_seam_um": round(seam2), "core_perimeter_um": round(core_perim),
           "type_cells": {t: est.get(t, (None,))[0] for t in T},
           "type_cells_quantiles": None, "caps": {}}
    vals = sorted(v for v in (est.get(t, (None,))[0] for t in inst) if v)
    if vals:
        q = lambda f: vals[min(len(vals) - 1, int(f * len(vals)))]
        out["type_cells_quantiles"] = {"min": vals[0], "p50": q(0.5), "p90": q(0.9), "max": vals[-1]}
    for C in caps:
        units = runs = 0
        kept_core_perim = 0.0
        for t, n in inst.items():
            c = est.get(t, (0,))[0] or 0
            k = 1 if c <= C else math.ceil(c / C)
            units += k * n
            runs += 1 if c <= C else 1 + len({x.get("module") for x in T[t].get("hard_cores", [])}) or k
            if c > C:
                kept_core_perim += sum(2 * sum(x["outline_um"]) for x in T[t].get("hard_cores", [])
                                       if x.get("outline_um")) * n
        out["caps"][str(C)] = {"flatten_units": units, "flatten_unique_runs_approx": runs,
                               "regions_lower_bound": math.ceil(tot / C) if tot else None,
                               "core_perimeter_kept_um": round(kept_core_perim)}
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--caps", default="400000,800000,1600000,3000000")
    ap.add_argument("--json")
    a = ap.parse_args()
    caps = [int(x) for x in a.caps.split(",")]
    res = [census(d, caps) for d in DIES]
    for r in res:
        print(f"{r['die']:13s} parts {r['partitions']:4d} types {r['types']:4d} cores {r['hard_core_instances']:5d} "
              f"core_mods {r['unique_core_modules']:4d} units {r['pnr_units_now']:5d} cells {r['total_cells_est']/1e6:7.1f}M "
              f"seam {r['partition_seam_um']/1e3:7.1f}mm coreperim {r['core_perimeter_um']/1e3:7.1f}mm q {r['type_cells_quantiles']}")
        for C, v in r["caps"].items():
            print(f"     cap {int(C)/1e6:4.1f}M: {v}")
    if a.json:
        for r in res:
            r.pop("type_cells")
        Path(a.json).write_text(json.dumps(res, indent=1) + "\n")


if __name__ == "__main__":
    main()
