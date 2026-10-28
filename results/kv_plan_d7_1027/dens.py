import re,collections,sys
L=open(sys.argv[1]).read()
W,H=map(float,re.search(r"SIZE (\S+) BY (\S+)",L).groups())
pins=re.findall(r"PIN (\S+)\n(.*?)END \1",L,re.S)
face=collections.defaultdict(list); st=collections.defaultdict(list)
for n,b in pins:
    r=re.search(r"LAYER (\S+) ;\s+RECT ([^;]+);",b); lay=r.group(1)
    x0,y0,x1,y1=map(float,r.group(2).split()); cx,cy=(x0+x1)/2,(y0+y1)/2
    m=re.match(r"ot_s_(ft\d+_\d+)_([dq])\[(\d+)\]",n)
    if m: st[m.group(1)].append((cx,cy)); continue
    f='W' if x0<0.3 else 'E' if x1>W-0.3 else 'S' if y0<0.3 else 'N' if y1>H-0.3 else None
    if f: face[(f,re.sub(r"\[\d+\]$","",n))].append((cx,cy,lay))
print("tile",W,H)
rows=[]
for (f,bus),v in face.items():
    c=[p[1] if f in 'EW' else p[0] for p in v]; lo,hi=min(c),max(c); n=len(v)
    lays=collections.Counter(p[2] for p in v)
    rows.append((n/max(hi-lo,0.05),f,bus,n,lo,hi,dict(lays)))
rows.sort(reverse=True)
print("face buses >=8 b/um (bits>=16):")
for r in rows:
    if r[0]>=8 and r[3]>=16: print("  %5.1f b/um %s %-28s %4d bits [%.1f,%.1f] %s"%r)
print("stations: pins per um2 of bbox (d+q), top")
s=[]
for k,v in st.items():
    xs=[a[0] for a in v]; ys=[a[1] for a in v]; w=max(xs)-min(xs)+2.16; h=max(ys)-min(ys)+0.27
    s.append((len(v)/(2*(w+h)),k,len(v)//2,min(xs),min(ys),w,h))
s.sort(reverse=True)
for r in s[:15]: print("  %5.1f nets/um-perim %-9s %4d b at (%.0f,%.0f) %.1fx%.1f"%r)
