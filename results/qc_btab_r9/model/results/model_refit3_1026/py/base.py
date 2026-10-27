import sys, time, statistics as st, json
sys.path.insert(0, sys.path[0])
import uf_phys3 as V, points as PT
from uf_phys3 import U, common
LIBS = U.load_libs(sys.argv[1])
F4 = json.load(open(PT.RES / "model_refit2_1026/refit4/uf_phys_refit4.json"))
for n, p in PT.POINTS.items():
    t = time.time()
    P = V.load_plan(p["spec"], p["geo"], p["seg"])
    dp = V.depth(P)
    for C, f, kind, b in (("TT", p["grt"][0], "max", "rise"), ("FF", p["grt"][1], "min", "early")):
        m = common.parse_sinks(f)[0]
        pr = V.basis_leaf(P, LIBS, C, kind, F4["PMAX"] if kind == "max" else F4["PMIN"])
        ks = [k for k in m if k in pr]
        r = [m[k][b] - pr[k] for k in ks]
        mm = [m[k][b] for k in ks]; pp = [pr[k] for k in ks]
        ds = sorted({dp[k] for k in ks})
        print(f"{n:10s} {C} leaves {len(ks)}/{len(m)} depth {ds} meas {st.mean(mm):.2f} w{max(mm)-min(mm):.2f} pred {st.mean(pp):.2f} w{max(pp)-min(pp):.2f} resid {st.mean(r):+.2f} sd{st.pstdev(r):.2f} max|{max(abs(x) for x in r):.2f}| {time.time()-t:.1f}s")
