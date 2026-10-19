"""Read immutable route, modify exact missing PG bindings only, export physical receipts."""
import odb,json,hashlib,gzip
from pathlib import Path
out=Path('/proof'); root=next(Path('/route').glob('work/orfs/results/asap7/*/base'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def save(n,j):
 with gzip.open(out/(n+'.json.gz'),'wt') as f:json.dump(j,f,separators=(',',':'))
def load(p):
 d=odb.dbDatabase.create();odb.read_db(d,str(p));return d,d.getChip().getBlock()
def digest(b):
 j={'insts':[(i.getName(),i.getMaster().getName(),i.getOrigin(),str(i.getOrient()),str(i.getPlacementStatus()),i.isDoNotTouch()) for i in b.getInsts()], 'signal':[(i.getName(),t.getMTerm().getName(),t.getNet().getName() if t.getNet() else None) for i in b.getInsts() for t in i.getITerms() if str(t.getMTerm().getSigType()) not in ('POWER','GROUND')], 'bterms':[(t.getName(),t.getNet().getName() if t.getNet() else None) for t in b.getBTerms()], 'wire_inventory':[(n.getName(),n.getWire().getId()) for n in b.getNets() if n.getWire()]}
 # Native detailed route serialization checked separately through DEF sections.
 return {k:hashlib.sha256(json.dumps(v,sort_keys=True).encode()).hexdigest() for k,v in j.items()}
def missing(b):return [(i.getName(),t.getMTerm().getName(),i.getMaster().getName(),str(t.getMTerm().getSigType())) for i in b.getInsts() for t in i.getITerms() if str(t.getMTerm().getSigType()) in ('POWER','GROUND') and not t.getNet()]
stages=[]
for name in ['2_4_floorplan_pdn.odb','3_place.odb','4_1_cts.odb','4_cts.odb','5_1_grt.odb','5_route.odb','6_final.odb']:
 d,b=load(root/name); m=missing(b); stages.append({'stage':name,'sha256':sha(root/name),'instances':len(b.getInsts()),'missing':m});del b,d
save('stage_pg',stages)
p=root/'6_final.odb';d,b=load(p);oldsha=sha(p);assert oldsha=='851903b3ea016e159ac50862a1c80c5b3f4c6276e13df27789182736ce4e72c6'
m=missing(b);assert len(m)==644 and len({x[0] for x in m})==322 and all(x[2]=='BUFx24_ASAP7_75t_R' for x in m)
old=digest(b);odb.write_def(b,str(out/'before.def'))
for ins,pin,master,role in m:
 net=b.findNet('VDD' if role=='POWER' else 'VSS');assert str(net.getSigType())==role
 inst=b.findInst(ins); protected=inst.isDoNotTouch(); inst.setDoNotTouch(False); inst.findITerm(pin).connect(net); inst.setDoNotTouch(protected)
assert not missing(b);assert digest(b)==old
odb.write_db(d,str(out/'clone.odb'));odb.write_def(b,str(out/'after.def'))
# Shape entries: layer, bbox, net role, owner. Real via cut instances link own enclosing metal.
shapes=[]; vias=[]; pins=[]; terminals=[]
def rect(s):return [s.xMin(),s.yMin(),s.xMax(),s.yMax()]
def add(layer,box,role,owner):
 shapes.append([layer,box,role,owner]);return len(shapes)-1
for n in b.getNets():
 role=str(n.getSigType())
 if role not in ('POWER','GROUND'):continue
 for sw in n.getSWires():
  for s in sw.getWires():
   if not s.isVia():add(s.getTechLayer().getName(),rect(s),role,'wire:'+n.getName());continue
   v=s.getTechVia() or s.getBlockVia(); x,y=s.getViaXY(); ids=[]
   for z in v.getBoxes():
    layer=z.getTechLayer(); box=[x+z.xMin(),y+z.yMin(),x+z.xMax(),y+z.yMax()]
    ids.append(add(layer.getName(),box,role,'via:'+v.getName()))
   vias.append({'name':v.getName(),'xy':[x,y],'ids':ids})
for i in b.getInsts():
 ox,oy=i.getOrigin();orient=str(i.getOrient());assert orient in ('R0','MX','MY','R180')
 for t in i.getITerms():
  mt=t.getMTerm();role=str(mt.getSigType())
  if role not in ('POWER','GROUND'):continue
  assert t.getNet() and str(t.getNet().getSigType())==role
  ids=[]
  for mp in mt.getMPins():
   for z in mp.getGeometry():
    assert not z.isVia()
    xs=[ox+(-x if orient in ('MY','R180') else x) for x in [z.xMin(),z.xMax()]];ys=[oy+(-y if orient in ('MX','R180') else y) for y in [z.yMin(),z.yMax()]]
    ids.append(add(z.getTechLayer().getName(),[min(xs),min(ys),max(xs),max(ys)],role,'pin:'+i.getName()+'/'+mt.getName()))
  pins.append({'instance':i.getName(),'pin':mt.getName(),'role':role,'ids':ids})
for t in b.getBTerms():
 role=str(t.getSigType())
 if role not in ('POWER','GROUND'):continue
 ids=[]
 for bp in t.getBPins():
  for z in bp.getBoxes():ids.append(add(z.getTechLayer().getName(),rect(z),role,'bpin:'+t.getName()))
 terminals.append({'name':t.getName(),'role':role,'ids':ids})
tech=d.getTech(); layers={l.getName():{'type':str(l.getType()),'level':l.getRoutingLevel()} for l in tech.getLayers()}
save('metal',{'units':b.getDbUnitsPerMicron(),'grid':tech.getManufacturingGrid(),'layers':layers,'shapes':shapes,'vias':vias,'pins':pins,'bterms':terminals})
summary={'original_odb_sha256':oldsha,'original_spef_sha256':sha(root/'6_final.spef'),'clone_odb_sha256':sha(out/'clone.odb'),'original_still_unchanged':sha(p)==oldsha,'invariants_before':old,'invariants_after':digest(b),'pg_pins_bound':len(m),'remaining_missing':len(missing(b)),'shapes':len(shapes),'via_instances':len(vias),'allowlist':m}
(out/'clone_summary.json').write_text(json.dumps(summary,indent=2)+'\n')
print('CLONE_DONE',len(m),len(shapes),len(vias))
