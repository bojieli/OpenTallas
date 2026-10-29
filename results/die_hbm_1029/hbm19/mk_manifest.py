#!/usr/bin/env python3
"""DIE-HBM-19: bind manifest variant = HBM-BIND-6 c3 manifest + map remap of single-source families onto the kept plan
copy (drop_dup_report.json). usage: mk_manifest.py C3_DIR DROP_REPORT OUT_VARIANT_DIR"""
import json, sys, os, shutil
c3, rep, out = sys.argv[1:4]
m = json.load(open(os.path.join(c3, "map.json"))); R = json.load(open(rep))
part = {"q_hub_ne": "NE_hub", "q_hub_nw": "NW_hub"}
n = []
for tn, fs in R["hubs"].items():
    for fam, st in fs.items():
        if "kept" not in st: continue
        for k, v in m["parts"].items():
            if isinstance(v, list) and v[0] == part[tn] and v[1] == st["dropped"]:
                m["parts"][k] = [v[0], st["kept"]]; n.append((k, st["dropped"], st["kept"]))
m["note"] = "DIE-HBM-19: c3 map + single-source family remap to the kept copy (%d) | " % len(n) + m["note"]
os.makedirs(os.path.join(out, "out"), exist_ok=True)
json.dump(m, open(os.path.join(out, "map.json"), "w"), indent=1)
d = json.load(open(os.path.join(c3, "asbuilt.json"))); d["map_file"] = os.path.abspath(os.path.join(out, "map.json"))
d["note"] = "DIE-HBM-19 variant: map remap %s | " % n + d["note"]
json.dump(d, open(os.path.join(out, "asbuilt.json"), "w"), indent=1)
for f in ("asbuilt.json", "asbuilt_sources.json"):
    dst = os.path.join(out, "out", f)
    if not os.path.exists(dst): os.link(os.path.join(c3, "out", f), dst)
print("remapped", n)
