import sys
from pathlib import Path
import numpy as np
import pytest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
import h3_deepseek_streaming_linear as S
import h3_deepseek_complete_native as N

@pytest.mark.parametrize('fmt',['fp8','fp4'])
@pytest.mark.parametrize('k',[32,64,288,512])
def test_streaming_linear_fullK_tree_matches_materialized_native(fmt,k):
    rng=np.random.default_rng(752);rows=3;x=rng.normal(0,.15,k).astype(np.float32)
    codes=rng.integers(0,126,(rows,k if fmt=='fp8' else k//2),dtype=np.uint32);scales=rng.integers(122,126,(rows,k//32),dtype=np.uint32)
    if fmt=='fp4':codes=rng.integers(0,255,(rows,k//2),dtype=np.uint32)
    p=N.recipe('linear_q',{'n':rows,'rows':rows,'k':k},{'fmt':fmt});expected=N.Machine(p,{'x':x,'weight_codes':codes,'weight_scale_codes':scales},N.primitive_div).run()['out']
    got,r=S.StreamingLinear((0,'x_v0',0,0,2)).run(x,codes,scales,fmt)
    assert np.array_equal(got.view(np.uint32),expected.view(np.uint32));assert r['recomputed_dependency_scalars']==0
    assert r['kernel_calls']['quantize32']==k//32
    assert r['provider']['outstanding']==0;assert not r['physical_visibility_qualified']
    for op,count in r['executed_primitive_scalars'].items():assert count==r['plan']['opcode_scalar_evaluations'][op]


def test_fullshape_polynomial_projection_and_typed_live_range():
    for rows,k in [(5120,5120),(129280,5120),(2304,5120),(5120,2304)]:
        p=S.model(rows,k);assert p['typed_live_workspace_upper_bytes_per_SM']<1048576
        assert p['integer_products']==rows*k;assert p['weight_decode_rows_blocks']==rows*(k//32)
        assert p['input_quantization_calls']==k//32;assert p['cross_row_requantization']==0
        assert p['latency_cycles'] is None;assert not p['hardware_admitted']


def test_streaming_source_poison_rejection():
    x=np.ones(32,np.float32);codes=np.ones((1,32),np.uint32);codes[0,0]=127
    with pytest.raises(ValueError,match='finite weight'):S.StreamingLinear((0,'v',0,0,0)).run(x,codes,np.ones((1,1),np.uint32)*127)

@pytest.mark.parametrize('rows',[2,9,17])
def test_index_scan_independent_rows_fullK_and_global_ID_order(rows):
    import importlib.util
    spec=importlib.util.spec_from_file_location('fixture',ROOT/'tests/test_h3_deepseek_complete_native.py');F=importlib.util.module_from_spec(spec);spec.loader.exec_module(F)
    p=N.recipe('index_scores',{'heads':4,'width':32,'rows':rows},{'rank':7});m=F.fixture(p);expected=N.Machine(p,m,N.primitive_div).run()
    got,r=S.StreamingIndex((1,'iqf_v0',7,0,8)).run_index(m,7)
    for key in expected:assert np.array_equal(got[key].view(np.uint8),expected[key].view(np.uint8))
    assert r['executed_primitive_scalars']==r['plan']['opcode_scalar_evaluations'];assert r['recomputed_dependency_scalars']==0
    assert r['provider']['outstanding']==0


def test_full_index_rows_projection_is_polynomial_and_resident_bounded():
    m=S.index_model(32768,64,128);assert m['typed_live_workspace_upper_bytes_per_SM']<1048576
    assert m['integer_products']==32768*64*128;assert m['query_decode_repeats_explicit']==1

@pytest.mark.parametrize('family',['mv','linear_bf16','wo_a_part'])
@pytest.mark.parametrize('k',[3,8,40,65])
def test_float_fullK_chunk_tree_and_unrounded_output_preserved(family,k):
    rng=np.random.default_rng(73);x=rng.normal(0,.1,k).astype(np.float32);w=rng.normal(0,.2,(3,k)).astype(np.float32)
    p=N.recipe(family,{'rows':3,'k':k},{});expected=N.Machine(p,{'x':x,'weight':w},N.primitive_div).run()['out']
    got,r=S.StreamingFloat((0,'x_v0',0,0,2)).run_float(x,w,family=='linear_bf16')
    assert np.array_equal(got.view(np.uint32),expected.view(np.uint32));assert r['executed_primitive_scalars']==r['plan']['opcode_scalar_evaluations']
    if family!='linear_bf16':assert np.any(got.view(np.uint32)&0xffff)


def test_gather_columns_preserve_provider_order_leases_and_bits():
    ranks,n=4,259;mask=np.zeros((ranks,n),np.uint32)
    for j in range(n):mask[j%ranks,j]=1
    parts=np.arange(ranks*n,dtype=np.float32).reshape(ranks,n);p=N.recipe('all_gather',{'n':n,'ranks':ranks},{})
    expected=N.Machine(p,{'parts':parts,'ownership_mask':mask},N.primitive_div).run()['out']
    got,r=S.StreamingGather((0,'p_v0',0,0,0)).run_gather(parts,mask);assert np.array_equal(got.view(np.uint32),expected.view(np.uint32))
    assert r['executed_primitive_scalars']==r['plan']['opcode_scalar_evaluations'];assert r['provider']['outstanding']==0
    mask[0,0]=2
    with pytest.raises(ValueError,match='one-bit'):S.StreamingGather((0,'v',0,0,0)).run_gather(parts,mask)
