import json,sys
import os;H=os.path.dirname(os.path.abspath(__file__));sys.path.insert(0,os.path.join(H,'../../../tools/die_plan'));import taps  # main cfea7b3a1
b=json.load(open(os.path.join(H,'current3_clock_bins.json')))['bins'];M=json.load(open(os.path.join(H,'macros.json')))
W,H=777.6,518.4
pts=[(x,y,n) for x,y,n in b]
blocked=lambda x,y:any(x0<x<x1 and y0<y<y1 for x0,y0,x1,y1 in M)
res={}
for target,cap,radius in [(1000,1250,100),(1200,1500,150),(1500,1875,200)]:
    L=taps._bisect(pts,target,radius,blocked,max(1,target//20))
    xy=[(min(max(q[0],17.28),W-17.28),min(max(q[1],17.28),H-17.28)) for q in L]
    for _ in range(6):
        _,_,asg=taps.assign([(None,x,y) for x,y in xy],pts,target,radius,max_distance_um=radius)
        g=[[] for _ in xy]
        for p,j in zip(pts,asg):g[j].append(p)
        nxt=[(taps._wmedian(gg,0),taps._wmedian(gg,1)) for gg in g if gg]
        if nxt==xy:break
        xy=nxt
    load,far,asg=taps.assign([(None,x,y) for x,y in xy],pts,cap,radius,max_distance_um=radius)
    rows=sorted([(round(x,2),round(y,2),int(n),round(r,1)) for (x,y),n,r in zip(xy,load,far) if n>0],key=lambda q:(q[1],q[0]))
    ns=[r[2] for r in rows];rs=[r[3] for r in rows]
    print(target,cap,radius,'taps',len(rows),'sinks',sum(ns),'max',max(ns),'min',min(ns),'maxR',max(rs),'over_cap',sum(n>cap for n in ns),'overR',sum(r>radius+1e-6 for r in rs))
    res[f"{target}_{cap}_{radius}"]=rows
json.dump(res,open(os.path.join(H,'seed_current3.json'),'w'),indent=0)
