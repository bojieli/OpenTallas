"""VMS placement-only experiment: nearest legal point within reach of every actual sequential neighbour."""
from pathlib import Path
from collections import Counter,defaultdict,deque
import sys,json,math,copy,argparse
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools'/'autopilot'))
import geom_rules as G
import vms_reach_plan as V

def render(spec,original,path):
 import matplotlib
 matplotlib.use('Agg')
 import matplotlib.pyplot as plt
 from matplotlib.patches import Rectangle
 fig,ax=plt.subplots(figsize=(5,7));old={c[6]:G.ctr(c) for c in original.values()}
 for c in original.values():
  if c[0]=='M':ax.add_patch(Rectangle((c[2],c[3]),c[4]-c[2],c[5]-c[3],facecolor='.85',edgecolor='.6',lw=.3))
 for m in spec['moves']:
  x,y=m['xy'];u,v=old[m['inst']];ax.plot([u,x],[v,y],color='#2688bd',lw=.5,alpha=.4);ax.scatter(x,y,c='#b90000',s=6)
 ax.set_xlim(0,spec['outline_um'][0]);ax.set_ylim(0,spec['outline_um'][1]);ax.set_aspect('equal')
 ax.set_title(f'VMS nearest feasible existing-stage plan\n{spec["cell_count"]} FF moves; 0 cycles; macro/pin/clock/PG unchanged')
 fig.tight_layout();fig.savefig(path,dpi=140);plt.close(fig)

def neighbours(D):
 seq=sorted(i for i,c in D.cells.items() if c[0]=='S');si={c:i for i,c in enumerate(seq)};comb={i for i,c in D.cells.items() if c[0] in 'BLK'}
 st=defaultdict(int);caps=defaultdict(int);indeg=Counter();succ=defaultdict(list)
 for cid in comb:
  for n in D.drives[cid]:
   for r in D.nets[n][2]:
    if r[0]=='i' and not r[2] and r[1] in comb:succ[cid].append(r[1]);indeg[r[1]]+=1
 for cid in seq:
  for n in D.drives[cid]:
   for r in D.nets[n][2]:
    if r[0]!='i' or r[2]:continue
    if r[1] in si:caps[r[1]]|=1<<si[cid]
    elif r[1] in comb:st[r[1]]|=1<<si[cid]
 q=deque(i for i in comb if not indeg[i]);done=0
 while q:
  cid=q.popleft();done+=1
  for n in D.drives[cid]:
   for r in D.nets[n][2]:
    if r[0]!='i' or r[2]:continue
    if r[1] in si:caps[r[1]]|=st[cid]
    elif r[1] in comb:st[r[1]]|=st[cid]
  for j in succ[cid]:
   indeg[j]-=1
   if indeg[j]==0:q.append(j)
 if done!=len(comb):raise ValueError('combinational cycle')
 edges=set();adj=defaultdict(set)
 for cap,bits in caps.items():
  while bits:
   b=bits&-bits;src=seq[b.bit_length()-1];bits-=b
   if src==cap:continue
   a,z=sorted((src,cap));edges.add((a,z));adj[src].add(cap);adj[cap].add(src)
 return sorted(edges),adj

def nearest(D,cid,adj,reach,reserved):
 old=G.ctr(D.cells[cid]);pts=[G.ctr(D.cells[n]) for n in adj[cid]]
 ul=max(x+y-reach for x,y in pts);uh=min(x+y+reach for x,y in pts)
 vl=max(x-y-reach for x,y in pts);vh=min(x-y+reach for x,y in pts)
 if ul>uh or vl>vh:return None
 x0,y0,x1,y1=D.extra['core'];hw,hh=.702,.135
 blocks=[(c[2]-2.16-hw,c[3]-2.16-hh,c[4]+2.16+hw,c[5]+2.16+hh) for c in D.cells.values() if c[0]=='M']
 blocks += [(x-.702-hw,y-.135-hh,x+.702+hw,y+.135+hh) for n,(x,y) in reserved.items() if n!=cid]
 ox=x0+hw;oy=y0+hh;best=None
 for row in range(int(math.floor((y1-hh-oy)/.27))+1):
  y=oy+row*.27;lo=max(x0+hw,ul-y,vl+y);hi=min(x1-hw,uh-y,vh+y)
  if lo>hi:continue
  spans=[(lo,hi)]
  for a,b,c,d in blocks:
   if not b<y<d:continue
   ns=[]
   for l,h in spans:
    if a>=h or c<=l:ns.append((l,h));continue
    if l<a:ns.append((l,min(h,a)))
    if c<h:ns.append((max(l,c),h))
   spans=ns
  for l,h in spans:
   low=math.ceil((l-ox)/2.16-1e-9);high=math.floor((h-ox)/2.16+1e-9)
   if low>high:continue
   col=min(high,max(low,round((old[0]-ox)/2.16)));x=ox+col*2.16
   rank=(abs(x-old[0])+abs(y-old[1]),abs(y-old[1]),x,y)
   if best is None or rank<best[0]:best=(rank,(x,y))
 return None if best is None else best[1]

