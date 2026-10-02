#!/usr/bin/env python3
"""Source-program consumer obligations and accepted-read deadline calibration.

Static order is not a deadline. A complete source/binary/program-enrolled
current journal must contain actual producer/publication/read/context events.
No copied phase origin, predicted read, busy/PC timer or physical-clock credit.
"""
import argparse
import collections
import copy
import gzip
import json
from pathlib import Path
import dsrom_I66_actual_service_join as J
S=J.S
ROOT=J.R.ROOT
OUT=ROOT/'results/uarch/dsrom_I66_consumer_deadline_20261002'


def source_model():
    demand=json.loads(gzip.decompress((OUT/'inputs/demand-r5.json.gz').read_bytes()))
    nodes=[n for n in demand['nodes'] if n.get('kind')=='instruction' and n.get('scope')==0]
    calls=S.load(OUT/'inputs/selected_six_calls.json')['calls']
    core=(J.P.OUT/'inputs/core.sv.txt').read_text();tile=(J.P.OUT/'inputs/tile.sv.txt').read_text()
    vec=(OUT/'inputs/vec.sv.txt').read_text();lane=(OUT/'inputs/vec_lane.sv.txt').read_text()
    adapt=(OUT/'inputs/su_adapt.sv.txt').read_text()
    for text,needle in [(core,'wire waited = ((d_wait & ~(idles & ~gos)) == 5\'d0);'),
                        (tile,"2'd0: xs_rd_q[32*q +: 32] <= vm[xa[VM_AW-1:0]];"),
                        (vec,"assign ready = (pst == 2'd0);"),
                        (vec,'assign dbg_eseq = a_seq;'),
                        (vec,'a_seq, last_v, a_red'),
                        (vec,'wire [7:0]  r_seq   = rm[WR-1 -: 8];'),
                        (vec,".DEPTHS({16'd5, 16'd3})"),
                        (adapt,'assign ready = !pend;'),
                        (lane,"m_v <= mr_v; x_v <= m_v;"),
                        (lane,'assign rd_re = {4{mr_v}};')]:
        if needle not in text:raise ValueError('source consumer contract changed')
    obligations=[]
    for call in calls:
        b=call['binding'];pc=int(b['node'].split('I')[1]);lo=b['consumer_output_base_elements']
        hits=[]
        for n in sorted(nodes,key=lambda n:n['instruction_index']):
            i=n['instruction']
            if n['instruction_index']<=pc or i.get('unit')!=2:continue
            for operand in ['a','b','c','d']:
                if (i.get(operand+'_src',0)==0 and i.get(operand+'_base')==lo
                    and i.get(operand+'_si',1)==1 and i.get('su_nin')==576):
                    hits.append(dict(consumer_node=n['id'],operand=operand,
                        consumer_template_word_sha256=n['template_word_sha256'],
                        wait_mask=i.get('wait',0),instruction_predicate=i.get('pred',0)))
            if hits:break
        if not hits:raise ValueError('no source consumer footprint')
        obligations.append(dict(producer_node=b['node'],output_VM_elements=[lo,lo+576],
            first_static_consumer=hits,actual_first_read_edge=None,
            patched_producer_word_sha256=J.hashlib.sha256(int(call['word']['word_hex'],16).to_bytes(256,'little')).hexdigest(),
            phase_choices=b['phase_choices']))
    return dict(schema='opentallas.I66.accepted-consumer-deadline.v1',obligations=obligations,
        core_sha256=S.sha(J.P.OUT/'inputs/core.sv.txt'),
        static_order_is_not_deadline=True,actual_current_program_journal=None,
        timebase_required='native_core_clk; read preedge and publication postNBA explicitly distinguished',
        source_contract=dict(SU_ready_does_not_mean_pipeline_idle=True,
            consumer_owner='Actual accepted vector sequence/context, never latest core PC',
            read_tag_binding='Accepted VM read at edgeR -> actual control X tag at R+2; two source registers, not predicted progress',
            memory_read='xs_rd_re[port] && xs_rd_src[2*port+:2]==0; full resolved VM address',
            same_edge_publication_meets_read=False,
            indexed_origin_not_remote_resolved_origin=True),
        passive_observer_model=dict(hardware_ports=0,hardware_state=0,new_RTL=False,
            required_existing_signals=['core su_go/su_ready and PC at front acceptance',
                'u_su.v_acc/seq/cp; owner context of latched command',
                'u_vec.dbg_emit/dbg_eseq and read-aligned control context',
                'xs_rd_re/src/addr/q; tile VM old data at accepted read',
                'producer/home writer identity and postNBA visibility',
                'source idle, all packet ACKs and completion credit'],
            read_ports_at_SUN256=1024,observer_cost_not_measured=True,
            compilation_or_runtime_admission=False),
        fulltoken=False,physical_admission=False)


