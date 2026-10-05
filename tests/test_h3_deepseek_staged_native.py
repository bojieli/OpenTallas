from pathlib import Path
import sys
import importlib.util
import numpy as np
import pytest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
import h3_deepseek_complete_native as N
import h3_deepseek_staged_native as S
spec=importlib.util.spec_from_file_location('fixtures',ROOT/'tests/test_h3_deepseek_complete_native.py');F=importlib.util.module_from_spec(spec);spec.loader.exec_module(F)

@pytest.mark.parametrize('family',['topk_local','topk_merge','route','cand_local','argmax_local','all_gather','index_q','hc_mixes','linear_q'])
def test_forward_native_stages_match_source_bits_and_have_no_recompute(family):
    p=N.recipe(family,F.TOY,F.ATTR);m=F.fixture(p);expected=N.Machine(p,m,N.primitive_div).run();got,r=S.StagedMachine(p,m,(1,'v0',0,0,5)).run()
    for key in expected:assert np.array_equal(got[key].reshape(-1).view(np.uint8),expected[key].reshape(-1).view(np.uint8))
    assert r['recomputed_dependency_scalars']==0;assert r['workspace_peak_bytes']<=S.CAP
    assert r['provider']['outstanding']==0;assert r['executed_primitive_scalars']==S.plan(p)['scalar_evaluations_by_opcode']


def test_staged_selection_ties_preserve_original_network_and_nan_bits():
    p=N.recipe('topk_merge',{'n':32},{'k':8});m=F.fixture(p);m['scores'][:]=np.resize(np.asarray([0.,-0.,1.,1.,-np.inf],np.float32),32);m['ids'][:]=np.arange(31,-1,-1,dtype=np.int64)
    expected=N.Machine(p,m,N.primitive_div).run();got,r=S.StagedMachine(p,m,(0,'v',0,0,0)).run()
    for key in expected:assert np.array_equal(got[key].reshape(-1).view(np.uint8),expected[key].reshape(-1).view(np.uint8))


def test_lease_no_reuse_until_accepted_credits_drained():
    arena=S.Arena();memory=N.PersistentMemory(credits=1);base=arena.reserve('v0',512);key=('arena',base)
    t=memory.submit(key,write=True,payload=b'x')
    with pytest.raises(RuntimeError):arena.release('v0',memory)
    assert 'v0' in arena.live
    memory.actual_backend_event(t);memory.consume(t);arena.release('v0',memory)
    assert arena.reserve('v1',512)==base
    with pytest.raises(ValueError,match='stale/duplicate'):memory.actual_backend_event(t)
