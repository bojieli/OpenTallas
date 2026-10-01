import sys
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from qwen_hbm_complete_program import compile_program
from qwen_hbm_complete_executor import SoftwareGPUProvider,execute,tree,chunk8,bf16,fp8_encode,fp8_decode
from test_qwen_hbm_complete_program import small

def test_entire_graph_two_tokens_produced_activations_and_persistent_KV():
    p=compile_program(small(),context=32,groups=16);provider=SoftwareGPUProvider(p)
    first=execute(p,provider,3,0);second=execute(p,provider,first['next_token'],1)
    assert first['instructions_retired']==second['instructions_retired']==len(p['instructions'])
    assert set(provider.calls)==set(range(len(p['instructions'])))
    assert len(provider.memory.published)==2*2*2
    reads=[e for e in second['memory_events'] if e['event']=='persistent_KV_read' and e['positions']==2]
    assert len(reads)==4
    assert not second['actual_RTL_executed'] and second['token_cycles'] is None
    assert not provider.memory.pending

def test_all_36_layers_plus_head_software_control_execution_reduced_parameters():
    p=compile_program(small(layers=36),context=16,groups=16);provider=SoftwareGPUProvider(p)
    r=execute(p,provider,3,0)
    assert r['instructions_retired']==len(p['instructions'])
    assert len(provider.memory.published)==72
    assert not r['fullshape'] and not r['full_token_RTL']

def test_acceptance_not_publication_and_stale_fence_rejected():
    p=compile_program(small(),context=32,groups=16);provider=SoftwareGPUProvider(p)
    k=np.ones((1,4),np.float32);tag=provider.memory.submit_KV(0,0,0,k,k)
    with pytest.raises(ValueError):provider.memory.read_KV(0,0,0,dict(tag=tag,key=(0,0,0)))
    fence=provider.memory.fence(tag)
    with pytest.raises(ValueError):provider.memory.read_KV(0,0,1,fence)
    with pytest.raises(ValueError):provider.memory.submit_KV(0,0,0,k,k)

def test_missing_previous_token_and_dependency_not_silently_injected():
    p=compile_program(small(),context=32,groups=16);provider=SoftwareGPUProvider(p)
    with pytest.raises(ValueError):execute(p,provider,3,1)
    p['instructions'][0]['dependencies']=[100]
    with pytest.raises(ValueError):execute(p,SoftwareGPUProvider(p),3,0)

def test_rounding_points_fp8_bits_and_chunk8_order():
    values=np.array([0,1,-1,448,-448,.001953125,1000],np.float32)
    assert fp8_encode(values).tolist()==[0,56,184,126,254,1,126]
    assert np.array_equal(fp8_decode(fp8_encode(values)),np.array([0,1,-1,448,-448,.001953125,448],np.float32))
    assert bf16(np.array([1.00390625,1.01171875],np.float32)).tolist()==[1,1.015625]
    v=np.array([1e10,1,-1e10,1,1,1,1,1],np.float32)
    assert chunk8(v)==np.float32(5)

def test_no_per_layer_inputs_accepted_by_executor():
    p=compile_program(small(),context=32,groups=16)
    with pytest.raises(TypeError):execute(p,SoftwareGPUProvider(p),3,0,golden_layer_inputs={})
