import json
from pathlib import Path
import sys
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import uarch_model_qwen_balanced_context as U

def test_replacement_credit_still_cannot_admit_clock_construction():
    r=U.qwen_rom_balanced_context_price();a=r['admission_decision']
    assert a['old_added_clock_reset_reservations_discarded_for_lower_bound'] is True
    assert a['area_lower_bound_um2']==pytest.approx(sum(a['area_lower_bound_terms_um2'].values()))
    assert a['area_lower_bound_um2']>a['cell_ceiling_um2']==125000
    assert a['area_lower_bound_fit'] is False
    assert r['hardware_admission'] is False and r['selected_explicitly'] is True
    assert a['provider_clock_slew_max_ps']['ss']>a['provider_clock_slew_limit_ps']==80
    assert a['clock_cut_failures']['1:489.888']['monotone_geometric_crossings']==325

def test_actual_graph_join_never_converts_initialization_or_Z_to_pass():
    r=U.qwen_rom_balanced_context_price();a=r['admission_decision']
    assert a['latest_actual_graph']['address_FFs']==24
    assert a['latest_actual_graph']['KV_raw_capture_FFs']==512
    parent=json.loads((U.R.ROOT/U.OUT/'inputs/parent-current-graph-review.json').read_text())
    assert parent['actual_parent_driven_initialization_contract'] is False
    assert a['initialized_binary_source_contract']['source_reachable_initialization_proven'] is False
    assert a['initialized_binary_source_contract']['stored_Z']=='FAIL_RETAINED'
    assert a['source_map_admission'] is a['PnR_admission'] is False
    assert a['additional_maps']==a['second_decode_position_runs']==0
