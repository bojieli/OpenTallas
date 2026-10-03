import json
import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import qwen_rom_kv_credit17_physical as P


@pytest.fixture(scope='module')
def model():return P.price()


def test_regular_17_capacity_is_not_pooled129_or_a_port_replica(model):
    t=model['credit17']['target']
    assert t['regular_total_cohort_capacity']==8*t['group_credits']==136
    assert t['global_necessary_bound']==129
    assert t['pending_entries_per_PC']==64+4
    assert t['total_assembly_words']==56*85==4760
    assert [t[k] for k in ['return_groups_per_stack','column_paths_per_stack','global_fill_lanes','write_slots_per_PC','lookup_edges']]==[8,4,7,4,12]
    assert model['extra_PHY_replicas']==0
    assert all(s['context_RAM_replicas_added']==0 for s in model['controller_slots'])


def test_spill_assembly_header_and_alias_checks_paid_once(model):
    c=model['credit17'];f=c['FF_families']
    assert f['pending_spill']['FFs']==128*4*472
    assert f['assembly_words']['FFs']==(4760-4480)*787
    assert f['matched_headers']['FFs']==(136-128)*259
    assert c['selector_bits']['pending_cache_alias_equality_bits']==128*4*16*34
    assert c['new_FFs']==sum(v['FFs'] for v in f.values())
    assert sum(model['credit17_added_clock_pins_by_domain'].values())==c['new_FFs']
    parent=P.R.obj(P.C.OUT/'model-r6.json')
    assert model['source_sized_clock_pins']-parent['source_sized_clock_pins']==c['new_FFs']
    assert model['source_reset_upper']-parent['source_reset_upper']==c['new_FFs']
    assert model['known_composed_area_mm2']-parent['known_composed_area_mm2']==pytest.approx(c['delta_known_mm2'])


def test_mutable_protection_and_finite_routes_do_not_create_free_IO(model):
    c=model['credit17']
    for p in c['protected_new_records'].values():
        r,positions,masks=P.parity_layout(p['data_bits'])
        assert len(set(positions))==len(positions)==p['data_bits']
        assert (1<<r)>=p['data_bits']+r+1
        assert (1<<(r-1))<p['data_bits']+r
        assert p['code_bits']==p['data_bits']+r+1
        assert p['encoder_edges']==p['decoder_edges']==1
        assert not p['combinational_SSFF_closed']
    assert c['additional_boundary_bits']==43256-42452
    assert sum(r['additional_service_bits'] for r in c['route_reservations'])==804
    assert c['additional_route_buffer_reservation']>804
    for x in c['collector_load_and_slew'].values():
        assert x['load_fF']>8*.4
        assert x['rise_slew_ps'][1]<=80 and x['fall_slew_ps'][1]<=80
        assert x['cell']=='BUFx8_ASAP7_75t_R'
        assert x['terminal_spurs_per_driver']*x['terminal_spur_um']==128
        assert x['route_segment_rise_slew_ps'][1]<=80 and x['route_segment_fall_slew_ps'][1]<=80
        assert not x['whole_clock_or_reset_timing_qualified']


def test_fixed_work_floor_cannot_admit_capacity_or_transport(model):
    assert json.loads(json.dumps(model))==P.R.obj(P.OUT/'model-r4.json')
    c=model['credit17']
    assert not c['candidate_replayed'] and not c['capacity_admitted']
    assert model['credit17_full_token_latency_s'] is None
    assert model['credit17_fixed_work_bounds']['group17_floor_if_lifetimes_unchanged_s']<1/3000
    assert model['actual_sustained_PHY_Bps'] is None
    assert not any(model[k] for k in ['source_map_admission','PnR','actual_contextual_SSFF','default_enabled'])
    assert all(x['nominal_skew_ps']>20 for x in model['aligned_local_release']['corners'].values())
    assert model['known_composed_area_mm2']+model['remaining_area_before_unknown_placements_mm2']==pytest.approx(815)
