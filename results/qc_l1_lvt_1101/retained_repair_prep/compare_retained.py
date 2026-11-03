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
A=snapshot(os.environ['OT_RETAINED_A']);B=snapshot(os.environ['OT_RETAINED_B']);errors=[]
for category in ['instances','bterms']:
 if A[category]!=B[category]:errors.append({'category':category,'changed':[k for k in sorted(set(A[category])|set(B[category])) if A[category].get(k)!=B[category].get(k)]})
if set(A['nets'])!=set(B['nets']):errors.append({'category':'net_names'})
for name,old in A['nets'].items():
 now=B['nets'].get(name)
 if now is None:continue
 fields=['special','source'] if name==TARGET else ['wire','special','source','guides']
 for field in fields:
  if old[field]!=now[field]:errors.append({'net':name,'field':field})
assert TARGET in A['nets'] and TARGET in B['nets'];target_changed=A['nets'][TARGET]['wire']!=B['nets'][TARGET]['wire']
if B['nets'][TARGET]['wire'] is None:errors.append({'target':'no_routed_wire'})
result={'pass':not errors,'target':TARGET,'target_wire_changed':target_changed,'instances':len(A['instances']),'nets':len(A['nets']),'errors':errors,'scope':'all non-target wire bytecode, guides, source topology; all special routes, cells, BTerms exact'}
json.dump(result,open(os.environ['OT_RETAINED_RESULT'],'w'),indent=2);print(json.dumps(result));sys.exit(0 if not errors else 1)
