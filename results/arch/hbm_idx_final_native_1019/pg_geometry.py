import odb,json,hashlib
from pathlib import Path
src=Path('/input/6_final.odb'); db=odb.dbDatabase.create();odb.read_db(db,str(src));b=db.getChip().getBlock();out=Path('/proof');missing=[]
for i in b.getInsts():
 for t in i.getITerms():
  m=t.getMTerm()
  if str(m.getSigType()) not in ('POWER','GROUND') or t.getNet():continue
  rects=[]
  for mp in m.getMPins():
   for s in mp.getGeometry():
    ox,oy=i.getOrigin(); orient=str(i.getOrient()); assert orient in ('R0','MX','MY','R180'),orient
    xs=[s.xMin(),s.xMax()];ys=[s.yMin(),s.yMax()]
    xs=[ox+(-x if orient in ('MY','R180') else x) for x in xs];ys=[oy+(-y if orient in ('MX','R180') else y) for y in ys]
    rects.append(dict(layer=s.getTechLayer().getName(),box=[min(xs),min(ys),max(xs),max(ys)]))
  bb=i.getBBox();missing.append(dict(instance=i.getName(),master=i.getMaster().getName(),pin=m.getName(),role=str(m.getSigType()),orient=str(i.getOrient()),bbox=[bb.xMin(),bb.yMin(),bb.xMax(),bb.yMax()],rects=rects))
rails=[]
for n in b.getNets():
 if str(n.getSigType()) not in ('POWER','GROUND'):continue
 for sw in n.getSWires():
  for s in sw.getWires():
   v=(s.getTechVia() or s.getBlockVia()) if s.isVia() else None
   rails.append(dict(net=n.getName(),role=str(n.getSigType()),via=s.isVia(),via_name=v.getName() if v else None,via_layers=sorted(set(z.getTechLayer().getName() for z in v.getBoxes())) if v else [],layer=s.getTechLayer().getName() if s.getTechLayer() else None,box=[s.xMin(),s.yMin(),s.xMax(),s.yMax()]))
rows=[]
for r in b.getRows():
 z=r.getBBox();rows.append(dict(name=r.getName(),orient=str(r.getOrient()),bbox=[z.xMin(),z.yMin(),z.xMax(),z.yMax()]))
j=dict(odb_sha256=hashlib.sha256(src.read_bytes()).hexdigest(),units=b.getDbUnitsPerMicron(),missing=missing,rails=rails,rows=rows)
(out/'pg_geometry.json').write_text(json.dumps(j,separators=(',',':'))+'\n');print('PG_GEOMETRY',len(missing),len(rails),len(rows))
