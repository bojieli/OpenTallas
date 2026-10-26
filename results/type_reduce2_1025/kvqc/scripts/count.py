import sys, json, os
wt, die = sys.argv[1], sys.argv[2]
sys.path.insert(0, os.path.join(wt, "tools/autopilot"))
import ownership as O
pdir = os.path.join(wt, "physical/die_plan", die)
plan = json.load(open(os.path.join(pdir, "die_plan.json")))
pins = {}
for t in plan["partition_types"].values():
    for h in t.get("hard_cores") or []:
        f = h.get("pins_file")
        if f and os.path.exists(os.path.join(pdir, f)):
            pins[f] = open(os.path.join(pdir, f)).read()
cand = O.bound_rtl_paths(die, plan)
bound = {}
for k, cs in cand.items():
    for c in cs:
        p = os.path.join(wt, c)
        if os.path.exists(p):
            bound[k] = open(p).read(); break
items = O.plan_items(die, plan, pins, None, bound)
nt = sum(1 for i in items if i["kind"] == "type"); nc = len(items) - nt
print(f"{die}: {len(items)} = {nt} types + {nc} cores", file=sys.stderr)
for i in items:
    print("\t".join([die, i["item"], i["kind"], str(i["replicas"]), ",".join(i["members"])]))
