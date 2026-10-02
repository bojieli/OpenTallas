"""Software-only native interpreter tests; golden is used only after execution."""
import copy
import gzip
import json
import sys
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import h3_qwen_complete_native as N
from qwen_hbm_complete_program import compile_program, OPCODES
from qwen_hbm_complete_executor import SoftwareGPUProvider, execute, FixtureWeights
import qwen_hbm_complete_executor as G


def small(layers=2):
    return dict(hidden_size=8,head_dim=4,num_attention_heads=2,num_key_value_heads=2,
                intermediate_size=16,vocab_size=16,num_hidden_layers=layers,
                rms_norm_eps=1e-6,rope_theta=1000000)


def exact(a,b):
    if isinstance(a,dict): assert a==b
    elif isinstance(a,tuple):
        assert a==b
    elif np.asarray(b).dtype.kind=='f':
        a=np.asarray(a,dtype=np.float32); b=np.asarray(b,dtype=np.float32)
        assert a.shape==b.shape
        np.testing.assert_array_equal(a.view(np.uint32),b.view(np.uint32))
    else: np.testing.assert_array_equal(a,b)


def machine(layers=2):
    return N.Machine(N.compile_native(compile_program(small(layers),context=32,groups=16)))


def test_actual_versioned_whole_program_compile_and_replay():
    native=N.compile_native()
    assert native['coverage']['PCs']==1737
    assert set(native['coverage']['families'])==set(OPCODES)
    assert len(native['coverage']['families'])==21
    assert native['coverage']['null_native_lowerings']==0
    with gzip.open(N.ROOT/N.INPUT,'rt') as f: old=json.load(f)
    for op,source in zip(native['operations'],old['operations']):
        assert op['reads']==source['reads'] and op['writes']==source['writes']
        assert op['recipe'] and op['native_lowering']['executable']
        assert op['dependencies']==source['dependencies']
        assert op['schedule']['duration_symbol'] in native['schedule']['duration_expression']
        assert not op['schedule']['hardware_qualified']
    assert all(x['cost_symbol'].startswith('C_') for x in native['schedule']['unknowns'].values())
    assert 'DIV' not in native['coverage']['primitives']
    assert N.canonical(native)==N.canonical(N.compile_native())


def test_no_source_opcode_or_oracle_callback_in_native_execution(monkeypatch):
    m=machine(36)
    def forbidden(*args,**kwargs): raise AssertionError('source opcode callback')
    monkeypatch.setattr(SoftwareGPUProvider,'execute',forbidden)
    for name in ('exp','rsqrt','reciprocal','matrix','rstd','chunk8','bf16','fp8_encode','fp8_decode'):
        monkeypatch.setattr(G,name,forbidden)
    r=m.run(3,0)
    assert r['instructions_retired']==1737
    assert r['status']=='SOFTWARE_NATIVE_PROGRAM_COMPLETED'
    assert not r['hardware_or_timing_credit']
    assert not m.live and not m.address_words


def test_every_PC_output_bits_two_tokens_vs_source_oracle():
    m=machine(); p=m.p; oracle=SoftwareGPUProvider(p); covered=set()
    for token,pos in [(3,0),(5,1)]:
        expected={}
        execute(p,oracle,token,pos,observer=lambda op,out:expected.update({op['id']:copy.deepcopy(out)}))
        def observe(op,out):
            covered.add(op['opcode'])
            assert len(out)==len(expected[op['id']])
            # Tags differ because the native storage shares tag and lease counters.
            if op['opcode'] in ('KV_WRITE','KV_FENCE'): return
            for a,b in zip(out,expected[op['id']]): exact(a,b)
        result=m.run(token,pos,observe)
        assert result['instructions_retired']==len(p['instructions'])
    assert covered==set(OPCODES)
    assert len(m.storage.published)==8
    assert len([e for e in m.storage.events if e['event']=='release'])==8


def eval_nodes(nodes,env=None):
    m=machine(1); e={} if env is None else dict(env)
    m.nodes(nodes,e,dict(reads=[],writes=[])); return e


@pytest.mark.parametrize('length',[1,7,8,9,15,16,17,128,4096])
def test_norm_and_sum_chunk_tree_rounding_boundaries(length):
    x=np.resize(np.array([1e10,1,-1e10,1,1,1,1,1],np.float32),length)
    e=eval_nodes(N.sum_last('x','out',length),{'x':x})
    exact(e['out'],G.chunk8(x))
    y=np.resize(np.array([-0.,1.,.001,100,1.00390625,1e-8],np.float32),length)
    e=eval_nodes(N.norm('x','out',length,1e-6),{'x':y})
    exact(e['out'],G.rstd(y,1e-6))
    means=[i for i in N.walk(N.norm('x','out',length,1e-6)) if i.get('dst')=='mean']
    assert means[0]['op']=='FMUL'
    if length==4096: assert means[0]['src'][1]=='f32(0.000244140625)'


