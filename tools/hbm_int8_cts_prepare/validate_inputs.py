#!/usr/bin/env python3
"""Read-only exact preflight. ROOT creates a separate grant; this kit cannot."""
import hashlib,json,sys
from pathlib import Path
root=Path(sys.argv[1]);a=json.loads(Path(sys.argv[2]).read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert a.get('root_authorized') is True and a.get('stage')=='INT8_CTS_ONLY', 'ROOT CTS-only authorization absent'
assert a.get('candidate')=='smh_int8_safe_tie_t1_cts1', 'wrong candidate'
assert a.get('manifest_sha256')==sha(root/'kit/manifest.json'), 'ROOT exact kit fingerprint absent'
m=json.loads((root/'kit/manifest.json').read_text())
for name,d in m['files'].items():assert sha(root/name)==d, 'wrong hash '+name
assert a.get('pg_tests_pass') is True and a.get('pg_helper_sha256')==m['pg_helper_sha256'], 'reviewed PG tests required'
assert a.get('neighbor_timing_status')=='DIAGNOSTIC_ONLY', 'this request qualifies diagnostic IO only'
assert not (root/'output').exists(), 'output exists: immutable single execution only'
print('EXACT_INPUTS_PASS; fleet launch remains separate')
