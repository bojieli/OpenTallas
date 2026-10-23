"""QC-P2 binding audit: what gen.py rtl needs before the Qwen compute die netlist binds to real RTL."""
import json, re, sys, collections, subprocess
sys.path.insert(0, "tools/die_plan")
import schema as S
raw = json.load(open("physical/die_plan/qwen_compute/die_plan.json"))
P = S.Plan(raw)
ninst = collections.Counter(p["type"] for p in raw["partitions"])
mods = {}
def has_module(m):
    if m not in mods:
        r = subprocess.run(["git", "-C", "/home/ubuntu/OpenTallas", "grep", "-l", "-E", r"^\s*module\s+" + re.escape(m) + r"\b", "origin/main", "--", "rtl"], capture_output=True, text=True)
        mods[m] = r.stdout.split("\n")[0].replace("origin/main:", "") if r.stdout else None
    return mods[m]
rep = {"types": len(P.types), "per_type": {}}
tot = collections.Counter()
for tn, t in sorted(P.types.items()):
    if t.get("hard"):
        continue
    c = t.get("contents", [])
    insts = {x["inst"] for x in c}
    pseudo = [x["module"] for x in c if not has_module(x["module"].split()[0]) or " " in x["module"]]
    leafb = collections.Counter(b.get("leaf") for b in t["buses"] if b.get("leaf"))
    twice = [k for k, v in leafb.items() if v > 1]
    noinst = [b["leaf"] for b in t["buses"] if b.get("leaf") and b["leaf"].split(".")[0] not in insts]
    noleaf = [b["name"] for b in t["buses"] if not b.get("leaf")]
    d = dict(instances=ninst[tn], contents=len(c), pseudo_modules=sorted(set(pseudo)), sources=len(t.get("sources", [])),
             binds=sum(1 for x in c if x.get("bind")), buses=len(t["buses"]), bus_leaf_shared=len(twice),
             bus_leaf_no_instance=len(noinst), bus_no_leaf=len(noleaf), ex_noinst=noinst[:3], ex_twice=twice[:3])
    rep["per_type"][tn] = d
    for k in ("contents", "buses", "bus_leaf_shared", "bus_leaf_no_instance", "bus_no_leaf", "binds", "sources"):
        tot[k] += d[k]
    tot["pseudo_contents"] += len(pseudo)
    tot["types_ok_for_rtl_root"] += (not pseudo and d["sources"] > 0 and not twice and not noinst and not noleaf)
rep["total"] = dict(tot)
rep["modules_found"] = {k: v for k, v in mods.items()}
json.dump(rep, open(sys.argv[1], "w"), indent=1)
print(json.dumps(rep["total"]))
for tn, d in rep["per_type"].items():
    print(tn, {k: v for k, v in d.items() if k in ("pseudo_modules", "bus_leaf_shared", "bus_leaf_no_instance", "bus_no_leaf")})
