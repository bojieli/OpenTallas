import odb,json,hashlib
from pathlib import Path
D=odb.dbDatabase.create();odb.read_db(D,'/checkpoint/5_1_grt.odb');b=D.getChip().getBlock();l=D.getTech().findLayer('M7');x0,x1,y=17280,22464,56160
G=b.findTrackGrid(l);tracks=list(G.getGridX());tracks=[x for x in tracks if x0<=x<x1]
PG=[];clock=[];other=[]
for n in b.getNets():
 for sw in n.getSWires():
  for z in sw.getWires():
   if z.isVia() or z.getTechLayer()!=l:continue
   if z.yMin()<=y<=z.yMax() and z.xMin()<x1 and z.xMax()>x0:PG.append(dict(net=n.getName(),x0=z.xMin(),x1=z.xMax(),y0=z.yMin(),y1=z.yMax()))
 for g in n.getGuides():
  if g.getLayer()!=l:continue
  z=g.getBox()
  if z.yMin()<=y<z.yMax() and z.xMin()<x1 and z.xMax()>x0:
   row=dict(net=n.getName(),x0=z.xMin(),x1=z.xMax(),y0=z.yMin(),y1=z.yMax())
   (clock if n.getSigType()=='CLOCK' else other).append(row)
blocked=set()
for q in PG:
 blocked.update(x for x in tracks if q['x0']-128<=x<=q['x1']+128)
for q in clock+other:
 blocked.update(x for x in tracks if q['x0']<=x<q['x1'])
usable=[x for x in tracks if x not in blocked]
r=dict(native_track_X_DBU=tracks,PG_at_boundary=PG,clock_guides_at_boundary=clock,other_guides_at_boundary=other,guide_unreserved_track_candidates_DBU=usable,guide_capacity_only_not_detailed_route_measurement=True,private_factor_bits_required=12,DBU=b.getDbUnitsPerMicron(),ODB_sha256=hashlib.sha256(Path('/checkpoint/5_1_grt.odb').read_bytes()).hexdigest())
Path('/output/private_tracks.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
