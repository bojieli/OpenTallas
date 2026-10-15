"""Read-only OpenROAD Python audit of actual routed metal above three rejected face pins."""
import argparse,hashlib,json,sys
from pathlib import Path
import odb

def rect(b): return [b.xMin(),b.yMin(),b.xMax(),b.yMax()]
def ov(a,b): return a[0]<b[2] and b[0]<a[2] and a[1]<b[3] and b[1]<a[3]
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
args=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else sys.argv[1:]
p=argparse.ArgumentParser();p.add_argument('--odb',required=True);p.add_argument('--out',required=True);a=p.parse_args(args)
before=sha(a.odb);db=odb.dbDatabase.create();odb.read_db(db,a.odb);block=db.getChip().getBlock();dbu=block.getDbUnitsPerMicron()
queries=[]
for name in ['dout[128]','dout[129]','dout[130]']:
 bt=block.findBTerm(name)
 if not bt:raise ValueError('Missing actual BTerm '+name)
 for bp in bt.getBPins():
  for box in bp.getBoxes():
   if box.getTechLayer().getName()=='M5':queries.append({'pin':name,'net':bt.getNet().getName(),'pin_box_dbu':rect(box),'above_layer':'M6','hits':[]})
if len(queries)!=3:raise ValueError('Expected exact3M5 facepins')

def check(net,layer,box,kind):
 if layer!='M6':return
 for q in queries:
  if ov(box,q['pin_box_dbu']):q['hits'].append({'net':net.getName(),'own_net':net.getName()==q['net'],'kind':kind,'rect_dbu':box})
for net in block.getNets():
 wire=net.getWire()
 if wire:
  dec=odb.dbWireDecoder();dec.begin(wire);prev=None
  while True:
   op=dec.next()
   if op==odb.dbWireDecoder.END_DECODE:break
   if op in (odb.dbWireDecoder.PATH,odb.dbWireDecoder.SHORT,odb.dbWireDecoder.VWIRE):prev=None
   elif op in (odb.dbWireDecoder.POINT,odb.dbWireDecoder.POINT_EXT):
    pt=list(dec.getPoint());layer=dec.getLayer()
    if prev is not None and layer:
     width=layer.getWidth()
     ndr=net.getNonDefaultRule()
     if ndr:
      rules=[r for r in ndr.getLayerRules() if r.getLayer()==layer]
      if len(rules)!=1:raise ValueError('Unresolved native nondefault width')
      width=max(width,rules[0].getWidth())
     # Conservative end extension: no false empty-space claim at a segment end.
     h=max(width/2,200)
     box=[min(prev[0],pt[0])-h,min(prev[1],pt[1])-h,max(prev[0],pt[0])+h,max(prev[1],pt[1])+h]
     check(net,layer.getName(),box,'routed_segment_conservative_200DBU_end_halo')
    prev=pt
   elif op in (odb.dbWireDecoder.TECH_VIA,odb.dbWireDecoder.VIA):
    pt=list(dec.getPoint());via=dec.getTechVia() if op==odb.dbWireDecoder.TECH_VIA else dec.getVia()
    for vb in via.getBoxes():
     if vb.getTechLayer().getName()=='M6':
      z=rect(vb);check(net,'M6',[z[0]+pt[0],z[1]+pt[1],z[2]+pt[0],z[3]+pt[1]],'actual_via_M6_metal')
    prev=pt
   elif op==odb.dbWireDecoder.JUNCTION:prev=list(dec.getPoint())
 for sw in net.getSWires():
  for box in sw.getWires():
   if not box.isVia():check(net,box.getTechLayer().getName(),rect(box),'special_wire')
   else:
    via=box.getTechVia() or box.getBlockVia()
    if via and any(b.getTechLayer().getName()=='M6' for b in via.getBoxes()):check(net,'M6',rect(box),'special_via_conservative_bbox')
for q in queries:
 q['classification']='foreign_metal_present' if any(not h['own_net'] for h in q['hits']) else ('own_signal_metal_only' if q['hits'] else 'no_actual_above_metal')
if sha(a.odb)!=before:raise AssertionError('ODB mutated')
x={'schema':'opentallas.hcoll.above-pin-geometry.v1','source_odb':a.odb,'odb_sha256':before,'read_only':True,'native_dbu_per_um':dbu,'queries':queries,'qualification':'Geometry ownership audit only; does not change LEF, routing, timing, or imply parent via DRC.'}
Path(a.out).write_text(json.dumps(x,indent=2)+'\n');print(json.dumps(x,indent=2))
