import json,sys,collections
F={"B5":"path-s81-ftA/die_B5i50/src/physical/die_plan/s81/die_plan.json","g0fix":"path-s81-taps-1026/src/physical/die_plan/s81/die_plan_phyfit_g0fix.json"}
HOT={'lk_WS0','lk_WS1','lk_WN0','lk_WN1','lk_WN3','lk_ES1','lk_EN0','lk_EN1','lk_WS3','lk_EN2','lk_EN3','iqf','s_4N_x06','gunit','bk_sel'}
R={}
for k,f in F.items():
    P=json.load(open(f)); T=P["partition_types"]; C={}
    for p in P["partitions"]:
        w,h=T[p["type"]]["outline_um"]; C[p["name"]]=(p["origin_um"][0]+w/2,p["origin_um"][1]+h/2)
    acc=collections.Counter(); tot=0
    for q in P["ports"]:
        a,b=q["src"]["part"],q["dst"]["part"]
        if a not in C or b not in C: continue
        d=abs(C[a][0]-C[b][0])+abs(C[a][1]-C[b][1]); bm=q["width"]*d/1e3
        tot+=bm
        for n in (a,b):
            if n in HOT: acc[n]+=bm/ (2 if (a in HOT and b in HOT) else 1)
        if a in HOT or b in HOT: acc["pair:%s-%s"%tuple(sorted((a,b)))]+=bm
    R[k]=(tot,acc)
print("total bit-m B5 %.0f g0fix %.0f"%(R["B5"][0]/1e3,R["g0fix"][0]/1e3))
keys=sorted(set(R["B5"][1])|set(R["g0fix"][1]),key=lambda x:-(R["g0fix"][1][x]-R["B5"][1][x]))
for x in keys[:18]: print(x,"B5 %.0f g0fix %.0f d %+.0f bit-m"%(R["B5"][1][x]/1e3,R["g0fix"][1][x]/1e3,(R["g0fix"][1][x]-R["B5"][1][x])/1e3))
