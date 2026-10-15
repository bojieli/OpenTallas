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
  itr=odb.dbWireShapeItr();shape=odb.dbShape();itr.begin(wire)
  while itr.next(shape):
   if not shape.isVia():
    layer=shape.getTechLayer()
    if layer:check(net,layer.getName(),rect(shape.getBox()),'routed_segment')
   else:
    via=shape.getTechVia() or shape.getVia()
    if via and any(b.getTechLayer().getName()=='M6' for b in via.getBoxes()):check(net,'M6',rect(shape.getBox()),'via_conservative_bbox')
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
