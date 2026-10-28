"""KV-PLAN-DELTA-7 what-if: move each FT station cluster (rigid shift) so its pin bbox keeps >= CLR um from every core
OBS (M5) rect, if the channel it sits in allows; reports moved / impossible clusters.  Abstract-only diagnostic."""
import re,sys,collections
src,dst,CLR=sys.argv[1],sys.argv[2],float(sys.argv[3])
L=open(src).read(); W,H=map(float,re.search(r"SIZE (\S+) BY (\S+)",L).groups())
ob=L[L.index("  OBS"):]; R=[]; cur=None
for line in ob.splitlines():
    m=re.match(r"\s+LAYER (\S+)",line)
    if m: cur=m.group(1); continue
    m=re.match(r"\s+RECT (\S+) (\S+) (\S+) (\S+)",line)
    if m and cur=="M5": R.append(tuple(map(float,m.groups())))
pins=collections.defaultdict(list)
for m in re.finditer(r"  PIN (ot_s_(ft\d+_\d+)_[dq]\[\d+\])\n.*?RECT (\S+) (\S+) (\S+) (\S+) ;",L,re.S):
    pins[m.group(2)].append(tuple(map(float,m.group(3,4,5,6))))
def bad(b):
    x0,y0,x1,y1=b
    return any(x0<c+CLR and x1>a-CLR and y0<d+CLR and y1>bb-CLR for a,bb,c,d in R)
shift={}; stuck=[]
for s,v in pins.items():
    b=(min(p[0] for p in v),min(p[1] for p in v),max(p[2] for p in v),max(p[3] for p in v))
    if b[0]<0.5 or b[2]>W-0.5 or not bad(b): continue    # face stations stay on the face
    best=None
    for k in range(1,400):
        for dx,dy in ((0,k*0.27),(0,-k*0.27),(k*0.27,0),(-k*0.27,0)):
            nb=(b[0]+dx,b[1]+dy,b[2]+dx,b[3]+dy)
            if nb[0]>1 and nb[2]<W-1 and nb[1]>1 and nb[3]<H-1 and not bad(nb): best=(dx,dy); break
        if best: break
    if best: shift[s]=best
    else: stuck.append(s)
def mv(m):
    s=m.group(2); dx,dy=shift.get(s,(0,0))
    a,b,c,d=map(float,m.group(3,4,5,6))
    return m.group(0)[:m.start(3)-m.start(0)]+f"{a+dx:.4f} {b+dy:.4f} {c+dx:.4f} {d+dy:.4f} ;"
L2=re.sub(r"  PIN (ot_s_(ft\d+_\d+)_[dq]\[\d+\])\n.*?RECT (\S+) (\S+) (\S+) (\S+) ;",mv,L,flags=re.S)
open(dst,"w").write(L2)
print("moved",len(shift),{k:(round(v[0],2),round(v[1],2)) for k,v in sorted(shift.items())}); print("stuck",stuck)
