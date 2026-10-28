import json, sys
def hops(e):
    pts = [e["from_um"]] + e["regs_um"] + [e["to_um"]]
    return [abs(a[0]-b[0]) + abs(a[1]-b[1]) for a, b in zip(pts, pts[1:])]
A = json.load(open(sys.argv[1] + "/die_plan.json")); B = json.load(open(sys.argv[2] + "/die_plan.json"))
for tn in ("q_hub_nw", "q_hub_ne", "root"):
    ea, eb = A["partition_types"][tn]["internal_stations"], B["partition_types"][tn]["internal_stations"]
    n = 0
    for a, b in zip(ea, eb):
        ha, hb = max(hops(a)), max(hops(b))
        if hb > 405 + 1e-6:
            n += 1
            if n <= 8: print(tn, b.get("conn", "")[:45], "c20h max %.1f  c20i max %.1f" % (ha, hb), "from", a["from_um"], "->", b["from_um"], "to", a["to_um"], "->", b["to_um"])
    print(tn, "over405 c20i", n, "c20h", sum(1 for a in ea if max(hops(a)) > 405 + 1e-6))
