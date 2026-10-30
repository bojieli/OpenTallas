"""Proposed multi-root load-bin clock graph. Geometry only; no physical qualification."""
import json,math,pickle,heapq,itertools,hashlib
from pathlib import Path
from types import SimpleNamespace
P=Path('/srv/opentallas-scratch2/claude/codex-kvleaf-clock-0336');D=P/'clock_candidate';D.mkdir(exist_ok=True)
x=json.loads((P/'prepared/model_inputs.json').read_text());roots=x['die_core_roots'];W,H=x['outline_um'];halo=4.32
boxes=[]
for c in x['children']+x['real_sram_loads']:
 a,b=c['proposed_origin_um'];w,h=c['body_um'];boxes.append((a-halo,b-halo,a+w+halo,b+h+halo))
def free(p):return 0<=p[0]<=W and 0<=p[1]<=H and not any(a<p[0]<c and b<p[1]<d for a,b,c,d in boxes)
def clear(a,b):
 if a[0]!=b[0] and a[1]!=b[1]:return False
 return all(not (min(a[0],b[0])<r and max(a[0],b[0])>l and min(a[1],b[1])<t and max(a[1],b[1])>z) if a[0]!=b[0] else not(l<a[0]<r and min(a[1],b[1])<t and max(a[1],b[1])>z) for l,z,r,t in boxes)
def man(a,b):return abs(a[0]-b[0])+abs(a[1]-b[1])
def hv(a,b):
 paths=[[a,(a[0],b[1]),b],[a,(b[0],a[1]),b]]
 return next((p for p in paths if all(clear(c,d) for c,d in zip(p,p[1:]))),None)
# Rectilinear visibility through expanded body corners, reused by all clock nets.
corners=sorted(set((a,b) for l,z,r,t in boxes for a,b in ((l,z),(l,t),(r,z),(r,t)) if free((a,b))))
vis={i:[] for i in range(len(corners))}
for i,a in enumerate(corners):
 for j in range(i):
  b=corners[j];path=hv(a,b)
  if path:vis[i].append((j,man(a,b),path));vis[j].append((i,man(a,b),list(reversed(path))))
def route(a,b):
 direct=hv(a,b)
 if direct:return direct
 n=len(corners);points=corners+[a,b];edges={i:list(v) for i,v in vis.items()};edges[n]=[];edges[n+1]=[]
 for k,p in ((n,a),(n+1,b)):
  for i,c in enumerate(corners):
   q=hv(p,c)
   if q:edges[k].append((i,man(p,c),q));edges[i].append((k,man(p,c),list(reversed(q))))
 dist={n:0};prev={};todo=[(0,n)]
 while todo:
  cost,i=heapq.heappop(todo)
  if cost!=dist[i]:continue
  if i==n+1:break
  for j,w,path in edges[i]:
   if cost+w<dist.get(j,math.inf):dist[j]=cost+w;prev[j]=(i,path);heapq.heappush(todo,(cost+w,j))
 if n+1 not in dist:raise ValueError(('unroutable',a,b))
 q=[];i=n+1
 while i!=n:j,path=prev[i];q=path[:-1]+q if q else path;i=j
 return q
xs=sorted(set(r['xy_um'][0] for r in roots));ys=sorted(set(r['xy_um'][1] for r in roots));xb=[0]+[(a+b)/2 for a,b in zip(xs,xs[1:])]+[W];yb=[0]+[(a+b)/2 for a,b in zip(ys,ys[1:])]+[H]
def home(p):
 if free(p):return p
 return min(corners,key=lambda c:man(p,c))
def choose_leaf_sites(root,n):
 cx,cy=root['xy_um'];i=xs.index(cx);j=ys.index(cy)
 sites=[(round(a,3),round(b,3)) for a in range(math.ceil(xb[i]+8),math.floor(xb[i+1]-8),12) for b in range(math.ceil(yb[j]+8),math.floor(yb[j+1]-8),12) if free((a,b)) and all(free((a+u,b+v)) for u,v in ((-2,-2),(2,2),(-2,2),(2,-2)))]
 assert len(sites)>=n,(root,n,len(sites))
 # Deterministic evenly spaced load-bin anchors; these are NOT placed native FFs.
 return [sites[min(len(sites)-1,math.floor((k+.5)*len(sites)/n))] for k in range(n)]
