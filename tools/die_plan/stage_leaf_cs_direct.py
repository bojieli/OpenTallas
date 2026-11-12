#!/usr/bin/env python3
"""LF-CS-DIRECT (S81-LEAF-FLOOR-2 11-12, DIE-S81-88): the leaf vn_a.c_s -> vn_b links (kit_istations class cs) have no
RTL station and need none -- every one is inside one 405 um hop (181-389 um, ready12ng).  This plan stage re-plans
them to a direct link (regs_um []) and writes the LF4 reach constraint: vn_a.c_s <-> vn_b <= REACH um in every leaf
type (the floorplan optimiser must keep it a direct reach; leaf_cs_depth then needs no cs register).

    stage_leaf_cs_direct.py PLAN.json OUT_PLAN.json --constraints OUT.json [--reach 405]

Fails closed if a cs link is already longer than the reach (it would need a register no RTL has)."""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import kit_istations as KI   # noqa: E402
import leaf_cs_depth as LCD  # noqa: E402


def manhattan(e):
    f, t = e.get("from_um"), e.get("to_um")
    return abs(f[0] - t[0]) + abs(f[1] - t[1]) if f and t else None


def stage(plan, reach):
    rows, over = [], []
    for tn, t in sorted(plan["partition_types"].items()):
        if not LCD.LEAF_TYPE.match(tn):
            continue
        for e in t.get("internal_stations") or []:
            if str(e.get("conn", "")).startswith("bus:") or KI.core_class(e)[0] != "cs":
                continue
            d = manhattan(e)
            if d is None or d > reach:
                over.append((tn, e["conn"], d))
                continue
            rows.append(dict(type=tn, conn=e["conn"], launch=e.get("launch"), capture=e.get("capture"),
                             from_um=e.get("from_um"), to_um=e.get("to_um"), manhattan_um=round(d, 2),
                             regs_before=len(e.get("regs_um") or []), limit_um=reach))
            e["regs_um"] = []
            tag = "lf_cs_direct: S81-LEAF-FLOOR-2 11-12, direct link (no RTL station), LF4 reach constraint"
            if tag not in (e.get("note") or ""):
                e["note"] = ((e.get("note") + "; ") if e.get("note") else "") + tag
    if over:
        raise SystemExit(f"cs links beyond {reach} um (need a register no RTL has): {over[:5]}")
    return rows


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("plan")
    ap.add_argument("out")
    ap.add_argument("--constraints", required=True)
    ap.add_argument("--reach", type=float, default=405.0)
    a = ap.parse_args(argv)
    plan = json.loads(Path(a.plan).read_text())
    rows = stage(plan, a.reach)
    Path(a.out).write_text(json.dumps(plan))
    Path(a.constraints).write_text(json.dumps(dict(
        schema="opentallas.lf4_reach.v1", rule="leaf vn_a.c_s <-> vn_b direct reach (cs class, no station)",
        reach_um=a.reach, links=rows), indent=1) + "\n")
    print(f"LF_CS_DIRECT: {len(rows)} cs rows -> direct (max {max((r['manhattan_um'] for r in rows), default=0)} um)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