def bind_actual_read_tags(reads,tags):
    """Join accepted raw VM reads to OBSERVED X-control tags two edges later.

    Source fetch control uses 3/5 cycles for linear/gather paths, respectively;
    the lane's mr_v -> m_v -> x_v path places the tag two edges after read.
    Missing/faulted tags cannot be synthesized from a last-seen emitter seq.
    Input lifetime/rank/generation are the qualified collector's context.
    """
    source_model()
    indexed={}
    for t in tags:
        edge=J.uint(t['edge']);rank=J.uint(t['rank'],2)
        if J.uint(t['valid'],1)!=1 or J.uint(t['fault'],1)!=0:
            raise ValueError('invalid/colliding source read tag')
        key=(rank,edge)
        if key in indexed:raise ValueError('duplicate source X tag')
        indexed[key]=t
    result=[]
    for read in reads:
        r=copy.deepcopy(read);key=(J.uint(r['identity']['rank'],2),J.uint(r['edge'])+2)
        if key not in indexed:raise ValueError('actual read-aligned X tag missing')
        tag=indexed[key]
        for k in ['generation','user','xversion']:
            J.uint(tag[k],32)
            if tag[k]!=r['identity'][k]:raise ValueError('stale source read tag context')
        r['source_seq']=J.uint(tag['seq'],8);result.append(r)
    return result


def operation_id(c,model):
    fields={'node','expert','rank','generation','user','xversion','owner_stage','phase','key_word'}
    if set(c)!=fields:raise ValueError('complete command/lease identity required')
    widths=dict(expert=9,rank=2,generation=32,user=32,xversion=32,owner_stage=6,phase=10,key_word=32)
    for k,w in widths.items():J.uint(c[k],w)
    try:o=next(o for o in model['obligations'] if o['producer_node']==c['node'])
    except StopIteration as e:raise ValueError('unknown source producer') from e
    choice=next((p for p in o['phase_choices'] if p['expert']==c['expert']),None)
    if choice is None or any(c[k]!=choice[v] for k,v in [('owner_stage','stage'),('phase','phase'),('key_word','source_key_word')]):
        raise ValueError('wrong selected owner/phase/key')
    return o


