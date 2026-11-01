# DIE-QC-57: judge plan_qc52 count_aligned_cycles (optionally +1 on a port set) on a re-derived CA plan (same tree/rows/START)
# usage: fixlat57.py <ca plan.json> <plan_qc52.json> <out bind.json> [plus1.json (list of ports)]
import json,sys
sys.path.insert(0,"/srv/opentallas-scratch2/claude/wt/die-qc-56/tools/die_plan")
pf,plan,out=sys.argv[1:4]; plus=set(json.load(open(sys.argv[4]))) if len(sys.argv)>4 else set()
T=833.0; ap=T/8
doc=json.load(open(pf)); cac=json.load(open(plan))["clock"]["landing_network"]["count_aligned_cycles"]
res=[]; dch=[]
for c in doc["crossings"]:
    P=cac[c["port"]]+(1 if c["port"] in plus else 0); sh=(P-1-c["K_eff"])*T
    Llo,Lhi=c["L_lo_ps"]+sh,c["L_hi_ps"]+sh
    dep=next((d for d in (4,8) if Lhi<=(d-0.5)*T-ap+1e-9),8)
    if dep!=c["depth"]: dch.append((c["port"],c["depth"],dep))
    mlo,mhi=Llo-0.5*T,(dep-0.5)*T-Lhi
    res.append((c["port"],P,c["lat_cycles"],round(mlo,1),round(mhi,1),dep))
    c.update(K_eff=P-1,K=P-1-c["n0"],L_lo_ps=round(Llo,1),L_hi_ps=round(Lhi,1),depth=dep,margin_lo_ps=round(mlo,1),margin_hi_ps=round(mhi,1),lat_cycles=P,rx_lat_counts=P-c["n0"],rtl=dict(c["rtl"],DEPTH=dep,K=P-1-c["n0"]))
f100=[r for r in res if min(r[3],r[4])<100]
print("crossings",len(res),"plus1",len(plus),"below100",len(f100),"lo",sum(r[3]<100 for r in f100),"hi",sum(r[4]<100 for r in f100),"depth_changed",len(dch),dch[:5])
print("worst lo",min(res,key=lambda r:r[3]),"worst hi",min(res,key=lambda r:r[4]))
json.dump(dict(fails=f100,depth_changed=dch),open(out+".fails.json","w"))
import count_align_bind as B
try:
    b=B.bind(doc); json.dump(b,open(out,"w")); print("BIND OK")
except Exception as e: print("BIND FAIL",repr(e)[:400])
