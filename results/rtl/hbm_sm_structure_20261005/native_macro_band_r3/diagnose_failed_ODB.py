import odb,json,re,collections,sys,bisect
from pathlib import Path
w=Path('/diag');d=odb.dbDatabase.create();odb.read_db(d,'/work/results/asap7/smh_tile_toW_tileW_a3/base/5_1_grt-failed.odb')
b=d.getChip().getBlock();tech=d.getTech();dbu=b.getDbUnitsPerMicron()
def box(r):return [r.xMin()/dbu,r.yMin()/dbu,r.xMax()/dbu,r.yMax()/dbu]
def overlap(a,c):return a[0]<c[2] and c[0]<a[2] and a[1]<c[3] and c[1]<a[3]
raw=(w/'congestion.rpt').read_text();rows=[];names=set()
for c in raw.split('violation type: ')[1:]:
 cap,u,ov=map(int,re.search(r'capacity:(\d+) usage:(\d+) congestion:(\d+)',c).groups());bb=list(map(float,re.search(r'bbox = \(([^,]+), ([^)]+)\) - \(([^,]+), ([^)]+)\)',c).groups()));nets=re.search(r'srcs: (.*)',c)[1].split()
 # Report escapes both square brackets; actual db names are unescaped.
 nets=[n[4:].replace('\\\\','\\') for n in nets];names.update(nets);rows.append(dict(capacity=cap,usage=u,overflow=ov,bbox=bb,nets=nets,direction=c.splitlines()[0]))
boxes=json.loads((w/'keepouts.json').read_text());endpoints=[];netrec={};samples={};macro=[]
for i in b.getInsts():
 if i.getMaster().isBlock():macro.append(dict(name=i.getName(),master=i.getMaster().getName(),bbox=box(i.getBBox()),location=list(i.getLocation()),orientation=str(i.getOrient())))
for n in b.getNets():
 if n.getName() not in names:continue
 eps=[]
 for t in n.getITerms():
  i=t.getInst();r=box(t.getBBox());ep=dict(inst=i.getName(),master=i.getMaster().getName(),pin=t.getMTerm().getName(),bbox=r,macro=i.getMaster().isBlock(),inside_keepout=[j for j,q in enumerate(boxes) if overlap(r,q)])
  ep['layers']=sorted(set(q[0].getName() for q in t.getGeometries()))
  eps.append(ep);endpoints.append(ep)
  if ep['macro'] and 'macro_geometry' not in samples:
   samples['macro_geometry']=str(t.getGeometries())[:1600]
 for t in n.getBTerms():
  for p in t.getBPins():
   for z in p.getBoxes():eps.append(dict(port=t.getName(),layer=z.getTechLayer().getName(),bbox=box(z.getBox())))
 netrec[n.getName()]=dict(signal_type=str(n.getSigType()),endpoints=eps)
grid=b.getGCellGrid();xs=list(grid.getGridX());ys=list(grid.getGridY());samples['grid_xy']=[xs[:4],ys[:4]]
for r in rows:
 x=bisect.bisect_right(xs,round((r['bbox'][0]+r['bbox'][2])/2*dbu))-1;y=bisect.bisect_right(ys,round((r['bbox'][1]+r['bbox'][3])/2*dbu))-1
 r['grid_idx']=[x,y];r['layers']={}
 for k in range(2,7):
  l=tech.findLayer('M'+str(k));r['layers'][l.getName()]=dict(capacity=grid.getCapacity(l,x,y),usage=grid.getUsage(l,x,y))
pg=[];pgcnt=collections.Counter();region=[110,197,215,299]
for n in b.getNets():
 if str(n.getSigType()) not in ['POWER','GROUND']:continue
 for sw in n.getSWires():
  for z in sw.getWires():
   r=[z.xMin()/dbu,z.yMin()/dbu,z.xMax()/dbu,z.yMax()/dbu]
   if not overlap(r,region):continue
   via=z.isVia();l=z.getTechLayer();ln=l.getName() if l else 'VIA'
   pgcnt[ln]+=1
   if not via or any(overlap(r,q) for q in boxes):
    pg.append(dict(net=n.getName(),layer=ln,via=via,bbox=r))
    if via and 'PG_via' not in samples:samples['PG_via']=dict(bbox=r,geometry=str(z.getTechVia())[:1500])
(w/'topology.json').write_text(json.dumps(dict(dbu=dbu,macros=macro,rows=rows,nets=netrec,endpoint_count=len(endpoints),endpoints_in_keepouts=sum(bool(e['inside_keepout']) for e in endpoints),PG_region_box=region,PG_region_counts=pgcnt,PG_shapes=pg,samples=samples),indent=2)+'\n')
print('DONE',len(rows),len(netrec),len(endpoints),sum(bool(e['inside_keepout']) for e in endpoints),'PG',pgcnt)
