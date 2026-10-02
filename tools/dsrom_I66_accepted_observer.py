#!/usr/bin/env python3
"""Passive current-PHW10 capture/read-token journal checks, never a scheduler.

Pure validation API tests do not enroll a runtime. CLI requires exact current
source/binary/program/argv and compiled callback qualification. Proposed
request/reply hooks remain unavailable until implemented and qualified.
"""
import argparse
import copy
import json
from pathlib import Path
import dsrom_I66_consumer_deadline as D
J=D.J
OUT=D.ROOT/'results/uarch/dsrom_I66_accepted_observer_20261002'


def source_plan():
    return dict(schema='opentallas.I66.passive-accepted-observer.v1',scope='SIMULATION_ONLY',
        predecessor='45f4aa4bd7a4ac4672002fd34e7acdeb825d3fbf',
        source_core_sha256=D.source_model()['core_sha256'],
        current_enrollment='PHW10/X_ROM1/SUN256 compiled closure, exact four programs, +DIR and separate +OT_ROM_DIR; no PHW6/D1_X_ROM0 fallback',
        hooks=[dict(event='lease_accept',source='Actual source-owned accepted command/context plus registered owner association',available_in_existing_source='Core/adapter accept exists; full proposed wire context/lease not installed'),
            dict(event='capture',source='Actual per-shard root/writer valid, root, row, raw data and fault; no ready',available_in_existing_source=True),
            dict(event='source_idle',source='Adapter/spine idle after observed accepted busy, healthy fault state',available_in_existing_source=True),
            dict(event='sinkseat_reserve/read_request_accept/request_ACK/reply_sample/ordered_delivery',source='Proposed capture/transport/gather owner; source edge plus frozen context and physical_shard',available_in_existing_source=False),
            dict(event='home_postNBA',source='Accepted real destination writer/address/data and VM snapshot after NBA',available_in_existing_source='Local source exists; proposed remote formatter/bridge unavailable'),
            dict(event='consumer_VM_read',source='xs_rd_re/src/addr and old VM read data, source vector ownership',available_in_existing_source=True),
            dict(event='read_X_tag',source='u_su.u_vec.vx and cwx[WR-1 -:8], two edges after accepted VM read',available_in_existing_source=True)],
        callback_journal=dict(frozen_PC='Accepted producer owner PC, not latest core PC',
            order='ordinal + native source edge; preedge request/read/hold and postNBA publication distinct',
            publication='Match packet and baseline journal in identity/row/address/data/edge',
            diagnostic_prefix='No completion/consumer deadline/finite-service claim',
            hold='Sample every native source edge until actual ready acceptance; absent samples rejected'),
        proposed_wire=dict(global_context_bits=169,physical_shard_route_bits=1,request_bits=187,response_bits=240,
            context=['stage6','rank2','EID9','phase10','key32','generation32','user32','Xversion32','producerPC14'],
            token_valid_distinct_raw_valid=True,record_bits=69,hardware_ABI_selected=False),
        rows=576,physical_shards=2,root_mapping='root=(row%256)//2; shard=root//64; local_root=root%64',
        source_seats=[320,256],no_cross_die_combinational_readtree=True,
        software_only_state=dict(logical_seat_capacity='Reviewed finite C, not selected here',
            no_new_hardware_ports_or_state=True,accepted_request_and_return_packet_bits_per_C=187+240,
            log_edges_are_64bit_host_observation=True,total_log_or_compile_cost_not_measured=True),
        clock='Native one-clock source; planned1.2GHz/0.9GHz CDC implementation and edge conversion unavailable',
        hold_timing='Observed stable hold paths only; no typed SS/FF physical timing qualification',
        register_positions=None,physical_homes=None,consumer_deadline=None,finite_service_bound=None,
        hardware_GO=False,compile_GO=False,runtime_GO=False,new_jobs=[])


def row_route(p):
    row=J.uint(p['row'],16)
    if row>=576:raise ValueError('row outside source576')
    root=(row%256)//2
    if J.uint(p['physical_shard'],1)!=root//64:
        raise ValueError('wrong physical shard for source-static row')
    return row,root


