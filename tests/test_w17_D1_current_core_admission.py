import copy
import importlib.util
import json
from pathlib import Path
import pytest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('admission',ROOT/'tools/w17_D1_current_core_admission.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
E=ROOT/m.EVIDENCE
PLAN=json.loads((E/'plan.json').read_text())


def test_portable_source_admission():
    r=m.verify(ROOT)
    assert r['source_files']==129
    assert r['ordinary_owner_gaps']==0
    assert not r['elaborated'] and not r['compiled'] and not r['runtime_admitted']


@pytest.mark.parametrize('invalid',[-1,True,False,1.0,'900',2**64,None])
def test_bad_time_envelope_rejected(invalid):
    p=copy.deepcopy(PLAN);p['caps']['frontend_seconds']=invalid
    with pytest.raises(ValueError):m.validate_plan(p)


@pytest.mark.parametrize('field', ['aggregate_memory_bytes','CXX_AS_bytes','runtime_AS_bytes',
                                  'frontend_seconds','runtime_seconds','compile_threads',
                                  'output_bytes','file_bytes','log_bytes','pids_max'])
def test_cap_lift_rejected(field):
    p=copy.deepcopy(PLAN);p['caps'][field]+=1
    with pytest.raises(ValueError):m.validate_plan(p)


@pytest.mark.parametrize('field,value',[('SUN',128),('K_MEM',264320),('WIN_STACK',2),
                                      ('CL_DEPTH',256),('ROM_PHW',5),('MEM_MODE',1)])
def test_fixture_geometry_cannot_replace_actual_geometry(field,value):
    p=copy.deepcopy(PLAN);p['source_geometry'][field]=value
    with pytest.raises(ValueError,match='geometry'):m.validate_plan(p)


def test_old_attention_archive_not_admitted():
    p=copy.deepcopy(PLAN);p['historical_attention_reused']=True
    with pytest.raises(ValueError,match='source admission'):m.validate_plan(p)


def test_busy_or_predicted_calendar_cannot_be_service_bound():
    p=copy.deepcopy(PLAN);p['model_limits']['causal_service_bound']='136800'
    with pytest.raises(ValueError,match='deadline'):m.validate_plan(p)


@pytest.mark.parametrize('field', ['waited','q_gate','m0_gate','me_ready','kv_ok','not_kvd_v','win_idle'])
def test_dropping_real_admission_guard_has_counterexample(field):
    values={k:True for k in ['waited','q_gate','m0_gate','me_ready','kv_ok','not_kvd_v','win_idle']}
    values[field]=False
    assert not m.admission_predicate(values)
    assert m.admission_predicate(values,drop=field)


def test_new_cpu_masks_need_new_review():
    p=copy.deepcopy(PLAN);p['caps']['frontend_affinity']=[0,1]
    with pytest.raises(ValueError,match='CPU mask'):m.validate_plan(p)


def test_native_event_phase_mutation_rejected():
    text=(ROOT/m.BENCH/'native_main.cpp').read_text()
    m.validate_native_order(text)
    text=text.replace('top->eval();++evals;', 'ctx->time(top->nextTimeSlot());top->eval();++evals;')
    with pytest.raises(ValueError,match='event phase'):m.validate_native_order(text)


def test_inverse_and_nonobservational_mutation():
    text=(ROOT/m.BENCH/'ot_v41_rt_die_D1_current.sv').read_text()
    original=(E/'source_authority/rtl/test/v41_runtime/ot_v41_rt_die.sv').read_text()
    assert m.inverse_wrapper(text)==original
    assert m.inverse_wrapper(text.replace('.X_ATT(1)', '.X_ATT(0)'))!=original
    block=text.split('// D1_CURRENT_OBSERVATION_BEGIN')[1].split('// D1_CURRENT_OBSERVATION_END')[0]
    assert 'force ' not in block
    assert not __import__('re').search(r'dut\.[\w.\[\]:+]+\s*(?:<=|=(?!=))',block)


def test_owner_gap_and_parameter_traps_are_distinct():
    inventory=json.loads((E/'module_owner_inventory.json').read_text())
    assert set(inventory['unresolved_potential_references'])==m.GUARDS
    assert not m.ordinary_owner_gaps(inventory)
    inventory['unresolved_potential_references'].append('ot_real_missing_owner')
    assert m.ordinary_owner_gaps(inventory)=={'ot_real_missing_owner'}


def test_no_12300_idle_prefix_or_unbounded_cycle_wait():
    text=(ROOT/m.BENCH/'tb_D1_current_core.sv').read_text()
    assert 'while(diag_cycle<12294)' not in text
    assert 'diag_cycle>=512' in text
    assert '.kv_ready(kv_ready)' in text
    assert '.att_from(att_from)' in text
    assert '.PHYS(0)' in text


def test_sticky_fault_precedes_witness():
    text=(ROOT/m.BENCH/'ot_v41_rt_die_D1_current.sv').read_text()
    assert text.index('$fatal(1,"D1_SOURCE_OR_LEDGER_FAULT")') < text.index('if(target_seen && returns>=1')
    assert '.accept(dut.w_v[0] && dut.w_rdy[0])' in text
    assert '.response(dut.w_sv[0] && dut.w_srdy[0])' in text


def test_only_synthetic_program_not_original_payload():
    x=json.loads((E/'synthetic_input_contract.json').read_text())
    d=x['decoded_full_shape_fields'][0]
    assert (d['UNIT'],d['WAIT'],d['ME_K'],d['ME_NOUT'],d['ME_TILES'])==(1,2,512,128,4)
    assert d['ME_MMODE']==1 and d['ME_WSRC']==1
    assert x['only_input_file']=='prog.hex'
    assert not x['external_payload_loaded'] and not x['original_program_replay']


def test_source_state_memory_is_not_reduced_fixture():
    x=json.loads((E/'resource_model.json').read_text())
    assert x['source_state_lower_bound']['K_backing_arrays_bytes']==2*1024**3
    assert not x['fit_claim']
    assert x['service_deadline']=='BOUND_MISSING'


def test_frontend_does_not_launch_native_build():
    p=copy.deepcopy(PLAN);p['commands']['frontend'].append('--build')
    with pytest.raises(ValueError,match='child compile'):m.validate_plan(p)
