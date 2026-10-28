import json, sys, collections
D = sys.argv[1]; S = sys.argv[2] if len(sys.argv) > 2 else "1.0485"
c = json.load(open(f"{D}/ca_s{S}.json"))
L = {r["port"]: r for r in json.load(open(f"{D}/lpo.json"))["corners"]["TT_droop-regions_corelat250"]["all"]}
g = collections.Counter()
for o in c["crossings"]:
    if not o.get("depth"):
        r = L[o["port"]]
        g[(tuple(sorted((o["src"], o["dst"]))), o["path_ambiguous_cycles"], round(max(r["unshared_a_ps"], r["unshared_b_ps"])), round(min(r["unshared_a_ps"], r["unshared_b_ps"])))] += 1
for k, n in g.most_common():
    print(n, k)