def validate_packets(packets,credits,complete=False):
    """Check observed ownership/hold transitions without inventing progress.

    A reserved sink seat is held until observed home visibility. Request ACK
    never returns that seat. Reply offers are sampled every source edge while
    held; omitted samples do not prove stability. Two shard interfaces may
    return out of order, but delivery rows remain0..575. No field ready exists.
    """
    packets=copy.deepcopy(packets);J.uint(credits,10)
    if not 1<=credits<=576:raise ValueError('reviewed finite sink capacity required')
    operations={};held={};last_edge=-1;active_owners={};peak=0;seen_requests=set();seen_replies=set();seen_captures=set()
    model=D.source_model()
    for ordinal,p in enumerate(packets):
        edge=J.uint(p['edge']);kind=p['kind']
        if J.uint(p['ordinal'])!=ordinal or edge<last_edge:raise ValueError('unordered source journal')
        # No absent edge or disappearing interface can count as a stable hold.
        for h in held.values():
            if edge>h['edge']+1:raise ValueError('missing held reply source-edge sample')
        last_edge=edge;D.operation_id(p['identity'],model)
        key=json.dumps(p['identity'],sort_keys=True);owner=(p['identity']['owner_stage'],p['identity']['rank'])
        if kind=='lease_accept':
            if any(J.uint(p[k],1)!=1 for k in ['valid','ready']):
                raise ValueError('lease event is not an accepted source handshake')
            if key in operations or owner in active_owners:raise ValueError('spent identity/undrained owner')
            J.uint(p['producer_pc'],14)
            operations[key]=dict(identity=p['identity'],pc=p['producer_pc'],captured={},seats={},
                requested={},ACKs={},returned={},delivered={},visible={},next_request=0,
                next_delivery=0,source_idle=None,retired=False,accept=edge)
            active_owners[owner]=key;continue
        if key not in operations:raise ValueError('packet lacks accepted source owner')
        op=operations[key]
        if J.uint(p['producer_pc'],14)!=op['pc']:
            raise ValueError('changed frozen accepted producer PC')
        if op['retired']:raise ValueError('callback after retired owner')
        if kind=='source_idle':
            if op['source_idle'] is not None or len(op['captured'])!=576 or J.uint(p['idle'],1)!=1 or J.uint(p['busy_seen'],1)!=1 or J.uint(p['fault'],1):
                raise ValueError('unqualified source terminal')
            op['source_idle']=edge;continue
        if kind=='lease_retire':
            if op['source_idle'] is None or op['seats'] or len(op['visible'])!=576 or any(h['token'][0]==key for h in held.values()) or len(op['ACKs'])!=576:
                raise ValueError('source/seat/return/publication/requestACK debt remains')
            old_state_edge=max(op['source_idle'],max(op['visible'].values()),max(op['ACKs'].values()))
            if edge<=old_state_edge:raise ValueError('rearm before old visibility/ACK retirement visible')
            if any(J.uint(p[k],1)!=1 for k in ['wire_fenced','delivery_fenced','provenance_fenced']):
                raise ValueError('missing causal wire/home fence')
            op['retired']=True;del active_owners[owner];continue
        row,root=row_route(p)
        if kind=='capture':
            if J.uint(p['root'],7)!=root or row in op['captured'] or edge<=op['accept']:
                raise ValueError('duplicate/foreign root capture')
            if J.uint(p['raw_valid'],1)!=1 or J.uint(p['fault'],1):raise ValueError('faulted raw capture')
            capture_port=(owner,root,edge)
            if capture_port in seen_captures:raise ValueError('two captures on one root edge')
            seen_captures.add(capture_port)
            op['captured'][row]=(edge,J.uint(p['raw69'],69))
        elif kind=='sinkseat_reserve':
            if J.uint(p['granted'],1)!=1:raise ValueError('sink seat not actually granted')
            if row in op['seats'] or row in op['requested'] or len(op['seats'])+sum(t==edge for t in op['visible'].values())>=credits:
                raise ValueError('spent row or sink capacity overbooked')
            op['seats'][row]=edge;peak=max(peak,len(op['seats']))
        elif kind=='read_request_accept':
            if any(J.uint(p[k],1)!=1 for k in ['valid','ready']):
                raise ValueError('read request not actually accepted')
            if op['source_idle'] is None or row not in op['captured'] or row not in op['seats']:
                raise ValueError('request before source drain/capture/reserved sink')
            if row!=op['next_request'] or edge<=op['seats'][row] or edge<=op['captured'][row][0]:
                raise ValueError('request admission ordering/old seat not visible')
            if (owner,edge) in seen_requests:raise ValueError('more than one scalar request per source edge')
            seen_requests.add((owner,edge));op['requested'][row]=edge;op['next_request']+=1
        elif kind=='request_ACK':
            if J.uint(p['valid'],1)!=1:raise ValueError('ACK not actually asserted')
            if row not in op['requested'] or row in op['ACKs'] or edge<=op['requested'][row]:
                raise ValueError('unowned/duplicate/premature request ACK')
            op['ACKs'][row]=edge # No data acceptance or sink release implied.
        elif kind=='reply_sample':
            if J.uint(p['token_valid'],1)!=1 or J.uint(p['raw_valid'],1)!=1 or J.uint(p['fault'],1):
                raise ValueError('invalid returned token/raw data')
            ready=J.uint(p['ready'],1);raw=J.uint(p['raw69'],69)
            if row not in op['requested'] or row in op['returned'] or row in op['delivered']:
                raise ValueError('unowned/spent reply')
            if edge<=op['requested'][row] or raw!=op['captured'][row][1]:raise ValueError('reply clock/data identity')
            port=(owner,p['physical_shard']);token=(key,row,raw)
            if (port,edge) in seen_replies:raise ValueError('two replies on one shard source edge')
            seen_replies.add((port,edge))
            if port in held:
                h=held[port]
                if token!=h['token'] or edge!=h['edge']+1:raise ValueError('held reply changed or repeated step')
            if not ready:held[port]=dict(edge=edge,token=token)
            else:
                held.pop(port,None);op['returned'][row]=edge
        elif kind=='ordered_delivery':
            if any(J.uint(p[k],1)!=1 for k in ['valid','ready']):
                raise ValueError('stalled gather is not ordered delivery')
            if row!=op['next_delivery'] or row not in op['returned'] or edge<=op['returned'][row]:
                raise ValueError('delivery without old returned row/order')
            op['delivered'][row]=edge;op['next_delivery']+=1
        elif kind=='home_postNBA':
            if row not in op['delivered'] or row in op['visible'] or edge<op['delivered'][row]:
                raise ValueError('home visibility before owned delivery')
            ob=D.operation_id(p['identity'],model)
            if J.uint(p['address'],19)!=ob['output_VM_elements'][0]+row:
                raise ValueError('wrong destination aperture')
            J.uint(p['data32'],32)
            op['visible'][row]=edge;del op['seats'][row]
        else:raise ValueError('unknown source hook; PC/busy is not service')
    if any(h['edge']!=last_edge for h in held.values()):
        raise ValueError('missing held sample on final observed source edge')
    if complete and (not operations or any(not op['retired'] for op in operations.values()) or held):
        raise ValueError('partial prefix cannot qualify complete ownership')
    return dict(status='MODEL_PACKET_CONTRACT_VALID_COMPLETE' if complete else 'DIAGNOSTIC_PREFIX_NO_COMPLETION',
        operations=len(operations),peak_reserved_sink_seats=peak,
        observed_debts=[dict(identity=o['identity'],sink_seats=len(o['seats']),
            captures=len(o['captured']),requests=len(o['requested']),request_ACKs=len(o['ACKs']),
            visible_rows=len(o['visible']),retired=o['retired']) for o in operations.values()],
        actual_runtime_enrolled=False,consumer_deadline=None,finite_service_bound=None,
        hardware_admission=False,whole_token=False)