def calibrate(trace,candidate_slots):
    """Per-row deadlines from actual accepted reads, not consumer issue edges.

    Normalized context records must come from qualified source hooks. seq is
    eight-bit source state; repeated seq uses require disjoint accepted/done
    lifetimes. A caller cannot label a read with whatever core PC is current.
    All supplied operations need full576 publication/read coverage. A partial
    prefix returns no PASS. Candidate slots are guarantees, not observed debt.
    """
    trace=copy.deepcopy(trace);candidate_slots=copy.deepcopy(candidate_slots)
    model=source_model()
    if trace['timebase']!='native_core_clk':raise ValueError('no common qualified clock/edge timebase')
    if trace['role']!='BASELINE_CURRENT_PROGRAM':raise ValueError('candidate-delayed reads cannot establish a no-loss baseline deadline')
    contexts=trace['vector_contexts']
    for c in contexts:
        for k,w in [('seq',8),('rank',2),('generation',32),('user',32),('xversion',32)]:J.uint(c[k],w)
        if J.uint(c['accept_edge'])>=J.uint(c['done_edge']):raise ValueError('invalid actual vector lifetime')
    operations={};last=-1
    for ordinal,e in enumerate(trace['events']):
        if J.uint(e['ordinal'])!=ordinal or J.uint(e['edge'])<last:raise ValueError('unordered accepted journal')
        last=e['edge'];ob=operation_id(e['identity'],model)
        key=tuple(e['identity'][k] for k in sorted(e['identity']))
        if e['kind']=='producer_accept':
            if key in operations:raise ValueError('spent operation identity')
            operations[key]=dict(identity=e['identity'],accept=e['edge'],publications={},reads={},source_idle=None,ACKs=set(),obligation=ob)
            continue
        if key not in operations:raise ValueError('callback before actual producer acceptance')
        op=operations[key];kind=e['kind']
        if kind=='home_postNBA':
            row=J.uint(e['row'],10);data=J.uint(e['data'],32)
            if row>=576 or row in op['publications'] or J.uint(e['address'],19)!=ob['output_VM_elements'][0]+row or e['edge']<=op['accept']:
                raise ValueError('foreign/duplicate publication')
            op['publications'][row]=(e['edge'],data)
        elif kind=='consumer_VM_read':
            if J.uint(e['valid'],1)!=1 or J.uint(e['src'],2)!=0:raise ValueError('not an accepted VM read')
            port=J.uint(e['port'],10);addr=J.uint(e['address'],19);row=addr-ob['output_VM_elements'][0]
            if not 0<=row<576 or row not in op['publications']:raise ValueError('read before owned publication')
            pub,data=op['publications'][row]
            if pub>=e['edge'] or J.uint(e['data_pre'],32)!=data:raise ValueError('same-edge/late publication or stale read data')
            seq=J.uint(e['source_seq'],8)
            owners=[c for c in contexts if c['seq']==seq and all(c[k]==e['identity'][k] for k in ['rank','generation','user','xversion']) and c['accept_edge']<=e['edge']<c['done_edge']]
            if len(owners)!=1:raise ValueError('ambiguous/stale source vector owner')
            target=ob['first_static_consumer'][0]
            if owners[0]['node']!=target['consumer_node'] or 'abcd'[port%4]!=target['operand']:
                raise ValueError('read owner/operand differs from source consumer')
            op['reads'][row]=min(e['edge'],op['reads'].get(row,e['edge']))
        elif kind=='source_idle':
            if op['source_idle'] is not None:raise ValueError('duplicate source retirement')
            if J.uint(e['busy_seen'],1)!=1 or J.uint(e['adapter_fault'],1)!=0 or J.uint(e['spine_fault'],1)!=0:
                raise ValueError('idle without accepted healthy busy lifetime')
            op['source_idle']=e['edge']
        else:raise ValueError('not a source accepted consumer/publication event')
    if not operations:raise ValueError('no actual operations')
    results=[]
    for op in operations.values():
        if set(op['publications'])!=set(range(576)) or set(op['reads'])!=set(range(576)) or op['source_idle'] is None:
            raise ValueError('partial prefix: complete publication/read/retirement required')
        proposed=[p for p in candidate_slots if p['identity']==op['identity']]
        rows={}
        for p in proposed:
            operation_id(p['identity'],model)
            row=J.uint(p['row'],10);edge=J.uint(p['postNBA_edge'])
            if row>=576 or row in rows or edge<=op['accept']:raise ValueError('invalid reserved publication slot')
            if edge>=op['reads'][row]:raise ValueError('reserved service misses actual consumer deadline')
            rows[row]=edge
        if set(rows)!=set(range(576)):raise ValueError('no guaranteed slot for every row')
        results.append(dict(identity=op['identity'],first_actual_read=min(op['reads'].values()),
            last_actual_read=max(op['reads'].values()),source_idle=op['source_idle'],
            last_reserved_publication=max(rows.values()),
            minimum_edge_margin=min(op['reads'][row]-rows[row] for row in rows),
            per_row_read_deadlines=op['reads']))
    if len(candidate_slots)!=576*len(operations):raise ValueError('foreign reserved operation')
    return dict(status='PASS_RESERVED_SLOTS_BEFORE_ACTUAL_ACCEPTED_READS',operations=results,
        deadline_role='BASELINE_CURRENT_PROGRAM',
        actual_read_deadlines_observed=True,candidate_service_measured=False,
        all_transport_ACK_and_credit_debt_proved=False,whole_token_no_loss=False,
        hardware_admission=False,arithmetic_golden_qualification=False)