def test_exp_reciprocal_bf16_and_fp8_boundaries():
    x=np.array([-100,-87,-1,-0.,0.,.3465736,1,10,88,100],np.float32)
    exact(eval_nodes(N.exponential('x','out'),{'x':x})['out'],G.exp(x))
    x=np.array([1e-30,.5,1,2,1e30,np.finfo(np.float32).max],np.float32)
    exact(eval_nodes(N.reciprocal('x','out'),{'x':x})['out'],G.reciprocal(x))
    x=np.array([-0.,1.00390625,1.01171875,-1.00390625,1e-40],np.float32)
    exact(eval_nodes(N.bfpack('x','out'),{'x':x})['out'],G.bf16(x))
    x=np.array([-0.,0.,.0009765625,.001953125,.0029296875,.0146484375,1.0625,1.1875,448,-448,1000],np.float32)
    np.testing.assert_array_equal(N.pack8(x),G.fp8_encode(x))


@pytest.mark.parametrize('interleaved,K,split',[(False,16,4),(True,17,8),(True,1,16)])
def test_matrix_order_and_empty_interleaved_chunks(interleaved,K,split):
    x=np.resize(np.array([1e10,1,-1e10,1],np.float32),K)
    w=np.resize(np.array([1,-1,3,0],np.float32),(3,K))
    exact(eval_nodes(N.dot('x','w','out',split,interleaved),{'x':x,'w':w})['out'],G.matrix(w,x,split,interleaved))


def test_collective_residual_and_argmax_tie_boundaries():
    m=machine(1)
    for family,inputs in [('RESIDUAL',[np.array([-0.,1e10],np.float32),np.array([0.,1],np.float32)]),
                          ('ARGMAX',[np.array([2,2,-1,2],np.float32)]),
                          ('ARGMAX_REDUCE',[(2.,7),(2.,3)])]:
        source=next(o for o in m.p['instructions'] if o['opcode']==family)
        e={f'input{i}':v for i,v in enumerate(inputs)}
        m.nodes(N.recipe(source,m.p),e,dict(reads=[],writes=[]))
        if family=='RESIDUAL': exact(e['out0'],G.add(*inputs))
        elif family=='ARGMAX': assert e['out0'][1]==source['attributes']['global_row_offset']
        else: assert int(e['out0'])==3


def test_write_accept_not_publication_and_missing_previous_rejected():
    m=machine(1); s=m.storage
    tag=s.begin(0,0,0)
    with pytest.raises(ValueError,match='stale fence'): s.acquire(dict(key=(0,0,0),tag=tag),0,0,0)
    with pytest.raises(ValueError,match='incomplete'): s.commit(tag)
    with pytest.raises(ValueError,match='overwrite'): s.begin(0,0,0)
    m=machine(1)
    with pytest.raises(ValueError,match='missing previous'): m.run(3,1)


def test_bad_versions_dependencies_and_addresses_fail_closed():
    m=machine(1); m.native['operations'][1]['dependencies']=[999]
    with pytest.raises(ValueError,match='unretired dependency'): m.run(3,0)
    m=machine(1); m.native['operations'][0]['reads']=['wrong']
    with pytest.raises(ValueError,match='missing source'): m.run(3,0)
    m=machine(1); s=m.storage; t=s.begin(0,0,0)
    with pytest.raises(ValueError,match='aperture'): s.write(t,np.array([-1]),np.array([0]))


def test_postexecution_shipped_torch_golden_all_layers_head():
    pytest.importorskip('torch')
    from qwen_hbm_complete_reference import PostExecutionReference
    m=machine(2); ref=PostExecutionReference(m.p,FixtureWeights(m.p))
    for token,pos in [(3,0),(5,1)]:
        ref.start_token(token,pos)
        def observe(op,out):
            name=op['outputs'][0]
            if name.startswith('L') and name.endswith('.X'): ref.layer(int(name.split('.')[0][1:]),out[0])
            if name=='head.norm': ref.final_norm(out[0])
            if name in ('head.d0.scaled','head.d1.scaled'): ref.head(int(name[6]),out[0])
        result=m.run(token,pos,observe)
        assert result['next_token']==ref.next_token
    assert all(c['bit_mismatches']==0 for c in ref.comparisons)


def test_bfpack_exceptional_payloads_and_zero_source_conventions():
    patterns=np.array([0,0x80000000,1,0x80000001,0x007fffff,0x00800000,
                       0x7f800000,0xff800000,0x7fc00000,0xffc00001,
                       0x7f800001,0xff800001,0x7fffffff,0xffffffff],dtype=np.uint32)
    values=patterns.view(np.float32)
    result=eval_nodes(N.bfpack('x','out'),{'x':values})['out']
    # Source BFPACK is integer modulo arithmetic, even on NaN payloads. It
    # does not apply the ADD/MUL canonical-zero convention or NaN repair.
    exact(result,G.bf16(values))
    assert result.view(np.uint32)[1]==0x80000000
    assert result.view(np.uint32)[-2]==0x80000000
    assert result.view(np.uint32)[-1]==0


def test_exact_scalar_committed_contract_witnesses():
    import subprocess
    model=json.loads(subprocess.check_output(['git','show',
        '66bd7367c:results/uarch/h3_exact_scalar_contract_20261002/model.json'],cwd=N.ROOT))
    for witness in model['Newton_traces']:
        x=np.array(int(witness['input'],16),np.uint32).view(np.float32)
        if witness['kind']=='reciprocal': nodes=N.reciprocal('x','out'); env={'x':x}; seedname='seed'
        else:
            nodes=N.norm('unused','out',4096,1e-6)
            nodes=nodes[next(i for i,n in enumerate(nodes) if n.get('dst')=='vb'):]
            env={'variance':x}; seedname='ybits'
        e=eval_nodes(nodes,env)
        assert int(np.asarray(e[seedname],np.uint32))==int(witness['seed'],16)
        assert int(np.asarray(e['out'],np.float32).view(np.uint32))==int(witness['result'],16)
        counts={op:sum(n['op']==op for n in N.walk(nodes)) for op in ('FMUL','FADD','NEG')}
        expected={'FMUL':6,'FADD':3,'NEG':3} if witness['kind']=='reciprocal' else {'FMUL':10,'FADD':3,'NEG':3}
        assert counts==expected


