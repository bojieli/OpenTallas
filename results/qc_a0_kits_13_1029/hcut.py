import sys,collections
cells={};nets=[];pins={}
for ln in open(sys.argv[1]):
    f=ln.rstrip('\n').split('\t')
    if f[0]=='C': cells[f[1]]=(f[2],f[3],(float(f[4])+float(f[6]))/2,(float(f[5])+float(f[7]))/2,f[8],float(f[4]),float(f[5]),float(f[6]),float(f[7]))
    elif f[0]=='N': nets.append(f[1:])
    elif f[0]=='P': pins[f[1]]=(f[2],f[3],float(f[6]),float(f[7]))
y0,y1=658.0,1153.44
# trace node-bus segments: nets connected (through B/L cells, up to 8 hops) between the node macro and W-face pins / W pin regs (x<20)
node=[k for k,c in cells.items() if c[1]=='ot_qwen_tile_node']
node=node[0] if node else None
term_xy=lambda t:(pins[t[1:]][2],pins[t[1:]][3]) if t.startswith('p') else (cells[t.rstrip('c')[1:]][2],cells[t.rstrip('c')[1:]][3])
def box(n):
    xs=[];ys=[]
    for t in n[1:]:
        if t=='-' : continue
        try: x,y=term_xy(t)
        except KeyError: continue
        if node and t.startswith('i') and t.rstrip('c')[1:]==node: pass
        xs.append(x);ys.append(y)
    return (min(xs),min(ys),max(xs),max(ys)) if len(xs)>=2 else None
# node pin coordinates are macro centres in this dump; use the node W face x for nets touching the node
NW=cells[node][5] if node else None
nb=[]
touch=[]
for n in nets:
    if len(n)>40: continue   # skip clock/reset/high-fanout
    b=box(n)
    if not b: continue
    tn=node and any(t.startswith('i') and t.rstrip('c')[1:]==node for t in n[1:])
    if tn: b=(min(b[0],NW),b[1],max(b[2],NW) if b[2]<NW else NW,b[3])
    nb.append((b,tn))
for c in (60,100,150,200,262,300,350,385):
    tot=0;tn=0
    for b,t in nb:
        if b[0]<c<b[2] and b[3]>=y0 and b[1]<=y1:
            tot+=1; tn+=t
    print(f"cut x={c}: upper-half crossings {tot} (nets touching node {tn})")
