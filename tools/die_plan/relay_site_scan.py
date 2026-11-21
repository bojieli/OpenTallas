#!/usr/bin/env python3
"""RESET-RELAY-GEN-R2 11-21 (S81-DIE-R4, COORD): scan the reset tree of every plan type for relays at ILLEGAL sites.

A legal relay site (reset_tree._free) is inside the type outline less CLEAR_UM, outside every hard core / macro leaf /
keepout grown by CLEAR_UM, and has a free row-high (0.27 um) and cell-wide (1.08 um) run.  S81 col_h9_r0_p3 cl0cd90c0e
(J5): rst_rl_137 at (219.6, 1093.0) sat in the 8.7 um channel between u_ha and u_hb (0.06 um left after the halos), so
OT_CLAND found no row in global placement.

  python3 -I relay_site_scan.py PLAN [--types T1,T2] [--reach 300] [--out REPORT.json]

Per type: the relays of reset_tree.for_type (the tree the bind would emit from this plan) that are not legal, each with its
nearest legal site (push_off) and the hop lengths to its parent / children before and after the move.  Read-only; never a gate.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import reset_tree as RT  # noqa: E402


def man(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def scan_tree(T, boxes, box_out, reach=300.0):
    """-> [dict] one row per relay of tree T not at a legal site"""
    xy = {r["q"]: tuple(r["xy"]) for r in T["relays"]}
    if T.get("root"):
        xy["rst_root_n"] = tuple(T["root"])
    kids = {}
    for r in T["relays"]:
        kids.setdefault(r["d"], []).append(r["q"])
    out = []
    for r in T["relays"]:
        p = tuple(r["xy"])
        if RT._free(p, boxes, box_out):
            continue
        q = RT.push_off(p, boxes, box_out)
        nb = ([xy[r["d"]]] if r["d"] in xy else []) + [xy[k] for k in kids.get(r["q"], []) if k in xy]
        was = max([man(p, n) for n in nb], default=0.0)
        now = max([man(q, n) for n in nb], default=0.0)
        out.append(dict(relay=r["name"], q=r["q"], xy=[round(p[0], 3), round(p[1], 3)], legal_xy=[round(q[0], 3), round(q[1], 3)],
                        moved_um=round(man(p, q), 1), hop_was_um=round(was, 1), hop_now_um=round(now, 1),
                        over_reach_after=now > reach + 1e-6, tap=r.get("tap")))
    return out


def scan_plan(P, types=None, reach=300.0):
    rep, C = {}, RT.CLEAR_UM
    for tn, t in P.types.items():
        if types and tn not in types:
            continue
        try:
            T = RT.for_type(P, tn)
        except Exception as e:                     # a type with no reset tree (hard, no contract): listed, not an error
            rep[tn] = dict(error=f"{type(e).__name__}: {e}"[:200])
            continue
        w, h = t["outline_um"]
        rows = scan_tree(T, RT.blockages(t), (C, C, w - C, h - C), reach)
        rep[tn] = dict(relays=len(T["relays"]), illegal=rows)
    return rep


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("plan")
    ap.add_argument("--types")
    ap.add_argument("--reach", type=float, default=300.0)
    ap.add_argument("--out")
    a = ap.parse_args(argv)
    import schema as S
    P = S.Plan(json.load(open(a.plan)), a.plan)
    rep = scan_plan(P, set(a.types.split(",")) if a.types else None, a.reach)
    bad = {k: v for k, v in rep.items() if v.get("illegal")}
    if a.out:
        Path(a.out).write_text(json.dumps(rep, indent=1) + "\n")
    for k, v in sorted(bad.items()):
        for r in v["illegal"]:
            print(f"{k}: relay {r['relay']} at {r['xy']} illegal -> {r['legal_xy']} (moved {r['moved_um']} um, hop {r['hop_was_um']} -> {r['hop_now_um']})")
    n = sum(len(v["illegal"]) for v in bad.values())
    err = sum(1 for v in rep.values() if v.get("error"))
    print(f"{len(rep)} types scanned ({err} without a tree), {len(bad)} with illegal relay sites, {n} relays")
    return 0


if __name__ == "__main__":
    sys.exit(main())
