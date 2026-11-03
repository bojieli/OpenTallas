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
A=snapshot('/input/input.odb');B=snapshot('/prep/TARGET_RIPPED_GUIDE_INPUT.odb');errors=[]
for c in ['instances','bterms']:
 if A[c]!=B[c]: errors.append({'category':c})
if set(A['nets'])!=set(B['nets']):errors.append({'category':'net_names'})
for name,old in A['nets'].items():
 now=B['nets'][name]
 for f in (['source','special'] if name==TARGET else ['wire','special','source','guides']):
  if old[f]!=now[f]:errors.append({'net':name,'field':f})
if not A['nets'][TARGET]['wire'] or B['nets'][TARGET]['wire'] is not None:errors.append({'target':'expected_exact_target_wire_rip'})
d=odb.dbDatabase.create();odb.read_db(d,'/prep/TARGET_RIPPED_GUIDE_INPUT.odb');n=d.getChip().getBlock().findNet(TARGET)
actual=sorted((g.getLayer().getName(),g.getBox().xMin(),g.getBox().yMin(),g.getBox().xMax(),g.getBox().yMax()) for g in n.getGuides())
proposal=json.load(open('/prep/proposed_guides.json'));want=sorted((g['layer'],*(round(v*1000) for v in g['bbox'])) for g in proposal['guides'])
if actual!=want:errors.append({'target':'guide_roundtrip_mismatch','actual':actual,'expected':want})
result={'pass':not errors,'errors':errors,'instances':len(A['instances']),'nets':len(A['nets']),'guides':actual,'scope':'native guide roundtrip and exactly one target wire rip only; no route/STA/filler/physical closure'}
json.dump(result,open('/prep/GUIDE_INPUT_RESULT.json','w'),indent=2);print(json.dumps(result));sys.exit(bool(errors))
