#!/usr/bin/env python3
"""Read-only preflight; never launches physical tools or grants approval."""
import hashlib,json,sys
from pathlib import Path
root=Path(sys.argv[1]); approval=json.loads(Path(sys.argv[2]).read_text())
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
assert approval.get('stage')=='INT8_CTS_ONLY' and approval.get('root_authorized') is True, 'ROOT CTS-only authorization absent'
assert approval.get('pg_tests_pass') is True, 'tested PG prototype absent'
expected={'input/placed.odb':'95dcd07da7a966ccf351a556ed952bf6460c5a81570b846f88786396adb86341'}
for name in ('prototype/pg_adapter.tcl','prototype/pg_test_receipt.json','kit/cts_only.tcl','kit/constraints.sdc','input/platform_SHA256SUMS','input/image.sha'):
    assert name in approval['sha256'], 'missing ROOT-pinned input '+name
    expected[name]=approval['sha256'][name]
for name,digest in expected.items():
    assert sha(root/name)==digest, 'input identity mismatch '+name
assert (root/'input/image.sha').read_text().strip()=='sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29', 'wrong image'
assert approval.get('neighbor_timing_status') in ('DIAGNOSTIC_ONLY','EXACT_REFERENCE_ATTACHED'), 'missing honest boundary status'
print('INPUT_IDENTITY_PASS; execution still requires the authorized fleet command')
