import copy
import json
from pathlib import Path
import sys

import pytest
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import qwen_rom_real_memory_calibration as c


def pair(pos=0):
    return [json.loads((ROOT / c.INPUT / 'runs' / f'{mode}2_p{pos}.json').read_text()) for mode in ('ideal', 'real')]


def test_actual_six_layer_cycles_and_full_range():
    r = c.build()
    assert [(x['ideal_cycles'], x['real_cycles'], x['observed_memory_service_extra_cycles']) for x in r['rows']] == [
        (4804, 4960, 156), (4804, 5736, 932), (4804, 5348, 544),
        (4828, 5075, 247), (4828, 5436, 608), (4828, 5587, 759)]
    assert r['observed_layer_overhead_percent']['low'] == pytest.approx(3.24729392173)
    assert r['observed_layer_overhead_percent']['high'] == pytest.approx(19.40049958368)
    assert r['pairs'][0]['layer_sum_extra_cycles'] == 1632
    assert r['pairs'][1]['layer_sum_extra_cycles'] == 1614


@pytest.mark.parametrize('key', c.MATCH)
def test_all_identity_mutations_refused(key):
    ideal, real = pair(); real[key] = {'wrong': True} if isinstance(real[key], dict) else 'wrong'
    with pytest.raises(ValueError):
        c.matched_pair(ideal, real, 0)


@pytest.mark.parametrize('mutate', [
    lambda r: r.update(status='fail'),
    lambda r: r.update(source_stable=False),
    lambda r: r.update(position=255),
    lambda r: r.update(stages_run=['E','L0']),
    lambda r: r['layer_x_checks']['L1_die3_x'].update(mismatches=1),
    lambda r: r['layer_x_checks']['L1_die3_x'].update(actual_sha256='0'*64),
    lambda r: r['token_kv_writeback_checks']['L2_die2'].update(v_mismatches=1),
    lambda r: r['token_kv_writeback_checks']['L0_die0'].update(k_codes=255),
])
def test_partial_failed_and_wrong_output_or_writeback_refused(mutate):
    ideal, real = pair(); mutate(real)
    with pytest.raises(ValueError):
        c.matched_pair(ideal, real, 0)


def test_no_old_baseline_or_posted_write_or_token_credit():
    r = c.build()
    assert r['full_token_memory_price_us'] is None
    assert r['full_token_rate'] is None and r['posted_write_gain'] is None
    assert r['adoption'] is False and r['physical_clock_credit'] is False
    assert r['old_compute_baseline_cycles'] == 4668
    assert r['rows'][0]['ideal_cycles'] != 4668
    assert r['pairs'][0]['unattributed_tail_cycles'] == {'ideal':10,'real':10}


def test_generated_record_byteexact():
    assert (ROOT / c.OUTPUT).read_text() == json.dumps(c.build(), indent=2, sort_keys=True)+'\n'
