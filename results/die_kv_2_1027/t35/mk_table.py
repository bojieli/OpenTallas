"""DIE-KV-2: landed crossing table for a partition->region map (same schema/relabel as LAND-KV-2 regroup_map_lk2.py)."""
import json, sys, collections
oldt, regmap, out = sys.argv[1:4]
T = json.load(open(oldt)); reg = json.load(open(regmap))["part_region"]
NT = {k: v for k, v in T.items() if k not in ("regions", "ports")}
NT["regions"] = [dict(r, tag=reg[r["parts"][0]]) for r in T["regions"]]
assert all(len({reg[p] for p in r["parts"]}) == 1 for r in T["regions"])
xp = [dict(q, src_region=reg[q["src"]], dst_region=reg[q["dst"]]) for q in T["ports"] if reg[q["src"]] != reg[q["dst"]]]
NT["ports"] = xp; NT["regions_count"] = len(set(reg.values())); NT["crossings"] = len(xp); NT["bits"] = sum(q["width"] for q in xp)
NT["note_dkv2"] = dict(source=oldt, map=regmap)
json.dump(NT, open(out, "w"))
print(json.dumps(dict(regions=NT["regions_count"], crossings=len(xp), bits=NT["bits"])))
