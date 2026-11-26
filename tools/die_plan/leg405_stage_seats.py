#!/usr/bin/env python3
"""leg405_stage_seats.py (C-LEG405-R2, 11-26): opt-in plan generator step, every relay_depth row staged so no hop exceeds 405 um.

  leg405_stage_seats.py run PLAN OUT [--types RE] [--limit 405] [--report REP.json]

relay_depth.py rows are D = stations_needed - stages_existing, but later plan events (grow, core_place, chain_resite, hand rows) leave
rows whose path_um needs more stations than stages_existing + D (S81 col_h10_r0_p4 u_rg1: 898.5 um, D=1, best single seat 449 um).
For every such row this raises D to ceil(path_um / limit) - 1 - stages_existing (never lowers a D), so each station + 1 hop is <= limit
by construction; the seats come from the existing relay_mid / chain_resite path.  Every raise is +1..n cycles on that path: the
report lists them under 'latency' (type, inst, port, old D, new D, extra cycles) for the producer / consumer / LATCHECK carry.
Rows whose note says 'align' belong to an aligned source group (one depth for payload + control): listed under 'align_review',
raised like the others, and the report refuses nothing silently.  Default off: nothing runs unless this tool is called
(leaf_generate.py --leg405-stages)."""
import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import adv_fpconv as AF  # noqa: E402


def restage(raw, types_re=None, limit=AF.LEG_UM):
    lat, align = [], []
    rx = re.compile(types_re) if types_re else None
    for tn, t in sorted((raw.get("partition_types") or {}).items()):
        if not isinstance(t, dict) or (rx and not rx.search(tn)):
            continue
        for r in t.get("relay_depth") or []:
            if not isinstance(r, dict):
                continue
            short = AF.staged_short(r, limit)
            if not short:
                continue
            old = int(r.get("D") or 0)
            r["D"] = old + short
            tag = f"C-LEG405-R2 +{short} stage(s): {r['path_um']} um > {int(limit)} um x ({int(r.get('stages_existing') or 0)}+{old}+1)"
            r["note"] = (r["note"] + "; " if r.get("note") else "") + tag
            row = dict(type=tn, inst=r.get("inst"), port=r.get("port"), side=r.get("side"), path_um=r["path_um"], old_D=old, new_D=r["D"], extra_cycles=short)
            lat.append(row)
            if "align" in (r.get("note") or "").lower():
                align.append(row)
    return {"latency": lat, "align_review": align, "types": len({x["type"] for x in lat}), "extra_cycles_total": sum(x["extra_cycles"] for x in lat)}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("cmd", choices=["run"])
    ap.add_argument("plan")
    ap.add_argument("out")
    ap.add_argument("--types")
    ap.add_argument("--limit", type=float, default=AF.LEG_UM)
    ap.add_argument("--report")
    a = ap.parse_args(argv)
    raw = json.loads(Path(a.plan).read_text())
    rep = restage(raw, a.types, a.limit)
    Path(a.out).write_text(json.dumps(raw, indent=1, sort_keys=False))
    if a.report:
        Path(a.report).write_text(json.dumps(rep, indent=1))
    print(f"leg405_stage_seats: {len(rep['latency'])} rows raised in {rep['types']} types, +{rep['extra_cycles_total']} row-cycles, "
          f"{len(rep['align_review'])} aligned-group rows -> {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
