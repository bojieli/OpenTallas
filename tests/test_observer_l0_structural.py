"""Actual lint failure remains authority. No compiler invocation in these tests."""
import hashlib,json,subprocess,sys
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import prepare_observer_l0_structural as prepare
import observer_l0_unavailable_api as api
import simulation_observation_api as base
import run_observer_capped_lint as runner
import prepare_simulation_observation_wrapper as packet
import prepare_observer_lint_gate as previous
OUT=ROOT/prepare.OUT
PLAN=json.loads((OUT/'plan.json').read_bytes())


def test_exact_source_inverse_and_generation():
    original=packet.original(ROOT)
    text=(ROOT/prepare.COPY).read_text()
    assert text==prepare.render(original)
    assert prepare.inverse(text)==original
    assert hashlib.sha256(original.encode()).hexdigest()=='43803b86e4bbdf5cbd68fb682a19611156d8595b7c9c71afd83f0898e9bf8d65'
    assert 'parameter bit SIM_OBS_ENABLE = 0' in text
    assert '.FULL_SHAPE(1)' in text
    assert '.WINDOW_HBM_ATTENTION(1)' in text


def test_structural_ckv_absence_whole_file_no_constant_guard():
    text=(ROOT/prepare.COPY).read_text()
    prepare.assert_l0_only(text)
    for forbidden in ['g_ckv','u_ckv','SIM_OBS_CKV_SELECTED','.CKV_SELECTED(']:assert forbidden not in text
    assert 'if (SIM_OBS_CKV_SELECTED)' not in text
    assert "ABI padding, no observations" in text


@pytest.mark.parametrize('guard',['0','SIM_OBS_ENABLE && 0'])
def test_reintroduced_reference_rejected_even_disabled(guard):
    text=(ROOT/prepare.COPY).read_text()
    bad=text.replace(prepare.START,prepare.START+f'\ngenerate if ({guard}) begin wire x=dut.g_packed_kv.g_window_hbm_attention.g_ckv.u_ckv.sel_v; end endgenerate')
    with pytest.raises(ValueError,match='non-L0 hierarchy'):prepare.assert_l0_only(bad)


def test_unavailable_is_not_a_qualified_zero():
    sample=api.decode_l0(base.encode({'epoch':1,'cycle':0,'rank':0}))
    assert sample.value('ckv_available')==0
    assert sample.value('window_rsp_take')==0
    assert sample.available_groups==frozenset({'common','WINDOW'})
    for field in api.CKV_FIELDS:
        assert sample.value(field) is None
        with pytest.raises(ValueError,match='unavailable'):sample.qualified_value(field)
    assert sample.qualified_value('window_rsp_take')==0


@pytest.mark.parametrize('field',sorted(api.CKV_FIELDS))
def test_reserved_ckv_slot_injection_rejected_before_mutation(field):
    state=base.State();before=repr(state)
    with pytest.raises(ValueError,match='forbidden CKV'):api.observe_l0(state,base.encode({field:1}))
    assert repr(state)==before


def test_ckv_availability_bit_rejected_for_l0():
    with pytest.raises(ValueError):api.decode_l0(base.encode({'ckv_available':1}))


def test_wrong_domain_ledger_rejected_before_mutation():
    state,_=base.observe(base.State(),base.encode({'epoch':1,'rank':0,'cycle':0,'ckv_available':1,'ckv_select_accept':1}))
    before=repr(state)
    with pytest.raises(ValueError,match='CKV ledger'):api.observe_l0(state,base.encode({'epoch':1,'rank':0,'cycle':1}))
    assert repr(state)==before


def test_valid_window_identity_and_reply_unavailable_domain():
    def frame(cycle,**values):return base.encode(dict(epoch=9,rank=0,cycle=cycle,**values))
    state,events,sample=api.observe_l0(base.State(),frame(0,source_accept=1,source_gen=7))
    operation=state.source
    state,_,_=api.observe_l0(state,frame(1,window_prefetch_accept=1,window_prefetch_row=127,window_prefetch_user=2))
    state,events,_=api.observe_l0(state,frame(2,window_state=5,window_req_offer=1,window_req_ready=1,window_req_take=1,window_row=127,window_active_user=2))
    assert len(events)==1 and events[0].kind=='request'
    state,events,sample=api.observe_l0(state,frame(3,window_state=6,window_rsp_take=1,window_reply_ok=1,window_row=127,window_active_user=2))
    assert len(events)==1 and events[0].kind=='reply'
    assert state.source==operation and not any(e.causal_certificate for e in events)
    assert all(sample.value(field) is None for field in api.CKV_FIELDS)


