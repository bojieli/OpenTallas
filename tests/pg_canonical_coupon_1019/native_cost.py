import odb,json,sys
from pathlib import Path
from collections import Counter
p=Path(sys.argv[1]);out=Path(sys.argv[2]);db=odb.dbDatabase.create();odb.read_db(db,str(p));b=db.getChip().getBlock();u=b.getDbUnitsPerMicron();rows=[]
for i in b.getInsts():
 m=i.getMaster();pg=[]
 for t in m.getMTerms():
  if str(t.getSigType()) in ('POWER','GROUND'):
   it=i.findITerm(t.getName()); assert it is not None and it.getMTerm()==t
   pg.append({'name':t.getName(),'role':str(t.getSigType()),'net':it.getNet().getName() if it.getNet() else None})
 rows.append({'instance':i.getName(),'master':m.getName(),'width_um':m.getWidth()/u,'height_um':m.getHeight()/u,'area_um2':m.getWidth()*m.getHeight()/u**2,'native_pg':pg})
r={'dbu':u,'instances':rows,'area_um2':sum(x['area_um2'] for x in rows),'masters':dict(Counter(x['master'] for x in rows)),'native_pg_terms':sum(len(x['native_pg']) for x in rows)}
out.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({k:v for k,v in r.items() if k!='instances'}))
