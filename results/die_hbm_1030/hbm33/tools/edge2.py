import sys, json
sys.path.insert(0, sys.argv[1] + "/tools/die_plan")
import schema as S, lane_add as LA
raw = json.load(open(sys.argv[2] + "/die_plan.json"))
P = S.Plan(raw)
a, b = sys.argv[3], sys.argv[4]
df, lo, hi = LA.shared_edge(P, a, b)
rows = []
for pid, pr in P.ports.items():
    if "face" not in pr or "window_um" not in pr: continue
    s, d = pr["src"]["part"], pr["dst"]["part"]
    on = (s == a and pr["face"] == df) or (d == a and LA.OPP.get(pr["face"]) == df) or (s == b and pr["face"] == LA.OPP[df]) or (d == b and LA.OPP.get(pr["face"]) == LA.OPP[df])
    if not on: continue
    for _, _, win in S.port_segments(pr):
        w0, w1 = sorted(win)
        rows.append((w0, w1, pid, s, d, pr.get("width"), S.port_pins_count(pr)))
rows.sort()
prev = lo
for w0, w1, pid, s, d, wd, pins in rows:
    print(f"gap {w0-prev:7.2f} | {w0:9.2f}-{w1:9.2f} len {w1-w0:7.2f} pins {pins:5d} dens {pins/max(w1-w0,1e-9):5.2f}/um {pid} {s}->{d}")
    prev = max(prev, w1)
print(f"gap {hi-prev:7.2f} to edge end {hi}")
