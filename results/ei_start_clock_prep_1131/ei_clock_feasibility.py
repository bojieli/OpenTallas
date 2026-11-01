#!/usr/bin/env python3
import sys,json,math,importlib.util,collections,hashlib
from pathlib import Path
src=Path('/srv/opentallas-scratch2/claude/codex-kv-wave-1131/src/tools/autopilot/geom_rules.py')
spec=importlib.util.spec_from_file_location('gr',src);g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g)
p=Path('/srv/opentallas-scratch2/claude/codex-kv-residuals-1101/hubei/ff/geom_final1131/geom.tsv');d=g.Design(p)
roots={};memo={}
def trace(n):
 if n in memo:return memo[n]
 seen=set();cur=n;r=None
 while cur not in seen:
  seen.add(cur);dr=d.nets[cur][1]
  if dr is None:break
  if dr[0]=='p':r=dr[1];break
  ins=d.cell_in.get(dr[1],[])
  if d.kind(dr[1]) not in ('B','K') or not ins:break
  ck=[n for n,c in ins if c];cur=ck[0] if ck else ins[0][0]
 for x in seen:memo[x]=r
 return r
for cid,c in d.cells.items():
 if c[0] in 'SM':
  for n,ck in d.cell_in.get(cid,[]):
   if ck:roots[cid]=trace(n)
grid={p['k']:p for p in d.pins if p['io']=='INPUT' and g.GRID_TAP_RE.match(p['name'])}
actual=collections.Counter(d.pin_by_k[r]['name'] if r is not None else 'UNROOTED' for r in roots.values());groups=collections.defaultdict(list);forward=[]
for cid,r in roots.items():
 x,y=g.ctr(d.cells[cid])
 if r in grid:
  k=min(grid,key=lambda k:abs(grid[k]['x']-x)+abs(grid[k]['y']-y));groups[k].append((x,y,cid))
 else:forward.append((cid,d.pin_by_k[r]['name'] if r is not None else None))
def partition(pts,n):
 if n==1:return [pts]
 xs=[p[0] for p in pts];ys=[p[1] for p in pts];axis=0 if max(xs)-min(xs)>=max(ys)-min(ys) else 1
 pts=sorted(pts,key=lambda p:p[axis]);a=n//2;cut=len(pts)*a//n
 return partition(pts[:cut],a)+partition(pts[cut:],n-a)
def centre(pts):
 return tuple(sorted(p[i] for p in pts)[len(pts)//2] for i in (0,1))
report={'status':'DISABLED_GEOMETRIC_FEASIBILITY_ONLY_RC_NLDM_PENDING','source_dump_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'actual_connected_root_counts':dict(actual),'planned_assignment':'nearest original ingress; no physical connectivity edits','external_ingress_count':len(grid),'forwarded_domains_preserved':dict(collections.Counter(r for _,r in forward)),'forwarded_ff_count':len(forward),'groups':[]}
for k,pts in sorted(groups.items(),key=lambda kv:grid[kv[0]]['name']):
 n=math.ceil(len(pts)/1500)
 while True:
  leaves=partition(pts,n)
  if all(max(abs(p[0]-centre(q)[0])+abs(p[1]-centre(q)[1]) for p in q)<=405 for q in leaves):break
  n+=1
 for i,q in enumerate(leaves):
  x,y=centre(q);root=grid[k];radius=max(abs(p[0]-x)+abs(p[1]-y) for p in q)
  report['groups'].append({'root':root['name'],'id':i,'weight':len(q),'xy':[x,y],'radius_l1_um':radius,'root_trunk_l1_um':abs(root['x']-x)+abs(root['y']-y),'endpoint_ids':[p[2] for p in q]})
report['planned_root_weights']={grid[k]['name']:len(v) for k,v in groups.items()};report['leaf_groups']=len(report['groups']);report['total_grid_ff']=sum(map(len,groups.values()));report['max_cluster_weight']=max(q['weight'] for q in report['groups']);report['max_cluster_radius_um']=max(q['radius_l1_um'] for q in report['groups'])
Path('clock_clusters.json').write_text(json.dumps(report,indent=1)+'\n');print(json.dumps({k:v for k,v in report.items() if k not in ['groups','forwarded_domains_preserved']},indent=1))
