#!/usr/bin/env python3
"""Finite candidate service calendar. Backend events are inputs, never guessed.

Transport timing is composed around actual controller events. Missing backend,
client ownership, publication, or consumer readiness fails closed. This is an
analytical candidate, not a qualification of existing RTL or a token rate.
"""
from fractions import Fraction
from collections import defaultdict

FAST = Fraction(10**12, 1200000000)
SLOW = Fraction(10**12, 900000000)


def cdc(time_ps, destination_period):
    """Two destination synchronizer stages plus registered delivery.

    At an exactly coincident edge, use the next edge conservatively. Clock
    phase zero is an explicit candidate assumption, not physical closure.
    """
    return (time_ps // destination_period + 3) * destination_period


def read_calendar(events, clients, ready_bounds, pc_depth=2, output_depth=2):
    """Calendar finite 32-PC to client/four-sector-bank response transport.

    Events carry actual backend return timestamps and ownership. Each bank has
    one 32B acceptance/cycle; every PC and client bank has finite landing slots.
    Consumer ready bound is mandatory and excludes backend latency. Input
    backpressure is reported, never hidden by accepting an unbounded trace.
    """
    if not isinstance(clients, int) or clients <= 0:
        raise ValueError('finite client population required')
    if pc_depth !=2 or output_depth !=2:
        raise ValueError('baseline two landing credits frozen; extra credits require separate candidate binding')
    for client in range(clients):
        if not isinstance(ready_bounds.get(client), int) or ready_bounds[client] < 1:
            raise ValueError('positive finite consumer ready bound required')
    pc_slots=defaultdict(lambda: [Fraction(0)]*pc_depth)
    output_slots=defaultdict(lambda: [Fraction(0)]*output_depth)
    bank_next=defaultdict(Fraction); pc_next=defaultdict(Fraction)
    result=[]; byte_slots=defaultdict(int); tags=set()
    # Conservative global arrival order. Equal-time ties rotate PC priority within
    # each destination bank; no starvation through fixed low-PC priority.
    rr=defaultdict(int)
    pending=list(events)
    while pending:
        for e in pending:
            if not {'return_ps','pc','client','sector','tag'} <= e.keys():
                raise ValueError('actual return event/ownership/tag required')
            if not 0<=e['pc']<32 or not 0<=e.get('stack',0)<4 or not 0<=e['client']<clients or e['sector']<0:
                raise ValueError('invalid owner/PC/sector')
        def key(e):
            bank=(e['client'],e['sector']%4)
            return (Fraction(e['return_ps']), (e.get('stack',0)*32+e['pc']-rr[bank])%128)
        e=min(pending,key=key); pending.remove(e)
        identity=(e.get('stack',0),e['tag'],e['sector'])
        if identity in tags:raise ValueError('duplicate live response sector/tag')
        tags.add(identity)
        returned=Fraction(e['return_ps']); pc=e['pc']; client=e['client']
        stack=e.get('stack',0); source=(stack,pc)
        bank=(client,e['sector']%4); ppool=pc_slots[source]
        pi=min(range(pc_depth),key=ppool.__getitem__)
        # Full input landing means backend valid must be held until ready.
        accepted=max(returned,ppool[pi],pc_next[source])
        opool=output_slots[bank]; oi=min(range(output_depth),key=opool.__getitem__)
        grant=max((-(-accepted//FAST))*FAST,bank_next[bank],opool[oi])
        tick=-(-grant//FAST)
        # Conservative750B per controller/fabric cycle: no borrowed future
        # credit or unmodeled fractional-sector packing (23 whole sectors).
        while byte_slots[stack,tick]+32>750:tick+=1
        grant=tick*FAST;byte_slots[stack,tick]+=32
        # Frozen four-cycle registered route, then consumer clock crossing.
        delivered=cdc(grant+4*FAST,SLOW)
        consumed=delivered+ready_bounds[client]*SLOW
        returned_credit=max(grant+5*FAST,cdc(consumed,FAST))
        bank_next[bank]=grant+FAST; pc_next[source]=accepted+FAST
        ppool[pi]=grant+FAST; opool[oi]=returned_credit
        rr[bank]=(stack*32+pc+1)%128
        result.append(dict(tag=e['tag'],client=client,stack=stack,pc=pc,bank=bank[1],
            backend_return_ps=str(returned),accepted_ps=str(accepted),
            input_backpressure_ps=str(accepted-returned),crossbar_grant_ps=str(grant),
            consumer_delivery_ps=str(delivered),consumer_complete_ps=str(consumed),
            credit_return_ps=str(returned_credit)))
    return dict(status='COMPONENT_CALENDAR_NOT_FULL_TOKEN',timeline=result,
        done_ps=str(max((Fraction(r['credit_return_ps']) for r in result),default=0)),
        physical_admission=False,full_token_cycles=None)


def write_calendar(events, consumer_wait_cycles, transactions=4):
    """Four retained write/ACK credits; actual WR-visible events mandatory.

    Backend column and visibility must respect admitted request and ingress.
    RMW requires actual prior read/merge events. No request acceptance, timer,
    or synthetic fixed latency supplies completion. Consumer completion returns
    ownership through the reverse CDC; row publication is separately gated.
    """
    if transactions!=4 or not isinstance(consumer_wait_cycles,int) or consumer_wait_cycles<1:
        raise ValueError('frozen four write credits and finite consumer bound required')
    credits=[Fraction(0)]*transactions; ingress=Fraction(0); locks={}; rows=[];tags=set()
    for e in events:
        if not {'submit_ps','column_ps','visible_ps','sector','tag'}<=e.keys():
            raise ValueError('actual WR schedule and visible events required')
        sector=e['sector']; ci=min(range(transactions),key=credits.__getitem__)
        if e['tag'] in tags:raise ValueError('write tag reuse without controller drain')
        tags.add(e['tag'])
        admission=max(Fraction(e['submit_ps']),credits[ci],locks.get(sector,Fraction(0)))
        offer=cdc(admission,FAST)
        if e.get('partial',False):
            if not {'read_return_ps','merge_done_ps'}<=e.keys():
                raise ValueError('actual RMW read/merge events required')
            read_issue=max(offer,ingress)
            if Fraction(e['read_return_ps'])<read_issue or Fraction(e['merge_done_ps'])<Fraction(e['read_return_ps']):
                raise ValueError('RMW event precedes admission/read completion')
            offer=max(Fraction(e['merge_done_ps'])+FAST,read_issue+FAST)
        write_issue=max(offer,ingress)
        column=Fraction(e['column_ps']); visible=Fraction(e['visible_ps'])
        if column<write_issue or visible<column+7274:
            raise ValueError('WR event precedes issue or CWL+burst visibility')
        ingress=write_issue+FAST
        registered_ack=(visible//FAST+1)*FAST
        delivered=cdc(registered_ack,SLOW)
        consumed=delivered+consumer_wait_cycles*SLOW
        released=cdc(consumed,FAST)
        credits[ci]=released; locks[sector]=released
        rows.append(dict(tag=e['tag'],sector=sector,admission_ps=str(admission),
            write_issue_ps=str(write_issue),actual_column_ps=str(column),
            actual_visible_ps=str(visible),ACK_delivery_ps=str(delivered),
            consumer_complete_ps=str(consumed),credit_and_lock_release_ps=str(released)))
    return dict(status='COMPONENT_CALENDAR_NOT_FULL_TOKEN',timeline=rows,
        done_ps=str(max(credits)),physical_admission=False,full_token_cycles=None)


def profile():
    """Source-bound quantitative component profile; no missing backend defaults."""
    import hashlib,json,subprocess
    from pathlib import Path
    root=Path(__file__).resolve().parents[1]
    records=[('8625c420a','results/uarch/common_gpu_sector_crossbar_20261001/model_before_RTL_r4.json'),
        ('07a07ec5d','results/uarch/qwen_hbm_connected_20261001/common_GPU_WRACK_port_contract_r2.json'),
        ('66aa67ed1','results/uarch/qwen_hbm_connected_20261001/publication_model_negative_gate.json'),
        ('758d3425c','results/rtl/w11_ckv_current_readmode_binding_20261001.json')]
    pins={}
    for rev,path in records:
        blob=subprocess.check_output(['git','show',f'{rev}:{path}'],cwd=root)
        pins[path]=dict(commit=rev,sha256=hashlib.sha256(blob).hexdigest())
    cross=json.loads(subprocess.check_output(['git','show',f'{records[0][0]}:{records[0][1]}'],cwd=root))
    return dict(schema='opentallas.w19.finite-service-calendar-profile.v1',
        status='EXECUTABLE_COMPONENT_CALENDAR_BACKEND_AND_CONSUMER_BINDINGS_PENDING',
        source_pins=pins,calendar_source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        clocks=dict(fast_hz=1200000000,consumer_hz=900000000,phase_zero_candidate=True),
        route=dict(capture_cycle=0,local32_mux_cycle=1,stack4_merge_cycle=2,
            destination_landing_cycle=3,macro_write_ready_cycle=4,earliest_credit_cycle=5,
            mandatory_baseline_landing_credits=2,credits_include_inflight=True,
            ideal_no_stall_grants_per_bank='2/5 cycles',
            corrected36client_ceiling_bytes_per_cycle='1843.2',
            role='Mandatory finite-resource baseline correction, not optional performance optimization'),
        return_budget=dict(controllers=4,PCs_per_controller=32,PC_landing_entries=2,
            client_sector_banks=4,whole_sector_bits=256,
            bytes_per_controller_cycle=750,whole_sectors_per_cycle=23,
            note='Conservative no fractional-sector carry; same backend byte budget must include writes in a complete provider.'),
        cdc=dict(destination_sync_stages=2,registered_delivery_stages=1,
            priced_both_directions=True,physical_qualified=False,
            note='Coincident edge conservatively uses next destination edge. Candidate phase/latency, exact rational calendar; no contextual closure.'),
        writes=dict(retained_transactions_per_controller=4,ACK_reserved_slots=4,
            actual_WR_schedule_and_visibility_required=True,CWL_plus_burst_ps=7274,
            request_accept_is_completion=False,credit_release='consumer complete followed by reverseCDC',
            RMW='actual read/merge then write on same ingress; sector lock to consumer completion'),
        publication_owner='66aa67ed1; use stored row/epoch/producer commit+consumer reader refs, not echoed request epoch',
        crossbar_known_addons=cross['complete_known_addons'],
        candidate='Additional4route-entry geometry separate in owner record; not enabled or adopted here.',
        shared_controller_calendar_bound=False,actual_programme_descriptor_trace=None,
        DeepSeek_SM_clients=32,DeepSeek_total_client_population=None,DeepSeek_service_endpoint_roles='32 ordinary SM baseline; additional endpoint roles/ports remain unbound, no silent36-client copy',
        graph_integration='Consumer contracts provide actual backend events and finite readiness. Until complete, wholegraph costs remain missing; component bounds cannot substitute a phase.',
        physical_admission=False,maximum_qualified_clock_hz=None,full_token_cycles=None,full_token_rate=None)


if __name__=='__main__':
    import argparse,json
    from pathlib import Path
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args()
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(profile(),indent=2)+'\n')
