#!/usr/bin/env python3
"""KV-PLAN3 10-25: per-type G2 table for face_budget.py from tools/die_plan/g2.py part probes (one probe dir per type,
hard cores obstructing M1..obs_max, main 26028effc).  PASS = probe done, GRT total overflow 0, no pin without an
access point, no ERROR, and every layer's GRT usage <= 60 % (COORD KV RULING 10-25 (a): <= 0.6 track use).
usage: g2_table.py G2_ROOT --out TABLE.json      (G2_ROOT/<type>/part_<type>/grt.json)
"""
import argparse
import json
from pathlib import Path

USE_MAX_PCT = 60.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    types = {}
    for g in sorted(Path(a.root).glob("*/part_*/grt.json")):
        r = json.loads(g.read_text())
        tn = r["type"]
        use = max((v["usage_pct"] for v in r.get("layers", {}).values()), default=None)
        ok = bool(r.get("done") and r.get("total_overflow") == 0 and not any(r.get("pin_access_no_ap", {}).values())
                  and not r.get("errors") and use is not None and use <= USE_MAX_PCT)
        types[tn] = {"pass": ok, "overflow": r.get("total_overflow"), "max_layer_usage_pct": use,
                     "no_ap": r.get("pin_access_no_ap"), "errors": r.get("errors"), "pins": r.get("pins"),
                     "leaf_blockages": r.get("leaf_blockages"), "wirelength_um": r.get("wirelength_um"),
                     "probe": str(g.parent)}
    out = {"schema": "opentallas.kv_g2_type_table.v1", "rule": "COORD KV RULING 2026-10-25 05:07 (a)",
           "use_max_pct": USE_MAX_PCT, "types": types,
           "summary": {"pass": sorted(t for t, v in types.items() if v["pass"]),
                       "fail": sorted(t for t, v in types.items() if not v["pass"])}}
    Path(a.out).write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps(out["summary"]))


if __name__ == "__main__":
    main()