def test_calendar_export_has_finite_concrete_workspace_and_provider_refs():
    native=N.compile_native()
    ids=set()
    for operation in native['operations']:
        assert operation['calendar_export']['operand_versions']==operation['reads']+operation['writes']
        assert operation['temporary_storage']['RF_vectors_used']<=32
        for name,allocation in operation['temporary_storage']['allocations'].items():
            home=allocation['home']
            assert allocation['max_words']>0 and allocation['lease']
            if home['class_']=='RF': assert min(home['vector_slots'])>=3
            else: assert home['byte_offset']>=0 and home['base_by_rank']
        for step in N.walk(operation['recipe']):
            assert step['step_id'] not in ids
            ids.add(step['step_id'])
            assert step['cost_parameter'].startswith('C_')
            if step['op']=='FOR': continue
            assert step['provider_ref']['ref'] and step['count_expression']
            assert step['read_ports'] is not None and step['write_port'] is not None
            assert step['source_arithmetic'] and step['value_versions']
            if step['op'].startswith('LOAD_'):
                ref=step['provider_ref']
                assert ref['base']>=0 and ref['extent_bytes']>0
                assert ref['depends_on']=='checkpoint_weight_and_table_residence'
                assert step['external_dependencies']
    for layout in native['storage']['software_provider_layout']:
        assert layout['workspace_base']>=layout['source_spill_base']+layout['source_spill_bytes']
        assert layout['capacity_fit'] and not layout['residence_qualified']
    assert all(not v['measured'] for v in native['schedule']['transport_cost_parameters'].values())


def test_argmax_first_nan_matches_source():
    m=machine(1); op=next(o for o in m.p['instructions'] if o['opcode']=='ARGMAX')
    x=np.array([1,np.nan,3,np.nan],np.float32); e={'input0':x}
    m.nodes(N.recipe(op,m.p),e,dict(reads=[],writes=[]))
    assert e['out0'][1]==int(np.argmax(x))+op['attributes']['global_row_offset']


def test_calendar_exact_primitive_counts_match_executable_recipe_two_positions():
    m=machine(1); values={v['version']:v for v in m.native['operands']}
    for position in (0,1):
        before=dict(m.primitive_counts); result=m.run(3,position)
        predicted={}
        for operation,source in zip(m.native['operations'],m.p['instructions']):
            count=N.count_transactions(operation,source,m.p,values,position)
            for primitive,entry in count['by_primitive'].items():
                predicted[primitive]=predicted.get(primitive,0)+entry['primitive_invocations']
        assert predicted=={op:n-before.get(op,0) for op,n in m.primitive_counts.items()}
        assert not result['hardware_or_timing_credit']


def test_KV_token16_layout_boundary_and_last_context_position():
    m=machine(1); oracle=SoftwareGPUProvider(m.p)
    for position in range(32):
        expected={}
        execute(m.p,oracle,3,position,observer=lambda op,out:expected.update({op['id']:copy.deepcopy(out)}))
        def compare(op,out):
            if position not in (15,16,31) or op['opcode'] in ('KV_WRITE','KV_FENCE'): return
            for a,b in zip(out,expected[op['id']]): exact(a,b)
        m.run(3,position,compare)
    assert len(m.storage.published)==64
    for die in (0,1):
        kbase=N.extent(m.p,die,'L0.K')['base']
        # dim0, head0: token15 occupies final byte of tile0; token16 begins tile1.
        assert (die,kbase+15) in m.storage.bytes
        assert (die,kbase+4*16) in m.storage.bytes
    with pytest.raises(ValueError,match='runtime aperture'): m.run(3,32)


def test_reciprocal_saturation_seed_exceptional_source_bits():
    patterns=np.array([0,0x80000000,0x7ef311c6,0x7ef311c7,0x7ef311c8,
                       0x7f7fffff,0x7f800000,0xff800000,0x7fc12345],np.uint32)
    x=patterns.view(np.float32)
    with np.errstate(all='ignore'):
        e=eval_nodes(N.reciprocal('x','out'),{'x':x})
        exact(e['out'],G.reciprocal(x))
    assert e['seed'][4]==0 and e['seed'][5]==0
    assert e['seed'][6]!=0  # positive Inf is excluded from finite saturation


def test_addressed_writes_and_reads_cannot_cross_tag_or_lease_generation():
    m=machine(1); s=m.storage; base=N.extent(m.p,0,'L0.K')['base']
    tag=s.begin(0,0,0)
    with pytest.raises(ValueError,match='write generation'): s.write(tag,np.array([base+1]),np.array([0]))
    m=machine(1); m.run(3,0); m.run(3,1)
    tag=m.storage.published[(0,0,0)]
    lease=m.storage.acquire(dict(key=(0,0,0),tag=tag),0,0,0)
    with pytest.raises(ValueError,match='outside lease generation'): m.storage.read(lease,np.array([base+1]))


