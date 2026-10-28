"""DIE-KV-4: per-crossing / per-lane latency comparison of CA plans (KV-3 MESO-INTEG x1.00 plan vs reconcile x1.00 / spice)."""
import json, sys
from collections import defaultdict
P = "/srv/opentallas-scratch2/claude/die-kv-4-1027/proto/"
E = "/srv/opentallas-scratch2/claude/die-kv-3-1027/"
plan = json.load(open("/srv/opentallas-scratch2/claude/kv-plan-d9b-1027/pd9b/hm_r26q9b.json"))
owner = {pid: l["id"] for l in plan["lanes"] for pid in l["ports"]}
src = {"kv3_x100": E + "H200B_ca.json", "kv3_x105": E + "H200B_s105_ca.json", "rec_x100": P + "H200B_s100_ca.json",
       "rec_x105": P + "H200B_s105_ca.json", "rec_spice": P + "H200B_spice_ca.json"}
cr = {k: {c["port"]: c for c in json.load(open(f))["crossings"]} for k, f in src.items()}
SEVEN = ["L2192_2", "L2374_0", "L2390_1", "L2401_1", "L2197_2", "L2391_0", "L2402_0"]
print("port src->dst | per plan: depth lat [margin_lo/hi or L_lo/L_hi] amb")
for p in SEVEN:
    c0 = cr["rec_spice"][p]
    s = f"{p} {c0['src']}->{c0['dst']}"
    for k in src:
        c = cr[k][p]
        m = (c.get("margin_lo_ps"), c.get("margin_hi_ps")) if "margin_lo_ps" in c else (c["L_lo_ps"], c["L_hi_ps"])
        s += f" | {k}: D{c['depth']} lat {c['lat_cycles']} {m} amb {c['path_ambiguous_cycles']}"
    print(s)
lane = {k: defaultdict(int) for k in src}
for k in src:
    for p, c in cr[k].items():
        lane[k][owner[p]] += c["lat_cycles"] if c["lat_cycles"] is not None else 99
aff = sorted({owner[p] for p in SEVEN})
for l in aff:
    print(l, {k: lane[k][l] for k in src}, "old+3:", 3 * sum(1 for p in cr["rec_spice"] if owner[p] == l))
for a, b in (("kv3_x100", "rec_spice"), ("rec_x100", "rec_spice")):
    d = [(lane[b][l] - lane[a][l], l) for l in lane[b]]
    up = sorted([x for x in d if x[0] > 0], reverse=True)
    print(f"{a}->{b}: lanes {len(d)} up {len(up)} (sum +{sum(x[0] for x in up)}) down {sum(1 for x in d if x[0]<0)} max {up[:8]}")
groups = plan.get("latency_groups", [])
for g in groups:
    print("group", g["name"], {k: [lane[k][l] for l in g["lanes"]] for k in ("kv3_x100", "rec_spice")})
