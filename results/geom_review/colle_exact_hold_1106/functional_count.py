import odb,json,sys,os
from pathlib import Path
odbpath,outpath=sys.argv[1:] if len(sys.argv)==3 else (os.environ["ODB"],os.environ["COUNT_OUT"])
db=odb.dbDatabase.create();odb.read_db(db,odbpath);b=db.getChip().getBlock();u=b.getDbUnitsPerMicron();c=b.getCoreArea();core=c.dx()*c.dy()/u**2
counts={'functional':0,'macro':0,'pg_only':0};areas={k:0. for k in counts};new=[]
for i in b.getInsts():
 m=i.getMaster();typ=str(m.getType());a=m.getWidth()*m.getHeight()/u**2
 if typ.startswith('BLOCK'):k='macro'
 elif all(str(t.getMTerm().getSigType()) in ('POWER','GROUND') for t in i.getITerms()):k='pg_only'
 else:k='functional'
 counts[k]+=1;areas[k]+=a
 if i.getName().startswith('codex_exact_hold_'):new.append({'instance':i.getName(),'master':m.getName(),'location':i.getLocation(),'orient':str(i.getOrient())})
r={'source':odbpath,'counts':counts,'areas_um2':areas,'core_area_um2':core,'macro_free_area_um2':core-areas['macro'],'functional_utilization':areas['functional']/(core-areas['macro']),'new_buffers':new}
Path(outpath).write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
