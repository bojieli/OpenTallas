#!/usr/bin/env python3
import json,sys,copy,os
from pathlib import Path
base,variant,target,out=map(Path,sys.argv[1:]);a=json.load(open(base/'die_plan.json'));b=json.load(open(variant/'die_plan.json'));t=json.load(open(target/'die_plan.json'));out.mkdir(parents=True,exist_ok=True)
rep={'base':str(base),'variant':str(variant),'target':str(target),'additions':{}}
for key,idkey in [('ports','id'),('lanes','id')]:
 old={x[idkey]:x for x in a[key]};new={x[idkey]:x for x in b[key]};assert all(new[k]==v for k,v in old.items()),key
 add=[v for k,v in new.items() if k not in old];have={x[idkey] for x in t[key]};assert all(x[idkey] not in have for x in add);t[key].extend(add);rep['additions'][key]=len(add)
for name,old in a['partition_types'].items():
 new=b['partition_types'][name]
 for k in set(old)|set(new):
  if old.get(k)==new.get(k):continue
  assert isinstance(old.get(k),list) and isinstance(new[k],list),(name,k)
  assert new[k][:len(old[k])]==old[k],(name,k,'not append')
  add=new[k][len(old[k]):];have={x.get('name') for x in t['partition_types'][name][k] if isinstance(x,dict)};assert all(x.get('name') not in have for x in add if isinstance(x,dict)),(name,k,'target duplicate')
  t['partition_types'][name][k].extend(add);rep['additions'][name+'.'+k]=len(add)
for k,v in b['latency']['lanes'].items():
 if k not in a['latency']['lanes']:assert k not in t['latency']['lanes'];t['latency']['lanes'][k]=v
 else:assert v==a['latency']['lanes'][k],k
for f in target.iterdir():
 if f.name not in ('die_plan.json','compose_report.json','gen') and not (out/f.name).exists():(out/f.name).symlink_to(f.resolve())
(out/'die_plan.json').write_text(json.dumps(t,indent=1));(out/'compose_report.json').write_text(json.dumps(rep,indent=1));print(json.dumps(rep))
