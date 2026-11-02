"""Finite row/site preparation on the complete source-model graph; no ODB/CAD mutation."""
from pathlib import Path
import json,re,collections,importlib.util,math,time
P=Path(__file__).parent
spec=importlib.util.spec_from_file_location('g',P/'geom_rules.py');g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g)
d=g.Design(P/'port_geom_repack3.tsv');names={c[6]:i for i,c in d.cells.items()};orig=dict(d.cells);homes=json.loads((P/'final_composed_homes_DISABLED.json').read_text());variables={names[h['name']] for h in homes}
for h in homes:
 i=names[h['name']];c=d.cells[i];w,hh=c[4]-c[2],c[5]-c[3];x,y=h['xy'];d.cells[i]=(c[0],c[1],x-w/2,y-hh/2,x+w/2,y+hh/2,c[6])
ori={st:next(i for i,c in d.cells.items() if c[6].startswith('u_bound.u_cland_origin/'+st+'$')) for st in ('s1','s2','pd')};oinv={i:st for st,i in ori.items()};rawid=next(i for i,c in d.cells.items() if c[6].startswith('u_bound.u_rrl_87/q$'))
regions=json.loads((P/'origin_instance_regions.json').read_text());source=json.loads((P/'final_source_homes_DISABLED.json').read_text())+json.loads((P/'final_raw_homes_DISABLED.json').read_text());fixed={(h['stage'],h['region']):h['xy'] for h in source}
clock=json.loads((P/'final_clock_association_DISABLED.json').read_text());assign={r['name']:r['parent_tap'] for r in clock['assignments']};pins={p['name']:p for p in d.pins};seq={i for i,c in d.cells.items() if c[0]=='S'};cache={}
def walk(i,fwd):
 if (i,fwd) in cache:return cache[i,fwd]
 todo=[i];seen=set();out=set()
 while todo:
  a=todo.pop()
  if a in seen:continue
  seen.add(a)
  ns=[z[1] for n in d.drives.get(a,[]) for z in d.nets[n][2] if z[0]=='i' and not z[2]] if fwd else [d.nets[n][1][1] for n,clk in d.cell_in.get(a,[]) if not clk and d.nets[n][1] and d.nets[n][1][0]=='i']
  for j in ns:
   if j in seq:out.add(j)
   elif d.kind(j) in 'BLK':todo.append(j)
 cache[i,fwd]=out;return out

def translate(a,b):
 if b in oinv:rs=range(4)
 elif b==rawid:rs=[-1,0,1,2,3]
 else:rs=[regions.get(d.cells[b][6].split('/')[0],-1)]
 out=[]
 for r in rs:
  def node(i):
   if i in oinv:return (oinv[i],max(r,0))
   if i==rawid and r>=0:return ('raw',r)
   return i
  aa,bb=node(a),node(b)
  if aa!=bb:out.append((aa,bb))
 return out
edges=set()
for i in variables:
 for j in walk(i,False):edges.update(translate(j,i))
 for j in walk(i,True):edges.update(translate(i,j))
adj=collections.defaultdict(set)
for a,b in edges:adj[a].add(b);adj[b].add(a)
def point(i):return fixed[i] if isinstance(i,tuple) else g.ctr(d.cells[i])
macros=[c[2:6] for c in d.cells.values() if c[0]=='M'];occupied=collections.defaultdict(list)
def occupy(box):
 for row in range(math.floor((box[1]+1e-6)/.27),math.ceil((box[3]-1e-6)/.27)):
  occupied[row].append((box[0],box[2]))
for i,c in d.cells.items():
 if c[0]=='S' and c[1]!='REAL_MACRO_PORT' and i not in variables and i not in oinv:occupy(c[2:6])
for h in source:occupy(h['box'])
pin_targets={}
for i in variables:
 name=d.cells[i][6]
 if name.startswith('u_bound.u_bout_tl/'):
  m=re.search(r'/q\\\[([0-9]+)\\\]',name)
  if not m:raise RuntimeError('No exact TL pin association '+name)
  p=pins['tl['+m[1]+']'];pin_targets[i]=(p['x'],p['y'])

def anchors(i):
 result=[(*point(j),405.0) for j in adj[i]]
 cp=pins[assign[d.cells[i][6]]];result.append((cp['x'],cp['y'],200.0))
 if i in pin_targets:result.append((*pin_targets[i],30.0))
 return result

