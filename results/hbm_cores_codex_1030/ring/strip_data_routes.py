"""Prepare a fresh data-route seed; retain the reviewed placement and every clock wire."""
import json,os
from pathlib import Path
import odb
root=Path(os.environ['RING_ROOT'])
clock_names=set((root/'ring_five_dpl/clk_freeze_nets.txt').read_text().splitlines())
assert len(clock_names)==1359
odb_path=root/'ring_five_dpl/data5_dpl.odb'
db=odb.dbDatabase.create();odb.read_db(db,str(odb_path));b=db.getChip().getBlock()
for name in clock_names:
 n=b.findNet(name);assert n is not None and n.getWire() is not None,name
for name in ['place9777','place10432','place10414','place9760','place10359']:
 assert b.findInst(name).getMaster().getName()=='BUFx6f_ASAP7_75t_R',name
counts=dict(clock_wires_kept=len(clock_names),data_wires_removed=0,data_guides_removed=0)
for n in b.getNets():
 if n.getName() in clock_names or n.getSigType()!='SIGNAL':continue
 wire=n.getWire()
 if wire is not None:odb.dbWire.destroy(wire);counts['data_wires_removed']+=1
 for guide in list(n.getGuides()):odb.dbGuide_destroy(guide);counts['data_guides_removed']+=1
for name in clock_names:assert b.findNet(name).getWire() is not None,name
out=Path(os.environ['RING_OUT']);out.mkdir(exist_ok=True)
odb.write_db(db,str(out/'data_seed.odb'))
(out/'strip_receipt.json').write_text(json.dumps(counts,indent=1)+'\n');print(counts)
