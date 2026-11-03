# Pure OpenDB saved-data query. No STA, callbacks, repair or database write.
from pathlib import Path
import odb,json,hashlib,gzip,collections
p=Path('/work/run/results/asap7/hc_qkd_kvs_pc__397_44x362_88/base/5_1_grt.odb')
db=odb.read_db(odb.dbDatabase.create(),str(p));b=db.getChip().getBlock();u=b.getDbUnitsPerMicron()
box=lambda q:[q.xMin()/u,q.yMin()/u,q.xMax()/u,q.yMax()/u]
j={'ODB':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'outline':box(b.getDieArea()),'rows':[box(x.getBBox()) for x in b.getRows()],'cells':{},'pins':[],'PG':{},'status':'READ_ONLY_SAVED_GEOMETRY_NOT_TIMING_OR_DRC'}
for i in b.getInsts():
 j['cells'][i.getName()]={'master':i.getMaster().getName(),'box':box(i.getBBox()),'location':[v/u for v in i.getLocation()],'orient':str(i.getOrient()),'status':str(i.getPlacementStatus())}
for t in b.getBTerms():
 for bp in t.getBPins():
  for z in bp.getBoxes():j['pins'].append({'name':t.getName(),'direction':str(t.getIoType()),'role':str(t.getSigType()),'layer':z.getTechLayer().getName(),'box':box(z)})
for name in ['VDD','VSS']:
 n=b.findNet(name);r=[]
 assert n is not None,name
 for sw in n.getSWires():
  for z in sw.getWires():
   if not z.isVia():r.append({'layer':z.getTechLayer().getName(),'box':box(z)})
 j['PG'][name]={'terminals':len(n.getITerms()),'rectangles':r}
Path('/case/GEOMETRY.json.gz').write_bytes(gzip.compress(json.dumps(j,separators=(',',':')).encode()))
print(json.dumps({'sha256':j['sha256'],'cells':len(j['cells']),'rows':len(j['rows']),'status':dict(collections.Counter(v['status'] for v in j['cells'].values())),'signal_pin_bits':len({v['name'] for v in j['pins'] if v['role'] not in ['POWER','GROUND']})}))