def test_integrated_provider_join_all_homes_and_external_refs_are_authoritative():
    native=N.compile_native(); provider,pin=N.load_provider_binding()
    assert native['provider_binding_pin']==pin
    assert provider['coverage']==dict(PCs=1737,control_homes=144,data_homes=31232,
                                      opcode_classes=21,unbound_versions=0,versions=2027)
    byversion={}
    for home in provider['version_homes']+provider['control_homes']:
        byversion.setdefault(home['version'],[]).append(home)
    for value in native['operands']:
        assert value['homes']==byversion[value['version']]
    extents={e['provider_ref']:e for a in provider['allocation'] for e in a['extents']}
    for operation,bound in zip(native['operations'],provider['operations']):
        assert operation['provider_binding']==bound
        assert operation['calendar_export']['concrete_provider_operation']==bound
        assert operation['calendar_export']['provider_resource_contract']==provider['resource_contract']
        for step in N.walk(operation['recipe']):
            if step['op']=='FOR': continue
            assert step['version_home_refs']['reads']==bound['inputs']
            assert step['external_provider_refs']==bound['external_providers']
            if step['op'].startswith('LOAD_'):
                ref=step['provider_ref']
                assert ref['ref'] in extents
                assert ref['base']==extents[ref['ref']]['base']
    assert all(layout['source_spill_bytes']==32*1024**2 for layout in native['storage']['software_provider_layout'])


def test_actual32SM_provider_home_executor_replay_all1737PCs():
    m=machine(36); provider,pin=N.load_provider_binding()
    N.join_provider_homes({v['version']:v for v in m.native['operands']},provider)
    m.native['concrete_provider_binding']=provider; m.native['provider_binding_pin']=pin
    # Reinitialize so the executor loads the exact reverse-release predecessor map.
    m=N.Machine(m.native)
    result=m.run(3,0)
    assert result['instructions_retired']==1737
    assert not m.provider_payloads
    pubs=[e for e in m.events if e['event'].startswith('PUBLISH:')]
    releases=[e for e in m.events if e['event'].startswith('RELEASE:')]
    assert len(pubs)==len(releases)==31232
    assert len(m.release_events)==31232
    assert not result['hardware_or_timing_credit']


def test_executor_reads_scattered_provider_words_and_rejects_missing_home():
    native=N.compile_native(); m=N.Machine(native)
    value=next(v for v in native['operands'] if v['name']=='X.embed')
    x=np.arange(4096,dtype=np.float32)
    m.write_version(value['version'],x)
    exact(m.read_version(value['version']),x)
    rank0=[h for h in value['homes'] if h['rank']==0]
    assert {h['SM'] for h in rank0}==set(range(16))
    home=rank0[1]
    np.testing.assert_array_equal(m.provider_payloads[home['provider_ref']],x[256:512].view(np.uint32))
    m.provider_payloads[home['provider_ref']][0]=np.array(7,np.float32).view(np.uint32)
    assert m.read_version(value['version'])[256]==7  # actual home backing is read, not register shadow
    m.provider_payloads.pop(home['provider_ref'])
    with pytest.raises(ValueError,match='unpublished provider'): m.read_version(value['version'])


class TiledOracleWeights:
    """TEST only: materialize small raw fixture weights for the source oracle."""
    def __init__(self,p): self.p=p; self.raw=N.TileFixtureWeights(p)
    def matrix(self,key):
        d=self.p['weight_descriptors'][key]
        assert d['rows']*d['K']<65536
        q=np.empty((d['rows'],d['K']),np.int8)
        for r in range(0,d['rows'],128):
            for k in range(0,d['K'],32):
                q[r:r+128,k:k+32]=self.raw.matrix_tile(key,r,min(128,d['rows']-r),k,min(32,d['K']-k))
        return q,self.raw.scale_tile(key,0,d['rows'])
    def constant(self,layer,kind):
        count=self.p['config']['head_dim'] if kind in ('q','k') else self.p['config']['hidden_size']
        return self.raw.gamma_tile(layer,kind,0,count)
    def embedding(self,token):
        codes,scale=self.raw.embedding_tile(token,0,self.p['config']['hidden_size'])
        return G.mul(codes.astype(np.float32),scale)


def test_tiled_every_PC_bits_source_oracle_two_layers_context_boundaries():
    p=compile_program(small(),context=32,groups=16)
    m=N.TiledMachine(N.compile_tiled(p)); oracle=SoftwareGPUProvider(m.p,TiledOracleWeights(m.p)); seen=set()
    for pos in range(17):
        expected={}
        G.execute(m.p,oracle,3,pos,observer=lambda op,out:expected.update({op['id']:copy.deepcopy(out)}))
        def observe(op,store):
            seen.add(op['opcode'])
            if op['opcode'] in ('KV_WRITE','KV_FENCE'): return
            for version,value in zip(op['writes'],expected[op['pc']]): exact(store.debug_snapshot(version),value)
        result=m.run(3,pos,observe if pos in (0,1,15,16) else None)
        assert result['RF_workspace_peak_vectors']<=32
        assert result['shared_tile_peak_bytes']<=16384
        assert result['temporary_HBM_bytes']==0
        assert not m.store.pages and not m.store.live and not m.memory.leases
    assert seen==set(OPCODES)


