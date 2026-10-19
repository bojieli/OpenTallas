"""Read-only conductor exporter extracted from39021a45e clone_export.py.
No clone modification code is executed. Same native geometry algorithm.
"""
import odb,json,hashlib,gzip,sys
from pathlib import Path
src=Path(sys.argv[1]);out=Path(sys.argv[2]);out.mkdir(parents=True,exist_ok=True)
d=odb.dbDatabase.create();odb.read_db(d,str(src));b=d.getChip().getBlock()
def save(n,j):
 with gzip.open(out/(n+'.json.gz'),'wt') as f:json.dump(j,f,separators=(',',':'))
# This exact single-domain candidate uses the reviewed VDD/VSS network only.
# Original39021 conductor graph keys by supply ROLE; refuse broader domains.
assert sorted((n.getName(),str(n.getSigType())) for n in b.getNets() if str(n.getSigType()) in ('POWER','GROUND')) == [('VDD','POWER'),('VSS','GROUND')]
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
print("READONLY_METAL_EXPORT",len(shapes),len(vias),len(pins))
