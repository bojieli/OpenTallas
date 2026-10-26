import sys, json, os
sys.path.insert(0, os.path.join(sys.argv[1], "tools/autopilot")); import ownership as O
plan = json.load(open(os.path.join(sys.argv[1], "physical/die_plan", sys.argv[2], "die_plan.json")))
T = plan["partition_types"]; a, b, key = sys.argv[3], sys.argv[4], sys.argv[5]
drop = {"contents": O.CONTENT_GEOM, "buses": O.BUS_GEOM, "ft_slots": O.SLOT_GEOM, "hard_cores": set()}[key]
A = {O._canon(O._strip(x, drop)) for x in T[a].get(key, [])}; B = {O._canon(O._strip(x, drop)) for x in T[b].get(key, [])}
lim = int(sys.argv[6]) if len(sys.argv) > 6 else 400
for x in sorted(A - B): print("-", x[:lim])
for x in sorted(B - A): print("+", x[:lim])
