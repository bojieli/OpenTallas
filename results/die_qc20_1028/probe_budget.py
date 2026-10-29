# DIE-QC-20 probe: per c_* region, dme_region_tree merge mode with join budgets; time, join calls, root spread S-Smin (ps)
import sys, pickle, time, signal, json
sys.path.insert(0, sys.argv[1]); sys.setrecursionlimit(100000)
import die_trial as D, os
if os.environ.get("DJB"): D.DME_JOIN_BUDGET = int(os.environ["DJB"])
c = pickle.load(open(sys.argv[2], "rb")); kw = c["kw"]
regs = sys.argv[3].split(","); budgets = [None if b == "none" else int(b) for b in sys.argv[4].split(",")]
from collections import defaultdict
rt = defaultdict(list)
for t in c["taps"]:
    rt[c["regions"][t[0]]].append(t)
class TO(Exception): pass
def h(*a): raise TO()
signal.signal(signal.SIGALRM, h)
for rn in regs:
    for b in budgets:
        signal.alarm(int(sys.argv[5]))
        t0 = time.time()
        try:
            dn, root, st = D.dme_region_tree(c["site"], rt[rn], rep_um=kw.get("rep_um"), delay_rep_um=kw.get("delay_rep_um"),
                                             early=kw.get("early"), snake=True, early_mode="merge", **({} if b is None else {"join_budget": b}))
            r = dn[root]
            keep, stk = [], [root]
            while stk:
                j = stk.pop(); keep.append(j); stk += dn[j]["kids"]
            res = dict(spread_ps=round(r["S"] - r["Smin"], 2), S=round(r["S"], 1), snake_um=round(sum(dn[j].get("snake_um", 0) for j in keep), 1),
                       snakes=sum(1 for j in keep if dn[j].get("snake_um")), nodes=len(keep), imb_max=round(max(dn[j].get("imb", 0) for j in keep), 2), topo=st.get("topology"), jf=st.get("join_fallbacks"), djb=D.DME_JOIN_BUDGET)
        except TO:
            res = "TIMEOUT"
        signal.alarm(0)
        print(json.dumps(dict(region=rn, taps=len(rt[rn]), budget=b, sec=round(time.time() - t0, 1), res=res)), flush=True)
