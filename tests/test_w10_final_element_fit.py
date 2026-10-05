import copy
import json
from pathlib import Path
import sys
import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import w10_final_element_fit as F

@pytest.fixture(scope='module')
def receipt():return json.loads(json.dumps(F.build()))

def test_actual_storage_parity_capacity_not_q_geometry_transfer(receipt):
    s=receipt['physical_storage']
    assert s['logical_capacity_bits']==s['physical_capacity_bits']==4489216
    assert s['four_macro_LEF_area_um2']==pytest.approx(31525.4592)
    assert s['model_macro_subtraction_um2']==pytest.approx(30004.94016)
    assert not receipt['fullmapped_element']['actual_q_area_from_this_BF16_map']

def test_negative_requested_and_synthetic_are_not_final_q(receipt):
    assert receipt['geometry_sources']['requested_failed_outline_um']==[510.84,126.9]
    assert receipt['geometry_sources']['requested_failed_density']==.6
    assert receipt['constraints']['density']==.5
    assert not receipt['geometry_sources']['synthetic_head_is_actual_q']
    assert not receipt['q_final_evidence']['current_q_footprint_binding']
    assert not receipt['q_final_evidence']['necessary_terminal_inputs_present']

def test_negative_terminal_markers_or_empty_unpinned_artifacts():
    q=copy.deepcopy(F.read(F.QFAIL));p=copy.deepcopy(F.read(F.QPRE))
    q.update(status='pass',flow_completed=True);q['design']['closed']=True
    p['preflight']['issues']=[];p['element_timing_passes']=True;p['physically_clean_route']=True
    p['preflight']['artifacts']={n:{'size_bytes':0,'sha256':''} for n in ('6_final.odb','6_final.sdc','6_final.spef','6_final.v')}
    assert not F.final_q_evidence(q,p)['necessary_terminal_inputs_present']
    for v in p['preflight']['artifacts'].values():v['size_bytes']=100
    assert not F.final_q_evidence(q,p)['necessary_terminal_inputs_present']
    for v in p['preflight']['artifacts'].values():v['sha256']='a'*64
    # A necessary metadata gate passes; final LEF/ETM/source/exactness still unbound.
    assert F.final_q_evidence(q,p)['necessary_terminal_inputs_present']
    assert not F.final_q_evidence(q,p)['current_q_footprint_binding']

def test_ceiling_crosses_capacity_boundary(receipt):
    p=next(x for x in receipt['stage_q_footprint_ceilings'] if x['stages']==45)
    assert p['maximum_q_footprint_um2']==pytest.approx(65974.6255543567)
    bf=receipt['fullmapped_element']['outline_um'];width=510.84
    below=F.compose((width,(p['maximum_q_footprint_um2']-1)/width),bf)
    above=F.compose((width,(p['maximum_q_footprint_um2']+1)/width),bf)
    assert below['conditional_min_layer_stages']==45
    assert above['conditional_min_layer_stages']==46

def test_historical_nonclosing_geometry_sensitivities(receipt):
    c=receipt['geometry_only_substitutions']
    assert [v['conditional_min_layer_stages'] for v in c.values()]==[45,46,49]
    assert all(v['field_need_mm2']<=v['usable_field_mm2']<v['preceding_stage_need_mm2'] for v in c.values())
    assert all(v['actual_q_transfer'] is False and v['full_token_rate'] is None for v in c.values())
    assert not receipt['geometry_sources']['historical_p5_is_current_PP_q']

def test_scalar_reserve_reduces_q_ceiling_not_sized_here(receipt):
    d=receipt['scalar_owner_dependency']
    p=next(x for x in receipt['stage_q_footprint_ceilings'] if x['stages']==45)
    assert d['actual_extra_field_mm2'] is None
    assert d['baseline_geometry_only_extra_headroom_at_S45_mm2']==pytest.approx(3.8201355019634207)
    assert p['maximum_q_footprint_um2']-d['one_mm2_extra_reserve_sensitivity']['maximum_q_footprint_um2']==pytest.approx(300.78240778792474)

def test_whole_expert_integer_plan_not_replaced_by_fractional_area(receipt):
    e=receipt['expert_owner_dependency']
    assert e['expert_only_stage_count']==46 and e['historical_q_pair_mask']==3749
    assert e['maximum_stage_expert_entries']==1023 and e['expected_slices']==184320
    assert e['historical_q_transfer'] is False and e['integer_allocator_replayed_here'] is False

def test_archived_q_actual_area_refutes_original50pct_slot(receipt):
    a=receipt['archived_failed_q_area_witness']
    assert a['stdcell_synth_um2']==21809.9 and a['stdcell_grt_um2']==24297.8
    assert a['synthesis_minimum_core_um2_before_reserves']==pytest.approx(75145.3)
    assert a['requested_core_shortfall_um2_before_reserves']==pytest.approx(10595.6)
    assert not a['uniform50pct_existing_outline_pass'] and not a['actual_q_transfer']
    s=a['projections']['synthesis'];g=a['projections']['global_route']
    assert s['rows']==612 and g['rows']==648
    assert s['source_outer_frame_y_um']==g['source_outer_frame_y_um']==.54
    assert s['outline_um']==pytest.approx([510.84,165.78])
    assert g['outline_um']==pytest.approx([510.84,175.5])
    assert s['composed_geometry']['conditional_min_layer_stages']==53
    assert g['composed_geometry']['conditional_min_layer_stages']==55
    assert all(p['density']==.5 and not p['current_q_transfer'] for p in (s,g))

def test_model_registry_cleaned_and_no_source_mutation():
    before=copy.deepcopy(F.U.CONS_PITCH)
    F.compose((510.84,126.9),(1002.89,173.07))
    assert F.U.CONS_PITCH==before

def test_saved_receipt_and_admission_scope(receipt):
    assert receipt==json.loads((ROOT/F.OUT/'fit.json').read_text())
    assert receipt['source_sha256']['tools/uarch_model.py']=='2da5b6d90adfbeb58ca9355db636835205bf6953328a247bf709c6ab93260c45'
    assert not receipt['adopt'] and not receipt['physical_admission'] and receipt['jobs_launched']==0
    assert receipt['headline_rate'] is None and receipt['latency']['full_token_cycles'] is None
