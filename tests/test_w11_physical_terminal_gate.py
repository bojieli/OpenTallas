import json
from pathlib import Path
import shutil
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import w11_physical_terminal_gate as W


@pytest.fixture
def archive(tmp_path):
    for folder in (W.CKV, W.CTL):
        shutil.copytree(W.ROOT / folder, tmp_path / folder)
    service = tmp_path / W.SERVICE
    service.parent.mkdir(parents=True)
    service.write_bytes((W.ROOT / W.SERVICE).read_bytes())
    paths = [W.FEASIBILITY, 'rtl/chip/ot_chip_v41x_ckv_stream_merge.sv',
             'rtl/chip/physical/ot_v41_ckv_merge_phys.sv']
    for name in paths:
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes((W.ROOT / name).read_bytes())
    return tmp_path


def test_zero_DRC_and_loaded_corners_do_not_promote_failed_terminals():
    result = W.build()
    assert result['CKV']['metrics']['route_drc'] == 0
    assert result['CKV']['independent_FF_hold_PASS'] is False
    assert result['controller']['wrapper_corner_label'] == 'TT'
    assert result['controller']['actual_constraints']['setup_corner'] == 'WC/SS'
    assert result['controller']['route_corner_verdict'] is None
    assert not result['physical_admission'] and not result['hardware_adopted']
    assert result['full_token_rate'] is None and result['maximum_qualified_clock_hz'] is None
    assert all(result['CKV']['current_RTL_matches_failed_source'].values())
    assert not result['CKV']['HBM_transfer_qualified']


def test_forged_nonnegative_slack_cannot_override_retained_raw_report(archive):
    path = archive / W.CKV / 'measurement.json'
    record = json.loads(path.read_text())
    record['metrics']['setup_worst_slack_ps'] = 0
    path.write_text(json.dumps(record))
    with pytest.raises(AssertionError, match='CKV finish metric drift'):
        W.build(archive)


def test_forged_controller_completion_cannot_hide_original_archive(archive):
    path = archive / W.CTL / 'physical.json'
    record = json.loads(path.read_text())
    record['flow_completed'] = True
    record['status'] = 'pass'
    path.write_text(json.dumps(record))
    with pytest.raises(AssertionError, match='controller archive drift'):
        W.build(archive)
