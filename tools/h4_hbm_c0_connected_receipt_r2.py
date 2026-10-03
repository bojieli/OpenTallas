#!/usr/bin/env python3
"""Strict immutable source/runtime artifact verification, no job dispatch."""
import json,hashlib,gzip,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];BASE=ROOT/'results/rtl/h4_hbm_c0_connected_bridge_20261003/r2'
MANIFEST_SHA='37dfe4848f415f16faaea0fa3a5608b08911ebe947b7b08ef0fcf3cc7b10783b'
def verify():
 raw=(BASE/'manifest.json').read_bytes()
 if hashlib.sha256(raw).hexdigest()!=MANIFEST_SHA:raise ValueError('receipt manifest')
 rows=json.loads(raw)
 for x in rows:
  p=ROOT/x['path']
  if not p.resolve().is_relative_to(BASE.resolve()):raise ValueError('artifact scope')
  if hashlib.sha256(p.read_bytes()).hexdigest()!=x['sha256']:raise ValueError('artifact hash '+x['path'])
 r=json.loads((BASE/'record.json').read_bytes());t=json.loads((BASE/'terminal.json').read_bytes())
 if r['source_commit']!='8c3dfbf7910cb74cbc74497c787c3fc3b790bc82' or t['source_commit']!=r['source_commit']:raise ValueError('source SHA')
 for x in r['source_input_pins']:
  p=ROOT/x['path']
  if not p.resolve().is_relative_to(ROOT.resolve()) or hashlib.sha256(p.read_bytes()).hexdigest()!=x['sha256']:raise ValueError('exact compiled source changed')
 if any(x!=0 for x in [r['compile_RC'],r['runtime_RC'],t['compile_RC'],t['runtime_RC']]):raise ValueError('terminal RC')
 log=(BASE/'runtime.log').read_text()
 if log.count('CONNECTED_PC40_PASS')!=1 or 'FATAL' in log:raise ValueError('terminal marker')
 expected={'NONFINITE_REFUSAL','STALE_ACK','RUNTIME_RESET','WRONG_REVERSE','WRONG_DRAIN','MISSING_ALLCOPY'}
 cases=re.findall(r'^CASE_PASS\s+(\w+)',log,re.M)
 if len(cases)!=6 or set(cases)!=expected or set(r['negatives'])!=expected:raise ValueError('negative gate coverage')
 if hashlib.sha256(gzip.decompress((BASE/'gate.vvp.gz').read_bytes())).hexdigest()!=t['binary_sha256'] or t['binary_sha256']!=r['binary_sha256']:raise ValueError('binary origin')
 for k in ['actual_payload','W2','physical_owner55_match','global_drain','full_token','protected_upset','SSFF','rate']:
  if r[k] is not False:raise ValueError('scope promoted '+k)
 events=[x for x in log.splitlines() if x.startswith('EVENT ')]
 if events!=t['source_lease_trace']:raise ValueError('cycle events origin')
 if not any('phase=FMIN_result_accept' in x for x in events) or not any('phase=W6_consumer' in x for x in events):raise ValueError('actual consumer missing')
 return dict(verdict=r['verdict'],artifact_hashes=len(rows),source_pins=len(r['source_input_pins']),negatives=len(cases),events=len(events),no_dispatch=True)
if __name__=='__main__':print(json.dumps(verify(),indent=2))
