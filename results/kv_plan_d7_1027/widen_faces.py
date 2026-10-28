"""KV-PLAN-DELTA-7 what-if: re-space FT face pins (ftN_i / ftN_o buses) to <= PER_UM bits/um about the window centre
(layer alternation kept). Abstract-only diagnostic of a wider seam window (needs the neighbour's window in a real event)."""
import re,sys,collections
src,dst,PER=sys.argv[1],sys.argv[2],float(sys.argv[3])
L=open(src).read(); W,H=map(float,re.search(r"SIZE (\S+) BY (\S+)",L).groups())
pat=re.compile(r"  PIN ((ft\d+_[io])\[(\d+)\])\n(.*?)RECT (\S+) (\S+) (\S+) (\S+) ;",re.S)
bus=collections.defaultdict(list)
for m in pat.finditer(L):
    x0,y0,x1,y1=map(float,m.group(5,6,7,8))
    f='W' if x0<0.3 else 'E' if x1>W-0.3 else 'S' if y0<0.3 else 'N'
    bus[m.group(2)].append((int(m.group(3)),f,(y0+y1)/2 if f in 'EW' else (x0+x1)/2))
newc={}; rep=[]
for b,v in bus.items():
    c=[q[2] for q in v]; lo,hi=min(c),max(c); n=len(v)
    if n<16 or n/max(hi-lo,0.05)<=PER: continue
    span=n/PER; mid=(lo+hi)/2; a=max(0.5,min((W if v[0][1] in 'NS' else H)-0.5-span,mid-span/2))
    order=sorted(v,key=lambda q:q[2])
    for k,(bit,f,_) in enumerate(order): newc[(b,bit)]=a+(k+0.5)/PER
    rep.append((b,v[0][1],n,round(hi-lo,1),round(span,1)))
def mv(m):
    key=(m.group(2),int(m.group(3)))
    if key not in newc: return m.group(0)
    x0,y0,x1,y1=map(float,m.group(5,6,7,8)); c=newc[key]
    if x0<0.3 or x1>W-0.3: h=(y1-y0)/2; y0,y1=c-h,c+h
    else: h=(x1-x0)/2; x0,x1=c-h,c+h
    return m.group(0)[:m.start(5)-m.start(0)]+f"{x0:.4f} {y0:.4f} {x1:.4f} {y1:.4f} ;"
open(dst,"w").write(pat.sub(mv,L)); print("widened",rep)
