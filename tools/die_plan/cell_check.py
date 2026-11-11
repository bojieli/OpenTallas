#!/usr/bin/env python3
"""PLAN-GEN-RULES-1 rule C (OWNER 2026-11-10, all dies): cell-count check after a type's first synthesis.

ADVISORY (owner rule: targets, not gates): the run continues; a flag becomes a PLAN-CHANGE item (outline or split) for
the die owner, who ranks it first (route-flags rule), and a row in lanes/FLAGS-CELLCHECK.tsv (same columns as
PLAN-ROUTE-1's FLAGS-1110.tsv, which its cron rewrites from epyc4, so rule C keeps its own file).

Measures (PLAN-ROUTE-1 route_supply.add_density, same definitions):
  density  = measured synth std cells / um2 of the type outline not under a hard core (hard_cores[] union);
             FLAG at >= 0.42 (route_supply FLAG_AT["dens"]: QC slice types fail GRT from 0.424, pass up to 0.413)
  ratio    = measured synth cells / the plan's cell estimate (type.cells, else cells.py); FLAG above 1.5.  Not
             computed for a type with hard cores (its plan count is flat incl. the cores, the synth count is the top
             only) nor without an estimate.

    python3 -I tools/die_plan/cell_check.py --plan PLAN --type T --stat SYNTH_STAT [--cells N]  -> one JSON line
The kit wave runs it after place when the die option cell_check is true (kit_wave.after_place, CELL_CHECK line).
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

DENS_FLAG = 0.42          # route_supply FLAG_AT["dens"] (PLAN-ROUTE-1 11-10, 184 measured rows)
RATIO_FLAG = 1.5          # OWNER 11-10 rule C


def union_area(rects):
    """area of a union of axis-aligned rects [(x0, y0, x1, y1)] (coordinate compression; a handful of cores)."""
    rects = [r for r in rects if r[2] > r[0] and r[3] > r[1]]
    if not rects:
        return 0.0
    xs = sorted({r[0] for r in rects} | {r[2] for r in rects})
    a = 0.0
    for x0, x1 in zip(xs, xs[1:]):
        iv = sorted((r[1], r[3]) for r in rects if r[0] <= x0 and r[2] >= x1)
        cov, cur = 0.0, None
        for lo, hi in iv:
            if cur is None or lo > cur[1]:
                if cur:
                    cov += cur[1] - cur[0]
                cur = [lo, hi]
            else:
                cur[1] = max(cur[1], hi)
        if cur:
            cov += cur[1] - cur[0]
        a += cov * (x1 - x0)
    return a


def soft_area(t):
    """outline um2 not under a hard core (cores clipped to the outline)."""
    w, h = map(float, t["outline_um"])
    rr = []
    for hc in t.get("hard_cores", []) or []:
        ox, oy = map(float, hc["origin_um"])
        cw, ch = map(float, hc["outline_um"])
        rr.append((max(0.0, ox), max(0.0, oy), min(w, ox + cw), min(h, oy + ch)))
    return w * h - union_area(rr)


def plan_cells(raw, tn, plan_dir=None):
    """(cells, basis) of the plan estimate, or (None, why)."""
    t = raw["partition_types"][tn]
    if t.get("hard_cores"):
        return None, "type has hard cores: plan count is flat incl. the cores (not comparable to the synth top)"
    if t.get("cells"):
        return int(t["cells"]), "plan type.cells"
    try:
        import cells as C
        est, _ = C.estimate(raw, plan_dir=plan_dir)
        v = est.get(tn)
        if v and v[0]:
            return int(v[0]), f"cells.py {v[1]}"
    except Exception as e:  # advisory: no estimate is not an error
        return None, f"cells.py unavailable: {type(e).__name__}"
    return None, "no plan estimate"


def check(raw, tn, cells, area_um2=None, plan_dir=None):
    """-> {type, cells, soft_um2, density, ratio, flags[], plan_change} (flags empty = ok)."""
    t = raw["partition_types"][tn]
    soft = soft_area(t)
    dens = round(cells / soft, 4) if soft > 0 and cells else None
    pc, pb = plan_cells(raw, tn, plan_dir)
    ratio = round(cells / pc, 3) if pc and cells else None
    flags = []
    if dens is not None and dens >= DENS_FLAG:
        flags.append(f"density {dens:g} cells/um2 >= {DENS_FLAG:g}")
    if ratio is not None and ratio > RATIO_FLAG:
        flags.append(f"measured/plan cells {ratio:g} > {RATIO_FLAG:g}")
    w, h = map(float, t["outline_um"])
    change = None
    if flags:
        # the outline that would bring the density to the flag limit (same aspect), or a split into k types
        need = cells / DENS_FLAG
        grow = (need / soft) if soft > 0 else None
        k = int(-(-cells // int(DENS_FLAG * soft))) if soft > 0 else None
        change = (f"PLAN-CHANGE {tn}: outline {w:g} x {h:g} (soft {soft:.0f} um2) carries {cells} cells; "
                  + (f"grow the soft area x{grow:.2f} (to {need:.0f} um2) or split into {k} types" if grow else "re-plan")
                  + " (rule C, advisory; die owner ranks a plan change first)")
    return dict(type=tn, cells=cells, synth_area_um2=area_um2, outline_um=[w, h], soft_um2=round(soft, 1),
                density=dens, density_flag=DENS_FLAG, plan_cells=pc, plan_cells_basis=pb, ratio=ratio,
                ratio_flag=RATIO_FLAG, flags=flags, plan_change=change)


def over_threshold(r):
    """the larger measure / its flag limit (0 when neither is measured)."""
    return max((r["density"] / r.get("density_flag", DENS_FLAG)) if r.get("density") else 0.0,
               (r["ratio"] / r.get("ratio_flag", RATIO_FLAG)) if r.get("ratio") else 0.0)


def flags_row(stamp, main_sha, die, plan, plan_sha, r):
    """one FLAGS-1110.tsv-shaped row (stamp main die plan plan_sha type flagged region dir layer p99_ratio
    ratio_over_threshold all_flagged_regions suggested_plan_change porous_need_free provisional_children)."""
    over = over_threshold(r)
    return "\t".join(str(x) for x in (stamp, main_sha, die, plan, plan_sha, r["type"], "yes" if r["flags"] else "no",
                                      "cells", "A", "-", r["density"], round(over, 3), "; ".join(r["flags"]) or "-",
                                      r["plan_change"] or "-", "-", "-"))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--plan", required=True)
    ap.add_argument("--type", required=True)
    ap.add_argument("--stat", help="Yosys synth_stat.txt of the kit (cells, area)")
    ap.add_argument("--cells", type=int, help="measured cells (overrides --stat), e.g. native_cell_count stdcells")
    a = ap.parse_args(argv)
    raw = json.loads(Path(a.plan).read_text())
    if a.type not in raw["partition_types"]:
        print("CELL_CHECK " + json.dumps(dict(type=a.type, skipped="not a plan partition type (core item)")))
        return 0
    cells, area = a.cells, None
    if a.stat:
        import plan_gen_rules as PGR
        st = PGR.parse_stat(Path(a.stat).read_text(errors="replace"))
        cells = cells or st["cells"]
        area = st["area_um2"]
    if not cells:
        print("CELL_CHECK " + json.dumps(dict(type=a.type, skipped="no measured cell count")))
        return 0
    print("CELL_CHECK " + json.dumps(check(raw, a.type, int(cells), area, Path(a.plan).parent)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