def test_tiled_analytical_counts_match_per_PC_execution():
    p=compile_program(small(1),context=32,groups=16); m=N.TiledMachine(N.compile_tiled(p))
    for position in range(2):
        previous={}; tile_previous={}
        def observe(op,store):
            counts=N.tiled_counts(p['instructions'][op['pc']],p,position)['logical_counts']
            for primitive in ('FADD','FMUL'):
                value=m.vm.word_counts[primitive]
                assert value-previous.get(primitive,0)==counts.get(primitive+'_words',0),(op['pc'],primitive)
                previous[primitive]=value
            for key in ('code_tile_reads','code_payload_bytes','code_sectors32','BF16_pack_windows'):
                value=m.counters[key]
                assert value-tile_previous.get(key,0)==counts.get(key,0),(op['pc'],key)
                tile_previous[key]=value
        # counters are cumulative; establish each token's starting value.
        previous.update(m.vm.word_counts); tile_previous.update(m.counters)
        m.run(3,position,observe)


def test_tiled_fullshape_compiler_actual_homes_and_counts():
    n=N.compile_tiled(); p=n['source_program']
    assert n['coverage']['PCs']==1737 and len(n['coverage']['families'])==21
    assert len(n['operands'])==2027
    assert len(n['provider_binding']['version_homes'])==31232
    assert n['provider_binding_pin']['commit']==N.PROVIDER_COMMIT
    assert n['feasibility']['temporary_HBM_bytes']==0
    assert n['feasibility']['RF_workspace_vectors']==32
    assert n['feasibility']['shared_reserved_bytes']==17408<65536
    for source,op in zip(p['instructions'],n['operations']):
        assert op['provider_binding']==n['provider_binding']['operations'][op['pc']]
        assert op['reads'] and op['writes']
        if op['opcode']=='MATRIX':
            d=p['weight_descriptors'][source['attributes']['weight']]
            c=op['calendar_export']['counts_full_context']['logical_counts']
            assert c['FMUL_words']==d['rows']*d['K']
            assert c['FADD_words']==d['rows']*(d['K']+d['split']-1)
            assert c['code_payload_bytes']==d['rows']*d['K']
    assert N.canonical(n)==N.canonical(N.compile_tiled())


def test_tiled_whole36layer_no_highlevel_oracle(monkeypatch):
    m=N.TiledMachine(N.compile_tiled(compile_program(small(36),context=32,groups=16)))
    def forbidden(*a,**k): raise AssertionError('high-level oracle callback')
    monkeypatch.setattr(SoftwareGPUProvider,'execute',forbidden)
    for name in ('exp','rsqrt','reciprocal','matrix','rstd','chunk8','bf16','fp8_encode','fp8_decode'):
        monkeypatch.setattr(G,name,forbidden)
    monkeypatch.setattr(N.TileWords,'debug_snapshot',forbidden)
    for pos in range(2):
        r=m.run(3,pos)
        assert r['PCs']==1737 and r['RF_workspace_peak_vectors']<=32
        assert r['tile_counts']['code_tile_reads']>0
        assert r['transfer_counts']['RF_write_ACK']>0
        assert r['temporary_HBM_bytes']==0


def test_tiled_BF16_exception_bits_source_contract():
    bits=np.array([0,0x80000000,1,0x007fffff,0x3f808000,0x3f818000,0x7f7fffff,
                   0x7f800000,0xff800000,0x7fc00000,0x7fffffff,0xffc12345,0x7f800001],np.uint32)
    vm=N.NativePrimitiveVM()
    result=vm.run_qwen(N.tile_microcode()['bf16'],{'x':bits.view(np.float32)})
    exact(result,G.bf16(bits.view(np.float32)))


def test_tiled_provider_visibility_bounds_and_RF_mirrors():
    n=N.compile_tiled(compile_program(small(1),context=32,groups=16)); s=N.TileWords(n)
    v=next(x['version'] for x in n['operands'] if x['name']=='token')
    with pytest.raises(ValueError,match='unpublished'): s.read(v,0,1)
    s.reserve(v,0,'U32'); s.write(v,0,np.array([3],np.uint32)); s.publish(v)
    with pytest.raises(ValueError,match='aperture'): s.read(v,1,1)
    key=next(iter(s.pages)); s.pages[key][1][0]^=1
    with pytest.raises(ValueError,match='mirror'): s.read(v,0,1)
    with pytest.raises(ValueError,match='SSA'): s.reserve(v,0)


def ds_reference_machine():
    import ast
    path=N.ROOT/N.OUT/'tiled_r1/Peirce_native_76d564c9a.py.source'
    tree=ast.parse(path.read_text())
    nodes=[x for x in tree.body if isinstance(x,ast.ClassDef) and x.name=='Machine']
    ns={'np':np}; exec(compile(ast.Module(body=nodes,type_ignores=[]),str(path),'exec'),ns)
    native=next(ast.literal_eval(x.value) for x in tree.body if isinstance(x,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='NATIVE' for t in x.targets))
    return ns['Machine'],native


