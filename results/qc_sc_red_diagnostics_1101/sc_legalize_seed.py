"""Freeze SC clock seed sites against the actual floorplan rows and fixed TAPs.

This changes only planned cell centers before GPL, never the logical clock
nodes/parents/leaves/count or any TAP. The original failed plan stays intact.
"""
import argparse,copy,json,math,re
from pathlib import Path
ap=argparse.ArgumentParser();ap.add_argument('kit');ap.add_argument('sites');ap.add_argument('out');a=ap.parse_args();k=Path(a.kit);o=Path(a.out);o.mkdir(parents=True,exist_ok=True)
rows=[];obs=[];unit=None;wh=None
for line in Path(a.sites).read_text().splitlines():
 x=line.split('\t')
 if x[0]=='DBU':unit=int(x[1])
 elif x[0]=='ROW':rows.append(dict(name=x[1],x=int(x[2]),y=int(x[3]),sw=int(x[4]),h=int(x[5]),n=int(x[6]),orient=x[7]))
 elif x[0]=='OBS':obs.append((x[1],*[int(v) for v in x[3:7]]))
 elif x[0]=='MASTER':wh=(int(x[2]),int(x[3]))
assert unit and rows and wh
w,h=wh;plan=json.load((k/'core_infra_plan.json').open());sl=json.load((k/'core_infra_slice.json').open());cells=plan['cells'];assert len(cells)==2389

def rfor(c):return min(rows,key=lambda r:abs(r['y']+h/2-c['xy_um'][1]*unit))
def initial(c):
 r=rfor(c);x=r['x']+round((c['xy_um'][0]*unit-w/2-r['x'])/r['sw'])*r['sw'];return (x,r['y'],r)
def overlap(x,y,b):return x<b[3] and x+w>b[1] and y<b[4] and y+h>b[2]
buckets={r['y']:[] for r in rows}
for ob in obs:
 for r in rows:
  if r['y']<ob[4] and r['y']+h>ob[2]:buckets[r['y']].append(ob)
original={c['name']:initial(c)for c in cells}
for c in cells:
 x,y,r=original[c['name']];buckets[y].append((c['name'],x,y,x+w,y+h))
selected={};changes=[];bad=[]
for c in cells:
 name=c['name'];x0,y0,r0=original[name];rect=[round(t*unit)for t in c['rect_um']]
 def valid(x,y,r):
  if x<max(r['x'],rect[0])or x+w>min(r['x']+r['n']*r['sw'],rect[2])or y<rect[1]or y+h>rect[3]:return False
  return not any(b[0]!=name and overlap(x,y,b)for b in buckets[y])
 oldhits=[b[0]for b in buckets[y0]if b[0]!=name and overlap(x0,y0,b)]
 if oldhits:bad.append(dict(name=name,obstacles=oldhits))
 found=None
 # Prefer the same legal row and nearest site, then nearby rows if needed.
 candidate_rows=sorted(rows,key=lambda r:(abs(r['y']-y0),r['y']))
 for r in candidate_rows:
  if abs(r['y']-y0)>4*r['h']:break
  base=r['x']+round((x0-r['x'])/r['sw'])*r['sw']
  for n in range(513):
   xs=[base]if n==0 else[base+n*r['sw'],base-n*r['sw']]
   for x in xs:
    if valid(x,r['y'],r):found=x,r['y'],r;break
   if found:break
  if found:break
 if found is None:raise ValueError('no TAP-safe planned site: '+name)
 x,y,r=found;selected[name]=((x+w/2)/unit,(y+h/2)/unit,r['orient'],x/unit,y/unit)
 if (x,y)!=(x0,y0):changes.append(dict(name=name,old_center_um=c['xy_um'],new_center_um=list(selected[name][:2]),dx_um=(x-x0)/unit,dy_um=(y-y0)/unit,old_conflicts=oldhits))
 buckets[y].append((name,x,y,x+w,y+h))
# Re-check the actual selected set independent of the greedy reservation map.
actual=[]
for c in cells:
 xy=selected[c['name']];x=round(xy[3]*unit);y=round(xy[4]*unit)
 hits=[b[0]for b in obs+actual if overlap(x,y,b)]
 if hits:raise ValueError((c['name'],hits))
 actual.append((c['name'],x,y,x+w,y+h))
for d in [plan,sl]:
 for node in d['core_tree']['nodes']:node['xy_um']=list(selected[node['name']][:2])
 if 'cells'in d:
  for cell in d['cells']:cell['xy_um']=list(selected[cell['name']][:2])
 for name,pos in d.get('cell_placements',{}).items():
  if name in selected and isinstance(pos,dict):pos['origin_um']=list(selected[name][3:5]);pos['orient']=selected[name][2]
for name,d in [('core_infra_plan.json',plan),('core_infra_slice.json',sl)]: (o/name).write_text(json.dumps(d,indent=1)+'\n')
text=(k/'master_core_infra.tcl').read_text();count=0
pat=r'^ot_ci_cell \{([^}]+)\} (\S+) ([\d.eE+-]+) ([\d.eE+-]+) (\{[^\n]+\})$'
def rewrite(m):
 global count
 name=m[1];assert name in selected;count+=1;x,y,orient,ox,oy=selected[name]
 return f'ot_ci_cell {{{name}}} {m[2]} {x:.6f} {y:.6f} {m[5]}\not_ci_origin_assert {{{name}}} {ox:.6f} {oy:.6f} {{{orient}}}'
new=re.sub(pat,rewrite,text,flags=re.M);assert count==2389
(o/'master_core_infra.tcl').write_text(new)
old_by={c['name']:c for c in json.load((k/'core_infra_plan.json').open())['core_tree']['nodes']}
new_by={c['name']:c for c in plan['core_tree']['nodes']}
def path_len(by,n):
 node=by[n];p=node['parent']
 if p.startswith('port:'):return 0.
 return sum(abs(a-b)for a,b in zip(node['xy_um'],by[p]['xy_um']))+path_len(by,p)
extra=[path_len(new_by,n)-path_len(old_by,n)for n in old_by]
report=dict(scope='SC_SEED_PLAN_TAP_AWARE_CORRECTION_BEFORE_GPL',nodes=2389,changed=len(changes),native_fixed_obstacles=len(obs),old_conflicting_cells=len(bad),new_conflicts=0,max_node_L1_displacement_um=max((abs(c['dx_um'])+abs(c['dy_um'])for c in changes),default=0),max_root_to_node_extra_L1_um=max(extra),clock_graph_counts_stages_unchanged=True,cycles_added=0,rows_changed=sum(c['dy_um']!=0 for c in changes),changes=changes)
(o/'seed_site_report.json').write_text(json.dumps(report,indent=1)+'\n');print(json.dumps({k:v for k,v in report.items()if k!='changes'}))
