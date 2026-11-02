"""PREP: move only the70 actual DPL-invalid FFs to vacant native row sites."""
import csv,json,collections,bisect,math,sys,re
from pathlib import Path
O=Path(__file__).resolve().parent;R=O.parents[1];C=Path('/srv/opentallas-scratch/claude/codex-kv-ctl-repack-r3-0130/failed_collector')
sys.path.insert(0,str(R/'tools/autopilot'));import geom_rules as G
r=json.load(open(C/'rows.json'));bad=json.load(open(C/'ff_outside_rows.json'))['bad'];badnames={x['name'] for x in bad};assert len(bad)==70
rows=collections.defaultdict(list)
for q in r['rows']:rows[q['y0']].append(q)
occ=collections.defaultdict(list);cells=list(csv.DictReader(open(C/'placed.csv')))
for q in cells:
 if q['kind'] not in ['ff','tap'] or q['name'] in badnames:continue
 x,y,w,h=[round(float(q[k])*1000) for k in ['x','y','w','h']]
 for yy in range(y,y+h,270):occ[yy].append((x,x+w,q['name']))
for v in occ.values():v.sort()
def free_segments(lo,hi,obstacles):
 left=lo
 for a,b,n in obstacles:
  if b<=left:continue
  if a>=hi:break
  if a>left:yield left,min(a,hi)
  left=max(left,b)
 if left<hi:yield left,hi
moves=[];failed=[]
for q in sorted(bad,key=lambda q:q['name']):
 x,y,x1,y1=q['bbox'];w=x1-x;h=y1-y;assert h==270;options=[]
 for yy,rs in rows.items():
  dy=abs(yy-y)
  if dy>6000:continue
  for rr in rs:
   for a,b in free_segments(rr['x0'],rr['x1'],occ[yy]):
    low=rr['x0']+math.ceil((a-rr['x0'])/54)*54;high=rr['x0']+math.floor((b-w-rr['x0'])/54)*54
    if low>high:continue
    xx=max(low,min(high,rr['x0']+round((x-rr['x0'])/54)*54));distance=abs(xx-x)+dy
    if distance<=6000:options.append((distance,dy,xx,yy,rr['orient']))
 if not options:failed.append(q['name']);continue
 dist,dy,xx,yy,orient=min(options);bisect.insort(occ[yy],(xx,xx+w,q['name']));moves.append(dict(name=q['name'],master=q['master'],old_ll_dbu=[x,y],new_ll_dbu=[xx,yy],size_dbu=[w,h],orient=orient,move_um=dist/1000))
assert not failed,failed
D=G.Design(str(C/'geom.tsv'),[str(O.parent/'kv_ctl_place_1102/memory_tt.lib')],True);byname={q[6]:i for i,q in D.cells.items()}
for m in moves:
 i=byname[m['name']];c=D.cells[i];x,y=[v/1000 for v in m['new_ll_dbu']];w,h=[v/1000 for v in m['size_dbu']];D.cells[i]=tuple(list(c[:2])+[x,y,x+w,y+h]+list(c[6:]))
r2r=G.r2r_metrics(D);pin=G.pin_reg_metrics(D,re.compile(G.STRAP_RE_DEFAULT))
public=[]
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
   if kind=='S':
    x,y=G.ctr(D.cells[cid]);public.append((abs(x-p['x'])+abs(y-p['y']),p['name'],D.cells[cid][6]))
   elif kind=='B':todo.extend(nn for nn,clk in D.cell_in.get(cid,[]) if not clk)
  else:
   for sink in D.nets[n][2]:
    if sink[0]!='i' or sink[2]:continue
    kind=D.kind(sink[1])
    if kind=='S':
     x,y=G.ctr(D.cells[sink[1]]);public.append((abs(x-p['x'])+abs(y-p['y']),p['name'],D.cells[sink[1]][6]))
    elif kind=='B':todo.extend(D.drives.get(sink[1],[]))
conflicts=set()
for m in moves:
 x,y=m['new_ll_dbu'];w,h=m['size_dbu']
 for c in cells:
  if c['kind'] in ['pin','macro','tap','ff']:continue
  a,b,cw,ch=[round(float(c[k])*1000) for k in ['x','y','w','h']]
  if x<a+cw and a<x+w and y<b+ch and b<y+h:conflicts.add(c['name'])
public_cert=dict(capture_edges=len(public),maximum_um=max(public)[0],gt150=sum(x[0]>150 for x in public),worst=sorted(public,reverse=True)[:5])
assert r2r['r2r_captures_gt405']==0 and public_cert['gt150']==0

out=dict(source='actual r3 failed DPL checkpoint; no P&R executed',FFs=18768,unchanged_FFs=18698,moved_FFs=len(moves),maximum_move_um=max(x['move_um'] for x in moves),actual_native_rows=len(r['rows']),other_FFs_and_taps_fixed=True,ordinary_comb_DPL_required=True,moves=moves,R2R=r2r,pins=pin,all_public_DATA_captures=public_cert,combinational_overlap_cells_requiring_DPL=len(conflicts),combinational_overlap_examples=sorted(conflicts)[:15])
(O/'rowfix_plan.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({k:v for k,v in out.items() if k not in ['moves']},indent=2))
