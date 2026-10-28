import json, pickle, sys, time
sys.path.insert(0, sys.argv[1]); sys.setrecursionlimit(100000)
import die_trial as D
D.DME_JOIN_BUDGET = int(sys.argv[4])
d = pickle.load(open(sys.argv[2], "rb")); kw = dict(d["kw"]); kw.pop("early_mode", None)
if sys.argv[3] != "hang": kw["early_mode"] = sys.argv[3]
t = time.time(); out, root, st = D.dme_region_tree(d["site"], d["taps"], **kw)
jc = sorted(D.JC)
print(json.dumps(dict(pkl=sys.argv[2][-12:], mode=sys.argv[3], B=int(sys.argv[4]), s=round(time.time()-t, 1), joins=len(jc), jmax=jc[-1] if jc else 0,
      jp99=jc[int(len(jc)*0.99)] if jc else 0, jsum=sum(jc), fb=st.get("join_fallbacks", 0), spread=st.get("spread_um"))))
