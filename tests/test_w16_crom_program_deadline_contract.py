"""Synthetic single-PC event harness; source census uses actual full program."""
import copy
import pytest
from tools import w16_crom_program_deadline_contract as C

@pytest.fixture(scope='module')
def contract():return C.build()

def harness(contract):
 c=copy.deepcopy(contract);row=copy.deepcopy(c['program'][6]);row['encoded_wait_predecessor_PCs']=[];c['program']=[row]
 coeff=row['coefficient'];base=coeff['credit_scenarios']['128'];fill=base['cold_fill_valid_and_reverse_credit_ticks'];issue=fill+coeff['consumer_local_read_ticks']
 p=dict(time_basis='hardware_model_3p6GHz_ticks',scope='CONDITIONAL_SOURCE_BOUND_MODEL',program_sha256=c['encoded_program_sha256'],
  placement_basis='PINNED_FULLRANK45_BANK_LEDGER',relocation_source_pin=None,
  ledger_sha256=c['ledger_pin']['sha256'],cost_source_pins=[c['ledger_pin']],rank=0,epoch=7,credits=128,
  events=[dict(PC=6,instruction_sha256=row['instruction_sha256'],executed=True,predicate_resolution_source='synthetic single-PC unit-test only',issue_tick=issue,retire_tick=issue+4,operator_ticks=4,
   coefficient=dict(service_release_tick=0,fill_valid_tick=fill,reverse_credit_tick=fill,emit_local_arrival_tick=issue,lease_release_tick=issue+4,
    critical_delta_ticks={k:0 for k in C.EXTRA_COSTS},runtime_context=dict(rank=0,image_sha256=c['rank_bindings'][0]['CROM_image_sha256'],layer=row['layer'],PC=6,epoch=7,burst_count=coeff['burst_count'])))])
 return c,p

def test_actual4778PC491coefficient_and_wait_dependencies(contract):
 assert len(contract['program'])==4778 and contract['coefficient_PC_count']==491
 assert contract['cold_gamma_PC_count']==81 and contract['canonical_serialized_destination_uses']==549760
 assert sum('coefficient' in r for r in contract['program'])==491
 assert any(r['encoded_wait_predecessor_PCs'] for r in contract['program'])
 assert not contract['absolute_PC_deadlines_bound'] and not contract['hardware_admission']

def test_synthetic_single_PC_can_discharge_explicit_bounds(contract):
 c,p=harness(contract);r=C.validate_events(c,p)
 assert r['source_bound_scenario_only'] and not r['physical_admission']

@pytest.mark.parametrize('mutation',['ordinal','missing_operator','early_fill','early_issue','lease_before_use','unknown_CDC','wrong_image','stale_PC','stage_transfer'])
def test_refuses_free_or_unmatched_critical_costs(contract,mutation):
 c,p=harness(contract);e=p['events'][0]
 if mutation=='ordinal':p['time_basis']='CPU_instruction_ordinal'
 elif mutation=='missing_operator':e['operator_ticks']=0
 elif mutation=='early_fill':e['coefficient']['fill_valid_tick']-=1
 elif mutation=='early_issue':e['issue_tick']-=1
 elif mutation=='lease_before_use':e['coefficient']['lease_release_tick']-=1
 elif mutation=='unknown_CDC':e['coefficient']['critical_delta_ticks']['actual_CDC_delta']=None
 elif mutation=='wrong_image':e['coefficient']['runtime_context']['image_sha256']='0'*64
 elif mutation=='stage_transfer':p['placement_basis']='STAGE_LOCAL_SMALLER_BANKS'
 else:e['instruction_sha256']='0'*64
 with pytest.raises(ValueError):C.validate_events(c,p)

def test_full_program_provider_cannot_omit_otherPCs(contract):
 _,p=harness(contract)
 with pytest.raises(ValueError,match='all4778PC'):C.validate_events(contract,p)
