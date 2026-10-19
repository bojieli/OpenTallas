import odb,json,sys
from pathlib import Path
db=odb.dbDatabase.create();odb.read_db(db,sys.argv[1]);b=db.getChip().getBlock();u=b.getDbUnitsPerMicron()
def box(bb):return [bb.xMin()/u,bb.yMin()/u,bb.xMax()/u,bb.yMax()/u]
cells=[]
for i in b.getInsts():
 cells.append(dict(name=i.getName(),master=i.getMaster().getName(),box=box(i.getBBox()),status=str(i.getPlacementStatus()),orient=str(i.getOrient())))
pins=[]
for p in b.getBTerms():
 for bp in p.getBPins():
  for bb in bp.getBoxes():pins.append(dict(name=p.getName(),layer=bb.getTechLayer().getName(),box=box(bb)))
ties=[i for i in b.getInsts() if i.getMaster().getName() in ('TIEHIx1_ASAP7_75t_R','TIELOx1_ASAP7_75t_R')]
receipts=[]
for i in ties:
 t=dict(name=i.getName(),master=i.getMaster().getName(),pins=[])
 for it in i.getITerms():
  n=it.getNet();t['pins'].append(dict(pin=it.getMTerm().getName(),role=str(it.getMTerm().getSigType()),net=n.getName() if n else None,special=n.isSpecial() if n else False,pg_shapes=len(n.getSWires()) if n else 0))
 receipts.append(t)
Path(sys.argv[2]).write_text(json.dumps(dict(die=box(b.getDieArea()),core=box(b.getCoreArea()),cells=cells,pins=pins,ties=receipts),separators=(',',':'))+'\n')
