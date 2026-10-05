import hashlib
import json
from pathlib import Path
import sys
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import qwen_rom_local_parent_composition as P
import uarch_model_qwen_local_parent as U

@pytest.fixture(scope='module')
def record():return P.R.obj(P.OUT/'model-r1.json')

def test_whole_field_pinwheel_has_exact_nonoverlapping_congruent_panels(record):
    f=record['field'];a=32*357.696;b=12*1360.8
    assert f['tiles']==1536 and len(f['placements'])==1536
    assert f['outer_square_um']==pytest.approx(a+b)
    assert f['selected_tile_slot_area_mm2']+f['central_hole_area_mm2']==pytest.approx(f['outer_envelope_area_mm2'])
    rectangles={0:(0,0,a,b),1:(a,0,a+b,a),2:(b,a,a+b,a+b),3:(0,b,b,a+b)}
    for tile in f['placements']:
        x,y=tile['origin_um'];w,h=(357.696,1360.8) if tile['orientation'] in ('R0','R180') else (1360.8,357.696)
        x0,y0,x1,y1=rectangles[tile['panel']]
        assert x>=x0-1e-7 and y>=y0-1e-7 and x+w<=x1+1e-7 and y+h<=y1+1e-7
    assert set(t['orientation'] for t in f['placements'])=={'R0','R90','R180','R270'}
    assert all(f['macro_R90_allowed'].values())
    assert f['rotated_global_directional_routes_and_PG_access_proven'] is False

def test_actual_launch_route_and_both_binary_edge_constraints_recomputed(record):
    launch=record['numeric_parent_root_launch']
    assert record['launch_geometry']['provider_to_sink_distance_um']>700
    assert launch['old_launch_window_transferred'] is False
    assert launch['external_paths_not_assumed_zero_delay'] is True
    for r in launch['corners'].values():
        assert r['max_launch_buffer_load_fF']<=46.08
        for s in r['scenarios']:
            assert set(s['launch'])=={'rise','fall'}
            assert s['root_external_RESETN_low_pulse_min_ps']>=330
            for t in s['launch'].values():assert t['delay_minmax_ps'][0]>0
    assert launch['source_contract_proven'] is False

def test_whole_field_clock_area_load_and_service_not_duplicated(record):
    f=record['field'];tile=record['local_tile_model']
    assert f['tile_cell_area_mm2']==pytest.approx(tile['complete_cell_area_um2']*1536/1e6)
    assert f['field_input_clock_buffer_area_mm2']==pytest.approx(f['field_input_clock_buffers']*.10206/1e6)
    assert f['tile_cell_plus_field_clock_buffer_area_mm2']==pytest.approx(f['tile_cell_area_mm2']+f['field_input_clock_buffer_area_mm2'])
    assert f['field_clock_terminal80ps_pass'] is True
    assert f['field_clock_ports']==102352*1536 and f['field_reset_pins']==56683*1536
    assert record['KV_TP4_service_macro_area_mm2']==pytest.approx(4*4.569720064)
    assert record['service_512macro_clock_loads_per_rank_separate_from_1536tiles'] is True
    assert record['startup_once_not_per_layer_token'] is True
    assert record['KV_cold_calendar_selected_production'] is False

def test_source_init_and_physical_gate_remain_explicit(record):
    assert U.qwen_rom_local_parent_price()['hardware_admission'] is False
    assert record['stored_Z']=='FAIL_RETAINED'
    assert record['historical_global157385_fit']=='FAIL_RETAINED'
    assert record['actual_source_reachable_binary_init_proven'] is False
    assert record['source_map_admission'] is record['PnR'] is False
    assert record['additional_maps']==record['numerical_runs']==0

def test_sourcepins_and_artifact_bytes(record):
    base=P.R.ROOT/P.OUT
    for name,d in json.loads((base/'sourcepins-r1.json').read_text())['sha256'].items():
        assert hashlib.sha256((P.R.ROOT/name).read_bytes()).hexdigest()==d,name
    for name,d in json.loads((base/'artifact-sha256-r1.json').read_text()).items():
        assert hashlib.sha256((base/name).read_bytes()).hexdigest()==d,name
