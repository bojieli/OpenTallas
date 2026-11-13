#!/usr/bin/env python3
"""QC-S28-B B6 rescore: route_supply p99 (core_place.rs_rows = the street-rule legalize scorer) per type on N plans.
   rescore.py OUT.json HALVING TYPES_CSV PLAN1 [PLAN2 ...]   (run from the srcS repo root)"""
import json, sys
from pathlib import Path
sys.path.insert(0, "tools/die_plan")
import core_place as CP
out, halving, types = sys.argv[1], sys.argv[2], sys.argv[3].split(",")
res = {}
for i, pl in enumerate(sys.argv[4:]):
    pl = Path(pl).resolve()
    rows = CP.rs_rows(pl, "qwen_compute", Path(".").resolve(), types, [str(Path("physical/die_plan/qwen_compute/plan_of_record").resolve())], halving, Path(out).parent / f"rs_{halving}_{i}")
    res[str(pl)] = {t: CP.rs_summary(rows.get(t)) for t in types}
json.dump(res, open(out, "w"), indent=1)
plans = list(res)
print("type\t" + "\t".join(Path(p).name for p in plans))
for t in types:
    print(t + "\t" + "\t".join(str(res[p][t].get("p99")) + ":" + str(res[p][t].get("worst", res[p][t].get("region", "")))[:30] for p in plans))