def test_common_ABI_every_Peirce_primitive_adapter():
    Ref,native=ds_reference_machine(); vm=N.NativePrimitiveVM()
    assert native<=N.COMMON_NATIVE
    f=np.array([1.25,-2.5,0,4],np.float32); u=np.array([1,2,3,4],np.uint32)
    cases={
      'IOTA':([],{},[4]),
      'RESHAPE':([f],{},[2,2]),'SLICE':([f],{'axis':0,'start':0,'stop':4,'step':2},[2]),
      'TRANSPOSE':([f.reshape(2,2)],{'axes':[1,0]},[2,2]),'CONCAT':([f[:2],f[2:]],{'axis':0},[4]),
      'BROADCAST':([f[:1]],{},[4]),'TAKE':([f,u[:2]],{'axis':0},[2]),
      'SCATTER':([f,np.array(2,np.int64),np.array(8,np.float32)],{'axis':0},[4]),
      'FADD':([f,f],{},[4]),'FMUL':([f,f],{},[4]),'SQRT':([np.abs(f)],{},[4]),
      'FMAX':([f,f[::-1]],{},[4]),'FMIN':([f,f[::-1]],{},[4]),
      'SELECT':([u,f,f[::-1]],{},[4]),'BITCAST_U':([f],{},[4]),'BITCAST_F':([u],{},[4]),
      'I2F':([u],{},[4]),'F2I':([f],{},[4]),'LDEXP':([f,u],{},[4]),
      'ASSERT':([u],{},[4]),'PACKET_COMMIT':([f],{'lease':'source:1','lease_state':'visible'},[4]),
    }
    for op in ('FCMP_GT','FCMP_LT','FCMP_EQ'): cases[op]=([f,f[::-1]],{},[4])
    for op in ('SHR','SHL','AND','OR','XOR','IADD','ISUB','IMUL','IMOD'): cases[op]=([u,u],{},[4])
    for op,(args,attrs,shape) in cases.items():
        code=[]; memory={}; providers={}
        for i,a in enumerate(args):
            dtype='F32' if a.dtype==np.float32 else 'I64' if a.dtype==np.int64 else 'U32'
            name='input'+str(i); memory[name]=a; providers[name]={'value':a,'lease':name,'state':'visible'}
            code.append(dict(op='LOAD',dst=name,src=[],shape=list(a.shape),attrs={'name':name,'dtype':dtype}))
        code.append(dict(op=op,dst='out',src=list(memory),shape=shape,attrs=attrs))
        p={'code':code,'outputs':{'out':'out'}}
        exact(vm.run_ds(p,providers)['out'],Ref(p,memory).run()['out'])
    for dtype,value in [('F32',f),('U32',u),('I64',u.astype(np.int64))]:
        at={'dtype':dtype,'bits':value.view(np.uint32).tolist()} if dtype=='F32' else {'dtype':dtype,'value':value.tolist()}
        p={'code':[dict(op='CONST',dst='out',src=[],shape=[4],attrs=at)],'outputs':{'out':'out'}}
        exact(vm.run_ds(p,{})['out'],Ref(p,{}).run()['out'])
    # DIV is separately covered with the explicit source restoring provider.
    assert set(cases)|{'LOAD','CONST','DIV'}==native


def test_common_ABI_rejects_missing_providers_and_illegal_semantics():
    vm=N.NativePrimitiveVM()
    for op,args in [('DIV',[np.float32(1),np.float32(3)]),('GOLDEN_MATRIX',[])]:
        with pytest.raises(ValueError): vm.primitive(op,args)
    with pytest.raises(ValueError,match='outer tile'): vm.primitive('FADD',[np.zeros(129,np.float32),np.float32(1)])
    with pytest.raises(ValueError,match='shift'): vm.primitive('SHR',[np.uint32(1),np.uint32(32)])
    with pytest.raises(ValueError,match='F2I'): vm.primitive('F2I',[np.float32(np.nan)])
    with pytest.raises(ValueError,match='NaN'): vm.primitive('FP8_UNPACK',[np.uint8(127)])
    p={'code':[dict(op='LOAD',dst='x',src=[],shape=[1],attrs={'name':'v','dtype':'F32'})],'outputs':{'x':'x'}}
    with pytest.raises(ValueError,match='lease'): vm.run_ds(p,{'v':np.array([1],np.float32)})


def test_common_DIV_restoring_provider_exception_rounding_and_DS_adapter():
    import h3_exact_scalar_contract as scalar
    Ref,_=ds_reference_machine()
    patterns=[(0x3f800000,0x40400000),(0x00800000,0x43800000),(0x80000001,0x40000000),
              (0x7f7fffff,0x3f000000),(0,0x45a00000),(0x3f800000,0),(0x7f800000,0x3f800000),
              (0x80000000,0x3f800000),(0x3f800001,0x3f800002)]
    a=np.array([x for x,y in patterns],np.uint32).view(np.float32)
    b=np.array([y for x,y in patterns],np.uint32).view(np.float32)
    values,faults=N.restoring_DIV_provider(a,b)
    expected=[scalar.div_contract(x,y) for x,y in patterns]
    np.testing.assert_array_equal(values.view(np.uint32),[x for x,y in expected])
    np.testing.assert_array_equal(faults,[y for x,y in expected])
    code=[dict(op='LOAD',dst=x,src=[],shape=[len(a)],attrs={'name':x,'dtype':'F32'}) for x in ('a','b')]
    code.append(dict(op='DIV',dst='out',src=['a','b'],shape=[len(a)],attrs={}))
    p={'code':code,'outputs':{'out':'out'}}
    vm=N.NativePrimitiveVM(div=N.restoring_DIV_provider)
    ref=Ref(p,{'a':a,'b':b},div=N.restoring_DIV_provider)
    exact(vm.run_ds(p,{x:{'value':v,'state':'visible','lease':x} for x,v in [('a',a),('b',b)]})['out'],ref.run()['out'])
    assert vm.fault and ref.fault
    assert vm.error_events==ref.error_events


