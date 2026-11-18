#!/usr/bin/env python3
"""LOCAL-RESET-RAW-1 write-back (S81-SERDES-GEN 11-17): put the raw relay names a bind re-picked into the plan, so G0 and the next bind see them.

usage: local_reset_writeback.py PLAN.json bind_local_reset_rederived.json OUT.json

The receipt is {type_key: [{name, was, raw}]} (bind writes it next to bind_report.json when clock_landings re-picked a name).  For each
row of partition_types[type_key].clock.landing_local_resets named `name` whose raw is `was`, raw becomes the re-picked name.  A row that
does not match (renamed / already updated) is left alone; the report line says how many were applied.  Nothing else in the plan changes.
"""
import json
import sys
from pathlib import Path


def apply(plan, receipt):
    n = 0
    for key, rows in receipt.items():
        cfg = ((plan.get("partition_types") or {}).get(key) or {}).get("clock", {}).get("landing_local_resets") or []
        for r in rows:
            for row in cfg:
                if row.get("name") == r["name"] and row.get("raw") == r["was"]:
                    row["raw"] = r["raw"]
                    n += 1
    return n


def main(argv):
    plan = json.loads(Path(argv[1]).read_text())
    n = apply(plan, json.loads(Path(argv[2]).read_text()))
    Path(argv[3]).write_text(json.dumps(plan, separators=(",", ":")))
    print(f"LOCAL_RESET_WRITEBACK {n} raw name(s) rewritten -> {argv[3]}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
