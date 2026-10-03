import sys,copy
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import dsrom_selector_capture_composition as M

def test_exact_source_wait_masks_not_ME_fences():
    m=M.model();assert len(m['admission_proof'])==12
    assert all(not p['explicit_ME_wait'] and not p['explicit_QE_wait'] for p in m['admission_proof'])
    assert sum(p['explicit_SU_wait'] for p in m['admission_proof'])==2
    assert m['holding_ROM_idle_does_not_prove_all_consumer_admission_fenced']
    assert m['actual_consumer_deadline'] is None;assert not m['build_admitted']

def test_bank_vs_VM_address_lifetime_and_four_frame_lower_bound():
    m=M.model()['lifetimes'];assert m['dispatch_only_VM_version_lease_lower_bound']==4
    assert m['witness']==dict(pc=69,producers=[66,67,68,69])
    assert m['actual_read_tag_lifetime_maximum'] is None
    assert m['bank_rearm_before_first_shared_consumer_required']==[[66,67,70]]

def test_c9_single_selected_clock_not_phase_credit():
    m=M.model();assert m['selected_clock_commit'].startswith('c9d19ed59')
    assert m['clock_bank']['core_clock70406']==70406
    assert m['clock_raw_correction_BUF']==68614
    assert m['clock_logical_depths']==[25,23]
    assert m['clock_parent_phase_reset_union'] is None

def fixture():
    clock=dict(domain='software_test_native_clk',origin_id='test_reset',period_ps='10',reset_qualified=True,accepted_provider_enrolled=True)
    events=[dict(row=r,domain=clock['domain'],origin_id=clock['origin_id'],identity='software_test_identity',consumer_identity='software_test_identity',
        full_writer_coverage=True,native_other_ROM_excluded=True,read_accept_ps=10*r,VM_visible_ps=10*r+20,
        SU_read_ps=10*r+30,observed_Xtag_ps=10*r+50,captured_credit_ps=10*r+40,positive_CDC_return_ps=20) for r in range(576)]
    return events,clock

def test_finite_deadline_exact_positive_credit_not_sameedge_reuse():
    e,c=fixture();m=M.finite_deadline(e,c)
    assert m['minimum_actual_visibility_to_read_slack_ps']=='10'
    assert m['minimum_source_read_credit_capacity_for_supplied_acceptances']==5
    assert not m['physical_credit_station_admission']

@pytest.mark.parametrize('bad',['clock','origin','writer','ROM','identity','visible','tag','CDC'])
def test_no_missing_provider_to_default_zero(bad):
    e,c=fixture()
    if bad=='clock':c['accepted_provider_enrolled']=False
    if bad=='origin':e[0]['origin_id']='other'
    if bad=='writer':e[0]['full_writer_coverage']=False
    if bad=='ROM':e[0]['native_other_ROM_excluded']=False
    if bad=='identity':e[0]['consumer_identity']='another'
    if bad=='visible':e[0]['VM_visible_ps']=e[0]['SU_read_ps']
    if bad=='tag':e[0]['observed_Xtag_ps']+=10
    if bad=='CDC':e[0]['positive_CDC_return_ps']=0
    with pytest.raises(ValueError):M.finite_deadline(e,c)

def test_source_mutant_idle_order_rejected():
    import json
    s=(M.OUT/'inputs/core.sv').read_text().replace('qe_idle, su_idle, me_idle','qe_idle, me_idle, su_idle')
    ops=json.loads((M.OUT/'inputs/consumer_source.json').read_text())['accepted_consumer_endpoints']['static_consumers']
    with pytest.raises(ValueError):M.wait_proof(s,ops)


def test_QE_source_role_and_conditional_lower_bound_not_deadline():
    m=M.model()
    assert 'QE LINQ' in m['GU0_source_unit']
    assert m['I66_to_I70_earliest_acceptance_lower_bound_if_all_intermediate_ordinary_engine_dispatch']==24
    assert m['dispatch_lower_bound_is_not_VM_read_deadline_or_service_upper_bound']
    assert m['actual_consumer_deadline'] is None


def test_all12_constructive_laterGU0_fences_and_relative_deadline():
    m=M.model()['constructive_deadline']
    assert len(m['fences'])==12
    assert sorted(set((x['later_GU0'],x['consumer']) for x in m['fences']))==[(69,70),(79,80),(84,85),(89,90),(94,95),(97,98)]
    assert all(x['consumer_front_acceptance_min_edge']=='F+7' for x in m['fences'])
    assert not m['new_SU_admission_guard_not_selected']==False
    assert m['ready_hook_is_new_implementation_not_native_guarantee']
    assert m['absolute_consumer_first_and_last_time_bound'] is None

def test_source_adapter_ready_can_not_substitute_retirement():
    import json
    proof=M.model()['admission_proof'];nodes=json.loads((M.OUT/'inputs/instruction_slice.json').read_text())
    a=(M.OUT/'inputs/rom_adapt.sv').read_text().replace('S_WAIT: if (!s_go && s_idle)','S_WAIT: if (!s_go && s_ready)')
    with pytest.raises(ValueError):M.constructive_fences(proof,nodes,a)
    # Removing finalGU0 fence destroys the selected sufficient construction.
    nodes=[n for n in nodes if n['instruction_index']!=97]
    with pytest.raises(ValueError):M.constructive_fences(proof,nodes,(M.OUT/'inputs/rom_adapt.sv').read_text())


def test_hook_gross_allowedcell_and_clock_cost_not_free():
    m=M.model()['constructive_deadline']['hook_allowedcell_floor']
    assert m['gross_control_bits']==2
    assert m['body_um2']>0
    assert all(x>0 for x in m['SSFF_new_CLK_pin_fF'].values())
    assert m['phase_active_existing_containment_credit']==0
    assert m['not_a_complete_state_area_or_contextual_timing_price']
