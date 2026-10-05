import copy
import hashlib
import json
from pathlib import Path
import pytest
from tools.w17_D1_reset_qualified_fixture import (
    copy_sv,copy_cpp,cpp_operations,inverse,edge_model,verify_healthy_accepts,once,OLD_CPP_SHA,
)
from tools.w17_D1_reset_fault_attribution import priming_timeline,verify_pins
ROOT=Path(__file__).resolve().parents[1]
E=ROOT/'results/uarch/w17_D1_reset_qualified_fixture_20261002'
N=ROOT/'rtl/test/w17_D1_reset_qualified_fixture'
OLD=ROOT/'results/uarch/w17_D1_disjoint_native_actual_runtime_20261002_r1/inputs/tb_D1_scope_core.sv'


def test_sv_copy_inverse_preserves_every_original_nonrepair_byte():
    candidate,operations=copy_sv(OLD.read_text())
    assert candidate==(N/'tb_D1_scope_core.sv').read_text()
    assert inverse(candidate,operations)==OLD.read_text()
    assert 'do @(negedge clk); while(probe.dut.rn !== 1\'b1);' in candidate
    assert 'while(probe.dut.rn !== 1\'b1 || window_prime_ready !== 1\'b1)' in candidate
    assert "#0.001; // Inspect committed row state" in candidate
    assert 'row_valid[row]' in candidate and 'row_tag[row]' in candidate


def test_native_copy_inverse_and_engine_prefix_suffix_unchanged():
    candidate=(N/'Vtb_D1_scope_core___024root__0.cpp').read_text()
    original=inverse(candidate,cpp_operations())
    assert hashlib.sha256(original.encode()).hexdigest()==OLD_CPP_SHA
    regenerated,operations,info=copy_cpp(original)
    assert regenerated==candidate
    assert inverse(candidate,operations)==original
    record=json.loads((E/'inverse.json').read_text())
    for key,value in info.items():assert record[key]==value
    assert record['CPP_inverse_exact'] and record['SV_inverse_exact']


def test_modified_engine_source_is_not_eligible_for_reuse():
    original=inverse((N/'Vtb_D1_scope_core___024root__0.cpp').read_text(),cpp_operations())
    with pytest.raises(ValueError,match='hash mismatch'):copy_cpp(original+'\n')


def test_transform_rejects_missing_or_duplicate_spans():
    with pytest.raises(ValueError):once('two two','two','new')
    with pytest.raises(ValueError):once('absent','old','new')


def test_healthy_reset_model_first_and_all128_exact_edges():
    model=edge_model()
    assert model==json.loads((E/'edge_model.json').read_text())
    assert model['reset_wait_samples']==[{'time_ps':5000,'rn':0},{'time_ps':6000,'rn':1}]
    assert model['accepts'][0]['sample_ps']==7500
    assert model['accepts'][-1]['sample_ps']==134500
    assert model['start_ps']==135000
    assert model['fixture_shift_cycles']==2
    assert verify_healthy_accepts(model['accepts'])==json.loads((E/'healthy_model_control.json').read_text())
    actual_old=priming_timeline()
    assert actual_old['lost_rows']==[0]
    healthy=priming_timeline(2)
    assert healthy['lost_rows']==[]
    assert [v['sample_ps'] for v in model['accepts']]==[v['time_ps'] for v in healthy['handshakes']]


@pytest.mark.parametrize('row,key,value',[
 (0,'rn',0),(0,'sample_ps',5500),(0,'valid',0),(0,'active',0),(0,'blocks',0),
 (1,'row',0),(1,'tag',0),(127,'user',1),(127,'commit_check_ps',134500)])
def test_old_early_handshake_wrong_identity_and_NBA_controls_rejected(row,key,value):
    events=copy.deepcopy(edge_model()['accepts']);events[row][key]=value
    with pytest.raises(ValueError):verify_healthy_accepts(events)


