#!/usr/bin/env python3
"""Read-only exact preflight. ROOT creates a separate grant; this kit cannot."""
import hashlib,json,sys
from pathlib import Path
root=Path(sys.argv[1]);a=json.loads(Path(sys.argv[2]).read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert a.get('root_authorized') is True and a.get('stage')=='INT8_CTS_ONLY_CHECKPOINT_V2', 'ROOT CTS-only authorization absent'
assert a.get('candidate')=='smh_int8_safe_tie_t1_cts2', 'wrong candidate'
assert a.get('manifest_sha256')==sha(root/'kit/manifest.json'), 'ROOT exact kit fingerprint absent'
m=json.loads((root/'kit/manifest.json').read_text())
for name,d in m['files'].items():assert sha(root/name)==d, 'wrong hash '+name
assert a.get('pg_tests_pass') is True and a.get('pg_helper_sha256')==m['pg_helper_sha256'], 'reviewed PG tests required'
receipt=json.loads((root/'kit/pg_test_receipt.json').read_text())
assert receipt['packet_commit']=='a92a40171' and receipt['helper_sha256']==m['pg_helper_sha256'], 'master-MTerm completeness receipt required'
for name,d in receipt['receipt_logs'].items(): assert sha(root/'kit'/name)==d, 'PG causal receipt mismatch '+name
assert receipt['results']['modeled_missing_iterm']=='EXPECTED_REFUSAL' and receipt['results']['modeled_type_mismatch']=='EXPECTED_REFUSAL'
assert a.get('neighbor_timing_status')=='DIAGNOSTIC_ONLY', 'this request qualifies diagnostic IO only'
assert not (root/'output').exists(), 'output exists: immutable single execution only'
assert m['schema']=='opentallas.int8.cts_exact_kit.v5', 'wrong kit generation'
smoke=json.loads((root/'kit/metric_smoke_receipt.json').read_text())
assert smoke['status']=='READONLY_NATIVE_TT_FF_PASS' and smoke['native_pins_per_corner']==2782
assert smoke['placed_odb_sha256']==m['files']['input/placed.odb']
for name in ('report_timing.tcl','metric_smoke.tcl','vendor/clock_family.tcl','constraints.sdc','libs_TT.tcl','libs_FF.tcl'):
 assert smoke['api_inputs_sha256'][name]==sha(root/'kit'/name), 'metric smoke code mismatch '+name
for name,d in smoke['witness_sha256'].items(): assert sha(root/'kit'/name)==d, 'metric witness mismatch '+name
assert a.get('metric_smoke_receipt_sha256')==sha(root/'kit/metric_smoke_receipt.json'), 'ROOT metric smoke approval absent'
print('EXACT_INPUTS_V2_PASS; fleet launch remains separate')
