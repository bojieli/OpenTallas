import json, sys
sys.path.insert(0, "/srv/opentallas-scratch2/claude/wt/die-hbm-42/tools/die_plan")
import station_resite as SR
p = json.load(open(sys.argv[1])); T = p["partition_types"]
used = {pp["type"] for pp in p["partitions"].values()} if isinstance(p["partitions"], dict) else {pp["type"] for pp in p["partitions"]}
tot = 0
for t in sorted(T):
    if t not in used: continue
    rects = SR.core_rects(T[t]); bad = []
    for s in T[t].get("ft_slots", []):
        for k, r in enumerate(s.get("regs_um", [])):
            for rr in rects:
                x0, y0, x1, y1 = rr[1:5] if len(rr) >= 5 else rr
                if x0 + 0.01 < r[0] < x1 - 0.01 and y0 + 0.01 < r[1] < y1 - 0.01:
                    bad.append((s["name"], k, s.get("width"), rr[0])); break
    if bad:
        tot += len(bad); print(t, len(bad), bad[:6])
print("total", tot)
