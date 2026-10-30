import sys,numpy as np,collections
sinks,ff,ex,ey,tag=sys.argv[1],sys.argv[2],float(sys.argv[3]),float(sys.argv[4]),sys.argv[5]
face={}
for l in open(ff):
    p=l.split("\t")
    if len(p)<2: continue
    face[p[0].replace("\\","")]=p[1]
rows=[]
for l in open(sinks):
    if l[0]=="#": continue
    p=l.split()
    inst=p[0].rsplit("/",1)[0]
    rows.append((inst,float(p[1]),float(p[2]),float(p[3]),int(p[4]),p[5],float(p[7]),float(p[8]),float(p[9]),face.get(inst,"-")))
print(tag,"sinks",len(rows),"face matched",sum(r[9]!="-" for r in rows),"of",len(face))
def st(v): v=np.array(v); return "n=%d p50=%.1f p90=%.1f max=%.1f min=%.1f"%(len(v),np.median(v),np.percentile(v,90),v.max(),v.min())
a=[r[1] for r in rows]; print("ALL",st(a))
for f in "NSEW-":
    s=[r for r in rows if r[9]==f]
    if not s: continue
    d=[abs(r[2]-ex)+abs(r[3]-ey) for r in s]
    out=sum(1 for r in s if abs(r[1]-250)>40)
    print("face",f,st([r[1] for r in s]),"| dist p50 %.0f max %.0f"%(np.median(d),max(d)),"| out250+-40",out,"| depth",collections.Counter(r[4] for r in s))
# correlation
A=np.array([r[1] for r in rows]); D=np.array([abs(r[2]-ex)+abs(r[3]-ey) for r in rows]); dep=np.array([r[4] for r in rows])
print("corr(ins,dist)=%.2f corr(ins,depth)=%.2f"%(np.corrcoef(A,D)[0,1],np.corrcoef(A,dep)[0,1]))
k=np.polyfit(D,A,1); print("fit ins = %.1f + %.3f ps/um * dist"%(k[1],k[0]))
for dd in sorted(set(dep)): print(" depth",dd,st(A[dep==dd]))
# leaf stage: sink arr - leaf arr ; leaf arr spread
ls=np.array([r[1]-r[8] for r in rows]); print("leaf->sink wire",st(ls))
la={} 
for r in rows: la[r[5]]=r[8]
print("leaf buf out arrival",st(list(la.values())))
# leaf distance from its sink
ld=np.array([abs(r[2]-r[6])+abs(r[3]-r[7]) for r in rows]); print("sink-leaf dist um",st(ld))
fs=[r for r in rows if r[9]!="-"]
print("FACE leaf out arr",st([r[8] for r in fs]),"| face leaf->sink",st([r[1]-r[8] for r in fs]))
print("bins by dist (face flops): ")
for lo in range(0,260,40):
    s=[r[1] for r in fs if lo<=abs(r[2]-ex)+abs(r[3]-ey)<lo+40]
    if s: print("  %3d-%3d um"%(lo,lo+40),st(s))
