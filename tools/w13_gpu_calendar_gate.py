#!/usr/bin/env python3
"""Full-program candidate service audit; never hardware qualification.

Time is integer 3.6GHz ticks: serial cycle=4, fast cycle=3. Instruction events
explicitly bind graph_op, sm, partition, rf_read_tick, issue_tick, finish_tick,
RF read/write bits, peak_registers and shared read/write word addresses. Fabric
sectors bind graph_op, quadrant, lane, launch/accept/consumer_done/credit_return
and service_tick. Every graph op needs complete ordinary lowering confirmation.
Candidate timing assumptions require later exact RTL and contextual SS/FF.
"""
from collections import Counter,defaultdict
import hashlib,json,subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

CORE={'FADD':7,'FMUL':7,'IADD':7,'FCMP':7,'SHFL':5,'DIV':19,'LOAD':2,'STORE':1}


def authoritative_dependencies(pin, repo):
    if not isinstance(pin,dict): raise ValueError('sourcebound_graph_pin_required')
    data=subprocess.check_output(['git','show',pin['source_git']+':'+pin['path']],cwd=repo)
    if hashlib.sha256(data).hexdigest()!=pin['sha256']:raise ValueError('graph_source_hash_mismatch')
    nodes=json.loads(data)['instructions'];deps={}
    for node in nodes:
        key=node['id'];edges=node['dependencies']
        if type(key) is not int or key in deps or not isinstance(edges,list) or any(type(d) is not int for d in edges):raise ValueError('invalid_authoritative_graph')
        deps[key]=set(edges)
    done=set()
    while len(done)<len(deps):
        ready={key for key,edges in deps.items() if key not in done and edges<=done}
        if not ready:raise ValueError('unknown_or_cyclic_authoritative_dependency')
        done|=ready
    return deps


