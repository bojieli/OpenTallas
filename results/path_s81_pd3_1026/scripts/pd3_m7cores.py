import json,collections,sys
sys.path.insert(0,sys.argv[3]+"/tools/die_plan")
import die_trial as D
F={"B5":sys.argv[1],"g0fix":sys.argv[2]}
R={}
for k,f in F.items():
    P=json.load(open(f)); T=P["partition_types"]; acc=collections.Counter(); per=collections.Counter()
    for p in P["partitions"]:
        for x0,y0,x1,y1,tl,mod,hv in D.core_obs(T[p["type"]]):
            a=(x1-x0)*(y1-y0)/1e6
            if int(tl[1:])>=7: acc["M7"]+=a; per[p["name"]]+=a
            elif int(tl[1:])>=6: acc["M6"]+=a
            else: acc["<=M5"]+=a
    R[k]=per; print(k,{x:round(v,1) for x,v in acc.items()},"mm2 of die area blocked to >=layer")
d={n:R["g0fix"][n]-R["B5"][n] for n in set(R["g0fix"])|set(R["B5"])}
top=sorted(d.items(),key=lambda kv:-abs(kv[1]))[:20]
print("parts with largest change in M7-blocked core area (mm2, g0fix-B5):",[(n,round(v,2)) for n,v in top])
print("sum change",round(sum(d.values()),2))
