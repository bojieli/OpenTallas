import json,gzip,hashlib,collections,sys
from pathlib import Path
p=Path(sys.argv[1]);out=Path(sys.argv[2]);out.mkdir(exist_ok=True)
d=json.load(gzip.open(p,'rt'));assert d['status']=='PASS' and not d['role_errors']
rows=[];groups=collections.Counter();sources=collections.Counter()
for s in d['sequential_instances']:
 for e in s['input_pins']:
  if e['roots']:continue
  assert e['constant_sources'],('unknown empty-root input',e['name'])
  for a in e['constant_sources']:
   assert a['kind']=='constant_function_driver' and a['function'] in ['0','1',"1'b0","1'b1"],a
   sources[(a['master'],a['pin'],a['function'])]+=1
  groups[(s['master'],e['pin'],e['kind'])]+=1
  rows.append(dict(consumer=e,consumer_actual_liberty_sequential_equations=s['sequential_equations'],constant_sources=e['constant_sources'],physical_source_to_consumer_L1_um=[sum(abs(x-y) for x,y in zip(a['xy_um'],e['xy_um'])) for a in e['constant_sources']],scope='Actual constant-only inputs shown separately; no dynamic driver or reset branch is waived. Consumer category derives from actual Liberty ff/latch expressions, macro category from source-bound registered-read model.'))
summary=dict(identity_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),odb_sha256=d['odb_sha256'],constant_only_inputs=len(rows),consumer_roles=[dict(master=k[0],pin=k[1],actual_role=k[2],count=v) for k,v in groups.items()],source_functions=[dict(master=k[0],pin=k[1],actual_Liberty_function=k[2],count=v) for k,v in sources.items()],actual_liberty_receipts=d['liberty'],synchronous_memory_proof=d['synchronous_memory_proof'])
(out/'constant_consumer_summary.json').write_text(json.dumps(summary,indent=2)+'\n')
with gzip.open(out/'constant_consumer_identity.json.gz','wt') as f:json.dump(rows,f,separators=(',',':'))
print({k:summary[k] for k in ['constant_only_inputs','consumer_roles','source_functions']},flush=True)
