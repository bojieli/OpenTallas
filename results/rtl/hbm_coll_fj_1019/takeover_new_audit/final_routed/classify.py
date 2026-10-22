import odb,os,json,hashlib
from pathlib import Path
p=Path(os.environ['AUDIT_ODB']);db=odb.dbDatabase.create();odb.read_db(db,str(p));b=db.getChip().getBlock()
rows=[];counts={}
for i in b.getInsts():
 for t in i.getITerms():
  if str(t.getSigType()) not in ('POWER','GROUND'):continue
  n=t.getNet()
  if n:continue
  protected=i.isDoNotTouch();fixed=str(i.getPlacementStatus()) in ('FIRM','LOCKED','COVER')
  k=f'protected={protected},fixed={fixed}';counts[k]=counts.get(k,0)+1
  rows.append(dict(instance=i.getName(),master=i.getMaster().getName(),pin=t.getMTerm().getName(),protected=protected,fixed=fixed))
Path(os.environ['AUDIT_OUT']).write_text(json.dumps(dict(odb_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),unbound=len(rows),classes=counts,terminals=rows),indent=2))
print(counts)