def subtract(parts,lo,hi):
 out=[]
 for a,b in parts:
  if hi<=a or lo>=b:out.append((a,b));continue
  if a<lo:out.append((a,min(b,lo)))
  if hi<b:out.append((max(a,hi),b))
 return out

def candidate(i):
 c=d.cells[i];hw,hh=(c[4]-c[2])/2,(c[5]-c[3])/2;xold,yold=g.ctr(c);aa=anchors(i)
 ymin=max([4.32+hh]+[y-r for x,y,r in aa]);ymax=min([514.08-hh]+[y+r for x,y,r in aa]);rmin=math.ceil((ymin-hh)/.27-1e-7);rmax=math.floor((ymax-hh)/.27+1e-7)
 best=None
 for row in sorted(range(rmin,rmax+1),key=lambda r:abs(r*.27+hh-yold)):
  y=row*.27+hh
  if best and abs(y-yold)>best[0]+1e-9:break
  lo,hi=4.32+hw,773.28-hw
  for x0,y0,r in aa:
   rest=r-abs(y-y0)
   if rest< -1e-7:lo,hi=1,0;break
   lo=max(lo,x0-rest);hi=min(hi,x0+rest)
  if lo>hi+1e-7:continue
  parts=[(lo,hi)]
  for x0,y0,x1,y1 in macros:
   if min(y+hh,y1)-max(y-hh,y0)>1e-6:parts=subtract(parts,x0-hw,x1+hw)
  for rr in range(math.floor((y-hh+1e-6)/.27),math.ceil((y+hh-1e-6)/.27)):
   for x0,x1 in occupied[rr]:parts=subtract(parts,x0-hw,x1+hw)
  for a,b in parts:
   left=math.ceil((a-hw)/.054-1e-7);right=math.floor((b-hw)/.054+1e-7)
   if left>right:continue
   ix=max(left,min(right,round((xold-hw)/.054)));x=ix*.054+hw;score=abs(x-xold)+abs(y-yold)
   if best is None or score<best[0]:best=(score,(x,y))
 return best
# Place the most constrained actual neighbor diamonds first. This is a finite
# candidate algorithm, not an infeasibility proof if some cells need joint moves.
def priority(i):
 aa=anchors(i);u0=max(x+y-r for x,y,r in aa);u1=min(x+y+r for x,y,r in aa);v0=max(x-y-r for x,y,r in aa);v1=min(x-y+r for x,y,r in aa)
 return (max(0,u1-u0)*max(0,v1-v0),-len(adj[i]),d.cells[i][6])
order=sorted(variables,key=priority);failed=[];placed=[];begin=time.time()
print('FULL_ROW_PREP',len(variables),'variables',len(edges),'actual typed edges; fixed63clock assignment; fixed source16slots',flush=True)
for count,i in enumerate(order):
 result=candidate(i)
 if result is None:failed.append(i)
 else:
  c=d.cells[i];w,hh=c[4]-c[2],c[5]-c[3];x,y=result[1];d.cells[i]=(c[0],c[1],x-w/2,y-hh/2,x+w/2,y+hh/2,c[6]);occupy(d.cells[i][2:6]);placed.append(i)
 if count%250==0:print('ROW_PROGRESS',count,'placed',len(placed),'need_joint',len(failed),'sec',round(time.time()-begin,1),flush=True)
rows=[dict(id=i,name=d.cells[i][6],old_xy=list(g.ctr(orig[i])),xy=list(g.ctr(d.cells[i]))) for i in sorted(variables)]
(P/'rowprep_homes.json').write_text(json.dumps(rows,separators=(',',':')))
report=dict(status='PASS_ROW_SITE_MODEL_ONLY' if not failed else 'PARTIAL_NEEDS_JOINT_REPAIR',variables=len(variables),placed=len(placed),need_joint=len(failed),failed=[d.cells[i][6] for i in failed],typed_neighbor_edges=len(edges),preserved_clock_capacity_overrides=clock['reassociated_sinks'],added_ff=0,added_cycles=0,full45301_audit_required=True,elapsed_seconds=time.time()-begin)
(P/'rowprep_report.json').write_text(json.dumps(report,indent=1));print('FULL_ROW_PREP_DONE',report['status'],'placed',len(placed),'joint',len(failed),flush=True)
