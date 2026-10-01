import sys
from pathlib import Path
import copy
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import w19_moe_opcode_proof as P


def recipe():return P.E.moe_recipe(P.E.provider())


def test_existing_typed_interpreter_run_is_reused():
    assert P.MoEVM.run is P.M.Machine.run
    assert P.MoEVM.stored_f32 is P.M.Machine.stored_f32


@pytest.mark.parametrize('rank',[0,1,53,54,95])
def test_actual53_54_rank_slices_original_reference(rank):
    _,slots=next(P.inputs());y,vm,r=P.run_rank(recipe(),slots,rank)
    assert len(y)==P.I.even(5120)[rank][1]-P.I.even(5120)[rank][0]
    assert r['rows'] in [53,54]
    assert len([t for t in vm.trace if t['op']=='FADD'])==7
    assert vm.admission['warps']==2


def test_disjoint_complete5120_ownership():
    spans=P.I.even(5120)
    assert spans[0][0]==0 and spans[-1][1]==5120
    assert all(spans[i][1]==spans[i+1][0] for i in range(95))
    assert sum(b-a for a,b in spans)==5120


def test_slot_order_mutant_fails():
    _,slots=list(P.inputs())[1];p=recipe()
    p[3]['attributes']['source'],p[6]['attributes']['source']=p[6]['attributes']['source'],p[3]['attributes']['source']
    with pytest.raises(AssertionError,match='boundary'):P.run_rank(p,slots,0)


def test_missing_zero_first_add_fails_even_if_late_zero_canonicalizes():
    _,slots=list(P.inputs())[5];p=recipe();p[1]['dst']='acc';del p[2]
    with pytest.raises(AssertionError,match='seven FADD'):P.run_rank(p,slots,0)


def test_rounding_and_shared_slot_controls():
    cases=list(P.inputs())
    for i,expectedbits in [(2,0x3F800000),(3,0x3F820000),(5,0),(6,0x3F800000),(7,0x00070000)]:
        y,_,_=P.run_rank(recipe(),cases[i][1],0)
        assert np.all(y.view(np.uint32)==expectedbits)
    slots=cases[4][1];y,_,_=P.run_rank(recipe(),slots,0)
    early=np.zeros(5120,np.float32)
    for e in range(7):early=P.G.to_bf16(P.G.add(early,slots[e]))
    assert np.any(y.view(np.uint32)!=early[:len(y)].view(np.uint32))


def test_unknown_source_and_RF_budget_rejected():
    p=recipe();p[2]['src'][0]='@UNKNOWN'
    with pytest.raises(ValueError):P.MoEVM(p,{})
    with pytest.raises(ValueError,match='RF'):P.MoEVM(recipe(),{},rf_budget=8)
