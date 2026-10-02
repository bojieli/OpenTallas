import copy
import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import dsrom_I66_consumer_deadline as D


def test_source_consumer_nodes_and_no_deadline_from_program_order():
    m=D.source_model();expected=['L0.I70','L0.I70','L0.I80','L0.I80','L0.I85','L0.I85','L0.I90','L0.I90','L0.I95','L0.I95','L0.I98','L0.I98']
    assert [o['first_static_consumer'][0]['consumer_node'] for o in m['obligations']]==expected
    assert all(o['actual_first_read_edge'] is None for o in m['obligations'])
    assert m['source_contract']['SU_ready_does_not_mean_pipeline_idle']
    assert not m['source_contract']['same_edge_publication_meets_read']


def sample(producer='L0.I66'):
    # Normalized fake callback API test: not a current-program actual journal.
    model=D.source_model();o=next(o for o in model['obligations'] if o['producer_node']==producer);p=o['phase_choices'][0]
    ident=dict(node=producer,expert=0,rank=0,generation=1,user=0,xversion=1,owner_stage=p['stage'],phase=p['phase'],key_word=p['source_key_word'])
    target=o['first_static_consumer'][0];port='abcd'.index(target['operand'])
    events=[dict(kind='producer_accept',edge=10,identity=ident)]
    for row in range(576):events.append(dict(kind='home_postNBA',edge=415+row//128,row=row,address=o['output_VM_elements'][0]+row,data=0x45a00000,identity=ident))
    events.append(dict(kind='source_idle',edge=422,busy_seen=1,adapter_fault=0,spine_fault=0,identity=ident))
    for row in range(576):events.append(dict(kind='consumer_VM_read',edge=500+row//256,valid=1,src=0,port=port,address=o['output_VM_elements'][0]+row,data_pre=0x45a00000,source_seq=9,identity=ident))
    events=[dict(e,ordinal=i) for i,e in enumerate(events)]
    contexts=[dict(seq=9,node=target['consumer_node'],rank=0,generation=1,user=0,xversion=1,accept_edge=490,done_edge=600)]
    slots=[dict(row=row,postNBA_edge=450+row//128,identity=ident) for row in range(576)]
    return dict(role='BASELINE_CURRENT_PROGRAM',timebase='native_core_clk',events=events,vector_contexts=contexts),slots


@pytest.mark.parametrize('producer',['L0.I66','L0.I67','L0.I92','L0.I93'])
def test_w1_w3_owner_specific_deadlines_fake_packet_schema(producer):
    trace,slots=sample(producer);r=D.calibrate(trace,slots)
    assert r['operations'][0]['first_actual_read']==500
    assert r['operations'][0]['last_actual_read']==502
    assert not r['whole_token_no_loss'] and not r['candidate_service_measured']


@pytest.mark.parametrize('mutation',['candidate_late','candidate_same_edge','missing_slot','source_same_edge','wrong_value','false_read','bool_read','wrong_src','wrong_port','wrong_owner','stale_generation','stale_xversion','wrap_collision','partial_prefix','busy_as_idle','fault_idle','duplicate_publication','float_address','wrong_timebase','candidate_delayed_baseline'])
def test_actual_deadline_api_negative_controls_before_mutation(mutation):
    trace,slots=sample();events=trace['events'];read=next(e for e in events if e['kind']=='consumer_VM_read')
    if mutation=='candidate_late':slots[0]['postNBA_edge']=501
    elif mutation=='candidate_same_edge':slots[0]['postNBA_edge']=500
    elif mutation=='missing_slot':slots.pop()
    elif mutation=='source_same_edge':
        read['edge']=events[1]['edge'];events.sort(key=lambda e:e['edge'])
        for i,e in enumerate(events):e['ordinal']=i
    elif mutation=='wrong_value':read['data_pre']^=1
    elif mutation=='false_read':read['valid']=0
    elif mutation=='bool_read':read['valid']=True
    elif mutation=='wrong_src':read['src']=1
    elif mutation=='wrong_port':read['port']=1
    elif mutation=='wrong_owner':trace['vector_contexts'][0]['node']='L0.I74'
    elif mutation=='stale_generation':trace['vector_contexts'][0]['generation']=2
    elif mutation=='stale_xversion':trace['vector_contexts'][0]['xversion']=2
    elif mutation=='wrap_collision':trace['vector_contexts'].append(dict(trace['vector_contexts'][0]))
    elif mutation=='partial_prefix':events.pop()
    elif mutation=='busy_as_idle':next(e for e in events if e['kind']=='source_idle')['busy_seen']=0
    elif mutation=='fault_idle':next(e for e in events if e['kind']=='source_idle')['adapter_fault']=1
    elif mutation=='duplicate_publication':events[2]['row']=0;events[2]['address']=events[1]['address']
    elif mutation=='float_address':events[1]['address']=float(events[1]['address'])
    elif mutation=='candidate_delayed_baseline':trace['role']='CANDIDATE_DIAGNOSTIC'
    else:trace['timebase']='unbound_remote_clock'
    before=copy.deepcopy((trace,slots))
    with pytest.raises(ValueError):D.calibrate(trace,slots)
    assert (trace,slots)==before


def test_actual_read_tag_alignment_uses_observed_X_tag_not_latest_corePC():
    t,_=sample();reads=[e for e in t['events'] if e['kind']=='consumer_VM_read'];ident=reads[0]['identity']
    for r in reads:r.pop('source_seq')
    tags=[dict(edge=edge+2,rank=0,valid=1,fault=0,seq=9,generation=1,user=0,xversion=1) for edge in [500,501,502]]
    bound=D.bind_actual_read_tags(reads,tags)
    assert all(r['source_seq']==9 for r in bound)
    assert all('source_seq' not in r for r in reads)


@pytest.mark.parametrize('mutation',['missing','wrong_edge','fault','stale','bool_seq','duplicate'])
def test_missing_or_stale_read_tags_never_become_progress(mutation):
    t,_=sample();read=next(e for e in t['events'] if e['kind']=='consumer_VM_read')
    tag=dict(edge=502,rank=0,valid=1,fault=0,seq=9,generation=1,user=0,xversion=1);tags=[tag]
    if mutation=='missing':tags=[]
    elif mutation=='wrong_edge':tag['edge']=501
    elif mutation=='fault':tag['fault']=1
    elif mutation=='stale':tag['generation']=2
    elif mutation=='bool_seq':tag['seq']=True
    else:tags.append(dict(tag))
    with pytest.raises(ValueError):D.bind_actual_read_tags([read],tags)


def service_sample(trace):
    # Schema test double, no assertion that this is an actual cfg/ROM calendar.
    ident=trace['events'][0]['identity'];o=D.operation_id(ident,D.source_model())
    ev=[dict(id='input',kind='input',domain='shared',bits=5120*32,release=0,deadline=10),
        dict(id='cfg',kind='cfg',domain='shared',bits=1,release=30,deadline=40),
        dict(id='activation',kind='activation',domain='shared',bits=1,release=31,deadline=40)]
    ev += [dict(id='row:'+str(row),kind='result',domain='shared',bits=32,
        row=row,address=o['output_VM_elements'][0]+row,release=415+row//128,deadline=425)
        for row in range(576)]
    return dict(timebase='native_core_clk',calendars=[dict(identity=ident,accepted_edge=10,source_idle_edge=422,
        first_VM_read_edge=45,source_calendar_sha256='a'*64,phase_source_sha256='b'*64,
        source_boundary_events=ev)],domains=dict(shared=dict(bits_per_edge=200000,
        latency_edges=1,ACK_edges=1,credits=2000,storage_bits=500000)))


def test_global_service_charge_and_finite_retirement_bound_schema_only():
    trace,_=sample();service=service_sample(trace)
    result=D.reserved_service_join(trace,service)
    assert result['finite_conditional_service'][0]['successful_completion_edge']==423
    assert result['operations'][0]['minimum_edge_margin']>0
    assert not result['provider_delivery_ACK_guarantees_measured']


@pytest.mark.parametrize('mutation',['insufficient_capacity','insufficient_credit','insufficient_storage','late_delivery','late_ACK_owner_reuse','missing_cfg','wrong_origin','emission_after_idle','wrong_destination','phase_hash','clock_transfer'])
def test_service_and_deadline_composition_rejects_unfunded_guarantees(mutation):
    trace,_=sample();service=service_sample(trace);c=service['calendars'][0];d=service['domains']['shared']
    if mutation=='insufficient_capacity':d['bits_per_edge']=1
    elif mutation=='insufficient_credit':d['credits']=0
    elif mutation=='insufficient_storage':d['storage_bits']=1
    elif mutation=='late_delivery':d['latency_edges']=500
    elif mutation=='late_ACK_owner_reuse':
        d['ACK_edges']=100;second,_=sample('L0.I67');other_service=service_sample(second)
        for e in second['events']:e['edge']+=420
        for ctx in second['vector_contexts']:ctx['accept_edge']+=420;ctx['done_edge']+=420
        other=other_service['calendars'][0]
        for k in ['accepted_edge','source_idle_edge','first_VM_read_edge']:other[k]+=420
        for e in other['source_boundary_events']:e['release']+=420;e['deadline']+=420
        service['calendars'].append(other);trace['events']+=second['events'];trace['vector_contexts']+=second['vector_contexts']
        trace['events'].sort(key=lambda e:e['edge'])
        for i,e in enumerate(trace['events']):e['ordinal']=i
    elif mutation=='missing_cfg':c['source_boundary_events']=[e for e in c['source_boundary_events'] if e['kind']!='cfg']
    elif mutation=='wrong_origin':c['accepted_edge']=11
    elif mutation=='emission_after_idle':c['source_boundary_events'][-1]['release']=422
    elif mutation=='wrong_destination':c['source_boundary_events'][-1]['address']+=1
    elif mutation=='clock_transfer':service['timebase']='unqualified_physical_link_clk'
    else:c['phase_source_sha256']='missing'
    before=copy.deepcopy((trace,service))
    with pytest.raises(ValueError):D.reserved_service_join(trace,service)
    assert (trace,service)==before


def test_two_ranks_cannot_reserve_the_same_shared_domain_twice():
    trace,_=sample();service=service_sample(trace)
    second=copy.deepcopy(trace);second['vector_contexts'][0]['rank']=1
    for e in second['events']:e['identity']['rank']=1
    standalone_second=copy.deepcopy(second)
    trace['events']+=second['events'];trace['events'].sort(key=lambda e:e['edge'])
    for i,e in enumerate(trace['events']):e['ordinal']=i
    trace['vector_contexts']+=second['vector_contexts']
    other=copy.deepcopy(service['calendars'][0]);other['identity']['rank']=1
    service['calendars'].append(other)
    service['domains']['shared']['bits_per_edge']=20000
    # Each input individually fits ten edges, their union does not.
    D.reserved_service_join(standalone_second,dict(timebase='native_core_clk',calendars=[other],domains=service['domains']))
    with pytest.raises(ValueError):D.reserved_service_join(trace,service)


@pytest.mark.parametrize('mutation',[None,'wrong_pc','wrong_word','bool_rank','bool_pc','out_of_bounds','negative_word'])
def test_program_word_and_accepted_PC_binding_schema_only(mutation):
    trace=dict(vector_contexts=[dict(node='L0.I70',accepted_front_pc=1,rank=0)])
    binding=dict(node_program_map={'L0.I70':{'0':1}});programs={0:['0','1']}
    expected={'L0.I70':D.J.hashlib.sha256((1).to_bytes(256,'little')).hexdigest()}
    c=trace['vector_contexts'][0]
    if mutation=='wrong_pc':c['accepted_front_pc']=0
    elif mutation=='wrong_word':programs[0][1]='2'
    elif mutation=='bool_rank':c['rank']=False
    elif mutation=='bool_pc':c['accepted_front_pc']=True
    elif mutation=='out_of_bounds':programs[0]=['0']
    elif mutation=='negative_word':programs[0][1]='-1'
    if mutation is None:D.check_program_contexts(trace,binding,programs,expected)
    else:
        with pytest.raises(ValueError):D.check_program_contexts(trace,binding,programs,expected)


@pytest.mark.parametrize('mutation',[None,'schedule_change','phase_change','missing_record'])
def test_service_calendar_requires_hash_verified_reviewed_preimage(tmp_path,mutation):
    import json
    trace,_=sample();service=service_sample(trace);c=service['calendars'][0]
    body={k:v for k,v in c.items() if k not in ['source_calendar_sha256','phase_source_sha256']}
    calendar=tmp_path/'calendar.json';calendar.write_text(json.dumps(body))
    phase=tmp_path/'phase.hex';phase.write_text('0\n')
    c['source_calendar_sha256']=D.S.sha(calendar);c['phase_source_sha256']=D.S.sha(phase)
    binding=dict(service_calendar_files=[dict(calendar_path=str(calendar),phase_path=str(phase))])
    if mutation=='schedule_change':c['source_boundary_events'][-1]['deadline']+=1
    elif mutation=='phase_change':phase.write_text('1\n')
    elif mutation=='missing_record':binding['service_calendar_files']=[]
    if mutation is None:D.qualified_service_calendars(service,binding)
    else:
        with pytest.raises(ValueError):D.qualified_service_calendars(service,binding)
