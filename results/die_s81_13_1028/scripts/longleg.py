"""DIE-S81-13: map tree paths -> tree.json nodes (same indexing as trial_tap_arrivals.py) and list every tree edge with
built late delay > THR ps, with parent/child region, xy, length, and the buffer nets on the edge."""
import json, sys
t = json.load(open(sys.argv[1])); arr = json.load(open(sys.argv[2])); thr = float(sys.argv[3])
N = {int(k): v for k, v in t["nodes"].items()}
path = {}
root = [i for i, v in N.items() if v["parent"] is None][0]
st = [(root, "h")]
while st:
    i, p = st.pop(); path[i] = p
    for j, c in enumerate(N[i].get("kids", [])):
        st.append((c, p + str(j)))
nl = arr["node_late_ps"]
rows = []
for i, v in N.items():
    if v["parent"] is None: continue
    pi = v["parent"]; a, b = path[pi], path[i]
    if a in nl and b in nl:
        d = nl[b] - nl[a]
        if d > thr:
            L = abs(v["x"] - N[pi]["x"]) + abs(v["y"] - N[pi]["y"])
            rows.append((d, i, pi, N[pi].get("region_root"), v.get("region_root"), v.get("feed"), round(L), (round(N[pi]["x"]), round(N[pi]["y"])), (round(v["x"]), round(v["y"])), len(b)))
rows.sort(reverse=True)
print("edges >", thr, ":", len(rows))
for r in rows[:40]:
    print("%.0f ps node %d<-%d reg %s->%s feed %s L1 %d um %s->%s depth %d" % r)
