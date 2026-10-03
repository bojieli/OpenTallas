"""Offline terminal/corridor replay; no RTL or physical execution."""
import pathlib,json,hashlib,math
p=pathlib.Path(__file__).resolve().parent
m=json.loads((p/'manifest.json').read_text())
for n,v in m.items():
 b=(p/n).read_bytes();assert len(b)==v['bytes'] and hashlib.sha256(b).hexdigest()==v['sha256'],n
s=json.loads((p/'progress.json').read_text());assert s['agidock_terminal']['status']=='FAIL_INCOMPLETE_HOST_GLOBAL_OOM'
k=(p/'inputs/row_engine_r4-kernel-journal.log').read_text();assert 'Killed process 84296 (openroad)' in k and 'global_oom' in k
r=json.loads((p/'inputs/row_engine_r4-launch-receipt.json').read_text());assert r['status']=='DRIVER_RETURNED' and r['exit_code']==1
f=json.loads((p/'inputs/row_engine_r4-physical.json').read_text());assert not f['flow_completed'] and not f['design']['closed'] and f['status']=='error'
c=json.loads((p/'corridor_model_contribution.json').read_text());assert c['constraints']['longhaul_forbidden_layers']==['M2','M3','M4','M5']
assert c['token_delta_cycles']==432 and c['token_delta_us_at_1p2GHz']==.36
for r in c['existing_full_die_model_contribution']['paths']:
 assert math.ceil(r['trunk_um']/430.56)+math.ceil(r['fan_um']/430.56)==52
assert not c['scope']['iteration_admitted'] and not s['new_jobs_launched']
print(f'PASS: {len(m)} file hashes, exact OOM attribution, no closure credit, four priced 52-stage paths and +432-cycle token delta')
