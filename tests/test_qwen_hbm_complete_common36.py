"""Supplied synthetic events, no checkpoint run, arithmetic DUT or real clocks."""
from collections import Counter
from pathlib import Path
from fractions import Fraction
import sys
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from qwen_hbm_complete_common36 import Common36,CONTROL_TAG,FAST,SLOW,crossing,contract,pc_of
from qwen_hbm_complete_service_provider import sector_descriptors

def edge(value,period):return (Fraction(value)//period+1)*period

def packet_request(service,op,die,client,sector,kind='write',length=1):
    return dict(die=die,stack=sector%4,client=client,logical_tag=service.stats['requests']+(1<<40),
        logical_epoch=42,instruction=op['id'],position=service.position,sector=sector,kind=kind,length=length)

def complete(service,owner,start):
    """Explicit supplied provider events. Delays are fixtures, never rates."""
    service.hold_request(owner);accepted=edge(start,FAST)
    tag=service.admit_next(owner['die'],accepted);assert tag is not None
    die=owner['die'];epoch=service.epoch
    for beat in range(owner['length']):
        service.controller_column(die,tag,epoch,beat,accepted)
        packet=service.controller_return(die,tag,epoch,beat,accepted+10000)
        assert service.capture_offer(packet)
        assert service.ACK_FIFO_push(die)
        landing=crossing((Fraction(packet['visible_ps'])//FAST+1)*FAST,SLOW)
        stored=edge(landing+beat*3*SLOW,SLOW);retired=stored+SLOW
        service.ACK_store(die,packet,landing,stored,retired)
    done=retired+SLOW;service.consumer_result_retire(die,tag,epoch,done,done)
    credit=dict(service.return_CDC[die][0]);returned=crossing(done,FAST)
    service.credit_return(die,credit,returned)
    return returned,packet

def control_fixture():
    # Explicit two-op control-only fixture; never full-program coverage.
    graph=Common36().graph.copy()
    first=dict(graph['instructions'][0]);last=dict(graph['instructions'][-1])
    last.update(id=1,dependencies=[0])
    graph['instructions']=[first,last]
    return Common36(graph=graph)

def finish_empty_program(service,position=0):
    service.begin_program(position)
    for op in service.graph['instructions']:
        service.instruction_issue(op['id'],op['opcode'],0)
        service.instruction_result_retire(op['id'],0,0)
    service.finish_program()

def drain(service):
    request=service.begin_drain()
    for packet in request:
        reply=service.control_destination_accept(packet['die'],packet)
        service.control_source_done(packet['die'],reply)
    for die in (0,1):service.control_destination_return_zero(die)
    service.control_source_ready()
    return request

def test_source_contract_prices_all1737_callbacks_and_explicit_missing_ports():
    record=contract()
    assert record['graph_instruction_count']==1737
    assert len(record['encoded_callback_contract'])==1737 and len(record['graph_opcodes'])==21
    assert record['candidate_additional_state']['all1737_event_bits']==10422
    assert not record['actual_provider_credit'] and not record['model_hardware_build_ready']
    assert record['finite_resource_latency']['total_token_cycles'] is None
    assert 'No visible/epoch/drain output' in record['source_audit']['controller']

def test_all36_client_RR_holds_four_mapping_bound_and_held_request_mutation():
    service=Common36();service.begin_program(0);op=service.graph['instructions'][0]
    service.instruction_issue(0,op['opcode'],0)
    for client in range(36):
        request=packet_request(service,op,0,client,client)
        assert service.hold_request(request)
        assert not service.hold_request(request)
    changed=dict(service.waiting[0,0]);changed['logical_tag']+=1
    with pytest.raises(ValueError,match='remain stable'):service.hold_request(changed)
    for client in range(4):
        tag=service.admit_next(0,(client+2)*FAST)
        assert service.entries[0,tag]['owner']['client']==client
    assert service.admit_next(0,100*FAST) is None
    assert len(service.waiting)==32 and len(service.entries)==4
    with pytest.raises(ValueError,match='full encoded boundary'):service.begin_drain()

def test_read8_capture_READY_holds_ack_and_drain_observes_actual_queues():
    service=Common36();service.begin_program(0);op=service.graph['instructions'][0]
    service.instruction_issue(0,op['opcode'],0)
    owner=packet_request(service,op,0,35,17,'read',8);service.hold_request(owner)
    tag=service.admit_next(0,2*FAST);packets=[]
    for beat in range(8):
        service.controller_column(0,tag,0,beat,2*FAST)
        packets.append(service.controller_return(0,tag,0,beat,10000))
    for packet in packets[:4]:assert service.capture_offer(packet)
    head=service.capture_head(0)
    assert not service.ACK_FIFO_push(0,ready=False) and service.capture_head(0)==head
    assert not service.capture_offer(packets[4])
    assert sum(service.r_n.values())==4 and not service.quiescent()
    for _ in range(4):assert service.ACK_FIFO_push(0)
    for packet in packets[4:]:assert service.capture_offer(packet)
    assert not service.capture_ready(0) and not service.ACK_FIFO_push(0)
    with pytest.raises(ValueError,match='owns finite service'):service.instruction_result_retire(0,100000,100000)
    packet=dict(packets[0]);packet['logical_epoch']+=1
    with pytest.raises(ValueError,match='head'):service.ACK_store(0,packet,20000,30000,40000)

def test_drain_control_tag_nonce_epoch_and_returnzero_are_not_fresh_boolean():
    service=control_fixture();finish_empty_program(service);requests=service.begin_drain();request=requests[0]
    for key in ('control_tag','epoch','next_epoch','nonce','position','final_instruction','die'):
        bad=dict(request);bad[key]+=1
        with pytest.raises(ValueError,match='control destination identity'):service.control_destination_accept(0,bad)
    with pytest.raises(ValueError,match='return-zero'):service.control_source_ready()
    reply=service.control_destination_accept(0,request)
    bad=dict(reply);bad['nonce']+=1
    with pytest.raises(ValueError,match='control identity'):service.control_source_done(0,bad)
    service.control_source_done(0,reply)
    with pytest.raises(ValueError,match='return-zero'):service.control_source_ready()
    with pytest.raises(ValueError,match='return zero'):service.control_destination_return_zero(0)
    reply=service.control_destination_accept(1,requests[1]);service.control_source_done(1,reply)
    service.control_destination_return_zero(0)
    with pytest.raises(ValueError,match='return-zero'):service.control_source_ready()
    service.control_destination_return_zero(1);service.control_source_ready()
    assert service.epoch==1 and service.next_tag==[0,0]
    with pytest.raises(ValueError,match='control destination identity'):service.control_destination_accept(0,request)

def test_old_ACK_after_proved_model_drain_reuse_and_missing_epoch_reject():
    service=control_fixture();service.begin_program(0);op=service.graph['instructions'][0]
    service.instruction_issue(0,op['opcode'],0)
    end,old=complete(service,packet_request(service,op,0,0,0,'read'),0)
    service.instruction_result_retire(0,end,end)
    for operation in service.graph['instructions'][1:]:
        service.instruction_issue(operation['id'],operation['opcode'],end)
        service.instruction_result_retire(operation['id'],end,end)
    service.finish_program();drain(service)
    service.begin_program(1);service.instruction_issue(0,op['opcode'],end)
    owner=packet_request(service,op,0,0,0,'read');service.hold_request(owner)
    assert service.admit_next(0,edge(end,FAST))==old['tag']==0
    with pytest.raises(ValueError,match='stale transport epoch'):service.capture_offer(old)
    missing=dict(old);del missing['transport_epoch']
    with pytest.raises(KeyError):service.capture_offer(missing)
    with pytest.raises(ValueError,match='control tag aperture'):service.controller_column(0,CONTROL_TAG,1,0,end)

def test_encoded_dependencies_and_result_visibility_are_mandatory():
    service=Common36();service.begin_program(0)
    with pytest.raises(ValueError,match='dependency'):service.instruction_issue(1,'RSTD',0)
    with pytest.raises(ValueError,match='opcode'):service.instruction_issue(0,'MATRIX',0)
    service.instruction_issue(0,'EMBED',0)
    with pytest.raises(ValueError,match='retirement order'):service.instruction_result_retire(0,1000,0)
    with pytest.raises(ValueError,match='full1737'):service.finish_program()

def test_RMW_owner_locks_and_merge_opcode_mutants_block_allclient_conflicts():
    service=Common36();service.begin_program(0)
    writer=next(o for o in service.graph['instructions'] if o['opcode']=='KV_WRITE')
    for op in service.graph['instructions'][:writer['id']+1]:
        service.instruction_issue(op['id'],op['opcode'],0)
        if op!=writer:service.instruction_result_retire(op['id'],0,0)
    descriptor=sector_descriptors(service.graph,writer,0)[0]
    owner=packet_request(service,writer,0,35,descriptor['sector'],'read');owner['stack']=descriptor['stack']
    service.acquire_RMW(owner,descriptor['mask'])
    write=dict(owner,kind='write')
    with pytest.raises(ValueError,match='before XOR'):service.hold_request(write)
    conflicting=dict(owner,client=0)
    with pytest.raises(ValueError,match='conflicting all-client'):service.hold_request(conflicting)
    end,_=complete(service,owner,0)
    assert not service.entries and not service.quiescent()
    with pytest.raises(ValueError,match='two-source opcodes'):service.RMW_merge_result(owner,['XOR','XOR','XOR'],end,end+27*SLOW)
    with pytest.raises(ValueError,match='three serial9cycle'):service.RMW_merge_result(owner,['XOR','AND','XOR'],end,end)
    service.RMW_merge_result(owner,['XOR','AND','XOR'],end,end+27*SLOW)
    complete(service,write,end+27*SLOW+FAST)
    assert not service.RMW_locks

def test_eight_full_encoded_graph_synthetic_sessions_cross_old_namespace_limit():
    service=Common36();now=Fraction(0);clients=set();old_packet=None
    for position in range(8):
        service.begin_program(position)
        for op in service.graph['instructions']:
            service.instruction_issue(op['id'],op['opcode'],now)
            if op['opcode']=='KV_WRITE':
                die=op['attributes']['die']
                for descriptor in sector_descriptors(service.graph,op,position):
                    client=(descriptor['ordinal']+op['attributes']['layer'])%36;clients.add(client)
                    # Synthetic fixture uses actual addressed masks: partial
                    # sectors pay a read mapping and a separate write mapping.
                    # No free RMW or actual RF/arithmetic claim.
                    kinds=['read','write'] if descriptor['partial'] else ['write']
                    if descriptor['partial']:
                        RMW_owner=packet_request(service,op,die,client,descriptor['sector'],'read')
                        RMW_owner['stack']=descriptor['stack']
                        service.acquire_RMW(RMW_owner,descriptor['mask'])
                    for kind in kinds:
                        if kind=='write' and descriptor['partial']:
                            issue=now+SLOW;result=issue+27*SLOW
                            service.RMW_merge_result(RMW_owner,['XOR','AND','XOR'],issue,result)
                            now=result+FAST
                        owner=packet_request(service,op,die,client,descriptor['sector'],kind)
                        owner['stack']=descriptor['stack']
                        now,packet=complete(service,owner,now+100000)
                        old_packet=old_packet or packet
            service.instruction_result_retire(op['id'],now,now)
        service.finish_program()
        assert service.quiescent()
        before=sum(service.stats[k] for k in ('requests_read','requests_write'))
        drain(service)
        assert sum(service.stats[k] for k in ('requests_read','requests_write'))==before
        with pytest.raises(ValueError,match='stale transport epoch'):service.capture_offer(old_packet)
    assert clients==set(range(36))
    assert service.stats['requests_write']==8*72*272
    assert service.stats['requests_read']==8*72*256
    assert service.stats['credit_returns']==service.stats['requests']==304128
    assert service.stats['encoded_instructions_retired']==8*1737
    assert service.stats['completed_drains']==8 and service.epoch==8
    assert service.stats['RMW_merges']==8*72*256


def test_writer_retirement_rejects_premerge_preWR_and_previsibility():
    service=Common36();service.begin_program(0)
    writer=next(o for o in service.graph['instructions'] if o['opcode']=='KV_WRITE')
    for op in service.graph['instructions'][:writer['id']+1]:
        service.instruction_issue(op['id'],op['opcode'],0)
        if op!=writer:service.instruction_result_retire(op['id'],0,0)
    descriptor=sector_descriptors(service.graph,writer,0)[0]
    owner=packet_request(service,writer,0,35,descriptor['sector'],'read')
    owner['stack']=descriptor['stack'];write=dict(owner,kind='write')
    with pytest.raises(ValueError,match='requires persistent'):service.hold_request(write)
    service.acquire_RMW(owner,descriptor['mask'])
    end,_=complete(service,owner,0)
    assert not service.entries and service.stats['requests_write']==0
    with pytest.raises(ValueError,match='persistent RMW'):service.instruction_result_retire(writer['id'],end,end)
    with pytest.raises(ValueError,match='dependency'):service.instruction_issue(writer['id']+1,service.graph['instructions'][writer['id']+1]['opcode'],end)
    result=end+27*SLOW
    service.RMW_merge_result(owner,['XOR','AND','XOR'],end,result)
    with pytest.raises(ValueError,match='persistent RMW'):service.instruction_result_retire(writer['id'],result,result)
    service.hold_request(write);accepted=edge(result+FAST,FAST)
    tag=service.admit_next(0,accepted);service.controller_column(0,tag,0,0,accepted)
    with pytest.raises(ValueError,match='owns finite service'):service.instruction_result_retire(writer['id'],accepted,accepted)
    with pytest.raises(ValueError,match='backing visibility'):service.controller_return(0,tag,0,0,accepted+1)
    packet=service.controller_return(0,tag,0,0,accepted+10000)
    assert service.capture_offer(packet) and service.ACK_FIFO_push(0)
    landing=crossing((Fraction(packet['visible_ps'])//FAST+1)*FAST,SLOW)
    stored=edge(landing,SLOW)
    with pytest.raises(ValueError,match='owns finite service'):service.instruction_result_retire(writer['id'],stored,stored)
    service.ACK_store(0,packet,landing,stored,stored+SLOW)
    service.consumer_result_retire(0,tag,0,stored+2*SLOW,stored+2*SLOW)
    with pytest.raises(ValueError,match='owns finite service'):service.instruction_result_retire(writer['id'],stored+2*SLOW,stored+2*SLOW)
    returned=crossing(stored+2*SLOW,FAST)
    service.credit_return(0,dict(service.return_CDC[0][0]),returned)
    with pytest.raises(ValueError,match='publication obligations'):service.instruction_result_retire(writer['id'],returned,returned)


def test_one_completed_WR_cannot_publish_remaining271_sectors():
    service=Common36();service.begin_program(0)
    writer=next(o for o in service.graph['instructions'] if o['opcode']=='KV_WRITE')
    for op in service.graph['instructions'][:writer['id']+1]:
        service.instruction_issue(op['id'],op['opcode'],0)
        if op!=writer:service.instruction_result_retire(op['id'],0,0)
    descriptor=next(r for r in sector_descriptors(service.graph,writer,0) if not r['partial'])
    owner=packet_request(service,writer,0,0,descriptor['sector']);owner['stack']=descriptor['stack']
    end,_=complete(service,owner,0)
    assert not service.entries and not service.RMW_locks
    with pytest.raises(ValueError,match='publication obligations'):service.instruction_result_retire(writer['id'],end,end)
    with pytest.raises(ValueError,match='duplicate completed'):service.hold_request(owner)
    bad=dict(owner,sector=0)
    with pytest.raises(ValueError,match='descriptor'):service.hold_request(bad)
