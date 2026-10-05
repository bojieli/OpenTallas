import sys
from pathlib import Path
from fractions import Fraction as F
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from qwen_hbm_downstream_contract_r8 import fixture,audit_sources,costs,OwnedRetirementLedger,SLOW

def test_exact272_metadata_has_no_invented_retirement_or_lease():
    f=fixture()
    assert f['sector_count']==272 and f['partial_RMW_count']==256
    assert list(f['sectors_by_stack'].values())==[64,64,64,80]
    assert f['supplied_retirement_events']==[] and f['supplied_lease_ACKs']==[]
    assert len(f['KV_prefix_read_rows'])==288
    assert {x['ordinal'] for x in f['sector_rows']}==set(range(272))

def test_actual_endpoint_audit_and_opcode_credit_circular_wait():
    a=audit_sources()
    assert not a['existing_retirement_is_Qwen_provider']
    assert all(c['status']=='PASS_SOURCE_AUDIT_ONLY' for c in a['checks'])
    assert 'CIRCULAR_WAIT' in a['sector_vs_opcode_retirement']['verdict']

def test_four_reservations_require_real_retirement_input():
    l=OwnedRetirementLedger(fixture()['sector_rows'])
    for i in range(4):assert l.reserve(i,i,i,10,11)
    assert not l.reserve(4,4,4,10,11)
    assert not l.bits and not l.credited
    with pytest.raises(ValueError,match='reversecredit'):l.reverse_credit(0,10000,1000)
    with pytest.raises(ValueError,match='all272'):l.acquire_lease()

def test_wrong_epoch_or_same_edge_retirement_rejected():
    l=OwnedRetirementLedger(fixture()['sector_rows']);l.reserve(0,0,55,123,456)
    with pytest.raises(ValueError,match='owner'):l.retire(0,0,55,124,456,0,SLOW,2*SLOW,SLOW)
    with pytest.raises(ValueError,match='registered'):l.retire(0,0,55,123,456,0,SLOW,SLOW,SLOW)
    assert not l.bits

def test_271_bit_snapshot_cannot_publish_and_empty_consumers_cannot_release():
    l=OwnedRetirementLedger(fixture()['sector_rows'])
    # Negative structural snapshot, not generated callbacks or real retirements.
    l.bits=set(range(271));l.credited=set(range(271))
    with pytest.raises(ValueError,match='all272'):l.acquire_lease()
    with pytest.raises(ValueError,match='SCORES/PV'):l.release_lease()

def test_inherited_occupancy_timerlogic_viaPDN_keep_slot_failed():
    c=costs()
    assert c['inherited_controller_fabric_reservation_mm2_per_stack']==10
    assert c['area_overflow_lower_bound_mm2_per_stack']>1
    assert c['timer_compare_mux_proxy_mm2']>0 and c['additional_provider_FF_bits']>0
    assert c['occupancy_overlap_credit']==0 and c['signal_share_reserved']==.5
    assert len(c['PDN_profiles'])==2
    assert c['candidate_overmacro_M4_to_upper_data_endpoint_vias_per_stack']==60352
    assert not c['slot_fit'] and c['failed_corridor']['verdict'].startswith('FAIL')


def test_exact_port_contract_has_no_real_provider_or_lease_events():
    from qwen_hbm_downstream_contract_r8 import provider_ports,compose
    ports=provider_ports();m=compose()
    assert not ports['source_endpoint_presence'] and not ports['compile_GO']
    assert ports['geometry']['retire_channels_per_die']==2
    assert m['fixture']['accepted_retirements']==0 and m['fixture']['lease_ACKs']==0
    assert m['candidate_added_service']['sector_commit_to_owned_retire_serial_edges']==1
    assert m['candidate_added_service']['scoreboard_work_floor_ps']=='2720000/9'
    assert not m['provider_PASS'] and not m['RTL_admission']
