"""Connect the accepted +0.92um QC root pin relocation to the fixed clock source."""
import argparse,json
from pathlib import Path
import odb
p=argparse.ArgumentParser();p.add_argument('--input',required=True);p.add_argument('--out',required=True);a=p.parse_args();o=Path(a.out);o.mkdir(parents=True,exist_ok=True)
d=odb.dbDatabase.create();odb.read_db(d,a.input);b=d.getChip().getBlock();D=b.getDbUnitsPerMicron();bt=b.findBTerm('root')
if bt is None:raise ValueError('actual root BTerm absent')
rows=[]
for bp in bt.getBPins():
 for r in bp.getBoxes():
  ly=r.getTechLayer();rows.append((ly,[r.xMin(),r.yMin(),r.xMax(),r.yMax()]))
print('ROOT_PIN_BEFORE',[(x.getName(),r) for x,r in rows],flush=True)
if not rows or any(ly.getName()!='M9' for ly,r in rows):raise ValueError('root pin is not actual M9 metal')
dx=round(.92*D);target=[round(17008.76*D),round(12463.2*D)]
if not any(r[0]+dx<=target[0]<=r[2]+dx and r[1]<=target[1]<=r[3] for ly,r in rows):raise ValueError('accepted root join is outside translated actual root pin')
for bp in list(bt.getBPins()):odb.dbBPin.destroy(bp)
bp=odb.dbBPin.create(bt);bp.setPlacementStatus('FIRM')
for ly,(x0,y0,x1,y1) in rows:odb.dbBox.create(bp,ly,x0+dx,y0,x1+dx,y1)
odb.write_db(d,str(o/'provider.odb'));json.dump(dict(delta_um=[.92,0],target_um=[17008.76,12463.2],before=[(ly.getName(),r) for ly,r in rows],source=a.input,verdict='ACCEPTED_ROOT_PIN_CONNECTED'),open(o/'receipt.json','w'),indent=2)
