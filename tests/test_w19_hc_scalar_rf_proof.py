import sys
from pathlib import Path
import copy,json
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import w19_hc_scalar_rf_proof as P


def setup():
    root=Path(__file__).resolve().parents[1]
    p=json.loads(P.blob(root,P.INPUTS));program=P.recipe()
    x=P.G.to_bf16(np.random.default_rng(190037).normal(size=(4,5120)).astype(np.float32))
    vm,_=P.numeric(program,x,1e-20,p)
    code,_=P.D.lower(P.D.address_program(program),p);_,issue=P.D.replay(program,1,p)
    return vm,code,issue,p


def test_actual_core20480_and_RF_assignment():
    vm,code,issue,p=setup();r=P.physical_ownership(code,issue,vm,p)
    assert P.ScalarVM.run is P.M.Machine.run
    assert r['numeric_opcodes']==21 and r['instructions']==27
    assert r['opaque_address_instructions']==6 and r['final_scalar_register']==0
    assert r['one_partition_write_reservations']==27


@pytest.mark.parametrize('mutation',['earlyread','alias','reserved','writecollision','readports','latency','constantprecision'])
def test_RF_ownership_rejects_faults(mutation):
    vm,code,issue,p=setup()
    if mutation=='earlyread':
        issue[7]['cycle']=issue[6]['cycle'];issue[7]['retire']=issue[7]['cycle']+P.D.latency(code[7],p)
    elif mutation=='alias':
        code[16]['physical_src'][0]=2;issue[16]['src'][0]=2
    elif mutation=='reserved':
        code[10]['physical_dst']=28;issue[10]['dst']=28
    elif mutation=='writecollision':
        issue[1]['retire']=issue[0]['retire']
    elif mutation=='readports':
        code[12]['physical_src'].append(1);code[12]['src'].append(code[12]['src'][0]);issue[12]['src'].append(1)
    elif mutation=='latency':issue[7]['retire']+=1
    else:
        code[7]['src'][1]='@F5120';code[7]['physical_src'][1]='@F5120';issue[7]['src'][1]='@F5120'
    with pytest.raises(ValueError):P.physical_ownership(code,issue,vm,p)


def test_wrong5120_denominator_and_missing_Newton_step_fail():
    vm,code,issue,p=setup();program=P.recipe()
    x=np.ones((4,5120),np.float32)
    program[1]['src'][1]='@F5120'
    with pytest.raises(AssertionError):P.numeric(program,x,1e-20,p)
    program=P.recipe()[:-5]
    with pytest.raises(AssertionError):P.numeric(program,x,1e-20,p)


def test_zero_BF16_activation_matches_golden_eps():
    _,_,_,p=setup();vm,total=P.numeric(P.recipe(),np.zeros((4,5120),np.float32),1e-20,p)
    assert total.view(np.uint32)==0
    assert P.M.equal(vm.regs['y'].f32(),np.asarray(P.G.rsqrt(np.float32(1e-20))))


def test_reserved_control_budget_and_RAW_rejected():
    _,_,_,p=setup();program=P.recipe();program[3]['src'][0]='unwritten'
    with pytest.raises(ValueError):P.D.lower(program,p)
    program=P.recipe();program[2]['dst']='@F20480'
    # Typed machine refuses writing an immediate even if logical lowering
    # treats arbitrary SSA names as values.
    with pytest.raises(ValueError):P.ScalarVM(program,np.float32(1),1e-20,p).run()
