#!/usr/bin/env python3
"""demacro_row.py -- SITE-IN-MACRO 11-25 (COORD ruling): a plan row (plan_ops.v1 style ops) that moves explicit internal-station bank
sites (bit_sites_um / face_bit_sites_um) out of every hard core + halo, with the same legaliser core_place.write_type uses
(core_place.resite_station_banks: CORE_AREA, site grid, off every core + halo, off other sites; nothing else moves).

    demacro_row.py PLAN.json --out ROW.json [--types RE] [--lane LANE] [--row NAME]

Only types where ADV-SITE-IN-MACRO finds internal_stations bank sites in a core/halo are touched.  The row is checked against a copy
of the plan with the ops applied: residual in-macro bank sites per type are printed (0 expected) and written to the row ("check").
ROW = {row, lane, base_sha12, why, ops:[{op: replace, path, old, value}], check}.  Report-only tool: it never edits PLAN."""
import argparse
import copy
import hashlib
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import adv_site_in_macro as AS  # noqa: E402

BANK_KEYS = ("internal_stations.bit_sites_um", "internal_stations.face_bit_sites_um")


def bank_hits(t):
    return sum(1 for e in AS.classify(t)[1] if e[0] in BANK_KEYS)


def row_ops(raw, types=None):
    """-> (ops, per-type report) for the types of `raw` with internal-station bank sites in a core"""
    import core_place as CP
    ops, rep = [], {}
    for tn, t in sorted((raw.get("partition_types") or {}).items()):
        if types and not re.search(types, tn):
            continue
        if not isinstance(t, dict) or not t.get("outline_um") or not bank_hits(t):
            continue
        t_new, r = copy.deepcopy(t), {}
        CP.resite_station_banks(t, t_new, r)
        n_ops = 0
        for i, (a, b) in enumerate(zip(t["internal_stations"], t_new["internal_stations"])):
            for k in ("bit_sites_um", "face_bit_sites_um"):
                if a.get(k) is not None and a.get(k) != b.get(k):
                    ops.append(dict(op="replace", path=f"/partition_types/{tn}/internal_stations/{i}/{k}", old=a[k], value=b[k]))
                    n_ops += 1
        rep[tn] = dict(before=bank_hits(t), after=bank_hits(t_new), ops=n_ops, sites_moved=r.get("bank_sites_moved", 0),
                       failed=r.get("bank_failed"))
    return ops, rep


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("plan")
    ap.add_argument("--out", required=True)
    ap.add_argument("--types")
    ap.add_argument("--lane", default="SITE-IN-MACRO")
    ap.add_argument("--row", default="DEMACRO")
    a = ap.parse_args(argv)
    data = Path(a.plan).read_bytes()
    raw = json.loads(data)
    ops, rep = row_ops(raw, a.types)
    row = dict(row=a.row, lane=a.lane, base_sha12=hashlib.sha256(data).hexdigest()[:12],
               why="internal_stations bank sites inside a hard core + halo moved to the nearest legal site (positions only, 0 cycles)",
               ops=ops, check=rep)
    Path(a.out).write_text(json.dumps(row, indent=1))
    print(f"{a.row}: {len(rep)} type(s), {len(ops)} op(s), bank sites in macro {sum(r['before'] for r in rep.values())} -> "
          f"{sum(r['after'] for r in rep.values())}" + "".join(f"\n  {t}: {r['before']} -> {r['after']} ({r['ops']} ops, failed {r['failed']})"
                                                                for t, r in list(rep.items())[:12]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
