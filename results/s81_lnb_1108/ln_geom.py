import json,re,sys,collections
d=json.load(open(sys.argv[1]))
pt=d["partition_types"]
rows=[]
for tn,t in sorted(pt.items()):
    ln={}
    for h in t.get("hard_cores",[]) or []:
        m=re.search(r"u_vp\.g_ln\[(\d+)\]\.u_l$",h.get("inst",""))
        if m:
            x,y=h["origin_um"]; w,hh=h["outline_um"]
            if h.get("orient","R0") in ("R90","R270","MXR90","MYR90"): w,hh=hh,w
            ln[int(m.group(1))]=(x,y,w,hh,h.get("orient"))
    if not ln: continue
    # K-group spread (centre bbox w+h), what one cf word must reach
    sp=[]
    for K in range(4):
        cs=[(ln[l][0]+ln[l][2]/2, ln[l][1]+ln[l][3]/2) for l in range(4*K,4*K+4) if l in ln]
        if cs: sp.append(max(c[0] for c in cs)-min(c[0] for c in cs)+max(c[1] for c in cs)-min(c[1] for c in cs))
    xs=sorted(set(round(v[0],2) for v in ln.values()))
    allc=[(v[0]+v[2]/2,v[1]+v[3]/2) for v in ln.values()]
    span=max(c[0] for c in allc)-min(c[0] for c in allc)+max(c[1] for c in allc)-min(c[1] for c in allc)
    # min gap between LN macros (x or y gutters among overlapping neighbours)
    gaps=[]
    L=list(ln.values())
    for i in range(len(L)):
        for j in range(i+1,len(L)):
            a,b=L[i],L[j]
            oy=min(a[1]+a[3],b[1]+b[3])-max(a[1],b[1]); ox=min(a[0]+a[2],b[0]+b[2])-max(a[0],b[0])
            if oy>0: gaps.append(max(b[0]-(a[0]+a[2]), a[0]-(b[0]+b[2])))
            if ox>0: gaps.append(max(b[1]-(a[1]+a[3]), a[1]-(b[1]+b[3])))
    gaps=[g for g in gaps if g>=0]
    rows.append(dict(type=tn,n=len(ln),cols=len(xs),xs=xs,kspread=[round(s) for s in sp],maxk=round(max(sp)),span=round(span),
                     mingap=round(min(gaps),2) if gaps else None, outline=t.get("outline_um"), key=tuple(sorted((l,round(v[0],1),round(v[1],1),v[4]) for l,v in ln.items()))))
json.dump([{k:v for k,v in r.items() if k!='key'} for r in rows],open(sys.argv[2],"w"),indent=0)
geo=collections.defaultdict(list)
for r in rows: geo[r["key"]].append(r["type"])
print("types with LN macros:",len(rows),"distinct LN geometries:",len(geo))
for r in rows: print(r["type"],r["n"],"cols",r["cols"],"xs",r["xs"],"Kspread",r["kspread"],"span",r["span"],"mingap",r["mingap"],"outline",r["outline"])
for k,v in sorted(geo.items(),key=lambda kv:-len(kv[1])): print(len(v),v[:12])
