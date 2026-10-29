#!/usr/bin/env python3
"""Allocate access jointly inside overlapping clock islands, preserving sites.
Every candidate uses real source metal/OBS, technology tracks, and exact island
coverage. Backtracking is finite geometry allocation, not a timing/route sweep.
"""
import argparse,json,math,collections,multiprocessing as MP
from pathlib import Path
from shapely.geometry import box
from shapely.strtree import STRtree
import jog_backbones as J
G={}

def rect_clear(a,b):
 if a[0]==b[0] or a[1]!=b[1]:return True
 dx=max(0,max(a[2],b[2])-min(a[4],b[4]));dy=max(0,max(a[3],b[3])-min(a[5],b[5]))
 return math.hypot(dx,dy)>=(.32 if a[1]=='M8' else .032)-1e-7

def compatible(a,b):
 return all(rect_clear(x,y) for x in a['geometry']+[a['_m8']] for y in b['geometry']+[b['_m8']])

def solve(group):
 pins=[r for cell in group for r in G['pins'][cell]];choices={};counts={}
 for pi,f in enumerate(pins):
  cell,pin,net=f['cell'],f['pin'],f['net'];x,y=f['base_xy_um'];hs=[q['rect_die_um'] for q in G['holes'][cell.removeprefix('ck_')]]
  cols=sorted({round(G['phase']+k*G['pitch'],6) for k in range(math.ceil((x-G['jog']-G['phase'])/G['pitch']),math.floor((x+G['jog']-G['phase'])/G['pitch'])+1)},key=lambda bx:abs(bx-x))
  ys=sorted({round(.04+k*.08,6) for k in range(math.ceil((min(h[1] for h in hs)+.027-.04)/.08),math.floor((max(h[3] for h in hs)-.027-.04)/.08)+1)},key=lambda ty:abs(ty-y));opts=[]
  for bx in cols:
   local=[[net,'M6',min(x,bx)-.016,y-.016,max(x,bx)+.016,y+.016],[net,'M6',bx-.035,y-.016,bx+.035,y+.016],[net,'M7',bx-.016,y-.036,bx+.016,y+.036]]
   if any(not J.covered(r,hs) or G['ix'].hits(r) for r in local):continue
   for ty in ys:
    riser=[net,'M7',bx-.016,min(y,ty)-.027,bx+.016,max(y,ty)+.027]
    if not J.covered(riser,hs) or G['ix'].hits(riser):continue
    if G['router'].place('M8',ty,bx-.096,bx+.096,net,keep=(ty,ty),dry=True)[0] is None:continue
    opts.append(dict(cell=cell,pin=pin,net=net,entry_xy_um=[x,y],backbone_xy_um=[bx,y],m7_window_um=[min(y,ty),max(y,ty)],m8_witness_y_um=ty,m6_jog_um=round(abs(bx-x),6),geometry=local+[riser],_m8=[net,'M8',bx-.096,ty-.04,bx+.096,ty+.04],proof='joint overlapping-island allocation; actual119_h800 metal/OBS/nativePG + canonicalPG + retained clock + native bridges;192x80nm M8 landing/.32um spacing'))
  choices[pi]=opts;counts[f['cell']+'/'+pin]=len(opts)
 nodes=0
 def search(remaining,chosen):
  nonlocal nodes
  nodes+=1
  if not remaining:return chosen
  reduced={i:[o for o in remaining[i] if all(compatible(o,v) for v in chosen)] for i in remaining}
  i=min(reduced,key=lambda k:len(reduced[k]))
  if not reduced[i]:return None
  rest={k:v for k,v in reduced.items() if k!=i}
  for o in reduced[i]:
   found=search(rest,chosen+[o])
   if found is not None:return found
  return None
 chosen=search(choices,[])
 if chosen is not None:
  for r in chosen:r.pop('_m8')
 return dict(cells=group,pins=len(pins),candidate_counts=counts,search_nodes=nodes,records=chosen,failures=pins if chosen is None else [])

