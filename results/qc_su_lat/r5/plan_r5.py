#!/usr/bin/env python3
"""QC-SU-LAT R5 (12.8b/c/d, 12.2a1): EQUAL-STRUCTURE channel H-tree, plan-computed before build.
entry root -> 4 plan islands (fixed) -> 4 B nodes each -> 4 leaf drivers each (64 leaves, equal load).
Every level: all edges get the SAME real wire length (short edges take a legal detour through a waypoint,
maze-routed around the SRAMs) and the SAME repeater count; branch fanout identical (4/4).  So every
root->leaf path is the same cell chain over the same wire lengths by construction.  No measurement input.
"""
import json,math,sys,collections
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent));import lib
geo,out=sys.argv[1],sys.argv[2]
G=0.54  # grid step um
sinks=[];macros=[]
for l in open(geo):
  f=l.split()
  if not f:continue
  if f[0]=='CORE':core=tuple(map(float,f[1:5]))
  if f[0]=='PIN' and f[1]=='ck':entry=(float(f[2]),float(f[3]))
  if f[0]=='SINK':sinks.append((float(f[1]),float(f[2]),f[4],f[5]))
  if f[0]=='MACRO':macros.append((f[1],tuple(map(float,f[3:7])),(float(f[8]),float(f[9]))))
ISL=[(108.0,99.36),(194.4,17.28),(259.2,112.32),(241.92,198.72)]   # plan island sites (pushdown cells ot_ms_Q*_nd)
NX=int((core[2]-core[0])/G);NY=int((core[3]-core[1])/G)
HALO=2.2
def blocked(i,j):
  x=core[0]+i*G;y=core[1]+j*G
  return any(r[0]-HALO<x<r[2]+HALO and r[1]-HALO<y<r[3]+HALO for _,r,_ in macros)
B=[[blocked(i,j) for j in range(NY+1)] for i in range(NX+1)]
def cell(p):
  i=min(NX,max(0,round((p[0]-core[0])/G)));j=min(NY,max(0,round((p[1]-core[1])/G)))
  if not B[i][j]:return (i,j)
  for r in range(1,400):
    for di in range(-r,r+1):
      for dj in (-r,r):
        for a,b in ((i+di,j+dj),(i+dj,j+di)):
          if 0<=a<=NX and 0<=b<=NY and not B[a][b]:return (a,b)
def xy(c):return (round(core[0]+c[0]*G,3),round(core[1]+c[1]*G,3))
_bfs={}
def bfs(c):
  if c in _bfs:return _bfs[c]
  D=[[-1]*(NY+1) for _ in range(NX+1)];P={};D[c[0]][c[1]]=0;q=collections.deque([c])
  while q:
    a,b=q.popleft()
    for na,nb in ((a+1,b),(a-1,b),(a,b+1),(a,b-1)):
      if 0<=na<=NX and 0<=nb<=NY and not B[na][nb] and D[na][nb]<0:D[na][nb]=D[a][b]+1;P[(na,nb)]=(a,b);q.append((na,nb))
  _bfs[c]=(D,P);return _bfs[c]
def md(a,b):return bfs(a)[0][b[0]][b[1]]*G
def path(a,b):  # cells from a to b
  D,P=bfs(b);out=[a];c=a
  while c!=b:
    # step to neighbour with smaller distance to b, prefer straight
    a0,b0=c;best=None
    for n in ((a0+1,b0),(a0-1,b0),(a0,b0+1),(a0,b0-1)):
      if 0<=n[0]<=NX and 0<=n[1]<=NY and D[n[0]][n[1]]==D[a0][b0]-1:best=n;break
    c=best;out.append(c)
  return out
