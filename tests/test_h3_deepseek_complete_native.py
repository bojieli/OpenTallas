import gzip
import importlib.util
import json
from pathlib import Path
import sys
from types import SimpleNamespace
import numpy as np
import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import h3_deepseek_complete_native as N
import hdc_golden_v41 as V
import hdc_golden as G

TOY=dict(n=16,k=32,rows=2,heads=4,width=32,qa=32,kv=32,window=3,index_width=32,ea=112,ea_start=0,ranks=4,vocab=32)
ATTR=dict(k=3,slot=0,global_n=16,ratio=2,closes=True,which='ffn')

def fixture(p):
    rng=np.random.default_rng(9827);mem={}
    for name,d in p['providers'].items():
        s=d['shape'];dt=d['dtype']
        if dt=='F32':mem[name]=(rng.normal(0,.15,s)).astype(np.float32)
        elif dt=='U32':mem[name]=np.ones(s,np.uint32)
        else:mem[name]=np.zeros(s,np.int64)
    for name in ('gamma','q_gamma','kv_gamma','index_gamma'): 
        if name in mem:mem[name]=np.ones_like(mem[name])
    for name in ('h','res','x','q_own','q','qa','kvraw','rows','keys','iqf','iq','key','value','g','u','expert_outputs'):
        if name in mem:mem[name]=G.to_bf16(mem[name])
    for prefix in ('rope','index_rope'):
        if prefix+'_cos' in mem:mem[prefix+'_cos'][:]=1;mem[prefix+'_sin'][:]=0
    if 'hc_scale' in mem:mem['hc_scale'][:]=.125
    if 'weight_codes' in mem:mem['weight_codes']=rng.choice([0,48,56,64,176,184,192],mem['weight_codes'].shape).astype(np.uint32)
    if 'weight_scale_codes' in mem:mem['weight_scale_codes'][:]=127
    if 'query_codes' in mem:
        tables=np.asarray([0,1,2,3,4,6,8,12,0,-1,-2,-3,-4,-6,-8,-12],np.int64)
        for prefix in ('query','key'):
            mem[prefix+'_codes']=rng.integers(0,256,mem[prefix+'_codes'].shape,dtype=np.uint32)
            mem[prefix+'_exp'][:]=0
            codes=mem[prefix+'_codes'];units=np.stack([tables[codes&15],tables[codes>>4]],axis=-1).reshape(codes.shape[0],-1)
            mem['iqf' if prefix=='query' else 'keys']=(units*.5).astype(np.float32)
    for name in ('index_w_scale','attn_scale','engram_scale','route_weight'):
        if name in mem:mem[name]=np.asarray(.5,np.float32)
    if 'gsc' in mem:mem['gsc']=np.linspace(-1,1,mem['gsc'].size,dtype=np.float32)
    for name in ('ids','global_ids','owned_blocks'):
        if name in mem:mem[name]=np.arange(mem[name].size,dtype=np.int64).reshape(mem[name].shape)
    if 'selected_blocks' in mem:mem['selected_blocks']=np.arange(mem['selected_blocks'].size,dtype=np.int64)
    if 'selected_values' in mem:mem['selected_values'][:]=1
    if 'candidate_keep' in mem:mem['candidate_keep'][::2]=0
    if 'selected_ckv_codes' in mem:
        mem['selected_ckv_codes'][:]=0x22;mem['selected_ckv_scales'][:]=56;mem['selected_row_ids']=np.arange(mem['selected_row_ids'].size,dtype=np.int64)
    if 'route_ids' in mem:mem['route_ids']=np.arange(mem['route_ids'].size,dtype=np.int64)
    if 'expert_descriptor_table' in mem:mem['expert_descriptor_table']=np.arange(mem['expert_descriptor_table'].size,dtype=np.int64).reshape(mem['expert_descriptor_table'].shape)
    if 'sel' in mem:mem['sel']=np.arange(mem['sel'].size,dtype=np.int64)
    if 'ownership_mask' in mem:
        m=np.zeros_like(mem['ownership_mask']);m[np.arange(m.shape[1])%m.shape[0],np.arange(m.shape[1])]=1;mem['ownership_mask']=m
    if 'raw_recent_tokens' in mem:
        mem['raw_recent_tokens']=np.arange(1,5,dtype=np.int64);mem['token_map']=np.arange(mem['token_map'].size,dtype=np.int64)
        mem['multipliers']=np.asarray([3,5,7,11],np.int64);mem['primes'][:]=13;mem['offsets'][:]=0
        rolling=0;ids=[]
        for j,(t,mul) in enumerate(zip(mem['raw_recent_tokens'],mem['multipliers'])):
            rolling^=int(t*mul)
            if j:ids.extend([rolling%13]*mem['primes'].shape[1])
        mem['selected_row_ids']=np.asarray(ids,np.int64);mem['selected_codes'][:]=56 # 1.0
        mem['E4M3_decode']=V.E4M3.astype(np.float32);mem['selected_exp'][:]=0
    return mem


