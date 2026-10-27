import odb,json
from pathlib import Path
D=odb.dbDatabase.create();odb.read_db(D,'/in/routed.odb');b=D.getChip().getBlock();u=b.getDbUnitsPerMicron()
g=json.loads(Path('/old/samenet_gaps_drc.json').read_text())['gap_list'];boxes=[v['box'] for v in g if v['gap']==.04]
boxes=[[round((q[0]-2)*u),round((q[1]-2)*u),round((q[2]+2)*u),round((q[3]+2)*u)] for q in boxes]
def hit(r):return any(r[0]<q[2] and q[0]<r[2] and r[1]<q[3] and q[1]<r[3] for q in boxes)
rows=[]
for n in b.getNets():
 for sw in n.getSWires():
  for s in sw.getWires():
   if s.isVia():continue
   l=s.getTechLayer().getName();r=[s.xMin(),s.yMin(),s.xMax(),s.yMax()]
   if l in ('M8','M9') and hit(r):rows.append(dict(net=n.getName(),layer=l,rect=r,special=True))
 w=n.getWire()
 if w:
  it=odb.dbWirePathItr();it.begin(w);pa=odb.dbWirePath();ps=odb.dbWirePathShape()
  while it.getNextPath(pa):
   while it.getNextShape(ps):
    sh=ps.shape
    if sh.isVia():continue
    l=sh.getTechLayer().getName();r=[sh.xMin(),sh.yMin(),sh.xMax(),sh.yMax()]
    if l in ('M8','M9') and hit(r):rows.append(dict(net=n.getName(),layer=l,rect=r,special=False))
Path('/out/source_boxes.json').write_text(json.dumps(dict(dbu_per_um=u,windows=boxes,shapes=rows),indent=1));print('EXTRACTED',len(boxes),len(rows))
