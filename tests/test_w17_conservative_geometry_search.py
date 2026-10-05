import importlib.util
import sys
from decimal import Decimal as D
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
spec=importlib.util.spec_from_file_location('geometry_search',ROOT/'tools/w17_conservative_geometry_search.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
@pytest.fixture(scope='module')
def model():return m.search([2048,1536,1024,768,512])
def test_fixed_geometry_rejects_larger_fields(model):
    g=model['fixed_sourcebound_product_geometry']
    assert g['product']=='w10_refit_crot' and g['die_mm2']==815
    assert D(g['usable_field_mm2'])==D('457.96549650802586')
    rows={r['q_pairs']:r for r in model['candidates']}
    assert not rows[2048]['q_cfg_BF1024_area_screen_pass']
    assert not rows[1536]['q_cfg_BF1024_area_screen_pass']
    assert D(rows[1024]['fixed_product_field_remainder_after_q_cfg_BF1024_mm2'])==D('22.85419819378586')
def test_integer_capacity_and_descriptor_change(model):
    r=next(r for r in model['candidates'] if r['q_pairs']==1024)
    assert (r['whole_triplet_capacity'],r['expert_only_physical_stages'],r['TP4_expert_die_count'])==(85,181,724)
    assert r['maximum_full_stage_physical_bank_rows']==4080
    assert sum(x['pairs'] for x in r['q_mask'])==1024
    assert r['descriptor']['cfg_cycles']==35 and r['owner_entry_bits']==16
    assert r['per_expert_cfg_plus_stream_partial_cycles']==329
def test_per_rank_serialization_not_aggregate_speed(model):
    r=next(r for r in model['candidates'] if r['q_pairs']==1024)
    d=r['dispatch_sensitivity']
    assert d['aggregate_bits_per_source_cycle']==1024
    assert d['request_serialization_cycles_per_hop']==320
    assert d['return_serialization_cycles_per_hop']==80
    assert d['source_order_six_expert_worst_linear_dispatch_serialization_cycles']==528000
def test_power_bound_failure_and_partial_fit_cannot_admit(model):
    assert all(not r['conditional_q_power_envelope_within_die_budget'] for r in model['candidates'])
    assert all(not r['complete_geometry_fit'] for r in model['candidates'])
    assert not model['engine_RTL_build_ready'] and not model['complete_architecture_admission']
    assert not model['construction_assumption']['actual_mapped_minimum']
