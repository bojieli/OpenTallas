import json, sys, odb
D=odb.dbDatabase.create(); odb.read_db(D,sys.argv[1]); B=D.getChip().getBlock(); U=B.getDbUnitsPerMicron()
def rect(b):return [b.xMin()/U,b.yMin()/U,b.xMax()/U,b.yMax()/U]
r={'outline':rect(B.getDieArea()),'clock':[],'macro':[],'sinks':[],'wires':[]}
ci=set()
for n in B.getNets():
 if n.getSigType()!='CLOCK':continue
 for t in n.getITerms():ci.add(t.getInst().getName())
 w=n.getWire()
 if w:
  it=odb.dbWirePathItr();it.begin(w);p=odb.dbWirePath();s=odb.dbWirePathShape()
  while it.getNextPath(p):
   while it.getNextShape(s):
    if not s.shape.isVia():r['wires'].append(rect(s.shape))
for i in B.getInsts():
 if i.getMaster().isBlock():r['macro'].append(rect(i.getBBox()))
 elif i.getName() in ci:r['clock'].append(rect(i.getBBox()))
with open(sys.argv[2],'w') as f:json.dump(r,f)
print('GEOMETRY_DONE',len(r['clock']),len(r['wires']),len(r['macro']))
