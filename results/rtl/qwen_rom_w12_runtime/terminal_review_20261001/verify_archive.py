"""Validate additive terminal receipts without rerunning scientific jobs."""
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def sha(data):
    return hashlib.sha256(data).hexdigest()


def committed(revision, path):
    return subprocess.check_output(['git', 'show', revision + ':' + path])


review = json.loads((ROOT / 'verification.json').read_text())
assert review['adoption'] is False and review['existing_records_edited'] is False
for path, digest in review['artifact_sha256'].items():
    assert sha((ROOT / path).read_bytes()) == digest, path

for name in ['partition_product_attempt2', 'spine_s833b']:
    receipt = json.loads((ROOT / name / 'archive.json').read_text())
    for source, info in receipt['files'].items():
        assert sha((ROOT / name / info['local_file']).read_bytes()) == info['sha256'], source
    snapshot = next(r for r in json.loads((ROOT / 'terminal_identity_recheck.json').read_text()) if r['job'] == name)
    assert snapshot['state'] == 'eligible_for_intake'
    assert snapshot['snapshot']['processes'] == {}
    assert snapshot['snapshot']['host'] == receipt['bound_host']

product = json.loads((ROOT / 'partition_product_attempt2/00_partition_product_attempt2.json').read_text())
assert product['status'] == 'pass' and product['source_stable'] is True
assert product['negative_control_rejected'] is True and product['params']['GT'] == '16'
for path, digest in product['source_sha256'].items():
    assert sha(committed(review['product_partition']['source_commit'], path)) == digest, path
reference = committed('0e8df511', 'rtl/hdc/ot_hdc_matvec.sv').decode().replace(
    'module ot_hdc_matvec #(', 'module ot_hdc_matvec_ref #(', 1).encode()
assert sha(reference) == product['reference_sha256']
assert sha((ROOT / 'partition_product_attempt2/ot_hdc_matvec_ref.sv').read_bytes()) == product['reference_sha256']
assert product['verdict'] in (ROOT / 'partition_product_attempt2/sim_dut.log').read_text()
assert product['negative_control'] in (ROOT / 'partition_product_attempt2/sim_mutant.log').read_text()
assert 'FAIL errors=2804 writes=5704' in (ROOT / 'partition_product_attempt2/sim_mutant.log').read_text()

spine = json.loads((ROOT / 'spine_s833b/00_physical.json').read_text())
assert spine['status'] == 'error' and spine['design']['closed'] is False
assert spine['flow_completed'] is False and spine['stages_completed'] == []
assert spine['corner']['name'] == 'TT' and 'timed out after 86400 seconds' in spine['error']
assert spine['target_clock_period_ns'] == 0.833333
assert spine['design']['clock_uncertainty_ns'] == 0.060
assert spine['design']['clock_uncertainty_hold_ns'] == 0.025
for item in spine['design']['sources']:
    assert sha(committed(spine['git']['commit'], item['path'])) == item['sha256'], item['path']
assert sha(committed(spine['git']['commit'], 'tools/run_abi3_physical.py')) == spine['runner']['driver']['sha256']
for item in json.loads((ROOT / 'spine_source_recheck.json').read_text())['source_checks'].values():
    assert item['recorded_sha256'] == item['current_sha256']
assert review['remaining']['tp4_token'].endswith('Full source_stable remains pending.')
print('PASS: artifact hashes, terminal identities, GT16 pins/golden/negative control, and unchanged TT spine timeout.')
