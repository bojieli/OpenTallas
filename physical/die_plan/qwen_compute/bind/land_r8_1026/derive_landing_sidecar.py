#!/usr/bin/env python3
"""Carry the clock-landing sidecar onto CB16 phase-class types.

compose_cb16_phase.py splits CB types into phase classes (internal station pads only; same outline, pins and
landing contract as the family type). clock_landings.Landings keys collector["types"] by plan type, so every new
class type needs its familys collector entry and every member partitions collector["parts"][pn]["type"] must
name the class type. Entries are copied exactly from the family (base_type kept); Landings still re-checks
per-type mask uniformity at bind time. Refuses unknown families and partitions whose plan type disagrees.
Also R8 support classes (apply_r8_support_classes.py, same type/family/parts schema).
usage: derive_landing_sidecar.py LANDING_TABLE PHASE_PLAN OUT CLASS_MANIFEST...
"""
import copy, json, sys
from pathlib import Path
table, plan, out = map(Path, sys.argv[1:4]); manifests = [Path(x) for x in sys.argv[4:]]
if out.exists(): raise SystemExit(f"refuse existing {out}")
t = json.loads(table.read_text()); col = t.get("landing_table", t)["collector"]
classes = [c for x in manifests for c in json.loads(x.read_text())["classes"]]; raw = json.loads(plan.read_text())
ptype = {p["name"]: p["type"] for p in raw["partitions"]}
added = []
for c in classes:
    tn, fam = c["type"], c["family"]
    if fam not in col["types"]: raise SystemExit(f"family {fam} of {tn} not in collector")
    if tn not in col["types"]:
        col["types"][tn] = copy.deepcopy(col["types"][fam]); added.append(tn)
    for pn in c["parts"]:
        if ptype[pn] != tn: raise SystemExit(f"{pn}: plan type {ptype[pn]} != class {tn}")
        col["parts"][pn]["type"] = tn
miss = sorted({v for v in ptype.values()} - set(col["types"]))
if miss: raise SystemExit(f"plan types missing from collector: {miss}")
bad = [pn for pn, v in col["parts"].items() if v["type"] != ptype[pn]]
if bad: raise SystemExit(f"collector part types disagree with plan: {bad[:5]}")
t["derived_from"] = dict(table=str(table), class_manifests=[str(x) for x in manifests], added_types=added)
out.write_text(json.dumps(t, indent=1) + "\n"); print(json.dumps(dict(added=len(added), types=len(col["types"]))))
