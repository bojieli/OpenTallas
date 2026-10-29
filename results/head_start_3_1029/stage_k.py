"""HEAD-START-3: per-STAGE consistent half-cycle re-choice from the routed STA (TT setup w/ droop+60 unc, FF hold +25 unc).
Each START stage has one incoming crossing (parent stage -> its FFs); all its crossing endpoints share ONE relative shift
k (half cycles) of the capture edge vs the as-built edge relation.  Tree => any per-crossing relative k is realisable
top-down (offset(child) = offset(parent) + as-built relation + k T/2).  margin(stage) = max_k min_ep min(s + kT/2, h - kT/2)."""
import json,collections,sys
T=833.333
ca=json.load(open(sys.argv[1]))
X=[r for r in ca['rows'] if r['cross']]
by=collections.defaultdict(list)
for r in X: by[(r['launch_setup'],r['cap'])].append(r)
res=[]
for (l,c),rs in by.items():
    best=max((min(min(r['s']+k*T/2,r['h']-k*T/2) for r in rs),k) for k in range(-24,25))
    asb=max((min(min(r['s']+j*T,r['h']-j*T) for r in rs),j) for j in range(-12,13))
    res.append(dict(launch=l,cap=c,eps=len(rs),margin=round(best[0],2),k=best[1],asbuilt=round(asb[0],2),J=asb[1]))
m=sorted(x['margin'] for x in res)
out=dict(crossing_stages=len(res),endpoints=len(X),replan_min=m[0],replan_lt0=sum(x<0 for x in m),replan_lt100=sum(x<100 for x in m),
         asbuilt_lt0=sum(x['asbuilt']<0 for x in res),k_hist=dict(sorted(collections.Counter(x['k'] for x in res).items())),
         k_odd_flip_edge=sum(x['k']%2 for x in res))
print(json.dumps(out))
json.dump(dict(summary=out,rows=sorted(res,key=lambda x:x['margin'])),open(sys.argv[2],'w'),indent=0)
for x in sorted(res,key=lambda x:x['margin'])[:6]: print(x)
