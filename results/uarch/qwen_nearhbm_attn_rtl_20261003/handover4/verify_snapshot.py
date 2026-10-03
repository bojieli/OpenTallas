"""Offline verification of retained handover observations, never launches hardware."""
import base64,hashlib,json,pathlib
p=pathlib.Path(__file__).resolve().parent
m=json.loads((p/'manifest.json').read_text())
for n,v in m.items():
 b=(p/n).read_bytes();assert len(b)==v['bytes'] and hashlib.sha256(b).hexdigest()==v['sha256'],n
count=0
def walk(x):
 global count
 if isinstance(x,dict):
  if 'base64' in x:
   b=base64.b64decode(x['base64'],validate=True)
   assert len(b)==x['bytes'] and hashlib.sha256(b).hexdigest()==x['sha256'],x['path'];count+=1
  for v in x.values():walk(v)
 elif isinstance(x,list):
  for v in x:walk(v)
for host in ['epyc','agidock']:walk(json.loads((p/(host+'-snapshot.json')).read_text()))
s=json.loads((p/'progress.json').read_text())
assert s['RF']['macro_count']==128 and s['RF']['physical_storage_bits']==4194304
assert s['RF']['macro_alignment_offtrack']==0
assert s['hierarchy_evidence']['current_hub_source_mismatches']
assert not s['hierarchy_evidence']['current_hierarchy_performance_qualified']
assert not any(j['terminal_present'] for j in s['jobs'].values())
assert s['source_lease']['raw_bits']==4293*123
print(f'PASS: {len(m)} files, {count} embedded raw receipts verified; live snapshots confer no terminal/SSFF/current-hierarchy qualification')
