#!/usr/bin/env python3
"""FALLBACK-HEAD-2: per-type reserved site rectangles for the s81_head landed fallback kits.

    python3 tools/s81_head/fallback_reserve.py LANDED_PLAN.json TREE.json SIDECAR.json --out PLAN_OUT.json [--report R.json]

* die_clock_tree: every die clock-tree cell site of the site-legal die tree (die_trial.py --tree-site-slide tree.json
  `sites`, die frame, cell lower-left as placed by place_inst) with its footprint (BUFx24 1.62 x 0.27 um) plus a
  one-site / one-row halo, clipped to every partition the halo touches and mapped into that type's frame with
  Plan.to_type. The UNION over all instances of a type is reserved in the type (one kit per type; an island unused
  by a given replica is still kept free) -- the apply_clkmesh_sites.py rule for die_islands_um.
* landing_ring_bank: the landing ring storage banks of compose --monitor dataflow (landing_contract.bands, type
  frame), cross-checked against the sidecar collector bands.
Writes partition_types[t].clock.reserved_sites_um; fails closed on a tree site over a hard core or a sidecar/plan
bank mismatch. A tree site inside a ring bank is reported per bank (the ring is packed around the hard hole). Geometry only: no cell, pin, cycle or timing change.
"""
import argparse
import hashlib
import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "die_plan"))
import schema as S  # noqa: E402
import die_trial as DT  # noqa: E402

CELL_W, CELL_H = 1.62, 0.27          # BUFx24_ASAP7_75t_R (die_trial.BUF), ASAP7 row height
HALO_X, HALO_Y = 0.54, 0.27          # one site / one row each side (apply_clkmesh_sites.py)


def _ov(a, b):
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


def _merge(rects):
    """merge rects that share a row band and touch/overlap in x (exact union, no area added beyond the hull of a row run)."""
    out = []
    for r in sorted(rects, key=lambda r: (r[1], r[3], r[0])):
        if out and out[-1][1] == r[1] and out[-1][3] == r[3] and r[0] <= out[-1][2]:
            m = out[-1]
            out[-1] = (m[0], m[1], max(m[2], r[2]), m[3])
        else:
            out.append(r)
    return out


