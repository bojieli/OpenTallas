"""Historical or incomplete records must not certify current RTL clocks."""
import hashlib
import json
from pathlib import Path

from tools.audit_current_physical_evidence import ZERO_METRICS, inspect_record


def fixture(root):
    source = root / 'rtl/top.sv'
    source.parent.mkdir()
    source.write_text('module top; endmodule\n')
    artifacts = root / 'artifacts'
    artifacts.mkdir()
    manifest = {}
    for name in ('6_final.v', '6_finish.rpt', 'config.mk', 'constraint.sdc'):
        (artifacts / name).write_text(name)
        manifest[name] = {'retained': True, 'sha256': hashlib.sha256(name.encode()).hexdigest()}
    record = {
        'design': {'top': 'top', 'sources': [{'path': 'rtl/top.sv', 'sha256': hashlib.sha256(source.read_bytes()).hexdigest()}]},
        'view': {'name': 'asap7'}, 'target_clock_period_ns': 2,
        'place_and_route': {'artifact_dir': 'artifacts', 'artifacts': manifest,
                            'metrics': {**dict.fromkeys(ZERO_METRICS, 0), 'setup_wns_ns': 0.2, 'hold_wns_ns': 0.01, 'fmax_hz': 999e6}},
    }
    path = root / 'record.json'
    path.write_text(json.dumps(record))
    return path, record


def test_frequency_is_tested_period_not_extrapolated(tmp_path):
    path, _ = fixture(tmp_path)
    row = inspect_record(path, tmp_path)
    assert row['current_source_and_artifact_verified']
    assert row['verified_current_frequency_mhz'] == 500
    (tmp_path / 'rtl/top.sv').write_text('module top; wire new_path; endmodule')
    row = inspect_record(path, tmp_path)
    assert row['routed_checks_pass']
    assert not row['current_source_and_artifact_verified']
    assert row['verified_current_frequency_mhz'] is None


def test_missing_checks_and_damaged_artifacts_are_not_passes(tmp_path):
    path, record = fixture(tmp_path)
    del record['place_and_route']['metrics']['max_fanout_violations']
    record['place_and_route']['metrics']['hold_wns_ns'] = -0.01
    path.write_text(json.dumps(record))
    (tmp_path / 'artifacts/6_final.v').write_text('modified')
    row = inspect_record(path, tmp_path)
    assert not row['routed_checks_pass']
    assert row['missing_metrics'] == ['max_fanout_violations']
    assert 'hold_wns_ns' in row['violations']
    assert 'hash_mismatch:6_final.v' in row['artifact_issues']


def test_snapshot_hash_does_not_certify_active_implementation(tmp_path):
    path, record = fixture(tmp_path)
    snapshot = tmp_path / 'snapshot.sv'
    snapshot.write_bytes((tmp_path / 'rtl/top.sv').read_bytes())
    record['design']['sources'][0]['path'] = 'snapshot.sv'
    path.write_text(json.dumps(record))
    row = inspect_record(path, tmp_path)
    assert row['routed_checks_pass']
    assert not row['current_source_and_artifact_verified']
    assert 'snapshot_or_external_sources_require_active_binding' in row['source_issues']


def test_nonfinite_timing_is_missing_evidence(tmp_path):
    path, record = fixture(tmp_path)
    record['place_and_route']['metrics']['setup_wns_ns'] = float('nan')
    path.write_text(json.dumps(record))
    row = inspect_record(path, tmp_path)
    assert not row['routed_checks_pass']
    assert 'setup_wns_ns' in row['missing_metrics']
