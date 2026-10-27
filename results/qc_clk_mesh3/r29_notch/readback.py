import odb,json
from pathlib import Path
D=odb.dbDatabase.create();odb.read_db(D,'/out/coupon_native.odb');b=D.getChip().getBlock();rows=[]
for n in b.getNets():
 for sw in n.getSWires():
  for s in sw.getWires():
   if not s.isVia():rows.append(dict(net=n.getName(),layer=s.getTechLayer().getName(),rect=[s.xMin(),s.yMin(),s.xMax(),s.yMax()],special=True))
s=json.loads(Path('/out/source_boxes.json').read_text());s['shapes']=rows
Path('/out/native_boxes.json').write_text(json.dumps(s,indent=1));print('NATIVE_READBACK',len(rows))
