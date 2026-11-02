"""Actual CTL failure witnesses; no RTL changes or physical execution."""
import sys,json,math,collections,re
from pathlib import Path
O=Path(__file__).parent;R=O.resolve().parents[1];sys.path.insert(0,str(R/'tools/autopilot'))
import geom_rules as G
D=G.Design('/srv/opentallas-scratch/claude/codex-kv-ctl-place-2330/collector/geom.tsv',[str(O/'memory_tt.lib')],True)
pairs=json.loads((O/'far_capture_pairs.json').read_text());names={x['launch'] for x in pairs};ids={c[6]:i for i,c in D.cells.items()};seq={i for i,c in D.cells.items() if c[0] in 'SM'}
anchors=collections.defaultdict(list)
for p in D.pins:
 if p['name'] in ('rst_n','por_n') or p['sig'] in ('POWER','GROUND','CLOCK') or G.CLOCK_PIN_RE.search(p['name']) or re.search(G.STRAP_RE_DEFAULT,p['name']):continue
 n=D.pin_net.get(p['k']);todo=[n] if n is not None else [];seen=set()
 while todo:
  n=todo.pop()
  if n in seen:continue
  seen.add(n)
  if p['io']=='OUTPUT':
   dr=D.nets[n][1]
   if not dr or dr[0]!='i':continue
   cid=dr[1];kind=D.kind(cid)
   if kind=='S':anchors[cid].append(p)
   elif kind=='B':todo.extend(nn for nn,clk in D.cell_in.get(cid,[]) if not clk)
  else:
   for s in D.nets[n][2]:
    if s[0]!='i' or s[2]:continue
    kind=D.kind(s[1])
    if kind=='S':anchors[s[1]].append(p)
    elif kind=='B':todo.extend(D.drives.get(s[1],[]))
def captures(cid):
 todo=list(D.drives.get(cid,[]));seen=set();out=set()
 while todo:
  n=todo.pop()
  if n in seen:continue
  seen.add(n)
  for s in D.nets[n][2]:
   if s[0]!='i' or s[2]:continue
   if s[1] in seq:out.add(s[1])
   else:todo.extend(D.drives.get(s[1],[]))
 return out
def clip(poly,a,b,c):
 out=[]
 for p,q in zip(poly,poly[1:]+poly[:1]):
  ep=a*p[0]+b*p[1]-c;eq=a*q[0]+b*q[1]-c
  if ep<=1e-8:out.append(p)
  if (ep<0 and eq>0) or (ep>0 and eq<0):
   t=ep/(ep-eq);out.append([p[0]+t*(q[0]-p[0]),p[1]+t*(q[1]-p[1])])
 return out
rows=[]
for name in sorted(names):
 cid=ids[name];caps=captures(cid);lo_u=(-1e8,None);hi_u=(1e8,None);lo_v=(-1e8,None);hi_v=(1e8,None)
 constraints=[]
 for cap in caps:
  c=D.cells[cap];points=[G.ctr(c)] if c[0]=='S' else [(c[x],c[y]) for x in [2,4] for y in [3,5]]
  constraints.extend((x,y,405.,'capture:'+c[6]) for x,y in points)
 constraints.extend((p['x'],p['y'],150.,'public:'+p['name']) for p in anchors[cid])
 for x,y,r,label in constraints:
  if x+y-r>lo_u[0]:lo_u=(x+y-r,label)
  if x+y+r<hi_u[0]:hi_u=(x+y+r,label)
  if x-y-r>lo_v[0]:lo_v=(x-y-r,label)
  if x-y+r<hi_v[0]:hi_v=(x-y+r,label)
 c=D.cells[cid];cw,ch=c[4]-c[2],c[5]-c[3];x0,x1=4.32+cw/2,367.2-cw/2;y0,y1=4.32+ch/2,367.2-ch/2
 poly=[[x0,y0],[x1,y0],[x1,y1],[x0,y1]]
 for a,b,k in [(1,1,hi_u[0]),(-1,-1,-lo_u[0]),(1,-1,hi_v[0]),(-1,1,-lo_v[0])]:
  if poly:poly=clip(poly,a,b,k)
 witness=None
 if lo_u[0]>hi_u[0]:witness=dict(axis='x+y',lower=lo_u,upper=hi_u,gap_um=lo_u[0]-hi_u[0])
 elif lo_v[0]>hi_v[0]:witness=dict(axis='x-y',lower=lo_v,upper=hi_v,gap_um=lo_v[0]-hi_v[0])
 rows.append(dict(launch=name,old_xy=G.ctr(c),capture_count=len(caps),public_anchors=[dict(name=p['name'],xy=[p['x'],p['y']],io=p['io']) for p in anchors[cid]],u_bounds=[lo_u,hi_u],v_bounds=[lo_v,hi_v],feasible_polygon=poly,feasible_fixed_targets=bool(poly),infeasible_witness=witness,capture_endpoints=[dict(name=D.cells[i][6],kind=D.cells[i][0],xy=G.ctr(D.cells[i])) for i in sorted(caps)]))
summary=dict(scope='304 actual worst-launch FFs; all reachable actual sequential capture endpoints fixed; every actual direct directional public DATA pin capture/output constrained150; typed rst_n/por_n reset nets separate; core bounds included; feasible polygon not yet legalized around macro/clock keepouts',launches=len(rows),feasible=sum(x['feasible_fixed_targets'] for x in rows),infeasible=sum(not x['feasible_fixed_targets'] for x in rows),public_feasible=sum(x['feasible_fixed_targets'] and bool(x['public_anchors']) for x in rows),public_infeasible=sum(not x['feasible_fixed_targets'] and bool(x['public_anchors']) for x in rows),rows=rows)
(O/'launch_regions.json').write_text(json.dumps(summary,indent=1)+'\n');print({k:v for k,v in summary.items() if k!='rows'});print('first infeasible',next(x for x in rows if not x['feasible_fixed_targets']))
