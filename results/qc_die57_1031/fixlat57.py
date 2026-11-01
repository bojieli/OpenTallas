# DIE-QC-57: judge plan_qc52 count_aligned_cycles (optionally moved by a port delta set) on a re-derived CA plan
# (same tree/rows/START, no re-plan of cycles).
# usage: fixlat57.py <ca plan.json> <plan_qc52.json> <out bind.json> [delta.json: list of ports (+1 each) or {port: delta}]
#        [--depth-from sidecar.json: judge with the as-built ring DEPTH of the sidecar instead of the derived one]
# parts (start_plan56 --parts ocv form) are taken from the sibling bind.json written by start_plan56 (same rows)
import json,sys,os
opt=sys.argv[1:]; args=[a for i,a in enumerate(opt) if not a.startswith("--") and not (i and opt[i-1]=="--depth-from")]
pf,plan,out=args[:3]; dl=json.load(open(args[3])) if len(args)>3 else {}
delta=dl if isinstance(dl,dict) else {p:1 for p in dl}
sdep=None
if "--depth-from" in opt: sdep={p:v["depth"] for p,v in json.load(open(opt[opt.index("--depth-from")+1]))["count_aligned"]["ports"].items()}
sys.path.insert(0,"/srv/opentallas-scratch2/claude/wt/die-qc-56/tools/die_plan")
T=833.0; ap=T/8
doc=json.load(open(pf)); cac=json.load(open(plan))["clock"]["landing_network"]["count_aligned_cycles"]
res=[]; dch=[]
for c in doc["crossings"]:
    P=cac[c["port"]]+int(delta.get(c["port"],0)); sh=(P-1-c["K_eff"])*T
    Llo,Lhi=c["L_lo_ps"]+sh,c["L_hi_ps"]+sh
    dep=sdep[c["port"]] if sdep else next((d for d in (4,8) if Lhi<=(d-0.5)*T-ap+1e-9),8)
    if dep!=c["depth"]: dch.append((c["port"],c["depth"],dep))
    mlo,mhi=Llo-0.5*T,(dep-0.5)*T-Lhi
    res.append((c["port"],P,c["lat_cycles"],round(mlo,1),round(mhi,1),dep))
    c.update(K_eff=P-1,K=P-1-c["n0"],L_lo_ps=round(Llo,1),L_hi_ps=round(Lhi,1),depth=dep,margin_lo_ps=round(mlo,1),margin_hi_ps=round(mhi,1),lat_cycles=P,rx_lat_counts=P-c["n0"],rtl=dict(c["rtl"],DEPTH=dep,K=P-1-c["n0"]))
f100=[r for r in res if min(r[3],r[4])<ap]
print("crossings",len(res),"moved",len(delta),"below_guard",len(f100),"lo",sum(r[3]<ap for r in f100),"hi",sum(r[4]<ap for r in f100),"depth_vs_replan",len(dch),dch[:3])
print("worst lo",min(res,key=lambda r:r[3]),"worst hi",min(res,key=lambda r:r[4]))
json.dump(dict(fails=f100,depth_changed=dch),open(out+".fails.json","w"))
import count_align_bind as B
try:
    ref=json.load(open(os.path.join(os.path.dirname(pf),"bind.json")));parts={p:(c["src_part"],c["dst_part"]) for p,c in ref["ports"].items()}
    b=B.bind(doc,parts=parts)
    if sdep:
        for p,c in b["ports"].items(): c["depth"]=sdep[p]
    json.dump(b,open(out,"w")); print("BIND OK")
except Exception as e: print("BIND FAIL",repr(e)[:400])
