"""Graph-home solver for NK V1L/ICG2 (analysis only). Nodes: seq cells + ICG cells. Fixed: face flops (FIRM at faces),
macros. Edges: launch(seq|macro) -> capture(seq|ICG|macro) through combinational cones (geom_rules kinds).
Minimal-move projection in (u=x+y, v=x-y) so every leg <= RT; homes pushed out of macro halos; density-capped bins."""
import sys,re,json,math
from collections import Counter,defaultdict,deque
sys.path.insert(0,'/home/ubuntu/OpenTallas/tools/autopilot')
import geom_rules as G
geom,face,out=sys.argv[1:4]
RT=float(sys.argv[4]) if len(sys.argv)>4 else 395.0
HALO=4.32+1.0
D=G.Design(geom)
nm=lambda c:D.cells[c][6].replace('\\','')
faceset={l.split('\t')[0].replace('\\','') for l in open(face) if l.strip()}
seq={c for c,v in D.cells.items() if v[0]=='S'}
icg={c for c,v in D.cells.items() if v[0]=='K' and v[1].startswith('ICG')}
mac={c for c,v in D.cells.items() if v[0]=='M'}
comb={c for c,v in D.cells.items() if v[0] in 'BLK'}-icg
launch=seq|mac; sinkset=seq|icg|mac
succ=defaultdict(list);indeg=Counter()
for c in comb:
    for n in D.drives.get(c,[]):
        for s in D.nets[n][2]:
            if s[0]=='i' and not s[2] and s[1] in comb: succ[c].append(s[1]);indeg[s[1]]+=1
src=defaultdict(set);E=set()
for c in launch:
    for n in D.drives.get(c,[]):
        for s in D.nets[n][2]:
            if s[0]!='i' or s[2]: continue
            if s[1] in sinkset: E.add((c,s[1]))
            elif s[1] in comb: src[s[1]].add(c)
dq=deque(c for c in comb if indeg[c]==0)
while dq:
    c=dq.popleft();e=src.get(c,set())
    for n in D.drives.get(c,[]):
        for s in D.nets[n][2]:
            if s[0]!='i' or s[2]: continue
            if s[1] in sinkset:
                for a in e: E.add((a,s[1]))
            elif s[1] in comb: src[s[1]]|=e
    for t in succ.get(c,[]):
        indeg[t]-=1
        if indeg[t]==0: dq.append(t)
E={(a,b) for a,b in E if a!=b and not (a in mac and b in mac)}
nb=defaultdict(set)
for a,b in E: nb[a].add(b);nb[b].add(a)
pos={c:G.ctr(D.cells[c]) for c in seq|icg}
box={c:D.cells[c][2:6] for c in mac}
fixed={c for c in seq if nm(c) in faceset}
# reset entry: rst_n pin first-level register -> home at the pin (<=30 um budget), keep it movable only inside that diamond
rp=[p for p in D.pins if p['name']=='rst_n'][0]
rst_entry=[c for c in seq if nm(c).endswith('g_rst_native.q$_DFF_P_')]
RST_R=float(sys.argv[5]) if len(sys.argv)>5 else 25.0
pinanch={c:((rp["x"],rp["y"]),RST_R) for c in rst_entry}
core=D.extra['core']
def mpt(m,x,y):
    x0,y0,x1,y1=box[m];return (min(max(x,x0),x1),min(max(y,y0),y1))
def inmac(x,y):
    for m,(x0,y0,x1,y1) in box.items():
        if x0-HALO<x<x1+HALO and y0-HALO<y<y1+HALO: return m
    return None
def narrow(x,y):
    Lm=[b for b in box.values() if b[1]-1<=y<=b[3]+1]
    lx=max([b[2] for b in Lm if b[2]<=x],default=0);rx=min([b[0] for b in Lm if b[0]>=x],default=D.die[2])
    Bm=[b for b in box.values() if b[0]-1<=x<=b[2]+1]
    by=max([b[3] for b in Bm if b[3]<=y],default=0);ty=min([b[1] for b in Bm if b[1]>=y],default=D.die[3])
    return (rx-lx)<=12 or (ty-by)<=12
RSTFAM=re.compile(r'(g_rst_native\.q|t_out_reset_q|fy_q|mis_q|g_lrr\.rq)\$')
CUR=[None]
def legal(x,y): return inmac(x,y) is None and not (NOGAP and CUR[0] not in rstset and narrow(x,y))
NOGAP=len(sys.argv)>6 and sys.argv[6]=='nogap'
def street0(x,y):
    x,y=street1(x,y)
    if legal(x,y): return x,y
    b=2.16
    for r in range(1,80):
        for dx in range(-r,r+1):
            for dy in sorted({-(r-abs(dx)),r-abs(dx)}):
                cx,cy=x+dx*b,y+dy*b
                if core[0]<cx<core[2] and core[1]<cy<core[3] and legal(cx,cy): return cx,cy
    return x,y