# ---- equal-load assignment (power diagram on maze distance) ----
def balanced(points,centres,dist,iters=400):
  n=len(points);k=len(centres);tgt=[n//k+(1 if i<n%k else 0) for i in range(k)]
  Dm=[[dist(p,c) for c in centres] for p in points];w=[0.0]*k
  for it in range(iters):
    a=[min(range(k),key=lambda c:Dm[i][c]+w[c]) for i in range(n)];cnt=collections.Counter(a)
    if all(cnt[c]==tgt[c] for c in range(k)):break
    for c in range(k):w[c]+=0.5*(cnt[c]-tgt[c])/max(1,n/k)*20/(1+it/50)
  # exact fix-up: move cheapest surplus points
  cnt=collections.Counter(a)
  while any(cnt[c]>tgt[c] for c in range(k)):
    best=None
    for i in range(n):
      if cnt[a[i]]<=tgt[a[i]]:continue
      for c in range(k):
        if cnt[c]<tgt[c]:
          cost=Dm[i][c]-Dm[i][a[i]]
          if best is None or cost<best[0]:best=(cost,i,c)
    _,i,c=best;cnt[a[i]]-=1;cnt[c]+=1;a[i]=c
  return [[points[i] for i in range(n) if a[i]==c] for c in range(k)]
scell={s:cell(s[:2]) for s in sinks}
isl=[cell(p) for p in ISL]
for c in isl:bfs(c)
Q=balanced(sinks,isl,lambda s,c:md(c,scell[s]))
def kmeans_bal(pts,k,seed):
  cs=[cell(p) for p in seed]
  for _ in range(6):
    grp=balanced(pts,list(range(k)),lambda s,c:abs(s[0]-xy(cs[c])[0])+abs(s[1]-xy(cs[c])[1]),iters=300)
    cs=[cell((sorted(p[0] for p in g)[len(g)//2],sorted(p[1] for p in g)[len(g)//2])) for g in grp]
  return grp
def seeds(pts,k):
  xs=sorted(p[0] for p in pts);ys=sorted(p[1] for p in pts)
  if xs[-1]-xs[0]>ys[-1]-ys[0]:
    srt=sorted(pts,key=lambda p:p[0])
  else:srt=sorted(pts,key=lambda p:p[1])
  return [srt[int((i+.5)*len(srt)/k)][:2] for i in range(k)]
tree=[]  # (qi,bi,li,leafsinks)
for qi,qs in enumerate(Q):
  for bi,bs in enumerate(kmeans_bal(qs,4,seeds(qs,4))):
    for li,ls in enumerate(kmeans_bal(bs,4,seeds(bs,4))):tree.append((qi,bi,li,ls))
def centroid(g):return cell((sum(p[0] for p in g)/len(g),sum(p[1] for p in g)/len(g)))
leafc={(q,b,l):centroid(ls) for q,b,l,ls in tree}
# B node: legal cell minimising max maze distance to its 4 leaf centroids
Bm={}
for q in range(4):
  for b in range(4):
    ls=[leafc[(q,b,l)] for l in range(4)];[bfs(c) for c in ls]
    cx=sum(c[0] for c in ls)/4;cy=sum(c[1] for c in ls)/4;best=None
    for i in range(max(0,int(cx)-80),min(NX,int(cx)+80)+1,2):
      for j in range(max(0,int(cy)-80),min(NY,int(cy)+80)+1,2):
        if B[i][j]:continue
        v=max(bfs(c)[0][i][j] for c in ls)
        if v>=0 and (best is None or v<best[0]):best=(v,(i,j))
    Bm[(q,b)]=best[1]
ent=cell(entry)
L1=[md(ent,isl[q]) for q in range(4)]
T1=max(L1);T2=max(md(isl[k[0]],v) for k,v in Bm.items())
def on_ring(src,T,near):
  """legal cell at maze distance T (+-1 cell) from src, nearest (Manhattan) to near."""
  D=bfs(src)[0];t=round(T/G);best=None
  for i in range(NX+1):
    for j in range(NY+1):
      if D[i][j]>=0 and abs(D[i][j]-t)<=1:
        e=abs(i-near[0])+abs(j-near[1])
        if best is None or e<best[0]:best=(e,(i,j))
  return best[1]
Bc=dict(Bm)
T3=max(md(Bc[k[:2]],v) for k,v in leafc.items())
leafd={k:on_ring(Bc[k[:2]],T3,v) for k,v in leafc.items()}
L2={k:md(isl[k[0]],v) for k,v in Bc.items()};L3={k:md(Bc[k[:2]],v) for k,v in leafd.items()}
SMAX=float(sys.argv[3]) if len(sys.argv)>3 else 70.0
K1,K2,K3=[max(1,math.ceil(t/SMAX)) for t in (T1,T2,T3)]
def exact_points(a,b,T,k):
  """k-1 repeater cells so every segment is a SHORTEST legal path of length T/k (GRT cannot shortcut)."""
  s=round(T/G/k);Db=bfs(b)[0]
  def ring(src,t):
    D=bfs(src)[0];return [(x,y) for x in range(0,NX+1) for y in range(0,NY+1) if D[x][y]>=0 and abs(D[x][y]-t)<=1]
  def last(p):
    Dp=bfs(p)[0];best=None
    for x in range(NX+1):
      for y in range(NY+1):
        if Dp[x][y]>=0 and abs(Dp[x][y]-s)<=1 and Db[x][y]>=0:
          e=abs(Db[x][y]-s)
          if best is None or e<best[0]:best=(e,(x,y))
    return best
  if k==1:return []
  if k==2:
    e,p=last(a)
    if e>2:print('WARN exact',a,b,T,k,e*G)
    return [p]
  assert k==3
  cand=sorted((abs(Db[x][y]-2*s)+(1000 if Db[x][y]>2*s+1 else 0),(x,y)) for x,y in ring(a,s) if Db[x][y]>=0)
  for _,p in cand[::max(1,len(cand)//60)][:60] if cand[0][0]>2 else cand[:1]:
    e,q=last(p)
    if e<=2:return [p,q]
  print('WARN exact3',a,b,T);return [p,q]
nodes=[]
REP='BUFx16f_ASAP7_75t_R';BIG='BUFx24_ASAP7_75t_R'
seglen=collections.defaultdict(list)
def chain(pname,pc,cname,cc,T,k,level):
  pts=exact_points(pc,cc,T,k);prev=pname;allp=[pc]+pts+[cc]
  segs=[md(allp[i],allp[i+1]) for i in range(len(allp)-1)]
  for i,c in enumerate(pts):
    n=f'{cname}_r{i}';nodes.append((n,prev,c,REP));prev=n
  seglen[level].append((cname,round(T,1),[round(s,1) for s in segs]))
  return prev,segs
paths={}
for q in range(4):
  par,s1=chain('root',ent,f'Q{q}',isl[q],T1,K1,1);nodes.append((f'Q{q}',par,isl[q],BIG))
  for b in range(4):
    par,s2=chain(f'Q{q}',isl[q],f'Q{q}B{b}',Bc[(q,b)],T2,K2,2);nodes.append((f'Q{q}B{b}',par,Bc[(q,b)],BIG))
    for l in range(4):
      par,s3=chain(f'Q{q}B{b}',Bc[(q,b)],f'Q{q}B{b}L{l}',leafd[(q,b,l)],T3,K3,3)
      paths[(q,b,l)]=(par,s1,s2,s3)
leaves=[]
for q,b,l,ls in tree:leaves.append((f'Q{q}B{b}L{l}',paths[(q,b,l)][0],leafd[(q,b,l)],ls))
# ---------- analytic NLDM model (TT/FF), plan geometry only ----------
LIBS={'TT':lib.cells(str(Path(__file__).parent/'invbuf_tt.lib'),[REP,BIG]),'FF':lib.cells(str(Path(__file__).parent/'invbuf_ff.lib'),[REP,BIG])}
FFC={'TT':0.474736,'FF':0.522010}
r=0.5*(1.80365e-2+1.89935e-2)*0.8; c=0.5*(1.78475e-1+1.64264e-1)*0.9
def interp(tab,s,C):
  i1,i2,v=tab
  def idx(a,x):
    for k in range(len(a)-1):
      if x<=a[k+1]:return k
    return len(a)-2
  a=idx(i1,s);b=idx(i2,C);ta=(s-i1[a])/(i1[a+1]-i1[a]);tb=(C-i2[b])/(i2[b+1]-i2[b])
  return (v[a][b]*(1-ta)*(1-tb)+v[a+1][b]*ta*(1-tb)+v[a][b+1]*(1-ta)*tb+v[a+1][b+1]*ta*tb)
def stage(corner,cellname,sin,branches):  # branches: list of (wire um, Cpin)
  L=LIBS[corner][cellname];C=sum(c*w+cp for w,cp in branches)
  d=0.5*(interp(L['rise'],sin,C)+interp(L['fall'],sin,C));so=interp(L['trise'],sin,C)
  wd=[r*w*(c*w/2+cp) for w,cp in branches]
  return d,so,wd,C
def mst(ptsl):
  n=len(ptsl);inn=[False]*n;dd=[1e18]*n;dd[0]=0;tot=0
  for _ in range(n):
    u=min((i for i in range(n) if not inn[i]),key=lambda i:dd[i]);inn[u]=True;tot+=dd[u]
    for v in range(n):
      if not inn[v]:
        e=abs(ptsl[u][0]-ptsl[v][0])+abs(ptsl[u][1]-ptsl[v][1])
        if e<dd[v]:dd[v]=e
  return tot
pred={}
for corner in ('TT','FF'):
  cin={k:LIBS[corner][k]['cin'] for k in (REP,BIG)};res={}
  for (q,b,l),(par,s1,s2,s3) in paths.items():
    t=0;s=20.0
    levels=[(BIG,s1,4),(BIG,s2,4),(BIG,s3,4)]  # root, Q, B drive fanout-4 first segments
    for lv,(drv,segs,fo) in enumerate(levels):
      for i,w in enumerate(segs):
        dcell=drv if i==0 else REP;nxt=REP if i<len(segs)-1 else BIG
        br=[(w,cin[nxt])]*(fo if i==0 else 1)
        d,s,wd,_=stage(corner,dcell,s,br);t+=d+wd[0]
    ls=[x for x in tree if x[:3]==(q,b,l)][0][3];lc=xy(leafd[(q,b,l)])
    wl=mst([lc]+[p[:2] for p in ls]);C=c*wl+len(ls)*FFC[corner]
    L=LIBS[corner][BIG];d=0.5*(interp(L['rise'],s,C)+interp(L['fall'],s,C))
    rad=sum(abs(p[0]-lc[0])+abs(p[1]-lc[1]) for p in ls)/len(ls)
    t+=d+r*rad*C/2
    res[f'Q{q}B{b}L{l}']=round(t,2)
  v=list(res.values());pred[corner]=dict(mean=round(sum(v)/len(v),2),min=min(v),max=max(v),window=round(max(v)-min(v),2),leaf=res)
# macros: designed leaf stage (BUFx24) on the input net of the nearest leaf driver
mac=[]
for name,rect,ck in macros:
  site=xy(cell((ck[0]+2.2,ck[1])));lf=min(leaves,key=lambda L:abs(xy(L[2])[0]-site[0])+abs(xy(L[2])[1]-site[1]));mac.append((name,lf[0],site))
def quote(s):return '{'+s+'}'
fixed=[('ot_ms_root',BIG,xy(ent))]+[(f'ot_ms_Q{q}_nd',BIG,xy(isl[q])) for q in range(4)]
L=['# QC-SU-LAT R5 equal-structure channel H-tree (plan-computed, no measurement input)','set ot_ms_port ck',
   'set ot_ms_root {%.3f %.3f}'%xy(ent),'set ot_h_entry_n 0','set ot_h_fixed {']
L+=[' {%s %s %.3f %.3f}'%(n,cl,*p) for n,cl,p in fixed]+['}','set ot_ms_tree {']
L+=[' {%s %s %.3f %.3f %s}'%(n,p,*xy(cc),cl) for n,p,cc,cl in nodes]+['}','set ot_ms_leaves {']
for n,p,cc,ls in leaves:
  L.append(' {%s %s {%.3f %.3f} {%s} %s}'%(n,p,*xy(cc),' '.join('{'+quote(s[2])+' '+quote(s[3])+'}' for s in ls),BIG))
L+=['}','set ot_ms_macros {']+[' {%s %s {%.3f %.3f}}'%(quote(n),l,*s) for n,l,s in mac]+['}']
Path(out).write_text('\n'.join(L)+'\n')
rep=dict(scope='PLAN MODEL ONLY (liberty NLDM + setRC x rc_cal 0.8/0.9, no measured input); UNCHECKED',entry=xy(ent),islands=[xy(c) for c in isl],
  quadrant_load=[len(q) for q in Q],leaf_load=[min(len(x[3]) for x in tree),max(len(x[3]) for x in tree)],
  level_len_um=dict(T1=T1,T2=T2,T3=T3),shortest=dict(L1=L1,L2=[min(L2.values()),max(L2.values())],L3=[min(L3.values()),max(L3.values())]),
  repeaters_per_edge=dict(K1=K1-1,K2=K2-1,K3=K3-1),stages_per_path=3+(K1-1)+(K2-1)+(K3-1)+1,n_buffers=len(nodes)+len(leaves)+len(mac)+1,
  seg=dict(seglen),pred={k:{kk:vv for kk,vv in v.items() if kk!='leaf'} for k,v in pred.items()},pred_leaf=pred,
  nodes=[(n,p,xy(cc),cl) for n,p,cc,cl in nodes],leaves=[(n,p,xy(cc),len(ls)) for n,p,cc,ls in leaves],macros=mac)
Path(out+'.json').write_text(json.dumps(rep,indent=1))
print(json.dumps({k:rep[k] for k in ('quadrant_load','leaf_load','level_len_um','shortest','repeaters_per_edge','stages_per_path','n_buffers','pred')},indent=0))