def reserved_service_join(trace, service):
    """Compose globally charged provider slots with baseline read deadlines.

    Calendars are qualified inputs, not generated from observed candidate
    reads. ALL operations share one reservation, so a physical domain cannot
    be sold twice at one edge. Delivery/ACK bounds remain provider obligations.
    The enrolled entry additionally pins this complete reviewed service file.
    """
    service=copy.deepcopy(service);trace=copy.deepcopy(trace)
    if service['timebase']!='native_core_clk' or service['timebase']!=trace['timebase']:
        raise ValueError('service slots and actual reads lack common qualified clock')
    model=source_model();events=[];calendars={}
    for index,c in enumerate(service['calendars']):
        operation_id(c['identity'],model)
        key=json.dumps(c['identity'],sort_keys=True)
        if key in calendars:raise ValueError('duplicate phase service calendar')
        for h in ['source_calendar_sha256','phase_source_sha256']:
            v=c[h]
            if type(v) is not str or len(v)!=64 or any(x not in '0123456789abcdef' for x in v):
                raise ValueError('qualified phase calendar hash required')
        accept=J.uint(c['accepted_edge']);idle=J.uint(c['source_idle_edge'])
        if idle<=accept:raise ValueError('source idle precedes accepted lifetime')
        calendars[key]=c
        kinds={e['kind'] for e in c['source_boundary_events']}
        if not {'input','cfg','activation','result'}<=kinds:
            raise ValueError('incomplete phase boundary service calendar')
        for e in c['source_boundary_events']:
            if e['kind'] not in {'input','cfg','activation','result'}:
                raise ValueError('unknown source boundary event')
            if e['kind']!='input' and not accept<=J.uint(e['release'])<idle:
                raise ValueError('source emission outside accepted phase lifetime')
            events.append(dict(e,id=str(index)+':'+e['id'],identity=c['identity']))
    if not events:raise ValueError('no source service calendars')
    reservation=J.R.reserve(events,service['domains'])
    slots=[];completions=[]
    for key,c in calendars.items():
        actual=[e for e in trace['events'] if e['identity']==c['identity']]
        accepts=[e['edge'] for e in actual if e['kind']=='producer_accept']
        idles=[e['edge'] for e in actual if e['kind']=='source_idle']
        if accepts!=[c['accepted_edge']] or idles!=[c['source_idle_edge']]:
            raise ValueError('phase calendar origin/retirement differs from baseline')
        ev=[e for e in reservation['events'] if e['identity']==c['identity']]
        inp=[e for e in ev if e['kind']=='input']
        if len(inp)!=1 or inp[0]['bits']!=5120*32 or inp[0]['visible']>J.uint(c['first_VM_read_edge']):
            raise ValueError('K5120 input not guaranteed before source read')
        ob=operation_id(c['identity'],model)
        for e in ev:
            if e['kind']=='result':
                row=J.uint(e['row'],10)
                if J.uint(e['address'],19)!=ob['output_VM_elements'][0]+row:
                    raise ValueError('reserved result destination differs from program')
                slots.append(dict(identity=c['identity'],row=row,postNBA_edge=e['visible']))
        completion=max(c['source_idle_edge'],max(e['retirement'] for e in ev))+1
        completions.append(dict(identity=c['identity'],successful_completion_edge=completion,
            successful_service_edges=completion-c['accepted_edge']))
        for other in service['calendars']:
            same_owner=all(other['identity'][k]==c['identity'][k] for k in ['rank','owner_stage'])
            if same_owner and c['accepted_edge']<other['accepted_edge']<completion:
                raise ValueError('owner reused before source idle/all reserved ACK retirements')
    result=calibrate(trace,slots)
    result.update(status='PASS_CONDITIONAL_SERVICE_BEFORE_BASELINE_READS',
        finite_conditional_service=completions,reservation=reservation,
        provider_delivery_ACK_guarantees_measured=False,
        phase_calendars_independently_qualified_required=True,
        all_transport_ACK_and_credit_debt_proved=False)
    return result