def street1(x,y):
    x=min(max(x,core[0]+1),core[2]-1);y=min(max(y,core[1]+1),core[3]-1)
    for _ in range(4):
        m=inmac(x,y)
        if m is None: return x,y
        x0,y0,x1,y1=box[m];c=[(x0-HALO,y),(x1+HALO,y),(x,y0-HALO),(x,y1+HALO)]
        c=[p for p in c if core[0]<p[0]<core[2] and core[1]<p[1]<core[3]]
        x,y=min(c,key=lambda p:abs(p[0]-x)+abs(p[1]-y))
    return x,y
def P(c,ref=None):
    if c in mac: return mpt(c,*ref)
    return pos[c]
movable=[c for c in seq|icg if c not in fixed]
rstset={c for c in movable if RSTFAM.search(nm(c))}
def viol(c):
    x,y=pos[c]
    for o in nb[c]:
        ox,oy=P(o,(x,y))
        if abs(ox-x)+abs(oy-y)>RT: return True
    if c in pinanch:
        (px,py),r=pinanch[c]
        if abs(px-x)+abs(py-y)>r: return True
    return False
work=deque(c for c in movable if viol(c));inq=set(work);it=0
while work and it<4000000:
    c=work.popleft();inq.discard(c);it+=1
    CUR[0]=c
    x,y=pos[c];ul,uh,vl,vh=-1e9,1e9,-1e9,1e9
    cons=[(P(o,(x,y)),RT) for o in nb[c]]
    if c in pinanch: cons.append(pinanch[c])
    for (ox,oy),r in cons:
        ul=max(ul,ox+oy-r);uh=min(uh,ox+oy+r);vl=max(vl,ox-oy-r);vh=min(vh,ox-oy+r)
    u,v=x+y,x-y
    u=(ul+uh)/2 if ul>uh else min(max(u,ul),uh)
    v=(vl+vh)/2 if vl>vh else min(max(v,vl),vh)
    nx,ny=street0((u+v)/2,(u-v)/2)
    if abs(nx-x)+abs(ny-y)>1e-3:
        pos[c]=(nx,ny)
        for o in nb[c]:
            if o in pos and o not in fixed and o not in inq and viol(o): work.append(o);inq.add(o)
        if viol(c) and c not in inq and it<3000000: work.append(c);inq.add(c)
