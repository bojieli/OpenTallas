import odb,json
from pathlib import Path
p=Path('/work');db=odb.dbDatabase.create();base=next((p/'run/results/asap7').glob('*/base'));odb.read_db(db,str(base/'4_cts.odb'));b=db.getChip().getBlock();u=b.getDbUnitsPerMicron();out=[]
for n in b.getNets():
 if n.getSigType() not in ('POWER','GROUND'):continue
 for sw in n.getSWires():
  for box in sw.getWires():
   if box.isVia():continue
   if box.getTechLayer().getName()!='M5':continue
   r=[box.xMin()/u,box.yMin()/u,box.xMax()/u,box.yMax()/u]
   if r[2]>=65 and r[0]<=73 and r[3]>=100 and r[1]<=107:out.append({'net':n.getName(),'rect':r})
(p/'island_pg.json').write_text(json.dumps(out,indent=2)+'\n');print('ISLAND_M5_PG',out)