def test_tiled_calendar_finite_and_costs_cannot_disappear():
    n=N.compile_tiled(compile_program(small(1),context=32,groups=16))
    calendar=N.materialize_tile_calendar(n,{k:1 for k in N.TILE_COSTS})
    assert len(calendar['operations'])==57
    assert calendar['resources']['outstanding_tiles']==1
    assert calendar['resources']['source_sector_credits_used']<=calendar['resources']['source_sector_credits_available']
    assert calendar['resources']['RF_vectors']==32
    previous=0
    for op in calendar['operations']:
        assert op['start']==previous and op['end']>op['start']
        assert all(x>0 for x in op['service_budget'].values())
        previous=op['end']
    for costs in ({},{k:0 for k in N.TILE_COSTS},{k:float('nan') for k in N.TILE_COSTS}):
        with pytest.raises(ValueError,match='positive'): N.materialize_tile_calendar(n,costs)


def test_tiled_full4096_RSTD_exact_mean_and_rounds():
    n=N.compile_tiled(); m=N.TiledMachine(n)
    op=next(o for o in n['operations'] if o['opcode']=='RSTD')
    m.position=0
    version=op['reads'][0]; x=np.resize(np.array([0.25,-0.5,1,0.00390625,2,-4,0,8],np.float32),4096)
    m.store.reserve(version,0)
    for start in range(0,4096,128): m.store.write(version,start,x[start:start+128])
    m.store.publish(version); m.execute(op)
    exact(m.store.debug_snapshot(op['writes'][0]),G.rstd(x,op['attributes']['epsilon']))
    assert m.vm.peak_vectors<=32
    assert m.vm.counts['DIV']==0
    assert np.float32(1/4096).view(np.uint32)==0x39800000


def test_tiled_matrix_rows129_K256_exact_split_tree_and_conversion():
    n=N.compile_tiled(); m=N.TiledMachine(n)
    op=next(o for o in n['operations'] if o['opcode']=='MATRIX'); out=op['writes'][0]
    m.store.reserve(out,0)
    x=np.resize(np.array([1.00390625,1e8,-1e8,-1,0.03125],np.float32),256)
    q=((np.arange(129*256).reshape(129,256)%9)-4).astype(np.int8)
    m.dot(129,256,256,lambda indexes:x[indexes],lambda r,n,k,t:q[r:r+n,k:k+t],out,0,True,True)
    m.store.publish(out)
    actual=np.concatenate([m.store.read(out,i,min(128,129-i)) for i in range(0,129,128)])
    exact(actual,G.matrix(q,G.bf16(x),256))
    assert m.vm.peak_vectors<=32 and m.peak_shared<=8192
    assert m.counters['code_tile_reads']==16
    # Interleaved K with empty source leaves, separate three-level padded tree.
    m2=N.TiledMachine(n); m2.store.reserve(out,0)
    w=q[:3,:3].astype(np.float32); y=np.array([1e8,-1e8,1],np.float32)
    m2.dot(3,3,8,lambda indexes:y[indexes],lambda r,n,kk:w[r:r+n,kk],out,0)
    m2.store.publish(out); exact(m2.store.read(out,0,3),G.matrix(w,y,8,True))


