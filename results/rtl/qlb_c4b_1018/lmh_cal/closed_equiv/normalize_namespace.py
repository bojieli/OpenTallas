from pathlib import Path
import json,hashlib
p=Path('miter.json');raw=p.read_bytes();j=json.loads(raw);m=j['modules']['gate'];ledger=[]
for bucket in ['cells','netnames']:
 d={}
 for k,v in m[bucket].items():
  new=k.replace('.genblk1.g_dense.','.g_dense.')
  if bucket=='cells' and v['type']=='ot_sram_1r1w_64x512_m1_r2c2':new+='_proof_unique'
  assert new not in d
  d[new]=v
  if new!=k:ledger.append(dict(bucket=bucket,old=k,new=new))
 m[bucket]=d
j['modules'].pop('equiv');assert len(ledger)>0
Path('namespace_sources.json').write_text(json.dumps(j)+'\n')
Path('namespace_ledger.json').write_text(json.dumps(dict(original_miter_sha256=hashlib.sha256(raw).hexdigest(),transformation='names only: exact SEG0 eliminated-generate namespace genblk1.g_dense -> g_dense',changed_names=len(ledger),ledger=ledger),indent=2)+'\n')
