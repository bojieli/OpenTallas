"""Read-only native comparison of actual retained route input and output. Run openroad -python."""
import odb,json,hashlib,os,sys
TARGET=r'u_u_rsq1.u_rsq.g_nr\[0\].g_h.d_h.genblk1.g_line.line\[238\]'
def digest(x):return hashlib.sha256(repr(x).encode()).hexdigest()
def snapshot(path):
 d=odb.dbDatabase.create();odb.read_db(d,path);b=d.getChip().getBlock();out={'instances':{},'nets':{},'bterms':{}}
 for i in b.getInsts():
  ports=sorted((t.getMTerm().getName(),t.getNet().getName() if t.getNet() else None) for t in i.getITerms())
  out['instances'][i.getName()]={'master':i.getMaster().getName(),'rest':digest((tuple(i.getLocation()),str(i.getOrient()),str(i.getPlacementStatus()),i.isDoNotTouch(),ports))}
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

A=snapshot('/work/final_5_1_grt.odb');B=snapshot('/work/LVT_DATA_GEOMETRY_CHECKPOINT.odb');proposal=json.load(open('/work/MODEL_PREP.json'));allowed={t['name']:t for t in proposal['targets']};errors=[]
assert len(allowed)==4 and len(A['instances'])==272550
if set(A['instances'])!=set(B['instances']):errors.append({'category':'instance_set'})
for name,old in A['instances'].items():
 now=B['instances'].get(name)
 if now is None:continue
 if name in allowed:
  t=allowed[name]
  if old['master']!=t['old'] or now['master']!=t['new'] or old['rest']!=now['rest']:errors.append({'instance':name,'category':'allowed_master_or_other_field'})
 elif old!=now:errors.append({'instance':name,'category':'unexpected_instance_delta'})
if A['bterms']!=B['bterms']:errors.append({'category':'bterms'})
if set(A['nets'])!=set(B['nets']):errors.append({'category':'net_set'})
for name,old in A['nets'].items():
 now=B['nets'].get(name)
 if now is not None:
  for field in old:
   if old[field]!=now[field]:errors.append({'net':name,'field':field})
result={'pass':not errors,'instances':len(A['instances']),'nets':len(A['nets']),'changed_masters':sorted(allowed),'errors':errors,'scope':'Only4expectedDATAmasters changed; allotherinstances/poses/status/DNT/ITerm incidence/BTerms/source/CLOCK/SIGNALguides/regular/specialPGwire bytecode exact'}
json.dump(result,open('/work/native_import_compare.json','w'),indent=2);print(json.dumps(result));sys.exit(0 if not errors else 1)
