import odb,json
from pathlib import Path
db=odb.dbDatabase.create(); odb.read_db(db,'/work/fixture.odb'); block=db.getChip().getBlock()
def rr(b): return [b.xMin(),b.yMin(),b.xMax(),b.yMax()]
shapes=[]
for net in block.getNets():
 for wire in net.getSWires():
  for s in wire.getWires():
   if s.isVia():
    v=s.getBlockVia() or s.getTechVia()
    x,y=s.getViaXY()
    for b in v.getBoxes():
     if b.getTechLayer().getType()=='ROUTING':
      a,c,d,e=rr(b);shapes.append([net.getName(),b.getTechLayer().getName(),a+x,c+y,d+x,e+y,'via'])
   else: shapes.append([net.getName(),s.getTechLayer().getName(),*rr(s),'wire'])
instances=[]
for inst in block.getInsts():
 m=inst.getMaster(); instances.append(dict(name=inst.getName(),orient=inst.getOrient(),bbox=rr(inst.getBBox()),width=m.getWidth(),height=m.getHeight(),
 obs=[[b.getTechLayer().getName(),*rr(b)] for b in m.getObstructions()],
 pins=[[t.getName(),t.getSigType(),b.getTechLayer().getName(),*rr(b)] for t in m.getMTerms() for p in t.getMPins() for b in p.getGeometry()]))
Path('/work/geometry.json').write_text(json.dumps(dict(shapes=shapes,instances=instances)))
print('GEOMETRY_EXPORTED',len(shapes))
