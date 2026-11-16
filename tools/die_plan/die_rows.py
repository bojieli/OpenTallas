#!/usr/bin/env python3
"""FABLE-DIE-KV 11-16: die-level delta rows for one whole-die plan event (die-agnostic).

Row file = {"lane": NAME, "rows": {TYPE: {"dotted.key": value}}, "top": {"dotted.key": value}} (the format
clksite_reserve.py writes; "top" is optional and addresses the plan root).  A value {"$delete": true} removes the key.

  die_rows.py apply   PLAN ROWS [ROWS ...] -o OUT.json      apply row files in order; prints the changed types
  die_rows.py windows PLAN KITWIN.json -o ROWS.json [--skip-types T,T] [--cap PS] [--seam PS]
        die_sta_related --kit-window-out table -> one "top" row clock.tap_window.per_port_ps (measured per-port
        related-pair damage of the die clock tree of record, gen_phys.tap_window_ports).  A port above --cap
        (default period / 4, the gen_phys limit) is clamped and listed as "over_cap": that port needs a tree fix,
        not a wider window.  --skip-types keeps the flat window of those types (signed views stay valid).
        --seam PS also sets clock.seam_hold.seam_ps.
"""
import argparse
import copy
import json
import sys


def _set(root, dotted, value):
    keys = dotted.split(".")
    d = root
    for k in keys[:-1]:
        d = d.setdefault(k, {})
    if isinstance(value, dict) and value.get("$delete") is True:
        return d.pop(keys[-1], None) is not None
    old = d.get(keys[-1])
    d[keys[-1]] = copy.deepcopy(value)
    return old != value


def apply_rows(plan, rowfile):
    """-> sorted list of changed type names ("@top" for a root row); unknown types are an error."""
    changed = set()
    types = plan["partition_types"]
    for tn, row in (rowfile.get("rows") or {}).items():
        if tn not in types:
            raise ValueError(f"row for unknown type {tn}")
        for key, value in row.items():
            if _set(types[tn], key, value):
                changed.add(tn)
    for key, value in (rowfile.get("top") or {}).items():
        if key.split(".")[0] in ("partition_types", "partitions"):
            raise ValueError(f"top row {key}: types and partitions are not root rows")
        if _set(plan, key, value):
            changed.add("@top")
    return sorted(changed)


def window_rows(plan, kitwin, skip=(), cap=None, seam=None, lane="die"):
    cap = float(plan["die"]["period_ps"]) / 4.0 if cap is None else float(cap)
    old = ((plan.get("clock") or {}).get("tap_window") or {}).get("per_port_ps") or {}
    table, over = {t: v for t, v in old.items() if t in skip}, []
    for tn, ports in sorted((kitwin.get("per_port_ps") or {}).items()):
        if tn in skip or tn not in plan["partition_types"]:
            continue
        row = {}
        for port, need in sorted(ports.items()):
            if need > cap:
                over.append([tn, port, need])
            row[port] = round(min(float(need), cap), 3)
        table[tn] = row
    top = {"clock.tap_window.per_port_ps": table}
    if seam is not None:
        top["clock.seam_hold.seam_ps"] = float(seam)
    return {"lane": lane, "top": top, "over_cap": over, "cap_ps": cap, "skipped": sorted(skip),
            "source_plan_sha256": kitwin.get("plan_sha256")}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("apply"); a.add_argument("plan"); a.add_argument("rows", nargs="+"); a.add_argument("-o", required=True)
    w = sub.add_parser("windows"); w.add_argument("plan"); w.add_argument("kitwin"); w.add_argument("-o", required=True)
    w.add_argument("--skip-types", default=""); w.add_argument("--cap", type=float); w.add_argument("--seam", type=float)
    w.add_argument("--lane", default="die")
    args = ap.parse_args(argv)
    plan = json.load(open(args.plan))
    if args.cmd == "apply":
        report = {}
        for f in args.rows:
            report[f] = apply_rows(plan, json.load(open(f)))
        json.dump(plan, open(args.o, "w"), indent=1)
        print(json.dumps({f: {"changed": len(v), "types": v} for f, v in report.items()}))
        return 0
    rows = window_rows(plan, json.load(open(args.kitwin)), tuple(t for t in args.skip_types.split(",") if t),
                       args.cap, args.seam, args.lane)
    json.dump(rows, open(args.o, "w"), indent=1)
    print(json.dumps({"types": len(rows["top"]["clock.tap_window.per_port_ps"]), "over_cap": len(rows["over_cap"]),
                      "cap_ps": rows["cap_ps"]}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
