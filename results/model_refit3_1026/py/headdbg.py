import sys, statistics as st, json
sys.path.insert(0, sys.path[0])
import uf_phys3 as V, points as PT
from uf_phys3 import U, common
LIBS = U.load_libs(sys.argv[1]); n = sys.argv[2]
F4 = json.load(open(PT.RES / "model_refit2_1026/refit4/uf_phys_refit4.json"))
p = PT.POINTS[n]; P = V.load_plan(p["spec"], p["geo"], p["seg"])
m = common.parse_sinks(p["grt"][0])[0]
pr, arr = V.predict3(P, LIBS, "TT", edge="rise", **F4["PMAX"])
rows = []
for k in m:
    v = P.nodes[k]; pts = [v["xy"]] + v["sinks"]
    rows.append((m[k]["rise"] - pr[k], k, len(v["sinks"]), U.mst_len(pts), v["cell"], arr[k][0], arr[k][1], pr[k] - arr[k][0], m[k]["rise"]))
rows.sort()
for r in rows[:6] + rows[-6:]:
    print("resid %+.1f %s n%d mst%.0f %s in_arr %.1f in_slew %.1f leafstage %.1f meas %.1f" % r)
import math
# correlations
def corr(a, b):
    ma, mb = st.mean(a), st.mean(b); return sum((x-ma)*(y-mb) for x, y in zip(a, b)) / math.sqrt(sum((x-ma)**2 for x in a) * sum((y-mb)**2 for y in b))
R = [r[0] for r in rows]
print("corr resid vs n", round(corr(R, [r[2] for r in rows]), 2), "mst", round(corr(R, [r[3] for r in rows]), 2), "in_arr", round(corr(R, [r[5] for r in rows]), 2), "slew", round(corr(R, [r[6] for r in rows]), 2), "leafstage", round(corr(R, [r[7] for r in rows]), 2))
print("leafstage range", round(min(r[7] for r in rows),1), round(max(r[7] for r in rows),1), "in_arr range", round(min(r[5] for r in rows),1), round(max(r[5] for r in rows),1))