def test_tiled_raw_HBM_byte_provider_complete_program():
    p=compile_program(small(1),context=32,groups=16); native=N.compile_tiled(p)
    ext={e['provider_ref']:e for a in native['provider_binding']['allocation'] for e in a['extents']}
    raw=N.TileFixtureWeights(p); backing={}
    def put(rank,name,offset,data):
        base=ext[f'Qwen.rank{rank}.extent.{name}']['base']+offset
        for i,byte in enumerate(data): backing[rank,base+i]=byte
    for key,d in p['weight_descriptors'].items():
        prefix='head' if d['layer'] is None else f'L{d["layer"]}.{d["name"]}'
        q=raw.matrix_tile(key,0,d['rows'],0,d['K'])
        put(d['die'],prefix+'.codes',0,q.tobytes())
        put(d['die'],prefix+'.scales',0,(raw.scale_tile(key,0,d['rows']).view(np.uint32)>>16).astype('<u2').tobytes())
    for rank in range(2):
        h=p['config']['hidden_size']; hd=p['config']['head_dim']
        for token in range(p['config']['vocab_size']):
            codes,scale=raw.embedding_tile(token,0,h); put(rank,'embedding',token*h,codes.tobytes())
            put(rank,'embedding',p['config']['vocab_size']*h+2*token,np.array([int(scale.view(np.uint32))>>16],'<u2').tobytes())
        put(rank,'L0.qk_norm',0,np.full(2*hd,0x3f80,dtype='<u2').tobytes())
        put(rank,'final_norm',0,np.full(h,0x3f80,dtype='<u2').tobytes())
        for pos in range(2):
            co,si=raw.rope_tile(pos,p['config']['rope_theta'],0,hd//2)
            put(rank,'rope_table',4*pos*hd,np.concatenate([co,si]).astype('<f4').tobytes())
    class Backend:
        def read_tile_bytes(self,record):
            rank=int(record['provider_ref'].split('.')[1][4:])
            return dict(provider_ref=record['provider_ref'],lease=record['lease'],state='visible',reverse_grant_ACK=True,
                        payloads=[bytes(backing[rank,r['address']+i] for i in range(r['bytes'])) for r in record['byte_ranges']])
    actual=N.TiledMachine(native,N.HBMByteTileProvider(Backend())); expected=N.TiledMachine(native)
    for pos in range(2): assert actual.run(3,pos)['next_token']==expected.run(3,pos)['next_token']
    assert actual.counters['immutable_HBM_sectors32']>0
    bad=copy.deepcopy(native); first=bad['operations'][0]; first['provider_binding']['external_providers']=[]
    with pytest.raises(ValueError,match='unbound external'): N.TiledMachine(bad).run(3,0)


def test_common_extra_primitives_FP8_all_finite_codes_and_signed_integer():
    vm=N.NativePrimitiveVM()
    for sign in (0,128):
        codes=(np.arange(127,dtype=np.uint8)|sign)
        values=vm.primitive('FP8_UNPACK',[codes])
        encoded=vm.primitive('FP8_PACK',[values])
        expected=codes.copy(); expected[0]=0
        np.testing.assert_array_equal(encoded,expected)
    np.testing.assert_array_equal(vm.primitive('FCMP_NE',[np.array([np.nan,1],np.float32),np.array([np.nan,1],np.float32)]),[1,0])
    np.testing.assert_array_equal(vm.primitive('SHR',[np.array([-8,8],np.int64),np.array([2,2],np.int64)]),[-2,2])


def test_tiled_physical_export_all_primitives_matches_runtime_per_PC():
    p=compile_program(small(1),context=32,groups=16); m=N.TiledMachine(N.compile_tiled(p)); previous={}
    def observe(op,store):
        expected=N.physical_tile_export(p['instructions'][op['pc']],p,0)['native_primitive_commands']
        actual={k:v-previous.get(k,0) for k,v in m.vm.counts.items() if v!=previous.get(k,0)}
        assert actual==expected,(op['pc'],actual,expected)
        previous.update(m.vm.counts)
    m.run(3,0,observe)
    for profile in N.tile_kernel_ABI().values():
        for step in profile['steps']:
            assert step['native_steps'] and step['reads']
            assert np.prod(step['write']['shape_max'])<=128
            assert step['write']['RF_vectors_max']<=2


def test_common_adapter_fault_suppresses_packet_and_oversize_IOTA():
    vm=N.NativePrimitiveVM()
    vm.primitive('LDEXP',[np.float32(1),np.uint32(1024)])
    assert vm.fault
    with pytest.raises(ValueError,match='publication'): vm.primitive('PACKET_COMMIT',[np.float32(1)])
    with pytest.raises(ValueError,match='IOTA'): N.NativePrimitiveVM().primitive('IOTA',[],shape=[129])


def test_sector_and_interleaved_cache_counts_do_not_assume_alignment():
    sectors=0
    for r in range(0,129,128):
        for k in range(0,48,32):
            touched=set()
            for row in range(r,min(129,r+128)):
                touched.update(range((row*48+k)//32,(row*48+k+min(32,48-k)-1)//32+1))
            sectors+=len(touched)
    assert N.code_sector_count(129,48)==sectors
    assert N.interleaved_BF16_windows(256,16)==32


def test_tiled_packed_KV_state_checks_actual_r17_extent_bytes():
    n=N.compile_tiled(compile_program(small(1),context=32,groups=16)); m=N.TiledMachine(n)
    m.run(3,0)
    memory=m.memory; assert isinstance(memory,N.BoundKVStorage)
    assert memory.bit(0,0,0) and memory.bit(0,1,0)
    assert (memory.record(0,0)>>88)&3==3
    assert (memory.record(0,0)>>90)&3==3
    state=memory.state[0]; memory.bytes[0,state['base']]=0
    with pytest.raises(ValueError,match='prefix'): memory.acquire({'key':(0,0,0),'tag':0},0,0,0)
    assert memory.counters['state_write_sectors32']>0
    assert memory.counters['state_read_sectors32']>0


def test_tiled_actual_r17_full_context_spill_home_retires_byte_backing():
    n=N.compile_tiled(); s=N.TileWords(n)
    operand=next(v for v in n['operands'] if any(h.get('home',{}).get('class')=='spill' for h in v['homes']))
    version=operand['version']; s.reserve(version,8191)
    values=np.arange(128,dtype=np.float32)
    s.write(version,0,values); s.publish(version)
    exact(s.read(version,0,128),values)
    assert any(k[0]=='HBM' for k in s.pages)
    assert s.counters['HBM_read_sectors32']==16
    assert s.counters['HBM_write_sectors32']==16
    assert s.counters['NoC_source_write_bits']==0
    s.retire(operand['retire_pc'])
    assert not s.live and not s.owners and not s.pages and not s.published
