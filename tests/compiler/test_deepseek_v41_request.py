from types import SimpleNamespace
import pytest
from compiler.ir.v3.kernel_ir import KernelGraph, RuntimeSymbol, Symbolic, Tensor, StateResource, Entrypoint
from compiler.frontends.v3.deepseek_v41_request import specialize_request
from compiler.backends.hbm_sram.plan import matrix_shape, PlanError
from compiler.backends.hbm_sram.request_plan import build_request_plan


def graph(n=262144):
    return KernelGraph('ds', {}, (RuntimeSymbol('span_tokens',1,n), RuntimeSymbol('context_length',1,n)),
        (Tensor('score','bf16',(Symbolic('span_tokens',1,n),Symbolic('context_length',1,n)),'activation'),),
        (StateResource('candidate_pool_mask.main.layer.20','scratch','u8',n,n),
         StateResource('kv','kv_cache','bf16',512,n)), (),
        (Entrypoint('decode',(),(),()), Entrypoint('prefill',(),(),())))


def test_decode_linear_score_and_persistent_mask():
    old = graph(); before=old.to_dict()
    new=specialize_request(old,phase='decode')
    assert matrix_shape(new.tensors[0],1)[:2] == (1,262144)
    assert new.states[0].capacity_rows == 1
    assert new.states[0].state_class == 'scratch'
    assert new.states[0].initialization == 'zero'
    assert new.states[1] == old.states[1]
    assert old.to_dict() == before
    assert [e.phase for e in new.entrypoints] == ['decode']


def test_prefill_bounded_and_generic_unchanged():
    old=graph(); new=specialize_request(old,phase='prefill',prefill_chunk_tokens=32)
    assert matrix_shape(new.tensors[0],32)[:2] == (32,262144)
    assert matrix_shape(old.tensors[0],262144)[:2] == (262144,262144)
    assert new.states[0].capacity_rows == 32
    assert new.states[1].capacity_rows == 262144


@pytest.mark.parametrize('phase,size',[('other',None),('decode',32),('prefill',None),('prefill',0),('prefill',262145),('prefill',True)])
def test_invalid_request_refuses(phase,size):
    with pytest.raises(ValueError): specialize_request(graph(),phase=phase,prefill_chunk_tokens=size)


def test_backend_checks_context_not_query_bound():
    new=specialize_request(graph(),phase='decode')
    with pytest.raises(PlanError,match='persistent context'):
        build_request_plan(new,SimpleNamespace(limits={'max_context_positions':512}))
    with pytest.raises(PlanError,match='span_override'):
        build_request_plan(new,SimpleNamespace(limits={'max_context_positions':262144}),span_override=1)
