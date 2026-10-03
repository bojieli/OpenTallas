import itertools
import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).parents[1]/'tools'))
import dsrom_I66_effective_idle_contract as M


def test_default_off_exact_native_idle_truth_table():
    for native,active,retired in itertools.product([0,1],repeat=3):
        assert M.effective_idle(native,active,retired)==native


def test_enabled_hook_blocks_only_active_unretired_debt_and_keeps_native_idle():
    for native,active,retired in itertools.product([0,1],repeat=3):
        expected=int(native==1 and (active==0 or retired==1))
        assert M.effective_idle(native,active,retired,enabled=True)==expected
    assert M.effective_idle(1,1,0,enabled=True)==0
    assert M.effective_idle(0,1,1,enabled=True)==0
    assert M.effective_idle(1,0,0,enabled=True)==1


def sample():
    return dict(edge=20,adapter_st=5,s_go=0,native_idle=1,phase_active=1,
                qualified_retired=1,effective_idle=1,healthy_reset_epoch=1)


def test_F_sample_and_three_distinct_acceptance_edges():
    r=M.validate_wait_exit(sample())
    assert r['next_QE_core_S_ISSUE_min']==21
    assert r['next_registered_ROM_adapter_accept_min']==22
    assert r['adjacent_SU_core_S_ISSUE_min']==27
    assert r['adjacent_SU_adapter_front_latch_min']==28
    assert r['adjacent_SU_vector_accept_min_if_ready']==29
    assert r['publication_latest_postNBA_edge']==19
    assert r['service_upper_bound'] is None


@pytest.mark.parametrize('change',[dict(adapter_st=0),dict(s_go=1),dict(native_idle=0),
                                  dict(qualified_retired=0),dict(effective_idle=0),
                                  dict(healthy_reset_epoch=0),dict(s_go=False),dict(edge=1.0)])
def test_idle_observation_is_not_qualified_WAIT_exit(change):
    s=sample();s.update(change)
    with pytest.raises(ValueError):M.validate_wait_exit(s)


def test_IDLExunretired_old_phase_exposes_bypass_not_actual_failure():
    with pytest.raises(ValueError,match='bypasses idle-only hook'):M.guard_lifecycle(0,1,0)
    assert M.guard_lifecycle(5,1,0)
    assert M.guard_lifecycle(0,1,1)
    assert M.guard_lifecycle(0,0,0)


def test_independent_old_register_state_matches_core_front_vector_minima():
    r=M.stepped_minimum()
    assert r['events']==dict(QE_core_issue=1,registered_ROM_accept=2,
                            SU_core_issue=7,SU_front_latch=8,SU_vector_accept=9)
    assert r['source_model_trace'][0]['adapter_st']==5
    assert r['source_model_trace'][1]['adapter_st']==0
    assert not r['actual_runtime']


@pytest.mark.parametrize('stall',[dict(issue_stalls=3),dict(decode_stalls=4),dict(vector_stalls=8),
                                dict(issue_stalls=2,decode_stalls=1,vector_stalls=3)])
def test_source_stalls_cannot_shorten_relative_order_or_create_upper_bound(stall):
    r=M.stepped_minimum(**stall)['events']
    assert r['QE_core_issue']>=1 and r['registered_ROM_accept']==r['QE_core_issue']+1
    assert r['SU_core_issue']>=r['QE_core_issue']+6
    assert r['SU_front_latch']==r['SU_core_issue']+1
    assert r['SU_vector_accept']>=r['SU_front_latch']+1
    assert M.minima(0)['service_upper_bound'] is None


@pytest.mark.parametrize('value',[True,1.0,-1,2])
def test_bits_cannot_be_bool_float_or_out_of_range(value):
    with pytest.raises(ValueError):M.effective_idle(value,1,1,enabled=True)


def test_adjacent_six_pairs_and_F_previous_phase_lineage():
    m=M.model()
    pairs={(r['consumer_pc'],r['adjacent_QE_pc'],r['F_is_WAIT_exit_of_pc']) for r in m['chains']}
    assert pairs=={(70,69,68),(80,79,73),(85,84,83),(90,89,88),(95,94,93),(98,97,94)}
    assert len(m['chains'])==12
    assert m['authority']['source_commit']=='e380a8e13de1d7f7543e68f0feb1747ae8cebcb3'
    assert not m['additional_SU_guard'] and not m['build_admitted']
    assert m['current_journal'] is None and m['live_job'] is None
    assert not m['native_wrong_data_or_deadlock_claim']


def test_peer_floor_is_single_reference_not_inclusion_credit_or_timing_admission():
    m=M.model();floor=m['hardware_reference_floor']
    assert floor['gross_control_bits']==2
    assert floor['phase_active_existing_containment_credit']==0
    assert not floor['hold_closed']
    assert floor['identity_compare_counters_credit_ledger_CDC_drivers_routes_clock_reset_PG_extra']
    assert all(r['physical_pins_route'] is None for r in m['physical_routes_required'])
    assert m['observer_only']['new_hardware_ports']==0
