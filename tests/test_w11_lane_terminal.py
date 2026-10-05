"""Reject adoption when an exact lane campaign measures slower."""
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'results/rtl/w11_lane_terminal_20261001'


def test_terminal_sources_and_artifacts_are_pinned():
    summary = json.loads((BASE / 'summary.json').read_text())
    assert summary['adoption'] is False
    for name, sha in summary['evidence_sha256'].items():
        assert hashlib.sha256((BASE / name).read_bytes()).hexdigest() == sha
    for name in ('reg_k20', 'vehfused_k40'):
        record = json.loads((BASE / (name + '.json')).read_text())
        assert record['git_dirty_tracked_files'] == []
        for path, sha in record['input_sha256'].items():
            blob = subprocess.check_output(['git', 'show', record['git_head'] + ':' + path], cwd=ROOT)
            assert hashlib.sha256(blob).hexdigest() == sha


def test_exact_but_slower_vehicle_is_rejected():
    summary = json.loads((BASE / 'summary.json').read_text())
    record = json.loads((BASE / 'vehfused_k40.json').read_text())
    for shape, batches in record['vehicle_fused']['batches'].items():
        row = summary['vehicle_fused'][shape]
        assert row['cases'] == row['passed'] == len(batches) == 56
        assert all(b['pass_'] and b['same_final_vm'] for b in batches)
        for b in batches:
            for kind in ('unfused', 'fused'):
                result = b[kind]
                assert result['ended'] and result['pass_']
                assert all(result[k] == 0 for k in ('vm_mismatch_words', 'kv_mismatch_words', 'faults', 'order_faults'))
            assert b['cycles_saved'] == b['unfused']['cycles'] - b['fused']['cycles']
        assert row['unfused_cycles'] == sum(b['unfused']['cycles'] for b in batches)
        assert row['fused_cycles'] == sum(b['fused']['cycles'] for b in batches)
        assert row['saved_cycles'] == row['unfused_cycles'] - row['fused_cycles']
        assert row['performance_verdict'] == ('rejected_slower' if row['saved_cycles'] < 0 else 'gain_only_not_adopted')
    assert summary['vehicle_fused']['N64_M16']['saved_cycles'] == -1742