def execute(f,sh=None,at=None):
    p=N.recipe(f,TOY if sh is None else sh,ATTR if at is None else at);m=fixture(p);vm=N.Machine(p,m,N.primitive_div);return vm.run(),m,p,vm


def same(a,b):assert np.array_equal(np.asarray(a,np.float32).view(np.uint32),np.asarray(b,np.float32).view(np.uint32))

@pytest.fixture(autouse=True)
def arithmetic():
    old=V.ARITH;fuse=V.FUSE.copy();V.set_arith('chunk8');V.set_fuse('')
    yield
    V.set_arith(old);V.set_fuse(fuse)

@pytest.mark.parametrize('family',sorted(N.FAMILIES))
def test_all30_executable_no_host_macro(family):
    out,mem,p,vm=execute(family)
    assert out and len(vm.events)==len(p['code'])
    assert all(i['op'] in N.NATIVE for i in p['code'])
    assert all(not i['op'].startswith(('HC_','NORM','ATTEND','TOPK','GOLDEN','CALL')) for i in p['code'])
    assert p['resources']['hardware_latency'] is None
    assert not vm.fault

@pytest.mark.parametrize('family',['hc_pre_norm','final_norm','hc_post','hc_mixes','engram_mix'])
def test_hc_engram_exact_boundaries(family):
    out,m,p,vm=execute(family)
    fake=SimpleNamespace(hc=4,dim=16,eps=np.float32(1e-20),hc_eps=np.float32(1e-6),sinkhorn_iters=20,engram_scale=m.get('engram_scale'))
    if family in ('hc_pre_norm','final_norm'):
        mix=V.Model.hc_pre(fake,m['h'],m['pre']);same(out['x'],V.rmsnorm_bf16(mix,m['gamma'],fake.eps))
    elif family=='hc_post':same(out['h'],V.Model.hc_post(fake,m['y'],m['res'],m['post'],m['comb']))
    elif family=='hc_mixes':
        fake.lw=lambda layer,name:{'hc_ffn_fn':m['hc_fn'],'hc_ffn_scale':m['hc_scale'],'hc_ffn_base':m['hc_base']}[name]
        pre,post,comb=V.Model.hc_mixes(fake,m['h'],0,'ffn')
        same(out['pre'],pre);same(out['post'],post);same(out['comb'],comb)
        assert sum(i['op']=='DIV' for i in p['code'])==43 # norm, pre/post sigmoid, initial and39passes
    else:
        weight=G.mul(m['q_weight'],m['k_weight']);want=[]
        for j in range(4):
            h=m['h'][j];k=m['key'][j];r=G.mul(G.rsqrt(G.add(V.div(V.csum(G.mul(h,h)),np.float32(16)),fake.eps)),G.rsqrt(G.add(V.div(V.csum(G.mul(k,k)),np.float32(16)),fake.eps)))
            dot=G.mul(G.mul(V.csum(G.mul(G.mul(h,weight[j]),k)),r),m['engram_scale']);mag=V.sqrt(np.maximum(np.abs(dot),np.float32(1e-6)))
            gate=V.sigmoid(G.neg(mag) if dot<0 else mag);want.append(G.add(h,G.mul(gate,m['value'])))
        same(out['h'],G.to_bf16(np.stack(want)))

