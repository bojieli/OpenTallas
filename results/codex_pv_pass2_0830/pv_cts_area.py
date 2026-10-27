import odb,json
from pathlib import Path
p=next(Path('/work/run/results/asap7').glob('*/base'))
r=odb.dbDatabase.create();odb.read_db(r,str(p/'3_place.odb'));b=r.getChip().getBlock();old={i.getName():i.getMaster().getName() for i in b.getInsts()};u=b.getDbUnitsPerMicron()
s=odb.dbDatabase.create();odb.read_db(s,str(p/'4_cts.odb'));c=s.getChip().getBlock();a=[]
for i in c.getInsts():
 if i.getName() not in old:
  m=i.getMaster();a.append((i.getName(),m.getName(),m.getWidth()*m.getHeight()/u**2))
h=[i for i in a if 'hold' in i[0].lower()];print('PV_ADDED_NEW',len(a),'area_um2',sum(z[2] for z in a),'HOLD',len(h),'area_um2',sum(z[2] for z in h),'first',h[:5])
open('/work/pv_cts_added_cells.json','w').write(json.dumps(dict(added_cells=len(a),added_area_um2=sum(z[2] for z in a),hold_cells=len(h),hold_area_um2=sum(z[2] for z in h),first_hold=h[:5]),indent=1)+'\n')
