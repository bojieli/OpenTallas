"""Real Device gates; miniature datapath fixtures are not full DS inference."""
from pathlib import Path
import hashlib
import struct
import pytest
import numpy as np
from runtime.abi3.builder import DeploymentBuilder, DynamicTerm
from runtime.abi3.constants import (Major, Tensor, Selection, Dma, State, StateClass,
    Control, DType, Permission, StorageClass, TopologyClass, CompletionStatus)
from runtime.abi3.descriptors import Phase, Symbol
from runtime.abi3.deployment import ObjectSource, Segment
from runtime.abi3.fixture import fixture_capability
from runtime.sim.device import Device
import runtime.sim.engines.dma
import runtime.sim.engines.tensor
import runtime.sim.engines.selection
from runtime.requests.ds_v41_generation import ingest_and_generate
from compiler.backends.hbm_sram.request_generation import publication_predicate, validate_publication_dependencies


def fixture(tmp_path, *, eos=3, corrupt=False, corrupt_row=None):
    cap = fixture_capability()
    cap.limits['max_context_positions'] = 16
    b = DeploymentBuilder(target_id='handoff', model_id='handoff-fixture', backend='test', capability=cap)
    b.topology(topology_class=TopologyClass.SINGLE_CHIP, node_count=1)
    rw = int(Permission.READ | Permission.WRITE)
    def obj(n, storage=StorageClass.HBM):
        return b.memory_object(storage_class=storage, size_bytes=n,
            source=ObjectSource.zeros(n), permissions=rw)
    host, committed, prepared, logits, selected, ring = obj(64,StorageClass.HOST),obj(64),obj(64),obj(8),obj(4),obj(64,StorageClass.HOST)
    # BF16 lookup rows are concrete fixture weights. Rows0/1 choose2, row2
    # chooses0, row3 ties at1/2 (lowest ID1), row4 chooses EOS3.
    words = np.asarray([[0,0,0x4000,0], [0,0,0x4000,0],
        [0x4040,0,0,0], [0,0x4080,0x4080,0],
        [0,0,0,0x40a0], [0x7fc0 if corrupt else 0,0,0,0],
        [0,0,0x4000,0], [0,0,0x4000,0]], dtype=np.uint16)
    if corrupt_row is not None:
        words[corrupt_row,0] = 0x7fc0
    data=words.tobytes(); (tmp_path/'lookup.bin').write_bytes(data)
    source=ObjectSource('segments',len(data),(Segment('lookup.bin',0,len(data),hashlib.sha256(data).hexdigest()),))
    weight=b.memory_object(storage_class=StorageClass.HBM,size_bytes=len(data),
        source=source,permissions=int(Permission.READ|Permission.IMMUTABLE),
        content_digest=source.authenticated_content_digest())
    def view(oid,dtype,dims,**kw):
        return b.tensor_view(object_id=oid,dtype=dtype,dims=dims,permissions=rw if oid!=weight else int(Permission.READ),**kw)
    # Fixture makes one scalar transfer per input token using a symbol loop.
    row=b.loop_control(lower_bound=0,upper_bound=4,step=1,bound_symbol=Symbol.SPAN_TOKENS,max_iterations=4)
    inrow=view(host,DType.U32,[1],dynamic=[DynamicTerm.loop(row,1)])
    # REQUEST_SPAN stages at prepared row0; Device publishes at committed
    # cursor. This is distinct from a SATURATING/direct circular source cache.
    outrow=view(prepared,DType.U32,[1],dynamic=[DynamicTerm.loop(row,1)])
    last=view(host,DType.U32,[1],dynamic=[DynamicTerm.symbol(Symbol.SPAN_LAST_INDEX,1)])
    table=view(weight,DType.BF16,[8,4])
    logitview=view(logits,DType.BF16,[1,4])
    tokenview=view(selected,DType.U32,[1])
    ringview=view(ring,DType.U32,[1],dynamic=[DynamicTerm.symbol(Symbol.GENERATION_INDEX,1)])
    state=b.state(state_class=StateClass.KV_CACHE,committed_object_id=committed,
        prepared_object_id=prepared,row_bytes=4,capacity_rows=16,element_dtype=DType.U32)
    policy=b.generation_policy(eos_token_ids=[eos],max_new_tokens=8,vocabulary_size=4,token_ring_object_id=ring)
    def op(major,sub,inputs,outputs):
        schedule=b.schedule(engine_family=major,tile_rows=1,tile_cols=4,tile_depth=1,bank_mask=1,max_outstanding=1)
        return b.operator(engine_family=major,engine_sub=sub,inputs=inputs,outputs=outputs,schedule_id=schedule)
    transfer=op(Major.DMA,Dma.TRANSFER,[inrow],[outrow])
    lookup=op(Major.TENSOR,Tensor.EMBED_LOOKUP,[last,table],[logitview])
    argmax=op(Major.SELECTION,Selection.ARGMAX,[logitview],[tokenview])
    append=op(Major.SELECTION,Selection.TOKEN_APPEND,[tokenview],[ringview])
    gate=publication_predicate(b)
    b.emit(Major.STATE,State.PREPARE,descriptor_id=state)
    b.open_loop(row);b.emit(Major.DMA,Dma.TRANSFER,descriptor_id=transfer);b.close_loop()
    b.emit(Major.TENSOR,Tensor.EMBED_LOOKUP,descriptor_id=lookup)
    selected_event=b.new_event();b.emit(Major.SELECTION,Selection.ARGMAX,descriptor_id=argmax,signal_event_id=selected_event)
    fence=b.new_event();b.emit(Major.CONTROL,Control.FENCE,wait_set_id=b.wait_set([selected_event]),signal_event_id=fence)
    b.emit(Major.SELECTION,Selection.TOKEN_APPEND,descriptor_id=append,
        predicate_id=gate,wait_set_id=b.wait_set([fence]),signal_event_id=b.new_event())
    b.emit(Major.STATE,State.COMMIT,descriptor_id=state)
    b.emit(Major.CONTROL,Control.COMPLETE)
    for n,phase in enumerate((Phase.PREFILL,Phase.DECODE)):
        b.entrypoint(entrypoint_id=n,first_instruction=0,phase=phase,generation_policy_id=policy)
    b.notes['shared_prompt_generation']={'schema':'ds-v41.shared-request.r1'}
    b.notes['request_runtime']={'query_rows':4,'context_capacity':16,'input_token_object_id':host}
    deployment=b.finish()
    return Device(deployment,cap,root=tmp_path,trace=True), committed, state


