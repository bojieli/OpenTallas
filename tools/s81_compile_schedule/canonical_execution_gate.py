#!/usr/bin/env python3
"""Replay real canonical missing-owner witness plus compiler mechanism mutants.

The full-source negative is an expected rejection, never a native chip PASS.
"""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from canonical_execution_join import load, join

root=Path(__file__).resolve().parents[2]
result=subprocess.run([sys.executable,'-m','unittest','discover','-s','tools/s81_compile_schedule',
                       '-p','test_canonical_execution_join.py','-v'],cwd=root,capture_output=True,text=True)
(root/'mechanism_tests.log').write_text(result.stdout+result.stderr)
if result.returncode:
    raise SystemExit(result.returncode)
canonical=load(root/'inputs/canonical_source_export.json.gz')
catalogue=load(root/'inputs/full_su_spatial.json.gz')
report=join(canonical,catalogue,{},root)
assert report['source_operations']==2654 and report['required_rank_operations']==10616
assert report['covered_rank_operations']==0 and report['rank_programmes_seen']==0
assert report['literal_mtp_operations']==0 and not report['dispatch_eligible']
kinds=[v['kind'] for v in report['violations']]
assert kinds.count('missing_rank_programme')==324
assert 'missing_literal_MTP_continuation_operations' in kinds
assert 'missing_or_invalid_native_instance_inventory' in kinds
assert report['compiled_rank_programmes']==[]
(root/'actual_source_join.json').write_text(json.dumps(report,indent=2)+'\n')
paths=[*sorted((root/'tools/s81_compile_schedule').glob('*.py')),
       root/'tools/s81_suhc/static_vm_reservations.py',*sorted((root/'inputs').glob('*'))]
receipt=dict(schema='opentallas.s81.canonical-execution-join-replay.v1',mechanism_tests_passed=True,
             full_source_expected_rejection_verified=True,native_qualified=False,
             literal_SU_operations=2654,required_rank_operations=10616,
             missing_rank_programmes=324,literal_MTP_operations=0,
             sources={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths})
(root/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(receipt))