@pytest.mark.parametrize('family',['mv','linear_bf16','wo_a_part','linear_q','index_scores'])
def test_matrix_index_single_round_and_order(family):
    out,m,p,_=execute(family)
    if family=='linear_q':
        w=V.Q8(V.E4M3[m['weight_codes']],m['weight_scale_codes'].astype(np.int64)-127);same(out['out'],V.linear_q(w,m['x']))
    elif family=='index_scores':
        scores=G.to_bf16(V.dots_q4(m['iqf'],m['keys']));terms=G.to_bf16(G.mul(np.maximum(scores,np.float32(0)),m['iw'][:,None]));same(out['is_v'],G.to_bf16(V.csum(terms.T)))
        wrong=dict(m);wrong['query_codes']=m['query_codes'].copy();wrong['query_codes'][0,0]^=1
        with pytest.raises(ValueError,match='match produced'):N.Machine(p,wrong,N.primitive_div).run()
    else:
        want=V.csum(G.mul(m['weight'],G.to_bf16(m['x'])[None]))
        if family=='linear_bf16':want=G.to_bf16(want)
        same(out['out'],want)

@pytest.mark.parametrize('family',['q_norm_kv_row','q_rope','index_q','attend','router_act','route','swiglu','moe_sum'])
def test_ordinary_and_attention_boundary(family):
    out,m,p,_=execute(family)
    if family=='q_norm_kv_row':
        same(out['qr'],V.rmsnorm_bf16(m['qa'],m['q_gamma'],1e-20));kv=V.rmsnorm_bf16(m['kvraw'],m['kv_gamma'],1e-20);row=V.qdq_fp8(V.rope_tail(kv,(m['rope_cos'],m['rope_sin'])));same(out['win_new'],row)
    elif family=='q_rope':same(out['q_own'],V.rope_tail(m['q'],(m['rope_cos'],m['rope_sin'])))
    elif family=='index_q':
        q=V.rope_tail(m['iq'],(m['rope_cos'],m['rope_sin']));same(out['iqf'],np.stack([V.qdq_fp4_e8m0(x) for x in q]));same(out['iw'],G.to_bf16(G.mul(m['iwr'],m['index_w_scale'])))
    elif family=='attend':
        s=G.mul(V.dots(m['q_own'],m['rows']),m['attn_scale']);mx=np.max(s,axis=1);e=G.exp(G.add(s,G.neg(mx)[:,None]));pv=V.dots(G.to_bf16(e),m['rows'].T);den=G.add(V.csum(e),G.exp(G.add(m['sink'],G.neg(mx))));a=G.to_bf16(V.div(pv,den[:,None]));same(out['o'],V.rope_tail(a,(m['rope_cos'],m['rope_sin']),inverse=True).reshape(-1))
    elif family=='router_act':same(out['gsc'],V.sqrt(V.softplus(m['gsc'])))
    elif family=='route':
        biased=G.add(m['gsc'],m['bias']);ids=np.sort(V.topk_lowest_index(biased,6));assert np.array_equal(out['route_ids'],ids);den=G.add(V.seqsum(list(m['gsc'][ids])),np.float32(1e-20));same(out['route_w'],G.mul(V.div(m['gsc'][ids],den),np.float32(1.5)))
    elif family=='swiglu':
        want=G.to_bf16(G.mul(m['route_weight'],G.mul(V.silu(np.minimum(m['g'],np.float32(10))),np.clip(m['u'],-10,10))));same(out['ea'][:16],want);same(out['ea'][16:],m['ea_old'][16:])
    else:same(out['yf'],G.to_bf16(V.csum(m['expert_outputs'],axis=0,c=7)))

