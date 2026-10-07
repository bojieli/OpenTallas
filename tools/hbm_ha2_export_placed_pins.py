import odb,json
from pathlib import Path
db=odb.dbDatabase.create();odb.read_db(db,'/in/3_5_place_dp.odb');block=db.getChip().getBlock();u=block.getDbUnitsPerMicron();pins=[]
for term in block.getBTerms():
 for pin in term.getBPins():
  for box in pin.getBoxes():
   pins.append(dict(name=term.getName(),direction=str(term.getIoType()),layer=box.getTechLayer().getName(),rect_um=[box.xMin()/u,box.yMin()/u,box.xMax()/u,box.yMax()/u]))
a=block.getDieArea();print(json.dumps(dict(scope='actual h2 placed pins, routing/signoff pending',die_um=[a.xMin()/u,a.yMin()/u,a.xMax()/u,a.yMax()/u],pins=pins)))