print('iterations',it,'still-violating queue',len(work))
# density: cap FFs per 4.32x4.32 um bin at the GPL result's own p99 FF occupancy (reference = the failed placement itself)
B=4.32;occ=Counter()
o0=Counter((int(G.ctr(D.cells[c])[0]//B),int(G.ctr(D.cells[c])[1]//B)) for c in seq|icg)
vals=sorted(o0.values());CAP=vals[int(.99*len(vals))]
print('GPL FF/bin p50/p99/max',vals[len(vals)//2],CAP,vals[-1])
for c in fixed: x,y=pos[c];occ[(int(x//B),int(y//B))]+=1
def ok(c,x,y):
    for o in nb[c]:
        ox,oy=P(o,(x,y))
        if abs(ox-x)+abs(oy-y)>RT: return False
    if c in pinanch:
        (px,py),r=pinanch[c]
        if abs(px-x)+abs(py-y)>r: return False
    return True
moved=0;bad=0
for c in sorted(movable,key=lambda c:-len(nb[c])):
    CUR[0]=c
    x,y=pos[c];bx,by=int(x//B),int(y//B)
    if occ[(bx,by)]<CAP and (legal(x,y) or abs(x-G.ctr(D.cells[c])[0])+abs(y-G.ctr(D.cells[c])[1])<0.5): occ[(bx,by)]+=1;continue
    best=None;fall=None
    for r in range(1,60):
        for dx in range(-r,r+1):
            for dy in sorted({-(r-abs(dx)),r-abs(dx)}):
                k=(bx+dx,by+dy);cx,cy=(k[0]+.5)*B,(k[1]+.5)*B
                if occ[k]>=CAP or not(core[0]<cx<core[2] and core[1]<cy<core[3]) or not legal(cx,cy): continue
                if fall is None: fall=k
                if ok(c,cx,cy): best=k;break
            if best: break
        if best: break
    if best is None: best=fall;bad+=1
    occ[best]+=1;pos[c]=((best[0]+.5)*B,(best[1]+.5)*B);moved+=1
print('density spread moved',moved,'without a leg-legal free bin',bad,'final FF/bin max',max(occ.values()))
# rewrite cells to homes and run the AUTO-GEOM r2r / relay rules on the repaired geometry
orig={c:G.ctr(D.cells[c]) for c in pos}
for c,(x,y) in pos.items():
    t=D.cells[c];w=(t[4]-t[2])/2;h=(t[5]-t[3])/2
    D.cells[c]=(t[0],t[1],x-w,y-h,x+w,y+h,t[6])
r=G.r2r_metrics(D);rl=G.relay_metrics(D);pr=G.pin_reg_metrics(D,re.compile(G.STRAP_RE_DEFAULT),frozenset({'ck'}))
legs=[]
for a,b in E:
    pa=P(a,P(b,(0,0)) if b not in mac else (0,0)) if a not in mac else None
    if a in mac: pb=P(b);pa=mpt(a,*pb)
    elif b in mac: pa=P(a);pb=mpt(b,*pa)
    else: pa=P(a);pb=P(b)
    legs.append((abs(pa[0]-pb[0])+abs(pa[1]-pb[1]),a,b))
legs.sort(reverse=True)
kind=lambda c:'M' if c in mac else ('ICG' if c in icg else 'FF')
lc=Counter((kind(a),kind(b)) for d,a,b in legs if d>405)
mv=sorted(((abs(pos[c][0]-orig[c][0])+abs(pos[c][1]-orig[c][1]),c) for c in movable),reverse=True)
asr=[]
fr=[D.pin_net[rp['k']]];seen=set(fr)
while fr:
    nf=[]
    for nn in fr:
        for s in D.nets[nn][2]:
            if s[0]=='i' and not s[2]:
                if D.kind(s[1])=='S': asr.append(s[1])
                elif D.kind(s[1])=='B':
                    for o in D.drives.get(s[1],[]):
                        if o not in seen: seen.add(o);nf.append(o)
    fr=nf
ad=sorted(abs(pos[c][0]-rp['x'])+abs(pos[c][1]-rp['y']) for c in asr)
icgd=[]
for c in icg:
    for o in nb[c]:
        if o in pos: icgd.append(abs(pos[o][0]-pos[c][0])+abs(pos[o][1]-pos[c][1]))
res=dict(RT=RT,edges=len(E),nodes=len(pos),fixed_face=len(fixed),movable=len(movable),
 r2r_max=r['r2r_max'],r2r_gt405=r['r2r_captures_gt405'],r2r_captures=r['r2r_captures'],r2r_worst=r['r2r_worst'],
 relay=rl,pin_reg_max=pr['pin_reg_max'],pin_reg_p90=pr['pin_reg_p90'],pin_reg_worst=pr['pin_reg_worst'],
 graph_legs_gt405=sum(1 for d,a,b in legs if d>405),graph_legs_gt405_by_kind={f'{k[0]}->{k[1]}':v for k,v in lc.items()},graph_leg_max=round(legs[0][0],2),
 graph_worst=[[round(d,1),nm(a),nm(b)] for d,a,b in legs[:12]],
 icg_enable_leg_max=round(max(icgd),2) if icgd else None,
 rst_n_asr_direct=len(asr),rst_n_asr_dist_max=round(ad[-1],1),rst_n_asr_gt150=sum(d>150 for d in ad),rst_n_asr_gt405=sum(d>405 for d in ad),
 moved_cells=sum(1 for d,c in mv if d>0.5),move_p90=round(mv[int(.1*len(mv))][0],1),move_max=round(mv[0][0],1),
 moved_by_family=Counter(re.sub(r'\[\d+\]','[]',nm(c)).split('.')[-1][:60] for d,c in mv if d>20).most_common(25))
json.dump(res,open(out+'.json','w'),indent=1)
with open(out+'.tsv','w') as f:
    for c in movable:
        if abs(pos[c][0]-orig[c][0])+abs(pos[c][1]-orig[c][1])>0.5 or kind(c)=='ICG' or c in pinanch:
            f.write(f"{D.cells[c][6]}\t{pos[c][0]:.3f}\t{pos[c][1]:.3f}\t{kind(c)}\n")
json.dump({'homes':{D.cells[c][6]:[round(pos[c][0],3),round(pos[c][1],3)] for c in movable},'orig':{D.cells[c][6]:[round(orig[c][0],3),round(orig[c][1],3)] for c in movable}},open(out+'_all.json','w'))
print(json.dumps({k:v for k,v in res.items() if k not in('graph_worst','moved_by_family')},indent=0));print(json.dumps(res['graph_worst'][:8]));print(res['moved_by_family'])
