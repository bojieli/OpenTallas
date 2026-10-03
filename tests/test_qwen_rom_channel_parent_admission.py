import json
import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import qwen_rom_channel_parent_admission as C


@pytest.fixture(scope='module')
def model():
    return C.price()


def test_current_source_and_handoff_discrepancy_preserved(model):
    assert json.loads(json.dumps(model))==C.R.obj(C.OUT/'model-r6.json')
    assert model['Russell_selected_commit']=='02e9c04b7'
    assert model['successor_model_and_live_source_match']
    assert model['handoff_discrepancy']['committed_conditional_us']==pytest.approx(412.9013)
    assert model['service_known_reservation_mm2']==18.381568
    assert model['finite_service_deficit_us']==pytest.approx(79.5679666667)
    assert model['reported_service_deficit_us']>0


def test_control_tracks_and_controller_reservation_are_paid(model):
    cut=model['current_shared_cut']
    assert cut['required']==7336+637
    assert cut['assigned_fill_control']+cut['clock_reset_reserved']+cut['remaining_spare']==cut['partitioned_channel_capacity']
    assert model['known_composed_area_mm2']+model['remaining_area_before_unknown_placements_mm2']==pytest.approx(815)
    assert all(0<s['minimum_cell_macro_utilization']<1 for s in model['controller_slots'])
    assert model['service_boundary_cut_ledger']['remaining_nonfill_bits']==35116


def test_good_local_release_cuts_cannot_hide_clock_ACK_or_source_failure(model):
    local=model['aligned_local_release']
    assert local['total_clock_pins']==116628 and local['total_reset_pins']==70959
    assert all(c['clock']<=64 and c['reset_ACK']<=64 for c in local['cuts'].values())
    for c in local['corners'].values():
        assert c['raw_reset_failures']==c['controlled_reset_failures']==0
        assert c['nominal_skew_ps']>20 and c['ACK_out_of_characterization']>0
    assert len(model['admission_failures'])==7
    assert not any(model[k] for k in ('source_map_admission','PnR','actual_contextual_SSFF','default_enabled','complete_route_allocation'))
