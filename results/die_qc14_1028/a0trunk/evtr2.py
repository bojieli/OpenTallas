# DIE-QC-14 evtr2: evtr.py with child budgets read from the trunk json (contract 250/202.5)
import sys,json,re,statistics as st
t=sys.argv[1]; tr=json.load(open(f"trunk_{t}.json")); plan=tr["arrival_plan"]
CI={k:tuple(v) for k,v in tr["summary"]["child_ins"].items()}
res={}
for C,ci in (("TT",0),("FF",1)):
    regs=[];kids={};T={};nets={}
    for l in open(f"arr_tr_{t}_{C}.txt"):
        p=l.split()
        if p[0]=="S":
            a=float(p[4])
            if p[2].startswith("ICG"): continue
            if p[2].startswith("ot_qwen"): kids[p[1]]=(p[2],a)
            else: regs.append(a); nets.setdefault(p[3],[]).append(a)
        else: T[p[1]]=(float(p[2]),float(p[3]))
    tot=[a+CI[m][ci] for m,a in kids.values()]
    allv=regs+tot
    res[C]=dict(regs=dict(n=len(regs),mean=round(st.mean(regs),1),min=round(min(regs),1),max=round(max(regs),1)),
        child_total=dict(n=len(tot),min=round(min(tot),1),max=round(max(tot),1)),
        all=dict(min=round(min(allv),1),max=round(max(allv),1),spread=round(max(allv)-min(allv),1)),
        icg_gclk=T.get("a0t_icg/GCLK"))
    # per sink measured vs plan
    dev={}
    for k,v in kids.items():
        nm=k[:-4]
        dev[nm]=round(v[1]+CI[v[0]][ci]-plan.get(nm.replace("\\",""),plan.get(nm,{})).get(C.lower(),float("nan")),1) if (nm in plan or nm.replace("\\","") in plan) else None
    for s in tr["sinks"]:
        if s["kind"]=="cluster":
            a=T.get(s["name"]+"_root/A")
            ms=[x for n,v in nets.items() if re.search(s["name"]+"$",n) for x in v]
            if ms: dev[s["name"]]=round(st.mean(ms)-plan[s["name"]][C.lower()],1)
    res[C]["dev_vs_plan"]=dict(min=min(x for x in dev.values() if x is not None),max=max(x for x in dev.values() if x is not None))
    res[C]["_dev"]=dev
print(json.dumps({C:{k:v for k,v in r.items() if k!="_dev"} for C,r in res.items()},indent=0))
json.dump(res,open(f"evtr_{t}.json","w"),indent=0)
