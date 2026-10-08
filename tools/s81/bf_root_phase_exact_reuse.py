#!/usr/bin/env python3
"""Reuse the immutable b73 proof only for an identical full BF transaction vehicle."""
import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()
def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--work', type=Path, required=True)
    a = p.parse_args()
    binding = json.loads((ROOT/'physical/s81_bf_root_phase/exact_reuse_binding.json').read_text())
    record_path = ROOT/binding['proof_record']
    record = json.loads(record_path.read_text())
    assert record['source_commit'] == binding['reference_commit']
    for name, pin in record['artifact_sha256'].items():
        assert digest(record_path.parent/name) == pin, name
    for name, pin in binding['execution_recipe_sha256'].items():
        assert digest(ROOT/name) == pin, 'execution recipe changed: '+name
    old = json.loads((record_path.parent/'bench/terminal.json').read_text())
    assert old['pass'] and set(old['cases']) == {'positive', 'mutant_front_pair', 'mutant_half_pv'}
    assert all(c['ok'] for c in old['cases'].values())
    for name in ('mutant_front_pair', 'mutant_half_pv'):
        assert old['cases'][name]['returncode'] != 0
        assert 'DIFF TXN' in (record_path.parent/'bench'/name/'run.log').read_text()
    subprocess.run([sys.executable, str(ROOT/'tools/s81/run_bf_root_phase_exact.py'),
                    '--work', str(a.work), '--prepare-only', '--jobs', '4'], check=True)
    new = json.loads((a.work/'terminal.json').read_text())
    assert new['sources_sha256'] == old['sources_sha256'], 'generated transaction vehicle changed'
    assert new['candidate_parameters'] == old['candidate_parameters']
    assert len(new['sources_sha256']) == 49
    result = {'status': 'PASS_REUSED_SOURCE_IDENTICAL_EXACTNESS',
              'proof_source_commit': binding['reference_commit'],
              'candidate_source_commit': new['source_commit'],
              'generated_source_count': len(new['sources_sha256']),
              'proof_record_sha256': digest(record_path),
              'physical_closed': False}
    (a.work/'reuse_receipt.json').write_text(json.dumps(result, indent=2)+'\n')
    print('BF_ROOT_PHASE_EXACT_REUSE_PASS generated_sources=49')
if __name__ == '__main__':
    main()
