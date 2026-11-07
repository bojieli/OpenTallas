import openroad as ora,odb,json,sys
from pathlib import Path
tech=ora.Tech();design=ora.Design(tech);design.readDb(sys.argv[1]);b=design.getBlock();u=b.getDbUnitsPerMicron();d={'u':u,'cells':[],'macros':[],'pins':[],'clock':[]}
for i in b.getInsts():
 if 'FILLER' in i.getMaster().getName().upper() or 'DECAP' in i.getMaster().getName().upper():continue
 bb=i.getBBox();row=[i.getName(),bb.xMin()/u,bb.yMin()/u,bb.xMax()/u,bb.yMax()/u]
 d['macros' if i.getMaster().isBlock() else 'cells'].append(row)
for p in b.getBTerms():
 if p.getSigType() in ('POWER','GROUND'):continue
 for bp in p.getBPins():
  for x in bp.getBoxes():d['pins'].append([p.getName(),(x.xMin()+x.xMax())/(2*u),(x.yMin()+x.yMax())/(2*u)])
for n in b.getNets():
 if n.getSigType()!='CLOCK':continue
 pts=[]
 for it in n.getITerms():
  z=it.getInst().getBBox();pts.append([(z.xMin()+z.xMax())/(2*u),(z.yMin()+z.yMax())/(2*u)])
 if len(pts)>1:d['clock'].append([n.getName(),pts])
Path(sys.argv[2]).write_text(json.dumps(d))
g=b.getGCellGrid()
if g:
 xs=list(g.getGridX());ys=list(g.getGridY());maps=[]
 if len(xs)>1 and len(ys)>1:
  for layer in b.getDb().getTech().getLayers():
   if layer.getRoutingLevel()<2:continue
   rows=[]
   for yi in range(len(ys)-1):
    rows.append([[int(g.getUsage(layer,xi,yi)),int(g.getCapacity(layer,xi,yi))] for xi in range(len(xs)-1)])
   maps.append({'layer':layer.getName(),'cells':rows})
  d['congestion']={'xs':[x/u for x in xs],'ys':[y/u for y in ys],'maps':maps}
Path(sys.argv[2]).write_text(json.dumps(d))
d['clock_wires']=[]
for n in b.getNets():
 if n.getSigType()!='CLOCK' or not n.getWire():continue
 it=odb.dbWirePathItr();it.begin(n.getWire());path=odb.dbWirePath();shape=odb.dbWirePathShape()
 while it.getNextPath(path):
  while it.getNextShape(shape):
   z=shape.shape
   if not z.isSegment():continue
   layer=z.getTechLayer();r=z.getBox()
   d['clock_wires'].append([n.getName(),layer.getName() if layer else '?',r.xMin()/u,r.yMin()/u,r.xMax()/u,r.yMax()/u])
Path(sys.argv[2]).write_text(json.dumps(d))
