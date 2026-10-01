"""Reject changes in arithmetic, latency, full shape and model readiness."""
import copy
import json
from pathlib import Path
import sys
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from w10_wake_qualification import compare_cases, validate_model


@pytest.fixture
def baseline():
    return json.loads((ROOT/'results/uarch/w10_baseline_bb01_qualification/fastpp_front0.json').read_text())


def test_actual_full_legal_baseline(baseline):
    assert compare_cases(baseline,copy.deepcopy(baseline)) == 240


@pytest.mark.parametrize('change',['cycle','arithmetic','shape','fault','failed_verdict','missing_case','checkpoint'])
def test_reject_changed_gate(baseline,change):
    candidate = copy.deepcopy(baseline)
    if change == 'cycle': candidate['cases'][0]['cycles_last_row'] += 1
    if change == 'arithmetic': candidate['cases'][0]['fp32_exact'] -= 1
    if change == 'shape': candidate['cases'][0]['N'] = 2
    if change == 'fault': candidate['cases'][0]['fault'] = 1
    if change == 'failed_verdict': candidate['verdict'] = 'FAIL'
    if change == 'missing_case': candidate['cases'].pop()
    if change == 'checkpoint': candidate['checkpoint_revision'] = 'other'
    with pytest.raises(ValueError): compare_cases(baseline,candidate)


@pytest.mark.parametrize('change',['latency','lat7','small_field','track_overflow'])
def test_model_blocks_unsafe_build(change):
    model = json.loads((ROOT/'results/uarch/w10_baseline_wake/prebuild.json').read_text())
    validate_model(model)
    if change == 'latency': model['latency']['added_walker_cycles'] = 1
    if change == 'lat7': model['parameters']['LAT'] = 7
    if change == 'small_field': model['full_size']['maximum_pairs_per_die'] = 100
    if change == 'track_overflow': model['elements']['column']['channel_tracks_estimate'] = 1
    with pytest.raises(ValueError): validate_model(model)