def test_real_device_shared_state_last_logits_and_unprocessed_final_token(tmp_path):
    device,kv,state=fixture(tmp_path)
    session=device.create_session(); memory=device.memory; resource=session.states[state]
    result=ingest_and_generate(device,session,[1,0,1,0,1,3],max_new_tokens=3)
    assert all(r.status==CompletionStatus.SUCCESS for r in result.receipts)
    assert result.prompt_committed and result.generated_tokens==(1,2,0)
    assert [r.produced_tokens for r in result.receipts]==[(),(),(1,),(2,),(0,)]
    assert session.position==8 and resource.cursor_rows==8
    assert device.memory is memory and session.states[state] is resource
    assert struct.unpack('<8I',memory[kv].read(0,32))==(1,0,1,0,1,3,1,2)
    assert memory[kv].read(32,4)==bytes(4) # token0 was published, not consumed
    assert sum(r.counters.get('tensor.embedding_rows',0) for r in result.receipts)==5


@pytest.mark.parametrize('prompt', [[4], [0,0,0,0,4]])
def test_real_device_final_prompt_eos_stops_without_extra_forward(tmp_path,prompt):
    device,kv,state=fixture(tmp_path);session=device.create_session()
    result=ingest_and_generate(device,session,prompt,max_new_tokens=4)
    assert result.generated_tokens==(3,) and session.finished
    assert session.position==len(prompt) and session.states[state].cursor_rows==len(prompt)
    assert device.memory[kv].read(4*len(prompt),4)==bytes(4)


def test_real_device_numeric_fault_stops_without_sampling_or_state_commit(tmp_path):
    device,kv,state=fixture(tmp_path,corrupt=True);session=device.create_session()
    result=ingest_and_generate(device,session,[0,0,0,0,5],max_new_tokens=2)
    assert not result.prompt_committed and result.generated_tokens==()
    assert len(result.receipts)==2 and result.receipts[-1].status==CompletionStatus.FAILED
    assert session.position==4 and session.states[state].cursor_rows==4


def test_publication_event_consumer_refuses(tmp_path):
    device,_,_=fixture(tmp_path)
    from runtime.abi3.records import decode_body,split_program
    from runtime.abi3.constants import NO_ID
    _,body=split_program(device.deployment.program)
    append=next(i for i in decode_body(body) if i.major==int(Major.SELECTION) and i.sub==int(Selection.TOKEN_APPEND))
    # Existing wait descriptor is mutated solely as a negative validator input.
    from runtime.abi3.descriptors import ExtendedDescriptorType
    wait=next(d for d in device.deployment.table.descriptors()
        if d.descriptor_type==ExtendedDescriptorType.EVENT_WAIT_SET)
    wait.payload['producer_0']=append.signal_event_id
    with pytest.raises(ValueError,match='strand'):
        validate_publication_dependencies(device.deployment)


@pytest.mark.parametrize('budget',[0,9,True])
def test_real_device_refuses_invalid_budget_before_input_or_state(tmp_path,budget):
    device,_,_=fixture(tmp_path);session=device.create_session()
    with pytest.raises(ValueError,match='budget'):
        ingest_and_generate(device,session,[1],max_new_tokens=budget)
    assert session.position==0 and not session.generated


