import gzip
import hashlib
import json
from pathlib import Path
import sys

import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import qwen_rom_mapped_root_pg_context as M


def test_actual_tech_directions_and_offsets():
    t=M.tech()
    assert t['M6']['direction']==t['M8']['direction']=='HORIZONTAL'
    assert t['M5']['direction']==t['M7']['direction']=='VERTICAL'
    assert t['M6']['pitch']==.064 and t['M8']['pitch']==.08
    assert t['M5']['offset']==.012 and t['M6']['offset']==.016


def test_directional_capacity_preserves_selected_slot_with_PG_exclusions():
    pg=M.corridor_pg()
    assert pg['selected_corridor_um']==96.768
    assert pg['selected_slot']['w_um']==357.696 and pg['selected_slot']['h_um']==1360.8
    assert len(pg['signal_lanes'])==1048+64+64+184
    assert sum(r['kind']=='fill' for r in pg['signal_lanes'])==1048
    for name,spec in pg['layers'].items():
        assert len(spec['signal_centers_um'])==spec['half_share_signal_budget']
        assert spec['PG_excluded_tracks']<=spec['raw_tracks']//2
        for center in spec['signal_centers_um']:
            assert abs((center-spec['offset'])/spec['pitch']-round((center-spec['offset'])/spec['pitch']))<1e-5
            for stripe in pg['PG_stripes']:
                if stripe['layer']==name:
                    assert abs(center-stripe['center_um'])>=stripe['width_um']/2+spec['width']/2+spec['PG_clearance']-1e-8
    assert pg['physical_admission'] is False


def test_two_directional_signal_feeds_have_unique_tracks_and_turns():
    pg=M.corridor_pg()
    lanes=pg['signal_lanes']
    assert len({(r['vertical_layer'],r['vertical_x_um']) for r in lanes})==1360
    assert len({(r['horizontal_layer'],r['horizontal_y_um']) for r in lanes})==1360
    assert {(r['vertical_layer'],r['horizontal_layer'],r['turn_via']) for r in lanes}=={('M5','M6','VIA56'),('M7','M8','VIA78')}
    assert pg['selected_M6_M8_capacity_not_increased'] is True
    assert pg['vertical_M5_M7_feed_required'] is True


def test_polarity_and_grid_for_all_PG_connections():
    pg=M.corridor_pg();lookup={(s['layer'],s['center_um']):s for s in pg['PG_stripes']}
    for s in pg['PG_stripes']:
        tech=M.tech()[s['layer']]
        assert abs((s['center_um']-tech['offset'])/tech['pitch']-round((s['center_um']-tech['offset'])/tech['pitch']))<1e-5
    for v in pg['PG_same_polarity_vias']:
        assert lookup['M5',v['x_um']]['net']==lookup['M6',v['y_um']]['net']==v['net']
    assert pg['IR_EM_DRC_routed'] is False


def test_committed_actual_model_inventory_and_retention_are_separate():
    r=M.load(M.OUT/'model-r1.json')
    assert r['mapped_sha256']==M.MAP_SHA
    groups=r['mapped_loads']['groups']
    assert sum(groups[g]['pins'] for g in ('logic_clock','ROM_clock','KV_clock'))==102299
    assert sum(groups[g]['pins'] for g in ('direct_parent_reset','distributed_reset'))==56630
    fix=r['retention_successor_price']
    assert fix['required_explicit_FFs']==85 and fix['added_FFs']==53
    assert fix['restoring_INV_reservation']==85
    assert fix['total_retention_increment_um2']==pytest.approx(23.80914)
    assert fix['mapped_counts_after_retention']=={'clock':102352,'reset':56683}
    assert fix['source_contract_qualified'] is False and fix['Z_literal_contract_failure_retained'] is True
    assert r['source_binding']['old_metadata_reset_buffers_bound']==15
    assert len(r['source_binding']['raw_reset_combinational_controls'])==2
    for corner,row in r['timing_preflight'].items():
        assert row['clock_sinks']==102299 and row['reset_FF_sinks']==56630
        assert row['provider_CLK_arrival_minmax_ps'][0]>0
        assert row['provider_external_reset_route_rise_minmax_ps'][0]>0
        assert row['branch_max_load_fF']<=46.08
        assert row['external_reset_required_deassert_minmax_ps'][0]<row['external_reset_required_deassert_minmax_ps'][1]
        assert row['actual_extracted_contextual_SSFF'] is False
    assert r['admission']['additional_maps']==r['admission']['numerical_runs']==0
    assert r['admission']['complete_gate_PASS'] is False


def test_pin_manifests_and_all_root_clock_sources_are_finite():
    base=M.ROOT/M.OUT
    for name,d in json.loads((base/'sourcepins-r1.json').read_text())['sha256'].items():
        assert hashlib.sha256((M.ROOT/name).read_bytes()).hexdigest()==d,name
    for name,d in json.loads((base/'artifact-sha256-r1.json').read_text()).items():
        assert hashlib.sha256((base/name).read_bytes()).hexdigest()==d,name
    g=json.loads(gzip.decompress((base/'root-bound-allocation-r1.json.gz').read_bytes()))
    c=g['added_primitive_cells'];clk=g['entry_ports']['clock']
    raw=[name for name,row in c.items() if any(bits==[clk] for pin,bits in row['connections'].items() if pin in ('A','clk_stream'))]
    assert raw==['bind_clock_entry']
    assert len(g['legacy_reset_BUFFERS'])==15
    assert any(e['sink']=='context_provider' and e['pin']=='external_reset_n' and e['length_um']>0 for e in g['wire_edges'])
    assert any(e['sink']=='context_provider' and e['pin']=='clk_stream' and e['length_um']>0 for e in g['wire_edges'])
    assert g['complete_gate_PASS'] is False
