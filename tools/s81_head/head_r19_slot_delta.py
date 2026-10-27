#!/usr/bin/env python3
"""HEAD-CORE-R19: explicit per-type declared-slot PLAN-DELTA (proposal only; never applied to the main plan) for a
head_mesh_r3 tree.  Every tree node / mesh driver (and, reported separately, every leg repeater) is mapped to its
partition-type frame; a site whose type has no declared 8.64-um island CENTRED on it (|d| <= tol per axis) becomes a
new slot, centre = the site (sites are already snap_inside by construction: edge nodes 4.32 um inside the outline),
UNION over the type's instances (12.2a1: identical per type).  Refused if a new slot overlaps a hard core of its type.
Optionally writes a trial plan (OUT_PLAN) with the slots appended to clock.die_islands_um, for gate evidence only.
  head_r19_slot_delta.py PLAN TREE_DIR OUT_JSON [--trial-plan OUT_PLAN] [--with-reps]"""
import argparse, hashlib, json, sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import head_mesh_r3 as H  # noqa: E402
import head_infra_delta_r4 as D  # noqa: E402

SIDE = D.SIDE


def local(p, xy):
    """inverse of head_mesh_r3.tf for the partition p (die -> type frame)."""
    dx, dy = xy[0] - p["x0"], xy[1] - p["y0"]
    w, h = p["w"], p["h"]
    return {"R0": (dx, dy), "MY": (w - dx, dy), "MX": (dx, h - dy), "R180": (w - dx, h - dy)}[p["o"]]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("plan"); ap.add_argument("tree"); ap.add_argument("out")
    ap.add_argument("--trial-plan"); ap.add_argument("--with-reps", action="store_true")
    ap.add_argument("--tol", type=float, default=1e-3)
    a = ap.parse_args()
    PL = H.Plan(a.plan)
    N = json.loads((Path(a.tree) / "tree_nodes.json").read_text())
    sites = H.sites_of(N)
    need = defaultdict(dict)            # type -> {(x, y): roles}
    stats = defaultdict(lambda: defaultdict(int))
    for kind, tag, xy in sites:
        if kind == "rep" and not a.with_reps:
            continue
        p = PL.part_at(xy)
        if p is None:
            raise SystemExit(f"site {tag} {xy} outside every partition")
        lx, ly = (round(v, 3) for v in local(p, xy))
        sx, sy = D.snap_inside(lx, ly, p["w"], p["h"])
        if (sx, sy) != (lx, ly):
            raise SystemExit(f"site {tag} {xy} not snap_inside ({lx},{ly}) -> ({sx},{sy})")
        isl = PL.T[p["type"]].get("clock", {}).get("die_islands_um", []) or []
        on = any(abs((r[0] + r[2]) / 2 - lx) <= a.tol and abs((r[1] + r[3]) / 2 - ly) <= a.tol for r in isl)
        stats[p["type"]][(kind, "centred" if on else "new")] += 1
        if not on:
            need[p["type"]].setdefault((lx, ly), set()).add(kind if kind != "node" else "tree_node")
    out, bad = dict(plan_in=hashlib.sha256(Path(a.plan).read_bytes()).hexdigest()[:8], tree=a.tree,
                    with_reps=a.with_reps, types={}), []
    for tn in sorted(need):
        t = PL.T[tn]
        cores = [(c["origin_um"][0], c["origin_um"][1], c["origin_um"][0] + c["outline_um"][0],
                  c["origin_um"][1] + c["outline_um"][1]) for c in t.get("hard_cores", []) or []]
        slots = []
        for (x, y), roles in sorted(need[tn].items()):
            r = [round(x - SIDE / 2, 3), round(y - SIDE / 2, 3), round(x + SIDE / 2, 3), round(y + SIDE / 2, 3)]
            for k in cores:
                if r[0] < k[2] and k[0] < r[2] and r[1] < k[3] and k[1] < r[3]:
                    bad.append((tn, r, k))
            slots.append(dict(centre_um=[x, y], rect_um=r, roles=sorted(roles)))
        out["types"][tn] = dict(new_slots=len(slots), slots=slots,
                                census={f"{k}:{v}": n for (k, v), n in sorted(stats[tn].items())})
    for tn in sorted(set(stats) - set(need)):
        out["types"][tn] = dict(new_slots=0, census={f"{k}:{v}": n for (k, v), n in sorted(stats[tn].items())})
    if bad:
        out["error"] = dict(slot_overlaps_hard_core=bad[:10])
    Path(a.out).write_text(json.dumps(out, indent=1) + "\n")
    if a.trial_plan and not bad:
        P = json.loads(Path(a.plan).read_text())
        for tn, v in out["types"].items():
            for s in v.get("slots", []):
                P["partition_types"][tn].setdefault("clock", {}).setdefault("die_islands_um", []).append(s["rect_um"])
        Path(a.trial_plan).write_text(json.dumps(P, indent=2) + "\n")
        out["trial_plan_sha8"] = hashlib.sha256(Path(a.trial_plan).read_bytes()).hexdigest()[:8]
        Path(a.out).write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps({tn: dict(new=v["new_slots"], centres=[s["centre_um"] for s in v.get("slots", [])][:12],
                               census=v["census"]) for tn, v in out["types"].items()}, indent=1))
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