def audit(graph_pin, instruction_events, fabric_events, lowerings, repo=ROOT):
    issues=[];seen=set();issue=Counter();rf_issue=Counter();rf_reads=Counter();writes=Counter();write_bits=Counter();shared=Counter();divider=Counter()
    try: deps=authoritative_dependencies(graph_pin,repo)
    except (ValueError,KeyError,TypeError,subprocess.CalledProcessError) as e:
        deps={};issues.append('authoritative_graph_unbound:'+str(e))
    expected=set(deps);actual_instructions=Counter(e['graph_op'] for e in instruction_events);actual_edges=Counter(e['graph_op'] for e in fabric_events)
    if not expected: issues.append('empty_program')
    for key in expected:
        row=lowerings.get(str(key),{})
        for field in ('ordinary_lowering_complete','issue_RF_calendar_complete','shared_bank_map_complete','fabric_edge_calendar_complete','SFU_lowering_complete'):
            if row.get(field) is not True:issues.append(f'missing_{field}:{key}')
        for field,actual in (('required_instruction_events',actual_instructions[key]),('required_fabric_events',actual_edges[key])):
            if type(row.get(field)) is not int or row[field]!=actual:issues.append(f'unbound_or_incomplete_{field}:{key}')
        if set(row.get('dependencies',[]))!=deps[key]:issues.append('callback_dependency_mismatch:'+str(key))
        for dep in deps[key]:
            producer=[e['finish_tick'] for e in instruction_events if e['graph_op']==dep]+[(e.get('write_visible_tick',e['accept_tick'])) for e in fabric_events if e['graph_op']==dep and e.get('phase') in ('read_response','write_commit')]
            consumer=[e['rf_read_tick'] for e in instruction_events if e['graph_op']==key]+[e['launch_tick'] for e in fabric_events if e['graph_op']==key]
            if dep not in expected or not producer or not consumer or min(consumer)<max(producer):issues.append('graph_dependency_not_visible:'+str(key))
    for e in instruction_events:
        key=e['graph_op'];seen.add(key)
        if key not in expected:issues.append('unknown_graph_op:'+str(key))
        sm,part=e['sm'],e['partition'];op=e['opcode'];r,i,f=e['rf_read_tick'],e['issue_tick'],e['finish_tick']
        if not (0<=sm<32 and 0<=part<4):issues.append('invalid_SM_partition')
        if any(type(t) is not int or t<0 or t%4 for t in (r,i,f)):issues.append('serial_phase')
        if op not in CORE:issues.append('unbound_opcode:'+op);continue
        if not(0<=e['peak_registers']<=32):issues.append('RF_register_capacity')
        read,write=e['RF_read_bits'],e['RF_write_bits']
        if not(0<=read<=2048 and 0<=write<=1024):issues.append('partition_RF_ports')
        if read and i<r+8:issues.append('RF_latency_not_priced')
        if f<i+4*CORE[op]:issues.append('opcode_latency_not_priced')
        if any(t>r for t in e.get('producer_visible_ticks',[])):issues.append('dependency_before_RF_visible')
        issue[sm,part,i]+=1
        if read:rf_issue[sm,part,r]+=1;rf_reads[sm,r]+=read
        if write:writes[sm,part,f]+=1;write_bits[sm,f]+=write
        if op=='DIV':
            # An issued warp event must bind its actual participating lanes.
            # The single scalar divider still admits only one lane per cycle;
            # invalid counts must never subtract from its occupancy.
            active=e.get('active_lanes')
            if type(active) is not int or not 1<=active<=32:
                issues.append('invalid_DIV_active_lanes')
            else:
                divider[sm,i]+=active
        if set(e.get('shared_read_words',[])) & set(e.get('shared_write_words',[])) and e.get('shared_collision_policy')!='forward_committed':issues.append('shared_same_address_RW_unbound')
        if e.get('shared_write_words') and e.get('partial_word_write') and not e.get('masked_write_exact_gate'):issues.append('shared_masked_write_unbound')
        for direction in ('read','write'):
            words=e.get('shared_'+direction+'_words',[])
            if words and op not in ('LOAD','STORE'):issues.append('unbound_shared_access')
            for address in words:
                if type(address) is not int or not 0<=address<16384:issues.append('shared_address_capacity');continue
                shared[sm,i,direction,address%32]+=1
    for key in expected:
        row=lowerings.get(str(key),{})
        if key not in seen and row.get('zero_instruction_address_view') is not True:issues.append('missing_instruction_events:'+str(key))
    for counts,limit,name in ((issue,1,'partition_issue'),(rf_issue,1,'partition_RF_issue'),(rf_reads,8192,'SM_RF_reads'),(writes,1,'partition_writeback'),(write_bits,4096,'SM_RF_writes'),(shared,1,'shared_bank_port'),(divider,1,'single_scalar_DIV')):
        if any(n>limit for n in counts.values()):issues.append(name+'_overbooked')
    lanes=Counter();service=Counter();credits=defaultdict(list)
    requests={};responses=Counter()
    for e in fabric_events:
        if e.get('phase')=='read_request':
            tx=e.get('transaction_id')
            if tx is None or tx in requests:issues.append('unbound_or_duplicate_read_request')
            requests[tx]=e
    for e in fabric_events:
        key=e['graph_op'];q,l=e['quadrant'],e['lane'];t,a,d,c=e['launch_tick'],e['accept_tick'],e['consumer_done_tick'],e['credit_return_tick'];s=e['service_tick']
        if key not in expected:issues.append('unknown_fabric_graph_op')
        if not(0<=q<4 and 0<=l<24):issues.append('invalid_fabric_quad_lane')
        if e.get('payload_bytes')!=32 or e.get('packet_bits')!=320:issues.append('fabric_width_contract')
        if e.get('direction') not in ('read','write'):issues.append('fabric_direction')
        if any(type(x) is not int or x<0 or x%3 for x in (t,a,c,s)) or type(d) is not int or d<0:issues.append('fabric_phase')
        if a<t+53*3 or d<a or c<max(d,t+115*3):issues.append('fabric_latency_or_consumer_credit_not_priced')
        phase=e.get('phase');charge=32
        if phase=='read_request':
            charge=0
            if e.get('direction')!='read' or not a<=s<=d<=c:issues.append('read_request_service_order')
        elif phase=='read_response':
            tx=e.get('transaction_id');request=requests.get(tx);responses[tx]+=1
            if e.get('direction')!='read' or request is None or not request['service_tick']<=s<=t<=a<=d<=c:issues.append('read_response_service_order')
            if request is not None and (request['graph_op']!=key or request['quadrant']!=q):issues.append('read_response_request_identity')
        elif phase=='write_commit':
            visible=e.get('write_visible_tick')
            if e.get('direction')!='write' or type(visible) is not int or visible<0 or visible%3 or not t<=a<=s<=visible<=d<=c:issues.append('write_commit_service_order')
        else:issues.append('unbound_fabric_service_phase')
        lanes[q,l,e.get('direction'),t]+=1
        service[q,s]+=charge  # response READ+committed WRITE share750; requests grant no payload service
        credits[q,l,e.get('direction')].extend([(t,1),(c,-1)])
    if any(responses[tx]!=1 for tx in requests):issues.append('missing_or_duplicate_read_response')
    if any(n>1 for n in lanes.values()):issues.append('fabric_lane_overbooked')
    if any(n>750 for n in service.values()):issues.append('combined_service_750B_overbooked')
    peak=0
    for events in credits.values():
        used=0
        for t,delta in sorted(events):  # returns before same-tick new launches
            used+=delta;peak=max(peak,used)
            if used<0 or used>128:issues.append('finite_credit_violation')
        if used:issues.append('credits_not_returned')
    return dict(schema='opentallas.w13.fullprogram-calendar-gate.v2',
                authoritative_graph_pin=graph_pin if isinstance(graph_pin,dict) else None,
                modeled_service_calendar_closed=not issues,issues=sorted(set(issues)),
                graph_ops=len(expected),instruction_events=len(instruction_events),fabric_events=len(fabric_events),max_lane_credits=peak,
                common_tick_hz=3600000000,serial_cycle_ticks=4,fast_cycle_ticks=3,
                physical_build_ready=False,hardware_adopted=False,speed_credit=0,
                qualification='Candidate calendar audit only; actual RTL, arithmetic, wirestage and contextual SS/FF remain mandatory.')
