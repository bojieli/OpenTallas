"""Read-only exact boundary-pin geometry from an actual OpenDB artifact."""
import argparse, hashlib, json, sys
from pathlib import Path
import odb
args=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else sys.argv[1:]
p=argparse.ArgumentParser();p.add_argument('--odb',required=True);p.add_argument('--out',required=True);p.add_argument('--source',required=True);a=p.parse_args(args)
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
before=sha(a.odb);db=odb.dbDatabase.create();odb.read_db(db,a.odb);b=db.getChip().getBlock();u=b.getDbUnitsPerMicron();d=b.getDieArea()
rect=lambda r:[r.xMin()/u,r.yMin()/u,r.xMax()/u,r.yMax()/u]
pins=[]
for t in sorted(b.getBTerms(),key=lambda t:t.getName()):
 boxes=[]
 for p in t.getBPins():
  for z in p.getBoxes():
   r=rect(z); faces=[]
   if z.yMin()<=d.yMin():faces.append('S')
   if z.yMax()>=d.yMax():faces.append('N')
   if z.xMin()<=d.xMin():faces.append('W')
   if z.xMax()>=d.xMax():faces.append('E')
   boxes.append({'layer':z.getTechLayer().getName(),'rect_um':r,'faces':faces})
 pins.append({'name':t.getName(),'direction':str(t.getIoType()),'signal_type':str(t.getSigType()),'boxes':boxes})
assert before==sha(a.odb),'ODB mutated'
x={'schema':'opentallas.hcoll.exact-pin-geometry.v1','source_commit':a.source,'source_odb':a.odb,'odb_sha256':before,'extractor_sha256':sha(__file__),'read_only':True,'dbu_per_um':u,'bbox_um':rect(d),'pins':pins,'qualification':'Exact snapshot of placed physical pin rectangles; final route access, PG cuts, timing and all hierarchy legs require separate checks.'}
Path(a.out).write_text(json.dumps(x,indent=2)+'\n');print('EXACT_PINS count='+str(len(pins))+' sha='+before)
