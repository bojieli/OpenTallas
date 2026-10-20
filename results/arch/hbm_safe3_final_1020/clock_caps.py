import odb,json,os,hashlib,collections
from pathlib import Path
p=Path('/frozen/routes/hbm_su_pg_stream_b_safe3_1019_s3_a160833f0/work/orfs/results/asap7/opentallas_ot_hbm_su_static_pg_stream_split_safe3_asap7_ref_hbm_su_pg_stream_b_safe3_1019_s3_a160833f0/base/6_final.odb')
db=odb.dbDatabase.create();odb.read_db(db,str(p));b=db.getChip().getBlock();rows=[];types=collections.Counter();inputs=collections.Counter();nonfloating=[]
for i in b.getInsts():
 if not i.getName().startswith('clkload'):continue
 row={'name':i.getName(),'master':i.getMaster().getName(),'dnt':i.isDoNotTouch(),'contacts':[]}
 types[i.getMaster().getName()]+=1
 for t in i.getITerms():
  if str(t.getSigType()) in ('POWER','GROUND'):continue
  n=t.getNet();z={'pin':t.getMTerm().getName(),'io':str(t.getIoType()),'net':n.getName() if n else None,'net_type':str(n.getSigType()) if n else None}
  row['contacts'].append(z)
  if z['io']=='INPUT':inputs[z['net']]+=1
  if z['io']=='OUTPUT' and n is not None:nonfloating.append(dict(name=i.getName(),**z))
 rows.append(row)
out=dict(scope='read-only actual6_final clockload contacts; no native rule modified',odb_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),instances=len(rows),master_counts=dict(types),input_nets=dict(inputs),connected_outputs=nonfloating,rows=rows)
Path('/audit/clockload_physical_contacts.json').write_text(json.dumps(out,indent=2)+'\n');print({k:v for k,v in out.items() if k!='rows'})
