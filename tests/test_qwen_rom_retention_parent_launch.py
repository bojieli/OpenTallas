import hashlib
import json
from pathlib import Path
import sys
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import qwen_rom_retention_parent_launch as L
import uarch_model_qwen_retained_context as U

@pytest.fixture(scope='module')
def record():return L.R.obj(L.OUT/'model-r1.json')

def test_baseline_skew_failure_preserved_separately(record):
    b=record['baseline_clock_balance_failure']
    assert b['ss']['span_ps']==pytest.approx(2008.8987726466)
    assert b['ff']['span_ps']==pytest.approx(878.6254376326)
    for c,r in record['timing_preflight'].items():
        assert r['clock_sinks']==102352 and r['reset_sinks']==56683
        assert r['reset_bound_failures']>0
        assert b[c]['clock_sinks']==102299 and b[c]['balanced_CTS'] is False

def test_all_restoring_inversions_and_mask_branches_characterized(record):
    for c,r in record['restoring_data_load_price'].items():
        assert len(r['source_cells'])==85
        assert r['selector_consumer_pins']==80*33
        assert r['selector_buffer_max_load_fF']<=46.08
        assert r['whole_data_setup_hold_qualified'] is False
        for cell in r['source_cells']:
            assert cell['QN_total_cap_fF']>0 and cell['INV_output_cap_fF']>0
            assert max(v[1] for v in cell['restoring_INV_slew_minmax_ps'].values())<=320

def test_launch_route_replaces_unfitted32um_transfer(record):
    route=record['launch_route']
    assert route['provider_to_sink_distance_um']>700
    assert route['added_buffers']==6
    for c,r in record['actual_parent_launch'].items():
        assert r['finite_route_delay_minmax_ps'][0]>0
        assert r['required_external_go_ready_arrival_after_provider_CLK_ps'][0]>50
        assert r['proposed_source_window_pass'] is False
        assert r['setup_uncertainty_ps']==60 and r['hold_uncertainty_ps']==25
        assert r['source_arrivals_observed'] is False

def test_selected_model_and_independent_KV_calendar(record):
    r=U.qwen_rom_retained_context_price()
    assert r['selected_explicitly'] and r['hardware_admission'] is False
    assert record['conservative_reserved_area_um2']<125000
    assert record['persistent_KV']['cold_calendar_role']=='reference only, not selected production'
    assert record['external_RESETN_source_requirement']['deassert_after_primary_clock_ps']==[262,823]
    assert record['source_map_admission'] is False

def test_source_artifact_hashes(record):
    root=L.R.ROOT;base=root/L.OUT
    for p,d in json.loads((base/'sourcepins-r1.json').read_text())['sha256'].items():
        assert hashlib.sha256((root/p).read_bytes()).hexdigest()==d,p
    for p,d in json.loads((base/'artifact-sha256-r1.json').read_text()).items():
        assert hashlib.sha256((base/p).read_bytes()).hexdigest()==d,p
