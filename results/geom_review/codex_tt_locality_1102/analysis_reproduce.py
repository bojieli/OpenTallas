from pathlib import Path
import importlib.util,json,collections
import argparse
ap=argparse.ArgumentParser();ap.add_argument('--dump',required=True);ap.add_argument('--out',required=True);args=ap.parse_args()
p=Path(args.out);p.mkdir(parents=True,exist_ok=True);w=Path(__file__).resolve().parents[3]
s=importlib.util.spec_from_file_location('geom',w/'tools/autopilot/geom_rules.py');g=importlib.util.module_from_spec(s);s.loader.exec_module(g);d=g.Design(args.dump);all_pairs=[];g.r2r_metrics(d,all_pairs,405);(p/'pairs.json').write_text(json.dumps(all_pairs))
seq={i for i,c in d.cells.items() if c[0]=='S'}
def walk(root,forward):
 todo=[root];seen=set();out=set()
 while todo:
  i=todo.pop()
  if i in seen:continue
  seen.add(i)
  if forward:
   nn=[(n,z[1]) for n in d.drives.get(i,[]) for z in d.nets[n][2] if z[0]=='i' and not z[2]]
  else:
   nn=[]
   for n,ck in d.cell_in.get(i,[]):
    z=d.nets[n][1]
    if not ck and z and z[0]=='i':nn.append((n,z[1]))
  for _,j in nn:
   if j in seq:out.add(j)
   elif d.kind(j) in 'BLK':todo.append(j)
 return out
rows=[]
for i,c in d.cells.items():
 if i not in seq or not c[6].startswith('u_bound.u_bin_'):continue
 if not any(c[6].startswith('u_bound.u_bin_'+x+'/') for x in ['ctx_x','dh','native_ret']):continue
 up,dn=walk(i,False),walk(i,True);ns=up|dn;pts=[g.ctr(d.cells[j]) for j in ns]
 uu=[x+y for x,y in pts];vv=[x-y for x,y in pts]
 ub=[max(uu)-405,min(uu)+405] if uu else [];vb=[max(vv)-405,min(vv)+405] if vv else []
 feasible=bool(ub and ub[0]<=ub[1] and vb[0]<=vb[1])
 xy=[(sum(ub)+sum(vb))/4,(sum(ub)-sum(vb))/4] if feasible else None
 rows.append(dict(name=c[6],xy=list(g.ctr(c)),up=len(up),down=len(dn),up_names=[d.cells[j][6] for j in sorted(up)],down_names=[d.cells[j][6] for j in sorted(dn)],neighbor_u=ub,neighbor_v=vb,fixed_neighbor_feasible=feasible,proposal_xy=xy))
(p/'bin_neighbors.json').write_text(json.dumps(rows,indent=1))
print('bins',len(rows),'fixed_neighbors feasible',sum(x['fixed_neighbor_feasible'] for x in rows))
for key in ['ctx_x','dh','native_ret']:
 rr=[x for x in rows if 'u_bin_'+key+'/' in x['name']];print(key,len(rr),sum(x['fixed_neighbor_feasible'] for x in rr),'up',max(x['up'] for x in rr),'dn',max(x['down'] for x in rr));print('examples', [{k:v for k,v in x.items() if k not in ['down_names']} for x in rr if not x['fixed_neighbor_feasible']][:1])
pairs=json.loads((p/'pairs.json').read_text());byname={c[6]:i for i,c in d.cells.items()}
viol={x['capture']:x for x in pairs}
macros=[c for c in d.cells.values() if c[0]=='M']
grid=[]
for ix in range(4,355):
 x=ix*2.16
 for iy in range(4,237):
  y=iy*2.16
  if any(c[2]-2.16<x<c[4]+2.16 and c[3]-2.16<y<c[5]+2.16 for c in macros):continue
  grid.append((x,y))
used=set();cand=[]
for rr in sorted((r for r in rows if r['name'] in viol),key=lambda r:viol[r['name']]['distance_um'],reverse=True):
 u0,u1=rr['neighbor_u'];v0,v1=rr['neighbor_v'];i=byname[rr['name']];ns=walk(i,False)|walk(i,True);pts=[g.ctr(d.cells[j]) for j in ns]
 valid=[q for q in grid if q not in used and u0<=sum(q)<=u1 and v0<=q[0]-q[1]<=v1]
 target=min(valid,key=lambda q:(max(abs(q[0]-x)+abs(q[1]-y) for x,y in pts),abs(q[0]-rr['xy'][0])+abs(q[1]-rr['xy'][1]))) if valid else None
 if target:used.add(target)
 cand.append(dict(name=rr['name'],old_xy=rr['xy'],new_xy=target,old_worst=viol[rr['name']]['distance_um'],new_neighbor_max=max(abs(target[0]-x)+abs(target[1]-y) for x,y in pts) if target else None))
(p/'boundary_candidates.json').write_text(json.dumps(cand,indent=1));print('BOUNDARY_MOVE',len(cand),'legalcoarse',sum(x['new_xy'] is not None for x in cand),'maxneighbor',max(x['new_neighbor_max'] or 1e9 for x in cand));print(cand[:1])
reader_names=sorted({z['launch'] for z in pairs if any(s in z['capture'] for s in ['u_bout_tl/','u_bout_native_cmd/'])})
reader_rows=[]
for name in reader_names:
 i=byname[name];up,dn=walk(i,False),walk(i,True);pts=[g.ctr(d.cells[j]) for j in up|dn];uu=[x+y for x,y in pts];vv=[x-y for x,y in pts];ub=[max(uu)-405,min(uu)+405];vb=[max(vv)-405,min(vv)+405];feasible=ub[0]<=ub[1] and vb[0]<=vb[1]
 reader_rows.append(dict(name=name,xy=list(g.ctr(d.cells[i])),up=len(up),down=len(dn),neighbor_u=ub,neighbor_v=vb,fixed_neighbor_feasible=feasible,up_names=[d.cells[j][6] for j in sorted(up)],down_names=[d.cells[j][6] for j in sorted(dn)]))
(p/'reader_neighbors.json').write_text(json.dumps(reader_rows,indent=1))
print('READERS',len(reader_rows),'fixedneighborsFeasible',sum(x['fixed_neighbor_feasible'] for x in reader_rows))
for ishr in [True,False]:
 rr=[x for x in reader_rows if ('.u_hr.' in x['name'])==ishr];print('HR' if ishr else 'TL',len(rr),'feasible',sum(x['fixed_neighbor_feasible'] for x in rr),'maxup',max(x['up'] for x in rr),'maxdn',max(x['down'] for x in rr));print('unfeasible-example',[{k:v for k,v in x.items() if k!='down_names'} for x in rr if not x['fixed_neighbor_feasible']][:1])