def test_real_device_generation_fault_preserves_prompt_and_prior_publication(tmp_path):
    device,kv,state=fixture(tmp_path,corrupt_row=2);session=device.create_session()
    result=ingest_and_generate(device,session,[1],max_new_tokens=3)
    assert result.prompt_committed and result.generated_tokens==(2,)
    assert len(result.receipts)==2 and result.receipts[-1].status==CompletionStatus.FAILED
    assert session.position==1 and session.states[state].cursor_rows==1
    assert device.memory[kv].read(0,8)==struct.pack('<II',1,0)


def test_real_device_isolated_session_state_is_not_migrated_or_shared(tmp_path):
    device,kv,state=fixture(tmp_path)
    first,second=device.create_batch_sessions(2)
    memories,views=device._session_address_space(first)
    sibling,_=device._session_address_space(second)
    result=ingest_and_generate(device,first,[3],max_new_tokens=2)
    assert result.generated_tokens==(1,2) and first.position==2
    assert second.position==0 and second.states[state].cursor_rows==0
    assert memories[0][kv].read(0,8)==struct.pack('<II',3,1)
    assert sibling[0][kv].read(0,8)==bytes(8)
    actual,actual_views=device._session_address_space(first)
    assert actual is memories and actual_views is views


def test_intermediate_prompt_argmax_eos_is_not_published_or_stopping(tmp_path):
    device,_,state=fixture(tmp_path);session=device.create_session()
    result=ingest_and_generate(device,session,[4,4,4,4,3],max_new_tokens=1)
    assert result.receipts[0].selected_token==3
    assert result.receipts[0].produced_tokens==()
    assert result.generated_tokens==(1,) and len(result.receipts)==2
    assert session.position==5 and session.states[state].cursor_rows==5


def test_actual_released_graph_artifact_layout_and_last_position_binding(tmp_path):
    import gzip,json
    from runtime.abi3.deployment import Deployment
    from runtime.abi3.capability import Capability
    from runtime.abi3.verifier import verify_deployment
    from runtime.abi3.descriptors import ExtendedDescriptorType,SelectorKind
    root=Path(__file__).resolve().parents[2]
    archive=root/'results/abi3/ds_v41_generation_handoff_20261003/shared32'
    manifest=json.loads((archive/'archive_manifest.json').read_text())
    for name,entry in manifest.items():
        payload=(archive/entry['archive']).read_bytes()
        assert hashlib.sha256(payload).hexdigest()==entry['archive_sha256']
        if entry['archive'].endswith('.gz'):
            payload=gzip.decompress(payload)
        assert hashlib.sha256(payload).hexdigest()==entry['sha256']
        (tmp_path/name).write_bytes(payload)
    deployment=Deployment.read(tmp_path)
    cap=Capability.from_dict(json.loads((root/'results/abi3/ds_v41_request_runtime_20261003/capability_comparator.json').read_text()))
    assert verify_deployment(deployment,cap).admitted
    assert validate_publication_dependencies(deployment)['state_layout_migrations']==0
    graph=json.loads((tmp_path/'request_graph.json').read_text())
    assert len(graph['kernels'])==3250
    last_position=[k for k in graph['kernels'] if k['kind']=='LAST_TOKEN_SELECT']
    assert len(last_position)==1
    kernel=last_position[0]['index']
    select=next(d for d in deployment.table.descriptors()
        if d.descriptor_type==ExtendedDescriptorType.OPERATOR
        and d.payload['source_kernel_id']==kernel)
    index=deployment.table[select.payload['input_view_0']].payload
    assert index['dynamic_term_count']==1
    assert index['term0_kind']==int(SelectorKind.RUNTIME_SYMBOL)
    assert index['term0_index']==int(Symbol.SPAN_LAST_INDEX) and index['term0_stride']==1
    plan=json.loads((tmp_path/'physical_plan.json').read_text())
    assert plan['proofs']['layers_covered']==40 and plan['span_max']==32
    assert plan['proofs']['hbm_fits'] and plan['proofs']['sram_fits']


@pytest.mark.parametrize('length,budget',[(15,1),(16,0)])
def test_released_context_clip_counts_unprocessed_output_position(tmp_path,length,budget):
    device,_,state=fixture(tmp_path);session=device.create_session()
    result=ingest_and_generate(device,session,[1]*length,max_new_tokens=8)
    assert result.prompt_committed and result.effective_new_token_budget==budget
    assert len(result.generated_tokens)==budget and result.context_exhausted
    assert session.position==length and session.states[state].cursor_rows==length
    assert all(r.status==CompletionStatus.SUCCESS for r in result.receipts)
