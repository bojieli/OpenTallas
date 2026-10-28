# DIE-KV-13: ECTL K round trip per frame (Codex analyse_ectl_ca.py member selection) on a bind's bus_groups, and the
# landed-stage model check: landed_stages(member) vs sum of count-aligned sched_lat over the lane's crossings (sidecar).
import json, sys, collections
bg = json.load(open(sys.argv[1])); side = json.load(open(sys.argv[2]))
ca = side["count_aligned"]["ports"]; bylane = collections.defaultdict(list)
for r in side["ports"]:
    bylane[r["lane"]].append(r["port"])
diff = collections.Counter(); n = 0
for g in bg["landing"]:
    for m in g["members"]:
        s = sum(ca[p]["sched_lat"] for p in bylane.get(m["lane"], []) if p in ca)
        diff[m["landed_stages"] - s] += 1; n += 1
print("landed_stages - sum(sched_lat) histogram (top):", diff.most_common(6), "members", n)
req = collections.defaultdict(list); rsp = collections.defaultdict(list)
for g in bg["landing"]:
    for m in g["members"]:
        sp, _, pn = m["source"].rpartition(".")
        if pn.startswith("req_") and m["sink_port"] == "kreq": req[sp].append(m)
        if m["sink_port"].startswith("rsp_") and "ectl" in g["sink"]: rsp[g["sink"]].append(m)
RT = {s: 8 + next(iter({m["landed_stages"] for m in v})) + next(iter({m["landed_stages"] for m in rsp[s]})) for s, v in req.items()}
print("ECTL RT per frame:", collections.Counter(RT.values()), "frames", len(RT))
if len(sys.argv) > 3:   # new count_align bind (ports K/sched_lat) -> RT per frame by the landed-stage delta model
    nb = json.load(open(sys.argv[3]))["ports"]
    def dl(m): return sum(nb[p]["sched_lat"] - ca[p]["sched_lat"] for p in bylane.get(m["lane"], []) if p in ca)
    NRT = {}
    for s, v in req.items():
        a = {m["landed_stages"] + dl(m) for m in v}; b = {m["landed_stages"] + dl(m) for m in rsp[s]}
        assert len(a) == 1 and len(b) == 1, (s, a, b)
        NRT[s] = (8 + a.pop() + b.pop(), [m["lane"] for m in v], [m["lane"] for m in rsp[s]])
    print("NEW ECTL RT per frame:", collections.Counter(x[0] for x in NRT.values()))
    json.dump({s: dict(RT=x[0], req_lanes=x[1], rsp_lanes=x[2]) for s, x in NRT.items()}, open(sys.argv[4], "w"), indent=1)
