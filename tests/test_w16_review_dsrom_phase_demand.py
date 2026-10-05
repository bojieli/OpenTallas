import copy
import gzip
import json

import pytest

from tools import w16_review_dsrom_phase_demand as review


@pytest.fixture(scope='module')
def inputs():
    values = {}
    for name in ('demand', 'CROM', 'phase'):
        raw, _ = review.blob(*review.PINS[name])
        values[name] = json.loads(gzip.decompress(raw) if name == 'demand' else raw)
    return values


def test_all_four_actual_rank_demands(inputs):
    for rank in inputs['demand']['ranks']:
        result = review.rank_review(rank)
        assert result['static_issue_cycles'] == 549760
        assert result['bound_cycles'] == 508800
        assert result['generated_cycles'] == 40960
        assert result['peak_same_bank_values'] == 1024
        assert result['response_peak_bits'] == 65536
        assert result['continuous_serial_emit_required_values_per_fast_cycle'] == '768'


@pytest.mark.parametrize('field', ['one_port_cycles_within_emit_dedup', 'ideal_command_prefetch_cycles', 'logical_lane_uses'])
def test_refuses_free_service_or_prefetch(inputs, field):
    rank = copy.deepcopy(inputs['demand']['ranks'][0])
    rank['records'][0][field] -= 1
    with pytest.raises(ValueError, match='issue totals'):
        review.rank_review(rank)


def test_refuses_descriptor_count_as_read_count(inputs):
    rank = copy.deepcopy(inputs['demand']['ranks'][0])
    rank['summary']['per_emit_dedup_service_cycles'] = 729
    with pytest.raises(ValueError, match='summary service'):
        review.rank_review(rank)


@pytest.mark.parametrize('change', ['address', 'port', 'bank_parallelism', 'root', 'timing'])
def test_refuses_unbound_service_changes(inputs, change):
    crom, phase = copy.deepcopy(inputs['CROM']), copy.deepcopy(inputs['phase'])
    if change == 'address':
        crom['capacity']['logical_address_bits'] = 19
    elif change == 'port':
        crom['ports']['scalar_logical_words_per_fast_cycle'] = 1024
    elif change == 'bank_parallelism':
        crom['ports']['unrelated_read_parallelism'] = True
    elif change == 'root':
        phase['root_stop_credit'] = 1
    else:
        crom['timing_preflight']['SS_macro_clk_to_q_ps'] += 1
    with pytest.raises(ValueError):
        review.validate_service(crom, phase)


def test_exact_dependencies_still_do_not_admit_schedule():
    record = review.build()
    assert record['frozen_git_source_integrity']
    assert len(record['verified_dependencies']) == 22
    assert record['verified_dependencies']['power']['commit'].startswith('e79394b1c')
    assert record['verified_dependencies']['geometry']['commit'].startswith('e61a5a1ee')
    assert record['Q_OR_repricing']['additional_q1024_reservation_mm2'] == '3.37302724608'
    assert record['Engram']['flat_sector_address_bits'] == 33
    for key in ('main_replay_claim', 'owner_phase_numerical_replay', 'full_program_cost_bound',
                'whole_feasible_schedule', 'engine_RTL_build_ready', 'physical_admission'):
        assert record[key] is False
    assert record['headline_rate'] is None
