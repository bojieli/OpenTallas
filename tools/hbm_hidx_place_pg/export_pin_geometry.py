"""Read-only complete native MTerm/MPin geometry for actual checkpoint."""
import odb,json,gzip,sys,re
from pathlib import Path
d=odb.dbDatabase.create();odb.read_db(d,sys.argv[1]);b=d.getChip().getBlock();pins=[]
for inst in b.getInsts():
 ox,oy=inst.getOrigin();orient=str(inst.getOrient());assert orient in ['R0','MX','MY','R180']
 for mt in inst.getMaster().getMTerms():
  term=inst.findITerm(mt.getName());assert term is not None and term.getMTerm()==mt and term.getSigType()==mt.getSigType()
  shapes=[]
  for mp in mt.getMPins():
   for z in mp.getGeometry():
    assert not z.isVia()
    xs=[ox+(-x if orient in ['MY','R180'] else x) for x in [z.xMin(),z.xMax()]];ys=[oy+(-y if orient in ['MX','R180'] else y) for y in [z.yMin(),z.yMax()]]
    shapes.append([z.getTechLayer().getName(),[min(xs),min(ys),max(xs),max(ys)]])
  assert shapes,(inst.getName(),mt.getName())
  pins.append(dict(cell=inst.getName(),canonical_cell=re.sub(r'\\(.)',r'\1',inst.getName()),pin=mt.getName(),role=str(mt.getSigType()),net=term.getNet().getId() if term.getNet() else None,shapes=shapes))
ports=[]
for bt in b.getBTerms():
 shapes=[[z.getTechLayer().getName(),[z.xMin(),z.yMin(),z.xMax(),z.yMax()]] for bp in bt.getBPins() for z in bp.getBoxes()]
 ports.append(dict(port=bt.getName(),role=str(bt.getSigType()),net=bt.getNet().getId(),shapes=shapes))
with gzip.open('/work/output/native_pin_geometry.json.gz','wt') as f:json.dump(dict(units=b.getDbUnitsPerMicron(),pins=pins,ports=ports),f,separators=(',',':'))
print('COMPLETE_NATIVE_PIN_GEOMETRY',len(pins),len(ports))
