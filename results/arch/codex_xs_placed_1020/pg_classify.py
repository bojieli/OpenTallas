import odb,os,json
from pathlib import Path
p=Path(os.environ['AUDIT_ODB']); db=odb.dbDatabase.create();odb.read_db(db,str(p));b=db.getChip().getBlock();d=json.loads(Path(os.environ['PG_RAW']).read_text()); rows=[]; counts={}
for f in d['failures']:
 i=b.findInst(f['instance']); touch=i.isDoNotTouch(); status=str(i.getPlacementStatus());key=('protected' if touch else 'unprotected')+'/'+status;counts[key]=counts.get(key,0)+1
 rows.append(dict(**f,do_not_touch=touch,placement_status=status))
Path(os.environ['AUDIT_OUT']).write_text(json.dumps(dict(schema='opentallas.pg_unbound_classification.v1',counts=counts,terminal_count=len(rows),instance_count=len(set(f['instance'] for f in rows)),failures=rows),indent=2)+'\n');print(counts)
