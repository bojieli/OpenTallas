import sys,numpy as np,collections
T={}
for l in open(sys.argv[1]):
    if l[0]=="#": continue
    p=l.split(); T[p[0]]=dict(m=p[1],x=float(p[2]),y=float(p[3]),ia=float(p[4]),oa=float(p[5]),sl=float(p[6]),fo=int(p[7]),drv=p[8])
def lvl(n):
    k=0
    while n in T: n=T[n]["drv"]; k+=1
    return k
for n,t in T.items(): t["lv"]=lvl(n)
print("lv8 leaves:")
for n,t in T.items():
    if t["lv"]==8: d=T[t["drv"]]; print(" ",n,"drv",t["drv"],"(%s fo %d @%.0f,%.0f)"%(d["m"],d["fo"],d["x"],d["y"]),"@%.0f,%.0f oa %.0f fo %d"%(t["x"],t["y"],t["oa"],t["fo"]))
# lv7: wire delay vs distance from lv6 driver
rows=[]
for n,t in T.items():
    if t["lv"]==7 and t["drv"] in T:
        d=T[t["drv"]]; dist=abs(t["x"]-d["x"])+abs(t["y"]-d["y"])
        rows.append((dist,t["ia"]-d["oa"],t["oa"]-t["ia"],t["sl"],d["fo"],t["fo"],t["oa"],n))
r=np.array([x[:7] for x in rows])
print("lv6->lv7 dist p50 %.0f p90 %.0f max %.0f um"%(np.median(r[:,0]),np.percentile(r[:,0],90),r[:,0].max()))
print("corr(wire,dist)=%.2f corr(leafcell,inslew)=%.2f corr(oa,dist)=%.2f corr(oa,lv6fo)=%.2f"%(np.corrcoef(r[:,0],r[:,1])[0,1],np.corrcoef(r[:,2],r[:,3])[0,1],np.corrcoef(r[:,6],r[:,0])[0,1],np.corrcoef(r[:,6],r[:,4])[0,1]))
k=np.polyfit(r[:,0],r[:,6],1); print("leaf out arr = %.1f + %.3f*dist(lv6->leaf)"%(k[1],k[0]))
# per lv6 driver
by=collections.defaultdict(list)
for x in rows: by[x[-1] and T[x[-1]]["drv"]].append(x)
print("per lv6 cluster driver: name fo x y oa | leaf oa min..max | max dist")
for dn,xs in sorted(by.items(), key=lambda kv:-max(x[6] for x in kv[1])):
    d=T[dn]; print("  %-28s fo %2d @%5.0f,%5.0f oa %.0f | leaf %.0f..%.0f | dist max %.0f slew max %.0f"%(dn,d["fo"],d["x"],d["y"],d["oa"],min(x[6] for x in xs),max(x[6] for x in xs),max(x[0] for x in xs),max(x[3] for x in xs)))