def main():
 p=argparse.ArgumentParser();p.add_argument('dump',type=Path);p.add_argument('--out',type=Path,required=True);p.add_argument('--reach',type=float,default=395);p.add_argument('--reset-plan',type=Path,required=True);p.add_argument('--module',default='hnx_vms_bank_q0_faces__vec6293');a=p.parse_args();a.out.mkdir(exist_ok=False,parents=True)
 if not a.module.startswith('hnx_vms_bank_q0_faces__vec') or not 0<a.reach<=395:
  p.error('VMS exact-view experiment requires a reach target in(0,395]')
 D=G.Design(a.dump);base=G.r2r_metrics(D);original=copy.deepcopy(D.cells);reserved={};moves={}
 def move(cid,xy,reason):
  if (D.cells[cid][0]!='S' or D.cells[cid][6].startswith(('u_bin_','u_bout_'))
      or D.extra.get('status',{}).get(cid) in {'FIRM','LOCKED','COVER'}):
   raise ValueError('existing boundary/fixed anchor cannot move')
  c=D.cells[cid];w,h=c[4]-c[2],c[5]-c[3];x,y=xy;D.cells[cid]=(*c[:2],x-w/2,y-h/2,x+w/2,y+h/2,c[6]);reserved[cid]=(x,y);moves[cid]=dict(inst=c[6],xy=[round(x-w/2,6),round(y-h/2,6)],reason=reason)
 names={c[6]:i for i,c in D.cells.items()}
 for m in json.load(open(a.reset_plan))['moves']:
  if 'reset' in m['reason']:
   if not any('.bank.rst_s'+stage+'$' in m['inst'] for stage in ['1','2']):
    raise ValueError('only the two measured VMS input synchronizers may use reset anchors')
   c=D.cells[names[m['inst']]];move(names[m['inst']],(m['xy'][0]+(c[4]-c[2])/2,m['xy'][1]+(c[5]-c[3])/2),'existing reset synchronizer near pin')
 edges,adj=neighbours(D);print('edges',len(edges),flush=True)
 def dist(e):
  x,y=G.ctr(D.cells[e[0]]);u,v=G.ctr(D.cells[e[1]]);return abs(x-u)+abs(y-v)
 assert abs(max(map(dist,edges))-G.r2r_metrics(D)['r2r_max'])<.011
 def eligible(i):return not D.cells[i][6].startswith(('u_bin_','u_bout_')) and D.extra.get('status',{}).get(i) not in {'FIRM','LOCKED','COVER'}
 for step in range(500):
  bad=[e for e in edges if dist(e)>405+1e-7]
  if not bad:break
  counts=Counter(i for e in bad for i in e if eligible(i));candidates=[]
  for i,count in counts.most_common(20):
   xy=nearest(D,i,adj,a.reach,reserved)
   if xy is None:continue
   old=G.ctr(D.cells[i]);cost=abs(xy[0]-old[0])+abs(xy[1]-old[1]);candidates.append((-count,cost,i,xy))
  if not candidates:raise ValueError(f'no existing internal FF site resolves {len(bad)} long edges')
  _,_,cid,xy=min(candidates);move(cid,xy,'nearest feasible point for all actual sequential neighbours')
 else:raise ValueError('placement did not converge')
 measured=G.r2r_metrics(D);assert measured['r2r_captures_gt405']==0
 result=dict(schema='opentallas.vms_reach_trial.v1',module=a.module,outline_um=list(D.die[2:]),prototype_only=True,added_cycles=0,macros=[],clock_moves=[],moves=list(moves.values()),cell_count=len(moves),review=dict(verdict='NOT_REVIEWED'),baseline=base,predicted_r2r=measured,reach_target_um=a.reach,connectivity_edges=len(edges),render_macros=[dict(xy=[c[2],c[3]],size=[c[4]-c[2],c[5]-c[3]]) for c in D.cells.values() if c[0]=='M'])
 (a.out/'plan.json').write_text(json.dumps(result,indent=1)+'\n')
 (a.out/'apply.tcl').write_text(V.tcl(result));(a.out/'affinity_pre_dpl.tcl').write_text(V.pre_dpl_hook(result))
 render(result,original,a.out/'plan.png')
 print('PLANNED',len(moves),'registers',measured,flush=True)
if __name__=='__main__':main()