def main():
 p=argparse.ArgumentParser()
 for n in ['plan','cell-windows','geometry','clock-seed','pg','out']:p.add_argument('--'+n,required=True)
 p.add_argument('--reserved-metal',action='append',default=[]);p.add_argument('--jobs',type=int,default=4);p.add_argument('--max-jog',type=float,default=1.5);a=p.parse_args();out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
 plan=json.load(open(a.plan));holes=json.load(open(a.cell_windows))['cells'];names=list(holes);bounds=[box(min(q['rect_die_um'][0] for q in holes[n])-.256,min(q['rect_die_um'][1] for q in holes[n])-.256,max(q['rect_die_um'][2] for q in holes[n])+.256,max(q['rect_die_um'][3] for q in holes[n])+.256) for n in names];tree=STRtree(bounds);parent=list(range(len(names)))
 def find(i):
  while parent[i]!=i:parent[i]=parent[parent[i]];i=parent[i]
  return i
 for i,b in enumerate(bounds):
  for j in tree.query(b):
   if j>i and b.intersects(bounds[j]):parent[find(j)]=find(i)
 ids={n:i for i,n in enumerate(names)};affected={find(ids[r['cell'].removeprefix('ck_')]) for r in plan['failures']};groups=collections.defaultdict(list)
 for i,n in enumerate(names):
  root=find(i)
  if root in affected:groups[root].append('ck_'+n)
 cells={n for row in groups.values() for n in row};kept=[r for r in plan['records'] if r['cell'] not in cells];pins=collections.defaultdict(list)
 for r in plan['records']:
  if r['cell'] in cells:pins[r['cell']].append(dict(cell=r['cell'],pin=r['pin'],net=r['net'],base_xy_um=r['entry_xy_um']))
 for r in plan['failures']:pins[r['cell']].append(r)
 print('GROUPS',len(groups),'CELLS',len(cells),'PINS',sum(map(len,pins.values())),'KEPT',len(kept),flush=True)
 for n in cells:
  if any(q['in_core'] for q in holes[n.removeprefix('ck_')]):raise ValueError('clock island inside hardcore')
 g=json.load(open(a.geometry));D=g['dbu'];ix=J.Index()
 for inst,pin,l,*xy in g['signal_shapes']:
  if l in ('M6','M7'):ix.add([f'SIGNAL:{inst}/{pin}',l,*[v/D for v in xy]])
 for inst,l,*xy in g['obstructions']:
  if l in ('M6','M7'):ix.add([f'OBS:{inst}',l,*[v/D for v in xy]])
 for n,l,*xy in g['existing_supplies']:
  if l in ('M6','M7'):ix.add([n,l,*[v/D for v in xy]])
 phase,count,pitch=g['tracks']['M7']['X'][0];phase/=D;pitch/=D;del g
 for r in json.load(open(a.clock_seed)):ix.add(r)
 router=J.C128.TrackRouter(dict(width=.08,space=.32,rf=.5,cf=1.15),'VSS',J.DCM.DEFAULT_TRACKS,8.64);router.reserve(J.C128.pg_shapes(json.load(open(a.pg))))
 for file in a.reserved_metal:
  rr=json.load(open(file))
  for r in rr:ix.add(r)
  router.reserve(J.C128.pg_shapes(rr))
 for r in kept:
  for q in r['geometry']:ix.add(q)
  x,y=r['backbone_xy_um'][0],r['m8_witness_y_um'];router.reserve(J.C128.pg_shapes([[r['net'],'M8',x-.096,y-.04,x+.096,y+.04]]))
 G.update(ix=ix,router=router,holes=holes,pins=pins,phase=phase,pitch=pitch,jog=a.max_jog)
 records=list(kept);failed=[];reports=[]
 with MP.get_context('fork').Pool(a.jobs) as pool:
  for i,result in enumerate(pool.imap_unordered(solve,list(groups.values()))):
   reports.append({k:v for k,v in result.items() if k not in ('records','failures')});failed.extend(result['failures'])
   if result['records'] is not None:records.extend(result['records'])
   else:
    # Retain the original qualified records of an unresolved group as history,
    # while its whole pin group remains explicitly unresolved for next repair.
    print('GROUP_FAIL',result['cells'],result['candidate_counts'],flush=True)
   if i%10==0:print('GROUP_PROGRESS',i+1,len(groups),'records',len(records),'unresolved',len(failed),flush=True)
 status='FAIL' if failed else 'PASS_GEOMETRY'
 json.dump(dict(status=status,records=records,failures=failed,physical_route=False),open(out/'backbone_plan.json','w'),separators=(',',':'))
 json.dump(dict(status=status,groups=len(groups),cells=len(cells),kept=len(kept),records=len(records),unresolved=len(failed),reports=reports,physical_route=False),open(out/'summary.json','w'),indent=1)
 print(status,len(records),len(failed),flush=True)
if __name__=='__main__':main()
