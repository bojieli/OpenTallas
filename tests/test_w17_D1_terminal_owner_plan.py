import copy
import json
from pathlib import Path
import pytest
from tools.w17_D1_terminal_owner_plan import verify_schema
from tools.w17_D1_reset_qualified_runtime_verify import verify,verify_priming,verify_bound_execution
ROOT=Path(__file__).resolve().parents[1]
E=ROOT/'results/uarch/w17_D1_terminal_program_binding_model_20261002'
P=ROOT/'results/rtl/w17_D1_reset_qualified_prefix_parent_20261002'

def test_frozen_source_plan_has_terminal_root_abi_hook_and_no_credit():
    plan=json.loads((E/'plan.json').read_text());verify_schema(plan)
    assert len(plan['fields'])==79 and not plan['replay_executed']
    assert plan['capture_hook']['root'].startswith('rdi direct')

@pytest.mark.parametrize('key,value',[('fulltoken',True),('first_return_deadline',512),('no_cap_extension',False),('replay_executed',True)])
def test_plan_credit_or_deadline_mutants_fail(key,value):
    plan=json.loads((E/'plan.json').read_text());plan[key]=value
    with pytest.raises(ValueError):verify_schema(plan)

def test_wrong_argv_cannot_be_admitted():
    plan=json.loads((E/'plan.json').read_text());plan['actual_run_argv_gap']['required_argv'].pop()
    with pytest.raises(ValueError):verify_schema(plan)

def test_parent_actual128proof_and_capremain_separate():
    text=(P/'runtime.log').read_text()
    assert verify_priming(text)['rows']==128
    with pytest.raises(ValueError,match='cycle-cap'):verify(text,0)
    live=json.loads((E/'actual_parent_runtime_argv.json').read_text())
    assert not live['required_argument_present'] and not live['default_program_file_exists']

def test_parent_actual_journal_mutant_loses_row0_witness():
    text=(P/'runtime.log').read_text().replace('time_ps=7501 row=0 rn=1 valid=1','time_ps=7501 row=0 rn=1 valid=0',1)
    with pytest.raises(ValueError):verify_priming(text)

def test_control_masks_not_payload_or_checkpoint_reads():
    plan=json.loads((E/'plan.json').read_text())
    masks=[x for x in plan['fields'].values() if 'control_mask_word' in x]
    assert len(masks)==12 and all(x['bytes']==4 for x in masks)
    assert all(x['type'] in ['CData','SData','IData','QData'] for x in plan['fields'].values())

def test_dependency_model_distinguishes_priming_reply_stage_and_score():
    model=json.loads((E/'first_return_dependency_model.json').read_text())
    assert not model['priming_is_staging'] and model['conditional_full_refill_requests']==128*17
    assert model['first_return_deadline'] is None and not model['I66_origin_edges_used']
    assert 'W_request_accept' in model['first_HBM_return_expression']


def test_cold_due_case_is_source_timing_expression_not_deadline():
    model=json.loads((E/'first_return_dependency_model.json').read_text())
    case=model['conditional_service_case']
    assert sum(case[k] for k in ['REQ_PS','RCDRD_PS','CL_PS','BURST_PS','RSP_PS'])==52899
    assert case['conditional_no_contention_cold_due_delta_ps']==52899
    assert not case['actual_preconditions_observed'] and case['consumer_capture_latency_not_included']
    assert case['not_universal_deadline_or_score_bound'] and model['first_return_deadline'] is None
    assert 'idx_hbm' in model['actual_selected_provider']
