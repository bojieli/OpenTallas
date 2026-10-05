"""Bounded full-control and numerical tests; reduced data, full40 topology."""
import copy
from pathlib import Path
import sys
from types import SimpleNamespace
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import w11_dsrom_full_tp_program as F

@pytest.fixture(scope='module')
def program():
    F.G.set_arith('chunk8');F.G.set_fuse('')
    return F.build_program(opt_in=True)

@pytest.mark.parametrize('layer',[0,20])
def test_existing_emission_unchanged(layer):
    assert F.FullLayerBuilder(layer).build_layer()==F.R.build_tp_layer(layer,rope_storage='hbm_cache')


def test_all40_and_head_encode_without_pinned_edits(program):
    assert F.validate_program(program)
    for stage in program['stages']:
        assert stage['scratch_fits_existing_2p19_VM']
        for op in F.FullLayerBuilder(stage['layer']).build_layer():
            word=F.I.encode(full_shape=True,**op)
            assert word<2**2048
    for op in program['head']['instructions']:
        if op['unit']==F.I.UNIT_ME:
            assert op['me_k']==5120 and op['me_nout']==32320 and not op['me_round']

@pytest.mark.parametrize('mutation',['drop','dependency','head','source','layer'])
def test_fail_closed_incomplete_or_wrong_contract(program,mutation):
    p=copy.deepcopy(program)
    if mutation=='drop':p['functional_ops'].pop(20)
    elif mutation=='dependency':p['functional_ops'][20]['depends_on']=[]
    elif mutation=='head':p['head']['dot_input_elements']=1280
    elif mutation=='source':p['stages'][30]['kv_source']=30
    else:p['functional_ops'][20]['layer']=39
    with pytest.raises(ValueError):F.validate_program(p)


def test_ratio2_engram_shared_state_and_fences(program):
    for L in [2,8,14]:
        s=program['stages'][L]
        assert any(a['kind']=='persistent_ratio2_slot' for a in s['runtime_actions'])
        assert any(a['kind']=='completed_group_publication' for a in s['runtime_actions'])
        assert any(c['tag'].endswith('projection_gather') and c['n']==128 for c in s['collectives'])
    for L in [1,14]:
        s=program['stages'][L]
        assert any(c['tag'].endswith('engram.projection_gather') and c['n']==6400 for c in s['collectives'])
        assert next(a for a in s['runtime_actions'] if a['kind']=='engram_checkpoint_codec')['scales_per_row']==8
    for L in [24,28,32,36]:
        assert any(a['kind']=='candidate_mask' for a in program['stages'][L]['runtime_actions'])
    assert program['stages'][19]['kv_source']==14
    assert program['stages'][39]['kv_source']==20 and program['stages'][39]['index_source']==36
    assert not program['complete_encoded_hardware_program_ready']


def test_full5120_head_shards_and_global_ties():
    rng=np.random.default_rng(19)
    w=F.G.to_bf16(rng.normal(size=(12,5120)).astype(np.float32)/16)
    x=F.G.to_bf16(rng.normal(size=5120).astype(np.float32))
    assert np.array_equal(F.tp_head(w,x).view(np.uint32),F.G.mv(w,x).view(np.uint32))
    assert F.lowest_argmax([0,3,3,0,3])==1
    with pytest.raises(ValueError):F.lowest_argmax([1,np.nan])


