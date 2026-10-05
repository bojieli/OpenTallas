import gzip
import json
from pathlib import Path
from types import SimpleNamespace
import pytest
from compiler.ir.v3.kernel_ir import KernelGraph, check_neutral
from compiler.frontends.v3.deepseek_v41_request_r2 import specialize_request, prompt_ingestion_graph
from compiler.backends.hbm_sram import plan as baseline
from compiler.backends.hbm_sram.request_plan_r2 import _planner
from runtime.requests.ds_v41_prompt import ingest_prompt

ROOT=Path(__file__).resolve().parents[2]

@pytest.fixture(scope='module')
def released():
    return KernelGraph.from_dict(json.loads(gzip.decompress((ROOT/'results/abi3/ds_v41_request_runtime_20261003/released_graph.json.gz').read_bytes())))

@pytest.mark.parametrize('phase,rows',[('decode',1),('prefill',32)])
def test_actual_released_graph_neutral_and_mask_binding(released,phase,rows):
    graph=specialize_request(released,phase=phase,prefill_chunk_tokens=rows if phase=='prefill' else None)
    assert not check_neutral(graph)
    assert len(graph.kernels)==3250
    tensors={t.tensor_id:t for t in graph.tensors}
    bands,_=baseline._build_bands(graph,tensors)
    _,_,band_of=baseline._emission_order(graph,bands)
    states,state_map,_=baseline._place_states(graph,bands,band_of,rows)
    bindings=baseline._bind_state_tensors(graph,tensors,state_map)
    masks=[s for s in graph.states if s.state_id.startswith('candidate_pool_mask.')]
    assert masks and all(s.capacity_rows==rows for s in masks)
    selections=[s for s in graph.states if s.state_id.startswith('index_selection.')]
    assert selections and all(s.capacity_rows==rows for s in selections)
    for kernel in graph.kernels:
        if kernel.kind=='CANDIDATE_MASK':
            assert kernel.attributes.get('committed_row')!='absolute_position'
            expected=state_map[kernel.state_writes[0]]
            assert bindings[kernel.outputs[0]][:2]==expected
            assert bindings[kernel.outputs[0]][2]==0
        if kernel.kind=='STATE_READ' and any(s.startswith('candidate_pool_mask.') for s in kernel.state_reads):
            assert bindings[kernel.outputs[0]]==bindings[kernel.inputs[0]]
    # Private request namespace validates context against retained capacity.
    scope=_planner(262144).__globals__
    for tensor in graph.tensors:
        if tensor.shape and isinstance(tensor.shape[0],baseline.Symbolic) and tensor.shape[0].symbol=='context_length':
            scope['request_extent_of'](tensor,rows)
    assert baseline.request_extent_of is not scope['request_extent_of']


def test_actual_prompt_forward_preserves_all_non_sampling_work(released):
    graph=specialize_request(released,phase='prefill',prefill_chunk_tokens=32)
    prompt=prompt_ingestion_graph(graph)
    assert not check_neutral(prompt)
    assert len(prompt.kernels)==3247
    original=[k for k in graph.kernels if k.attributes.get('source_operation_kind')!='SAMPLE']
    for old,new in zip(original,prompt.kernels):
        assert old.to_dict() | {'index':new.index} == new.to_dict()
    assert prompt.states==graph.states
    assert not prompt.generation_policy
    assert not any(k.kind=='TOKEN_APPEND' for k in prompt.kernels)


class ProtocolDevice:
    """Protocol-only spy; no numerical/runtime qualification is inferred."""
    def __init__(self,fail_at=None):
        self.deployment=SimpleNamespace(notes={'request_runtime':{'prompt_ingestion_only':True,'context_capacity':64,'query_rows':4,'input_token_object_id':7}})
        self._entrypoints={0:{'phase':0},1:{'phase':1}}
        self.calls=[];self.payload=None;self.payloads=[];self.fail_at=fail_at
    def _session_address_space(self,session):
        def write(offset,data):
            assert offset==0
            self.payload=data
            self.payloads.append(data)
        return ({7:SimpleNamespace(write=write)},),()
    def run_transaction(self,session,*,entrypoint_id,symbols):
        self.calls.append((entrypoint_id,dict(symbols)))
        fail=len(self.calls)==self.fail_at
        if not fail: session.position=symbols[2]
        return SimpleNamespace(status=int(fail),produced_tokens=())


