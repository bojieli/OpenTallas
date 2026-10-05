import copy
import json

import pytest

from tools import w16_review_crom_control_join as review


@pytest.fixture(scope='module')
def records():
    finite = json.loads(review.blob(*review.PINS['finite'])[0])
    control = json.loads(review.blob(*review.PINS['control'])[0])
    pin = control['source_pins']['operand_buffer']
    base = json.loads(review.blob(pin['commit'], pin['path'])[0])
    return finite, control, base


def test_actual_inventory_and_costs(records):
    costs = review.totals(*records)
    assert [r['FF_bits'] for r in costs] == [564652, 567346, 734260]
    assert [r['conditional_area_mm2'] for r in costs] == ['1.54880470656', '1.55278527984', '1.79938988352']
    assert costs[0]['partial_delivery_ticks'] > costs[1]['partial_delivery_ticks'] > costs[2]['partial_delivery_ticks']
    assert all(not r['qualified_receiver_deadline'] for r in costs)


@pytest.mark.parametrize('field', ['mandatory_raw_capture_FF_bits', 'page_select_mux_bits', 'tag_valid_and_epoch_state_FF_bits'])
def test_refuses_control_elimination(records, field):
    finite, control, base = copy.deepcopy(records)
    finite['compiler_control_storage'][field] = 0
    with pytest.raises(ValueError, match='control inventory'):
        review.totals(finite, control, base)


@pytest.mark.parametrize('field', ['combined_ungated_clock_W', 'conditional_combined_area_mm2'])
def test_refuses_free_clock_or_area(records, field):
    finite, control, base = copy.deepcopy(records)
    control['credit_scenarios'][0][field] = '0'
    with pytest.raises(ValueError, match='combined'):
        review.totals(finite, control, base)


def test_refuses_serializer_only_credit_route_inventory(records):
    finite, control, base = copy.deepcopy(records)
    control['credit_scenarios'][0]['state_bits_by_purpose']['route_pipeline_bits'] = 0
    with pytest.raises(ValueError, match='credit state count'):
        review.totals(finite, control, base)


def test_exact_owner_replays_keep_whole_join_blocked():
    record = review.build()
    assert record['owner_finite_exact_replay'] and record['owner_control_exact_replay']
    assert record['landed_tool_exact_to_bc1']
    assert record['BF_separate_review']['incoming_pin_internal_allocation_W'] == '106.92643195876835328'
    assert record['BF_separate_review']['unresolved_wire_ceiling_W'] == '524.5264025616384'
    assert not record['BF_separate_review']['floor']
    assert not record['complete_whole_clock_bound']
    assert not record['engine_RTL_build_ready'] and not record['physical_admission']
    assert record['full_operator_critical_path_ticks'] is None
