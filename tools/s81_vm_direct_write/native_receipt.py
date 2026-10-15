#!/usr/bin/env python3
"""Freeze actual six-profile publication, bench and native-pin receipts; fail closed."""
import hashlib,json,subprocess
from pathlib import Path
from datetime import datetime,timezone
base=Path(__file__).resolve().parents[2]
binding=json.loads((base/'physical/s81_vm_direct_write_native_1015/profile_binding.json').read_text())
out=base/'results/rtl/s81_vm_direct_write_native_1015/native_closure_receipt.json'
assert not out.exists(), 'immutable receipt already exists'
rows={}
for profile,p in binding['profiles'].items():
 state=Path.home()/'.local/state/closure_loop/jobs'/(p['job']+'.json')
 d=json.loads(state.read_text()); assert d['status']=='CLOSED',(profile,d['status'])
 assert not d.get('failed_checks'); assert all(b['ok'] for b in d['benches'].values())
 m=d['metrics']; assert m['ss_ps']>=0 and m['ff_ps']>=0 and m['drc']==0
 pins=base/f'results/rtl/s81_vm_direct_write_native_1015/{profile}_native_assigned_pins.json'
 pd=json.loads(pins.read_text());assert pd['status']=='PASS' and not pd['mismatches']
 remote=d['run']+'/record/views/'+p['master']
 views={}
 for name in ['insertion.json','abstract.json','child_lint.json']:
  r=subprocess.run(['ssh',d['host'],'cat',remote+'/'+name],capture_output=True,check=True)
  views[name]={'remote':remote+'/'+name,'sha256':hashlib.sha256(r.stdout).hexdigest(),'data':json.loads(r.stdout)}
 assert views['child_lint.json']['data']['verdict']=='PASS'
 assert views['abstract.json']['data']['ok'] and views['abstract.json']['data']['checked']
 rows[profile]={'master':p['master'],'job':p['job'],'source_commit':d['commit_full'],'source_host':d['host'],'run':d['run'],'state_sha256':hashlib.sha256(state.read_bytes()).hexdigest(),'status':d['status'],'publication':d['publish'],'tt_setup_ps':m['ss_ps'],'ff_hold_ps':m['ff_ps'],'ss_sensitivity_ps':m['ss_sensitivity_ps'],'drc':m['drc'],'benches':d['benches'],'routed_ioref':d['routed_ioref'],'assigned_pin_check':str(pins.relative_to(base)),'assigned_pin_check_sha256':hashlib.sha256(pins.read_bytes()).hexdigest(),'native_views':views}
receipt={'schema':'opentallas.s81.direct-write-native-six-profile-closure.v1','created':datetime.now(timezone.utc).isoformat(),'status':'SIX_DISTINCT_NATIVE_MASTERS_CLOSED','scope':'Per-profile native leaf closure only. Parent geometry/master adoption, composed local hops, global clock/reset and full programme remain separate gates. Two existing source stages, zero added cycles.','profiles':rows}
out.write_text(json.dumps(receipt,indent=2)+'\n'); print('NATIVE_SIX_PROFILE_CLOSURE_PASS',out)
