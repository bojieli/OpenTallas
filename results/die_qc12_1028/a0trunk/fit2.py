# empirical stage table from built trunks: delay vs segment L (um), fanout 1 / 2; TT, FF; pooled over builds
import json,sys,numpy as np
rows={"TT":[], "FF":[]}
for g in sys.argv[1:]:
    tr=json.load(open(f"trunk_{g}.json"))
    for C in ("TT","FF"):
        T={}
        for l in open(f"arr_tr_{g}_{C}.txt"):
            p=l.split()
            if p[0]=="T": T[p[1]]=(float(p[2]),float(p[3]))
        drv={i["out_net"]:i for i in tr["insts"]}; loads={}
        for i in tr["insts"]: loads.setdefault(i["in_net"],[]).append((i["name"],i["p"]))
        for s in tr["sinks"]:
            if s["kind"]=="cluster": loads.setdefault(s["net"],[]).append((s["name"]+"_root",s["p"]))
        for net,ls in loads.items():
            if net not in drv: continue
            d=drv[net]; a=T.get(d["name"]+"/A")
            for nm,p in ls:
                b=T.get(nm+"/A")
                if a and b:
                    L=abs(p[0]-d["p"][0])+abs(p[1]-d["p"][1])
                    rows[C].append((L,len(ls),((b[1]-a[0])+(b[0]-a[1]))/2))
out={}
edges=[0,8,16,30,45,60,75,90,105,120,140,170]
for C,R in rows.items():
    R=np.array(R); tab=[]
    for fo in (1,2):
        S=R[R[:,1]==fo]
        for lo,hi in zip(edges,edges[1:]):
            m=S[(S[:,0]>=lo)&(S[:,0]<hi)]
            if len(m)>=3: tab.append([fo,float(np.median(m[:,0])),float(np.median(m[:,2])),len(m)])
    out[C]=tab
    print(C,[(t[0],round(t[1]),round(t[2],1),t[3]) for t in tab])
json.dump(out,open("stage_table.json","w"))
