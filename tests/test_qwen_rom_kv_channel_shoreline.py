import hashlib
import json
import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import qwen_rom_kv_channel_shoreline as Q


def overlap(a,b):
    return a[0]<b[2]-1e-8 and b[0]<a[2]-1e-8 and a[1]<b[3]-1e-8 and b[1]<a[3]-1e-8


def test_native_PHY_and_all_source_tiles_legal_rectangles():
    m=Q.price();d=m['die']
    assert d['width_um']<=26000 and d['width_um']*d['height_um']/1e6==pytest.approx(815)
    assert d['columns']==68 and d['rows']==23 and d['unused_tile_footprints']==28
    assert {t['tile'] for t in m['tiles']}==set(range(1536))
    assert all(t['orientation']=='R0' for t in m['tiles'])
    assert [p['orientation'] for p in m['PHY_slots']]==['R0','R0','R180','R180']
    rectangles=[p['rectangle_um'] for p in m['PHY_slots']+m['controller_slots']]
    rectangles += [p['extension_rectangle_um'] for p in m['controller_slots']]
    rectangles += [[*t['origin_um'],t['origin_um'][0]+t['size_um'][0],t['origin_um'][1]+t['size_um'][1]] for t in m['tiles']]
    for i,a in enumerate(rectangles):
        assert a[0]>=0 and a[1]>=0 and a[2]<=d['width_um']+1e-8 and a[3]<=d['height_um']+1e-8
        assert all(not overlap(a,b) for b in rectangles[i+1:])
    #Dedicated M6/M8 bands overlay prepaid tiles; this proves geometry only,
    #not exclusive ownership against their currently unrouted control nets.
    for c in m['dedicated_fill_channels']:
        assert c['within_prepaid_tile_upper_metal']
        assert c['macro_OBS_max_layer']=='M4'
        assert not c['clocks_reset_and_all_other_signal_exclusivity_at_new_bands_proven']


def test_preserve_partition_and_separate_channel_track_ownership():
    m=Q.price()
    for c in m['dedicated_fill_channels']:
        lane=c['fill_lane'];assert sum(t['fill_lane']==lane for t in m['tiles'])==(220 if lane<3 else 219)
        assert all(t['tile']%7==lane for t in m['tiles'] if t['fill_lane']==lane)
        assert c['fill_tracks']+c['clock_tracks']+c['reset_ACK_tracks']+c['spare_tracks']==c['capacity']==1360
    assert m['new_channel_area_mm2']==0
    assert m['reserved_upper_metal_channel_footprint_mm2']==pytest.approx(4*96.768*68*357.696/1e6)
    assert m['historical_shared_cut']==dict(required=6925,available=1360,deficit=5565,verdict='FAIL_PRESERVED')
    for s in m['shoreline_cuts']:
        assert set(s['capacity_by_layer'])=={'M9'}
        assert s['capacity']>=s['two_stack_mid_cut_demand']==2*9209+128
        assert s['PHY_pin_spread_50percent_capacity']>=9209
    assert m['original_tile_corridor_um']==96.768


def test_source_domain_counts_and_no_macro_replicas_or_free_bandwidth():
    m=Q.price();d=Q.R.obj(Q.OUT/'inputs/ampere-dependency-r1.json')['cells']
    assert m['delta_service_domain_FFs']+m['delta_stream_domain_FFs']==7955700
    assert m['retained_assembly_FFs']==3223552
    assert m['source_sized_clock_pins']==7955700+3223552+2052184+560+4+8
    assert m['source_reset_upper']==7955700+3223552+2052184+8
    assert m['collector_replica_counts']==d['clock_reset_replicas']
    assert m['collector_buffers_by_family']==d['collector_buffers_by_local_replica_family']
    assert m['extra_PHY_replicas']==0 and m['source_request_ports_per_stack']==1
    assert m['actual_sustained_PHY_Bps'] is None and m['PHY_stack_bandwidth_required_Bps']==113135616000
    assert m['assembly_clock_domain_source_binding'] is None


def test_load_sized_PHY_clock_and_component_units():
    m=Q.price()
    for c,f in m['four_PHY_clock_feeds'].items():
        assert f['load_fF']==pytest.approx(50+16*.165790)
        assert f['cell']=='BUFx12_ASAP7_75t_R'
        assert f['unchanged_80ps_slew_demand_met']
        assert f['output_low_pulse_lower_ps']>=f['PHY_min_pulse_ps']
        assert f['output_high_pulse_lower_ps']>=f['PHY_min_pulse_ps']
        assert not f['source_1GHz_SSFF_admitted']
    kv=Q.R.obj(Q.OUT/'inputs/model-r4.json')
    area=747.6521730048+m['service_known_reservation_mm2']+m['inherited_other_service_debit_mm2']+kv['slot']['parent_interface_mm2']+kv['PHY']['existing_physical_footprint_rank_mm2']+m['new_channel_area_mm2']+m['route_buffer_area_mm2']+(m['PHY_clock_driver_area_um2']+m['PHY_local_release_reserved_area_um2'])/1e6
    assert m['known_composed_area_mm2']==pytest.approx(area)
    assert m['remaining_area_before_unknown_placements_mm2']==pytest.approx(815-area)
    assert all(0<s['minimum_cell_macro_utilization']<1 for s in m['controller_slots'])
    assert all(r['buffer_reservation']>r['source_signal_bits'] for r in m['source_to_controller_route_lower_bounds'])


def test_calendar_and_context_failures_cannot_be_admitted():
    m=Q.price()
    assert m['six_fill_constructive_calendar_ps']>m['target_token_ps']
    assert m['minimum_fill_integer_full_schedule'] is None
    assert m['minimum_fill_integer_under_preserved_overhead']==7
    assert m['successor_observed_conditional_calendar_s']>1/3000
    assert not m['source_matched_successor_calendar_admitted']
    assert not any(m[k] for k in ('default_enabled','source_map_admission','PnR','actual_contextual_SSFF','complete_route_allocation','six_fill_calendar_admitted','second_decode','new_SU_spatial_redistribution'))
    assert 'cuts and routes' in m['missing_physical_bindings'][0]
    assert m['levels_used']==[1,2,3,4,5]


def test_cold_model_and_pinned_inputs():
    m=Q.R.obj(Q.OUT/'model-r5.json')
    assert json.loads(json.dumps(Q.price()))==m
    for name in ('sourcepins-r3.json','artifact-sha256-r3.json'):
        for p,h in Q.R.obj(Q.OUT/name).items():
            assert hashlib.sha256((Q.R.ROOT/p).read_bytes()).hexdigest()==h
