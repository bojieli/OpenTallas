import hashlib
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import qwen_rom_physical_context_contract as context

MODEL = context.object_at(context.RESET / 'model-r5.json')
SOURCE = 'a' * 64


def receipt():
    return dict(schema='QWEN_ROOT_PROVIDER_PIN_INTERVALS_V1', scope='physical_external_root_pins',
                bench_schedule=False, provider_source_sha256='b'*64, instantiated_source_sha256=SOURCE,
                pins=[dict(instance_pin=f'root/s{i}/RESETN',
                           deassert_min_ps_after_previous_root_posedge=100,
                           deassert_max_ps_after_previous_root_posedge=780,
                           reset_low_pulse_min_ps=330, reset_slew_min_ps=5, reset_slew_max_ps=320,
                           clock_slew_min_ps=5, clock_slew_max_ps=320) for i in (1, 2)])


def test_actual_provider_interval_checks_both_pins_without_hardware_admission():
    result = context.release_preflight(receipt(), MODEL, SOURCE)
    assert result['hardware_admission'] is False
    assert len(result['margins']) == 2
    assert result['margins'][0]['removal_margin_ps'] == pytest.approx(7.4936)
    assert result['margins'][0]['recovery_margin_ps'] == pytest.approx(11.5025333333)


@pytest.mark.parametrize('field,value', [
    ('deassert_min_ps_after_previous_root_posedge', 0),
    ('deassert_max_ps_after_previous_root_posedge', 800),
    ('reset_low_pulse_min_ps', 320), ('reset_slew_max_ps', 321),
    ('clock_slew_min_ps', 4), ('reset_slew_min_ps', None),
    ('deassert_max_ps_after_previous_root_posedge', float('nan')),
])
def test_external_missing_or_invalid_bounds_are_not_internal_failures(field, value):
    r = receipt()
    r['pins'][1][field] = value
    with pytest.raises(ValueError):
        context.release_preflight(r, MODEL, SOURCE)


def test_wrong_source_and_bench_and_missing_second_root_pin_rejected():
    for key, value in [('instantiated_source_sha256', 'c'*64), ('bench_schedule', True),
                       ('provider_source_sha256', ''), ('pins', receipt()['pins'][:1])]:
        r = receipt()
        r[key] = value
        with pytest.raises(ValueError):
            context.release_preflight(r, MODEL, SOURCE)


def test_existing_mapped_sink_census_and_policy_scope():
    packet, sinks = context.build()
    mapped = packet['mapped_sinks']
    assert mapped['historical_complete_logic']['clock_sinks'] == 62651
    assert mapped['historical_complete_logic']['reset_sinks'] == 28158
    assert mapped['historical_complete_logic']['current_source_qualified'] is False
    assert mapped['current_loaded_capture']['clock_sinks'] == 3168
    assert mapped['current_loaded_capture']['reset_sinks'] == 86
    assert mapped['current_loaded_capture']['complete_tile'] is False
    assert mapped['planned_cone_with_four_bank5_FFs_and_two_root_FFs']['clock_sinks'] == 3174
    assert packet['routing']['policy_capacity_tracks'] == 843.75
    assert packet['routing']['actual_KV_fill_tracks'] == 1048
    assert packet['routing']['policy_fit'] is False
    assert packet['routing']['minimum_policy_width_um'] == pytest.approx(74.5244444444)
    assert len(sinks['current_loaded_capture']) == 3168 + 86
    assert mapped['complete_current_tile']['current_wrapper_SMIN'] == 6
    assert mapped['complete_current_tile']['preserved_census_SMIN'] == 7
    assert mapped['complete_current_tile']['census_transfer_to_current_wrapper_allowed'] is False
    assert packet['peer_source_joins']['Russell_production']['policy_selected'] is False
    assert packet['peer_source_joins']['Russell_production']['actual_tail_physical_context']['banks_per_rank'] == 128
    assert packet['macros'][0]['clock_cap_fF']['ff'] == 10.3732
    assert packet['macros'][0]['signal_pin_layers'] == ['M4']
    assert packet['RTL_map_PR_allowed'] is False
    assert packet['current_once_calendar']['admitted'] is False
    assert packet['persistent_KV']['cold_calendar_role'] == 'reference only, not selected production'


def test_capacitance_units_and_missing_pin_cannot_be_guessed():
    with pytest.raises(ValueError):
        context.pin_caps('capacitive_load_unit (1, pf);')
    with pytest.raises(KeyError):
        context.summarize([dict(cell='not_in_library', pin='CLK', net='clk')], dict(ss={}))


def test_committed_pins_and_byte_exact_model_replay():
    pins = context.object_at(context.OUT / 'sourcepins-r1.json')['sha256']
    for path, sha in pins.items():
        assert hashlib.sha256((context.ROOT/path).read_bytes()).hexdigest() == sha, path
    packet, _ = context.build()
    assert (context.ROOT/context.OUT/'model-r1.json').read_text() == json.dumps(packet, indent=2, sort_keys=True)+'\n'