def tiny_model():
    """No checkpoint/activation fixtures: seeded weights, real golden primitives."""
    g=F.G;rng=np.random.default_rng(20261001);m=g.Model.__new__(g.Model)
    for k,v in dict(L=40,dim=32,hc=4,heads=4,hd=32,rd=4,ih=4,ihd=32,q_rank=32,
                    groups=4,o_rank=32,n_exp=4,k_exp=2,window=2,topk=2,cand_k=2,
                    cand_b=2,cand_src=20,eps=np.float32(1e-20),hc_eps=np.float32(1e-6),
                    route_scale=np.float32(1.5),limit=np.float32(10),sinkhorn_iters=2,
                    attn_scale=np.float32(32**-.5),index_w_scale=np.float32((32*4)**-.5),
                    engram_scale=np.float32(32**-.5),vendor_decode_from=None,dspark_targets=[]).items():setattr(m,k,v)
    m.kv_src=list(F.R.KV_SRC);m.idx_src=list(F.R.IDX_SRC);m.ratio=list(F.R.RATIO)
    m.kv_of={L:max(s for s in m.kv_src if s<=L) for L in range(2,40)}
    m.idx_of={L:max(s for s in m.idx_src if s<=L) for L in range(2,40)}
    m.freqs_plain=np.array([.02,.05],np.float32);m.freqs_yarn=np.array([.01,.03],np.float32)
    m.engram=SimpleNamespace(layer_ids=[1,14],hashes=lambda hist,li:(np.arange(24)+sum(hist)+li)%31)
    m.w={};m.emb_codes={}
    def dense(n,k):return g.to_bf16((rng.normal(size=(n,k))*.02).astype(np.float32))
    def q(n,k):return g.Q8(rng.choice([-2.,-1.,0.,1.,2.],size=(n,k)),np.full((n,k//32),-5,np.int32))
    m.w['embed.weight']=dense(16,32);m.w['head.weight']=dense(12,32);m.w['norm.weight']=np.ones(32,np.float32)
    for L in range(40):
        p=f'layers.{L}.'
        for wh in ['attn','ffn']:
            m.w[p+f'hc_{wh}_fn']=dense(24,128)
            m.w[p+f'hc_{wh}_scale']=np.ones(3,np.float32)*.1
            m.w[p+f'hc_{wh}_base']=np.zeros(24,np.float32)
            m.w[p+f'{wh}_norm.weight']=np.ones(32,np.float32)
        for name,n,k in [('wq_a',32,32),('wq_b',128,32),('wkv',32,32),('wo_b',32,128)]:m.w[p+'attn.'+name+'.weight']=q(n,k)
        m.w[p+'attn.q_norm.weight']=np.ones(32,np.float32)
        m.w[p+'attn.kv_norm.weight']=np.ones(32,np.float32)
        m.w[p+'attn.attn_sink']=np.zeros(4,np.float32)
        m.w[p+'attn.wo_a.weight']=dense(128,32)
        if L in m.kv_src:
            for name in ['wkv','wgate']:m.w[p+'attn.compressor.'+name+'.weight']=dense(32,32)
            m.w[p+'attn.compressor.norm.weight']=np.ones(32,np.float32)
            m.w[p+'attn.indexer.wk.weight']=dense(32,32)
            m.w[p+'attn.indexer.k_norm.weight']=np.ones(32,np.float32)
        if L in m.idx_src:
            m.w[p+'attn.indexer.wq_b.weight']=q(128,32)
            m.w[p+'attn.indexer.weights_proj.weight']=dense(4,32)
        m.w[p+'ffn.gate.weight']=dense(4,32);m.w[p+'ffn.gate.bias']=np.zeros(4,np.float32)
        for family in [f'experts.{e}' for e in range(4)]+['shared_experts']:
            for part in ['w1','w3','w2']:m.w[p+'ffn.'+family+'.'+part+'.weight']=q(32,32)
        if L in [1,14]:
            m.emb_codes[L]=(np.full((31,32),0x38,np.uint8),np.zeros((31,1),np.int32))
            m.w[p+'engram.wkv.weight']=q(160,768)
            m.w[p+'engram.q_weight']=np.ones((4,32),np.float32)
            m.w[p+'engram.k_weight']=np.ones((4,32),np.float32)
    return m


def equal_state(a,b):
    if isinstance(a,dict):assert a.keys()==b.keys();[equal_state(a[k],b[k]) for k in a]
    elif isinstance(a,(list,tuple)):assert len(a)==len(b);[equal_state(x,y) for x,y in zip(a,b)]
    else:assert np.array_equal(np.asarray(a),np.asarray(b))


def test_full40_functional_execution_against_golden_and_persistent_next_tokens(program):
    m=tiny_model();a=m.new_state();b=m.new_state()
    for pos,tokens in [(0,[3,7]),(2,[9,1])]:
        ta=[{} for _ in tokens];tb=[{} for _ in tokens]
        expected=m.forward_positions(tokens,pos,a,traces=ta,force=None)
        actual=F.execute(program,m,tokens,pos,b,traces=tb)
        for x,y in zip(expected,actual['logits']):assert np.array_equal(x.view(np.uint32),y.view(np.uint32))
        assert actual['next_tokens']==[int(np.argmax(x)) for x in expected]
        equal_state(a,b);equal_state(ta,tb)
        assert all(len(b['win'][L])==pos+len(tokens) for L in range(40))
        assert len(b['ckv'][2])==(pos+len(tokens))//2
        assert len(b['ckv'][20])==pos+len(tokens)


def test_optin_required():
    with pytest.raises(ValueError,match="opt_in"):F.build_program()


def test_home_contract_codec_scope_and_prelease(program):
    import w11_dsrom_full_tp_program_contract as C
    c=C.build_contract(program)
    t=c['corrected_reference_word_totals']
    assert t['reference_word_totals_by_codec']['reference_HE_hplace_FP32']==1638400
    assert t['HE_words_all_four_reference_copies']==6553600
    assert all(v['physical_home'] is None for v in c['matrix_views'])
    assert c['source_pins']['corrected_codec']['commit'].startswith('93431e3c')
    assert c['mandatory_order'].index('9actual burstvisible writes')<c['mandatory_order'].index('f_job')
    w=next(v for v in c['matrix_views'] if v['tensor']=='layers.0.attn.wo_a.weight')
    assert w['checkpoint_dtype']=='F8_E4M3' and w['runtime_format']=='BF16_after_FP8_QDQ'
    hc=next(v for v in c['matrix_views'] if v['tensor']=='layers.0.hc_attn_fn')
    assert hc['reference_codec_contract']['word_bits']==768
    assert hc['reference_codec_contract']['tensor_count_scope']=='per_reference_rank'


def test_ratio2_projection_gathers_do_not_mix_gate_and_latent_rows(program):
    for L in [2,8,14]:
        s=program['stages'][L]
        gathers=[c for c in s['collectives'] if '.compressor.' in c['tag'] and 'projection_gather' in c['tag']]
        assert len(gathers)==2 and [c['n'] for c in gathers]==[128,128]
        assert gathers[1]['destination']-gathers[0]['destination']==512
        assert any(m['logical_key'][-1]=='cwgate' and m['rows_per_rank']==128 for m in s['matrices'])