def test_shared_layout_preserved_exactly():
    assert packet.BITS==PLAN['structural_correction']['packet_bits']==1020
    assert PLAN['structural_correction']['simulation_register_bits']==1085
    fields=packet.layout();first=min(f['offset'] for f in fields if f['ckv'])
    text=(ROOT/prepare.COPY).read_text()
    assert f"assign sim_obs_raw[{first} +: {packet.BITS-first}] = '0;" in text
    availability=next(f for f in fields if f['name']=='ckv_available')
    assert f"assign sim_obs_raw[{availability['offset']} +: 1] = 1'b0;" in text


def test_new_plan_valid_but_old_go_cannot_authorize():
    runner.validate_plan(PLAN)
    with pytest.raises(ValueError):runner.require_go((OUT/'plan.json').read_bytes(),json.loads((ROOT/'results/rtl/parent_observer_lint_GO_20261002/GO.json').read_bytes()))
    template=json.loads((OUT/'GO.template.json').read_bytes())
    assert template['decision']=='PENDING'
    assert template['plan_sha256']==hashlib.sha256((OUT/'plan.json').read_bytes()).hexdigest()


def test_ckv_mode_exactly_preserved_separate_real_l20():
    old=json.loads((ROOT/previous.OUT/'plan.json').read_bytes())
    assert PLAN['modes'][1]==old['modes'][1]
    assert PLAN['modes'][1]['copy']==previous.CKV_COPY
    for name,val in dict(X_IDX=2,X_SEL=1,IDX_RING=1,SUN=256,SUM=64,CL_DEPTH=512,ROM_PHW=6).items():assert PLAN['modes'][1]['parameters'][name]==val


def test_real_l0_ancestors_and_params_preserved():
    mode=PLAN['modes'][0]
    assert prepare.COPY in mode['source_sha256']
    assert mode['top']==prepare.TOP
    assert 'SIM_OBS_CKV_SELECTED' not in mode['parameters']
    assert not any('SIM_OBS_CKV_SELECTED' in arg for arg in mode['argv'])
    for name,val in dict(SUN=256,SUM=64,CL_DEPTH=512,ROM_PHW=6).items():assert mode['parameters'][name]==val
    assert not mode['closure']['ambiguous']
    assert set(mode['closure']['unresolved'])==previous.GUARDS
    assert 'rtl/w17_runtime/chip/ot_chip_v41x_die.sv' in mode['closure']['files']
    for path,sha in mode['source_sha256'].items():
        data=(ROOT/path).read_bytes() if path==prepare.COPY else prepare.old.blob(ROOT,path)
        assert hashlib.sha256(data).hexdigest()==sha


def test_failed_copy_and_receipt_byte_identical():
    paths=['rtl/test/v41_runtime/ot_v41_rt_die_sim_observe_l0.sv','rtl/test/v41_runtime/ot_v41_rt_die_sim_observe.sv',previous.CKV_COPY]
    paths += [str(p.relative_to(ROOT)) for p in (ROOT/'results/rtl/observer_lint_execution_4fed19018_20261002').iterdir()]
    for path in paths:
        original=subprocess.check_output(['git','show','277d7f2c167b279a23ab2a50f3b60cb473cc3a69:'+path],cwd=ROOT)
        assert (ROOT/path).read_bytes()==original
    assert PLAN['actual_failure']['verdict']=='FAIL_RETAINED'
    assert 'NOT_LINTED' in PLAN['qualification']


def test_producer_engine_instance_binding_unchanged():
    original=packet.original(ROOT)
    text=prepare.inverse((ROOT/prepare.COPY).read_text())
    start=original.index('    ot_chip_v41x_die #(')
    end=original.index(');',start)+2
    assert text[start:end]==original[start:end]


def test_mutants_remain_finite_no_execution():
    for mode in PLAN['modes']:
        source=(ROOT/mode['copy']).read_text()
        for mutant in mode['mutants']:
            assert mutant['timeout_seconds']==30
            assert source.count(mutant['find'])==1
    assert PLAN['caps']['mode_wall_seconds']==60 and PLAN['caps']['memory_bytes']==4*1024**3