def qualified_service_calendars(service,binding):
    """Require reviewed phase files, not calendar hashes without a preimage."""
    records=binding['service_calendar_files']
    if len(records)!=len(service['calendars']):
        raise ValueError('incomplete reviewed service calendar preimages')
    for c,r in zip(service['calendars'],records):
        calendar_path=J.file_pin(r['calendar_path'],c['source_calendar_sha256'])
        J.file_pin(r['phase_path'],c['phase_source_sha256'])
        body={k:v for k,v in c.items() if k not in ['source_calendar_sha256','phase_source_sha256']}
        if S.load(calendar_path)!=body:
            raise ValueError('reserved phase schedule differs from reviewed source calendar')


def check_program_contexts(trace,binding,programs,expected_words):
    """Bind accepted vector ownership to actual enrolled program words."""
    for context in trace['vector_contexts']:
        node=context['node'];pc=J.uint(context['accepted_front_pc'],14)
        rank=J.uint(context['rank'],2)
        if node not in expected_words:
            continue  # Other contexts stay in the seq-wrap ambiguity checks.
        mapped=J.uint(binding['node_program_map'][node][str(rank)],14)
        if mapped!=pc or pc>=len(programs[rank]):
            raise ValueError('source consumer node not bound to actual accepted PC')
        word=int(programs[rank][pc],16)
        J.uint(word,2048)
        if J.hashlib.sha256(word.to_bytes(256,'little')).hexdigest()!=expected_words[node]:
            raise ValueError('actual program consumer word differs from source footprint')


def enrolled_join(provenance,slots_path,service_path=None):
    J.current_enrollment(provenance)
    if provenance['parameters'].get('SUN')!=256 or type(provenance['parameters'].get('SUN')) is not int:
        raise ValueError('source-sized SUN256 read observer binding required')
    q=S.load(Path(provenance['qualification_path']))
    binding=q['consumer_deadline_binding']
    J.file_pin(slots_path,binding['reserved_slots_sha256'])
    J.file_pin(OUT/'inputs/selected_six_calls.json',binding['source_calls_sha256'])
    if not binding['callback_source_files'] or not set(binding['callback_source_files'].items())<=set(q['source_files'].items()):
        raise ValueError('consumer callbacks not compiled in enrolled source')
    required={S.sha(OUT/'inputs'/name) for name in ['vec.sv.txt','vec_lane.sv.txt','su_adapt.sv.txt']}
    if not required<=set(q['source_files'].values()):
        raise ValueError('read ownership/tag source not in enrolled closure')
    trace=S.load(Path(provenance['journal_path']))
    expected_words={x['consumer_node']:x['consumer_template_word_sha256']
                    for o in source_model()['obligations'] for x in o['first_static_consumer']}
    programs={rank:Path(provenance['program_paths'][str(rank)]).read_text().splitlines() for rank in range(4)}
    check_program_contexts(trace,binding,programs,expected_words)
    reads=[e for e in trace['events'] if e['kind']=='consumer_VM_read']
    bound=bind_actual_read_tags(reads,trace['read_X_tags'])
    for before,after in zip(reads,bound):
        if before.get('source_seq')!=after['source_seq']:
            raise ValueError('normalized consumer ownership differs from observed read X tag')
    if service_path is None:
        raise ValueError('current composed deadline gate requires reviewed finite service plan')
    J.file_pin(service_path,binding['service_plan_sha256'])
    service=S.load(service_path)
    qualified_service_calendars(service,binding)
    result=reserved_service_join(trace,service)
    supplied=calibrate(trace,S.load(slots_path))
    if supplied['operations']!=result['operations']:
        raise ValueError('supplied slots differ from globally reserved service slots')
    expected={(o['producer_node'],rank) for o in source_model()['obligations'] for rank in range(4)}
    observed={(o['identity']['node'],o['identity']['rank']) for o in result['operations']}
    if observed!=expected:raise ValueError('partial current-program target-node/rank coverage')
    result['coverage_scope']='Actual current-program L0 twelve W1/W3 consumers xTP4; not all layers/fulltoken'
    return result


if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('--enrollment',type=Path)
    a.add_argument('--slots',type=Path);a.add_argument('--service',type=Path);a.add_argument('--out',type=Path,required=True)
    p=a.parse_args()
    if p.enrollment:
        if not p.slots:a.error('require reviewed --slots')
        result=enrolled_join(S.load(p.enrollment),p.slots,p.service)
    else:result=source_model()
    p.out.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
