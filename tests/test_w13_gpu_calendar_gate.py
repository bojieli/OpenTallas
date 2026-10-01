import importlib.util
import pytest,subprocess,json,hashlib
from pathlib import Path
s=importlib.util.spec_from_file_location('gate',Path(__file__).resolve().parents[1]/'tools/w13_gpu_calendar_gate.py');g=importlib.util.module_from_spec(s);s.loader.exec_module(g)


PINS={};REPO=None
@pytest.fixture(scope='module',autouse=True)
def source_graphs(tmp_path_factory):
    global REPO
    REPO=tmp_path_factory.mktemp('authoritative-graphs')
    subprocess.run(['git','init','-q',str(REPO)],check=True)
    subprocess.run(['git','-C',str(REPO),'config','user.email','test@example.invalid'],check=True)
    subprocess.run(['git','-C',str(REPO),'config','user.name','test'],check=True)
    for name,ops in [('one',[{'id':0,'dependencies':[]}]),('two',[{'id':0,'dependencies':[]},{'id':1,'dependencies':[]}]),('dependency',[{'id':0,'dependencies':[]},{'id':1,'dependencies':[0]}])]:
        (REPO/(name+'.json')).write_text(json.dumps({'instructions':ops}))
    (REPO/'actual_callbacks.json').write_text(json.dumps({'trace':[{'id':0,'dependencies':[],'cycles':None,'provider_kind':'software_functional_unqualified'}],'memory_events':[{'event':'software_consumer_done','cycles':None}]}))
    subprocess.run(['git','-C',str(REPO),'add','one.json','two.json','dependency.json','actual_callbacks.json'],check=True)
    subprocess.run(['git','-C',str(REPO),'commit','-qm','authoritative graph test fixtures'],check=True)
    rev=subprocess.check_output(['git','-C',str(REPO),'rev-parse','HEAD'],text=True).strip()
    for name in ['one','two','dependency','actual_callbacks']:
        PINS[name]=dict(source_git=rev,path=name+'.json',sha256=hashlib.sha256((REPO/(name+'.json')).read_bytes()).hexdigest())


def run(ids,instructions,edges,lowerings):
    return g.audit(PINS['one' if ids==[0] else 'two'],instructions,edges,lowerings,repo=REPO)


def lowering():
    return {'0':{k:True for k in ['ordinary_lowering_complete','issue_RF_calendar_complete','shared_bank_map_complete','fabric_edge_calendar_complete','SFU_lowering_complete']}}


def ins(**kw):
    e=dict(graph_op=0,sm=0,partition=0,opcode='FADD',rf_read_tick=0,issue_tick=8,finish_tick=36,RF_read_bits=2048,RF_write_bits=1024,peak_registers=32,producer_visible_ticks=[0]);e.update(kw);return e


def edge(**kw):
    e=dict(graph_op=0,quadrant=0,lane=0,launch_tick=0,accept_tick=159,consumer_done_tick=160,credit_return_tick=345,service_tick=159,payload_bytes=32,packet_bits=320,direction='write',phase='write_commit',write_visible_tick=159);e.update(kw);return e


def test_valid_candidate_has_no_hardware_or_speed_credit():
    l=lowering();l['0'].update(required_instruction_events=1,required_fabric_events=1,dependencies=[]);j=run([0],[ins()],[edge()],l);assert j['modeled_service_calendar_closed'] and not j['physical_build_ready'] and j['speed_credit']==0


def test_missing_fullprogram_binding_and_SFU_failclosed():
    assert not run([0,1],[ins()],[],lowering())['modeled_service_calendar_closed']
    assert 'unbound_opcode:EXP' in run([0],[ins(opcode='EXP')],[],lowering())['issues']


def test_RF_dependency_writeback_and_DIV_contention():
    assert 'dependency_before_RF_visible' in run([0],[ins(producer_visible_ticks=[4])],[],lowering())['issues']
    assert 'partition_writeback_overbooked' in run([0],[ins(),ins(rf_read_tick=4,issue_tick=12)],[],lowering())['issues']
    events=[ins(opcode='DIV',partition=p,finish_tick=84,active_lanes=1) for p in (0,1)]
    assert 'single_scalar_DIV_overbooked' in run([0],events,[],lowering())['issues']


def test_real_shared_bank_conflicts_and_combined_service_limit():
    j=run([0],[ins(opcode='LOAD',finish_tick=16,shared_read_words=[0,32])],[],lowering())
    assert 'shared_bank_port_overbooked' in j['issues']
    events=[edge(lane=i) for i in range(24)]
    assert 'combined_service_750B_overbooked' in run([0],[ins()],events,lowering())['issues']


def test_credit_may_not_return_before_consumer_done_or_exceed128():
    assert 'fabric_latency_or_consumer_credit_not_priced' in run([0],[ins()],[edge(consumer_done_tick=400)],lowering())['issues']
    edges=[edge(launch_tick=i*3,accept_tick=i*3+159,consumer_done_tick=i*3+160,credit_return_tick=3000+i*3,service_tick=i*3) for i in range(129)]
    assert 'finite_credit_violation' in run([0],[ins()],edges,lowering())['issues']


