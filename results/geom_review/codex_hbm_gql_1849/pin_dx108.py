import odb,json,os
from pathlib import Path
p=Path('/work')
base=next((p/'run/results/asap7').glob('*/base'))
db=odb.dbDatabase.create();odb.read_db(db,str(base/'4_cts.odb'))
b=db.getChip().getBlock();u=b.getDbUnitsPerMicron()
changes=[]
for name in ['mp_isl0_ck_i','mp_isl0_ck_o','mp_isl0_rst_i','mp_isl0_rst_o']:
 bt=b.findBTerm(name); shift=round((1.08 if name.endswith('_i') else -1.08)*u)
 for pin in bt.getBPins():
  for box in pin.getBoxes():
   old=[box.xMin(),box.yMin(),box.xMax(),box.yMax()]; layer=box.getTechLayer()
   odb.dbBox_create(pin,layer,old[0]+shift,old[1],old[2]+shift,old[3]);odb.dbBox_destroy(box)
   changes.append(dict(name=name,old=[v/u for v in old],new=[(old[0]+shift)/u,old[1]/u,(old[2]+shift)/u,old[3]/u]))
odb.write_db(db,str(base/'4_cts.odb'))
infra=json.loads((p/'core_infra_plan.json').read_text())
for pin in infra['ports']:
 pin['xy_um'][0]+=1.08 if pin['name'].endswith('_i') else -1.08
(p/'core_infra_plan.json').write_text(json.dumps(infra,indent=2)+'\n')
f=p/'master_core_infra.tcl';s=f.read_text().replace(' 66.96 ',' 68.04 ').replace(' 71.28 ',' 70.2 ');f.write_text(s)
(p/'pin_dx108.json').write_text(json.dumps(dict(changes=changes,instances=len(b.getInsts()),nets=len(b.getNets()),cycle_delta=0),indent=2)+'\n')
print('PIN_DX108',changes)
