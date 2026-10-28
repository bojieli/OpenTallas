"""DIE-QC-4: INFO-only CA rows with the plan-FAIL crossings dropped (never a gate number). usage: info_drop.py XING CA OUT"""
import json, sys
d = json.load(open(sys.argv[1]))
bad = {x["port"] for x in json.load(open(sys.argv[2]))["crossings"] if x["depth"] not in (4, 8)}
print("INFO drop", sorted(bad))
for k in d["corners"]:
    d["corners"][k]["all"] = [r for r in d["corners"][k]["all"] if r["port"] not in bad]
json.dump(d, open(sys.argv[3], "w"))