@pytest.mark.parametrize('fmt,block',[('FP8',32),('FP4E8',32),('FP4E4',16)])
def test_codec_ties_and_extrema(fmt,block):
    b=N.Builder();x=b.load('x',(64,));out,_,_=b.codec(x,fmt,block);b.output('out',out);p=b.finish()
    vals=np.resize(np.asarray([0,-0.,.25,.75,1.25,1.75,2.5,3.5,5.,-6.,.03125,.01171875,448.,-448.],np.float32),64)
    got=N.Machine(p,{'x':vals},N.primitive_div).run()['out'];fn={'FP8':V.qdq_fp8,'FP4E8':V.qdq_fp4_e8m0,'FP4E4':V.qdq_fp4_e4m3}[fmt];same(got,fn(vals,block))


def test_gather_collision_rejected_and_no_early_physical_claim():
    out,m,p,_=execute('all_gather');want=np.zeros(16,np.float32)
    for r in range(4):want[m['ownership_mask'][r]!=0]=m['parts'][r][m['ownership_mask'][r]!=0]
    same(out['out'],want);m['ownership_mask'][1,0]=1
    with pytest.raises(ValueError,match='exactly one owner'):N.Machine(p,m,N.primitive_div).run()


def test_exact_div_fault_contract_reused():
    b=N.Builder();a=b.load('a',(4,));c=b.load('b',(4,));y=b.op('DIV',a,c);b.output('y',y)
    a=np.asarray([1.,1.,np.inf,np.finfo(np.float32).max],np.float32);d=np.asarray([5120.,0.,1.,.5],np.float32);vm=N.Machine(b.finish(),{'a':a,'b':d},N.primitive_div);out=vm.run()['y']
    assert vm.fault;assert np.all(out[1:].view(np.uint32)==0);assert out[0].view(np.uint32)==N._scalar.div_contract(0x3f800000,0x45a00000)[0]


def test_selection_ties_lowest_global_id():
    p=N.recipe('topk_local',{'n':7},{'k':4});v=np.asarray([1,2,2,-np.inf,2,-0.,0.],np.float32);ids=np.asarray([9,8,2,0,1,7,6],np.int64)
    out=N.Machine(p,{'scores':v,'ids':ids},N.primitive_div).run();ix=np.lexsort((ids,-v))[:4];same(out['values'],v[ix]);assert np.array_equal(out['ids'],ids[ix])


def test_compressor_full_paired_append_and_open_branch():
    out,m,p,_=execute('compressor')
    slots=np.concatenate([m['open_group'],m['cmp'].reshape(1,2,32)],axis=0);kv=slots[:,0];scores=slots[:,1];mx=np.max(scores,axis=0);e=G.exp(G.add(scores,G.neg(mx)));weights=V.div(e,V.seqsum(list(e)));pooled=V.seqsum([G.mul(kv[j],weights[j]) for j in range(2)])
    latent=V.rmsnorm_bf16(G.to_bf16(pooled),m['gamma'],1e-20);key=V.rmsnorm_bf16(V.linear_bf16(m['index_weight'],latent),m['index_gamma'],1e-20)
    same(out['new_ckv'],V.qdq_fp4_e4m3(V.rope_tail(latent,(m['rope_cos'],m['rope_sin'])),16));same(out['new_ik'],V.qdq_fp4_e8m0(V.rope_tail(key,(m['index_rope_cos'],m['index_rope_sin']))))
    out,m,p,_=execute('compressor',at={**ATTR,'closes':False});assert set(out)=={'open_group'};same(out['open_group'],m['cmp'].reshape(1,2,32))


def test_engram_integer_hash_and_selected_payload_identity():
    out,m,p,_=execute('engram_fetch');rolling=0;ids=[]
    for j in range(4):
        rolling^=int(m['token_map'][m['raw_recent_tokens'][j]])*int(m['multipliers'][j])
        if j:ids.extend(rolling%m['primes'][j-1])
    assert np.array_equal(out['row_ids'],np.asarray(ids)+m['offsets'])
    expected=G.to_bf16(np.ldexp(V.E4M3[m['selected_codes']].astype(np.float32).reshape(*m['selected_exp'].shape,32),m['selected_exp'][...,None])).reshape(-1);same(out['eg_rows'],expected)
    m['selected_row_ids']=m['selected_row_ids']+1
    with pytest.raises(ValueError,match='row response identity'):N.Machine(p,m,N.primitive_div).run()