allplans=[];geo=[]
for v in x['variants']:
 plans=[]
 for root,budget in zip(roots,v['distributed_tree']):
  nodes={};kids={};nets={};counter=itertools.count();points=choose_leaf_sites(root,budget['ff_leaves_48']);remaining=budget['proposed_soft_ff'];weighted={c:v['soft_ff_total_clock_pin_cap_fF'][c]/v['measured_parent_census']['flops'] for c in ('TT','FF')}
  for pt in points:
   n=min(48,remaining);remaining-=n;name=f'f{next(counter)}'
   sinks=[(pt[0]+(k%8-3.5)*.27,pt[1]+(k//8-2.5)*.54) for k in range(n)]
   nodes[name]={'xy':pt,'kind':'leaf','cell':'BUFx8_ASAP7_75t_R','sinks':sinks,'cpin':weighted,'role':'PROPOSED load-bin, exact counted FF; actual native FF XY unknown'}
  assert remaining==0
  for terminal in x['hard_clock_terminals']:
   if terminal['proposed_core_root']!=root['pin']:continue
   # Parent-side buffer outside the body drives the entry pin. Native child-root
   # propagation is deliberately outside this parent-only clock estimate.
   t=terminal['xy_um'];pt=home((t[0]-halo-.6,t[1]));name=f'h{next(counter)}'
   nodes[name]={'xy':pt,'kind':'macro','cell':'BUFx8_ASAP7_75t_R','sinks':[t],'cpin':terminal['cap_fF'],'role':terminal['basis'],'terminal':terminal['inst']}
  level=list(nodes)
  while len(level)>8:
   level.sort(key=lambda n:(round(nodes[n]['xy'][0]/72),nodes[n]['xy'][1],nodes[n]['xy'][0]));new=[]
   for i in range(0,len(level),8):
    group=level[i:i+8];xy=home(tuple(sum(nodes[n]['xy'][k] for n in group)/len(group) for k in (0,1)));name=f'b{next(counter)}';nodes[name]={'xy':xy,'kind':'buf','cell':'BUFx12f_ASAP7_75t_R'};kids[name]=group;new.append(name)
   level=new
  nodes['root']={'xy':tuple(root['xy_um']),'kind':'buf','cell':'BUFx24_ASAP7_75t_R'};kids['root']=level
  # Each driver->child path uses the same expanded-body visibility geometry.
  # Split long routes using fixed BUF12f repeaters, no fitting or sizing sweep.
  original=list(kids.items());paths=[]
  for parent,children in original:
   adjusted=[]
   for child in children:
    path=route(nodes[parent]['xy'],nodes[child]['xy']);length=sum(man(a,b) for a,b in zip(path,path[1:]));segments=max(1,math.ceil(length/180));seq=[parent]
    # Split by path arclength with all endpoint moves frozen in the record.
    for k in range(1,segments):
     distance=length*k/segments
     for a,b in zip(path,path[1:]):
      d=man(a,b)
      if distance<=d:
       fraction=distance/d if d else 0;xy=(a[0]+fraction*(b[0]-a[0]),a[1]+fraction*(b[1]-a[1]));break
      distance-=d
     name=f'r{next(counter)}';nodes[name]={'xy':xy,'kind':'buf','cell':'BUFx12f_ASAP7_75t_R'};seq.append(name)
    seq.append(child);adjusted.append(seq[1])
    for a,b in zip(seq[1:-1],seq[2:]):kids[a]=[b]
    paths.append({'parent':parent,'child':child,'polyline':path,'length_um':length,'inserted_repeaters':segments-1})
   kids[parent]=adjusted
  for parent,children in kids.items():
   pts=[nodes[parent]['xy']];edges=[];pin={}
   for child in children:
    path=route(nodes[parent]['xy'],nodes[child]['xy']);last=0
    for xy in path[1:]:
     idx=len(pts);pts.append(xy);edges.append((last,idx,man(pts[last],xy)));last=idx
    pin[child]=last
   nets[parent]={'pts':pts,'edges':edges,'pin':pin,'detour':1.0}
  plans.append(SimpleNamespace(nodes=nodes,kids=kids,nets=nets));geo.append({'type':v['type'],'root':root['pin'],'nodes':len(nodes),'ff':budget['proposed_soft_ff'],'paths':paths,'stage_min':None})
 allplans.append((v['type'],plans))
with (D/'graphs.pkl').open('wb') as f:pickle.dump(allplans,f)
(D/'geometry.json').write_text(json.dumps(geo,indent=2)+'\n')
print('GRAPH_PREP',[(t,sum(len(p.nodes) for p in plans)) for t,plans in allplans])
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
fig,ax=plt.subplots(figsize=(11,10));t,plans=allplans[1]
for b in boxes:ax.add_patch(Rectangle(b[:2],b[2]-b[0],b[3]-b[1],facecolor='#dae4ef',edgecolor='#607587',lw=.4))
for p in plans:
 for net in p.nets.values():
  for a,b,_ in net['edges']:ax.plot([net['pts'][a][0],net['pts'][b][0]],[net['pts'][a][1],net['pts'][b][1]],color='#206f68',lw=.25)
 for name,n in p.nodes.items():
  if name=='root':ax.scatter(*n['xy'],s=15,c='red')
ax.set(xlim=(0,W),ylim=(0,H),aspect='equal',title='KVleaf23 t3 proposed 16-root load-bin clock geometry\n70,729 actual counted FF; proposed XY/clock buffer masters; NO physical qualification',xlabel='um',ylabel='um');fig.tight_layout();fig.savefig(D/'geometry.png',dpi=160)
