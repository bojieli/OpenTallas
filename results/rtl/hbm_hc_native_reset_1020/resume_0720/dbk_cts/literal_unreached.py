import odb,json,os,hashlib
from pathlib import Path
p=Path(os.environ['AUDIT_ODB']);db=odb.dbDatabase.create();odb.read_db(db,str(p));b=db.getChip().getBlock()
r=Path('/audit');d=json.loads((r/'l1_CTS_sequential_reach.json').read_text());rows=[]
for x in d['unreached_capture_pins']:
 n=b.findNet(x['net']);drivers=[]
 for t in n.getITerms():
  if str(t.getIoType())=='OUTPUT':drivers.append(dict(instance=t.getInst().getName(),master=t.getInst().getMaster().getName(),pin=t.getMTerm().getName()))
 rows.append(dict(**x,drivers=drivers,literal_tie=len(drivers)==1 and drivers[0]['master'].startswith(('TIEHI','TIELO'))))
out=dict(odb_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),unreached=len(rows),literal_tie=sum(x['literal_tie']for x in rows),rows=rows)
(r/'l1_CTS_unreached_literals.json').write_text(json.dumps(out,indent=2)+'\n');print('UNREACHED',out['unreached'],'LITERAL_TIE',out['literal_tie'])
