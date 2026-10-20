import odb, os, json, hashlib
from pathlib import Path
p=Path(os.environ['AUDIT_ODB']); db=odb.dbDatabase.create(); odb.read_db(db,str(p)); b=db.getChip().getBlock(); scale=b.getDbUnitsPerMicron()
rows=[]; skipped={}; missing=[]; counts={}
for n in b.getNets():
 typ=str(n.getSigType()); counts[typ]=counts.get(typ,0)+1
 if typ in ('POWER','GROUND','CLOCK'):continue
 pts=[]
 for t in n.getITerms():
  v=t.getAvgXY()
  if not v[0]:missing.append(t.getInst().getName()+'/'+t.getMTerm().getName());continue
  pts.append((v[1]/scale,v[2]/scale,t.getInst().getName()+'/'+t.getMTerm().getName()))
 for t in n.getBTerms():
  for pin in t.getBPins():
   for box in pin.getBoxes():
    pts.append(((box.xMin()+box.xMax())/2/scale,(box.yMin()+box.yMax())/2/scale,'PORT/'+t.getName()))
 if len(pts)<2:continue
 candidates=[]
 for sx,sy in [(1,1),(1,-1)]:
  a=min(pts,key=lambda v:sx*v[0]+sy*v[1]);z=max(pts,key=lambda v:sx*v[0]+sy*v[1]);candidates.append((abs(a[0]-z[0])+abs(a[1]-z[1]),a,z))
 dist,a,z=max(candidates)
 rows.append(dict(net=n.getName(),type=typ,diameter_um=round(dist,6),a=a,z=z,term_points=len(pts)))
rows.sort(key=lambda r:r['diameter_um'],reverse=True)
out=dict(schema='opentallas.placed_net_diameter.v1',scope='all non-PG non-CLOCK net terminal centers, all pairs Manhattan diameter; direct nets only, not full sequential cone path length',odb=str(p),odb_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),limit_um=405,net_type_counts=counts,checked_nets=len(rows),missing_pin_geometry=missing,max_um=rows[0]['diameter_um'],over_limit_count=sum(r['diameter_um']>405 for r in rows),top=rows[:100],over_limit=[r for r in rows if r['diameter_um']>405])
Path(os.environ['AUDIT_OUT']).write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({k:v for k,v in out.items() if k not in ('top','over_limit','missing_pin_geometry')}))
