import copy
import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import dsrom_I66_accepted_observer as O


def sample(n=576):
    # Pure fake observer packets. Never an actual current runtime receipt.
    ob=O.D.source_model()['obligations'][0];choice=ob['phase_choices'][0]
    ident=dict(node=ob['producer_node'],expert=0,rank=0,generation=1,user=0,xversion=1,
        owner_stage=choice['stage'],phase=choice['phase'],key_word=choice['source_key_word'])
    packets=[dict(kind='lease_accept',edge=10,identity=ident,producer_pc=66)]
    for row in range(576):
        root=(row%256)//2
        packets.append(dict(kind='capture',edge=20+2*(row//256)+(row%2),row=row,root=root,
            physical_shard=root//64,raw69=row,raw_valid=1,fault=0,identity=ident))
    packets.append(dict(kind='source_idle',edge=30,busy_seen=1,fault=0,identity=ident))
    for row in range(n):
        edge=40+5*row;shard=((row%256)//2)//64
        base=dict(row=row,identity=ident,physical_shard=shard)
        packets += [dict(base,kind='sinkseat_reserve',edge=edge),
            dict(base,kind='read_request_accept',edge=edge+1),
            dict(base,kind='request_ACK',edge=edge+2),
            dict(base,kind='reply_sample',edge=edge+3,raw69=row,raw_valid=1,token_valid=1,fault=0,ready=1),
            dict(base,kind='ordered_delivery',edge=edge+4),
            dict(base,kind='home_postNBA',edge=edge+4,address=ob['output_VM_elements'][0]+row,data32=row)]
    if n==576:packets.append(dict(kind='lease_retire',edge=3000,identity=ident,
        wire_fenced=1,delivery_fenced=1,provenance_fenced=1))
    for e in packets:
        for name in ['valid','ready','granted','idle']:e.setdefault(name,1)
    packets.sort(key=lambda p:p['edge'])
    return [dict(p,ordinal=i,producer_pc=66) for i,p in enumerate(packets)]


def test_all576_ordered_rows_fake_interface_contract_only():
    p=sample();r=O.validate_packets(p,1,complete=True)
    assert r['observed_debts'][0]['visible_rows']==576
    assert r['peak_reserved_sink_seats']==1 and not r['actual_runtime_enrolled']
    assert r['consumer_deadline'] is None and not r['whole_token']


def test_partial_prefix_cannot_return_complete_and_ACK_does_not_release_seat():
    p=sample(1);p=p[:next(i for i,e in enumerate(p) if e['kind']=='reply_sample')]
    r=O.validate_packets(p,1)
    assert r['observed_debts'][0]['sink_seats']==1
    with pytest.raises(ValueError):O.validate_packets(p,1,complete=True)


def held_reply():
    p=sample(1);i=next(i for i,e in enumerate(p) if e['kind']=='reply_sample')
    first=copy.deepcopy(p[i]);first['ready']=0
    p.insert(i,first)
    for e in p[i+1:]:e['edge']+=1
    return [dict(e,ordinal=j) for j,e in enumerate(p)]


def test_held_reply_keeps_data_identity_and_reserved_sink():
    r=O.validate_packets(held_reply(),1)
    assert r['observed_debts'][0]['visible_rows']==1


@pytest.mark.parametrize('mutation',['wrong_shard','missing_seat','stale_return','changed_hold','missing_hold_edge',
    'requestACK_as_release','bad_raw','bool_valid','false_token','wrong_aperture','duplicate_reply',
    'duplicate_root','early_rearm','busy_as_retire','two_requests_oneedge','fault_capture','false_fence','changed_PC'])
def test_source_packet_mutants_reject_before_caller_mutation(mutation):
    p=held_reply() if mutation in ['changed_hold','missing_hold_edge'] else sample()
    find=lambda kind:next(e for e in p if e['kind']==kind)
    if mutation=='wrong_shard':find('read_request_accept')['physical_shard']=1
    elif mutation=='missing_seat':p.remove(find('sinkseat_reserve'))
    elif mutation=='stale_return':e=find('reply_sample');e['identity']=dict(e['identity'],generation=2)
    elif mutation=='changed_hold':next(e for e in p if e['kind']=='reply_sample' and e['ready'])['raw69']=1
    elif mutation=='missing_hold_edge':
        for e in p:
            if e['edge']>=44:e['edge']+=1
    elif mutation=='requestACK_as_release':
        at=p.index(find('request_ACK'))+1
        extra=dict(find('sinkseat_reserve'),row=1,edge=find('request_ACK')['edge'])
        p.insert(at,extra)
    elif mutation=='bad_raw':find('reply_sample')['raw69']=1
    elif mutation=='bool_valid':find('reply_sample')['token_valid']=True
    elif mutation=='false_token':find('reply_sample')['token_valid']=0
    elif mutation=='wrong_aperture':find('home_postNBA')['address']+=1
    elif mutation=='duplicate_reply':p.insert(p.index(find('reply_sample'))+1,copy.deepcopy(find('reply_sample')))
    elif mutation=='duplicate_root':p[2]['root']=p[1]['root'];p[2]['row']=p[1]['row']
    elif mutation=='early_rearm':p.insert(p.index(find('read_request_accept'))+1,dict(find('lease_retire'),edge=41))
    elif mutation=='busy_as_retire':find('source_idle')['busy_seen']=0
    elif mutation=='two_requests_oneedge':
        at=p.index(find('read_request_accept'))+1
        p.insert(at,dict(find('sinkseat_reserve'),row=1,edge=40))
        p.sort(key=lambda e:e['edge'])
        at=p.index(find('read_request_accept'))+1
        p.insert(at,dict(find('read_request_accept'),row=1))
    elif mutation=='fault_capture':find('capture')['fault']=1
    elif mutation=='changed_PC':find('reply_sample')['producer_pc']=67
    else:find('lease_retire')['wire_fenced']=0
    p=[dict(e,ordinal=i) for i,e in enumerate(p)];before=copy.deepcopy(p)
    with pytest.raises(ValueError):O.validate_packets(p,2 if mutation=='two_requests_oneedge' else 1,complete=True)
    assert p==before


def test_OoO_returns_keep_their_reserved_seats_but_ordered_delivery():
    p=sample(0);ident=p[0]['identity'];out=O.D.source_model()['obligations'][0]['output_VM_elements'][0]
    seq=[('sinkseat_reserve',40,0),('sinkseat_reserve',40,1),
         ('read_request_accept',41,0),('read_request_accept',42,1),
         ('request_ACK',43,0),('request_ACK',44,1),('reply_sample',45,1),
         ('reply_sample',46,0),('ordered_delivery',47,0),('home_postNBA',47,0),
         ('ordered_delivery',48,1),('home_postNBA',48,1)]
    for kind,edge,row in seq:
        e=dict(kind=kind,edge=edge,row=row,physical_shard=0,identity=ident,producer_pc=66)
        if kind=='reply_sample':e.update(raw69=row,raw_valid=1,token_valid=1,fault=0,ready=1)
        if kind=='home_postNBA':e.update(address=out+row,data32=row)
        p.append(e)
    for e in p:
        for name in ['valid','ready','granted','idle']:e.setdefault(name,1)
    p=[dict(e,ordinal=i) for i,e in enumerate(p)]
    r=O.validate_packets(p,2)
    assert r['peak_reserved_sink_seats']==2 and r['observed_debts'][0]['visible_rows']==2


@pytest.mark.parametrize('mutation',['same_edge_seat_reuse','same_edge_rearm_ACK','held_final_sample_missing'])
def test_old_state_hold_and_credit_boundaries(mutation):
    p=sample()
    if mutation=='same_edge_seat_reuse':
        next(e for e in p if e['kind']=='sinkseat_reserve' and e['row']==1)['edge']=44
    elif mutation=='same_edge_rearm_ACK':
        ack=next(e for e in p if e['kind']=='request_ACK' and e['row']==575);ack['edge']=3000
    else:
        p=held_reply();p=[e for e in p if e['edge']<=44]
        p=[e for e in p if not(e['kind']=='reply_sample' and e['ready']==1)]
        p.append(dict(p[-1],kind='sinkseat_reserve',row=1,edge=44))
    p.sort(key=lambda e:e['edge']);p=[dict(e,ordinal=i) for i,e in enumerate(p)]
    with pytest.raises(ValueError):O.validate_packets(p,2 if mutation=='held_final_sample_missing' else 1,complete=mutation!='held_final_sample_missing')


@pytest.mark.parametrize('mutation',[None,'candidate_delayed','different_publication','missing_X_tag','wrong_vector_owner'])
def test_baseline_consumer_read_association_schema_only(mutation):
    packets=sample();ob=O.D.source_model()['obligations'][0];ident=packets[0]['identity']
    events=[dict(kind='producer_accept',edge=10,identity=ident),
        dict(kind='source_idle',edge=30,identity=ident,busy_seen=1,adapter_fault=0,spine_fault=0)]
    for p in packets:
        if p['kind']=='home_postNBA':
            events.append(dict(kind='home_postNBA',edge=p['edge'],row=p['row'],address=p['address'],data=p['data32'],identity=ident))
    for row in range(576):events.append(dict(kind='consumer_VM_read',edge=4000+row//256,
        row=row,src=0,valid=1,port=0,address=ob['output_VM_elements'][0]+row,
        data_pre=row,source_seq=9,identity=ident))
    events.sort(key=lambda e:e['edge']);events=[dict(e,ordinal=i) for i,e in enumerate(events)]
    trace=dict(role='BASELINE_CURRENT_PROGRAM',timebase='native_core_clk',events=events,
        vector_contexts=[dict(node='L0.I70',rank=0,generation=1,user=0,xversion=1,seq=9,accept_edge=3990,done_edge=4500)],
        read_X_tags=[dict(edge=t+2,rank=0,generation=1,user=0,xversion=1,seq=9,valid=1,fault=0) for t in [4000,4001,4002]])
    if mutation=='candidate_delayed':trace['role']='CANDIDATE_DIAGNOSTIC'
    elif mutation=='different_publication':next(e for e in trace['events'] if e['kind']=='home_postNBA')['data']^=1
    elif mutation=='missing_X_tag':trace['read_X_tags'].pop()
    elif mutation=='wrong_vector_owner':trace['vector_contexts'][0]['node']='L0.I74'
    if mutation is None:
        r=O.baseline_consumer_join(trace,packets)
        assert r['status']=='BASELINE_OBSERVED_HOME_READ_ASSOCIATION' and r['finite_service_bound'] is None
    else:
        with pytest.raises(ValueError):O.baseline_consumer_join(trace,packets)



def test_source_plan_marks_unimplemented_hooks_and_no_admission():
    p=O.source_plan();w=p['proposed_wire']
    assert w['global_context_bits']==169 and w['request_bits']==187 and w['response_bits']==240
    assert any(h['available_in_existing_source'] is False for h in p['hooks'])
    assert p['consumer_deadline'] is None and not p['runtime_GO'] and not p['hardware_GO']


@pytest.mark.parametrize('kind,field',[('lease_accept','ready'),('read_request_accept','ready'),
    ('sinkseat_reserve','granted'),('source_idle','idle'),('ordered_delivery','ready'),('request_ACK','valid')])
def test_declared_event_kind_cannot_override_false_source_acceptance(kind,field):
    p=sample();next(e for e in p if e['kind']==kind)[field]=0
    with pytest.raises(ValueError):O.validate_packets(p,1,complete=True)


@pytest.mark.parametrize('key,value',[('ROM_PHW',6),('ROM_FBW',1628),('X_ROM',0),('X_ROM',True),('ROM_R',64)])
def test_no_historical_or_HBM_binary_fallback_before_trace_consumption(monkeypatch,key,value):
    params=dict(FULL_SHAPE=1,X_ROM=1,ROM_PHW=10,ROM_R=128,ROM_BST=17,logical_NP=4096,NBF=724,ROM_FBW=1632,SUN=256)
    params[key]=value
    def forbidden_read(_):raise AssertionError('Rejected geometry must not open or substitute binary')
    monkeypatch.setattr(O.D.S,'sha',forbidden_read)
    with pytest.raises(ValueError):O.current_packets(dict(parameters=params))
