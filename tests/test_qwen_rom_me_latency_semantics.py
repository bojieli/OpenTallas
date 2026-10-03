import json
import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import qwen_rom_me_latency_semantics as P


@pytest.fixture(scope='module')
def model():return json.loads((P.ROOT/P.OUT/'model-r2.json').read_text())


def test_exact_wire_debit_and_generated_ME_count(model):
    assert model['old_effective_ME_latency_cycles']==71
    assert model['corrected_me_lat_extra_argument']==167
    assert model['corrected_effective_ME_latency_cycles']==183
    assert model['generated_program_ME_count']==36*6+1==217
    assert model['added_wire_cycles_per_layer']==6*112==672
    assert model['added_wire_cycles_per_token']==217*112==24304
    assert model['added_wire_debit_token_s']==pytest.approx(20.25333333333333e-6)
    assert [s['ME_contributions'] for s in model['stage_debits']]==[1,2,1,1,1]


def test_compute_prefix_rest_and_head_not_double_charged(model):
    c=model['calendar_compute_inputs']
    assert c['historical_prefix_cycles']==451 and c['corrected_prefix_cycles']==563
    assert c['historical_remaining_body_cycles']==2887 and c['corrected_remaining_body_cycles']==3447
    assert c['unchanged_serial_AR_multiplier']==1.28
    assert c['corrected_rest_cycles']-c['historical_rest_cycles']==pytest.approx(560)
    assert c['additional_nonlayer_head_cycles']==112
    assert model['corrected_finite_calendar_s'] is None and model['corrected_prefetch_rate'] is None


def test_LAT339_does_not_replace_full_two_segment_collective(model):
    h=model['additive_corrected_l0_helper'];old=h['historical_helper']
    assert old['model_layer_cycles_at_rtl_collective']==3138
    assert old['gap_cycles_at_rtl_collective']==1531
    assert h['collective_LAT_parameter']==339
    assert h['full_collective_cycles_each']==991
    assert h['model_layer_cycles_at_rtl_collective']==2460+2*991==4442
    assert h['gap_cycles_at_rtl_collective']==227
    assert model['L0_calibration']['model_layer_cycles']==3344
    assert model['L0_calibration']['AR_gap_cycles']==1098
    assert not h['current_source_timing_admission']
    assert model['frozen_credit17_verdict'].startswith('REJECTED')


def test_cold_semantics_replay_and_no_source_or_rate_admission(model):
    assert json.loads(json.dumps(P.build()))==model
    assert not any(model[k] for k in ['source_scope_transfer','headline_admission','SSFF_closed'])
    assert model['actual_sustained_PHY_Bps'] is None
    assert not model['L0_calibration']['ratio_current_context_or_SSFF_qualified']
