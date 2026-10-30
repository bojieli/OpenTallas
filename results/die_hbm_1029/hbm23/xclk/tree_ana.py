import sys,numpy as np,collections
T={}
for l in open(sys.argv[1]):
    if l[0]=="#": continue
    p=l.split(); T[p[0]]=dict(m=p[1],x=float(p[2]),y=float(p[3]),ia=float(p[4]),oa=float(p[5]),sl=float(p[6]),fo=int(p[7]),drv=p[8])
def lvl(n):
    k=0
    while n in T: n=T[n]["drv"]; k+=1
    return k
L=collections.defaultdict(list)
for n,t in T.items(): t["lv"]=lvl(n); L[t["lv"]].append(n)
for lv in sorted(L):
    d=np.array([T[n]["oa"]-T[n]["ia"] for n in L[lv]]); w=np.array([T[n]["ia"]-(T[T[n]["drv"]]["oa"] if T[n]["drv"] in T else 0) for n in L[lv]])
    sl=np.array([T[n]["sl"] for n in L[lv]]); oa=np.array([T[n]["oa"] for n in L[lv]]); fo=np.array([T[n]["fo"] for n in L[lv]])
    names=collections.Counter(n.split("_")[0] for n in L[lv])
    print("lv%d n=%3d %s | cell p50 %.1f max %.1f | wire p50 %.1f max %.1f | in_slew p50 %.0f max %.0f | out_arr %.0f..%.0f | fo p50 %d max %d"%(lv,len(d),dict(names),np.median(d),d.max(),np.median(w),w.max(),np.median(sl),sl.max(),oa.min(),oa.max(),np.median(fo),fo.max()))
