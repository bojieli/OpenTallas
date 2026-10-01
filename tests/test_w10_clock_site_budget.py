import json
import sys
from pathlib import Path
import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import w10_clock_site_budget as C

@pytest.fixture(scope='module')
def receipt():
    return C.build()

def test_full_endpoint_groups_integer_buffers(receipt):
    assert [g['sinks'] for g in receipt['groups']] == [10108,6161,5269,67762,1,1,1,1,2441]
    assert [g['buffers'] for g in receipt['groups']] == [424,262,224,2828,7,7,7,7,107]
    assert receipt['buffer_replicas']==3873
    assert receipt['clock_network']['endpoint_pins']==91745

def test_physical_area_density_and_model_composition(receipt):
    b=receipt['slot'];m=b['composed_model']
    assert b['additional_buffer_sites']==61968
    assert b['additional_clock_buffer_um2']==pytest.approx(903.49344)
    assert b['rows']==625 and b['exclusive_clock_channel_sites']==33750
    assert b['outline_um']==pytest.approx([1002.89,173.07])
    assert b['stdcell_spare_um2']==pytest.approx(39.46534)
    assert m['stages']==45 and m['dies']==224
    assert m['required_field_mm2']<=m['usable_field_mm2']<m['preceding_stage_field_mm2']

def test_ss_loads_and_fixed_wire_guard(receipt):
    assert receipt['predicates']['fixed_endpoint_cap_and_guarded_nominal_wire_pass']
    assert receipt['groups'][-1]['leaf_load']['total_ff']==pytest.approx(172.653312)
    assert receipt['buffer']['SS_output_max_ff']==368.64
    assert receipt['groups'][0]['tree_driver']['total_ff']==pytest.approx(8.3923)

def test_negative_unbuffered_logic_icg_overload():
    owner=json.loads((C.OWNER/'audit.json').read_text())
    assert all(not C.cap_witness(g['total_endpoint_CLK_capacitance_ff'],46.08,0)['pass_half_maxcap']
               for g in owner['icg_gates'][:4])

def test_negative_wire_and_library_limits():
    assert not C.cap_witness(8*2.0635+24*.446638,368.64,600)['pass_half_maxcap']
    assert not C.cap_witness(1.121,10,25)['pass_half_maxcap']

def test_negative_depth_and_old_slot(receipt):
    with pytest.raises(AssertionError,match='seven-stage'):
        C.tree(32*4**7+1)
    assert not receipt['slot']['previous_slot_fits']
    # Omitting every buffer and clock channel makes the old capacity appear sufficient.
    assert C.slot(0,.23328,16,clock_columns=0)['rows']==617
    assert C.slot(3873,.23328,16,clock_columns=0)['rows']==623

def test_phase_and_geometry_are_not_admitted(receipt):
    assert receipt['latency']['ungated_buffer_stages']==7
    assert receipt['latency']['gated_buffer_stages']==14
    assert receipt['latency']['ICG_delay']=='UNKNOWN'
    assert not receipt['physical_admission'] and not receipt['adopt']
    assert receipt['jobs_launched']==0
    assert not receipt['predicates']['SS_FF_timing']
    assert 'conditional_ar_tokens_s' not in receipt['slot']['composed_model']

def test_negative_ignoring_source_track_derating(receipt):
    network=receipt['clock_network']
    assert network['actual_routing_capacity_adjustment']==.25
    assert 4*(1-.25)<network['per_internal_branch_tracks']
    assert network['modeled_usable_tracks_each']>=network['per_internal_branch_tracks']
    assert network['leaf32_local_cut_physical_tracks_if_all_coincident']==43

def test_saved_receipt_and_source_pins(receipt):
    saved=json.loads((C.INPUT/'receipt.json').read_text())
    assert saved==receipt
    assert saved['source_sha256']['tools/uarch_model.py']=='2da5b6d90adfbeb58ca9355db636835205bf6953328a247bf709c6ab93260c45'
