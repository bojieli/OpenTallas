#!/usr/bin/env python3
"""PATH-S81-PD6 10-27: merge partition types that are byte-identical apart from their key (G0 near-duplicates).
usage: merge_identical_types_1026.py PLAN_IN PLAN_OUT NEW_NAME TYPE1 TYPE2 [...]
Refuses unless every listed type dict is deep-equal to the first.  The listed partitions get NEW_NAME; the old keys
are removed.  Nothing else in the plan references these keys (checked: only partition_types keys + partitions.type)."""
import json, sys
src, dst, new, *names = sys.argv[1:]
raw = json.load(open(src)); T = raw["partition_types"]
ref = T[names[0]]
for n in names[1:]:
    if T[n] != ref:
        raise SystemExit(f"{n} differs from {names[0]}: not merged")
if new in T and new not in names:
    raise SystemExit(f"{new} exists")
s = json.dumps({k: v for k, v in raw.items() if k not in ("partition_types", "partitions")})
for n in names:
    if f'"{n}"' in s:
        raise SystemExit(f"{n} referenced outside partition_types/partitions")
T[new] = json.loads(json.dumps(ref))
for n in names:
    if n != new: del T[n]
moved = []
for p in raw["partitions"]:
    if p["type"] in names:
        p["type"] = new; moved.append(p["name"])
T[new]["note"] = (T[new].get("note", "") + f"; PATH-S81-PD6 merged identical types {names}").strip("; ")
json.dump(raw, open(dst, "w"), indent=1)
print("RESULT merged", len(names), "->", new, "partitions", moved)
