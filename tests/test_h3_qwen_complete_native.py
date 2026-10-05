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
