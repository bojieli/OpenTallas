import sys, statistics as st, math
sys.path.insert(0, sys.path[0])
import uf_phys3 as V, points as PT
from uf_phys3 import U, common
LIBS = U.load_libs(sys.argv[1]); n = sys.argv[2]
p = PT.POINTS[n]; P = V.load_plan(p["spec"], p["geo"], p["seg"]); D = V.depth(P)
m = common.parse_sinks(p["grt"][0])[0]
q = dict(alpha=0.2, beta=0.45, gslew=4.0, bleaf=0.25, kstage=1.5, kleaf=1.2868)
pr, arr = V.predict3(P, LIBS, "TT", edge="rise", **q)
def corr(a, b):
    ma, mb = st.mean(a), st.mean(b); return sum((x-ma)*(y-mb) for x, y in zip(a, b)) / math.sqrt(sum((x-ma)**2 for x in a) * sum((y-mb)**2 for y in b) + 1e-12)
ks = list(m); R = [m[k]["rise"] - pr[k] for k in ks]
# path features: sum of upstream seg lengths, number of fanout>1 nets on path
def path(k):
    out = []; x = k
    while P.nodes[x]["par"]:
        out.append(x); x = P.nodes[x]["par"]
    return out
up = [sum(P._seglen(x) for x in path(k)) for k in ks]
mst = [U.mst_len([P.nodes[k]["xy"]] + P.nodes[k]["sinks"]) for k in ks]
ia = [arr[k][0] for k in ks]; sl = [arr[k][1] for k in ks]
print(n, "resid mean %.2f sd %.2f" % (st.mean(R), st.pstdev(R)), "corr up_len %.2f mst %.2f in_arr %.2f in_slew %.2f" % (corr(R, up), corr(R, mst), corr(R, ia), corr(R, sl)))
# grouped by L1 branch (first-level child)
g = {}
for k, r in zip(ks, R):
    g.setdefault(path(k)[-1], []).append(r)
print(" by L1 branch:", {a: round(st.mean(v), 1) for a, v in g.items()})
g = {}
for k, r in zip(ks, R):
    pp = path(k); g.setdefault(pp[-2] if len(pp) > 1 else pp[-1], []).append(r)
print(" by L2:", {a: round(st.mean(v), 1) for a, v in sorted(g.items())})