def baseline_consumer_join(trace,packets):
    """Join actual home observations to accepted baseline consumer reads.

    This calibrates observations only, not a proposed reserved service. The
    source-aligned tags and vector contexts must come from the same enrolled
    journal. A delayed candidate trace cannot define a no-loss deadline.
    """
    if trace['role']!='BASELINE_CURRENT_PROGRAM':
        raise ValueError('candidate-delayed trace cannot define baseline deadline')
    reads=[e for e in trace['events'] if e['kind']=='consumer_VM_read']
    bound=D.bind_actual_read_tags(reads,trace['read_X_tags'])
    if any(a.get('source_seq')!=b['source_seq'] for a,b in zip(reads,bound)):
        raise ValueError('consumer tag differs from observed source-aligned X context')
    actual={}
    for p in packets:
        if p['kind']=='home_postNBA':
            key=(json.dumps(p['identity'],sort_keys=True),p['row'])
            if key in actual:raise ValueError('duplicate home publication observation')
            actual[key]=p
    slots=[]
    for e in trace['events']:
        if e['kind']=='home_postNBA':
            key=(json.dumps(e['identity'],sort_keys=True),e['row'])
            if key not in actual:raise ValueError('consumer journal lacks owned home callback')
            p=actual.pop(key)
            if (e['edge'],e['address'],e['data'])!=(p['edge'],p['address'],p['data32']):
                raise ValueError('publication/consumer traces disagree in edge/address/data')
            slots.append(dict(identity=e['identity'],row=e['row'],postNBA_edge=e['edge']))
    if actual:raise ValueError('unassociated home callbacks')
    result=D.calibrate(trace,slots)
    result.update(status='BASELINE_OBSERVED_HOME_READ_ASSOCIATION',
        reserved_candidate_service_proved=False,finite_service_bound=None)
    return result


