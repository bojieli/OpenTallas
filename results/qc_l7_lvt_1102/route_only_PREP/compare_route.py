"""Read-only native comparison of actual retained route input and output. Run openroad -python."""
import odb,json,hashlib,os,sys
TARGET=r'u_u_rsq1.u_rsq.g_nr\[0\].g_h.d_h.genblk1.g_line.line\[238\]'
def digest(x):return hashlib.sha256(repr(x).encode()).hexdigest()
def snapshot(path):
 d=odb.dbDatabase.create();odb.read_db(d,path);b=d.getChip().getBlock();out={'instances':{},'nets':{},'bterms':{}}
 for i in b.getInsts():
  ports=sorted((t.getMTerm().getName(),t.getNet().getName() if t.getNet() else None) for t in i.getITerms())
  out['instances'][i.getName()]=digest((i.getMaster().getName(),tuple(i.getLocation()),str(i.getOrient()),str(i.getPlacementStatus()),i.isDoNotTouch(),ports))
 for n in b.getNets():
  wire=n.getWire();regular=digest([(wire.getOpcode(k),wire.getData(k)) for k in range(wire.length())]) if wire else None
  special=[]
  for sw in n.getSWires():
   shapes=[]
   for q in sw.getWires():
    via=(q.getTechVia() or q.getBlockVia()) if q.isVia() else None
    shapes.append((q.getTechLayer().getName() if q.getTechLayer() else None,q.xMin(),q.yMin(),q.xMax(),q.yMax(),via.getName() if via else None,str(q.getWireShapeType())))
   special.append((str(sw.getWireType()),shapes))
  topology=sorted([('i',t.getInst().getName(),t.getMTerm().getName()) for t in n.getITerms()]+[('b',t.getName()) for t in n.getBTerms()])
  guides=sorted((g.getLayer().getName(),g.getBox().xMin(),g.getBox().yMin(),g.getBox().xMax(),g.getBox().yMax()) for g in n.getGuides())
  out['nets'][n.getName()]={'wire':regular,'special':digest(special),'source':digest((str(n.getSigType()),n.isSpecial(),topology)),'guides':digest(guides)}
 for t in b.getBTerms():
  out['bterms'][t.getName()]=digest((t.getNet().getName() if t.getNet() else None,str(t.getIoType()),str(t.getSigType()),sorted((str(p.getPlacementStatus()),q.getTechLayer().getName(),q.xMin(),q.yMin(),q.xMax(),q.yMax()) for p in t.getBPins() for q in p.getBoxes())))
 return out
A=snapshot('/work/LVT_DATA_GEOMETRY_CHECKPOINT.odb');B=snapshot('/route/actual_after_route.odb');errors=[]
for c in ['instances','bterms']:
 if A[c]!=B[c]:errors.append({'category':c,'changed':[k for k in sorted(set(A[c])|set(B[c])) if A[c].get(k)!=B[c].get(k)]})
if set(A['nets'])!=set(B['nets']):errors.append({'category':'net_names'})
for n,old in A['nets'].items():
 if n not in B['nets']:continue
 for f in ['source','special','guides']:
  if old[f]!=B['nets'][n][f]:errors.append({'net':n,'field':f})
r={'pass':not errors,'instances':len(A['instances']),'nets':len(A['nets']),'errors':errors,'scope':'all source masters/poses/status/DNT/ITerm incidence/BTerms/net types+topology/specialPG/guides exact; ordinaryDRTregularwires may change'}
json.dump(r,open('/route/DRT_SOURCE_COMPARE.json','w'),indent=2);print(json.dumps(r));sys.exit(bool(errors))
