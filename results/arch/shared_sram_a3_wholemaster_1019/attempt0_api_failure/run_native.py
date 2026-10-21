#!/usr/bin/env python3
import os,json,hashlib,sys
from pathlib import Path
import odb,openroad
BASE=Path('/work'); P=BASE/os.environ['A3_CASE']; os.chdir(P)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert sha('/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad')=='21eda99eeae7eccb22ca64ad28949c08a6c01dcece3ccb23e2206d635f8d2846'
assert sha(BASE/'input/asap7_tech.lef')=='7694bf4f8ef2f9745e4579f454788a0cf048e8605320f32d1d83ec540ed4ca41'
tech=openroad.Tech();tech.readLef(str(BASE/'input/asap7_tech.lef'))
design=openroad.Design(tech);design.readDef(str(P/'empty.def'))
db=tech.getDB(); block=design.getBlock(); t=db.getTech()
# Dump actual imported rule objects, preserving every callable scalar getter and rule class.
def dump_obj(obj):
 out={'class':type(obj).__name__}
 for n in dir(obj):
  if n.startswith(('get','is','has')) and not n.startswith(('getTech','getDb','getOwner','getBlock','getDatabase','getImpl','getObject')):
   try:
    value=getattr(obj,n)()
    if isinstance(value,(str,int,float,bool,list,tuple)) or value is None:out[n]=value
   except Exception as e:out[n]={'unavailable':str(e)}
 return out
rules={'tech_dbu':t.getDbUnitsPerMicron(),'manufacturing_grid':t.getManufacturingGrid(),'layers':{}}
for ln in ['M4','M5']:
 l=t.findLayer(ln);d=dump_obj(l)
 for n in ['getTechLayerWidthTableRules','getTechLayerCornerSpacingRules','getTechLayerEolKeepOutRules','getTechLayerSpacingEolRules','getTechLayerSpacingTablePrlRules']:
  try:d[n]=[dump_obj(v) for v in getattr(l,n)()]
  except Exception as e:d[n]={'unavailable':str(e)}
 rules['layers'][ln]=d
(P/'loaded_rules.json').write_text(json.dumps(rules,indent=2,default=str)+'\n')
coupon=json.loads((P/'coupon.json').read_text()); ledger=[]
for ci,c in enumerate(coupon['cases']):
 bynet={}
 for a in c['shapes']:bynet.setdefault(a['net'],{'shapes':[],'vias':[]})['shapes'].append(a)
 for v in c['vias']:bynet.setdefault(v['net'],{'shapes':[],'vias':[]})['vias'].append(v)
 for ni,(name,shapes) in enumerate(bynet.items()):
  net=odb.dbNet.create(block,f'case{ci}_net{ni}'); net.setSigType('SIGNAL')
  expected_boxes=[]
  wire=odb.dbWire.create(net);enc=odb.dbWireEncoder();enc.begin(wire)
  typ=c['wire_status']
  for a in shapes['shapes']:
   x0,y0,x1,y1=a['rect_nm'];l=t.findLayer(a['layer']);enc.newPath(l,typ)
   if a['layer']=='M4' and y1-y0==24 and x1-x0>24:
    enc.addPoint(x0+12,y0+12);enc.addPoint(x1-12,y0+12);representation='segment'
   elif a['layer']=='M5' and x1-x0==24 and y1-y0>24:
    enc.addPoint(x0+12,y0+12);enc.addPoint(x0+12,y1-12);representation='segment'
   else:
    enc.addPoint(x0,y0);enc.addRect(0,0,x1-x0,y1-y0);representation='patch'
   expected_boxes.append((a['layer'],tuple(a['rect_nm'])))
   ledger.append(dict(source_identity=a.get('source_identity'),case=ci,net=net.getName(),source_net=name,layer=a['layer'],rect_nm=a['rect_nm'],status=c['wire_status'],representation=representation,role=a.get('role')))
  for v in shapes['vias']:
   via=t.findVia(v['name']); assert via is not None
   x,y=v['center_nm'];enc.newPath(t.findLayer('M4'),typ);enc.addPoint(x,y);enc.addTechVia(via)
   native=[dict(layer=b.getTechLayer().getName(),rect_nm=[b.xMin()+x,b.yMin()+y,b.xMax()+x,b.yMax()+y]) for b in via.getBoxes()]
   expected={'M4':v['m4_rect_nm'],'M5':v['m5_rect_nm'],'V4':v['cut_rect_nm']}
   assert len(native)==3 and all(z['rect_nm']==expected[z['layer']] for z in native),(v,native)
   expected_boxes.extend((z['layer'],tuple(z['rect_nm'])) for z in native)
   ledger.append(dict(source_identity=v.get('identity'),case=ci,net=net.getName(),source_net=name,via=v['name'],center_nm=v['center_nm'],native_boxes=native,status=c['wire_status']))
  enc.end()
  # Re-extract actual encoded ODB boxes, including every native cut/enclosure.
  from collections import Counter
  actual_boxes=[];it=odb.dbWireShapeItr();it.begin(wire);shape=odb.dbShape()
  while it.next(shape):
   if shape.isVia():
    via=shape.getTechVia();x,y=shape.getViaXY()
    actual_boxes.extend((b.getTechLayer().getName(),(b.xMin()+x,b.yMin()+y,b.xMax()+x,b.yMax()+y)) for b in via.getBoxes())
   else:
    r=shape.getBox();actual_boxes.append((shape.getTechLayer().getName(),(r.xMin(),r.yMin(),r.xMax(),r.yMax())))
  assert Counter(actual_boxes)==Counter(expected_boxes),(name,actual_boxes,expected_boxes)
  assert wire.getWireType()=='ROUTED' and net.getSigType()=='SIGNAL'
  (P/f'odb_net_{ci}_{ni}.json').write_text(json.dumps(dict(source_net=name,native_net=net.getName(),exact_box_multiset=True,actual_boxes=actual_boxes,wire_type=wire.getWireType(),sig_type=net.getSigType()),indent=2)+'\n')
(P/'native_shape_ledger.json').write_text(json.dumps(ledger,indent=2)+'\n')
design.evalTclString(f'write_db {P}/original.odb')
design.evalTclString(f'write_def {P}/original.def')
print('NATIVE_INPUT_READY',len(ledger),'objects',flush=True)
# Native GC only: neither pin access nor routing nor repair is invoked.
design.evalTclString('set_thread_count 1')
design.evalTclString(f'if {{[catch {{drt::check_drc -output_file {P}/all_markers.rpt -marker_name A3_ORIGINAL}} err]}} {{error $err}}')
assert (P/'all_markers.rpt').is_file()
print('NATIVE_ORIGINAL_CHECK_COMPLETE',flush=True)
# ROI reports are native checker invocations on exactly the same unchanged original ODB.
for i,c in enumerate(coupon['cases']):
 box=' '.join(str(z) for z in c['score_roi_nm'])
 result=design.evalTclString(f'if {{[catch {{drt::check_drc -box {{{box}}} -output_file {P}/roi_{i:02d}.rpt -marker_name CASE_{i}}} err]}} {{error $err}}')
 assert (P/f'roi_{i:02d}.rpt').is_file(), (i,result)
 print('CASE_COMPLETE',i,c['name'],flush=True)
design.evalTclString(f'write_db {P}/checked_unrepaired.odb')