def reserve(raw, tree, side, cell_w=CELL_W):
    P = S.Plan(raw)
    rects = {n: P.rect(n) for n in P.parts}
    B = 500.0
    grid = defaultdict(list)
    for n, r in rects.items():
        for i in range(int(r[0] // B), int(r[2] // B) + 1):
            for j in range(int(r[1] // B), int(r[3] // B) + 1):
                grid[(i, j)].append(n)
    hard = defaultdict(set)
    outside, spanning = [], 0
    for name, (x, y) in sorted(tree["sites"].items()):
        halo = (x - HALO_X, y - HALO_Y, x + cell_w + HALO_X, y + CELL_H + HALO_Y)
        cand = {n for i in range(int(halo[0] // B), int(halo[2] // B) + 1)
                for j in range(int(halo[1] // B), int(halo[3] // B) + 1) for n in grid[(i, j)]}
        body = [n for n in cand if _ov((x, y, x + cell_w, y + CELL_H), rects[n])]
        if not body:
            outside.append(name)
            continue
        spanning += len(body) > 1
        for n in sorted(cand):
            pr = rects[n]
            c = (max(halo[0], pr[0]), max(halo[1], pr[1]), min(halo[2], pr[2]), min(halo[3], pr[3]))
            if c[0] >= c[2] or c[1] >= c[3]:
                continue
            pts = [P.to_type(n, (a, b)) for a in (c[0], c[2]) for b in (c[1], c[3])]
            hard[P.parts[n]["type"]].add((round(min(p[0] for p in pts), 3), round(min(p[1] for p in pts), 3),
                                          round(max(p[0] for p in pts), 3), round(max(p[1] for p in pts), 3)))
    if outside:
        raise ValueError(f"{len(outside)} die tree cells are not inside any partition, e.g. {outside[:5]}")
    coll = (side or {}).get("collector", {}).get("types", {})
    report, bad, in_bank = {}, [], defaultdict(list)
    for tn, t in raw["partition_types"].items():
        lc = t.get("clock", {}).get("landing_contract", {})
        banks = {b: tuple(v["rect_um"]) for b, v in sorted(lc.get("bands", {}).items()) if v.get("rect_um")}
        sb = {b: tuple(v["rect_um"]) for b, v in coll.get(tn, {}).get("bands", {}).items() if v.get("rect_um")}
        if coll and sb != banks:
            raise ValueError(f"{tn}: plan landing bands differ from the sidecar collector bands")
        hs = _merge(hard.get(tn, ()))
        cores = [c[:4] for c in DT.core_obs(t)]
        for r in hs:
            for c in cores:
                if _ov(r, c):
                    bad.append(dict(type=tn, kind="core", rect=list(r), core=list(c)))
            for b, q in banks.items():
                # A tree site in a ring bank (both use the same macro-free channel) stays a hard hole: the
                # landing placement packs the ring around it (cland_avoid_rects). Reported, never silently merged.
                if _ov(r, q):
                    in_bank[(tn, b)].append(r)
        rows = [dict(rect_um=list(r), kind="die_clock_tree") for r in hs]
        rows += [dict(rect_um=list(q), kind="landing_ring_bank", ref="u_cland_" + b) for b, q in banks.items()]
        w, h = t["outline_um"]
        if rows:
            t.setdefault("clock", {})["reserved_sites_um"] = rows
        else:
            t.get("clock", {}).pop("reserved_sites_um", None)
        tib = {b: dict(rects=len(v), area_um2=round(sum((r[2] - r[0]) * (r[3] - r[1]) for r in v), 3),
                       bank_frac=round(sum((r[2] - r[0]) * (r[3] - r[1]) for r in v)
                                       / ((banks[b][2] - banks[b][0]) * (banks[b][3] - banks[b][1])), 6))
               for (tt, b), v in in_bank.items() if tt == tn}
        report[tn] = dict(tree_sites_in_ring_bank=tib, instances=sum(1 for p in P.parts.values() if p["type"] == tn), tree_rects=len(hs),
                          tree_area_um2=round(sum((r[2] - r[0]) * (r[3] - r[1]) for r in hs), 3),
                          bank_rects=len(banks), bank_area_um2=round(sum((q[2] - q[0]) * (q[3] - q[1]) for q in banks.values()), 3),
                          outline_frac=round((sum((r[2] - r[0]) * (r[3] - r[1]) for r in hs)
                                              + sum((q[2] - q[0]) * (q[3] - q[1]) for q in banks.values())) / (w * h), 6))
    if bad:
        raise ValueError(f"{len(bad)} reservation conflicts, e.g. {bad[:4]}")
    return raw, dict(schema="opentallas.fallback_head.reserved_sites.v1", tree_cells=len(tree["sites"]),
                     boundary_spanning_cells=spanning, cell_w_um=cell_w, halo_um=[HALO_X, HALO_Y],
                     conflicts=0, types=report, physical_qualified=False)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("plan")
    ap.add_argument("tree")
    ap.add_argument("sidecar")
    ap.add_argument("--out", required=True)
    ap.add_argument("--report")
    a = ap.parse_args()
    raw = json.loads(Path(a.plan).read_text())
    raw, rep = reserve(raw, json.loads(Path(a.tree).read_text()), json.loads(Path(a.sidecar).read_text()))
    rep.update(plan_sha256=hashlib.sha256(Path(a.plan).read_bytes()).hexdigest(),
               tree_sha256=hashlib.sha256(Path(a.tree).read_bytes()).hexdigest(),
               sidecar_sha256=hashlib.sha256(Path(a.sidecar).read_bytes()).hexdigest())
    Path(a.out).write_text(json.dumps(raw, indent=1) + "\n")
    if a.report:
        Path(a.report).write_text(json.dumps(rep, indent=1) + "\n")
    print(json.dumps({k: rep[k] for k in ("tree_cells", "boundary_spanning_cells", "conflicts")}
                     | {"types": {k: (v["tree_rects"], v["bank_rects"], v["outline_frac"]) for k, v in rep["types"].items()}}))


if __name__ == "__main__":
    main()
