import pickle,collections,re,json,sys
m=pickle.load(open(sys.argv[1],'rb')); I=m['insts']
CX,CY=16492.144,12989.5
def fam(bid): return re.sub(r'\d+', '#', re.sub(r'(_\d+)?(_e)?(_[twqr]\d+(n\d+)?)*$', '', bid))[:28]
def logical(bid): return re.sub(r'(_\d+)?(_e)?(_[twqr]\d+(n\d+)?)*$', '', bid)
def quad(n):
    v=I[n]; x=v[2]+v[4]/2; y=v[3]+v[5]/2
    return ('N' if y>CY else 'S')+('E' if x>CX else 'W')
def kind(n): return I[n][1]
L=collections.defaultdict(lambda: dict(bits=0,ends=collections.Counter(),cls=None,hops=0))
for bid,cls,bits,eps in m['buses']:
    if cls in ('clock_trunk','reset_tree'): continue
    lg=logical(bid); r=L[lg]; r['bits']=max(r['bits'],bits); r['cls']=cls; r['hops']+=1
    for e in eps:
        if e[0] in I and I[e[0]][1]!='waypoint': r['ends'][e[0]]+=1
# hub demand per family from segs (L shapes, half bits each) inside HUB rect
HUB=(11000,7000,21500,20000); HOT=(12000,14000,15000,17000)
def inrect_len(x1,y1,x2,y2,R):
    # two L shapes: (x1,y1)->(x2,y1)->(x2,y2) and (x1,y1)->(x1,y2)->(x2,y2)
    def hseg(y,xa,xb):
        if not (R[1]<=y<=R[3]): return 0
        a,b=sorted((xa,xb)); return max(0,min(b,R[2])-max(a,R[0]))
    def vseg(x,ya,yb):
        if not (R[0]<=x<=R[2]): return 0
        a,b=sorted((ya,yb)); return max(0,min(b,R[3])-max(a,R[1]))
    return 0.5*(hseg(y1,x1,x2)+vseg(x2,y1,y2)+vseg(x1,y1,y2)+hseg(y2,x1,x2))
hubd=collections.Counter(); hotd=collections.Counter(); totd=collections.Counter()
for bid,cls,bits,x1,y1,x2,y2 in m['segs']:
    lg=logical(bid)
    hubd[lg]+=bits*inrect_len(x1,y1,x2,y2,HUB)/1000; hotd[lg]+=bits*inrect_len(x1,y1,x2,y2,HOT)/1000
    totd[lg]+=bits*(abs(x2-x1)+abs(y2-y1))/1000
rows=[]
for lg,r in L.items():
    ends=list(r['ends'])
    rows.append(dict(bus=lg,fam=fam(lg),cls=r['cls'],bits=r['bits'],ends=ends,
        masters=sorted(set(I[e][0] for e in ends)),quads=sorted(set(quad(e) for e in ends)),
        hub_bitmm=round(hubd[lg]),hot_bitmm=round(hotd[lg]),tot_bitmm=round(totd[lg])))
json.dump(rows,open(sys.argv[2],'w'),indent=0)
H=sum(hubd.values()); T=sum(hotd.values())
print('logical buses',len(rows),'hub bit-mm',round(H),'hot bit-mm',round(T))
# family aggregation
F=collections.defaultdict(lambda: dict(n=0,bits=0,hub=0,hot=0,tot=0,ends=collections.Counter(),xq=0,cls=collections.Counter()))
for r in rows:
    f=F[r['fam']]; f['n']+=1; f['bits']+=r['bits']; f['hub']+=r['hub_bitmm']; f['hot']+=r['hot_bitmm']; f['tot']+=r['tot_bitmm']; f['cls'][r['cls']]+=1
    for e in r['ends']: f['ends'][I[e][0]]+=1
    if len(r['quads'])>1: f['xq']+=r['bits']
for k,f in sorted(F.items(),key=lambda t:-t[1]['hub'])[:60]:
    print(f"{k:28s} n={f['n']:4d} bits={f['bits']:7d} xq={f['xq']:7d} hub={f['hub']/H*100:5.1f}% hot={f['hot']/T*100:5.1f}% cls={dict(f['cls'])} ends={dict(f['ends'].most_common(4))}")