def test_missing_duplicated_reordered_accepts_rejected():
    events=edge_model()['accepts']
    for wrong in (events[1:],events+[events[-1]],events[:1]+events[:1]+events[2:],list(reversed(events))):
        with pytest.raises(ValueError):verify_healthy_accepts(wrong)


def test_plan_one_object_only_and_no_restrictive_caps():
    plan=json.loads((E/'incremental_plan.json').read_text())
    assert plan['reuse']['required_objects']==3829
    assert plan['reuse']['reused_objects']==3828
    assert plan['reuse']['only_replace']=='Vtb_D1_scope_core___024root__0.o'
    assert plan['commands']['no_make_or_frontend']
    assert plan['commands']['compile'][0]=='/usr/bin/g++-11'
    assert plan['commands']['compile'][-4:]==['-o','FRESH_OUT/Vtb_D1_scope_core___024root__0.o','-MF','FRESH_OUT/Vtb_D1_scope_core___024root__0.d']
    for key in ('wall_limit','CPU_limit','AS_limit','FS_limit','MemoryMax'):
        assert plan['capacity_proposal'][key] is None
    assert not plan['scope']['actual_fixture_PASS']
    assert plan['scope']['service_bound']=='BOUND_MISSING'
    assert plan['model']['existing_prefix_cycle_stop']==512
    objects=json.loads((E/'ordered_original_objects.json').read_text())
    assert len(objects)==3829 and len({x['target'] for x in objects})==3829
    assert sum(x['target']==plan['reuse']['only_replace'] for x in objects)==1


def test_source_and_candidate_hash_records():
    pins=json.loads((E/'source_pins.json').read_text())
    verify_pins(ROOT,pins['protected_sources'])
    for item in pins['evidence'].values():
        path=Path(item['path'])
        if path.is_absolute():path=ROOT/path.relative_to(ROOT)
        verify_pins(path.parent,{path.name:item['SHA256']})
    verify_pins(E,json.loads((E/'artifact_SHA256.json').read_text()))


@pytest.mark.parametrize('bad',[True,1.0,None])
def test_noninteger_commit_fields_rejected(bad):
    events=copy.deepcopy(edge_model()['accepts']);events[0]['rn']=bad
    with pytest.raises(ValueError):verify_healthy_accepts(events)


def test_final_all128_guard_is_present_before_start():
    sv=(N/'tb_D1_scope_core.sv').read_text()
    cpp=(N/'Vtb_D1_scope_core___024root__0.cpp').read_text()
    assert sv.index('D1_PRIME_SET_INCOMPLETE')<sv.index('  start=1;')
    assert cpp.index('D1_PRIME_SET_INCOMPLETE')<cpp.index('vlSelfRef.tb_D1_scope_core__DOT__start = 1U;')
    assert 'D1_ALL128_PRIMED' in sv and 'D1_ALL128_PRIMED' in cpp
    assert edge_model()['all128_commit_witness_ps']==134501


def test_native_coroutine_lexical_balance():
    import re
    cpp=(N/'Vtb_D1_scope_core___024root__0.cpp').read_text()
    first=cpp.index('VlCoroutine Vtb_D1_scope_core___024root___eval_initial__TOP__Vtiming__0(Vtb_D1_scope_core___024root* vlSelf) {')
    last=cpp.index('VlCoroutine Vtb_D1_scope_core___024root___eval_initial__TOP__Vtiming__1(Vtb_D1_scope_core___024root* vlSelf) {',first)
    body=re.sub(r'"(?:[^"\\]|\\.)*"|//[^\n]*','',cpp[first:last])
    pairs={')':'(',']':'[','}':'{'};stack=[]
    for char in body:
        if char in '([{':stack.append(char)
        elif char in pairs:assert stack.pop()==pairs[char]
    assert not stack


def test_unpinned_sv_geometry_or_source_change_rejected():
    with pytest.raises(ValueError,match='hash mismatch'):
        copy_sv(OLD.read_text().replace('.SUN(256)','.SUN(64)'))