def test_source_graph_dependency_cannot_be_omitted_by_callback():
    l=lowering();l['0'].update(required_instruction_events=1,required_fabric_events=0,dependencies=[]);l['1']=l['0'].copy()
    j=g.audit(PINS['dependency'],[ins(),ins(graph_op=1,partition=1)],[],l,repo=REPO)
    assert 'callback_dependency_mismatch:1' in j['issues']
    assert 'graph_dependency_not_visible:1' in j['issues']
    l['1']['dependencies']=[0]
    j=g.audit(PINS['dependency'],[ins(),ins(graph_op=1,partition=1,rf_read_tick=36,issue_tick=44,finish_tick=72)],[],l,repo=REPO)
    assert j['modeled_service_calendar_closed']


def test_graph_hash_tampering_and_ids_only_input_are_rejected():
    pin=dict(PINS['one'],sha256='0'*64)
    assert not g.audit(pin,[ins()],[],{},repo=REPO)['modeled_service_calendar_closed']
    assert not g.audit([0],[ins()],[],{},repo=REPO)['modeled_service_calendar_closed']


def test_future_negative_service_and_write_acceptance_without_commit_fail():
    for e in [edge(service_tick=999999),edge(service_tick=-3),edge(write_visible_tick=348)]:
        assert 'write_commit_service_order' in run([0],[ins()],[e],lowering())['issues']
    assert 'unbound_fabric_service_phase' in run([0],[ins()],[edge(phase='unknown')],lowering())['issues']


def test_read_response_requires_matching_request_and_ordered_service():
    request=edge(direction='read',phase='read_request',transaction_id='read0')
    response=edge(direction='read',phase='read_response',transaction_id='read0',launch_tick=162,accept_tick=321,consumer_done_tick=322,credit_return_tick=507,service_tick=159)
    l=lowering();l['0'].update(required_instruction_events=1,required_fabric_events=2,dependencies=[])
    assert run([0],[ins()],[request,response],l)['modeled_service_calendar_closed']
    assert 'read_response_service_order' in run([0],[ins()],[response],l)['issues']
    response['service_tick']=999999
    assert 'read_response_service_order' in run([0],[ins()],[request,response],l)['issues']


@pytest.mark.parametrize('active_lanes',[-1,0,True,False,1.0,1.5,'1',None,33])
def test_DIV_participation_rejects_invalid_cardinality_before_accounting(active_lanes):
    l=lowering();l['0'].update(required_instruction_events=1,required_fabric_events=0,dependencies=[])
    j=run([0],[ins(opcode='DIV',finish_tick=84,active_lanes=active_lanes)],[],l)
    assert not j['modeled_service_calendar_closed']
    assert 'invalid_DIV_active_lanes' in j['issues']
    assert not j['physical_build_ready'] and j['speed_credit']==0


def test_DIV_participation_must_be_explicit():
    l=lowering();l['0'].update(required_instruction_events=1,required_fabric_events=0,dependencies=[])
    assert 'invalid_DIV_active_lanes' in run([0],[ins(opcode='DIV',finish_tick=84)],[],l)['issues']


@pytest.mark.parametrize('active_lanes',[1,2,32])
def test_valid_DIV_cardinality_still_obeys_single_scalar_service(active_lanes):
    l=lowering();l['0'].update(required_instruction_events=1,required_fabric_events=0,dependencies=[])
    j=run([0],[ins(opcode='DIV',finish_tick=84,active_lanes=active_lanes)],[],l)
    assert 'invalid_DIV_active_lanes' not in j['issues']
    assert j['modeled_service_calendar_closed'] is (active_lanes==1)
    if active_lanes>1:assert 'single_scalar_DIV_overbooked' in j['issues']


def test_negative_DIV_participation_cannot_cancel_real_overbooking():
    l=lowering();l['0'].update(required_instruction_events=3,required_fabric_events=0,dependencies=[])
    events=[ins(opcode='DIV',partition=p,finish_tick=84,active_lanes=n) for p,n in enumerate([1,1,-1])]
    j=run([0],events,[],l)
    assert not j['modeled_service_calendar_closed']
    assert 'invalid_DIV_active_lanes' in j['issues']
    assert 'single_scalar_DIV_overbooked' in j['issues']


def test_full_warp_DIV_lanes_can_serialize_without_capacity_relaxation():
    events=[ins(opcode='DIV',rf_read_tick=4*i,issue_tick=8+4*i,finish_tick=84+4*i,active_lanes=1) for i in range(32)]
    l=lowering();l['0'].update(required_instruction_events=32,required_fabric_events=0,dependencies=[])
    j=run([0],events,[],l)
    assert j['modeled_service_calendar_closed']
    assert not j['physical_build_ready'] and j['speed_credit']==0


def test_actual_fullgraph_software_callbacks_are_preserved_not_promoted_to_clocks():
    j=g.audit_actual_callbacks(PINS['one'],PINS['actual_callbacks'],repo=REPO)
    assert j['fullgraph_trace_coverage']
    assert j['per_op_event_admission'][0]['callback_dependency_binding_pass']
    assert j['actual_trace_rows']==1 and j['actual_memory_or_collective_rows']==1
    assert j['per_op_event_admission'][0]['actual_callback']['cycles'] is None
    assert not j['modeled_service_calendar_closed'] and not j['physical_build_ready']
    assert 'actual_physical_instruction_fabric_callbacks_unbound' in j['issues']


def test_actual_callback_source_hash_is_verified():
    pin=dict(PINS['actual_callbacks'],sha256='0'*64)
    with pytest.raises(ValueError,match='callback_source_hash_mismatch'):
        g.audit_actual_callbacks(PINS['one'],pin,repo=REPO)