def test_driver_causal_schedule_retains_session_and_never_resets():
    dev=ProtocolDevice();session=SimpleNamespace(position=0,finished=False,generated=[])
    result=ingest_prompt(dev,session,range(7))
    assert len(result)==4 and session.position==7
    assert [(e,s[0],s[1],s[2],s[3]) for e,s in dev.calls]==[(0,4,0,4,4),(1,1,4,5,5),(1,1,5,6,6),(1,1,6,7,7)]
    assert len(dev.payload)==4 and not session.generated
    import struct
    assert [struct.unpack('<'+'I'*(len(b)//4),b) for b in dev.payloads]==[(0,1,2,3),(4,),(5,),(6,)]


def test_driver_stops_on_actual_transaction_failure():
    dev=ProtocolDevice(fail_at=2);session=SimpleNamespace(position=0,finished=False,generated=[])
    result=ingest_prompt(dev,session,range(7))
    assert len(result)==2 and result[-1].status==1 and session.position==4


def test_driver_refuses_generation_program_and_nonfresh_state():
    dev=ProtocolDevice();session=SimpleNamespace(position=1,finished=False,generated=[])
    with pytest.raises(ValueError,match='fresh'): ingest_prompt(dev,session,range(7))
    dev.deployment.notes['request_runtime']['prompt_ingestion_only']=False
    with pytest.raises(ValueError,match='source-compiled'): ingest_prompt(dev,session,range(7))


def test_actual_emitter_resolves_retained_context_independently(released):
    from compiler.backends.hbm_sram.request_deployment import _emitter_class
    from compiler.backends.hbm_sram import lower as lowering
    graph=specialize_request(released,phase='decode')
    tensors={t.tensor_id:t for t in graph.tensors}
    name='main.layer02.attention.compressed_view.valid'
    original=lowering.join_extent_under
    emitter=_emitter_class(262144)
    repaired=emitter.__init__.__globals__['join_extent_under']
    repaired(tensors,[name],0,1,{},{})
    assert lowering.join_extent_under is original
    assert repaired is not original


def test_actual_phase_split_gather_is_charged_for_retained_prefix(released):
    graph=specialize_request(released,phase='decode')
    tensors={t.tensor_id:t for t in graph.tensors}
    producers={name:k for k in graph.kernels for name in k.outputs}
    plans=[]
    for kernel in graph.kernels:
        if kernel.kind!='ATTENTION_SPARSE':
            continue
        for name in kernel.inputs:
            source=producers.get(name)
            if source and 'phase_inputs' in source.attributes:
                tensor=tensors[name]
                kv=SimpleNamespace(direction='in',slot=1,tensor_id=name,
                    tile_rows=1,tile_cols=int(tensor.shape[-1]),dtype=tensor.dtype)
                plans.append(SimpleNamespace(link_class='sparse_gather',operands=(kv,)))
    assert plans
    scope=_planner(262144,graph=graph).__globals__
    charged=scope['_communication_scratch_bytes'](plans,64)
    assert charged==536870912
    # Both emitted phase paths share one physical pool. This conservatively
    # reserves the encoded prefix at the retained context maximum, including
    # the prefill span+span path, rather than hiding it behind query-sized cost.
    assert charged > baseline._communication_scratch_bytes(plans,64)


def test_actual_phase_join_backing_arena_covers_emitted_context(released):
    graph=specialize_request(released,phase='decode')
    tensors={t.tensor_id:t for t in graph.tensors}
    bands,_=baseline._build_bands(graph,tensors)
    units,body_position,band_of=baseline._emission_order(graph,bands)
    states,state_map,_=baseline._place_states(graph,bands,band_of,1)
    bindings=baseline._bind_state_tensors(graph,tensors,state_map)
    stream,rolling=baseline._streaming_schedule(graph,tensors,body_position,band_of,1,1)
    scope=_planner(262144,graph=graph).__globals__
    keys,arenas,arena_of,_=scope['_place_activations'](
        graph,tensors,bands,units,body_position,band_of,1,1,bindings,rolling,True)
    by_slot={a.slot_id:a for a in arenas}
    covered=[]
    for kernel in graph.kernels:
        if 'phase_inputs' not in kernel.attributes:
            continue
        for name in kernel.outputs:
            slot=arena_of.get(keys.get(name))
            if slot and tensors[name].dtype=='bf16' and int(tensors[name].shape[-1])==512:
                covered.append(by_slot[slot].size_bytes)
    assert covered and max(covered)>=268566528
    assert sum(a.size_bytes for a in arenas)>12752300


def test_actual_ring_table_reserves_source_modulus_headroom(released):
    graph=specialize_request(released,phase='decode')
    scope=_planner(262144,graph=graph).__globals__
    constants=scope['_generated_constants'](graph,262144,headroom=64)
    modulus=max(baseline.ring_moduli(graph))
    rings=[c for c in constants if c.tensor_id==f'{baseline.RING_INDEX_PREFIX}{modulus}']
    assert len(rings)==1
    assert rings[0].size_bytes>=4*(262144+modulus)


@pytest.fixture(scope='module')
def compiled(tmp_path_factory):
    """Actual emitted artifacts, not a reduced replacement graph."""
    from runtime.abi3.deployment import Deployment
    result = {}
    for name in ('decode', 'prompt32'):
        source = ROOT/'results/abi3/ds_v41_request_runtime_20261003'/name
        target = tmp_path_factory.mktemp(name)
        manifest = json.loads((source/'archive_manifest.json').read_text())
        import hashlib
        for filename, entry in manifest.items():
            data = (source/entry['archive']).read_bytes()
            assert hashlib.sha256(data).hexdigest() == entry['archive_sha256']
            if entry['archive'].endswith('.gz'):
                data = gzip.decompress(data)
            assert hashlib.sha256(data).hexdigest() == entry['sha256']
            (target/filename).write_bytes(data)
        result[name] = Deployment.read(target)
    return result


@pytest.mark.parametrize('name', ['decode', 'prompt32'])
def test_actual_compiled_program_independent_admission(compiled, name):
    from runtime.abi3.capability import Capability
    from runtime.abi3.verifier import verify_deployment
    from compiler.backends.hbm_sram.check import check_deployment
    deployment = compiled[name]
    graph = KernelGraph.read(deployment.root/'request_graph.json')
    cap = Capability.from_dict(json.loads((ROOT/'results/abi3/ds_v41_request_runtime_20261003/capability_comparator.json').read_text()))
    assert verify_deployment(deployment, cap).admitted
    assert check_deployment(graph, deployment, cap)['ok']
    plan = json.loads((deployment.root/'physical_plan.json').read_text())
    assert plan['span_max'] == (1 if name == 'decode' else 32)
    assert plan['proofs']['hbm_fits'] and plan['proofs']['host_resident_fits']
    assert plan['proofs']['communication_scratch_bytes'] == 536870912


def test_actual_emitted_mask_addresses_across_later_query_positions(compiled):
    """Execute the actual mask operator and read through its emitted consumer.

    Only the selected operator's declared zero-backed objects are allocated.
    Selection IDs are external test stimuli, not model numerical results. This
    checks physical addressing/reuse, not full checkpoint or transaction commit.
    """
    import numpy as np
    from runtime.abi3.constants import Major, Route
    from runtime.abi3.descriptors import ExtendedDescriptorType, Symbol, Phase
    from runtime.sim.memory import MemoryObject, ViewResolver
    from runtime.sim.engine import EngineContext, dispatch
    from runtime.sim.counters import CounterSet
    import runtime.sim.engines.route  # register the actual operator
    deployment = compiled['decode']
    table = deployment.table
    writer = next(d for d in table.descriptors()
        if d.descriptor_type == ExtendedDescriptorType.OPERATOR
        and d.payload['engine_family'] == int(Major.ROUTE)
        and d.payload['engine_sub'] == int(Route.CANDIDATE_MASK))
    output = table[writer.payload['output_view_0']]
    reader = next(table[d.payload['input_view_3']] for d in table.descriptors()
        if d.descriptor_type == ExtendedDescriptorType.OPERATOR
        and d.payload['engine_family'] == int(Major.ROUTE)
        and d.payload['engine_sub'] == int(Route.INDEX_TOPK)
        and d.payload['input_view_3'] != 0xffffffff
        and table[d.payload['input_view_3']].primary_object_id == output.primary_object_id
        and table[d.payload['input_view_3']].payload['element_offset'] == output.payload['element_offset'])
    view_ids = [writer.payload['input_view_0'], writer.payload['output_view_0'], reader.descriptor_id]
    objects = {}
    for view in view_ids:
        oid = table[view].primary_object_id
        assert deployment.objects[oid].kind == 'zero'
        objects[oid] = MemoryObject(oid, table[oid], deployment.objects[oid], deployment.root)
    views = ViewResolver(deployment, objects)
    loops = {table[v].payload[f'term{i}_index']: 0 for v in view_ids
             for i in range(table[v].payload['dynamic_term_count'])}
    context = EngineContext(table, objects, views, CounterSet(), loops, {})
    for position, block_id in ((9, 1), (100000, 2)):
        context.symbols.update({int(Symbol.SPAN_TOKENS): 1,
            int(Symbol.POSITION_START): position, int(Symbol.CONTEXT_LENGTH): position+1,
            int(Symbol.PHASE): int(Phase.DECODE)})
        ids = context.input_view(writer, 0)
        values = np.full(ids.dims, 0xffffffff, dtype=np.uint32)
        values.flat[0] = block_id
        context.write(ids, values)
        dispatch(context, int(Major.ROUTE), int(Route.CANDIDATE_MASK), writer)
        written = context.output_view(writer)
        consumed = context.view(reader.descriptor_id)
        assert written.object_id == consumed.object_id
        assert written.element_offset == consumed.element_offset
        expected = np.zeros(written.dims, dtype=np.uint8)
        expected[:, block_id*8:(block_id+1)*8] = 1
        expected[:, -8:] = 1
        assert np.array_equal(context.read(consumed), expected)
