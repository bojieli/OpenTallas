import copy
import sys
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import hdc_golden as G
from qwen_hbm_complete_isa import ARITY,evaluate,manifest,recipe,striped_lines

def equal(actual,expected):assert np.array_equal(np.asarray(actual,np.float32).view(np.uint32),np.asarray(expected,np.float32).view(np.uint32))

def test_exp_recip_rsqrt_ordinary_instruction_sequences_bit_exact():
    rng=np.random.default_rng(45)
    values=np.concatenate([np.linspace(-100,100,301,dtype=np.float32),rng.normal(0,20,500).astype(np.float32)])
    equal(evaluate(recipe('EXP'),a=values),G.exp(values))
    positive=np.concatenate([np.exp(rng.uniform(-20,80,500)).astype(np.float32),np.array([1,1.6158e38,2e38,3e38],np.float32)])
    equal(evaluate(recipe('RECIP'),a=positive),G.reciprocal(positive))
    equal(evaluate(recipe('RSQRT'),a=positive),G.rsqrt(positive))

def test_bf16_ties_and_rounding_boundaries():
    bits=np.random.default_rng(23).integers(0,0x7f7fffff,2000,dtype=np.uint32)
    values=np.concatenate([bits.view(np.float32),np.array([-0.,0.,1.00390625,1.01171875,-1.00390625],np.float32)])
    equal(evaluate(recipe('BF16'),a=values),G.to_bf16(values))

def test_silu_gate_and_normalize_preserve_separate_rounding_and_saturation():
    rng=np.random.default_rng(69)
    gate=np.concatenate([rng.normal(0,40,500).astype(np.float32),np.array([-100,-88,-87.98,-87,0,88,100],np.float32)])
    up=rng.normal(0,10,len(gate)).astype(np.float32)
    equal(evaluate(recipe('SILU_GATE'),a=gate,b=up),G.mul(G.silu(gate),up))
    denominator=np.exp(rng.uniform(-10,30,len(gate))).astype(np.float32)
    equal(evaluate(recipe('NORMALIZE'),a=up,b=denominator),G.mul(up,G.reciprocal(denominator)))

def test_ordinary_two_source_arity_and_finite_RF_liveness():
    for kind in ('EXP','RECIP','RSQRT','BF16','SILU_GATE','NORMALIZE','FADD','FMUL'):
        p=recipe(kind)
        assert p['peak_live_value_registers_per_lane']+p['address_loop_registers']<=32
        assert all(len(i['src'])==ARITY[i['opcode']]<=2 for i in p['instructions'])
        assert all(i['core_serial_cycles'] is None for i in p['instructions'])
        assert not any(i['opcode'] in ('FMA','EXP','DIV','RECIP','RSQRT') for i in p['instructions'])

def test_injected_seed_fault_fails_numeric_comparison_and_unknown_ops_fail_closed():
    p=copy.deepcopy(recipe('RECIP'));p['constants_U32']['@RECIP_SEED']^=0x400
    with pytest.raises(AssertionError):equal(evaluate(p,a=np.array([1,3,7],np.float32)),G.reciprocal(np.array([1,3,7],np.float32)))
    p=recipe('RSQRT');p['instructions'][0]['opcode']='MAGIC_SFU'
    with pytest.raises(ValueError,match='opcode arity'):evaluate(p,a=np.array([1],np.float32))
    with pytest.raises(ValueError,match='unbound ordinary'):recipe('FP8_CODEC')
    with pytest.raises(ValueError,match='NaN compare'):evaluate(recipe('EXP'),a=np.array([np.nan],np.float32))

def test_full_graph_element_counts_and_missing_calendars_block_physical():
    m=manifest();assert m['instructions']==1737 and not m['physical_build_ready']
    assert not m['full_program_GPU_lowering_qualified'] and m['token_cycles'] is None
    assert {'MATRIX','SCORES','PV','KV_READ','RSTD','EXP_SUM'}<=set(m['incomplete_macro_lowerings'])
    head=next(x for x in m['elementwise_instruction_instances'] if x['outputs']==['head.d1.scaled'])
    assert head['elements_per_participant']==75968 and head['warp32_invocations_per_participant']==2374
    assert head['participants']==[1] and head['placement_and_shared_bank_map'] is None
    assert all(x['issue_writeback_serial_cycles'] is None for x in m['elementwise_instruction_instances'])
    qkv=next(x for x in m['matrix_weight_demand_instances'] if x['weight']=='L0.qkv.d0')
    assert qkv['weight_INT8_bytes']==3072*4096
    assert sum(qkv['unique_code_128B_lines_by_stack'])*128==3072*4096
    assert sum(qkv['candidate_cross_quad_code_line_requests_by_stack'])*4==3*sum(qkv['uncached_per_SM_code_128B_lines_by_stack'])
    assert qkv['callback_timeline'] is None and qkv['request_return_service_fast_cycles'] is None
    assert len(m['matrix_weight_demand_instances'])==290

def test_striped_read_footprint_endpoint_and_per_stack_counts():
    assert striped_lines(0,128)==[1,0,0,0]
    assert striped_lines(127,2)==[1,1,0,0]
    assert striped_lines(128*3,128*6)==[2,1,1,2]
    with pytest.raises(ValueError):striped_lines(0,0)