@pytest.mark.parametrize('family',['cand_local','cand_apply','cand_mask','topk_local','topk_merge','argmax_local','all_reduce','expert_fetch','kv_gather'])
def test_metadata_collective_provider_boundaries(family):
    out,m,p,_=execute(family)
    if family in ('topk_local','topk_merge','argmax_local'):
        ids=m.get('ids',np.arange(16,dtype=np.int64));ix=np.lexsort((ids,-m['scores']))[:len(out['values'])];same(out['values'],m['scores'][ix]);assert np.array_equal(out['ids'],ids[ix])
    elif family=='cand_local':
        blocks=np.asarray([0,96]);v=np.max(m['scores'].reshape(2,8),axis=1);ix=np.lexsort((blocks,-v));same(out['cand_v'],v[ix]);assert np.array_equal(out['cand_i'],blocks[ix])
    elif family=='cand_apply':assert np.array_equal(out['candidate_keep'],np.isin(m['ids'],m['selected_blocks']).astype(np.uint32))
    elif family=='cand_mask':same(out['is_v'],np.where(m['candidate_keep'][np.arange(16)//8],m['scores'],-np.inf))
    elif family=='all_reduce':
        t=list(m['parts'])
        while len(t)>1:t=[G.add(t[j],t[j+1]) for j in range(0,len(t),2)]
        same(out['out'],G.to_bf16(t[0]))
    elif family=='expert_fetch':assert np.array_equal(out['descriptors'],m['expert_descriptor_table'][m['route_ids']])
    elif family=='kv_gather':same(out['selected'],np.ones((2,32),np.float32))


def test_chunk_order_mutant_is_numerically_detected():
    b=N.Builder();v=b.load('x',(16,));s=b.reduce(v);b.output('out',s);p=b.finish()
    x=np.asarray([2**24,1,-2**24,1,0,0,0,0,1,0,0,0,0,0,0,0],np.float32);good=N.Machine(p,{'x':x},N.primitive_div).run()['out'];same(good,V.csum(x))
    assert good!=np.sum(x.astype(np.float64)).astype(np.float32)
    # Changed opcode at a real accumulation boundary must differ, not a mirrored test.
    mutant=json.loads(json.dumps(p));acc=next(i for i in mutant['code'] if i['op']=='FADD');acc['op']='FMUL'
    bad=N.Machine(mutant,{'x':x},N.primitive_div).run()['out'];assert bad.view(np.uint32)!=good.view(np.uint32)

@pytest.mark.parametrize('fmt',['fp8','fp4'])
def test_native_raw_weight_decode_and_poison(fmt):
    p=N.recipe('linear_q',TOY,{**ATTR,'fmt':fmt});m=fixture(p)
    if fmt=='fp4':
        raw=m['weight_codes'];w=V.E2M1[np.stack([raw&15,raw>>4],axis=-1).reshape(2,32)]
    else:w=V.E4M3[m['weight_codes']]
    got=N.Machine(p,m,N.primitive_div).run()['out'];same(got,V.linear_q(V.Q8(w,m['weight_scale_codes'].astype(np.int64)-127),m['x']))
    if fmt=='fp8':
        m['weight_codes'][0,0]=127
        with pytest.raises(ValueError,match='finite weight'):N.Machine(p,m,N.primitive_div).run()


def test_index_query_codes_are_actual_integer_kernel_operands():
    out,m,p,_=execute('index_q');raw=out['query_codes'];units=np.asarray([0,1,2,3,4,6,8,12,0,-1,-2,-3,-4,-6,-8,-12],np.int64)
    decoded=V.E2M1[np.stack([raw&15,raw>>4],axis=-1).reshape(4,32)].reshape(4,1,32)
    exponent=out['query_exp'].astype(np.uint32).view(np.int32)
    same(np.ldexp(decoded,exponent[...,None]).astype(np.float32).reshape(4,32),out['iqf'])


def test_whole_source_census_every_pc_every_native_output():
    path=ROOT/'results/uarch/h3_deepseek_complete_native_20261002/program_final.json.gz'
    p=json.loads(gzip.decompress(path.read_bytes()));assert p['coverage']['PCs']==2213;assert set(p['coverage']['families'])==N.FAMILIES
    assert len(p['instructions'])==2213;assert [o['pc'] for o in p['instructions']]==list(range(2213))
    for o in p['instructions']:
        assert o['native_program_present'];assert all(dep<o['pc'] for dep in o['dependencies'])
        assert all('native_result_binding' in w for w in o['writes'])
        for rank in o['rank_bindings']:
            if rank.get('empty_owned_extent'):continue
            template=p['templates'][rank['template']];written=set()
            for ins in template['code']:
                assert ins['op'] in N.NATIVE;assert all(v in written for v in ins['src']);written.add(ins['dst'])
            assert all(v in written for v in template['outputs'].values())
    assert p['coverage']['golden_macro_callbacks']==0;assert p['scalar_dependency']['owner']=='Epicurus'
    assert not p['hardware_qualified'];assert p['clock_costs']['full_token_cycles'] is None

@pytest.mark.parametrize('family',['linear_q','index_scores','kv_gather','hc_mixes','compressor','engram_fetch'])
def test_finite_versioned_native_provider_join(family):
    p=N.recipe(family,TOY,ATTR);m=fixture(p)
    expected=N.Machine(p,m,N.primitive_div).run()
    got,receipt=N.execute_finite(p,m,(17,'operand_v3',0,2,9))
    assert receipt['status']=='PASS_NATIVE_LOGICAL_PROVIDER_JOIN'
    assert receipt['provider']['outstanding']==0
    assert receipt['provider']['events']['accepted']==receipt['provider']['events']['consumer_done']
    assert not receipt['physical_visibility_qualified'];assert receipt['timing_cycles'] is None
    for key in expected:assert np.array_equal(got[key].view(np.uint8).reshape(-1),expected[key].view(np.uint8).reshape(-1))


def test_fault_blocks_logical_output_and_retains_exact_div_error_codes():
    b=N.Builder();a=b.load('a',(3,));d=b.load('b',(3,));b.output('out',b.op('DIV',a,d));p=b.finish()
    out,receipt=N.execute_finite(p,{'a':np.asarray([1,np.inf,np.finfo(np.float32).max],np.float32),'b':np.asarray([0,1,.5],np.float32)},(1,'v0',0,0,0))
    assert out=={};assert receipt['status']=='FAULT_NO_OUTPUT_PUBLICATION'
    assert receipt['errors'][0]['errors']==[1,1,2]
    assert not any(e['key'][0]=='native_output' for e in receipt['provider']['trace'])


def test_packet_commit_after_arithmetic_fault_is_rejected():
    b=N.Builder();v=b.op('DIV',b.load('a',()),b.const(0.));v=b.emit('PACKET_COMMIT',v,shape=());b.output('out',v)
    with pytest.raises(ValueError,match='fault prevents successful publication'):N.Machine(b.finish(),{'a':np.float32(1)},N.primitive_div).run()


@pytest.mark.parametrize('failure',['missing','shape','identity','scale_poison'])
def test_selected_packet_provider_rejections(failure):
    p=N.recipe('kv_gather',TOY,ATTR);m=fixture(p)
    if failure=='missing':del m['selected_ckv_codes']
    elif failure=='shape':m['selected_ckv_codes']=m['selected_ckv_codes'][:1]
    elif failure=='identity':m['selected_row_ids'][0]+=1
    else:m['selected_ckv_scales'][0,0]=127
    with pytest.raises(ValueError):N.execute_finite(p,m,(8,'ckv_v2',0,0,4))
