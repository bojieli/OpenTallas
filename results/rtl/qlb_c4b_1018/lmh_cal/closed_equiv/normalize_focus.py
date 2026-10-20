from pathlib import Path
import json,hashlib
p=Path('gate_focus.json');j=json.loads(p.read_text());m=j['modules']['gate'];changes=[]
for bucket in ['cells','netnames']:
 d={}
 for n,c in m[bucket].items():
  new=n.replace('.genblk1.g_dense.','.g_dense.');assert new not in d;d[new]=c
  if new!=n:changes.append(dict(bucket=bucket,old=n,new=new))
 m[bucket]=d
Path('gate_focus_names.json').write_text(json.dumps(j)+'\n');Path('focus_name_ledger.json').write_text(json.dumps(dict(source_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),claim='net/cell namespace only; logic/parameters/connections unchanged',changes=changes),indent=2)+'\n')