def current_packets(provenance):
    J.current_enrollment(provenance)
    q=D.S.load(Path(provenance['qualification_path']));binding=q['accepted_observer_binding']
    if not binding['callback_source_files'] or not set(binding['callback_source_files'].items())<=set(q['source_files'].items()):
        raise ValueError('observer callbacks not in qualified compiled closure')
    trace=D.S.load(Path(provenance['journal_path']))
    if trace['timebase']!='native_core_clk':raise ValueError('unimplemented CDC cannot enroll a native journal')
    if provenance['parameters'].get('SUN')!=256 or type(provenance['parameters'].get('SUN')) is not int:
        raise ValueError('observer source requires enrolled SUN256')
    if any(type(binding[k]) is not bool for k in ['require_complete','require_consumer_reads']):
        raise ValueError('explicit complete versus diagnostic-prefix scope required')
    packets=trace['observer_packets'];model=D.source_model()
    words={o['producer_node']:o['patched_producer_word_sha256'] for o in model['obligations']}
    contexts=[dict(node=p['identity']['node'],rank=p['identity']['rank'],accepted_front_pc=p['producer_pc'])
        for p in packets if p['kind']=='lease_accept']
    programs={r:Path(provenance['program_paths'][str(r)]).read_text().splitlines() for r in range(4)}
    D.check_program_contexts(dict(vector_contexts=contexts),binding,programs,words)
    result=validate_packets(packets,binding['sinkseat_credits'],complete=binding['require_complete'])
    result['actual_runtime_enrolled']=True
    if binding['require_consumer_reads']:
        consumer_words={h['consumer_node']:h['consumer_template_word_sha256']
            for o in model['obligations'] for h in o['first_static_consumer']}
        D.check_program_contexts(trace,binding,programs,consumer_words)
        result['baseline_consumer_association']=baseline_consumer_join(trace,packets)
    # Enrollment does not supply baseline accepted consumer reads/physical time.
    result['deadline_join_entry']='dsrom_I66_consumer_deadline.py --enrollment/--slots/--service'
    return result


if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('--enrollment',type=Path)
    a.add_argument('--out',type=Path,required=True);p=a.parse_args()
    result=current_packets(D.S.load(p.enrollment)) if p.enrollment else source_plan()
    p.out.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
