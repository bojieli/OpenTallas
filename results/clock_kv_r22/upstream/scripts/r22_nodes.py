import json, sys, collections
m = json.load(open(sys.argv[1] + "/mesh.json"))
P = json.load(open(sys.argv[2]))
T = P["partition_types"]; parts = {p["name"]: p for p in P["partitions"]}
mod = {}
for p in P["partitions"]:
    for h in T[p["type"]].get("hard_cores", []) or []:
        mod[f"{p['name']}/{h['inst']}"] = h["module"]
c = collections.Counter(); ex = {}
for x in m["pushdown"]:
    if x["role"] != "tree_node":
        continue
    md = mod.get(x.get("core"), x.get("core"))
    k = (x.get("level"), md, "upstream" if x.get("upstream_um") else "island")
    c[k] += 1
    ex.setdefault(k, x)
for k, v in sorted(c.items(), key=lambda kv: str(kv[0])):
    print(k, v, json.dumps(ex[k])[:300])
print("upstream_slides", json.dumps(m["meta"]["upstream_slides"])[:1500])
