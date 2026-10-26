#!/usr/bin/env python3
"""CLOCK-128-R2: die-frame reserved clock sites (ot_clock_sites/1) from the master-plan slices (12.2a1 / COORD 11:26).

The master plan (die_infra.py master-plan, master_plan.write_slices) declares, per partition / core TYPE, the pushdown
islands (fixed dont_touch driver cells + mp_isl* ft ports, identical in every instance) and the plan-fixed H-tree leg
repeaters (pushdown.clock_repeaters).  This tool maps every one of them through every instance of its type into the
die frame, so die_clock_mesh.py build --plan-sites puts each mesh driver / tree node / repeater ON its plan site: the
only allowed move is the PG-track snap (die_clock_128.SITE_SNAP_UM); a farther point is a plan error, never a slide.

  python3 tools/die_plan/clock_plan_sites.py PLAN SLICES_DIR --out sites.json

Interface (agreed with MASTER-PLAN-R2; the master-plan tool may later write this file itself):
  {"schema": "ot_clock_sites/1", "plan_sha256", "slices", "snap_um",
   "sites": [{"name": "<inst>:<island>", "role", "inst", "island", "type", "kind": "partition"|"core",
              "xy_um": [x, y] (die frame, island centre / repeater site), "rect_um": die-frame rect | null,
              "ft_ports": [names]}]}
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

SCHEMA = "ot_clock_sites/1"
SNAP_UM = 0.5


def _r(v):
    return round(float(v), 4)


def _core_pt(h, pt):
    """core-local point -> type frame through the core orient (master_plan.core_to_type on a point)."""
    import master_plan as MP
    x0, y0, _, _ = MP.core_to_type(h, (pt[0], pt[1], pt[0], pt[1]))
    return x0, y0


def sites_from_slices(P, slices):
    """[site] die frame.  slices = iterable of slice dicts (master_plan SLICE_SCHEMA)."""
    import master_plan as MP
    import infra_sites as IS
    by_type = {}
    for part, v in P.parts.items():
        by_type.setdefault(v["type"], []).append(part)
    out = []

    def add(kind, tn, inst, isl_name, role, xy, rect, ft):
        out.append(dict(name=f"{inst}:{isl_name}", role=role, inst=inst, island=isl_name, type=tn, kind=kind,
                        xy_um=[_r(xy[0]), _r(xy[1])], rect_um=[_r(v) for v in rect] if rect else None,
                        ft_ports=list(ft)))
    for sl in slices:
        pd = sl.get("pushdown") or {}
        if sl.get("kind") == "partition":
            tn = sl["type"]
            for part in sorted(by_type.get(tn, [])):
                for isl in pd.get("islands", []):
                    add("partition", tn, part, isl["name"], isl.get("role"), P.to_die(part, isl["centre_um"]),
                        IS.rect_pts(P, part, isl["rect_um"]), [f["name"] for f in isl.get("ft_ports", [])])
                for rp in pd.get("clock_repeaters", []):
                    add("partition", tn, part, rp["name"], "clock_rep", P.to_die(part, rp["xy_um"]),
                        IS.rect_pts(P, part, rp["rect_um"]) if rp.get("rect_um") else None,
                        [f["name"] for f in rp.get("ft_ports", [])])
        elif sl.get("kind") == "core":
            mod = sl.get("module") or sl["type"]
            for tn, parts in sorted(by_type.items()):
                hs = [h for h in P.types[tn].get("hard_cores", []) if h["module"] == mod]
                for part in sorted(parts):
                    for h in hs:
                        inst = f"{part}/{h['inst']}"
                        for isl in pd.get("islands", []):
                            add("core", mod, inst, isl["name"], isl.get("role"),
                                P.to_die(part, _core_pt(h, isl["centre_um"])),
                                IS.rect_pts(P, part, MP.core_to_type(h, isl["rect_um"])),
                                [f["name"] for f in isl.get("ft_ports", [])])
    return out


def collisions(sites, tol=1e-3):
    """sites closer than tol (two islands claiming one point): a plan error for the master plan."""
    seen, bad = {}, []
    for s in sites:
        k = (round(s["xy_um"][0] / tol), round(s["xy_um"][1] / tol))
        if k in seen:
            bad.append([seen[k], s["name"]])
        else:
            seen[k] = s["name"]
    return bad


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("plan")
    ap.add_argument("slices", help="master-plan slices directory (slices/*.json)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--snap-um", type=float, default=SNAP_UM)
    a = ap.parse_args(argv)
    import schema as S
    P = S.Plan(S.load(a.plan))
    sha = hashlib.sha256(Path(a.plan).read_bytes()).hexdigest()
    slices = []
    for f in sorted(Path(a.slices).glob("*.json")):
        sl = json.loads(f.read_text())
        if sl.get("plan_sha256") and sl["plan_sha256"] != sha:
            raise SystemExit(f"clock_plan_sites: slice {f.name} was cut from plan {sl['plan_sha256'][:12]}, "
                             f"not {sha[:12]}")
        slices.append(sl)
    sites = sites_from_slices(P, slices)
    if not sites:
        raise SystemExit("clock_plan_sites: the slices declare no pushdown islands / clock repeaters")
    dup = collisions(sites)
    if dup:
        raise SystemExit(f"clock_plan_sites: {len(dup)} coincident plan sites (plan error), e.g. {dup[:3]}")
    roles = {}
    for s in sites:
        roles[s["role"]] = roles.get(s["role"], 0) + 1
    Path(a.out).write_text(json.dumps(dict(schema=SCHEMA, plan=str(a.plan), plan_sha256=sha, slices=str(a.slices),
                                           snap_um=a.snap_um, roles=roles, sites=sites)) + "\n")
    print(json.dumps(dict(sites=len(sites), roles=roles, out=a.out)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
