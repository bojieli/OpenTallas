import hashlib,json
from pathlib import Path
import odb
r=Path('/work/native');meta=json.loads((r/'repair.json').read_text());db=odb.dbDatabase.create();odb.read_db(db,str(r/'clock_native.odb'));b=db.getChip().getBlock();found={}
for i in b.getInsts():
 m=i.getMaster()
 if m.isBlock():found[m.getName()]=m
for rec in meta['records']:
 m=found[rec['master']];assert m.getLib().getName()==rec['new_lib']
 actual=sorted((x.getTechLayer().getName(),x.xMin(),x.yMin(),x.xMax(),x.yMax()) for x in m.getObstructions() if x.getTechLayer() and x.getTechLayer().getRoutingLevel() in (1,2,3))
 assert len(actual)==rec['expected_lower_boxes'],rec['master']
 assert hashlib.sha256(json.dumps(actual,separators=(',',':')).encode()).hexdigest()==rec['expected_lower_sha256'],rec['master']
(r/'reload_verified.json').write_text(json.dumps({'status':'EXACT_REPLACEMENT_OBS_SERIALIZED','masters':len(meta['records']),'old_MASTER_obstructions_absent_from_active_masters':True},indent=1)+'\n');print('EXACT_REPLACEMENT_OBS_SERIALIZED',len(meta['records']))
